from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from policy_lab.dag import NodeSpec, compute_cache_key
from policy_lab.jsonio import content_hash
from policy_lab.i18n import suspicious_identity
from policy_lab.live.experiment import ArtifactDagRunner, PsychologyLensExperiment
from policy_lab.schema_registry import SchemaRegistry, SchemaValidationError
from policy_lab.store import ArtifactRepository, GraphIntegrityError

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "v2"
ZERO_HASH = "0" * 64


def provenance_record() -> dict:
    return {
        "id": "PV-test",
        "record_type": "provenance",
        "schema_version": "2.0.0",
        "topic": "early-selection",
        "status": "candidate",
        "content": {
            "node_id": "research_psychology",
            "execution_id": "EX-test",
            "input_artifact_hashes": [],
            "spec_hashes": {"research.md": ZERO_HASH},
            "schema_hashes": {"finding.schema.json": ZERO_HASH},
            "prompt_hash": ZERO_HASH,
            "provider": "anthropic",
            "model": "test-model",
            "role": "research",
        },
        "provenance_ref": None,
        "created_at": "2026-07-20T12:00:00Z",
        "supersedes": None,
    }


def source_record() -> dict:
    return {
        "id": "SRC-test",
        "record_type": "source",
        "schema_version": "2.0.0",
        "topic": "early-selection",
        "status": "candidate",
        "content": {
            "title": "Example longitudinal study",
            "url": "https://example.org/study",
            "source_type": "research_paper",
            "license_status": "public_pointer_only",
            "accessed_at": "2026-07-20T12:00:00Z",
        },
        "provenance_ref": "PV-test",
        "created_at": "2026-07-20T12:01:00Z",
        "supersedes": None,
    }


def finding_record() -> dict:
    return {
        "id": "F-test",
        "record_type": "finding",
        "schema_version": "2.0.0",
        "topic": "early-selection",
        "status": "candidate",
        "content": {
            "claim": "Early selection can affect academic self-concept.",
            "kind": "fact",
            "domain_tags": ["educational_psychology"],
            "evidence_strength": "moderate",
            "source_refs": ["SRC-test"],
            "population": "Students exposed to selective school placement",
            "context": "Longitudinal school-composition research",
            "time_scope": "Adolescence",
            "transferability": "uncertain",
            "limitations": ["Institutional contexts differ."],
            "assumption_ids": [],
            "uncertainty_ids": [],
        },
        "provenance_ref": "PV-test",
        "created_at": "2026-07-20T12:02:00Z",
        "supersedes": None,
    }


class SchemaRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schemas = SchemaRegistry(SCHEMA_DIR)

    def test_registers_versioned_record_schemas(self) -> None:
        available = set(self.schemas.available())
        archive = {
                ("approved_option_space", "2.0.0"),
                ("architecture_overlay", "2.0.0"),
                ("assumption", "2.0.0"),
                ("canonical_claim", "2.0.0"),
                ("coverage_ledger", "2.0.0"),
                ("decision_package", "2.0.0"),
                ("decision_readiness", "2.0.0"),
                ("dilemma", "2.0.0"),
                ("evaluation", "2.0.0"),
                ("evidence_conflict", "2.0.0"),
                ("finding", "2.0.0"),
                ("human_gate_decision", "2.0.0"),
                ("lens_assessment", "2.0.0"),
                ("lens_definition", "2.0.0"),
                ("option_space_proposal", "2.0.0"),
                ("option_seed", "2.0.0"),
                ("policy_question", "2.0.0"),
                ("problem_brief", "2.0.0"),
                ("problem_brief_decision", "2.0.0"),
                ("problem_brief_proposal", "2.0.0"),
                ("provenance", "2.0.0"),
                ("research_question", "2.0.0"),
                ("source", "2.0.0"),
                ("transformation_family", "2.0.0"),
                ("transformation_proposal", "2.0.0"),
                ("uncertainty", "2.0.0"),
        }
        self.assertTrue(archive.issubset(available))
        self.assertEqual(
            {record_type for record_type, version in available if version == "2.1.0"},
            {record_type for record_type, _ in archive} - {"provenance"},
        )

    def test_rejects_unknown_fields(self) -> None:
        record = finding_record()
        record["content"]["expert_position"] = "This field must not exist."
        with self.assertRaises(SchemaValidationError):
            self.schemas.validate(record)

    def test_rejects_bilingual_shape(self) -> None:
        record = finding_record()
        record["content"]["claim"] = {
            "en": "English claim",
            "hu": "Localized claim",
        }
        with self.assertRaises(SchemaValidationError):
            self.schemas.validate(record)

    def test_bilingual_schema_requires_and_accepts_exact_language_pairs(self) -> None:
        record = finding_record()
        record["schema_version"] = "2.1.0"
        for field in ("claim", "population", "context", "time_scope"):
            record["content"][field] = {
                "en": record["content"][field],
                "hu": f"HU: {record['content'][field]}",
            }
        record["content"]["limitations"] = [
            {"en": value, "hu": f"HU: {value}"}
            for value in record["content"]["limitations"]
        ]
        self.schemas.validate(record)

        record["content"]["claim"] = "English-only claim"
        with self.assertRaises(SchemaValidationError):
            self.schemas.validate(record)

    def test_long_unchanged_prose_is_flagged_but_citations_are_exempt(self) -> None:
        copied = {
            "en": "This long semantic statement was never translated into Hungarian.",
            "hu": "This long semantic statement was never translated into Hungarian.",
        }
        self.assertTrue(suspicious_identity("finding", "claim", copied))
        self.assertFalse(suspicious_identity("source", "title", copied))
        self.assertFalse(suspicious_identity(
            "decision_package", "evidence_appendix.*.sources.*.title", copied
        ))

    def test_rejects_invalid_standard_format(self) -> None:
        record = source_record()
        record["content"]["url"] = "not a URI"
        with self.assertRaises(SchemaValidationError):
            self.schemas.validate(record)

    def test_optional_reference_field_contributes_no_edges(self) -> None:
        package = {
            "id": "DP-test", "record_type": "decision_package",
            "schema_version": "2.0.0", "topic": "early-selection",
            "status": "candidate", "provenance_ref": "PV-test",
            "created_at": "2026-07-20T12:00:00Z", "supersedes": None,
            "content": {
                "title": "Test", "public_question": "Test?", "summary": "Test.",
                "transformation_family_refs": ["TF-test"],
                "proposal_refs": ["TP-test"],
                "lens_assessment_refs": ["AS-test"],
                "dilemma_refs": [], "research_question_refs": [],
                "migration_notice": "Legacy artifact without a coverage ledger."
            },
        }
        self.schemas.validate(package)
        fields = {reference.field for reference in self.schemas.references(package)}
        self.assertNotIn("/content/coverage_ledger_refs/*", fields)

        package["content"]["evidence_appendix"] = [{
            "finding_ref": "F-test", "claim": "A test claim.",
            "sources": [{
                "source_ref": "SRC-test", "title": "Test source",
                "url": "https://example.org/source",
            }],
        }]
        self.schemas.validate(package)
        references = self.schemas.references(package)
        self.assertIn(("F-test", "finding"), {(ref.target_id, ref.target_type) for ref in references})
        self.assertIn(("SRC-test", "source"), {(ref.target_id, ref.target_type) for ref in references})


class ArtifactRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.schemas = SchemaRegistry(SCHEMA_DIR)
        self.repo = ArtifactRepository(self.tempdir.name, self.schemas)

    def seed_graph(self) -> None:
        self.repo.put(provenance_record())
        self.repo.put(source_record())
        self.repo.put(finding_record())

    def test_canonical_hash_ignores_mapping_insertion_order(self) -> None:
        record = finding_record()
        reversed_record = dict(reversed(list(record.items())))
        self.assertEqual(content_hash(record), content_hash(reversed_record))

    def test_put_is_immutable_and_deduplicated(self) -> None:
        ref_a = self.repo.put(provenance_record())
        ref_b = self.repo.put(copy.deepcopy(provenance_record()))
        self.assertEqual(ref_a.content_hash, ref_b.content_hash)
        paths = (Path(self.tempdir.name) / "artifacts").glob("*/*.json")
        self.assertEqual(len(list(paths)), 1)

    def test_semantic_version_lineage(self) -> None:
        first = self.repo.put(provenance_record())
        revised = provenance_record()
        revised["content"]["model"] = "new-test-model"
        revised["created_at"] = "2026-07-20T13:00:00Z"
        revised["supersedes"] = first.content_hash
        second = self.repo.put(revised)

        current = self.repo.get_current("PV-test")
        self.assertEqual(current["content"]["model"], "new-test-model")
        self.assertEqual(
            [ref.content_hash for ref in self.repo.lineage("PV-test")],
            [second.content_hash, first.content_hash],
        )

    def test_put_successor_links_changed_node_output(self) -> None:
        first = self.repo.put(provenance_record())
        revised = provenance_record()
        revised["content"]["model"] = "new-test-model"
        revised["created_at"] = "2026-07-20T13:00:00Z"
        second = self.repo.put_successor(revised)

        self.assertEqual(
            self.repo.get_by_hash(second.content_hash)["supersedes"],
            first.content_hash,
        )
        self.assertEqual(
            [ref.content_hash for ref in self.repo.lineage("PV-test")],
            [second.content_hash, first.content_hash],
        )

    def test_graph_validation_and_queries(self) -> None:
        self.seed_graph()
        self.repo.validate_graph(("F-test",))
        outgoing = self.repo.outgoing("F-test")
        self.assertEqual(
            {(ref.target_id, ref.target_type) for ref in outgoing},
            {("PV-test", "provenance"), ("SRC-test", "source")},
        )
        incoming = self.repo.incoming("SRC-test")
        self.assertEqual(incoming[0][0], "F-test")

    def test_graph_validation_rejects_missing_reference(self) -> None:
        self.repo.put(provenance_record())
        self.repo.put(finding_record())
        with self.assertRaises(GraphIntegrityError):
            self.repo.validate_graph(("F-test",))


class NodeSpecTests(unittest.TestCase):
    def test_cache_key_is_order_stable_and_dependency_scoped(self) -> None:
        spec = NodeSpec(
            name="cluster_option_seeds",
            version="1.0.0",
            input_types=("option_seed_set",),
            output_types=("transformation_family_set",),
            config_keys=("clustering.max_families",),
            role="generator",
        )
        common = {
            "spec": spec,
            "input_artifact_hashes": {
                "option_seed_set": ("b" * 64, "a" * 64)
            },
            "spec_hashes": {"cluster.md": "c" * 64},
            "schema_hashes": {"family.schema.json": "d" * 64},
            "relevant_config": {"clustering.max_families": 5},
            "provider": "anthropic",
            "model": "test-model",
            "generation_parameters": {"temperature": 0},
            "prompt_hash": "e" * 64,
        }
        key_a = compute_cache_key(**common)
        common["input_artifact_hashes"] = {
            "option_seed_set": tuple(
                reversed(common["input_artifact_hashes"]["option_seed_set"])
            )
        }
        key_b = compute_cache_key(**common)
        self.assertEqual(key_a, key_b)

        common["relevant_config"] = {"clustering.max_families": 6}
        self.assertNotEqual(key_a, compute_cache_key(**common))

        common["relevant_config"] = {"clustering.max_families": 5}
        common["prompt_hash"] = "f" * 64
        self.assertNotEqual(key_a, compute_cache_key(**common))

    def test_live_node_dependencies_are_implementation_scoped(self) -> None:
        runner = object.__new__(PsychologyLensExperiment)
        spec = runner._spec(
            "derive_transformations", ("finding",),
            ("transformation_proposal",),
            ("transformation_proposal.schema.json",), role="generator",
        )
        self.assertEqual(spec.spec_files, ())
        self.assertNotEqual(
            runner._contract_hash("derive_transformations_v1"),
            runner._contract_hash("decision_package_v1"),
        )

    def test_experiment_runner_remains_a_production_runner_subtype(self) -> None:
        self.assertTrue(issubclass(PsychologyLensExperiment, ArtifactDagRunner))

    def test_live_source_normalization_selects_one_valid_uri(self) -> None:
        self.assertEqual(
            ArtifactDagRunner._safe_uri(
                "https://hudoc.echr.coe.int/; https://ec.europa.eu", "SRC-test"
            ),
            "https://hudoc.echr.coe.int/",
        )
        self.assertEqual(
            ArtifactDagRunner._safe_uri("No direct URL in the notes", "SRC Test"),
            "urn:epl:live-source:src-test",
        )
        self.assertEqual(
            ArtifactDagRunner._safe_uri(
                "https://scholar.google.com/scholar?q=Böheim-Galehr", "SRC-test"
            ),
            "https://scholar.google.com/scholar?q=B%C3%B6heim-Galehr",
        )


if __name__ == "__main__":
    unittest.main()
