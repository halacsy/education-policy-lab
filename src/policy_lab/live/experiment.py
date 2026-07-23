"""Live A/B acceptance runner for the v2 artifact DAG."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlsplit

from policy_lab.dag import HumanGatePending, NodeExecutor, NodeSpec
from policy_lab.jsonio import canonical_json_bytes, content_hash, write_json
from policy_lab.i18n import BILINGUAL_VERSION, is_localized_text, localized, text
from policy_lab.live import contracts
from policy_lab.live.dag_spec import VERSION as DAG_VERSION, build_policy_analysis_dag
from policy_lab.schema_registry import SchemaRegistry
from policy_lab.store import ArtifactRef, ArtifactRepository

ARTIFACT_VERSION = BILINGUAL_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower()


def _cardinality_repair_instruction(
    constraints: dict[str, tuple[int, int]], violations: list[str]
) -> str:
    """Turn range failures into unambiguous exact targets for a retry.

    Anthropic's structured-output grammar cannot express array maxima. A retry
    that only repeats a range tends to over-correct one collection while
    under-filling another, so every collection receives a stable midpoint
    target on the replacement attempt.
    """

    targets = []
    for field, (minimum, maximum) in constraints.items():
        target = minimum if minimum == maximum else (minimum + maximum) // 2
        targets.append(
            f"{field} MUST contain exactly {target} items"
            f" (the accepted range is {minimum}-{maximum})"
        )
    return (
        "\n\nSTRICT CARDINALITY REPAIR: The previous complete response was rejected: "
        + "; ".join(violations)
        + ". Return a complete replacement. "
        + "; ".join(targets)
        + ". Do not return fewer or more items in any named collection."
    )


def _normalize_collection_counts(
    result: dict[str, Any], constraints: dict[str, tuple[int, int]]
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, int]]:
    """Trim deterministic surplus and report semantic deficits to fill."""

    normalized = dict(result)
    actions: list[dict[str, Any]] = []
    deficits: dict[str, int] = {}
    for field, (minimum, maximum) in constraints.items():
        values = list(normalized.get(field, []))
        if len(values) > maximum:
            actions.append({
                "field": field,
                "action": "truncate_surplus",
                "before": len(values),
                "after": maximum,
            })
            values = values[:maximum]
            normalized[field] = values
        if len(values) < minimum:
            deficits[field] = minimum - len(values)
    return normalized, actions, deficits


def _escalated_token_budget(max_tokens: int, error: Exception) -> int | None:
    """Return the bounded bilingual retry budget for a real truncation."""

    if "structured output truncated at max_tokens=" not in str(error):
        return None
    return min(max_tokens * 3 // 2, 48000)


class ArtifactDagRunner:
    """Run the live artifact DAG for production or a localized lens test."""

    def __init__(
        self,
        *,
        root: str | Path,
        output_root: str | Path,
        llm_module: Any,
        topic: str = "korai-szelekcio",
    ):
        self.root = Path(root)
        self.output_root = Path(output_root)
        self.topic = topic
        self.llm = llm_module
        self.schemas = SchemaRegistry(self.root / "schemas" / "v2")
        self.repository = ArtifactRepository(self.output_root, self.schemas)
        self.base_lenses = self._load(self.root / "config" / "v2" / "lenses.json")["lenses"]
        self.psychology = self._load(
            self.root / "config" / "v2" / "educational_psychology_lens.json"
        )
        self.topic_data = self._load(self.root / "topics" / topic / "topic.json")
        self.created_at = self._experiment_created_at()
        self.call_log_path = self.output_root / "backend_calls.jsonl"
        self.provider_generator = "anthropic"
        self.provider_judge = "openai"

    def run(self, arms: tuple[str, ...] = ("baseline", "psychology")) -> dict[str, Any]:
        results: dict[str, Any] = {}
        if "baseline" in arms:
            results["baseline"] = self.run_arm("baseline", include_psychology=False)
        if "psychology" in arms:
            results["psychology"] = self.run_arm("psychology", include_psychology=True)
        if {"baseline", "psychology"}.issubset(results) or self._arm_summary("baseline").exists() and self._arm_summary("psychology").exists():
            comparison = self.compare_arms()
            results["comparison"] = comparison
        self._write_cost_report()
        return results

    def run_production(self) -> dict[str, Any]:
        """Run one production replicate from the persisted declarative plan."""

        summary, plan_hash = self._run_planned_production()
        self._write_cost_report()
        write_json(self.output_root / "production_manifest.json", {
            "architecture_version": DAG_VERSION,
            "topic": self.topic,
            "run_id": summary["run_id"],
            "run_plan": {
                "content_hash": plan_hash,
                "path": f"runs/{summary['run_id']}/run_plan.json",
            },
            "root_refs": [
                summary["package_ref"], summary["evaluation_ref"],
                summary["readiness_ref"],
            ],
            "summary": summary,
            "completed_at": _now(),
        })
        return summary

    def _run_planned_production(self) -> tuple[dict[str, Any], str]:
        """Execute exactly the nodes and bindings in the compiled RunPlan."""

        arm = "production"
        run_id = f"live-{self.topic}-{arm}"
        run_dir = self.output_root / "runs" / run_id
        brief_mode = (
            "draft_and_approve"
            if "raw_question" in self.topic_data and "problem_brief" not in self.topic_data
            else "approved_root"
        )
        root_refs = self._admit_run_roots()
        dag = build_policy_analysis_dag(
            (lens["id"] for lens in self.base_lenses), brief_mode=brief_mode
        )
        plan = dag.compile(topic=self.topic, root_artifacts=root_refs)
        plan_path = run_dir / "run_plan.json"
        if plan_path.exists():
            existing = self._load(plan_path)
            if existing != plan.as_dict():
                raise ValueError(
                    f"RunPlan changed for existing run {run_id}; use a new run tag"
                )
        else:
            plan.write(plan_path)
        executor = NodeExecutor(
            repository=self.repository,
            run_dir=run_dir,
            source_root=self.root,
            run_id=run_id,
            artifact_created_at=self.created_at,
            topic=self.topic,
            run_plan_hash=plan.hash,
        )
        outputs: dict[str, tuple[ArtifactRef, ...]] = {}
        common_config = {"topic": self.topic, "run_plan_hash": plan.hash}

        if brief_mode == "draft_and_approve":
            node_id = "draft_problem_brief"
            node = plan.node(node_id)
            inputs = plan.resolve_inputs(node_id, outputs)
            brief_candidate_refs = executor.run(
                node.node_spec(),
                inputs=inputs,
                relevant_config=common_config,
                provider=node.provider,
                model=node.model,
                generation_parameters=dict(node.generation_parameters),
                prompt_hash=self._contract_hash("draft_problem_brief_v1"),
                builder=lambda pv: self._problem_brief_proposal_records(
                    inputs["question"][0], pv, node=node_id,
                    run_dir=run_dir, arm=arm,
                ),
            )
            outputs[node_id] = brief_candidate_refs
            self._report_node(run_dir, node_id)

            gate_id = "approve_problem_brief"
            gate_node = plan.node(gate_id)
            gate_inputs = plan.resolve_inputs(gate_id, outputs)
            candidate_ref = gate_inputs["candidate"][0]
            decision = self._require_problem_brief_decision(
                executor, run_dir, candidate_ref, plan.hash
            )
            gate_refs = executor.run(
                gate_node.node_spec(),
                inputs=gate_inputs,
                relevant_config={
                    **common_config, "decision_hash": content_hash(decision),
                },
                provider=gate_node.provider,
                model=gate_node.model,
                generation_parameters={},
                prompt_hash=content_hash({
                    "gate": gate_id, "version": gate_node.version,
                }),
                builder=lambda pv: self._approved_problem_brief_records(
                    candidate_ref, decision, pv
                ),
            )
            outputs[gate_id] = gate_refs
            self._report_node(run_dir, gate_id)

        for lens in self.base_lenses:
            node_id = f"research_{lens['id']}"
            node = plan.node(node_id)
            inputs = plan.resolve_inputs(node_id, outputs)
            problem = self.repository.get_by_hash(
                inputs["problem"][0].content_hash
            )["content"]
            exact_lens = {
                "id": lens["id"],
                **self.repository.get_by_hash(
                    inputs["lens"][0].content_hash
                )["content"],
            }
            refs = executor.run(
                node.node_spec(),
                inputs=inputs,
                relevant_config=common_config,
                provider=node.provider,
                model=node.model,
                generation_parameters=dict(node.generation_parameters),
                prompt_hash=self._contract_hash("research_v1"),
                builder=lambda pv, lens=exact_lens, node_id=node_id, problem=problem: self._research_records(
                    lens, pv, node=node_id, run_dir=run_dir, arm=arm,
                    problem=problem,
                ),
            )
            outputs[node_id] = refs
            self._report_node(run_dir, node_id)

        node_id = "normalize_evidence"
        node = plan.node(node_id)
        inputs = plan.resolve_inputs(node_id, outputs)
        normalized_refs = executor.run(
            node.node_spec(),
            inputs=inputs,
            relevant_config=common_config,
            provider=node.provider,
            model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("normalize_evidence_v1"),
            builder=lambda pv: self._normalize_evidence_records(
                inputs["problem"][0], inputs["evidence"], pv,
                node=node_id, run_dir=run_dir, arm=arm,
            ),
        )
        outputs[node_id] = normalized_refs
        self._report_node(run_dir, node_id)

        node_id = "derive_option_seeds"
        node = plan.node(node_id)
        inputs = plan.resolve_inputs(node_id, outputs)
        seed_refs = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=common_config,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("derive_option_seeds_v1"),
            builder=lambda pv: self._option_seed_records(
                inputs["problem"][0], inputs["normalized"], inputs["evidence"], pv,
                node=node_id, run_dir=run_dir, arm=arm,
            ),
        )
        outputs[node_id] = seed_refs
        self._report_node(run_dir, node_id)

        node_id = "cluster_option_seeds"
        node = plan.node(node_id)
        inputs = plan.resolve_inputs(node_id, outputs)
        option_refs = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=common_config,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("cluster_option_seeds_v1"),
            builder=lambda pv: self._cluster_option_seed_records(
                inputs["problem"][0], inputs["seeds"], pv,
                node=node_id, run_dir=run_dir, arm=arm,
            ),
        )
        outputs[node_id] = option_refs
        self._report_node(run_dir, node_id)

        gate_id = "approve_option_space"
        gate_node = plan.node(gate_id)
        gate_inputs = plan.resolve_inputs(gate_id, outputs)
        candidate_ref = gate_inputs["candidate"][0]
        decision = self._require_gate_decision(
            executor, run_dir, candidate_ref, plan.hash
        )
        gate_refs = executor.run(
            gate_node.node_spec(),
            inputs=gate_inputs,
            relevant_config={
                **common_config,
                "decision_hash": content_hash(decision),
            },
            provider=gate_node.provider,
            model=gate_node.model,
            generation_parameters={},
            prompt_hash=content_hash({"gate": gate_id, "version": gate_node.version}),
            builder=lambda pv: self._approved_option_space_records(
                candidate_ref, decision, pv
            ),
        )
        outputs[gate_id] = gate_refs
        self._report_node(run_dir, gate_id)

        node_id = "derive_transformations"
        node = plan.node(node_id)
        inputs = plan.resolve_inputs(node_id, outputs)
        problem = self.repository.get_by_hash(inputs["problem"][0].content_hash)["content"]
        approved = self.repository.get_by_hash(inputs["option_space"][0].content_hash)["content"]
        finding_refs = tuple(
            ref for ref in inputs["evidence"] if ref.record_type == "finding"
        )
        canonical_claim_refs = tuple(
            ref for ref in inputs["normalized"]
            if ref.record_type == "canonical_claim"
        )
        transformation_refs = executor.run(
            node.node_spec(),
            inputs=inputs,
            relevant_config=common_config,
            provider=node.provider,
            model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("derive_transformations_v1"),
            builder=lambda pv: self._transformation_records(
                finding_refs, pv, node=node_id, run_dir=run_dir, arm=arm,
                problem=problem, option_space=approved,
                canonical_claim_refs=canonical_claim_refs,
            ),
        )
        outputs[node_id] = transformation_refs
        self._report_node(run_dir, node_id)
        proposals = self._types(transformation_refs, "transformation_proposal")

        assessment_refs: list[ArtifactRef] = []
        for lens in self.base_lenses:
            node_id = f"assess_{lens['id']}"
            node = plan.node(node_id)
            inputs = plan.resolve_inputs(node_id, outputs)
            exact_lens = {
                "id": lens["id"],
                **self.repository.get_by_hash(
                    inputs["lens"][0].content_hash
                )["content"],
            }
            refs = executor.run(
                node.node_spec(),
                inputs=inputs,
                relevant_config=common_config,
                provider=node.provider,
                model=node.model,
                generation_parameters=dict(node.generation_parameters),
                prompt_hash=self._contract_hash("apply_lens_v1"),
                builder=lambda pv, lens=exact_lens, node_id=node_id, inputs=inputs: self._assessment_records(
                    lens, inputs["proposals"], inputs["evidence"], pv,
                    node=node_id, run_dir=run_dir, arm=arm,
                ),
            )
            outputs[node_id] = refs
            assessment_refs.extend(refs)
            self._report_node(run_dir, node_id)

        downstream = self._run_planned_downstream(
            plan=plan,
            outputs=outputs,
            executor=executor,
            run_dir=run_dir,
            arm=arm,
            common_config=common_config,
        )
        package_ref = downstream["package"][0]
        evaluation_ref = downstream["evaluation"][0]
        readiness_ref = downstream["readiness"][0]
        plan.assert_complete(outputs)
        self.repository.validate_graph((
            package_ref.id, evaluation_ref.id, readiness_ref.id,
        ))
        summary = self._summarize_arm(
            arm, run_dir, package_ref, evaluation_ref, proposals,
            assessment_refs, downstream,
        )
        summary["run_plan_hash"] = plan.hash
        write_json(self._arm_summary(arm), summary)
        print(
            f"ARM {arm}: total={summary['evaluation']['total']:.3f}, "
            f"cache_hits={summary['execution']['cache_hits']}, "
            f"executed={summary['execution']['executed']}",
            flush=True,
        )
        return summary, plan.hash

    def rebuild_reports(self) -> dict[str, Any]:
        """Recompute manifest-derived summaries and the A/B comparison without model calls."""

        for arm in ("baseline", "psychology"):
            path = self._arm_summary(arm)
            summary = self._load(path)
            run_dir = self.output_root / "runs" / summary["run_id"]
            summary["counts"] = self._manifest_counts(run_dir)
            write_json(path, summary)
        comparison = self.compare_arms()
        self._write_cost_report()
        return comparison

    def run_arm(self, arm: str, *, include_psychology: bool) -> dict[str, Any]:
        print(f"\n=== V2 LIVE ARM: {arm.upper()} ===", flush=True)
        run_id = f"live-{self.topic}-{arm}"
        run_dir = self.output_root / "runs" / run_id
        executor = NodeExecutor(
            repository=self.repository,
            run_dir=run_dir,
            source_root=self.root,
            run_id=run_id,
            artifact_created_at=self.created_at,
            topic=self.topic,
        )
        common_config = {"topic": self.topic, "problem_hash": content_hash(self.topic_data["problem_brief"])}

        research_by_lens: dict[str, tuple[ArtifactRef, ...]] = {}
        for lens in self.base_lenses:
            lens_id = lens["id"]
            name = f"research_{lens_id}"
            refs = executor.run(
                self._spec(
                    name, (), ("source", "assumption", "uncertainty", "finding"),
                    ("source.schema.json", "assumption.schema.json", "uncertainty.schema.json", "finding.schema.json"),
                    role="research",
                    spec_files=("config/v2/lenses.json",),
                ),
                inputs={}, relevant_config={**common_config, "lens": lens_id},
                provider=self.provider_generator, model="anthropic-task-ladder",
                generation_parameters={"search_max_tokens": 10000, "analysis_max_tokens": 16000},
                prompt_hash=self._contract_hash("research_v1"),
                builder=lambda pv, lens=lens, node=name, run_dir=run_dir: self._research_records(
                    lens, pv, node=node, run_dir=run_dir, arm=arm
                ),
            )
            research_by_lens[lens_id] = refs
            self._report_node(run_dir, name)
        evidence_refs = tuple(ref for refs in research_by_lens.values() for ref in refs)
        finding_refs = self._types(evidence_refs, "finding")

        lens_refs = executor.run(
            self._spec(
                "register_baseline_lenses", ("finding",), ("lens_definition",),
                ("lens_definition.schema.json",),
                spec_files=("config/v2/lenses.json",),
            ),
            inputs={"findings": finding_refs}, relevant_config=common_config,
            provider="local", model="deterministic-1.0.0",
            prompt_hash=self._contract_hash("baseline_lens_registry_v1"),
            builder=lambda pv: self._baseline_lens_records(pv),
        )
        self._report_node(run_dir, "register_baseline_lenses")

        transformation_refs = executor.run(
            self._spec(
                "derive_transformations", ("finding", "assumption", "uncertainty"),
                ("assumption", "uncertainty", "transformation_proposal", "transformation_family", "coverage_ledger"),
                ("assumption.schema.json", "uncertainty.schema.json", "transformation_proposal.schema.json", "transformation_family.schema.json", "coverage_ledger.schema.json"),
                role="generator",
            ),
            inputs={"evidence": self._types(evidence_refs, "finding", "assumption", "uncertainty")},
            relevant_config=common_config,
            provider=self.provider_generator, model="claude-sonnet-5",
            generation_parameters={"max_tokens": 30000},
            prompt_hash=self._contract_hash("derive_transformations_v1"),
            builder=lambda pv: self._transformation_records(
                finding_refs, pv, node="derive_transformations", run_dir=run_dir, arm=arm
            ),
        )
        self._report_node(run_dir, "derive_transformations")
        proposals = self._types(transformation_refs, "transformation_proposal")

        assessment_refs: list[ArtifactRef] = []
        for lens, lens_ref in zip(self.base_lenses, sorted(lens_refs, key=lambda ref: ref.id)):
            lens_id = lens["id"]
            # Sorting by id is not guaranteed to match config order; resolve explicitly.
            lens_ref = next(ref for ref in lens_refs if ref.id == f"L-live-{lens_id}")
            domain_findings = self._types(research_by_lens[lens_id], "finding")
            name = f"assess_{lens_id}"
            refs = executor.run(
                self._spec(
                    name, ("lens_definition", "transformation_proposal", "finding"),
                    ("lens_assessment",), ("lens_assessment.schema.json",),
                    role="generator", spec_files=("config/v2/lenses.json",),
                ),
                inputs={"lens": (lens_ref,), "proposals": proposals, "evidence": domain_findings},
                relevant_config=common_config,
                provider=self.provider_generator, model="claude-sonnet-5",
                generation_parameters={"max_tokens": 16000},
                prompt_hash=self._contract_hash("apply_lens_v1"),
                builder=lambda pv, lens=lens, findings=domain_findings, node=name: self._assessment_records(
                    lens, proposals, findings, pv, node=node, run_dir=run_dir, arm=arm
                ),
            )
            assessment_refs.extend(refs)
            self._report_node(run_dir, name)

        all_finding_refs = list(finding_refs)
        all_source_refs = list(self._types(evidence_refs, "source"))
        all_lens_refs = list(lens_refs)
        if include_psychology:
            psych_refs = executor.run(
                self._spec(
                    "register_educational_psychology_lens", (),
                    ("source", "finding", "lens_definition"),
                    ("source.schema.json", "finding.schema.json", "lens_definition.schema.json"),
                    spec_files=("config/v2/educational_psychology_lens.json",),
                ),
                inputs={}, relevant_config={**common_config, "treatment": "pr29_psychology_lens"},
                provider="local", model="deterministic-1.0.0",
                prompt_hash=self._contract_hash("psychology_lens_pr29"),
                builder=lambda pv: self._psychology_lens_records(pv),
            )
            self._report_node(run_dir, "register_educational_psychology_lens")
            psych_lens_ref = self._types(psych_refs, "lens_definition")[0]
            psych_findings = self._types(psych_refs, "finding")
            psych_assessments = executor.run(
                self._spec(
                    "assess_educational_psychology",
                    ("lens_definition", "transformation_proposal", "finding"),
                    ("lens_assessment",), ("lens_assessment.schema.json",),
                    role="generator",
                    spec_files=("config/v2/educational_psychology_lens.json",),
                ),
                inputs={"lens": (psych_lens_ref,), "proposals": proposals, "evidence": psych_findings},
                relevant_config={**common_config, "treatment": "pr29_psychology_lens"},
                provider=self.provider_generator, model="claude-sonnet-5",
                generation_parameters={"max_tokens": 16000},
                prompt_hash=self._contract_hash("apply_lens_v1"),
                builder=lambda pv: self._assessment_records(
                    self.psychology["lens"], proposals, psych_findings, pv,
                    node="assess_educational_psychology", run_dir=run_dir, arm=arm,
                    evidence_notes=self.psychology["evidence_notes"],
                ),
            )
            self._report_node(run_dir, "assess_educational_psychology")
            assessment_refs.extend(psych_assessments)
            all_finding_refs.extend(psych_findings)
            all_source_refs.extend(self._types(psych_refs, "source"))
            all_lens_refs.append(psych_lens_ref)

        downstream = self._run_downstream(
            executor=executor, run_dir=run_dir, arm=arm,
            proposals=proposals, transformation_refs=transformation_refs,
            lens_refs=tuple(all_lens_refs), assessment_refs=tuple(assessment_refs),
            finding_refs=tuple(all_finding_refs),
            source_refs=tuple(all_source_refs),
            uncertainty_refs=self._types((*evidence_refs, *transformation_refs), "uncertainty"),
            common_config=common_config,
        )
        package_ref = downstream["package"][0]
        evaluation_ref = downstream["evaluation"][0]
        readiness_ref = downstream["readiness"][0]
        self.repository.validate_graph((package_ref.id, evaluation_ref.id, readiness_ref.id))
        summary = self._summarize_arm(arm, run_dir, package_ref, evaluation_ref, proposals, assessment_refs, downstream)
        write_json(self._arm_summary(arm), summary)
        print(f"ARM {arm}: total={summary['evaluation']['total']:.3f}, cache_hits={summary['execution']['cache_hits']}, executed={summary['execution']['executed']}", flush=True)
        return summary

    def _run_downstream(
        self, *, executor: NodeExecutor, run_dir: Path, arm: str,
        proposals: tuple[ArtifactRef, ...], transformation_refs: tuple[ArtifactRef, ...],
        lens_refs: tuple[ArtifactRef, ...], assessment_refs: tuple[ArtifactRef, ...],
        finding_refs: tuple[ArtifactRef, ...], uncertainty_refs: tuple[ArtifactRef, ...],
        source_refs: tuple[ArtifactRef, ...],
        common_config: dict[str, Any],
    ) -> dict[str, tuple[ArtifactRef, ...]]:
        arm_config = {**common_config, "arm": arm, "lens_count": len(lens_refs)}
        dilemmas = executor.run(
            self._spec(
                "identify_decision_dilemmas",
                ("transformation_proposal", "lens_assessment", "finding"),
                ("dilemma",), ("dilemma.schema.json",), role="generator",
            ),
            inputs={"proposals": proposals, "assessments": assessment_refs, "findings": finding_refs},
            relevant_config=arm_config,
            provider=self.provider_generator, model="claude-sonnet-5",
            generation_parameters={"max_tokens": 16000},
            prompt_hash=self._contract_hash("identify_dilemmas_v1"),
            builder=lambda pv: self._dilemma_records(
                arm, proposals, assessment_refs, finding_refs, pv,
                node="identify_decision_dilemmas", run_dir=run_dir
            ),
        )
        self._report_node(run_dir, "identify_decision_dilemmas")
        agenda = executor.run(
            self._spec(
                "build_research_agenda",
                ("transformation_proposal", "lens_assessment", "uncertainty"),
                ("research_question",), ("research_question.schema.json",), role="generator",
            ),
            inputs={"proposals": proposals, "assessments": assessment_refs, "uncertainties": uncertainty_refs},
            relevant_config=arm_config,
            provider=self.provider_generator, model="claude-sonnet-5",
            generation_parameters={"max_tokens": 12000},
            prompt_hash=self._contract_hash("research_agenda_v1"),
            builder=lambda pv: self._agenda_records(
                arm, proposals, assessment_refs, uncertainty_refs, pv,
                node="build_research_agenda", run_dir=run_dir
            ),
        )
        self._report_node(run_dir, "build_research_agenda")
        package_inputs = (
            *self._types(transformation_refs, "transformation_family", "transformation_proposal", "coverage_ledger"),
            *lens_refs, *assessment_refs, *dilemmas, *agenda,
            *finding_refs, *source_refs,
        )
        package = executor.run(
            self._spec(
                "assemble_decision_package",
                ("transformation_family", "transformation_proposal", "coverage_ledger", "lens_definition", "lens_assessment", "dilemma", "research_question", "finding", "source"),
                ("decision_package",), ("decision_package.schema.json",), role="generator",
            ),
            inputs={"parts": package_inputs}, relevant_config=arm_config,
            provider=self.provider_generator, model="claude-sonnet-5",
            generation_parameters={"max_tokens": 20000},
            prompt_hash=self._contract_hash("decision_package_v1"),
            builder=lambda pv: self._package_records(
                arm, package_inputs, pv, node="assemble_decision_package", run_dir=run_dir
            ),
        )
        self._report_node(run_dir, "assemble_decision_package")
        evaluation = executor.run(
            self._spec(
                "evaluate_decision_package", ("decision_package", "transformation_proposal", "lens_assessment", "dilemma", "research_question"),
                ("evaluation",), ("evaluation.schema.json",), role="judge",
            ),
            inputs={"package": package, "proposals": proposals, "assessments": assessment_refs, "dilemmas": dilemmas, "agenda": agenda},
            relevant_config=arm_config,
            provider=self.provider_judge, model="gpt-5-mini",
            generation_parameters={"max_tokens": 8000},
            prompt_hash=self._contract_hash("evaluate_package_v1"),
            builder=lambda pv: self._evaluation_records(
                arm, package[0], proposals, assessment_refs, dilemmas, agenda, pv,
                node="evaluate_decision_package", run_dir=run_dir
            ),
        )
        self._report_node(run_dir, "evaluate_decision_package")
        readiness = executor.run(
            self._spec(
                "assess_decision_readiness",
                ("decision_package", "evaluation", "transformation_proposal", "dilemma", "research_question"),
                ("decision_readiness",), ("decision_readiness.schema.json",),
            ),
            inputs={
                "package": package, "evaluation": evaluation,
                "proposals": proposals, "dilemmas": dilemmas, "agenda": agenda,
            },
            relevant_config=arm_config,
            provider="local", model="deterministic-1.0.0",
            prompt_hash=self._contract_hash("decision_readiness_v1"),
            builder=lambda pv: self._readiness_records(
                arm, package[0], evaluation[0], proposals, dilemmas, agenda, pv
            ),
        )
        self._report_node(run_dir, "assess_decision_readiness")
        return {
            "dilemmas": dilemmas, "agenda": agenda, "package": package,
            "evaluation": evaluation, "readiness": readiness,
        }

    def _admit_run_roots(self) -> dict[str, tuple[ArtifactRef, ...]]:
        """Materialize the exact, externally admitted inputs compiled into a run."""

        roots: dict[str, tuple[ArtifactRef, ...]] = {}
        if "raw_question" in self.topic_data and "problem_brief" not in self.topic_data:
            raw = self.topic_data["raw_question"]
            question_content = {
                "question": raw["question"],
                "submission_context": raw["submission_context"],
                "source_refs": list(raw.get("source_refs", [])),
                "language": raw["language"],
                "approval_basis": raw["approval_basis"],
            }
            if raw.get("research_directions"):
                directions = raw["research_directions"]
                question_content["research_directions"] = {
                    "status": directions["status"],
                    "hypotheses_to_test": directions["hypotheses_to_test"],
                    "inquiry_priorities": directions["inquiry_priorities"],
                    "candidate_response_domains": list(
                        directions["candidate_response_domains"]
                    ),
                    "source_ref": directions["source_ref"],
                }
            source_files = (
                f"topics/{self.topic}/topic.json",
                *tuple(raw.get("context_files", [])),
            )
            provenance = self._admission_provenance(
                "admit_policy_question",
                source_files=source_files,
                admitted_content=question_content,
            )
            question_ref = self.repository.put_successor({
                **self._record(
                    f"QI-{self.topic}", "policy_question", provenance.id,
                    question_content,
                ),
                "status": "admitted",
            })
            roots["policy_question"] = (question_ref,)
        else:
            problem = self.topic_data["problem_brief"]
            problem_content = {
                "title": problem["title"],
                "public_question": problem["public_question"],
                "problem_statement": problem["problem_statement"],
                "learning_goals": problem["learning_goals"],
                "scope": problem["scope"],
                "seed_sources": [self._english(value) for value in problem.get("seed_sources", [])],
                "approval_basis": localized(
                    f"Human-approved topic brief admitted from topics/{self.topic}/topic.json as an immutable run root.",
                    f"Az ember által jóváhagyott témaleírás a topics/{self.topic}/topic.json fájlból változtathatatlan futási gyökérként befogadva.",
                ),
            }
            problem_provenance = self._admission_provenance(
                "admit_problem_brief",
                source_files=(f"topics/{self.topic}/topic.json",),
                admitted_content=problem_content,
            )
            problem_ref = self.repository.put_successor({
                **self._record(
                    f"PB-{self.topic}", "problem_brief", problem_provenance.id,
                    problem_content,
                ),
                "status": "admitted",
            })
            roots["problem_brief"] = (problem_ref,)
        for lens in self.base_lenses:
            lens_id = lens["id"]
            lens_content = {
                "name": lens["name"],
                "discipline": lens["discipline"],
                "questions": lens["questions"],
                "criteria": lens["criteria"],
                "limitations": lens["limitations"],
            }
            provenance = self._admission_provenance(
                f"admit_lens_{lens_id}",
                source_files=("config/v2/lenses.json",),
                admitted_content=lens_content,
            )
            lens_ref = self.repository.put_successor({
                **self._record(
                    f"L-live-{lens_id}", "lens_definition", provenance.id,
                    lens_content,
                ),
                "status": "admitted",
            })
            roots[f"lens_{lens_id}"] = (lens_ref,)
        return roots

    def _problem_brief_proposal_records(
        self,
        question_ref: ArtifactRef,
        provenance: str,
        *,
        node: str,
        run_dir: Path,
        arm: str,
    ) -> list[dict[str, Any]]:
        question = self.repository.get_by_hash(question_ref.content_hash)["content"]
        directions = question.get("research_directions")
        directions_text = (
            json.dumps(directions, ensure_ascii=False, indent=2)
            if directions else "none"
        )
        prompt = self._header("draft_problem_brief", "problem_framing_editor") + f"""
Turn the admitted raw policy question below into a bounded bilingual problem-brief proposal for human review. Do not research or answer the question yet.

RAW QUESTION: {self._english(question['question'])}
SUBMISSION CONTEXT: {self._english(question['submission_context'])}
SOURCE POINTERS: {'; '.join(question['source_refs']) or 'none'}
HUMAN RESEARCH DIRECTIONS: {directions_text}

Rules:
- Treat every empirical premise in the raw question as something research must verify, not as an established fact.
- Preserve the submitter's real concern while distinguishing prevalence, measurement, definitions, access, incentives, implementation, and value choices where relevant.
- Define a decision-useful scope and state exclusions inside the scope text.
- Write 3-7 learning goals that the later research and option-space nodes can answer.
- Do not propose interventions, scenarios, preferred outcomes, or expert seats.
- Seed sources are pointers only; never infer their contents.
- Treat human hypotheses as questions to test and response domains as areas to
  examine; do not convert either into facts or approved solutions.
- Preserve relationships explicitly requested in the human research directions,
  but do not import relationships, premises, or response domains from any other
  topic.
- Framing notes must make the important interpretation choices visible to the human reviewer.
"""
        result = self._call_structured_counted(
            prompt,
            contracts.PROBLEM_BRIEF_OUTPUT,
            role="generator",
            max_tokens=6000,
            arm=arm,
            node=node,
            run_dir=run_dir,
            suffix="draft",
            constraints={"learning_goals": (3, 7), "framing_notes": (1, 7)},
        )
        return [self._record(
            f"PBP-live-{self.topic}",
            "problem_brief_proposal",
            provenance,
            {"question_ref": question_ref.id, **result},
        )]

    def _require_problem_brief_decision(
        self,
        executor: NodeExecutor,
        run_dir: Path,
        candidate_ref: ArtifactRef,
        run_plan_hash: str,
    ) -> dict[str, Any]:
        gate_dir = run_dir / "gates" / "approve_problem_brief"
        gate_dir.mkdir(parents=True, exist_ok=True)
        request_path = gate_dir / f"{candidate_ref.content_hash}.request.json"
        decision_path = gate_dir / f"{candidate_ref.content_hash}.decision.json"
        candidate = self.repository.get_by_hash(candidate_ref.content_hash)
        request = {
            "candidate": candidate["content"],
            "candidate_hash": candidate_ref.content_hash,
            "candidate_ref": candidate_ref.id,
            "created_at": self.created_at,
            "gate_id": "approve_problem_brief",
            "run_plan_hash": run_plan_hash,
        }
        if request_path.exists() and self._load(request_path) != request:
            raise ValueError(f"Problem-brief gate request changed at {request_path}")
        if not request_path.exists():
            write_json(request_path, request)
        if not decision_path.exists():
            executor.events.append(
                "human_gate_waiting", run_id=executor.run_id,
                node_id="approve_problem_brief",
                candidate_hash=candidate_ref.content_hash,
                request_path=str(request_path),
            )
            raise HumanGatePending(
                "approve_problem_brief", candidate_ref.content_hash, request_path
            )
        decision = self._load(decision_path)
        required = {
            "gate_id", "candidate_ref", "candidate_hash", "decision",
            "decided_by", "decided_at", "rationale",
        }
        if set(decision) != required:
            raise ValueError(f"Problem-brief decision fields differ at {decision_path}")
        if decision["gate_id"] != "approve_problem_brief" or (
            decision["candidate_ref"] != candidate_ref.id
        ) or decision["candidate_hash"] != candidate_ref.content_hash:
            raise ValueError(
                f"Problem-brief decision does not match exact candidate "
                f"{candidate_ref.id} @ {candidate_ref.content_hash}"
            )
        if decision["decision"] != "approved":
            raise HumanGatePending(
                "approve_problem_brief", candidate_ref.content_hash, request_path
            )
        for key in ("decided_by", "decided_at"):
            if not isinstance(decision[key], str) or not decision[key].strip():
                raise ValueError(f"Problem-brief decision has empty {key}")
        if not is_localized_text(decision["rationale"]):
            raise ValueError("Problem-brief decision rationale must be an exact {en, hu} pair")
        return decision

    def _approved_problem_brief_records(
        self,
        candidate_ref: ArtifactRef,
        decision: dict[str, Any],
        provenance: str,
    ) -> list[dict[str, Any]]:
        candidate = self.repository.get_by_hash(candidate_ref.content_hash)
        content = candidate["content"]
        decision_id = f"HGB-live-{self.topic}-{candidate_ref.content_hash[:16]}"
        decision_record = {
            **self._record(
                decision_id, "problem_brief_decision", provenance, dict(decision)
            ),
            "status": "admitted",
        }
        brief_record = {
            **self._record(
                f"PB-{self.topic}", "problem_brief", provenance,
                {
                    "candidate_ref": candidate_ref.id,
                    "candidate_hash": candidate_ref.content_hash,
                    "decision_ref": decision_id,
                    "title": content["title"],
                    "public_question": content["public_question"],
                    "problem_statement": content["problem_statement"],
                    "learning_goals": content["learning_goals"],
                    "scope": content["scope"],
                    "seed_sources": content["seed_sources"],
                    "approval_basis": decision["rationale"],
                },
            ),
            "status": "admitted",
        }
        return [decision_record, brief_record]

    def _admission_provenance(
        self,
        node_id: str,
        *,
        source_files: tuple[str, ...],
        admitted_content: dict[str, Any],
    ) -> ArtifactRef:
        source_hashes = {
            name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()
            for name in source_files
        }
        execution_id = content_hash({
            "node_id": node_id,
            "source_hashes": source_hashes,
            "admitted_content": admitted_content,
        })
        return self.repository.put({
            "id": f"PV-{node_id}-{execution_id[:16]}",
            "record_type": "provenance",
            "schema_version": "2.0.0",
            "topic": self.topic,
            "status": "candidate",
            "content": {
                "node_id": node_id,
                "execution_id": execution_id,
                "input_artifact_hashes": [],
                "spec_hashes": source_hashes,
                "schema_hashes": {},
                "prompt_hash": "0" * 64,
                "provider": "local",
                "model": "deterministic-1.0.0",
                "role": "deterministic",
                "generation_parameters": {},
                "relevant_config_hash": content_hash({"topic": self.topic}),
            },
            "provenance_ref": None,
            "created_at": self.created_at,
            "supersedes": None,
        })

    def _require_gate_decision(
        self,
        executor: NodeExecutor,
        run_dir: Path,
        candidate_ref: ArtifactRef,
        run_plan_hash: str,
    ) -> dict[str, Any]:
        """Load a decision bound to one exact candidate or stop at the gate."""

        gate_dir = run_dir / "gates" / "approve_option_space"
        gate_dir.mkdir(parents=True, exist_ok=True)
        stem = candidate_ref.content_hash
        request_path = gate_dir / f"{stem}.request.json"
        decision_path = gate_dir / f"{stem}.decision.json"
        candidate = self.repository.get_by_hash(candidate_ref.content_hash)
        request = {
            "candidate_hash": candidate_ref.content_hash,
            "candidate_ref": candidate_ref.id,
            "created_at": self.created_at,
            "directions": candidate["content"]["directions"],
            "gate_id": "approve_option_space",
            "rejected_framings": candidate["content"]["rejected_framings"],
            "run_plan_hash": run_plan_hash,
        }
        if request_path.exists() and self._load(request_path) != request:
            raise ValueError(f"Human-gate request changed at {request_path}")
        if not request_path.exists():
            write_json(request_path, request)
        if not decision_path.exists():
            executor.events.append(
                "human_gate_waiting",
                run_id=executor.run_id,
                node_id="approve_option_space",
                candidate_hash=candidate_ref.content_hash,
                request_path=str(request_path),
            )
            raise HumanGatePending(
                "approve_option_space", candidate_ref.content_hash, request_path
            )
        decision = self._load(decision_path)
        required = {
            "gate_id", "candidate_ref", "candidate_hash", "decision",
            "decided_by", "decided_at", "rationale",
        }
        if set(decision) != required:
            raise ValueError(
                f"Gate decision fields differ at {decision_path}: "
                f"expected {sorted(required)}, got {sorted(decision)}"
            )
        if decision["gate_id"] != "approve_option_space":
            raise ValueError(f"Wrong gate id in {decision_path}")
        if decision["candidate_ref"] != candidate_ref.id or (
            decision["candidate_hash"] != candidate_ref.content_hash
        ):
            raise ValueError(
                f"Gate decision does not match exact candidate {candidate_ref.id} "
                f"@ {candidate_ref.content_hash}"
            )
        if decision["decision"] != "approved":
            raise HumanGatePending(
                "approve_option_space", candidate_ref.content_hash, request_path
            )
        for key in ("decided_by", "decided_at"):
            if not isinstance(decision[key], str) or not decision[key].strip():
                raise ValueError(f"Gate decision has empty {key} at {decision_path}")
        if not is_localized_text(decision["rationale"]):
            raise ValueError(
                f"Gate decision rationale must be an exact {{en, hu}} pair at {decision_path}"
            )
        return decision

    def _approved_option_space_records(
        self,
        candidate_ref: ArtifactRef,
        decision: dict[str, Any],
        provenance: str,
    ) -> list[dict[str, Any]]:
        candidate = self.repository.get_by_hash(candidate_ref.content_hash)
        decision_id = f"HG-live-option-space-{candidate_ref.content_hash[:16]}"
        approved_id = f"AO-live-{self.topic}"
        decision_record = {
            **self._record(
                decision_id,
                "human_gate_decision",
                provenance,
                dict(decision),
            ),
            "status": "admitted",
        }
        approved_record = {
            **self._record(
                approved_id,
                "approved_option_space",
                provenance,
                {
                    "candidate_ref": candidate_ref.id,
                    "candidate_hash": candidate_ref.content_hash,
                    "decision_ref": decision_id,
                    "directions": candidate["content"]["directions"],
                    "rejected_framings": candidate["content"]["rejected_framings"],
                },
            ),
            "status": "admitted",
        }
        return [decision_record, approved_record]

    def _run_planned_downstream(
        self,
        *,
        plan: Any,
        outputs: dict[str, tuple[ArtifactRef, ...]],
        executor: NodeExecutor,
        run_dir: Path,
        arm: str,
        common_config: dict[str, Any],
    ) -> dict[str, tuple[ArtifactRef, ...]]:
        """Execute the remaining graph by resolving every input from RunPlan."""

        arm_config = {**common_config, "arm": arm, "lens_count": len(self.base_lenses)}

        node_id = "identify_decision_dilemmas"
        node = plan.node(node_id)
        inputs = plan.resolve_inputs(node_id, outputs)
        dilemmas = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=arm_config,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("identify_dilemmas_v1"),
            builder=lambda pv: self._dilemma_records(
                arm, inputs["proposals"], inputs["assessments"], inputs["findings"], pv,
                node=node_id, run_dir=run_dir,
            ),
        )
        outputs[node_id] = dilemmas
        self._report_node(run_dir, node_id)

        node_id = "build_research_agenda"
        node = plan.node(node_id)
        inputs = plan.resolve_inputs(node_id, outputs)
        agenda = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=arm_config,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("research_agenda_v1"),
            builder=lambda pv: self._agenda_records(
                arm, inputs["proposals"], inputs["assessments"],
                inputs["uncertainties"], pv, node=node_id, run_dir=run_dir,
            ),
        )
        outputs[node_id] = agenda
        self._report_node(run_dir, node_id)

        node_id = "assemble_decision_package"
        node = plan.node(node_id)
        inputs = plan.resolve_inputs(node_id, outputs)
        package_inputs = tuple(
            ref for refs in inputs.values() for ref in refs
        )
        package = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=arm_config,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("decision_package_v1"),
            builder=lambda pv: self._package_records(
                arm, package_inputs, pv, node=node_id, run_dir=run_dir,
                problem=self.repository.get_by_hash(
                    inputs["problem"][0].content_hash
                )["content"],
            ),
        )
        outputs[node_id] = package
        self._report_node(run_dir, node_id)

        node_id = "evaluate_decision_package"
        node = plan.node(node_id)
        inputs = plan.resolve_inputs(node_id, outputs)
        evaluation = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=arm_config,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("evaluate_package_v1"),
            builder=lambda pv: self._evaluation_records(
                arm, inputs["package"][0], inputs["proposals"],
                inputs["assessments"], inputs["dilemmas"], inputs["agenda"], pv,
                node=node_id, run_dir=run_dir,
            ),
        )
        outputs[node_id] = evaluation
        self._report_node(run_dir, node_id)

        node_id = "assess_decision_readiness"
        node = plan.node(node_id)
        inputs = plan.resolve_inputs(node_id, outputs)
        readiness = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=arm_config,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("decision_readiness_v1"),
            builder=lambda pv: self._readiness_records(
                arm, inputs["package"][0], inputs["evaluation"][0],
                inputs["proposals"], inputs["dilemmas"], inputs["agenda"], pv,
            ),
        )
        outputs[node_id] = readiness
        self._report_node(run_dir, node_id)
        return {
            "dilemmas": dilemmas,
            "agenda": agenda,
            "package": package,
            "evaluation": evaluation,
            "readiness": readiness,
        }

    def _research_records(
        self, lens: dict[str, Any], provenance: str, *, node: str,
        run_dir: Path, arm: str, problem: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        problem = problem or self.topic_data["problem_brief"]
        public_question = self._english(problem["public_question"])
        problem_statement = self._english(problem["problem_statement"])
        search_prompt = f"""TASK: expert_research\nAGENT: {lens['id']}\nLANG: en\n
This is a non-canonical web-search scratchpad. Its claims become artifacts
only after the next structured step authors and validates exact {{en, hu}}
pairs.

Research the following Hungarian education-policy problem from the disciplinary perspective of {self._english(lens['discipline'])}.

PUBLIC QUESTION: {public_question}
PROBLEM: {problem_statement}

QUESTIONS:
{self._bullets(lens['questions'])}

Use live web search. Return concise English research notes with direct source URLs, dates or scopes where material, contested evidence clearly marked, and no policy recommendation. Separate facts from inference. Cover seven to ten distinct decision-relevant findings; do not split one claim merely to hit the range.
"""
        notes = self._recover_or_call_search(
            search_prompt, arm=arm, node=node, run_dir=run_dir
        )
        analysis_prompt = self._header("expert_analysis", lens["id"]) + f"""
Convert the live research notes below into a bilingual evidence artifact set for this policy problem.

DISCIPLINE: {self._english(lens['discipline'])}
PUBLIC QUESTION: {public_question}
CRITERIA: {', '.join(self._english(value) for value in lens['criteria'])}
KNOWN LENS LIMITS: {'; '.join(self._english(value) for value in lens['limitations'])}

RESEARCH NOTES:
{notes}

Rules: preserve contested labels; never invent a source or statistic; findings must be empirical claims rather than recommendations; source_url must be a direct URL when present in the notes, otherwise a short source identifier. Produce 7-10 distinct findings, 1-4 assumptions, and 2-4 uncertainties with concrete reduction paths.
"""
        result = self._call_structured_counted(
            analysis_prompt, contracts.RESEARCH_OUTPUT, role="generator", max_tokens=16000,
            arm=arm, node=node, run_dir=run_dir, suffix="analysis",
            constraints={"findings": (7, 10), "assumptions": (1, 4), "uncertainties": (2, 4)},
        )
        records: list[dict[str, Any]] = []
        assumption_ids = []
        for index, statement in enumerate(result["assumptions"], 1):
            artifact_id = f"A-live-{lens['id']}-{index:02d}"
            assumption_ids.append(artifact_id)
            records.append(self._record(artifact_id, "assumption", provenance, {
                "statement": statement, "domain_tags": [lens["id"]],
                "testability": "partly_testable", "source_context": localized(
                    "Fresh live v2 domain research", "Friss, élő v2 szakterületi kutatás"
                ),
            }))
        uncertainty_ids = []
        for index, item in enumerate(result["uncertainties"], 1):
            artifact_id = f"U-live-{lens['id']}-{index:02d}"
            uncertainty_ids.append(artifact_id)
            records.append(self._record(artifact_id, "uncertainty", provenance, {
                "question": item["question"], "uncertainty_type": "unknown",
                "current_confidence": "low", "reduction_path": item["reduction_path"],
            }))
        for index, item in enumerate(result["findings"], 1):
            source_id = f"SRC-live-{lens['id']}-{index:02d}"
            records.append(self._record(source_id, "source", provenance, {
                "title": item["source_title"], "url": self._safe_uri(item["source_url"], source_id),
                "source_type": "web_page", "license_status": "public_pointer_only",
                "accessed_at": self.created_at,
            }))
            records.append(self._record(f"F-live-{lens['id']}-{index:02d}", "finding", provenance, {
                "claim": item["claim"], "kind": "fact", "domain_tags": [lens["id"]],
                "evidence_strength": item["evidence_strength"], "source_refs": [source_id],
                "population": localized(
                    "Population described in the cited finding",
                    "A hivatkozott megállapításban leírt populáció",
                ),
                "context": localized(
                    f"Fresh live research through the {self._english(lens['name'])} lens",
                    f"Friss, élő kutatás a(z) {text(lens['name'], 'hu')} nézőpontján keresztül",
                ),
                "time_scope": localized(
                    "As reported by the cited source", "A hivatkozott forrás közlése szerint"
                ),
                "transferability": "uncertain", "limitations": item["limitations"],
                "assumption_ids": assumption_ids, "uncertainty_ids": uncertainty_ids,
            }))
        return records

    def _baseline_lens_records(self, provenance: str) -> list[dict[str, Any]]:
        return [self._record(f"L-live-{lens['id']}", "lens_definition", provenance, {
            "name": lens["name"], "discipline": lens["discipline"],
            "questions": lens["questions"], "criteria": lens["criteria"],
            "limitations": lens["limitations"],
        }) for lens in self.base_lenses]

    def _psychology_lens_records(self, provenance: str) -> list[dict[str, Any]]:
        lens = self.psychology["lens"]
        records: list[dict[str, Any]] = []
        for note in self.psychology["evidence_notes"]:
            source_id = f"SRC-live-psychology-{_slug(note['id'])}"
            records.append(self._record(source_id, "source", provenance, {
                "title": note["source"], "url": f"urn:epl:pr29:{_slug(note['id'])}",
                "source_type": "research_paper", "license_status": "public_pointer_only",
                "accessed_at": self.created_at,
            }))
            records.append(self._record(f"F-live-psychology-{_slug(note['id'])}", "finding", provenance, {
                "claim": note["claim"], "kind": "fact",
                "domain_tags": ["educational_psychology"],
                "evidence_strength": note["evidence_strength"], "source_refs": [source_id],
                "population": localized(
                    "Students in learning and educational-sorting contexts",
                    "Tanulási és oktatási szelekciós helyzetben lévő tanulók",
                ),
                "context": localized(
                    "PR #29 curated educational-psychology evidence base",
                    "A PR #29 válogatott oktatáspszichológiai bizonyítékbázisa",
                ),
                "time_scope": localized(
                    "Evidence base admitted to the PR #29 sensitivity test",
                    "A PR #29 érzékenységi vizsgálatába befogadott bizonyítékbázis",
                ),
                "transferability": "uncertain",
                "limitations": [localized(
                    "Use only within the stated population, domain, and evidence-strength boundary.",
                    "Csak a megadott populációs, szakterületi és bizonyítékerősségi határok között használható.",
                )],
                "assumption_ids": [], "uncertainty_ids": [],
            }))
        records.append(self._record("L-live-educational_psychology", "lens_definition", provenance, {
            "name": lens["name"], "discipline": lens["discipline"],
            "questions": lens["questions"], "criteria": lens["criteria"],
            "limitations": lens["limitations"],
        }))
        return records

    def _option_space_records(
        self,
        problem_ref: ArtifactRef,
        evidence_refs: tuple[ArtifactRef, ...],
        provenance: str,
        *,
        node: str,
        run_dir: Path,
        arm: str,
    ) -> list[dict[str, Any]]:
        """Derive an option-space candidate before any human approval."""

        problem = self.repository.get_by_hash(problem_ref.content_hash)["content"]
        findings = [
            self.repository.get_by_hash(ref.content_hash)
            for ref in evidence_refs if ref.record_type == "finding"
        ]
        digest = "\n".join(
            f"- {record['id']} [{record['content']['evidence_strength']}]: "
            f"{self._english(record['content']['claim'])}"
            for record in findings
        )
        prompt = self._header("derive_option_space", "option_space_architect") + f"""
Derive the real bilingual option space for the approved education-policy problem below. This is a pre-approval proposal, not a policy recommendation and not a transformation portfolio.

PUBLIC QUESTION: {self._english(problem['public_question'])}
PROBLEM: {self._english(problem['problem_statement'])}
SCOPE: {self._english(problem['scope'])}

FRESH EVIDENCE RECORD:
{digest}

Produce 2-7 materially distinct direction families with sequential ids S1..Sn. Each direction must cite at least one supplied finding id and state a bounded scope. Include a no-new-policy or passive-change baseline when decision-relevant. Do not import any previously approved frame, scenario title, or knowledge outside the supplied evidence. Record at least one considered-but-rejected framing with reasons and finding references. The directions must span rather than prematurely collapse the option space.
"""
        finding_ids = [record["id"] for record in findings]
        result = self._call_structured_counted(
            prompt,
            contracts.option_space_output(finding_ids),
            role="generator",
            max_tokens=12000,
            arm=arm,
            node=node,
            run_dir=run_dir,
            suffix="generate",
            constraints={"directions": (2, 7), "rejected_framings": (1, 7)},
            item_constraints={("directions", "finding_refs"): (1, 20)},
        )
        ids = [item["id"] for item in result["directions"]]
        expected = [f"S{index}" for index in range(1, len(ids) + 1)]
        if ids != expected:
            raise ValueError(
                f"Option-space direction ids must be sequential: expected {expected}, got {ids}"
            )
        return [self._record(
            f"OS-live-{self.topic}", "option_space_proposal", provenance,
            {
                "directions": result["directions"],
                "rejected_framings": result["rejected_framings"],
                "derivation_notice": localized(
                    "Derived only from the exact fresh finding artifacts declared by the run plan; pending an explicit human gate.",
                    "Kizárólag a futási tervben deklarált, pontos friss megállapítás-artefaktokból levezetve; explicit emberi kapudöntésre vár.",
                ),
            },
        )]

    def _normalize_evidence_records(
        self,
        problem_ref: ArtifactRef,
        evidence_refs: tuple[ArtifactRef, ...],
        provenance: str,
        *,
        node: str,
        run_dir: Path,
        arm: str,
    ) -> list[dict[str, Any]]:
        """Create bounded claims and conflicts with exact finding coverage."""

        problem = self.repository.get_by_hash(problem_ref.content_hash)["content"]
        by_type = {
            record_type: [
                self.repository.get_by_hash(ref.content_hash)
                for ref in evidence_refs if ref.record_type == record_type
            ]
            for record_type in ("finding", "assumption", "uncertainty")
        }
        finding_ids = [record["id"] for record in by_type["finding"]]
        if len(finding_ids) > 60:
            result = self._normalize_evidence_sharded(
                problem, by_type, node=node, run_dir=run_dir, arm=arm,
            )
        else:
            result = self._request_evidence_normalization(
                problem, by_type["finding"], by_type["assumption"],
                by_type["uncertainty"], node=node, run_dir=run_dir, arm=arm,
                suffix="generate",
            )
        claims = result["claims"]
        conflicts = result["conflicts"]
        normalization_actions = []
        reference_fields = (
            (claims, "claims", (
                "supporting_finding_refs", "contradicting_finding_refs",
                "assumption_refs", "uncertainty_refs",
            )),
            (conflicts, "conflicts", ("finding_refs", "claim_keys")),
            (result["coverage"], "coverage", (
                "claim_keys", "conflict_keys", "duplicate_of_refs",
            )),
        )
        for items, collection, fields in reference_fields:
            for index, item in enumerate(items, 1):
                for field in fields:
                    before = item[field]
                    after = list(dict.fromkeys(before))
                    if before == after:
                        continue
                    item[field] = after
                    normalization_actions.append({
                        "field": f"{collection}[{index}].{field}",
                        "action": "deduplicate_redundant_references",
                        "before_count": len(before), "after_count": len(after),
                    })
        claim_keys = [item["key"] for item in claims]
        conflict_keys = [item["key"] for item in conflicts]
        if claim_keys != [f"C{i}" for i in range(1, len(claims) + 1)]:
            raise ValueError(f"Canonical claim keys must be sequential: {claim_keys}")
        if conflict_keys != [f"E{i}" for i in range(1, len(conflicts) + 1)]:
            raise ValueError(f"Evidence conflict keys must be sequential: {conflict_keys}")
        coverage = {entry["finding_ref"]: entry for entry in result["coverage"]}
        if len(coverage) != len(result["coverage"]) or set(coverage) != set(finding_ids):
            raise ValueError(
                "Finding coverage must contain every input exactly once: "
                f"expected={sorted(finding_ids)}, got={sorted(coverage)}"
            )
        claimed_findings = {
            finding_id
            for claim in claims
            for finding_id in (
                claim["supporting_finding_refs"]
                + claim["contradicting_finding_refs"]
            )
        }
        finding_by_id = {
            record["id"]: record for record in by_type["finding"]
        }
        transferability_map = {
            "high": "direct", "medium": "conditional",
            "uncertain": "conditional", "low": "analogy_only",
            "not_applicable": "not_transferable",
        }
        for entry in result["coverage"]:
            finding_id = entry["finding_ref"]
            if entry["status"] != "carried_forward" or finding_id in claimed_findings:
                continue
            source_finding = finding_by_id[finding_id]["content"]
            fallback_key = f"C{len(claims) + 1}"
            claims.append({
                "key": fallback_key,
                "statement": source_finding["claim"],
                "claim_type": "descriptive",
                "population": source_finding["population"],
                "context": source_finding["context"],
                "time_scope": source_finding["time_scope"],
                "evidence_strength": source_finding["evidence_strength"],
                "transferability": transferability_map[
                    source_finding["transferability"]
                ],
                "supporting_finding_refs": [finding_id],
                "contradicting_finding_refs": [],
                "assumption_refs": source_finding["assumption_ids"],
                "uncertainty_refs": source_finding["uncertainty_ids"],
            })
            claimed_findings.add(finding_id)
            normalization_actions.append({
                "field": f"claims.{fallback_key}",
                "action": "synthesize_lossless_atomic_fallback_claim",
                "finding_ref": finding_id,
            })
        claim_keys = [item["key"] for item in claims]
        known_claims = set(claim_keys)
        known_conflicts = set(conflict_keys)
        derived_claim_keys = {finding_id: [] for finding_id in finding_ids}
        derived_conflict_keys = {finding_id: [] for finding_id in finding_ids}
        for claim in claims:
            for finding_id in dict.fromkeys(
                claim["supporting_finding_refs"] + claim["contradicting_finding_refs"]
            ):
                derived_claim_keys[finding_id].append(claim["key"])
        for conflict in conflicts:
            for finding_id in conflict["finding_refs"]:
                derived_conflict_keys[finding_id].append(conflict["key"])
        for entry in result["coverage"]:
            finding_id = entry["finding_ref"]
            expected_claims = derived_claim_keys[finding_id]
            expected_conflicts = derived_conflict_keys[finding_id]
            if (
                entry["claim_keys"] != expected_claims
                or entry["conflict_keys"] != expected_conflicts
            ):
                normalization_actions.append({
                    "field": f"coverage.{finding_id}",
                    "action": "derive_redundant_reverse_references",
                    "claim_keys_before": entry["claim_keys"],
                    "claim_keys_after": expected_claims,
                    "conflict_keys_before": entry["conflict_keys"],
                    "conflict_keys_after": expected_conflicts,
                })
                entry["claim_keys"] = expected_claims
                entry["conflict_keys"] = expected_conflicts
        if normalization_actions:
            self._record_semantic_normalizations(
                run_dir, arm=arm, node=node, attempt=1,
                actions=normalization_actions,
            )
        for entry in coverage.values():
            unknown_claims = set(entry["claim_keys"]) - known_claims
            unknown_conflicts = set(entry["conflict_keys"]) - known_conflicts
            if unknown_claims or unknown_conflicts:
                raise ValueError(
                    f"Coverage {entry['finding_ref']} cites unknown normalized outputs"
                )
            if entry["status"] == "carried_forward" and not entry["claim_keys"]:
                raise ValueError(f"{entry['finding_ref']} is carried forward without a claim")
            if entry["status"] == "conflict_recorded" and not entry["conflict_keys"]:
                raise ValueError(f"{entry['finding_ref']} records no conflict")
            if entry["status"] == "duplicate_of" and (
                len(entry["duplicate_of_refs"]) != 1
                or entry["duplicate_of_refs"][0] == entry["finding_ref"]
            ):
                raise ValueError(f"{entry['finding_ref']} has an invalid duplicate disposition")
            if entry["critical"] and entry["status"] in {"rejected", "out_of_scope", "needs_review"}:
                raise ValueError(f"Critical finding attrition at {entry['finding_ref']}")
        for claim in claims:
            for finding_id in set(claim["supporting_finding_refs"] + claim["contradicting_finding_refs"]):
                if claim["key"] not in coverage[finding_id]["claim_keys"]:
                    raise ValueError(f"Coverage omits {claim['key']} for {finding_id}")
        for conflict in conflicts:
            self._require_count(conflict["finding_refs"], 2, 20, f"{conflict['key']}.finding_refs")
            unknown = set(conflict["claim_keys"]) - known_claims
            if unknown:
                raise ValueError(f"{conflict['key']} cites unknown claims: {sorted(unknown)}")
            for finding_id in conflict["finding_refs"]:
                if conflict["key"] not in coverage[finding_id]["conflict_keys"]:
                    raise ValueError(f"Coverage omits {conflict['key']} for {finding_id}")

        claim_ids = {item["key"]: f"CC-live-{item['key'].lower()}" for item in claims}
        conflict_ids = {item["key"]: f"EC-live-{item['key'].lower()}" for item in conflicts}
        records: list[dict[str, Any]] = []
        for item in claims:
            records.append(self._record(claim_ids[item["key"]], "canonical_claim", provenance, {
                key: value for key, value in item.items() if key != "key"
            }))
        for item in conflicts:
            records.append(self._record(conflict_ids[item["key"]], "evidence_conflict", provenance, {
                **{key: value for key, value in item.items() if key not in {"key", "claim_keys"}},
                "canonical_claim_refs": [claim_ids[key] for key in item["claim_keys"]],
            }))
        records.append(self._record("CL-live-evidence-normalization", "coverage_ledger", provenance, {
            "gate_basis": "evidence_normalization",
            "entries": [
                {
                    "finding_ref": entry["finding_ref"],
                    "status": entry["status"],
                    "canonical_claim_refs": [claim_ids[key] for key in entry["claim_keys"]],
                    "evidence_conflict_refs": [conflict_ids[key] for key in entry["conflict_keys"]],
                    "duplicate_of_ref": entry["duplicate_of_refs"][0] if entry["duplicate_of_refs"] else None,
                    "critical": entry["critical"],
                    "rationale": entry["rationale"],
                }
                for entry in result["coverage"]
            ],
            "critical_attrition_count": 0,
            "verdict": "complete",
        }))
        return records

    def _request_evidence_normalization(
        self, problem: dict[str, Any], findings: list[dict[str, Any]],
        assumptions: list[dict[str, Any]], uncertainties: list[dict[str, Any]],
        *, node: str, run_dir: Path, arm: str, suffix: str,
    ) -> dict[str, Any]:
        """Normalize one bounded finding shard with exact local coverage."""

        digest = "\n".join(
            f"- {record['id']} [{record['content']['evidence_strength']}]: "
            f"{self._english(record['content']['claim'])} | "
            f"population={self._english(record['content']['population'])}; "
            f"context={self._english(record['content']['context'])}; "
            f"time={self._english(record['content']['time_scope'])}"
            for record in findings
        )
        prompt = self._header("normalize_evidence", "evidence_normalizer") + f"""
Normalize the complete atomic finding set for this approved problem. Merge only genuinely equivalent claims. Preserve population, context, time, method, causal status, transferability, and evidence strength. Record contradictions and apparent contradictions explicitly; do not average them away.

PUBLIC QUESTION: {self._english(problem['public_question'])}
PROBLEM: {self._english(problem['problem_statement'])}

FINDINGS:
{digest}

Produce sequential claim keys C1..Cn and conflict keys E1..En. A conflict must cite at least two findings. Return exactly one coverage entry for every supplied finding id and no others. Every claim or conflict reference must be mirrored in that finding's coverage entry. `carried_forward` requires a claim; `conflict_recorded` requires a conflict; `duplicate_of` requires exactly one different finding. A critical finding may not be rejected, placed out of scope, or left for review. No expert identity or authority is part of the normalized claim.
"""
        finding_ids = [record["id"] for record in findings]
        return self._call_structured_counted(
            prompt,
            contracts.evidence_normalization_output(
                finding_ids,
                [record["id"] for record in assumptions],
                [record["id"] for record in uncertainties],
            ),
            role="generator", max_tokens=24000, arm=arm, node=node,
            run_dir=run_dir, suffix=suffix,
            constraints={
                "claims": (1, 60), "conflicts": (0, 30),
                "coverage": (len(finding_ids), len(finding_ids)),
            },
        )

    def _normalize_evidence_sharded(
        self, problem: dict[str, Any], by_type: dict[str, list[dict[str, Any]]],
        *, node: str, run_dir: Path, arm: str,
    ) -> dict[str, Any]:
        """Normalize large snapshots in bounded shards plus global conflict pass.

        Shards prevent a complete coverage ledger from exceeding provider output
        limits. Claim identities are made global deterministically; a separate
        reconciliation call can only add conflicts whose claims span shards.
        The final caller still applies one exact all-finding coverage gate.
        """

        shard_size = 40
        findings = by_type["finding"]
        merged: dict[str, list[dict[str, Any]]] = {
            "claims": [], "conflicts": [], "coverage": [],
        }
        actions: list[dict[str, Any]] = []
        claim_shards: dict[str, int] = {}
        local_conflict_signatures: set[tuple[str, ...]] = set()
        for shard_index, start in enumerate(range(0, len(findings), shard_size), 1):
            result = self._request_evidence_normalization(
                problem, findings[start:start + shard_size],
                by_type["assumption"], by_type["uncertainty"],
                node=node, run_dir=run_dir, arm=arm,
                suffix=f"generate-shard-{shard_index:02d}",
            )
            claim_map: dict[str, str] = {}
            for claim in result["claims"]:
                global_key = f"C{len(merged['claims']) + 1}"
                claim_map[claim["key"]] = global_key
                claim["key"] = global_key
                claim_shards[global_key] = shard_index
                merged["claims"].append(claim)
            conflict_map: dict[str, str] = {}
            for conflict in result["conflicts"]:
                source_key = conflict["key"]
                conflict["finding_refs"] = list(dict.fromkeys(
                    conflict["finding_refs"]
                ))
                if len(conflict["finding_refs"]) < 2:
                    conflict_map[source_key] = ""
                    actions.append({
                        "field": f"shard_{shard_index}.{source_key}",
                        "action": "drop_single_finding_pseudo_conflict",
                        "finding_refs": conflict["finding_refs"],
                    })
                    continue
                global_key = f"E{len(merged['conflicts']) + 1}"
                conflict_map[source_key] = global_key
                conflict["key"] = global_key
                conflict["claim_keys"] = [
                    claim_map[key] for key in conflict["claim_keys"]
                ]
                local_conflict_signatures.add(tuple(sorted(conflict["finding_refs"])))
                merged["conflicts"].append(conflict)
            for entry in result["coverage"]:
                entry["claim_keys"] = [claim_map[key] for key in entry["claim_keys"]]
                entry["conflict_keys"] = [
                    conflict_map[key] for key in entry["conflict_keys"]
                    if conflict_map.get(key)
                ]
                if entry["status"] == "conflict_recorded" and not entry["conflict_keys"]:
                    actions.append({
                        "field": f"coverage.{entry['finding_ref']}",
                        "action": "retain_finding_after_pseudo_conflict_removal",
                        "status_before": "conflict_recorded",
                        "status_after": "carried_forward",
                    })
                    entry["status"] = "carried_forward"
                merged["coverage"].append(entry)

        claim_digest = "\n".join(
            f"- {claim['key']} [shard {claim_shards[claim['key']]}] "
            f"findings={','.join(claim['supporting_finding_refs'] + claim['contradicting_finding_refs'])}: "
            f"{self._english(claim['statement'])} | "
            f"population={self._english(claim['population'])}; "
            f"context={self._english(claim['context'])}; "
            f"time={self._english(claim['time_scope'])}"
            for claim in merged["claims"]
        )
        prompt = self._header(
            "normalize_evidence_cross_shard", "evidence_normalizer"
        ) + f"""
Reconcile bounded claims that were normalized in separate execution shards.

MERGE GROUPS: Group only genuinely equivalent claims that express the same bounded proposition for the same population, context, time and causal status. Every merge group must span at least two shard numbers. A claim may occur in at most one group. Do not merge merely related findings, mechanisms with outcomes, or findings whose scope differs.

CONFLICTS: Detect material evidence conflicts that were invisible inside the bounded shards. Every conflict must cite at least two supplied claims from at least two shard numbers and at least two of their exact finding ids. Do not repeat a within-shard conflict. Context, population, measurement, time, causal interpretation, and transferability differences are conflicts to preserve when decision-relevant; do not average them away.

Do not invent claims or findings. Return empty collections where no cross-shard merge or conflict is warranted.

PUBLIC QUESTION: {self._english(problem['public_question'])}
CANONICAL CLAIMS:
{claim_digest}
"""
        reconciliation = self._call_structured_counted(
            prompt,
            contracts.cross_shard_reconciliation_output(
                [record["id"] for record in findings],
                [claim["key"] for claim in merged["claims"]],
            ),
            role="generator", max_tokens=12000, arm=arm, node=node,
            run_dir=run_dir, suffix="reconcile-cross-shard",
            constraints={"merge_groups": (0, 30), "conflicts": (0, 20)},
        )
        claims_by_key = {claim["key"]: claim for claim in merged["claims"]}
        claimed_for_merge: set[str] = set()
        collapse_to: dict[str, str] = {}
        strength_rank = {
            "strong": 0, "moderate": 1, "weak": 2, "contested": 3,
        }
        transfer_rank = {
            "direct": 0, "conditional": 1,
            "analogy_only": 2, "not_transferable": 3,
        }
        for group in reconciliation["merge_groups"]:
            keys = list(dict.fromkeys(group["claim_keys"]))
            shards = {claim_shards[key] for key in keys}
            claim_types = {claims_by_key[key]["claim_type"] for key in keys}
            if (
                len(keys) < 2 or len(shards) < 2 or len(claim_types) != 1
                or claimed_for_merge.intersection(keys)
            ):
                actions.append({
                    "field": "cross_shard_merge_groups",
                    "action": "drop_invalid_or_overlapping_merge_group",
                    "claim_keys": keys,
                })
                continue
            representative = min(keys, key=lambda key: int(key[1:]))
            target = claims_by_key[representative]
            members = [claims_by_key[key] for key in keys]
            for field in (
                "supporting_finding_refs", "contradicting_finding_refs",
                "assumption_refs", "uncertainty_refs",
            ):
                target[field] = list(dict.fromkeys(
                    value for member in members for value in member[field]
                ))
            target["evidence_strength"] = max(
                (member["evidence_strength"] for member in members),
                key=strength_rank.__getitem__,
            )
            target["transferability"] = max(
                (member["transferability"] for member in members),
                key=transfer_rank.__getitem__,
            )
            for key in keys:
                collapse_to[key] = representative
            claimed_for_merge.update(keys)
            actions.append({
                "field": "cross_shard_merge_groups",
                "action": "merge_equivalent_cross_shard_claims",
                "representative": representative,
                "claim_keys": keys,
                "rationale": group["rationale"],
            })
        retained_claims = [
            claim for claim in merged["claims"]
            if collapse_to.get(claim["key"], claim["key"]) == claim["key"]
        ]
        renumber = {
            claim["key"]: f"C{index}"
            for index, claim in enumerate(retained_claims, 1)
        }
        final_claim_key = {
            key: renumber[collapse_to.get(key, key)]
            for key in claims_by_key
        }
        for claim in retained_claims:
            claim["key"] = renumber[claim["key"]]
        merged["claims"] = retained_claims
        for conflict in merged["conflicts"]:
            conflict["claim_keys"] = list(dict.fromkeys(
                final_claim_key[key] for key in conflict["claim_keys"]
            ))
        for entry in merged["coverage"]:
            entry["claim_keys"] = list(dict.fromkeys(
                final_claim_key[key] for key in entry["claim_keys"]
            ))

        for conflict in reconciliation["conflicts"]:
            signature = tuple(sorted(dict.fromkeys(conflict["finding_refs"])))
            shards = {claim_shards[key] for key in conflict["claim_keys"]}
            if len(shards) < 2 or signature in local_conflict_signatures:
                actions.append({
                    "field": "cross_shard_conflicts",
                    "action": "drop_non_cross_shard_or_duplicate_conflict",
                    "finding_refs": list(signature),
                })
                continue
            conflict["key"] = f"E{len(merged['conflicts']) + 1}"
            conflict["finding_refs"] = list(signature)
            conflict["claim_keys"] = list(dict.fromkeys(
                final_claim_key[key] for key in conflict["claim_keys"]
            ))
            local_conflict_signatures.add(signature)
            merged["conflicts"].append(conflict)
        if actions:
            self._record_semantic_normalizations(
                run_dir, arm=arm, node=node, attempt=1, actions=actions,
            )
        self._record_semantic_normalizations(
            run_dir, arm=arm, node=node, attempt=1,
            actions=[{
                "field": "findings",
                "action": "normalize_in_bounded_shards_with_global_equivalence_and_conflict_reconciliation",
                "finding_count": len(findings),
                "shard_count": (len(findings) + shard_size - 1) // shard_size,
                "shard_size": shard_size,
            }],
        )
        return merged

    def _option_seed_records(
        self, problem_ref: ArtifactRef, normalized_refs: tuple[ArtifactRef, ...],
        evidence_refs: tuple[ArtifactRef, ...], provenance: str, *, node: str,
        run_dir: Path, arm: str,
    ) -> list[dict[str, Any]]:
        """Derive unclustered possible change levers from normalized evidence."""

        problem = self.repository.get_by_hash(problem_ref.content_hash)["content"]
        records = [self.repository.get_by_hash(ref.content_hash) for ref in normalized_refs]
        claims = [record for record in records if record["record_type"] == "canonical_claim"]
        conflicts = [record for record in records if record["record_type"] == "evidence_conflict"]
        evidence = [self.repository.get_by_hash(ref.content_hash) for ref in evidence_refs]
        claim_digest = "\n".join(
            f"- {record['id']} [{record['content']['evidence_strength']}]: {self._english(record['content']['statement'])}"
            for record in claims
        )
        conflict_digest = "\n".join(
            f"- {record['id']} [{record['content']['resolvability']}]: {self._english(record['content']['description'])}"
            for record in conflicts
        ) or "- None recorded"
        prompt = self._header("derive_option_seeds", "option_seed_architect") + f"""
Derive 4-20 possible education-system change levers from the normalized evidence. These are option seeds, not recommendations and not yet clustered policy directions. Include a counterfactual seed when decision-relevant. Keep empirical support, assumptions, uncertainties, and evidence conflicts explicit. Do not use knowledge outside the supplied artifacts.

PUBLIC QUESTION: {self._english(problem['public_question'])}
CANONICAL CLAIMS:
{claim_digest}

EVIDENCE CONFLICTS:
{conflict_digest}

Return sequential keys O1..On. Every seed must cite at least one canonical claim and one underlying finding.
"""
        by_type = {
            record_type: [record["id"] for record in evidence if record["record_type"] == record_type]
            for record_type in ("finding", "assumption", "uncertainty")
        }
        result = self._call_structured_counted(
            prompt, contracts.option_seed_output(
                [record["id"] for record in claims],
                [record["id"] for record in conflicts],
                by_type["finding"], by_type["assumption"], by_type["uncertainty"],
            ),
            role="generator", max_tokens=16000, arm=arm, node=node,
            run_dir=run_dir, suffix="generate", constraints={"seeds": (4, 20)},
        )
        keys = [item["key"] for item in result["seeds"]]
        if keys != [f"O{i}" for i in range(1, len(keys) + 1)]:
            raise ValueError(f"Option seed keys must be sequential: {keys}")
        allowed_refs = {
            "canonical_claim_refs": {record["id"] for record in claims},
            "evidence_conflict_refs": {record["id"] for record in conflicts},
            "finding_refs": set(by_type["finding"]),
            "assumption_refs": set(by_type["assumption"]),
            "uncertainty_refs": set(by_type["uncertainty"]),
        }
        for item in result["seeds"]:
            for field, allowed in allowed_refs.items():
                unknown = set(item[field]) - allowed
                if unknown:
                    raise ValueError(
                        f"Option seed {item['key']} cites unknown {field}: "
                        f"{sorted(unknown)}"
                    )
        return [
            self._record(f"OSD-live-{item['key'].lower()}", "option_seed", provenance, {
                key: value for key, value in item.items() if key != "key"
            })
            for item in result["seeds"]
        ]

    def _cluster_option_seed_records(
        self, problem_ref: ArtifactRef, seed_refs: tuple[ArtifactRef, ...],
        provenance: str, *, node: str, run_dir: Path, arm: str,
    ) -> list[dict[str, Any]]:
        """Cluster option seeds and prove that none disappeared silently."""

        problem = self.repository.get_by_hash(problem_ref.content_hash)["content"]
        seeds = [self.repository.get_by_hash(ref.content_hash) for ref in seed_refs]
        digest = "\n".join(
            f"- {record['id']} [{record['content']['seed_type']}]: "
            f"{self._english(record['content']['title'])} — {self._english(record['content']['scope'])}"
            for record in seeds
        )
        prompt = self._header("cluster_option_seeds", "option_space_architect") + f"""
Cluster the complete option-seed set into 2-7 materially distinct candidate directions. This remains a pre-approval option-space proposal, not a recommendation. Preserve counterfactuals and meaningful minority directions. Return one exact disposition for every option seed and no others; critical seeds may not be rejected, placed out of scope, or left for human review.

PUBLIC QUESTION: {self._english(problem['public_question'])}
OPTION SEEDS:
{digest}

Use sequential direction ids S1..Sn. `clustered_into` and `retained_as_counterfactual` require at least one direction id. `merged_with` requires exactly one different seed. Every direction must cite its seed artifacts. Record at least one considered-but-rejected framing.
"""
        seed_ids = [record["id"] for record in seeds]
        result = self._call_structured_counted(
            prompt, contracts.clustered_option_space_output(seed_ids),
            role="generator", max_tokens=12000, arm=arm, node=node,
            run_dir=run_dir, suffix="generate",
            constraints={
                "directions": (2, 7), "rejected_framings": (1, 7),
                "coverage": (len(seed_ids), len(seed_ids)),
            },
        )
        direction_ids = [item["id"] for item in result["directions"]]
        if direction_ids != [f"S{i}" for i in range(1, len(direction_ids) + 1)]:
            raise ValueError(f"Option-space direction ids must be sequential: {direction_ids}")
        coverage = {entry["option_seed_ref"]: entry for entry in result["coverage"]}
        if len(coverage) != len(result["coverage"]) or set(coverage) != set(seed_ids):
            raise ValueError(
                "Option-seed coverage must contain every seed exactly once: "
                f"expected={sorted(seed_ids)}, got={sorted(coverage)}"
            )
        known_directions = set(direction_ids)
        for entry in coverage.values():
            if set(entry["direction_ids"]) - known_directions:
                raise ValueError(f"{entry['option_seed_ref']} cites an unknown direction")
            if entry["status"] in {"clustered_into", "retained_as_counterfactual"} and not entry["direction_ids"]:
                raise ValueError(f"{entry['option_seed_ref']} is retained without a direction")
            if entry["status"] == "merged_with" and (
                len(entry["merged_into_refs"]) != 1
                or entry["merged_into_refs"][0] == entry["option_seed_ref"]
            ):
                raise ValueError(f"{entry['option_seed_ref']} has an invalid merge disposition")
            if entry["critical"] and entry["status"] in {"rejected", "out_of_scope", "human_review"}:
                raise ValueError(f"Critical option-seed attrition at {entry['option_seed_ref']}")
        for direction in result["directions"]:
            for seed_id in direction["option_seed_refs"]:
                if direction["id"] not in coverage[seed_id]["direction_ids"]:
                    raise ValueError(f"Coverage omits {direction['id']} for {seed_id}")

        proposal = self._record(f"OS-live-{self.topic}", "option_space_proposal", provenance, {
            "directions": result["directions"],
            "rejected_framings": result["rejected_framings"],
            "derivation_notice": localized(
                "Clustered only from the complete option-seed artifacts declared by the run plan; pending an explicit human gate.",
                "Kizárólag a futási tervben deklarált teljes opciómag-készletből klaszterezve; explicit emberi kapudöntésre vár.",
            ),
        })
        ledger = self._record("CL-live-option-seeds", "coverage_ledger", provenance, {
            "gate_basis": "option_seed_clustering",
            "entries": [
                {
                    "option_seed_ref": entry["option_seed_ref"],
                    "status": entry["status"],
                    "direction_ids": entry["direction_ids"],
                    "merged_into_ref": entry["merged_into_refs"][0] if entry["merged_into_refs"] else None,
                    "critical": entry["critical"],
                    "rationale": entry["rationale"],
                }
                for entry in result["coverage"]
            ],
            "critical_attrition_count": 0,
            "verdict": "complete",
        })
        return [proposal, ledger]

    def _transformation_records(
        self, finding_refs: tuple[ArtifactRef, ...], provenance: str, *,
        node: str, run_dir: Path, arm: str,
        problem: dict[str, Any] | None = None,
        option_space: dict[str, Any] | None = None,
        canonical_claim_refs: tuple[ArtifactRef, ...] = (),
    ) -> list[dict[str, Any]]:
        findings = [self.repository.get_by_hash(ref.content_hash) for ref in finding_refs]
        digest = "\n".join(
            f"- {record['id']} [{record['content']['evidence_strength']}; {', '.join(record['content']['domain_tags'])}]: {self._english(record['content']['claim'])}"
            for record in findings
        )
        normalized_claims = [
            self.repository.get_by_hash(ref.content_hash)
            for ref in canonical_claim_refs
        ]
        normalized_digest = "\n".join(
            f"- {record['id']} [{record['content']['evidence_strength']}]: "
            f"{self._english(record['content']['statement'])}"
            for record in normalized_claims
        ) or "- No canonical-claim layer is available in this legacy run."
        problem = problem or self.topic_data["problem_brief"]
        frames = option_space["directions"] if option_space else self.topic_data["frames"]["scenarios"]
        frame_digest = "\n".join(
            f"- {frame['id']} — {self._english(frame['title'])}: {self._english(frame['scope'])}"
            for frame in frames
        )
        prompt = self._header("build_scenarios", "transformation_architect") + f"""
Derive a bilingual education-system transformation portfolio from the evidence record below. The final product is a library of change directions, not a debate among experts.

PUBLIC QUESTION: {self._english(problem['public_question'])}
PROBLEM: {self._english(problem['problem_statement'])}
SCOPE: {self._english(problem['scope'])}

EVIDENCE RECORD:
{digest}

NORMALIZED CLAIMS:
{normalized_digest}

HUMAN-APPROVED COVERAGE DIRECTIONS:
{frame_digest}

Produce 4-6 materially distinct proposals T1..Tn. The approved directions are a content-retention gate, not titles that must be copied: every S-id must map to at least one substantive proposal, while proposals may cover multiple directions or add a genuinely new direction. Include an explicit no-new-policy or passive-change counterfactual when decision-relevant. Every empirical mechanism must cite finding ids. When normalized claims are available, every proposal must also cite at least one supplied canonical-claim id. Keep evidence, assumptions, uncertainties, value choices, and implementation steps separate. Do not attribute content to experts. Do not use knowledge outside the supplied findings. Each family may contain one proposal in this first live slice, but its system problem, lever, and boundary must be explicit. Return one coverage entry for every S-id and no others.
"""
        result = self._call_structured_counted(
            prompt, contracts.transformation_output(
                [ref.id for ref in finding_refs], [frame["id"] for frame in frames],
                [ref.id for ref in canonical_claim_refs],
            ),
            role="generator", max_tokens=30000, arm=arm, node=node,
            run_dir=run_dir, suffix="generate", constraints={
                "proposals": (4, 6), "coverage": (len(frames), len(frames))
            },
            item_constraints={
                ("proposals", "mechanisms"): (2, 5),
                ("proposals", "implementation_steps"): (2, 6),
                ("proposals", "finding_refs"): (2, 20),
                ("proposals", "canonical_claim_refs"): (
                    1 if canonical_claim_refs else 0, 20
                ),
            },
        )
        proposals = sorted(result["proposals"], key=lambda item: int(item["key"][1:]))
        keys = [item["key"] for item in proposals]
        if len(keys) != len(set(keys)) or keys != [f"T{i}" for i in range(1, len(keys) + 1)]:
            raise ValueError(f"Transformation keys must be sequential and unique: {keys}")
        coverage = {entry["direction_id"]: entry for entry in result["coverage"]}
        expected_directions = {frame["id"] for frame in frames}
        if set(coverage) != expected_directions:
            raise ValueError(
                f"Approved-direction coverage mismatch: expected {sorted(expected_directions)}, "
                f"got {sorted(coverage)}"
            )
        for direction_id, entry in coverage.items():
            unknown = set(entry["proposal_keys"]) - set(keys)
            if unknown:
                raise ValueError(f"Coverage {direction_id} references unknown proposals: {sorted(unknown)}")
        records: list[dict[str, Any]] = []
        for item in proposals:
            key = item["key"].lower()
            assumption_ids = []
            for index, statement in enumerate(item["assumptions"], 1):
                artifact_id = f"A-live-{key}-{index:02d}"
                assumption_ids.append(artifact_id)
                records.append(self._record(artifact_id, "assumption", provenance, {
                    "statement": statement, "domain_tags": ["transformation_design"],
                    "testability": "partly_testable", "source_context": localized(
                        f"Live proposal {item['key']}", f"Élő {item['key']} javaslat"
                    ),
                }))
            uncertainty_ids = []
            for index, question in enumerate(item["uncertainties"], 1):
                artifact_id = f"U-live-{key}-{index:02d}"
                uncertainty_ids.append(artifact_id)
                records.append(self._record(artifact_id, "uncertainty", provenance, {
                    "question": question, "uncertainty_type": "implementation",
                    "current_confidence": "low", "reduction_path": localized(
                        "Targeted research or a reversible pilot.",
                        "Célzott kutatás vagy visszafordítható kísérleti bevezetés.",
                    ),
                }))
            proposal_id = f"TP-live-{key}"
            records.append(self._record(proposal_id, "transformation_proposal", provenance, {
                "title": item["title"], "goal": item["goal"], "change_level": item["change_level"],
                "mechanisms": item["mechanisms"], "implementation_steps": item["implementation_steps"],
                "expected_benefits": item["expected_benefits"], "costs": item["costs"],
                "risks": item["risks"], "equity_impact": item["equity_impact"],
                "evidence_status": item["evidence_status"], "finding_refs": item["finding_refs"],
                **(
                    {"canonical_claim_refs": item["canonical_claim_refs"]}
                    if canonical_claim_refs else {}
                ),
                "assumption_refs": assumption_ids, "uncertainty_refs": uncertainty_ids,
                "origin": "live_generation",
            }))
            records.append(self._record(f"TF-live-{key}", "transformation_family", provenance, {
                "name": item["title"], "system_problem": item["system_problem"],
                "change_lever": item["change_lever"], "boundary": item["boundary"],
                "proposal_refs": [proposal_id],
            }))
        frame_by_id = {frame["id"]: frame for frame in frames}
        records.append(self._record("CL-live-approved-frames", "coverage_ledger", provenance, {
            "gate_basis": "approved_option_space" if option_space else "approved_frames",
            "entries": [
                {
                    "direction_id": direction_id,
                    "direction_title": frame_by_id[direction_id]["title"],
                    "status": "covered",
                    "proposal_refs": [f"TP-live-{key.lower()}" for key in coverage[direction_id]["proposal_keys"]],
                    "rationale": coverage[direction_id]["rationale"],
                }
                for direction_id in sorted(coverage, key=lambda value: int(value[1:]))
            ],
            "critical_attrition_count": 0,
            "verdict": "complete",
        }))
        return records

    def _assessment_records(
        self, lens: dict[str, Any], proposals: tuple[ArtifactRef, ...],
        finding_refs: tuple[ArtifactRef, ...], provenance: str, *,
        node: str, run_dir: Path, arm: str,
        evidence_notes: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        proposal_records = [self.repository.get_by_hash(ref.content_hash) for ref in proposals]
        finding_records = [self.repository.get_by_hash(ref.content_hash) for ref in finding_refs]
        proposal_digest = "\n\n".join(
            f"{record['id']} — {self._english(record['content']['title'])}\nGoal: {self._english(record['content']['goal'])}\nMechanisms: {'; '.join(self._english(value) for value in record['content']['mechanisms'])}\nRisks: {'; '.join(self._english(value) for value in record['content']['risks'])}\nEvidence: {record['content']['evidence_status']}"
            for record in proposal_records
        )
        evidence_digest = "\n".join(
            f"- {record['id']} [{record['content']['evidence_strength']}]: {self._english(record['content']['claim'])}"
            for record in finding_records
        )
        note_text = ""
        if evidence_notes:
            note_text = "\nCURATED EVIDENCE BOUNDARIES:\n" + "\n".join(
                f"- [{note['evidence_strength']}] {self._english(note['claim'])} "
                f"Source: {self._english(note['source'])}"
                for note in evidence_notes
            )
        prompt = self._header("synthesis", lens["id"]) + f"""
Apply one reusable scientific lens to every unchanged transformation proposal. The proposal is the object of evaluation; do not simulate a person or attribute authority to a speaker. Author every assessment bilingually.

LENS: {self._english(lens['name'])}
DISCIPLINE: {self._english(lens['discipline'])}
QUESTIONS: {'; '.join(self._english(value) for value in lens['questions'])}
CRITERIA: {'; '.join(self._english(value) for value in lens['criteria'])}
LIMITATIONS: {'; '.join(self._english(value) for value in lens['limitations'])}
{note_text}

LENS EVIDENCE:
{evidence_digest}

PROPOSALS:
{proposal_digest}

Return exactly one assessment per proposal. Cite only supplied finding ids. Preserve contested evidence as contested in the prose. Separate strengths, weaknesses, opportunities, and threats. The verdict must follow from this lens only; it is not an overall recommendation.
"""
        result = self._call_structured_counted(
            prompt,
            contracts.assessment_output([ref.id for ref in proposals], [ref.id for ref in finding_refs]),
            role="generator", max_tokens=16000, arm=arm, node=node,
            run_dir=run_dir, suffix="assess",
            constraints={"assessments": (len(proposals), len(proposals))},
        )
        by_proposal = {item["proposal_ref"]: item for item in result["assessments"]}
        expected = {ref.id for ref in proposals}
        if set(by_proposal) != expected:
            raise ValueError(f"Lens {lens['id']} assessment coverage mismatch")
        return [self._record(
            f"AS-live-{ref.id.removeprefix('TP-live-')}-{lens['id']}",
            "lens_assessment", provenance,
            {**by_proposal[ref.id], "lens_ref": f"L-live-{lens['id']}"},
        ) for ref in proposals]

    def _dilemma_records(
        self, arm: str, proposals: tuple[ArtifactRef, ...],
        assessment_refs: tuple[ArtifactRef, ...], finding_refs: tuple[ArtifactRef, ...],
        provenance: str, *, node: str, run_dir: Path,
    ) -> list[dict[str, Any]]:
        proposal_records = [self.repository.get_by_hash(ref.content_hash) for ref in proposals]
        assessments = [self.repository.get_by_hash(ref.content_hash) for ref in assessment_refs]
        digest = "\n".join(
            f"- {record['id']} / {record['content']['lens_ref']} / {record['content']['verdict']}: {self._english(record['content']['assessment'])}"
            for record in assessments
        )
        prompt = self._header("argument_map", "dilemma_mapper") + f"""
Identify the decision tensions revealed by the transformation proposals and scientific lens assessments. Author every tension bilingually. Distinguish an empirical open question from a value conflict or irreducible trade-off. Evidence may clarify consequences but must not be presented as ranking public values.

PROPOSALS:
{self._compact_proposals(proposal_records)}

LENS ASSESSMENTS:
{digest}

Return 3-8 non-duplicative dilemmas. Cite proposal ids and finding ids. The evidence_boundary must say what further evidence can and cannot resolve. Psychology-specific mechanisms must remain visible when they materially change a value tension, but must not be forced into unrelated dilemmas.
"""
        result = self._call_structured_counted(
            prompt, contracts.dilemma_output([ref.id for ref in proposals], [ref.id for ref in finding_refs]),
            role="generator", max_tokens=16000, arm=arm, node=node,
            run_dir=run_dir, suffix="map", constraints={"dilemmas": (3, 8)},
            item_constraints={("dilemmas", "value_poles"): (2, 3)},
        )
        return [self._record(f"D-live-{arm}-{index:02d}", "dilemma", provenance, {
            **item, "origin": "live_generation",
        }) for index, item in enumerate(result["dilemmas"], 1)]

    def _agenda_records(
        self, arm: str, proposals: tuple[ArtifactRef, ...],
        assessment_refs: tuple[ArtifactRef, ...], uncertainty_refs: tuple[ArtifactRef, ...],
        provenance: str, *, node: str, run_dir: Path,
    ) -> list[dict[str, Any]]:
        assessments = [self.repository.get_by_hash(ref.content_hash) for ref in assessment_refs]
        uncertainties = [self.repository.get_by_hash(ref.content_hash) for ref in uncertainty_refs]
        prompt = self._header("synthesis", "research_agenda") + f"""
Build a bilingual, decision-relevant research agenda from the explicit uncertainties and low-confidence scientific lens assessments. Do not convert value conflicts into fake research questions.

UNCERTAINTIES:
{chr(10).join(f"- {r['id']}: {self._english(r['content']['question'])}" for r in uncertainties)}

ASSESSMENT SIGNALS:
{chr(10).join(f"- {r['content']['proposal_ref']} / {r['content']['lens_ref']} / {r['content']['confidence']}: {self._english(r['content']['assessment'])}" for r in assessments if r['content']['confidence'] != 'high')}

Return 4-10 prioritized questions with concrete methods. Cite proposal and uncertainty ids exactly. Mark questions that evidence cannot resolve as not_empirically_resolvable only when they expose a normative premise rather than ask for more data.
"""
        result = self._call_structured_counted(
            prompt, contracts.agenda_output([ref.id for ref in proposals], [ref.id for ref in uncertainty_refs]),
            role="generator", max_tokens=12000, arm=arm, node=node,
            run_dir=run_dir, suffix="agenda", constraints={"questions": (4, 10)},
        )
        return [self._record(f"RQ-live-{arm}-{index:02d}", "research_question", provenance, item)
                for index, item in enumerate(result["questions"], 1)]

    def _package_records(
        self, arm: str, refs: tuple[ArtifactRef, ...], provenance: str, *,
        node: str, run_dir: Path, problem: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        records = [self.repository.get_by_hash(ref.content_hash) for ref in refs]
        by_type: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            by_type.setdefault(record["record_type"], []).append(record)
        proposal_text = self._compact_proposals(by_type["transformation_proposal"])
        lens_text = "\n".join(
            f"- {r['content']['proposal_ref']} / {r['content']['lens_ref']} / {r['content']['verdict']}: {self._english(r['content']['assessment'])}"
            for r in by_type["lens_assessment"]
        )
        dilemma_text = "\n".join(f"- {self._english(r['content']['title'])}: {self._english(r['content']['tension'])}" for r in by_type["dilemma"])
        agenda_text = "\n".join(f"- {self._english(r['content']['question'])}" for r in by_type["research_question"])
        coverage_text = "\n".join(
            f"- {entry['direction_id']} -> {', '.join(entry['proposal_refs'])}: {self._english(entry['rationale'])}"
            for ledger in by_type.get("coverage_ledger", [])
            for entry in ledger["content"]["entries"]
        )
        sources_by_id = {record["id"]: record for record in by_type.get("source", [])}
        referenced_finding_ids = {
            finding_id
            for record_type in ("transformation_proposal", "lens_assessment", "dilemma")
            for record in by_type.get(record_type, [])
            for finding_id in record["content"].get("finding_refs", [])
        }
        finding_records = [
            record for record in by_type.get("finding", [])
            if record["id"] in referenced_finding_ids
        ]
        evidence_appendix = [
            {
                "finding_ref": finding["id"],
                "claim": finding["content"]["claim"],
                "sources": [
                    {
                        "source_ref": source_id,
                        "title": sources_by_id[source_id]["content"]["title"],
                        "url": sources_by_id[source_id]["content"]["url"],
                    }
                    for source_id in finding["content"]["source_refs"]
                ],
            }
            for finding in sorted(finding_records, key=lambda item: item["id"])
        ]
        citation_index = "\n".join(
            f"- [{entry['finding_ref']}] {self._english(entry['claim'])} — "
            + "; ".join(
                f"{self._english(source['title'])} ({source['url']})" for source in entry["sources"]
            )
            for entry in evidence_appendix
        )
        treatment_rule = ""
        if arm == "psychology":
            treatment_rule = (
                "The educational-psychology lens is present. If it materially changes "
                "the assessment, explicitly carry its named mechanism (for example "
                "academic self-concept/BFLPE, labeling, motivation, or goal orientation) "
                "into the summary. Do not merely mention the lens name."
            )
        problem = problem or self.topic_data["problem_brief"]
        prompt = self._header("brief", "decision_package_writer") + f"""
Write a concise bilingual decision-package summary for the public question below. The summary must preserve the transformation option space, distinguish empirical uncertainty from value choice, and name material disciplinary mechanisms rather than speakers. Do not choose one winner.

PUBLIC QUESTION: {self._english(problem['public_question'])}

TRANSFORMATIONS:
{proposal_text}

LENS ASSESSMENTS:
{lens_text}

DILEMMAS:
{dilemma_text}

RESEARCH AGENDA:
{agenda_text}

APPROVED-DIRECTION COVERAGE:
{coverage_text}

EVIDENCE CITATION INDEX:
{citation_index}

{treatment_rule}

Write 500-900 words. Explain what can change, the leading mechanism and constraint of each direction, what evidence supports or weakens it, what people must decide, and which research would most change the choice. Cite every material empirical or comparative claim inline with its exact finding id in square brackets, for example [F-live-demography-01]. Use only ids from the citation index.
"""
        required_terms = (
            "big-fish", "little-pond", "self-concept", "labeling",
            "goal orientation", "self-determination", "motivation",
        ) if arm == "psychology" else ()
        result = self._call_structured_text_checked(
            prompt, contracts.PACKAGE_OUTPUT, field="summary",
            minimum_words=500, maximum_words=900, required_terms=required_terms,
            minimum_citations=len(by_type["transformation_proposal"]),
            role="generator", max_tokens=20000, arm=arm, node=node,
            run_dir=run_dir, suffix="package",
        )
        def ids(record_type: str) -> list[str]:
            return sorted(r["id"] for r in by_type.get(record_type, []))
        return [self._record(f"DP-live-{arm}", "decision_package", provenance, {
            "title": problem["title"],
            "public_question": problem["public_question"],
            "summary": result["summary"],
            "transformation_family_refs": ids("transformation_family"),
            "proposal_refs": ids("transformation_proposal"),
            "coverage_ledger_refs": ids("coverage_ledger"),
            "lens_assessment_refs": ids("lens_assessment"),
            "dilemma_refs": ids("dilemma"), "research_question_refs": ids("research_question"),
            "evidence_appendix": evidence_appendix,
            "generation_notice": self._generation_notice(arm),
        })]

    def _evaluation_records(
        self, arm: str, package_ref: ArtifactRef, proposals: tuple[ArtifactRef, ...],
        assessments: tuple[ArtifactRef, ...], dilemmas: tuple[ArtifactRef, ...],
        agenda: tuple[ArtifactRef, ...], provenance: str, *, node: str, run_dir: Path,
    ) -> list[dict[str, Any]]:
        package = self.repository.get_by_hash(package_ref.content_hash)
        prompt = self._header("judge_score", "cross_family_evaluator") + f"""
Evaluate this artifact-first decision package on six dimensions from 0 to 10. You are the judge family and must evaluate the generator's output, not rewrite it. Return bilingual strengths and concerns.

PACKAGE SUMMARY:
{self._english(package['content']['summary'])}

VISIBLE EVIDENCE APPENDIX:
{chr(10).join(f"- [{entry['finding_ref']}] {self._english(entry['claim'])} — " + '; '.join(source['url'] for source in entry['sources']) for entry in package['content'].get('evidence_appendix', []))}

STRUCTURAL COUNTS: proposals={len(proposals)}, lens_assessments={len(assessments)}, dilemmas={len(dilemmas)}, research_questions={len(agenda)}.

Rubric:
- artifact_integrity: typed separation and traceable references;
- evidence_discipline: facts, assumptions, uncertainty, and values remain distinct;
- transformation_specificity: mechanisms and implementation are concrete;
- lens_traceability: disciplinary judgments and their limits survive into the package;
- dilemma_clarity: evidence boundaries and human value choices are explicit;
- decision_usefulness: the package accelerates a real decision without manufacturing consensus.

Score only what is visible. Treat an inline finding id as auditable only when the visible appendix resolves it to a claim and source URI. Note missing evidence edges or generic prose as concerns. In the psychology arm, do not award points merely because an extra lens exists; score whether its substantive mechanism is carried and decision-relevant.
"""
        result = self._call_structured(
            prompt, contracts.EVALUATION_OUTPUT, role="judge", max_tokens=8000,
            arm=arm, node=node, run_dir=run_dir, suffix="judge"
        )
        dimensions = result["dimensions"]
        total = round(sum(dimensions.values()) / len(dimensions), 3)
        return [self._record(f"EV-live-{arm}", "evaluation", provenance, {
            "package_ref": package_ref.id, "total": total, "dimensions": dimensions,
            "strengths": result["strengths"], "concerns": result["concerns"],
            "verdict": result["verdict"],
        })]

    def _readiness_records(
        self, arm: str, package_ref: ArtifactRef, evaluation_ref: ArtifactRef,
        proposals: tuple[ArtifactRef, ...], dilemmas: tuple[ArtifactRef, ...],
        agenda: tuple[ArtifactRef, ...], provenance: str,
    ) -> list[dict[str, Any]]:
        evaluation = self.repository.get_by_hash(evaluation_ref.content_hash)["content"]
        verdict = {
            "accept": "ready_for_human_review",
            "accept_with_caveats": "ready_with_conditions",
            "revise": "needs_revision",
            "reject": "needs_revision",
        }[evaluation["verdict"]]
        priority_questions = []
        for ref in agenda:
            record = self.repository.get_by_hash(ref.content_hash)
            if record["content"]["decision_impact"] == "high":
                priority_questions.append(ref.id)
        rationale = (
            localized(
                "The cross-family evaluation accepted the package for human review; the external-use gate remains a human decision.",
                "Az eltérő modellcsalád értékelése emberi felülvizsgálatra elfogadta a csomagot; a külső felhasználás kapuja továbbra is emberi döntés.",
            )
            if verdict != "needs_revision"
            else localized(
                "The cross-family evaluation requires revision before human external-use review.",
                "Az eltérő modellcsalád értékelése módosítást kér az emberi külsőfelhasználási felülvizsgálat előtt.",
            )
        )
        return [self._record(f"DR-live-{arm}", "decision_readiness", provenance, {
            "package_ref": package_ref.id,
            "evaluation_ref": evaluation_ref.id,
            "verdict": verdict,
            "conditions": evaluation["concerns"],
            "candidate_first_move_refs": [ref.id for ref in proposals],
            "unresolved_dilemma_refs": [ref.id for ref in dilemmas],
            "priority_research_question_refs": priority_questions,
            "human_external_use_gate": "pending",
            "rationale": rationale,
        })]

    def compare_arms(self) -> dict[str, Any]:
        baseline = self._load(self._arm_summary("baseline"))
        psychology = self._load(self._arm_summary("psychology"))
        base_package = self.repository.get_current(baseline["package_ref"])
        psych_package = self.repository.get_current(psychology["package_ref"])
        psych_assessments = self.repository.list(record_type="lens_assessment", topic=self.topic)
        psych_assessments = [r for r in psych_assessments if r["content"]["lens_ref"] == "L-live-educational_psychology"]
        keywords = ["big-fish", "little-pond", "self-concept", "label", "stereotype", "motivation", "goal orientation", "psycholog"]
        assessment_text = " ".join(
            self._english(r["content"]["assessment"])
            for r in psych_assessments
        ).lower()
        package_text = self._english(psych_package["content"]["summary"]).lower()
        comparison = {
            "architecture_version": DAG_VERSION,
            "baseline_package_ref": baseline["package_ref"],
            "psychology_package_ref": psychology["package_ref"],
            "transformation_hashes_identical": baseline["transformation_hashes"] == psychology["transformation_hashes"],
            "baseline_lens_count": baseline["counts"]["lens_definition"],
            "psychology_lens_count": psychology["counts"]["lens_definition"],
            "psychology_assessment_count": len(psych_assessments),
            "psychology_keyword_hits": {
                "assessments": {word: assessment_text.count(word) for word in keywords},
                "decision_package": {word: package_text.count(word) for word in keywords},
            },
            "baseline_evaluation": baseline["evaluation"],
            "psychology_evaluation": psychology["evaluation"],
            "evaluation_delta": round(psychology["evaluation"]["total"] - baseline["evaluation"]["total"], 3),
            "treatment_execution": psychology["execution"],
            "position_carriage_passed": any(word in package_text for word in keywords),
            "comparison_notice": "One live sample per arm; score differences are descriptive, not causal estimates.",
        }
        write_json(self.output_root / "comparison.json", comparison)
        return comparison

    def _summarize_arm(
        self, arm: str, run_dir: Path, package_ref: ArtifactRef,
        evaluation_ref: ArtifactRef, proposals: tuple[ArtifactRef, ...],
        assessments: list[ArtifactRef], downstream: dict[str, tuple[ArtifactRef, ...]],
    ) -> dict[str, Any]:
        manifests = [self._load(path) for path in sorted((run_dir / "nodes").glob("*.json"))]
        dispositions = [item["disposition"] for item in manifests]
        counts = self._manifest_counts(run_dir)
        evaluation = self.repository.get_by_hash(evaluation_ref.content_hash)["content"]
        readiness = self.repository.get_by_hash(downstream["readiness"][0].content_hash)["content"]
        return {
            "arm": arm, "run_id": f"live-{self.topic}-{arm}",
            "package_ref": package_ref.id, "evaluation_ref": evaluation_ref.id,
            "evaluation": evaluation, "counts": counts,
            "readiness_ref": downstream["readiness"][0].id,
            "readiness": readiness,
            "transformation_hashes": sorted(ref.content_hash for ref in proposals),
            "execution": {
                "nodes": len(manifests), "cache_hits": dispositions.count("cache_hit"),
                "executed": dispositions.count("executed"),
                "failed": dispositions.count("failed"),
                "dispositions": {item["node_id"]: item["disposition"] for item in manifests},
            },
            "dilemma_refs": [ref.id for ref in downstream["dilemmas"]],
            "research_question_refs": [ref.id for ref in downstream["agenda"]],
            "completed_at": _now(),
        }

    def _manifest_counts(self, run_dir: Path) -> dict[str, int]:
        ids_by_type: dict[str, set[str]] = {}
        for path in sorted((run_dir / "nodes").glob("*.json")):
            manifest = self._load(path)
            for artifact in manifest["output_artifacts"]:
                ids_by_type.setdefault(artifact["record_type"], set()).add(artifact["id"])
        tracked = (
            "finding", "transformation_family", "transformation_proposal",
            "lens_definition", "lens_assessment", "dilemma", "research_question",
            "coverage_ledger", "decision_readiness",
        )
        return {record_type: len(ids_by_type.get(record_type, set())) for record_type in tracked}

    def _call_free(
        self, prompt: str, *, role: str, max_tokens: int, web_search: bool,
        arm: str, node: str, run_dir: Path, suffix: str,
    ) -> str:
        self._persist_prompt(run_dir, node, suffix, prompt)
        marker = self.llm.call_log_len()
        try:
            result = self.llm.call_model(
                prompt, role, max_tokens=max_tokens, web_search=web_search
            )
            raw = run_dir / "raw" / f"{node}.{suffix}.txt"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text(result, encoding="utf-8")
            self._persist_attempt(
                run_dir, node, suffix, prompt, result.encode("utf-8"), "txt"
            )
            return result
        finally:
            self._record_calls(marker, arm=arm, node=node)

    def _recover_or_call_search(
        self, prompt: str, *, arm: str, node: str, run_dir: Path,
    ) -> str:
        raw = run_dir / "raw" / f"{node}.search.txt"
        if raw.exists():
            return raw.read_text(encoding="utf-8")
        # A failed structured phase may still have persisted the next prompt,
        # which contains the completed paid search notes. Recover them instead
        # of issuing the same web search again.
        analysis_prompt = run_dir / "prompts" / f"{node}.analysis.md"
        if analysis_prompt.exists():
            text = analysis_prompt.read_text(encoding="utf-8")
            marker = "RESEARCH NOTES:\n"
            end_marker = "\n\nRules:"
            if marker in text and end_marker in text:
                notes = text.split(marker, 1)[1].split(end_marker, 1)[0]
                raw.parent.mkdir(parents=True, exist_ok=True)
                raw.write_text(notes, encoding="utf-8")
                return notes
        return self._call_free(
            prompt, role="generator", max_tokens=10000, web_search=True,
            arm=arm, node=node, run_dir=run_dir, suffix="search"
        )

    def _call_structured(
        self, prompt: str, schema: dict[str, Any], *, role: str,
        max_tokens: int, arm: str, node: str, run_dir: Path, suffix: str,
    ) -> dict[str, Any]:
        self._persist_prompt(run_dir, node, suffix, prompt)
        recovered = self._recover_structured_attempt(
            run_dir, node, suffix, prompt
        )
        if recovered is not None:
            return recovered
        escalation_budget = min(max_tokens * 3 // 2, 48000)
        escalation_suffix = f"{suffix}-token-escalation-{escalation_budget}"
        recovered = self._recover_structured_attempt(
            run_dir, node, escalation_suffix, prompt
        )
        if recovered is not None:
            return recovered
        marker = self.llm.call_log_len()
        try:
            response_stage = suffix
            try:
                result = self.llm.call_structured(
                    prompt, schema, role, max_tokens=max_tokens
                )
            except Exception as exc:
                escalated = _escalated_token_budget(max_tokens, exc)
                if escalated is None or escalated <= max_tokens:
                    raise
                response_stage = f"{suffix}-token-escalation-{escalated}"
                self._persist_prompt(run_dir, node, response_stage, prompt)
                result = self.llm.call_structured(
                    prompt, schema, role, max_tokens=escalated
                )
            self._persist_attempt(
                run_dir, node, response_stage, prompt,
                canonical_json_bytes(result), "json"
            )
            return result
        finally:
            self._record_calls(marker, arm=arm, node=node)

    @staticmethod
    def _recover_structured_attempt(
        run_dir: Path, node: str, stage: str, prompt: str
    ) -> dict[str, Any] | None:
        """Replay an immutable response for the exact prompt during resume."""

        current_path = run_dir / "attempts" / node / "current.json"
        execution_ids = []
        if current_path.exists():
            execution_ids.append(
                json.loads(current_path.read_text(encoding="utf-8"))["execution_id"]
            )
        attempts_root = run_dir / "attempts" / node
        if attempts_root.exists():
            execution_ids.extend(
                path.name for path in sorted(attempts_root.iterdir())
                if path.is_dir() and path.name not in execution_ids
            )
        prompt_bytes = prompt.encode("utf-8")
        prompt_hash = hashlib.sha256(prompt_bytes).hexdigest()
        leaf = f"{stage}-{prompt_hash[:16]}"
        for execution_id in execution_ids:
            attempt_dir = attempts_root / execution_id / leaf
            prompt_path = attempt_dir / "prompt.md"
            response_path = attempt_dir / "response.json"
            if (
                prompt_path.exists()
                and response_path.exists()
                and prompt_path.read_bytes() == prompt_bytes
            ):
                response = response_path.read_bytes()
                current = (
                    json.loads(current_path.read_text(encoding="utf-8"))
                    if current_path.exists()
                    else None
                )
                if current and current["execution_id"] != execution_id:
                    # A code-level cache-key change may still produce the exact
                    # same prompt. Adopt that immutable response into the
                    # current execution so output provenance names the attempt
                    # it actually replayed instead of leaving an audit gap.
                    ArtifactDagRunner._persist_attempt(
                        run_dir, node, stage, prompt, response, "json"
                    )
                return json.loads(response)
        return None

    def _call_structured_counted(
        self, prompt: str, schema: dict[str, Any], *, role: str,
        max_tokens: int, arm: str, node: str, run_dir: Path, suffix: str,
        constraints: dict[str, tuple[int, int]], retries: int = 2,
        item_constraints: dict[tuple[str, str], tuple[int, int]] | None = None,
    ) -> dict[str, Any]:
        current_prompt = prompt
        for attempt in range(retries + 1):
            attempt_suffix = suffix if attempt == 0 else f"{suffix}-semantic-retry-{attempt}"
            result = self._call_structured(
                current_prompt, schema, role=role, max_tokens=max_tokens,
                arm=arm, node=node, run_dir=run_dir, suffix=attempt_suffix,
            )
            result, normalizations, deficits = _normalize_collection_counts(
                result, constraints
            )
            for field, missing in deficits.items():
                result[field] = self._fill_structured_collection(
                    prompt=prompt,
                    schema=schema,
                    field=field,
                    existing=list(result.get(field, [])),
                    missing=missing,
                    role=role,
                    max_tokens=max_tokens,
                    arm=arm,
                    node=node,
                    run_dir=run_dir,
                    suffix=attempt_suffix,
                )
                normalizations.append({
                    "field": field,
                    "action": "targeted_fill",
                    "added": missing,
                    "after": len(result[field]),
                })
            if normalizations:
                self._record_semantic_normalizations(
                    run_dir, arm=arm, node=node, attempt=attempt + 1,
                    actions=normalizations,
                )
            violations = []
            for field, (minimum, maximum) in constraints.items():
                count = len(result.get(field, []))
                if not minimum <= count <= maximum:
                    violations.append(
                        f"{field} requires {minimum}-{maximum} items, got {count}"
                    )
            for (collection, field), (minimum, maximum) in (item_constraints or {}).items():
                for index, item in enumerate(result.get(collection, []), 1):
                    count = len(item.get(field, []))
                    if not minimum <= count <= maximum:
                        violations.append(
                            f"{collection}[{index}].{field} requires "
                            f"{minimum}-{maximum} items, got {count}"
                        )
            if not violations:
                return result
            rejection = {
                "recorded_at": _now(), "arm": arm, "node_id": node,
                "attempt": attempt + 1, "violations": violations, "output": result,
            }
            rejection_path = run_dir / "semantic_rejections.jsonl"
            with rejection_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(rejection, ensure_ascii=False, sort_keys=True) + "\n")
            current_prompt = prompt + _cardinality_repair_instruction(
                constraints, violations
            )
        raise ValueError(
            f"{node} failed semantic cardinality after {retries + 1} attempts"
        )

    def _fill_structured_collection(
        self, *, prompt: str, schema: dict[str, Any], field: str,
        existing: list[Any], missing: int, role: str, max_tokens: int,
        arm: str, node: str, run_dir: Path, suffix: str,
    ) -> list[Any]:
        """Generate missing semantic items one at a time without replacing valid data."""

        item_schema = schema["properties"][field]["items"]
        repaired = list(existing)
        for offset in range(missing):
            fill_prompt = (
                prompt
                + "\n\nTARGETED CARDINALITY FILL: The main response is otherwise valid, "
                f"but {field} is missing {missing} required item(s). Generate exactly "
                "ONE additional, non-duplicative item for that collection. Existing "
                f"items:\n{json.dumps(repaired, ensure_ascii=False, indent=2)}\n"
                "Return only the requested item in the wrapper field named item."
            )
            wrapper_schema = {
                "type": "object",
                "additionalProperties": False,
                "properties": {"item": item_schema},
                "required": ["item"],
            }
            filled = self._call_structured(
                fill_prompt,
                wrapper_schema,
                role=role,
                max_tokens=min(max_tokens, 4000),
                arm=arm,
                node=node,
                run_dir=run_dir,
                suffix=f"{suffix}-fill-{field}-{offset + 1}",
            )
            repaired.append(filled["item"])
        return repaired

    @staticmethod
    def _record_semantic_normalizations(
        run_dir: Path, *, arm: str, node: str, attempt: int,
        actions: list[dict[str, Any]],
    ) -> None:
        path = run_dir / "semantic_normalizations.jsonl"
        entry = {
            "arm": arm,
            "node_id": node,
            "attempt": attempt,
            "actions": actions,
        }
        existing = (
            [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if path.exists() else []
        )
        if entry not in existing:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    def _call_structured_text_checked(
        self, prompt: str, schema: dict[str, Any], *, field: str,
        minimum_words: int, maximum_words: int, required_terms: tuple[str, ...],
        minimum_citations: int,
        role: str, max_tokens: int, arm: str, node: str, run_dir: Path,
        suffix: str, retries: int = 2,
    ) -> dict[str, Any]:
        current_prompt = prompt
        for attempt in range(retries + 1):
            attempt_suffix = suffix if attempt == 0 else f"{suffix}-semantic-retry-{attempt}"
            result = self._call_structured(
                current_prompt, schema, role=role, max_tokens=max_tokens,
                arm=arm, node=node, run_dir=run_dir, suffix=attempt_suffix,
            )
            checked_text = self._english(result.get(field, ""))
            word_count = len(checked_text.split())
            violations = []
            if not minimum_words <= word_count <= maximum_words:
                violations.append(
                    f"{field} requires {minimum_words}-{maximum_words} words, got {word_count}"
                )
            normalized = checked_text.lower()
            if required_terms and not any(term in normalized for term in required_terms):
                violations.append(
                    f"{field} must carry at least one named mechanism from: "
                    + ", ".join(required_terms)
                )
            citation_count = checked_text.count("[F-")
            if citation_count < minimum_citations:
                violations.append(
                    f"{field} requires at least {minimum_citations} inline finding citations, "
                    f"got {citation_count}"
                )
            if not violations:
                return result
            rejection = {
                "recorded_at": _now(), "arm": arm, "node_id": node,
                "attempt": attempt + 1, "violations": violations, "output": result,
            }
            rejection_path = run_dir / "semantic_rejections.jsonl"
            with rejection_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(rejection, ensure_ascii=False, sort_keys=True) + "\n")
            current_prompt = prompt + (
                "\n\nSTRICT DECISION-PACKAGE REPAIR: The previous complete response was rejected: "
                + "; ".join(violations)
                + ". Generate a complete replacement and finish every option before concluding."
            )
        raise ValueError(
            f"{node} failed decision-package semantics after {retries + 1} attempts"
        )

    def _record_calls(self, marker: int, *, arm: str, node: str) -> None:
        self.call_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.call_log_path.open("a", encoding="utf-8") as handle:
            for entry in self.llm.CALL_LOG[marker:]:
                safe = {
                    key: value for key, value in entry.items()
                    if key in {"task", "agent", "role", "provider", "backend", "model", "ms", "input_tokens", "output_tokens", "web_searches", "errors"}
                }
                safe.update({"arm": arm, "node_id": node, "recorded_at": _now()})
                handle.write(json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def _persist_prompt(run_dir: Path, node: str, suffix: str, prompt: str) -> None:
        path = run_dir / "prompts" / f"{node}.{suffix}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8") != prompt:
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
            path = path.with_name(f"{node}.{suffix}.{digest}.md")
        if not path.exists():
            path.write_text(prompt, encoding="utf-8")

    @staticmethod
    def _persist_attempt(
        run_dir: Path, node: str, stage: str, prompt: str,
        response: bytes, extension: str,
    ) -> None:
        current_path = run_dir / "attempts" / node / "current.json"
        if current_path.exists():
            execution_id = json.loads(
                current_path.read_text(encoding="utf-8")
            )["execution_id"]
        else:
            # Compatibility for direct method tests outside NodeExecutor.
            execution_id = "unbound"
        prompt_bytes = prompt.encode("utf-8")
        prompt_hash = hashlib.sha256(prompt_bytes).hexdigest()
        response_hash = hashlib.sha256(response).hexdigest()
        attempt_dir = run_dir / "attempts" / node / execution_id / (
            f"{stage}-{prompt_hash[:16]}"
        )
        attempt_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = attempt_dir / "prompt.md"
        response_path = attempt_dir / f"response.{extension}"
        if prompt_path.exists() and prompt_path.read_bytes() != prompt_bytes:
            raise ValueError(f"Attempt prompt hash collision at {prompt_path}")
        if response_path.exists() and response_path.read_bytes() != response:
            raise ValueError(f"Attempt response changed at {response_path}")
        prompt_path.write_bytes(prompt_bytes)
        response_path.write_bytes(response)
        index_path = attempt_dir.parent / "index.jsonl"
        entry = {
            "stage": stage,
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "status": "completed",
        }
        existing = (
            [json.loads(line) for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if index_path.exists() else []
        )
        if entry not in existing:
            with index_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    def _write_cost_report(self) -> None:
        if not self.call_log_path.exists():
            return
        entries = [json.loads(line) for line in self.call_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        prices = self._load(self.root / "config" / "system_config.json")["pricing"]["usd_per_mtok"]
        per_arm: dict[str, dict[str, Any]] = {}
        for entry in entries:
            arm = entry["arm"]
            bucket = per_arm.setdefault(arm, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_usd": 0.0, "failed_calls": 0})
            bucket["calls"] += 1
            if entry.get("backend") == "failed":
                bucket["failed_calls"] += 1
            input_tokens = entry.get("input_tokens") or 0
            output_tokens = entry.get("output_tokens") or 0
            bucket["input_tokens"] += input_tokens
            bucket["output_tokens"] += output_tokens
            price = prices.get(entry.get("model"))
            if price:
                bucket["estimated_usd"] += input_tokens / 1_000_000 * price[0] + output_tokens / 1_000_000 * price[1]
        for bucket in per_arm.values():
            bucket["estimated_usd"] = round(bucket["estimated_usd"], 4)
        write_json(self.output_root / "cost_report.json", {"arms": per_arm, "pricing_source": "config/system_config.json", "call_count": len(entries)})

    def _report_node(self, run_dir: Path, name: str) -> None:
        manifest = self._load(run_dir / "nodes" / f"{name}.json")
        print(f"[{manifest['disposition'].upper():9}] {name} -> {len(manifest['output_artifacts'])} artifacts", flush=True)

    @staticmethod
    def _require_count(items: list[Any], minimum: int, maximum: int, label: str) -> None:
        if not minimum <= len(items) <= maximum:
            raise ValueError(
                f"{label} requires {minimum}-{maximum} items, got {len(items)}"
            )

    def _spec(
        self, name: str, inputs: tuple[str, ...], outputs: tuple[str, ...],
        schemas: tuple[str, ...], *, role: str = "deterministic",
        spec_files: tuple[str, ...] = (),
    ) -> NodeSpec:
        return NodeSpec(
            name=name, version="1.0.0", input_types=inputs, output_types=outputs,
            schema_files=tuple(f"schemas/v2/{schema}" for schema in schemas),
            spec_files=spec_files, role=role,
        )

    def _record(
        self, artifact_id: str, record_type: str, provenance: str,
        content: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "id": artifact_id, "record_type": record_type,
            "schema_version": ARTIFACT_VERSION, "topic": self.topic, "status": "candidate",
            "content": content, "provenance_ref": provenance,
            "created_at": self.created_at, "supersedes": None,
        }

    def _experiment_created_at(self) -> str:
        path = self.output_root / "experiment_config.json"
        if path.exists():
            return self._load(path)["created_at"]
        created_at = _now()
        write_json(path, {
            "architecture_version": DAG_VERSION, "created_at": created_at,
            "generator_provider": self.provider_generator if hasattr(self, "provider_generator") else "anthropic",
            "judge_provider": self.provider_judge if hasattr(self, "provider_judge") else "openai",
            "topic": self.topic,
        })
        return created_at

    @staticmethod
    def _header(task: str, agent: str) -> str:
        return (
            f"TASK: {task}\nAGENT: {agent}\nLANG: en+hu\n\n"
            "Every semantic prose field must be authored natively in both "
            "languages as one exact {en, hu} object. The two texts must carry "
            "the same claim, scope, numbers, uncertainty, and references. "
            "Do not write Hungarian as a later translation step.\n\n"
        )

    @staticmethod
    def _bullets(items: Iterable[Any]) -> str:
        return "\n".join(f"- {text(item, 'en')}" for item in items)

    @staticmethod
    def _english(value: Any) -> str:
        """Read canonical English text or a legacy bilingual leaf."""

        return text(value, "en")

    @classmethod
    def _contract_hash(cls, name: str) -> str:
        """Hash the exact node implementation and provider contract.

        The live runner used to hash only a hand-maintained label while every
        generative node declared the complete experiment module as a spec
        dependency. That combination was both too broad and too easy to leave
        stale. This map makes the dependency executable and node-local.
        """

        dependencies = {
            "draft_problem_brief_v1": (
                cls._problem_brief_proposal_records,
                contracts.PROBLEM_BRIEF_OUTPUT,
            ),
            "research_v1": (cls._research_records, contracts.RESEARCH_OUTPUT),
            "derive_option_space_v1": (
                cls._option_space_records,
                contracts.option_space_output,
            ),
            "normalize_evidence_v1": (
                cls._normalize_evidence_records,
                contracts.evidence_normalization_output,
            ),
            "derive_option_seeds_v1": (
                cls._option_seed_records,
                contracts.option_seed_output,
            ),
            "cluster_option_seeds_v1": (
                cls._cluster_option_seed_records,
                contracts.clustered_option_space_output,
            ),
            "baseline_lens_registry_v1": (cls._baseline_lens_records, None),
            "psychology_lens_pr29": (cls._psychology_lens_records, None),
            "derive_transformations_v1": (
                cls._transformation_records,
                contracts.transformation_output,
            ),
            "apply_lens_v1": (cls._assessment_records, contracts.assessment_output),
            "identify_dilemmas_v1": (cls._dilemma_records, contracts.dilemma_output),
            "research_agenda_v1": (cls._agenda_records, contracts.agenda_output),
            "decision_package_v1": (cls._package_records, contracts.PACKAGE_OUTPUT),
            "evaluate_package_v1": (cls._evaluation_records, contracts.EVALUATION_OUTPUT),
            "decision_readiness_v1": (cls._readiness_records, None),
        }
        try:
            implementation, contract = dependencies[name]
        except KeyError as exc:
            raise ValueError(f"Unknown live node contract: {name}") from exc
        contract_source = (
            inspect.getsource(contract)
            if callable(contract)
            else json.dumps(contract, ensure_ascii=False, sort_keys=True)
        )
        payload = f"{name}\n{inspect.getsource(implementation)}\n{contract_source}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _safe_uri(value: str, fallback_id: str) -> str:
        # Provider output occasionally joins several citations in one field.
        # The canonical Source contract stores one URI, so select the first
        # explicit HTTP(S) target instead of weakening URI validation.
        match = re.search(r"https?://[^\s;]+", value)
        if match:
            candidate = match.group(0).rstrip(".,)")
            candidate = quote(candidate, safe=":/?#[]@!$&'()*+,;=%")
            if urlsplit(candidate).scheme in {"http", "https"}:
                return candidate
        return f"urn:epl:live-source:{_slug(fallback_id)}"

    @staticmethod
    def _types(refs: Iterable[ArtifactRef], *record_types: str) -> tuple[ArtifactRef, ...]:
        allowed = set(record_types)
        return tuple(ref for ref in refs if ref.record_type in allowed)

    @staticmethod
    def _compact_proposals(records: list[dict[str, Any]]) -> str:
        return "\n\n".join(
            f"{r['id']} — {text(r['content']['title'], 'en')}\nGoal: {text(r['content']['goal'], 'en')}\nMechanisms: {'; '.join(text(value, 'en') for value in r['content']['mechanisms'])}\nEvidence: {r['content']['evidence_status']}\nRisks: {'; '.join(text(value, 'en') for value in r['content']['risks'])}"
            for r in records
        )

    @staticmethod
    def _generation_notice(arm: str) -> dict[str, str]:
        if arm == "psychology":
            return localized(
                "Fresh live v2 psychology sensitivity arm. Generator=anthropic; "
                "judge=openai. The PR #29 lens is test-only, not registry admission.",
                "Friss, élő v2 pszichológiai érzékenységi ág. Generátor=anthropic; "
                "értékelő=openai. A PR #29 nézőpont csak teszt, nem jegyzékbe vétel.",
            )
        if arm == "production":
            return localized(
                "Fresh live v2 production replicate using the admitted lens registry. "
                "Generator=anthropic; judge=openai; human external-use gate remains pending.",
                "Friss, élő v2 produkciós ismétlés a befogadott nézőpontjegyzékkel. "
                "Generátor=anthropic; értékelő=openai; az emberi külsőfelhasználási kapu függőben marad.",
            )
        return localized(
            "Fresh live v2 baseline arm. Generator=anthropic; judge=openai.",
            "Friss, élő v2 alapág. Generátor=anthropic; értékelő=openai.",
        )

    def _arm_summary(self, arm: str) -> Path:
        return self.output_root / "runs" / f"live-{self.topic}-{arm}" / "arm_summary.json"

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))


class PsychologyLensExperiment(ArtifactDagRunner):
    """Backward-compatible name for the PR #29 A/B acceptance experiment."""
