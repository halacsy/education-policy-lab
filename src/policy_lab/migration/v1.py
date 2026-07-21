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
from policy_lab.i18n import BILINGUAL_VERSION, is_localized_text, localized, text
from policy_lab.schema_registry import SchemaRegistry
from policy_lab.store import ArtifactRef, ArtifactRepository

CREATED_AT = "2026-07-20T00:00:00Z"
VERSION = BILINGUAL_VERSION


def _english(value: Any, default: str = "Not specified in the v1 corpus.") -> str:
    if isinstance(value, dict):
        return str(value.get("en") or default).strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _language(
    value: Any,
    language: str,
    default: str = "Not specified in the v1 corpus.",
) -> str:
    if is_localized_text(value):
        return text(value, language).strip()
    if isinstance(value, dict):
        candidate = value.get(language) or value.get("en") or value.get("hu")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _pair(
    value: Any,
    default_en: str = "Not specified in the v1 corpus.",
    default_hu: str = "A v1 korpuszban nincs megadva.",
) -> dict[str, str]:
    """Preserve native v1 pairs; citations/proper names may be language-neutral."""

    return localized(
        _language(value, "en", default_en),
        _language(value, "hu", default_hu),
    )


def _joined_pairs(values: Iterable[Any], separator: str = "; ") -> dict[str, str]:
    values = list(values)
    return localized(
        separator.join(_language(value, "en") for value in values),
        separator.join(_language(value, "hu") for value in values),
    )


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
            schema_files=(
                *(f"schemas/v2/{name}" for name in schemas),
                "schemas/v2/bilingual.schema.json",
                "config/v2/bilingual_fields.json",
            ),
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
                        "statement": _pair(item), "domain_tags": [domain],
                        "testability": "partly_testable",
                        "source_context": localized(
                            f"Migrated from v1 expert output: {expert_id}",
                            f"A v1 szakértői kimenetéből átemelve: {expert_id}",
                        ),
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
                        "question": _pair(item.get("text", item)),
                        "uncertainty_type": "unknown",
                        "current_confidence": confidence,
                        "reduction_path": _pair(item.get("reduced_by")),
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
                            "title": localized(source_text, source_text),
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
                        "claim": _pair(finding.get("claim")), "kind": "fact",
                        "domain_tags": [domain], "evidence_strength": strength,
                        "source_refs": [source_id],
                        "population": localized(
                            "Population described in the migrated claim",
                            "Az átemelt állításban leírt populáció",
                        ),
                        "context": _pair(output.get("position")),
                        "time_scope": localized(
                            "As reported in the v1 source corpus",
                            "A v1 forráskorpusz közlése szerint",
                        ),
                        "transferability": "uncertain",
                        "limitations": [
                            localized(
                                "The v1 source string was not re-verified during migration.",
                                "A v1 forrásszöveget a migráció során nem ellenőriztük újra.",
                            )
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
                        "statement": _pair(item),
                        "domain_tags": ["transformation_design"],
                        "testability": "partly_testable",
                        "source_context": localized(
                            f"Migrated from v1 scenario {sid}",
                            f"A(z) {sid} v1 forgatókönyvből átemelve",
                        ),
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
                        "question": _pair(item),
                        "uncertainty_type": "implementation",
                        "current_confidence": "low",
                        "reduction_path": localized(
                            "Targeted research or a reversible pilot.",
                            "Célzott kutatás vagy visszafordítható pilot.",
                        ),
                    },
                ))
            proposal_id = f"TP-{topic}-{sid.lower()}"
            title = _english(scenario.get("title"))
            records.append(_record(
                artifact_id=proposal_id, record_type="transformation_proposal",
                topic=topic, provenance_ref=provenance,
                content={
                    "title": _pair(scenario.get("title")),
                    "goal": _pair(scenario.get("goal")),
                    "change_level": self._change_level(title),
                    "mechanisms": [
                        _pair(item.get("text", item))
                        for item in scenario.get("mechanism", [])
                    ],
                    "implementation_steps": [
                        {"actor": _pair(step.get("actor")),
                         "action": _pair(step.get("action")),
                         "timeline": _pair(step.get("timeline"))}
                        for step in scenario.get("implementation_steps", [])
                    ],
                    "expected_benefits": [
                        _pair(item.get("text", item))
                        for item in scenario.get("expected_benefits", [])
                    ],
                    "costs": [_pair(item) for item in scenario.get("cost_categories", [])],
                    "risks": [_pair(item) for item in scenario.get("political_risks", [])],
                    "equity_impact": _pair(scenario.get("equity_impact")),
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
                    "name": _pair(scenario.get("title")),
                    "system_problem": _pair(scenario.get("goal")),
                    "change_lever": _joined_pairs(
                        item.get("text", item)
                        for item in scenario.get("mechanism", [])[:2]
                    ),
                    "boundary": _pair(
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
                    "name": localized(
                        expert_id.replace("_", " ").title(),
                        expert_id.replace("_", " ").title(),
                    ),
                    "discipline": localized(
                        expert_id.replace("_", " "),
                        expert_id.replace("_", " "),
                    ),
                    "questions": [
                        localized(
                            f"What does {expert_id.replace('_', ' ')} reveal about this change?",
                            f"Mit mutat meg a(z) {expert_id.replace('_', ' ')} nézőpont erről a változásról?",
                        ),
                        localized(
                            "Which effects, limits, and implementation conditions matter?",
                            "Mely hatások, korlátok és megvalósítási feltételek lényegesek?",
                        ),
                    ],
                    "criteria": [
                        localized("Evidence fit", "Bizonyítékok illeszkedése"),
                        localized("Expected effects", "Várható hatások"),
                        localized("Feasibility", "Megvalósíthatóság"),
                    ],
                    "limitations": [
                        localized(
                            "This lens definition is inferred from a v1 expert role.",
                            "Ezt a nézőpont-definíciót egy v1 szakértői szerepből vezettük le.",
                        )
                    ],
                },
            ))
            expert_findings = [
                artifact_id for artifact_id in finding_ids
                if f"-{expert_id}-" in artifact_id
            ]
            strengths = [
                _pair(item.get("claim")) for item in output.get("findings", [])[:2]
            ] or [localized(
                "No explicit strength was extractable from the v1 record.",
                "A v1 rekordból nem volt kinyerhető kifejezett erősség.",
            )]
            weaknesses = [
                _pair(item.get("text", item))
                for item in output.get("uncertainties", [])[:2]
            ] or [localized(
                "The v1 record did not state a lens-specific limitation.",
                "A v1 rekord nem jelölt meg nézőpont-specifikus korlátot.",
            )]
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
                        "assessment": localized(
                            f"Migrated lens reading for '{_language(scenario['title'], 'en')}'. "
                            f"{_language(output.get('position'), 'en')}",
                            f"Átemelt nézőpontértékelés ehhez: „{_language(scenario['title'], 'hu')}”. "
                            f"{_language(output.get('position'), 'hu')}",
                        ),
                        "strengths": strengths,
                        "weaknesses": weaknesses,
                        "opportunities": [
                            _pair(item.get("text", item))
                            for item in scenario.get("expected_benefits", [])[:2]
                        ] or [localized(
                            "No explicit opportunity was extractable.",
                            "Nem volt kinyerhető kifejezett lehetőség.",
                        )],
                        "threats": [
                            _pair(item) for item in scenario.get("political_risks", [])[:2]
                        ] or [localized(
                            "No explicit threat was extractable.",
                            "Nem volt kinyerhető kifejezett veszély.",
                        )],
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
            value_hu = _language(cluster.get("value"), "hu")
            poles = re.split(r"\s+(?:versus|vs\.?|against)\s+", value, maxsplit=1,
                             flags=re.IGNORECASE)
            poles_hu = re.split(r"\s+(?:kontra|szemben|vagy)\s+", value_hu, maxsplit=1,
                                flags=re.IGNORECASE)
            if len(poles) < 2:
                poles = [value, "A competing public value requiring human judgment"]
            if len(poles_hu) < 2:
                poles_hu = [value_hu, "Emberi mérlegelést igénylő versengő közérték"]
            scenario_id = cluster.get("scenario", "S1")
            dilemma_type = response if response in {
                "value_conflict", "irreducible_tradeoff"
            } else ("value_conflict" if kind == "value" else "mixed")
            records.append(_record(
                artifact_id=f"D-{topic}-{cluster['id'].lower()}",
                record_type="dilemma", topic=topic, provenance_ref=provenance,
                content={
                    "title": localized(
                        f"Decision tension {cluster['id']}: {scenario_id}",
                        f"Döntési feszültség {cluster['id']}: {scenario_id}",
                    ),
                    "tension": _pair(cluster.get("claim")),
                    "dilemma_type": dilemma_type,
                    "value_poles": [
                        localized(en.strip(), hu.strip())
                        for en, hu in zip(poles[:2], poles_hu[:2])
                    ],
                    "affected_groups": [
                        _pair(item) for item in cluster.get("affected", [])
                    ],
                    "decision_question": _pair(cluster.get("value")),
                    "evidence_boundary": _pair(
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
                    "question": _pair(item),
                    "why_it_matters": localized(
                        "It can change the comparison of transformation choices.",
                        "Megváltoztathatja az átalakítási lehetőségek összehasonlítását.",
                    ),
                    "method": localized(
                        "Use the study or pilot design stated in the migrated v1 research agenda.",
                        "Az átemelt v1 kutatási agendában megjelölt vizsgálati vagy pilottervet kell használni.",
                    ),
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
                "title": _pair(problem.get("title")),
                "public_question": _pair(problem.get("public_question")),
                "summary": _pair(brief.get("intro")),
                "transformation_family_refs": ids("transformation_family"),
                "proposal_refs": ids("transformation_proposal"),
                "lens_assessment_refs": ids("lens_assessment"),
                "dilemma_refs": ids("dilemma"),
                "research_question_refs": ids("research_question"),
                "migration_notice": localized(
                    "Deterministically compiled from committed v1 artifacts; no "
                    "claims or assessments were re-researched during migration.",
                    "Rögzített v1 artifaktokból determinisztikusan összeállítva; "
                    "a migráció során egyetlen állítást vagy értékelést sem kutattunk újra.",
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
