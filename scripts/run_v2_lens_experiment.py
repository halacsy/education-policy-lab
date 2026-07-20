#!/usr/bin/env python3
"""Run the live v2 baseline and PR #29 educational-psychology lens treatment."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

# Provider choice must be set before importing lab.llm, which resolves model
# overrides after loading .env. Generator and judge intentionally differ.
os.environ["GENERATOR_PROVIDER"] = "anthropic"
os.environ["JUDGE_PROVIDER"] = "openai"
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")

from lab import llm  # noqa: E402
from policy_lab.live import PsychologyLensExperiment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("baseline", "psychology", "both"), default="both")
    parser.add_argument("--topic", default="korai-szelekcio")
    parser.add_argument("--reports-only", action="store_true")
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "v2" / "experiments" / "2026-07-20-psychology-lens-live",
    )
    args = parser.parse_args()
    if llm.provider_for_role("generator") == llm.provider_for_role("judge"):
        raise SystemExit("generator and judge provider families must differ")
    arms = ("baseline", "psychology") if args.arm == "both" else (args.arm,)
    experiment = PsychologyLensExperiment(
        root=ROOT, output_root=args.output, llm_module=llm, topic=args.topic,
    )
    if args.reports_only:
        experiment.rebuild_reports()
    else:
        experiment.run(arms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
