from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from policy_lab.migration import V1CorpusCompiler

ROOT = Path(__file__).resolve().parents[2]


def contains_bilingual_shape(value: object) -> bool:
    if isinstance(value, dict):
        if "en" in value or "hu" in value:
            return True
        return any(contains_bilingual_shape(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_bilingual_shape(item) for item in value)
    return False


class V1CorpusCompilerTests(unittest.TestCase):
    def test_compiles_valid_english_only_graph_and_resumes_from_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            compiler = V1CorpusCompiler(ROOT, temporary)
            first = compiler.compile_topic("korai-szelekcio", "round_09")
            self.assertEqual(first["artifact_counts"]["finding"], 124)
            self.assertEqual(first["artifact_counts"]["transformation_proposal"], 5)
            self.assertEqual(first["artifact_counts"]["lens_assessment"], 60)

            compiler.compile_topic("korai-szelekcio", "round_09")
            event_path = (
                Path(temporary) / "runs" / "migration-korai-szelekcio"
                / "events.jsonl"
            )
            events = [json.loads(line) for line in event_path.read_text().splitlines()]
            self.assertEqual(
                [event["event_type"] for event in events[-6:]],
                ["node_cache_hit"] * 6,
            )
            for record in compiler.repository.list(topic="korai-szelekcio"):
                self.assertFalse(contains_bilingual_shape(record["content"]))


if __name__ == "__main__":
    unittest.main()
