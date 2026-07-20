"""Live A/B acceptance runner for the v2 artifact DAG."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from policy_lab.dag import NodeExecutor, NodeSpec
from policy_lab.jsonio import content_hash, write_json
from policy_lab.live import contracts
from policy_lab.schema_registry import SchemaRegistry
from policy_lab.store import ArtifactRef, ArtifactRepository

VERSION = "2.0.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower()


class PsychologyLensExperiment:
    """Run one full baseline and one dependency-localized lens treatment."""

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
                generation_parameters={"search_max_tokens": 8000, "analysis_max_tokens": 12000},
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
                ("assumption", "uncertainty", "transformation_proposal", "transformation_family"),
                ("assumption.schema.json", "uncertainty.schema.json", "transformation_proposal.schema.json", "transformation_family.schema.json"),
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
            all_lens_refs.append(psych_lens_ref)

        downstream = self._run_downstream(
            executor=executor, run_dir=run_dir, arm=arm,
            proposals=proposals, transformation_refs=transformation_refs,
            lens_refs=tuple(all_lens_refs), assessment_refs=tuple(assessment_refs),
            finding_refs=tuple(all_finding_refs),
            uncertainty_refs=self._types((*evidence_refs, *transformation_refs), "uncertainty"),
            common_config=common_config,
        )
        package_ref = downstream["package"][0]
        evaluation_ref = downstream["evaluation"][0]
        self.repository.validate_graph((package_ref.id, evaluation_ref.id))
        summary = self._summarize_arm(arm, run_dir, package_ref, evaluation_ref, proposals, assessment_refs, downstream)
        write_json(self._arm_summary(arm), summary)
        print(f"ARM {arm}: total={summary['evaluation']['total']:.3f}, cache_hits={summary['execution']['cache_hits']}, executed={summary['execution']['executed']}", flush=True)
        return summary

    def _run_downstream(
        self, *, executor: NodeExecutor, run_dir: Path, arm: str,
        proposals: tuple[ArtifactRef, ...], transformation_refs: tuple[ArtifactRef, ...],
        lens_refs: tuple[ArtifactRef, ...], assessment_refs: tuple[ArtifactRef, ...],
        finding_refs: tuple[ArtifactRef, ...], uncertainty_refs: tuple[ArtifactRef, ...],
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
            *self._types(transformation_refs, "transformation_family", "transformation_proposal"),
            *lens_refs, *assessment_refs, *dilemmas, *agenda,
        )
        package = executor.run(
            self._spec(
                "assemble_decision_package",
                ("transformation_family", "transformation_proposal", "lens_definition", "lens_assessment", "dilemma", "research_question"),
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
        return {"dilemmas": dilemmas, "agenda": agenda, "package": package, "evaluation": evaluation}

    def _research_records(
        self, lens: dict[str, Any], provenance: str, *, node: str,
        run_dir: Path, arm: str,
    ) -> list[dict[str, Any]]:
        problem = self.topic_data["problem_brief"]
        search_prompt = self._header("expert_research", lens["id"]) + f"""
Research the following Hungarian education-policy problem from the disciplinary perspective of {lens['discipline']}.

PUBLIC QUESTION: {problem['public_question']['en']}
PROBLEM: {problem['problem_statement']['en']}

QUESTIONS:
{self._bullets(lens['questions'])}

Use live web search. Return concise English research notes with direct source URLs, dates or scopes where material, contested evidence clearly marked, and no policy recommendation. Separate facts from inference. Four to seven decision-relevant findings are enough.
"""
        notes = self._recover_or_call_search(
            search_prompt, arm=arm, node=node, run_dir=run_dir
        )
        analysis_prompt = self._header("expert_analysis", lens["id"]) + f"""
Convert the live research notes below into an English-only evidence artifact set for this policy problem.

DISCIPLINE: {lens['discipline']}
PUBLIC QUESTION: {problem['public_question']['en']}
CRITERIA: {', '.join(lens['criteria'])}
KNOWN LENS LIMITS: {'; '.join(lens['limitations'])}

RESEARCH NOTES:
{notes}

Rules: preserve contested labels; never invent a source or statistic; findings must be empirical claims rather than recommendations; source_url must be a direct URL when present in the notes, otherwise a short source identifier. Produce 4-7 findings, 1-4 assumptions, and 2-4 uncertainties with concrete reduction paths.
"""
        result = self._call_structured_counted(
            analysis_prompt, contracts.RESEARCH_OUTPUT, role="generator", max_tokens=12000,
            arm=arm, node=node, run_dir=run_dir, suffix="analysis",
            constraints={"findings": (4, 7), "assumptions": (1, 4), "uncertainties": (2, 4)},
        )
        records: list[dict[str, Any]] = []
        assumption_ids = []
        for index, statement in enumerate(result["assumptions"], 1):
            artifact_id = f"A-live-{lens['id']}-{index:02d}"
            assumption_ids.append(artifact_id)
            records.append(self._record(artifact_id, "assumption", provenance, {
                "statement": statement, "domain_tags": [lens["id"]],
                "testability": "partly_testable", "source_context": "Fresh live v2 domain research",
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
                "population": "Population described in the cited finding",
                "context": f"Fresh live research through the {lens['name']} lens",
                "time_scope": "As reported by the cited source",
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
                "population": "Students in learning and educational-sorting contexts",
                "context": "PR #29 curated educational-psychology evidence base",
                "time_scope": "Evidence base admitted to the PR #29 sensitivity test",
                "transferability": "uncertain",
                "limitations": ["Use only within the stated population, domain, and evidence-strength boundary."],
                "assumption_ids": [], "uncertainty_ids": [],
            }))
        records.append(self._record("L-live-educational_psychology", "lens_definition", provenance, {
            "name": lens["name"], "discipline": lens["discipline"],
            "questions": lens["questions"], "criteria": lens["criteria"],
            "limitations": lens["limitations"],
        }))
        return records

    def _transformation_records(
        self, finding_refs: tuple[ArtifactRef, ...], provenance: str, *,
        node: str, run_dir: Path, arm: str,
    ) -> list[dict[str, Any]]:
        findings = [self.repository.get_by_hash(ref.content_hash) for ref in finding_refs]
        digest = "\n".join(
            f"- {record['id']} [{record['content']['evidence_strength']}; {', '.join(record['content']['domain_tags'])}]: {record['content']['claim']}"
            for record in findings
        )
        problem = self.topic_data["problem_brief"]
        prompt = self._header("build_scenarios", "transformation_architect") + f"""
Derive an education-system transformation portfolio from the evidence record below. Work in English only. The final product is a library of change directions, not a debate among experts.

PUBLIC QUESTION: {problem['public_question']['en']}
PROBLEM: {problem['problem_statement']['en']}
SCOPE: {problem['scope']['en']}

EVIDENCE RECORD:
{digest}

Produce 4-6 materially distinct proposals T1..Tn. Include an explicit no-new-policy or passive-change counterfactual when decision-relevant. Every empirical mechanism must cite finding ids. Keep evidence, assumptions, uncertainties, value choices, and implementation steps separate. Do not attribute content to experts. Do not use knowledge outside the supplied findings. Each family may contain one proposal in this first live slice, but its system problem, lever, and boundary must be explicit.
"""
        result = self._call_structured_counted(
            prompt, contracts.transformation_output([ref.id for ref in finding_refs]),
            role="generator", max_tokens=30000, arm=arm, node=node,
            run_dir=run_dir, suffix="generate", constraints={"proposals": (4, 6)},
        )
        proposals = sorted(result["proposals"], key=lambda item: int(item["key"][1:]))
        keys = [item["key"] for item in proposals]
        if len(keys) != len(set(keys)) or keys != [f"T{i}" for i in range(1, len(keys) + 1)]:
            raise ValueError(f"Transformation keys must be sequential and unique: {keys}")
        records: list[dict[str, Any]] = []
        for item in proposals:
            key = item["key"].lower()
            assumption_ids = []
            for index, statement in enumerate(item["assumptions"], 1):
                artifact_id = f"A-live-{key}-{index:02d}"
                assumption_ids.append(artifact_id)
                records.append(self._record(artifact_id, "assumption", provenance, {
                    "statement": statement, "domain_tags": ["transformation_design"],
                    "testability": "partly_testable", "source_context": f"Live proposal {item['key']}",
                }))
            uncertainty_ids = []
            for index, question in enumerate(item["uncertainties"], 1):
                artifact_id = f"U-live-{key}-{index:02d}"
                uncertainty_ids.append(artifact_id)
                records.append(self._record(artifact_id, "uncertainty", provenance, {
                    "question": question, "uncertainty_type": "implementation",
                    "current_confidence": "low", "reduction_path": "Targeted research or a reversible pilot.",
                }))
            proposal_id = f"TP-live-{key}"
            records.append(self._record(proposal_id, "transformation_proposal", provenance, {
                "title": item["title"], "goal": item["goal"], "change_level": item["change_level"],
                "mechanisms": item["mechanisms"], "implementation_steps": item["implementation_steps"],
                "expected_benefits": item["expected_benefits"], "costs": item["costs"],
                "risks": item["risks"], "equity_impact": item["equity_impact"],
                "evidence_status": item["evidence_status"], "finding_refs": item["finding_refs"],
                "assumption_refs": assumption_ids, "uncertainty_refs": uncertainty_ids,
                "origin": "live_generation",
            }))
            records.append(self._record(f"TF-live-{key}", "transformation_family", provenance, {
                "name": item["title"], "system_problem": item["system_problem"],
                "change_lever": item["change_lever"], "boundary": item["boundary"],
                "proposal_refs": [proposal_id],
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
            f"{record['id']} — {record['content']['title']}\nGoal: {record['content']['goal']}\nMechanisms: {'; '.join(record['content']['mechanisms'])}\nRisks: {'; '.join(record['content']['risks'])}\nEvidence: {record['content']['evidence_status']}"
            for record in proposal_records
        )
        evidence_digest = "\n".join(
            f"- {record['id']} [{record['content']['evidence_strength']}]: {record['content']['claim']}"
            for record in finding_records
        )
        note_text = ""
        if evidence_notes:
            note_text = "\nCURATED EVIDENCE BOUNDARIES:\n" + "\n".join(
                f"- [{note['evidence_strength']}] {note['claim']} Source: {note['source']}"
                for note in evidence_notes
            )
        prompt = self._header("synthesis", lens["id"]) + f"""
Apply one reusable scientific lens to every unchanged transformation proposal. The proposal is the object of evaluation; do not simulate a person or attribute authority to a speaker. Work in English only.

LENS: {lens['name']}
DISCIPLINE: {lens['discipline']}
QUESTIONS: {'; '.join(lens['questions'])}
CRITERIA: {'; '.join(lens['criteria'])}
LIMITATIONS: {'; '.join(lens['limitations'])}
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
            f"- {record['id']} / {record['content']['lens_ref']} / {record['content']['verdict']}: {record['content']['assessment']}"
            for record in assessments
        )
        prompt = self._header("argument_map", "dilemma_mapper") + f"""
Identify the decision tensions revealed by the transformation proposals and scientific lens assessments. Work in English only. Distinguish an empirical open question from a value conflict or irreducible trade-off. Evidence may clarify consequences but must not be presented as ranking public values.

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
Build a decision-relevant research agenda from the explicit uncertainties and low-confidence scientific lens assessments. Work in English only. Do not convert value conflicts into fake research questions.

UNCERTAINTIES:
{chr(10).join(f"- {r['id']}: {r['content']['question']}" for r in uncertainties)}

ASSESSMENT SIGNALS:
{chr(10).join(f"- {r['content']['proposal_ref']} / {r['content']['lens_ref']} / {r['content']['confidence']}: {r['content']['assessment']}" for r in assessments if r['content']['confidence'] != 'high')}

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
        node: str, run_dir: Path,
    ) -> list[dict[str, Any]]:
        records = [self.repository.get_by_hash(ref.content_hash) for ref in refs]
        by_type: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            by_type.setdefault(record["record_type"], []).append(record)
        proposal_text = self._compact_proposals(by_type["transformation_proposal"])
        lens_text = "\n".join(
            f"- {r['content']['proposal_ref']} / {r['content']['lens_ref']} / {r['content']['verdict']}: {r['content']['assessment']}"
            for r in by_type["lens_assessment"]
        )
        dilemma_text = "\n".join(f"- {r['content']['title']}: {r['content']['tension']}" for r in by_type["dilemma"])
        agenda_text = "\n".join(f"- {r['content']['question']}" for r in by_type["research_question"])
        treatment_rule = ""
        if arm == "psychology":
            treatment_rule = (
                "The educational-psychology lens is present. If it materially changes "
                "the assessment, explicitly carry its named mechanism (for example "
                "academic self-concept/BFLPE, labeling, motivation, or goal orientation) "
                "into the summary. Do not merely mention the lens name."
            )
        problem = self.topic_data["problem_brief"]
        prompt = self._header("brief", "decision_package_writer") + f"""
Write a concise English decision-package summary for the public question below. The summary must preserve the transformation option space, distinguish empirical uncertainty from value choice, and name material disciplinary mechanisms rather than speakers. Do not choose one winner.

PUBLIC QUESTION: {problem['public_question']['en']}

TRANSFORMATIONS:
{proposal_text}

LENS ASSESSMENTS:
{lens_text}

DILEMMAS:
{dilemma_text}

RESEARCH AGENDA:
{agenda_text}

{treatment_rule}

Write 500-900 words. Explain what can change, the leading mechanism and constraint of each direction, what evidence supports or weakens it, what people must decide, and which research would most change the choice.
"""
        required_terms = (
            "big-fish", "little-pond", "self-concept", "labeling",
            "goal orientation", "self-determination", "motivation",
        ) if arm == "psychology" else ()
        result = self._call_structured_text_checked(
            prompt, contracts.PACKAGE_OUTPUT, field="summary",
            minimum_words=500, maximum_words=900, required_terms=required_terms,
            role="generator", max_tokens=20000, arm=arm, node=node,
            run_dir=run_dir, suffix="package",
        )
        def ids(record_type: str) -> list[str]:
            return sorted(r["id"] for r in by_type.get(record_type, []))
        return [self._record(f"DP-live-{arm}", "decision_package", provenance, {
            "title": problem["title"]["en"], "public_question": problem["public_question"]["en"],
            "summary": result["summary"],
            "transformation_family_refs": ids("transformation_family"),
            "proposal_refs": ids("transformation_proposal"),
            "lens_assessment_refs": ids("lens_assessment"),
            "dilemma_refs": ids("dilemma"), "research_question_refs": ids("research_question"),
            "generation_notice": (
                f"Fresh live v2 {arm} arm. Generator=anthropic; judge=openai. "
                "The psychology treatment is a PR #29 sensitivity test, not registry admission."
            ),
        })]

    def _evaluation_records(
        self, arm: str, package_ref: ArtifactRef, proposals: tuple[ArtifactRef, ...],
        assessments: tuple[ArtifactRef, ...], dilemmas: tuple[ArtifactRef, ...],
        agenda: tuple[ArtifactRef, ...], provenance: str, *, node: str, run_dir: Path,
    ) -> list[dict[str, Any]]:
        package = self.repository.get_by_hash(package_ref.content_hash)
        prompt = self._header("judge_score", "cross_family_evaluator") + f"""
Evaluate this artifact-first decision package on six dimensions from 0 to 10. You are the judge family and must evaluate the generator's output, not rewrite it. Work in English only.

PACKAGE SUMMARY:
{package['content']['summary']}

STRUCTURAL COUNTS: proposals={len(proposals)}, lens_assessments={len(assessments)}, dilemmas={len(dilemmas)}, research_questions={len(agenda)}.

Rubric:
- artifact_integrity: typed separation and traceable references;
- evidence_discipline: facts, assumptions, uncertainty, and values remain distinct;
- transformation_specificity: mechanisms and implementation are concrete;
- lens_traceability: disciplinary judgments and their limits survive into the package;
- dilemma_clarity: evidence boundaries and human value choices are explicit;
- decision_usefulness: the package accelerates a real decision without manufacturing consensus.

Score only what is visible. Note missing evidence edges or generic prose as concerns. In the psychology arm, do not award points merely because an extra lens exists; score whether its substantive mechanism is carried and decision-relevant.
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

    def compare_arms(self) -> dict[str, Any]:
        baseline = self._load(self._arm_summary("baseline"))
        psychology = self._load(self._arm_summary("psychology"))
        base_package = self.repository.get_current(baseline["package_ref"])
        psych_package = self.repository.get_current(psychology["package_ref"])
        psych_assessments = self.repository.list(record_type="lens_assessment", topic=self.topic)
        psych_assessments = [r for r in psych_assessments if r["content"]["lens_ref"] == "L-live-educational_psychology"]
        keywords = ["big-fish", "little-pond", "self-concept", "label", "stereotype", "motivation", "goal orientation", "psycholog"]
        assessment_text = " ".join(r["content"]["assessment"] for r in psych_assessments).lower()
        package_text = psych_package["content"]["summary"].lower()
        comparison = {
            "architecture_version": VERSION,
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
        return {
            "arm": arm, "run_id": f"live-{self.topic}-{arm}",
            "package_ref": package_ref.id, "evaluation_ref": evaluation_ref.id,
            "evaluation": evaluation, "counts": counts,
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
            prompt, role="generator", max_tokens=8000, web_search=True,
            arm=arm, node=node, run_dir=run_dir, suffix="search"
        )

    def _call_structured(
        self, prompt: str, schema: dict[str, Any], *, role: str,
        max_tokens: int, arm: str, node: str, run_dir: Path, suffix: str,
    ) -> dict[str, Any]:
        self._persist_prompt(run_dir, node, suffix, prompt)
        marker = self.llm.call_log_len()
        try:
            return self.llm.call_structured(
                prompt, schema, role, max_tokens=max_tokens
            )
        finally:
            self._record_calls(marker, arm=arm, node=node)

    def _call_structured_counted(
        self, prompt: str, schema: dict[str, Any], *, role: str,
        max_tokens: int, arm: str, node: str, run_dir: Path, suffix: str,
        constraints: dict[str, tuple[int, int]], retries: int = 2,
    ) -> dict[str, Any]:
        current_prompt = prompt
        for attempt in range(retries + 1):
            attempt_suffix = suffix if attempt == 0 else f"{suffix}-semantic-retry-{attempt}"
            result = self._call_structured(
                current_prompt, schema, role=role, max_tokens=max_tokens,
                arm=arm, node=node, run_dir=run_dir, suffix=attempt_suffix,
            )
            violations = []
            for field, (minimum, maximum) in constraints.items():
                count = len(result.get(field, []))
                if not minimum <= count <= maximum:
                    violations.append(
                        f"{field} requires {minimum}-{maximum} items, got {count}"
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
                "\n\nSTRICT CARDINALITY REPAIR: The previous complete response was rejected: "
                + "; ".join(violations)
                + ". Generate a complete replacement, obeying every requested range exactly."
            )
        raise ValueError(
            f"{node} failed semantic cardinality after {retries + 1} attempts"
        )

    def _call_structured_text_checked(
        self, prompt: str, schema: dict[str, Any], *, field: str,
        minimum_words: int, maximum_words: int, required_terms: tuple[str, ...],
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
            text = result.get(field, "")
            word_count = len(text.split())
            violations = []
            if not minimum_words <= word_count <= maximum_words:
                violations.append(
                    f"{field} requires {minimum_words}-{maximum_words} words, got {word_count}"
                )
            normalized = text.lower()
            if required_terms and not any(term in normalized for term in required_terms):
                violations.append(
                    f"{field} must carry at least one named mechanism from: "
                    + ", ".join(required_terms)
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
        if not path.exists():
            path.write_text(prompt, encoding="utf-8")

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
            "schema_version": VERSION, "topic": self.topic, "status": "candidate",
            "content": content, "provenance_ref": provenance,
            "created_at": self.created_at, "supersedes": None,
        }

    def _experiment_created_at(self) -> str:
        path = self.output_root / "experiment_config.json"
        if path.exists():
            return self._load(path)["created_at"]
        created_at = _now()
        write_json(path, {
            "architecture_version": VERSION, "created_at": created_at,
            "generator_provider": self.provider_generator if hasattr(self, "provider_generator") else "anthropic",
            "judge_provider": self.provider_judge if hasattr(self, "provider_judge") else "openai",
            "topic": self.topic,
        })
        return created_at

    @staticmethod
    def _header(task: str, agent: str) -> str:
        return f"TASK: {task}\nAGENT: {agent}\nLANG: en\n\n"

    @staticmethod
    def _bullets(items: Iterable[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    @classmethod
    def _contract_hash(cls, name: str) -> str:
        """Hash the exact node implementation and provider contract.

        The live runner used to hash only a hand-maintained label while every
        generative node declared the complete experiment module as a spec
        dependency. That combination was both too broad and too easy to leave
        stale. This map makes the dependency executable and node-local.
        """

        dependencies = {
            "research_v1": (cls._research_records, contracts.RESEARCH_OUTPUT),
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
        value = value.strip().rstrip(".,)")
        if urlsplit(value).scheme in {"http", "https"}:
            return value
        return f"urn:epl:live-source:{_slug(fallback_id)}"

    @staticmethod
    def _types(refs: Iterable[ArtifactRef], *record_types: str) -> tuple[ArtifactRef, ...]:
        allowed = set(record_types)
        return tuple(ref for ref in refs if ref.record_type in allowed)

    @staticmethod
    def _compact_proposals(records: list[dict[str, Any]]) -> str:
        return "\n\n".join(
            f"{r['id']} — {r['content']['title']}\nGoal: {r['content']['goal']}\nMechanisms: {'; '.join(r['content']['mechanisms'])}\nEvidence: {r['content']['evidence_status']}\nRisks: {'; '.join(r['content']['risks'])}"
            for r in records
        )

    def _arm_summary(self, arm: str) -> Path:
        return self.output_root / "runs" / f"live-{self.topic}-{arm}" / "arm_summary.json"

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))
