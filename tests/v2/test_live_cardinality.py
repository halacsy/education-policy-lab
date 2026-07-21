from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from policy_lab.jsonio import canonical_json_bytes
from policy_lab.live.experiment import (
    ArtifactDagRunner,
    _cardinality_repair_instruction,
    _escalated_token_budget,
    _normalize_collection_counts,
)


class LiveCardinalityRepairTests(unittest.TestCase):
    def test_retry_uses_stable_exact_targets_for_every_collection(self) -> None:
        instruction = _cardinality_repair_instruction(
            {
                "findings": (7, 10),
                "assumptions": (1, 4),
                "uncertainties": (2, 4),
            },
            ["findings requires 7-10 items, got 12"],
        )

        self.assertIn("findings MUST contain exactly 8 items", instruction)
        self.assertIn("assumptions MUST contain exactly 2 items", instruction)
        self.assertIn("uncertainties MUST contain exactly 3 items", instruction)
        self.assertIn("Do not return fewer or more", instruction)

    def test_structured_attempt_replays_exact_response_on_resume(self) -> None:
        prompt = "exact prompt"
        response = {"findings": [], "assumptions": [], "uncertainties": []}
        with TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            current = run_dir / "attempts" / "research" / "current.json"
            current.parent.mkdir(parents=True)
            current.write_text('{"execution_id":"cache-key"}', encoding="utf-8")
            ArtifactDagRunner._persist_attempt(
                run_dir, "research", "analysis", prompt,
                canonical_json_bytes(response), "json",
            )

            recovered = ArtifactDagRunner._recover_structured_attempt(
                run_dir, "research", "analysis", prompt
            )

        self.assertEqual(response, recovered)

    def test_surplus_is_trimmed_and_only_deficit_is_reported(self) -> None:
        result, actions, deficits = _normalize_collection_counts(
            {
                "findings": list(range(11)),
                "assumptions": ["a"],
                "uncertainties": ["u"],
            },
            {
                "findings": (7, 10),
                "assumptions": (1, 4),
                "uncertainties": (2, 4),
            },
        )

        self.assertEqual(10, len(result["findings"]))
        self.assertEqual({"uncertainties": 1}, deficits)
        self.assertEqual("truncate_surplus", actions[0]["action"])

    def test_truncation_gets_bounded_bilingual_retry_budget(self) -> None:
        error = RuntimeError(
            "structured output truncated at max_tokens=16000 — raise this step's token budget"
        )
        self.assertEqual(24000, _escalated_token_budget(16000, error))
        self.assertIsNone(
            _escalated_token_budget(16000, RuntimeError("network failure"))
        )


if __name__ == "__main__":
    unittest.main()
