from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from policy_lab.dag import (
    DagNode, DagSpec, DagSpecError, HumanGatePending, InputBinding,
    NodeExecutor, NodeSpec, RootPort,
)
from policy_lab.jsonio import write_json
from policy_lab.live.dag_spec import build_policy_analysis_dag
from policy_lab.live.experiment import ArtifactDagRunner
from policy_lab.store import ArtifactRef


ROOT = Path(__file__).resolve().parents[2]


class NoCallLlm:
    CALL_LOG: list[dict] = []

    @classmethod
    def call_log_len(cls) -> int:
        return len(cls.CALL_LOG)


def ref(record_id: str, record_type: str, marker: str) -> ArtifactRef:
    return ArtifactRef(
        id=record_id,
        record_type=record_type,
        content_hash=marker * 64,
        path=Path(f"/{record_id}.json"),
    )


class DagSpecTests(unittest.TestCase):
    def test_live_dag_is_explicit_and_contains_human_gate(self) -> None:
        lenses = ("legal", "finance")
        dag = build_policy_analysis_dag(lenses)
        dag.validate()

        self.assertEqual(dag.version, "3.0.0")
        self.assertEqual(len(dag.roots), 3)
        self.assertEqual(len(dag.nodes), 12)
        self.assertEqual(dag.nodes[2].id, "derive_option_space")
        self.assertEqual(dag.nodes[3].id, "approve_option_space")
        self.assertEqual(dag.nodes[3].kind, "human_gate")
        transformation = next(
            node for node in dag.nodes if node.id == "derive_transformations"
        )
        option_binding = next(
            binding for binding in transformation.inputs
            if binding.name == "option_space"
        )
        self.assertEqual(option_binding.sources, ("approve_option_space",))
        self.assertEqual(option_binding.record_types, ("approved_option_space",))

    def test_compile_binds_exact_root_hashes_and_writes_edges(self) -> None:
        dag = build_policy_analysis_dag(("legal",))
        roots = {
            "problem_brief": (ref("PB-test", "problem_brief", "a"),),
            "lens_legal": (ref("L-test-legal", "lens_definition", "b"),),
        }
        plan = dag.compile(topic="test", root_artifacts=roots)

        self.assertEqual(plan.as_dict()["roots"]["problem_brief"][0]["content_hash"], "a" * 64)
        self.assertIn(
            {
                "binding": "problem",
                "from": "root:problem_brief",
                "record_types": ["problem_brief"],
                "to": "research_legal",
            },
            plan.as_dict()["edges"],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run_plan.json"
            plan.write(path)
            self.assertTrue(path.exists())

    def test_unknown_or_later_source_fails_static_validation(self) -> None:
        first = DagNode(
            id="first", version="1.0.0", kind="deterministic",
            role="deterministic", stage="test", title="First",
            description="Test", handler="first",
            inputs=(InputBinding("later", ("second",), ("finding",)),),
            output_types=("finding",),
        )
        second = DagNode(
            id="second", version="1.0.0", kind="deterministic",
            role="deterministic", stage="test", title="Second",
            description="Test", handler="second", inputs=(),
            output_types=("finding",),
        )
        dag = DagSpec("bad", "1.0.0", (RootPort("problem", ("finding",)),), (first, second))
        with self.assertRaisesRegex(DagSpecError, "later node"):
            dag.validate()

    def test_plan_resolves_only_declared_types(self) -> None:
        dag = build_policy_analysis_dag(("legal",))
        plan = dag.compile(
            topic="test",
            root_artifacts={
                "problem_brief": (ref("PB-test", "problem_brief", "a"),),
                "lens_legal": (ref("L-test", "lens_definition", "b"),),
            },
        )
        research_outputs = (
            ref("F-test", "finding", "c"),
            ref("SRC-test", "source", "d"),
            ref("A-test", "assumption", "e"),
            ref("U-test", "uncertainty", "f"),
        )
        inputs = plan.resolve_inputs(
            "derive_option_space", {"research_legal": research_outputs}
        )
        self.assertEqual(
            {item.record_type for item in inputs["evidence"]},
            {"finding", "assumption", "uncertainty"},
        )

    def test_runner_materializes_exact_admitted_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = ArtifactDagRunner(
                root=ROOT, output_root=directory, llm_module=NoCallLlm(),
                topic="korai-szelekcio",
            )
            roots = runner._admit_run_roots()
            plan = build_policy_analysis_dag(
                lens["id"] for lens in runner.base_lenses
            ).compile(topic=runner.topic, root_artifacts=roots)

            problem = runner.repository.get_by_hash(
                roots["problem_brief"][0].content_hash
            )
            self.assertEqual(problem["status"], "admitted")
            self.assertEqual(problem["record_type"], "problem_brief")
            self.assertEqual(len(roots), 13)
            self.assertEqual(len(plan.nodes), 32)

    def test_human_gate_is_bound_to_one_exact_candidate_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = ArtifactDagRunner(
                root=ROOT, output_root=directory, llm_module=NoCallLlm(),
                topic="korai-szelekcio",
            )
            provenance = runner._admission_provenance(
                "test_option_candidate", source_files=("config/v2/lenses.json",),
                admitted_content={"test": True},
            )
            candidate_ref = runner.repository.put(runner._record(
                "OS-live-test", "option_space_proposal", provenance.id,
                {
                    "directions": [
                        {"id": "S1", "title": "One", "scope": "First", "finding_refs": ["F-test"]},
                        {"id": "S2", "title": "Two", "scope": "Second", "finding_refs": ["F-test"]},
                    ],
                    "rejected_framings": [
                        {"framing": "Too narrow", "reason": "Misses the evidence", "finding_refs": []}
                    ],
                    "derivation_notice": "Test candidate pending exact approval.",
                },
            ))
            run_dir = Path(directory) / "runs" / "test"
            executor = NodeExecutor(
                repository=runner.repository, run_dir=run_dir, source_root=ROOT,
                run_id="test", artifact_created_at=runner.created_at,
                topic=runner.topic, run_plan_hash="a" * 64,
            )
            with self.assertRaises(HumanGatePending) as context:
                runner._require_gate_decision(
                    executor, run_dir, candidate_ref, "a" * 64
                )
            request_path = context.exception.request_path
            decision_path = request_path.with_name(
                request_path.name.replace(".request.json", ".decision.json")
            )
            decision = {
                "gate_id": "approve_option_space",
                "candidate_ref": candidate_ref.id,
                "candidate_hash": "b" * 64,
                "decision": "approved",
                "decided_by": "test-owner",
                "decided_at": datetime.now(timezone.utc).isoformat(),
                "rationale": "The candidate spans the test option space.",
            }
            write_json(decision_path, decision)
            with self.assertRaisesRegex(ValueError, "does not match exact candidate"):
                runner._require_gate_decision(
                    executor, run_dir, candidate_ref, "a" * 64
                )
            decision["candidate_hash"] = candidate_ref.content_hash
            write_json(decision_path, decision)
            accepted = runner._require_gate_decision(
                executor, run_dir, candidate_ref, "a" * 64
            )
            self.assertEqual(accepted["candidate_hash"], candidate_ref.content_hash)
            records = runner._approved_option_space_records(
                candidate_ref, accepted, provenance.id
            )
            refs = [runner.repository.put(record) for record in records]
            approved = runner.repository.get_by_hash(refs[1].content_hash)
            self.assertEqual(approved["status"], "admitted")
            self.assertEqual(
                approved["content"]["candidate_hash"], candidate_ref.content_hash
            )

    def test_llm_attempt_hashes_enter_output_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = ArtifactDagRunner(
                root=ROOT, output_root=directory, llm_module=NoCallLlm(),
                topic="korai-szelekcio",
            )
            roots = runner._admit_run_roots()
            run_dir = Path(directory) / "runs" / "attempt-test"
            executor = NodeExecutor(
                repository=runner.repository, run_dir=run_dir, source_root=ROOT,
                run_id="attempt-test", artifact_created_at=runner.created_at,
                topic=runner.topic, run_plan_hash="c" * 64,
            )
            spec = NodeSpec(
                name="test_llm_attempt", version="1.0.0",
                input_types=("problem_brief",), output_types=("source",),
                schema_files=("schemas/v2/source.schema.json",), role="research",
            )

            def build(provenance_id: str) -> list[dict]:
                runner._persist_attempt(
                    run_dir, spec.name, "generate", "EXACT PROMPT",
                    b'{"answer":"EXACT RESPONSE"}', "json",
                )
                return [runner._record(
                    "SRC-attempt-test", "source", provenance_id,
                    {
                        "title": "Test source", "url": "https://example.org/test",
                        "source_type": "web_page",
                        "license_status": "public_pointer_only",
                        "accessed_at": runner.created_at,
                    },
                )]

            refs = executor.run(
                spec, inputs={"problem": roots["problem_brief"]}, builder=build,
                provider="anthropic", model="test-model",
                generation_parameters={"max_tokens": 10}, prompt_hash="d" * 64,
            )
            source = runner.repository.get_by_hash(refs[0].content_hash)
            provenance = runner.repository.get_current(source["provenance_ref"])
            self.assertEqual(provenance["content"]["run_plan_hash"], "c" * 64)
            self.assertEqual(len(provenance["content"]["attempts"]), 1)
            self.assertEqual(provenance["content"]["attempts"][0]["stage"], "generate")


if __name__ == "__main__":
    unittest.main()
