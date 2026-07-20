#!/usr/bin/env python3
"""Build the deterministic v2 vertical-slice corpus from committed v1 rounds."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.jsonio import write_json  # noqa: E402
from policy_lab.migration import V1CorpusCompiler  # noqa: E402

TOPICS = {
    "korai-szelekcio": "round_09",
    "rural-school-closures": "round_02",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", choices=sorted(TOPICS), action="append")
    parser.add_argument("--output", type=Path, default=ROOT / "v2")
    args = parser.parse_args()
    topics = args.topic or list(TOPICS)
    compiler = V1CorpusCompiler(ROOT, args.output)
    manifests = [compiler.compile_topic(topic, TOPICS[topic]) for topic in topics]
    write_json(args.output / "catalog" / "topics.json", {
        "architecture_version": "2.0.0",
        "topics": manifests,
    })
    for manifest in manifests:
        counts = ", ".join(
            f"{name}={count}"
            for name, count in manifest["artifact_counts"].items()
        )
        print(f"{manifest['topic']}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
