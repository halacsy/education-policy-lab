from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from policy_lab.migration import V1CorpusCompiler
from policy_lab.i18n import BILINGUAL_VERSION, load_field_map, validate_bilingual_content

ROOT = Path(__file__).resolve().parents[2]


class V1CorpusCompilerTests(unittest.TestCase):
    def test_compiles_valid_bilingual_graph_and_resumes_from_cache(self) -> None:
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
            field_map = load_field_map(ROOT)
            for record in compiler.repository.list(topic="korai-szelekcio"):
                if record["record_type"] not in field_map:
                    continue
                self.assertEqual(record["schema_version"], BILINGUAL_VERSION)
                validate_bilingual_content(
                    record["record_type"], record["content"], field_map
                )


if __name__ == "__main__":
    unittest.main()
