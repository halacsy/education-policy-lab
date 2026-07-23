#!/usr/bin/env python3
"""Run an internal architecture-3.2 overlay over published 3.1 snapshots."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["GENERATOR_PROVIDER"] = "anthropic"

from lab import llm  # noqa: E402
from policy_lab.live.overlay import SnapshotOverlayRunner  # noqa: E402


DEFAULT_TOPICS = ("korai-szelekcio", "rural-school-closures")
DEFAULT_SOURCE_TAG = "2026-07-21-v3-bilingual"
DEFAULT_OUTPUT_TAG = "2026-07-22-v32-snapshot-overlay"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reuse exact architecture-3.1 research artifacts and run only the "
            "3.2 normalization, option-seed, clustering, and trace comparison nodes."
        )
    )
    parser.add_argument("--topic", action="append", dest="topics")
    parser.add_argument("--source-run-tag", default=DEFAULT_SOURCE_TAG)
    parser.add_argument("--output-tag", default=DEFAULT_OUTPUT_TAG)
    parser.add_argument(
        "--output-root", type=Path,
        default=ROOT / "v2" / "experiments",
    )
    parser.add_argument(
        "--repair-attempt-provenance", action="store_true",
        help=(
            "Adopt unambiguous immutable response files into missing current "
            "provenance without executing any DAG node."
        ),
    )
    args = parser.parse_args()
    topics = tuple(args.topics or DEFAULT_TOPICS)
    for topic in topics:
        source_root = ROOT / "v2" / "production" / args.source_run_tag / topic
        if not source_root.exists():
            raise SystemExit(f"Missing source production store: {source_root}")
        output_root = args.output_root / args.output_tag / topic
        runner = SnapshotOverlayRunner(
            root=ROOT, output_root=output_root, llm_module=llm, topic=topic,
        )
        if args.repair_attempt_provenance:
            runner.repair_existing_attempt_provenance()
            print(f"REPAIRED {topic}: exact attempt provenance", flush=True)
            continue
        manifest = runner.run_overlay(
            source_root=source_root, source_run_tag=args.source_run_tag,
        )
        summary = manifest["summary"]
        print(
            f"OVERLAY {topic}: seeds={summary['seed_count']}, "
            f"uncovered={summary['uncovered_seed_count']}, "
            f"directions={summary['new_direction_count']}, "
            f"novel_gaps={summary['novel_gap_count']}, "
            f"conflicts={summary['evidence_conflict_count']}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
