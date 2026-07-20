from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from policy_lab.dag import NodeSpec, compute_cache_key
from policy_lab.jsonio import content_hash
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
        self.assertEqual(
            self.schemas.available(),
            (
                ("finding", "2.0.0"),
                ("provenance", "2.0.0"),
                ("source", "2.0.0"),
            ),
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

    def test_rejects_invalid_standard_format(self) -> None:
        record = source_record()
        record["content"]["url"] = "not a URI"
        with self.assertRaises(SchemaValidationError):
            self.schemas.validate(record)


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


if __name__ == "__main__":
    unittest.main()
