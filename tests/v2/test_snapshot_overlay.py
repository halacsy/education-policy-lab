from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from policy_lab.live.overlay import (
    SnapshotOverlayRunner,
    SnapshotSelection,
    build_snapshot_overlay_dag,
    build_trace_overlap_content,
    import_transitive_closure,
    select_source_snapshot,
    select_v31_snapshot,
)
from policy_lab.schema_registry import SchemaRegistry
from policy_lab.store import ArtifactRef, ArtifactRepository


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "v2" / "production" / "2026-07-21-v3-bilingual" / "korai-szelekcio"
SNI_SOURCE = (
    ROOT / "v2" / "production" / "2026-07-21-sni-brief-revision-2"
    / "sni-letszamnovekedes"
)


def pair(en: str) -> dict[str, str]:
    return {"en": en, "hu": f"HU: {en}"}


class ScriptedOverlayLlm:
    CALL_LOG: list[dict] = []

    @classmethod
    def call_log_len(cls) -> int:
        return len(cls.CALL_LOG)

    @staticmethod
    def call_structured(
        prompt: str, schema: dict, role: str, *, max_tokens: int
    ) -> dict:
        del role, max_tokens
        if "TASK: normalize_evidence_cross_shard" in prompt:
            claim_keys = (
                schema["properties"]["merge_groups"]["items"]
                ["properties"]["claim_keys"]["items"]["enum"]
            )
            return {
                "merge_groups": [{
                    "claim_keys": claim_keys[:2],
                    "rationale": pair("Equivalent bounded test claims"),
                }],
                "conflicts": [],
            }
        if "TASK: normalize_evidence" in prompt:
            coverage_schema = schema["properties"]["coverage"]["items"]
            finding_ids = coverage_schema["properties"]["finding_ref"]["enum"]
            return {
                "claims": [{
                    "key": "C1", "statement": pair("Shared bounded claim"),
                    "claim_type": "descriptive", "population": pair("Students"),
                    "context": pair("Source snapshot"), "time_scope": pair("Snapshot period"),
                    "evidence_strength": "moderate", "transferability": "conditional",
                    "supporting_finding_refs": finding_ids[:-1] + [finding_ids[0]],
                    "contradicting_finding_refs": [], "assumption_refs": [],
                    "uncertainty_refs": [],
                }],
                "conflicts": [{
                    "key": "E1", "title": pair("Invalid pseudo conflict"),
                    "conflict_type": "context_dependence",
                    "description": pair("Only one finding was cited"),
                    "resolvability": "context_specific",
                    "research_question": pair("What would a second finding show?"),
                    "decision_relevance": pair("Tests the strict conflict gate"),
                    "finding_refs": [finding_ids[0]], "claim_keys": ["C1"],
                }],
                "coverage": [{
                    "finding_ref": finding_id,
                    "status": "conflict_recorded" if index == 0 else "carried_forward",
                    "claim_keys": [] if index == 0 else ["C1"],
                    "conflict_keys": ["E1"] if index == 0 else [],
                    "duplicate_of_refs": [], "critical": False,
                    "rationale": pair("Carried into the test claim"),
                } for index, finding_id in enumerate(finding_ids)],
            }
        if "TASK: derive_option_seeds" in prompt:
            item = schema["properties"]["seeds"]["items"]
            claim_id = item["properties"]["canonical_claim_refs"]["items"]["enum"][0]
            finding_id = item["properties"]["finding_refs"]["items"]["enum"][0]
            return {"seeds": [{
                "key": f"O{index}", "title": pair(f"Seed {index}"),
                "system_problem": pair("System problem"),
                "change_lever": pair("Change lever"), "scope": pair("Bounded scope"),
                "seed_type": "organizational", "canonical_claim_refs": [claim_id],
                "evidence_conflict_refs": [], "finding_refs": [finding_id],
                "assumption_refs": [], "uncertainty_refs": [],
            } for index in range(1, 5)]}
        if "TASK: cluster_option_seeds" in prompt:
            seed_ids = schema["properties"]["coverage"]["items"]["properties"]["option_seed_ref"]["enum"]
            return {
                "directions": [
                    {"id": "S1", "title": pair("First direction"), "scope": pair("First scope"), "option_seed_refs": seed_ids[:2]},
                    {"id": "S2", "title": pair("Second direction"), "scope": pair("Second scope"), "option_seed_refs": seed_ids[2:]},
                ],
                "rejected_framings": [{
                    "framing": pair("Narrow framing"),
                    "reason": pair("It would hide relevant levers"),
                    "option_seed_refs": [],
                }],
                "coverage": [{
                    "option_seed_ref": seed_id, "status": "clustered_into",
                    "direction_ids": ["S1" if index < 2 else "S2"],
                    "merged_into_refs": [], "critical": False,
                    "rationale": pair("Retained in a test direction"),
                } for index, seed_id in enumerate(seed_ids)],
            }
        raise AssertionError("Unexpected scripted prompt")


class SnapshotOverlayTests(unittest.TestCase):
    def test_scripted_overlay_executes_complete_run_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = SnapshotOverlayRunner(
                root=ROOT, output_root=directory,
                llm_module=ScriptedOverlayLlm(), topic="korai-szelekcio",
            )
            manifest = runner.run_overlay(
                source_root=SOURCE,
                source_run_tag="2026-07-21-v3-bilingual",
            )
            self.assertEqual(manifest["architecture_version"], "3.2.0-overlay.1")
            self.assertEqual(manifest["summary"]["seed_count"], 4)
            self.assertEqual(
                len(list((Path(directory) / "runs" / manifest["run_id"] / "nodes").glob("*.json"))),
                4,
            )
            normalization_log = (
                Path(directory) / "runs" / manifest["run_id"]
                / "semantic_normalizations.jsonl"
            )
            self.assertIn(
                "derive_redundant_reverse_references",
                normalization_log.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "synthesize_lossless_atomic_fallback_claim",
                normalization_log.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "deduplicate_redundant_references",
                normalization_log.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "merge_equivalent_cross_shard_claims",
                normalization_log.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "drop_single_finding_pseudo_conflict",
                normalization_log.read_text(encoding="utf-8"),
            )
            attempts = (
                Path(directory) / "runs" / manifest["run_id"]
                / "attempts" / "normalize_evidence"
            )
            self.assertEqual(len(list(attempts.rglob("response.json"))), 4)
            prompt_names = {
                path.name
                for path in (
                    Path(directory) / "runs" / manifest["run_id"] / "prompts"
                ).glob("normalize_evidence.*.md")
            }
            self.assertTrue(any("generate-shard-01" in name for name in prompt_names))
            self.assertTrue(any("generate-shard-03" in name for name in prompt_names))
            self.assertTrue(any("reconcile-cross-shard" in name for name in prompt_names))
            runner.repository.validate_graph((manifest["overlay_ref"],))

    def test_overlay_dag_has_only_new_middle_layer_and_comparison(self) -> None:
        dag = build_snapshot_overlay_dag()
        dag.validate()
        self.assertEqual(dag.version, "3.2.0-overlay.1")
        self.assertEqual(
            [node.id for node in dag.nodes],
            [
                "normalize_evidence", "derive_option_seeds",
                "cluster_option_seeds", "compare_to_v31",
            ],
        )
        self.assertEqual(
            {root.name for root in dag.roots},
            {
                "problem_brief", "research_snapshot",
                "legacy_option_space", "legacy_proposals",
            },
        )

    def test_selects_exact_v31_research_outputs_and_imports_closed_graph(self) -> None:
        source, snapshot = select_v31_snapshot(
            SOURCE, "2026-07-21-v3-bilingual"
        )
        self.assertEqual(snapshot.source_run_plan_hash, "9f413a7d2fb6a9a7fd36aa03403bbfdbeeb4e641726c70afddefdfee8099099b")
        self.assertEqual(
            len([ref for ref in snapshot.evidence_refs if ref.record_type == "finding"]),
            115,
        )
        self.assertEqual(len(snapshot.legacy_proposal_refs), 5)
        with tempfile.TemporaryDirectory() as directory:
            target = ArtifactRepository(
                directory, SchemaRegistry(ROOT / "schemas" / "v2")
            )
            copied = import_transitive_closure(source, target, snapshot.seed_refs())
            self.assertGreater(copied, len(snapshot.seed_refs()))
            target.validate_graph()

    def test_selects_v30_human_approved_problem_brief_and_research(self) -> None:
        source, snapshot = select_source_snapshot(
            SNI_SOURCE, "2026-07-21-sni-brief-revision-2"
        )
        self.assertEqual(snapshot.source_architecture_version, "3.0.0")
        self.assertEqual(
            snapshot.source_run_plan_hash,
            "d362cf93d6cce4558b5890d554a57183be564c8924c536e62a1e2b493f9f313c",
        )
        self.assertEqual(snapshot.problem_ref.id, "PB-sni-letszamnovekedes")
        self.assertEqual(
            snapshot.problem_ref.content_hash,
            "20b6773d7df18e2689f13f4784a9aac729a99e6bd8deb841d74567a445e91293",
        )
        self.assertEqual(
            len([
                ref for ref in snapshot.evidence_refs
                if ref.record_type == "finding"
            ]),
            119,
        )
        self.assertEqual(len(snapshot.legacy_proposal_refs), 6)
        with tempfile.TemporaryDirectory() as directory:
            target = ArtifactRepository(
                directory, SchemaRegistry(ROOT / "schemas" / "v2")
            )
            copied = import_transitive_closure(
                source, target, snapshot.seed_refs()
            )
            self.assertGreater(copied, len(snapshot.seed_refs()))
            self.assertEqual(
                target.get_current("PB-sni-letszamnovekedes")[
                    "schema_version"
                ],
                "2.1.0",
            )
            self.assertTrue(all(
                target.get_current(ref.id)["schema_version"] == "2.1.0"
                for ref in snapshot.evidence_refs
            ))
            target.validate_graph()

    def test_trace_overlap_exposes_uncovered_seed_and_conflict(self) -> None:
        marker = "a" * 64
        snapshot = SnapshotSelection(
            source_root=Path("/source"), source_run_tag="source-tag",
            source_architecture_version="3.1.0",
            source_manifest_hash=marker, source_run_plan_hash="b" * 64,
            problem_ref=ArtifactRef("PB-test", "problem_brief", marker, Path("/pb")),
            evidence_refs=(),
            legacy_option_ref=ArtifactRef("AO-test", "approved_option_space", marker, Path("/ao")),
            legacy_proposal_refs=(),
        )
        legacy_option = {
            "id": "AO-test", "content": {
                "directions": [{"id": "S1", "finding_refs": ["F-1"]}]
            },
        }
        proposals = [{
            "id": "TP-old", "content": {"finding_refs": ["F-1"]}
        }]
        seeds = [
            {"id": "OSD-1", "content": {"finding_refs": ["F-1"]}},
            {"id": "OSD-2", "content": {"finding_refs": ["F-2"]}},
        ]
        conflicts = [{
            "id": "EC-1", "content": {"finding_refs": ["F-2", "F-3"]}
        }]
        new_option = {
            "id": "OS-overlay-test", "content": {"directions": [
                {"id": "S1", "option_seed_refs": ["OSD-1"]},
                {"id": "S2", "option_seed_refs": ["OSD-2"]},
            ]},
        }
        content = build_trace_overlap_content(
            source=snapshot, legacy_option=legacy_option,
            legacy_proposals=proposals, seeds=seeds, conflicts=conflicts,
            new_option=new_option,
            normalization_coverage_ref="CL-normalization",
            seed_coverage_ref="CL-seeds",
        )
        self.assertEqual(content["summary"]["uncovered_seed_count"], 1)
        self.assertEqual(content["summary"]["novel_gap_count"], 1)
        self.assertEqual(
            content["summary"]["conflicts_without_legacy_proposal_count"], 1
        )
        self.assertEqual(content["seed_entries"][1]["status"], "uncovered")

        record = {
            "id": "OV-test", "record_type": "architecture_overlay",
            "schema_version": "2.1.0", "topic": "test", "status": "candidate",
            "content": content, "provenance_ref": "PV-test",
            "created_at": "2026-07-22T00:00:00Z", "supersedes": None,
        }
        SchemaRegistry(ROOT / "schemas" / "v2").validate(record)


if __name__ == "__main__":
    unittest.main()
