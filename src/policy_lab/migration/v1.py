"""Compile a v1 round into the v2 artifact graph without inventing evidence."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from policy_lab.dag import NodeExecutor, NodeSpec
from policy_lab.jsonio import write_json
from policy_lab.schema_registry import SchemaRegistry
from policy_lab.store import ArtifactRef, ArtifactRepository

CREATED_AT = "2026-07-20T00:00:00Z"
VERSION = "2.0.0"


def _english(value: Any, default: str = "Not specified in the v1 corpus.") -> str:
    if isinstance(value, dict):
        return str(value.get("en") or default).strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-")
    return normalized or "record"


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:14]


def _record(
    *, artifact_id: str, record_type: str, topic: str, content: dict[str, Any],
    provenance_ref: str,
) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "record_type": record_type,
        "schema_version": VERSION,
        "topic": topic,
        "status": "candidate",
        "content": content,
        "provenance_ref": provenance_ref,
        "created_at": CREATED_AT,
        "supersedes": None,
    }


class V1CorpusCompiler:
    """Produce an honest v2 vertical slice from already-committed v1 outputs."""

    def __init__(self, root: str | Path, output_root: str | Path):
        self.root = Path(root)
        self.output_root = Path(output_root)
        self.schemas = SchemaRegistry(self.root / "schemas" / "v2")
        self.repository = ArtifactRepository(self.output_root, self.schemas)

    def compile_topic(self, topic: str, round_name: str) -> dict[str, Any]:
        topic_path = self.root / "topics" / topic / "topic.json"
        round_path = (
            self.root / "outputs" / "topics" / topic / "iterations" / round_name
        )
        topic_data = self._load(topic_path)
        scenarios = self._load(round_path / "scenarios.json")["scenarios"]
        brief = self._load(round_path / "brief.json")
        clusters = self._load(round_path / "discourse" / "argument_map.json")[
            "clusters"
        ]
        experts = {
            path.stem: self._load(path)
            for path in sorted((round_path / "expert_outputs").glob("*.json"))
        }
        run_id = f"migration-{topic}"
        run_dir = self.output_root / "runs" / run_id
        executor = NodeExecutor(
            repository=self.repository,
            run_dir=run_dir,
            source_root=self.root,
            run_id=run_id,
            artifact_created_at=CREATED_AT,
        )
        config = {"source_round": round_name, "topic": topic}

        evidence_refs = executor.run(
            self._spec(
                "import_v1_evidence", (),
                ("source", "assumption", "uncertainty", "finding"),
                ("source.schema.json", "assumption.schema.json",
                 "uncertainty.schema.json", "finding.schema.json"),
            ),
            inputs={}, relevant_config=config,
            builder=lambda pv: self._evidence_records(topic, experts, pv),
        )
        transformation_refs = executor.run(
            self._spec(
                "compile_transformations",
                ("finding", "assumption", "uncertainty"),
                ("assumption", "uncertainty", "transformation_proposal",
                 "transformation_family"),
                ("assumption.schema.json", "uncertainty.schema.json",
                 "transformation_proposal.schema.json",
                 "transformation_family.schema.json"),
            ),
            inputs={"evidence": self._types(
                evidence_refs, "finding", "assumption", "uncertainty"
            )},
            relevant_config=config,
            builder=lambda pv: self._transformation_records(
                topic, scenarios, evidence_refs, pv
            ),
        )
        lens_refs = executor.run(
            self._spec(
                "apply_scientific_lenses",
                ("finding", "transformation_proposal"),
                ("lens_definition", "lens_assessment"),
                ("lens_definition.schema.json", "lens_assessment.schema.json"),
            ),
            inputs={
                "findings": self._types(evidence_refs, "finding"),
                "proposals": self._types(
                    transformation_refs, "transformation_proposal"
                ),
            },
            relevant_config=config,
            builder=lambda pv: self._lens_records(
                topic, experts, scenarios, evidence_refs, pv
            ),
        )
        dilemma_refs = executor.run(
            self._spec(
                "identify_decision_dilemmas",
                ("finding", "transformation_proposal"), ("dilemma",),
                ("dilemma.schema.json",),
            ),
            inputs={
                "findings": self._types(evidence_refs, "finding"),
                "proposals": self._types(
                    transformation_refs, "transformation_proposal"
                ),
            },
            relevant_config=config,
            builder=lambda pv: self._dilemma_records(
                topic, clusters, brief, evidence_refs, pv
            ),
        )
        research_refs = executor.run(
            self._spec(
                "build_research_agenda",
                ("uncertainty", "transformation_proposal"),
                ("research_question",), ("research_question.schema.json",),
            ),
            inputs={
                "uncertainties": self._types(
                    (*evidence_refs, *transformation_refs), "uncertainty"
                ),
                "proposals": self._types(
                    transformation_refs, "transformation_proposal"
                ),
            },
            relevant_config=config,
            builder=lambda pv: self._research_records(
                topic, brief, (*evidence_refs, *transformation_refs), pv
            ),
        )
        package_inputs = self._types(
            (*transformation_refs, *lens_refs, *dilemma_refs, *research_refs),
            "transformation_family", "transformation_proposal",
            "lens_definition", "lens_assessment", "dilemma",
            "research_question",
        )
        package_refs = executor.run(
            self._spec(
                "assemble_decision_package",
                ("transformation_family", "transformation_proposal",
                 "lens_definition", "lens_assessment", "dilemma",
                 "research_question"),
                ("decision_package",), ("decision_package.schema.json",),
            ),
            inputs={"package_parts": package_inputs},
            relevant_config=config,
            builder=lambda pv: self._package_records(
                topic, topic_data, brief, package_inputs, pv
            ),
        )
        root_ids = tuple(ref.id for ref in package_refs)
        self.repository.validate_graph(root_ids)
        all_topic_records = self.repository.list(topic=topic)
        counts = Counter(record["record_type"] for record in all_topic_records)
        manifest = {
            "architecture_version": VERSION,
            "artifact_counts": dict(sorted(counts.items())),
            "decision_package_refs": [ref.id for ref in package_refs],
            "honesty_notice": (
                "This vertical slice deterministically restructures committed v1 "
                "content. It is not a new research or model-generation run."
            ),
            "run_id": run_id,
            "source_round": str(round_path.relative_to(self.root)),
            "source_topic": str(topic_path.relative_to(self.root)),
            "topic": topic,
        }
        write_json(run_dir / "run_manifest.json", manifest)
        return manifest

    def _spec(
        self, name: str, inputs: tuple[str, ...], outputs: tuple[str, ...],
        schemas: tuple[str, ...],
    ) -> NodeSpec:
        return NodeSpec(
            name=name, version="1.0.0", input_types=inputs,
            output_types=outputs,
            schema_files=tuple(f"schemas/v2/{name}" for name in schemas),
            config_keys=("source_round", "topic"), role="deterministic",
        )

    def _evidence_records(
        self, topic: str, experts: dict[str, dict], provenance: str
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        sources: dict[str, str] = {}
        for expert_id, output in experts.items():
            domain = expert_id
            assumption_ids = []
            for index, item in enumerate(output.get("assumptions", []), 1):
                artifact_id = f"A-{topic}-{domain}-{index:02d}"
                assumption_ids.append(artifact_id)
                records.append(_record(
                    artifact_id=artifact_id, record_type="assumption", topic=topic,
                    provenance_ref=provenance,
                    content={
                        "statement": _english(item), "domain_tags": [domain],
                        "testability": "partly_testable",
                        "source_context": f"Migrated from v1 expert output: {expert_id}",
                    },
                ))
            uncertainty_ids = []
            for index, item in enumerate(output.get("uncertainties", []), 1):
                artifact_id = f"U-{topic}-{domain}-{index:02d}"
                uncertainty_ids.append(artifact_id)
                confidence = str(item.get("confidence", "unknown"))
                if confidence not in {"high", "medium", "low", "unknown"}:
                    confidence = "unknown"
                records.append(_record(
                    artifact_id=artifact_id, record_type="uncertainty", topic=topic,
                    provenance_ref=provenance,
                    content={
                        "question": _english(item.get("text", item)),
                        "uncertainty_type": "unknown",
                        "current_confidence": confidence,
                        "reduction_path": _english(item.get("reduced_by")),
                    },
                ))
            for index, finding in enumerate(output.get("findings", []), 1):
                source_text = str(finding.get("source") or "Unspecified v1 source")
                source_key = _short_hash(source_text)
                source_id = f"SRC-{topic}-{source_key}"
                if source_id not in sources:
                    sources[source_id] = source_text
                    url_match = re.search(r"https?://[^\s;]+", source_text)
                    records.append(_record(
                        artifact_id=source_id, record_type="source", topic=topic,
                        provenance_ref=provenance,
                        content={
                            "title": source_text,
                            "url": url_match.group(0).rstrip(".,)") if url_match
                            else f"urn:epl:v1-source:{source_key}",
                            "source_type": "web_page" if url_match else "report",
                            "license_status": "public_pointer_only" if url_match
                            else "unknown",
                            "accessed_at": CREATED_AT,
                        },
                    ))
                strength = str(finding.get("evidence", "weak"))
                if strength not in {"strong", "moderate", "weak", "contested"}:
                    strength = "weak"
                records.append(_record(
                    artifact_id=f"F-{topic}-{domain}-{index:02d}",
                    record_type="finding", topic=topic,
                    provenance_ref=provenance,
                    content={
                        "claim": _english(finding.get("claim")), "kind": "fact",
                        "domain_tags": [domain], "evidence_strength": strength,
                        "source_refs": [source_id],
                        "population": "Population described in the migrated claim",
                        "context": _english(output.get("position")),
                        "time_scope": "As reported in the v1 source corpus",
                        "transferability": "uncertain",
                        "limitations": [
                            "The v1 source string was not re-verified during migration."
                        ],
                        "assumption_ids": assumption_ids,
                        "uncertainty_ids": uncertainty_ids,
                    },
                ))
        return records

    def _transformation_records(
        self, topic: str, scenarios: list[dict], evidence: Iterable[ArtifactRef],
        provenance: str,
    ) -> list[dict[str, Any]]:
        records = []
        finding_ids = [ref.id for ref in evidence if ref.record_type == "finding"]
        for scenario in scenarios:
            sid = scenario["id"]
            assumption_ids = []
            for index, item in enumerate(scenario.get("assumptions", []), 1):
                artifact_id = f"A-{topic}-{sid.lower()}-{index:02d}"
                assumption_ids.append(artifact_id)
                records.append(_record(
                    artifact_id=artifact_id, record_type="assumption", topic=topic,
                    provenance_ref=provenance,
                    content={
                        "statement": _english(item),
                        "domain_tags": ["transformation_design"],
                        "testability": "partly_testable",
                        "source_context": f"Migrated from v1 scenario {sid}",
                    },
                ))
            uncertainty_ids = []
            for index, item in enumerate(scenario.get("uncertainties", []), 1):
                artifact_id = f"U-{topic}-{sid.lower()}-{index:02d}"
                uncertainty_ids.append(artifact_id)
                records.append(_record(
                    artifact_id=artifact_id, record_type="uncertainty", topic=topic,
                    provenance_ref=provenance,
                    content={
                        "question": _english(item),
                        "uncertainty_type": "implementation",
                        "current_confidence": "low",
                        "reduction_path": "Targeted research or a reversible pilot.",
                    },
                ))
            proposal_id = f"TP-{topic}-{sid.lower()}"
            title = _english(scenario.get("title"))
            records.append(_record(
                artifact_id=proposal_id, record_type="transformation_proposal",
                topic=topic, provenance_ref=provenance,
                content={
                    "title": title, "goal": _english(scenario.get("goal")),
                    "change_level": self._change_level(title),
                    "mechanisms": [
                        _english(item.get("text", item))
                        for item in scenario.get("mechanism", [])
                    ],
                    "implementation_steps": [
                        {"actor": _english(step.get("actor")),
                         "action": _english(step.get("action")),
                         "timeline": _english(step.get("timeline"))}
                        for step in scenario.get("implementation_steps", [])
                    ],
                    "expected_benefits": [
                        _english(item.get("text", item))
                        for item in scenario.get("expected_benefits", [])
                    ],
                    "costs": [_english(item) for item in scenario.get("cost_categories", [])],
                    "risks": [_english(item) for item in scenario.get("political_risks", [])],
                    "equity_impact": _english(scenario.get("equity_impact")),
                    "evidence_status": scenario.get("evidence_status", {}).get(
                        "label", "unknown"
                    ),
                    "finding_refs": finding_ids,
                    "assumption_refs": assumption_ids,
                    "uncertainty_refs": uncertainty_ids,
                    "legacy_scenario_id": sid,
                },
            ))
            records.append(_record(
                artifact_id=f"TF-{topic}-{sid.lower()}",
                record_type="transformation_family", topic=topic,
                provenance_ref=provenance,
                content={
                    "name": title,
                    "system_problem": _english(scenario.get("goal")),
                    "change_lever": "; ".join(
                        _english(item.get("text", item))
                        for item in scenario.get("mechanism", [])[:2]
                    ),
                    "boundary": _english(
                        scenario.get("evidence_status", {}).get("note")
                    ),
                    "proposal_refs": [proposal_id],
                },
            ))
        return records

    def _lens_records(
        self, topic: str, experts: dict[str, dict], scenarios: list[dict],
        evidence: Iterable[ArtifactRef], provenance: str,
    ) -> list[dict[str, Any]]:
        records = []
        finding_ids = [ref.id for ref in evidence if ref.record_type == "finding"]
        for expert_id, output in experts.items():
            lens_id = f"L-{topic}-{expert_id}"
            records.append(_record(
                artifact_id=lens_id, record_type="lens_definition", topic=topic,
                provenance_ref=provenance,
                content={
                    "name": expert_id.replace("_", " ").title(),
                    "discipline": expert_id.replace("_", " "),
                    "questions": [
                        f"What does {expert_id.replace('_', ' ')} reveal about this change?",
                        "Which effects, limits, and implementation conditions matter?",
                    ],
                    "criteria": ["Evidence fit", "Expected effects", "Feasibility"],
                    "limitations": [
                        "This lens definition is inferred from a v1 expert role."
                    ],
                },
            ))
            expert_findings = [
                artifact_id for artifact_id in finding_ids
                if f"-{expert_id}-" in artifact_id
            ]
            strengths = [
                _english(item.get("claim")) for item in output.get("findings", [])[:2]
            ] or ["No explicit strength was extractable from the v1 record."]
            weaknesses = [
                _english(item.get("text", item))
                for item in output.get("uncertainties", [])[:2]
            ] or ["The v1 record did not state a lens-specific limitation."]
            for scenario in scenarios:
                status = scenario.get("evidence_status", {}).get("label", "unknown")
                verdict = {
                    "strong": "supports_with_conditions", "moderate": "supports_with_conditions",
                    "weak": "insufficient_evidence", "contested": "cautions",
                }.get(status, "neutral")
                sid = scenario["id"]
                records.append(_record(
                    artifact_id=f"AS-{topic}-{sid.lower()}-{expert_id}",
                    record_type="lens_assessment", topic=topic,
                    provenance_ref=provenance,
                    content={
                        "proposal_ref": f"TP-{topic}-{sid.lower()}",
                        "lens_ref": lens_id,
                        "assessment": (
                            f"Migrated lens reading for '{_english(scenario['title'])}'. "
                            f"{_english(output.get('position'))}"
                        ),
                        "strengths": strengths,
                        "weaknesses": weaknesses,
                        "opportunities": [
                            _english(item.get("text", item))
                            for item in scenario.get("expected_benefits", [])[:2]
                        ] or ["No explicit opportunity was extractable."],
                        "threats": [
                            _english(item) for item in scenario.get("political_risks", [])[:2]
                        ] or ["No explicit threat was extractable."],
                        "verdict": verdict,
                        "confidence": "high" if status == "strong" else (
                            "medium" if status == "moderate" else "low"
                        ),
                        "finding_refs": expert_findings,
                    },
                ))
        return records

    def _dilemma_records(
        self, topic: str, clusters: list[dict], brief: dict,
        evidence: Iterable[ArtifactRef], provenance: str,
    ) -> list[dict[str, Any]]:
        records = []
        response_types = {
            item["cluster_id"]: item.get("response_type")
            for item in brief.get("stakeholder_responses", [])
        }
        finding_ids = [ref.id for ref in evidence if ref.record_type == "finding"][:8]
        for cluster in clusters:
            kind = cluster.get("kind", "mixed")
            response = response_types.get(cluster["id"])
            if kind not in {"value", "mixed"} and response not in {
                "value_conflict", "irreducible_tradeoff"
            }:
                continue
            value = _english(cluster.get("value"))
            poles = re.split(r"\s+(?:versus|vs\.?|against)\s+", value, maxsplit=1,
                             flags=re.IGNORECASE)
            if len(poles) < 2:
                poles = [value, "A competing public value requiring human judgment"]
            scenario_id = cluster.get("scenario", "S1")
            dilemma_type = response if response in {
                "value_conflict", "irreducible_tradeoff"
            } else ("value_conflict" if kind == "value" else "mixed")
            records.append(_record(
                artifact_id=f"D-{topic}-{cluster['id'].lower()}",
                record_type="dilemma", topic=topic, provenance_ref=provenance,
                content={
                    "title": f"Decision tension {cluster['id']}: {scenario_id}",
                    "tension": _english(cluster.get("claim")),
                    "dilemma_type": dilemma_type,
                    "value_poles": [pole.strip() for pole in poles[:2]],
                    "affected_groups": [
                        _english(item) for item in cluster.get("affected", [])
                    ],
                    "decision_question": _english(cluster.get("value")),
                    "evidence_boundary": _english(
                        cluster.get("empirical_uncertainty")
                    ),
                    "proposal_refs": [f"TP-{topic}-{scenario_id.lower()}"],
                    "finding_refs": finding_ids,
                    "legacy_cluster_id": cluster["id"],
                },
            ))
        return records

    def _research_records(
        self, topic: str, brief: dict, artifacts: Iterable[ArtifactRef],
        provenance: str,
    ) -> list[dict[str, Any]]:
        uncertainty_ids = [
            ref.id for ref in artifacts if ref.record_type == "uncertainty"
        ]
        records = []
        for index, item in enumerate(brief.get("what_research_could_resolve", []), 1):
            question = _english(item)
            mentioned = sorted(set(re.findall(r"\bS([1-9][0-9]*)\b", question)))
            proposals = [f"TP-{topic}-s{number}" for number in mentioned]
            if not proposals:
                proposals = [f"TP-{topic}-s1"]
            records.append(_record(
                artifact_id=f"RQ-{topic}-{index:02d}",
                record_type="research_question", topic=topic,
                provenance_ref=provenance,
                content={
                    "question": question,
                    "why_it_matters": "It can change the comparison of transformation choices.",
                    "method": "Use the study or pilot design stated in the migrated v1 research agenda.",
                    "decision_impact": "high" if index <= 3 else "medium",
                    "answerability": "requires_pilot" if "pilot" in question.lower()
                    else "requires_new_data",
                    "proposal_refs": proposals,
                    "uncertainty_refs": uncertainty_ids[:3],
                },
            ))
        return records

    def _package_records(
        self, topic: str, topic_data: dict, brief: dict,
        artifacts: Iterable[ArtifactRef], provenance: str,
    ) -> list[dict[str, Any]]:
        def ids(record_type: str) -> list[str]:
            return sorted(ref.id for ref in artifacts if ref.record_type == record_type)

        problem = topic_data.get("problem_brief", {})
        return [_record(
            artifact_id=f"DP-{topic}-v1-migration",
            record_type="decision_package", topic=topic,
            provenance_ref=provenance,
            content={
                "title": _english(problem.get("title")),
                "public_question": _english(problem.get("public_question")),
                "summary": _english(brief.get("intro")),
                "transformation_family_refs": ids("transformation_family"),
                "proposal_refs": ids("transformation_proposal"),
                "lens_assessment_refs": ids("lens_assessment"),
                "dilemma_refs": ids("dilemma"),
                "research_question_refs": ids("research_question"),
                "migration_notice": (
                    "Deterministically compiled from committed v1 artifacts; no "
                    "claims or assessments were re-researched during migration."
                ),
            },
        )]

    @staticmethod
    def _change_level(title: str) -> str:
        lower = title.lower()
        if any(word in lower for word in ("structural", "system", "national")):
            return "system"
        if any(word in lower for word in ("network", "supply", "consolidation")):
            return "network"
        if any(word in lower for word in ("admission", "regulation", "framework")):
            return "governance"
        return "organization"

    @staticmethod
    def _types(refs: Iterable[ArtifactRef], *types: str) -> tuple[ArtifactRef, ...]:
        allowed = set(types)
        return tuple(ref for ref in refs if ref.record_type in allowed)

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))
