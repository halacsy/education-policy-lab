from __future__ import annotations

import unittest
from pathlib import Path

from policy_lab.coverage import CoverageValidationError, validate_exact_coverage
from policy_lab.schema_registry import SchemaRegistry
from policy_lab.live.contracts import transformation_output


ROOT = Path(__file__).resolve().parents[2]


def pair(en: str, hu: str) -> dict[str, str]:
    return {"en": en, "hu": hu}


def record(record_id: str, record_type: str, content: dict) -> dict:
    return {
        "id": record_id, "record_type": record_type,
        "schema_version": "2.1.0", "topic": "test", "status": "candidate",
        "content": content, "provenance_ref": "PV-test",
        "created_at": "2026-07-22T00:00:00Z", "supersedes": None,
    }


class ExactCoverageTests(unittest.TestCase):
    def test_normalized_claim_requirement_is_new_dag_only(self) -> None:
        legacy = transformation_output(["F-test"], ["S1"])
        normalized = transformation_output(["F-test"], ["S1"], ["CC-test"])
        legacy_proposal = legacy["properties"]["proposals"]["items"]
        normalized_proposal = normalized["properties"]["proposals"]["items"]
        self.assertNotIn("canonical_claim_refs", legacy_proposal["properties"])
        self.assertIn("canonical_claim_refs", normalized_proposal["required"])

    def test_new_bilingual_artifact_schemas_validate(self) -> None:
        schemas = SchemaRegistry(ROOT / "schemas" / "v2")
        claim = record("CC-test", "canonical_claim", {
            "statement": pair("Bounded claim", "Korlátozott állítás"),
            "claim_type": "descriptive",
            "population": pair("Students", "Tanulók"),
            "context": pair("Test context", "Tesztkörnyezet"),
            "time_scope": pair("Current period", "Jelenlegi időszak"),
            "evidence_strength": "moderate", "transferability": "conditional",
            "supporting_finding_refs": ["F-test"],
            "contradicting_finding_refs": [], "assumption_refs": [],
            "uncertainty_refs": [],
        })
        conflict = record("EC-test", "evidence_conflict", {
            "title": pair("Context conflict", "Kontextuskonfliktus"),
            "conflict_type": "context_dependence",
            "description": pair("Results differ by context.", "Az eredmények kontextusonként eltérnek."),
            "resolvability": "context_specific",
            "research_question": pair("Where does it hold?", "Hol érvényes?"),
            "decision_relevance": pair("Limits transfer.", "Korlátozza az átvihetőséget."),
            "finding_refs": ["F-test", "F-other"],
            "canonical_claim_refs": ["CC-test"],
        })
        seed = record("OSD-test", "option_seed", {
            "title": pair("Possible lever", "Lehetséges beavatkozási pont"),
            "system_problem": pair("Unequal access", "Egyenlőtlen hozzáférés"),
            "change_lever": pair("Resource allocation", "Erőforrás-elosztás"),
            "scope": pair("A bounded pilot", "Korlátozott kísérlet"),
            "seed_type": "funding", "canonical_claim_refs": ["CC-test"],
            "evidence_conflict_refs": ["EC-test"], "finding_refs": ["F-test"],
            "assumption_refs": [], "uncertainty_refs": [],
        })
        for artifact in (claim, conflict, seed):
            schemas.validate(artifact)

    def test_evidence_coverage_requires_exact_identity_set(self) -> None:
        content = {
            "gate_basis": "evidence_normalization",
            "entries": [{
                "finding_ref": "F-1", "status": "carried_forward",
                "canonical_claim_refs": ["CC-1"], "evidence_conflict_refs": [],
                "duplicate_of_ref": None, "critical": True, "rationale": {"en": "Used", "hu": "Felhasználva"},
            }],
            "critical_attrition_count": 0, "verdict": "complete",
        }
        with self.assertRaisesRegex(CoverageValidationError, "missing"):
            validate_exact_coverage(
                content, {"F-1", "F-2"}, basis="evidence_normalization"
            )

    def test_critical_silent_attrition_cannot_claim_completion(self) -> None:
        content = {
            "gate_basis": "option_seed_clustering",
            "entries": [{
                "option_seed_ref": "OSD-1", "status": "rejected",
                "direction_ids": [], "merged_into_ref": None,
                "critical": True, "rationale": {"en": "Rejected", "hu": "Elvetve"},
            }],
            "critical_attrition_count": 0, "verdict": "complete",
        }
        with self.assertRaisesRegex(CoverageValidationError, "critical_attrition_count"):
            validate_exact_coverage(
                content, {"OSD-1"}, basis="option_seed_clustering",
                direction_ids={"S1"},
            )

    def test_complete_seed_coverage_passes(self) -> None:
        content = {
            "gate_basis": "option_seed_clustering",
            "entries": [{
                "option_seed_ref": "OSD-1", "status": "clustered_into",
                "direction_ids": ["S1"], "merged_into_ref": None,
                "critical": True, "rationale": {"en": "Retained", "hu": "Megtartva"},
            }],
            "critical_attrition_count": 0, "verdict": "complete",
        }
        validate_exact_coverage(
            content, {"OSD-1"}, basis="option_seed_clustering",
            direction_ids={"S1"},
        )


if __name__ == "__main__":
    unittest.main()
