#!/usr/bin/env python3
"""Run one fresh artifact-DAG production replicate for one or more topics."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

# Provider selection must precede lab.llm import. D-58 restores D-34 native
# bilingual generation while retaining the cross-family generator/judge gate.
os.environ["GENERATOR_PROVIDER"] = "anthropic"
os.environ["JUDGE_PROVIDER"] = "openai"
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")

from lab import llm  # noqa: E402
from policy_lab.jsonio import write_json  # noqa: E402
from policy_lab.dag import HumanGatePending  # noqa: E402
from policy_lab.live import ArtifactDagRunner  # noqa: E402

DEFAULT_TOPICS = ("korai-szelekcio", "rural-school-closures")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", action="append", dest="topics")
    parser.add_argument("--run-tag", default="2026-07-20-live")
    parser.add_argument("--output-root", type=Path, default=ROOT / "v2" / "production")
    args = parser.parse_args()
    topics = tuple(args.topics or DEFAULT_TOPICS)
    if llm.provider_for_role("generator") == llm.provider_for_role("judge"):
        raise SystemExit("generator and judge provider families must differ")

    run_root = args.output_root / args.run_tag
    entries = []
    for topic in topics:
        topic_root = run_root / topic
        runner = ArtifactDagRunner(
            root=ROOT, output_root=topic_root, llm_module=llm, topic=topic,
        )
        try:
            summary = runner.run_production()
        except HumanGatePending as exc:
            gate_command = (
                "approve-brief" if exc.gate_id == "approve_problem_brief"
                else "approve"
            )
            gate_label = (
                "problem brief" if exc.gate_id == "approve_problem_brief"
                else "option space"
            )
            rationale_hint_en = (
                "WHY THIS BRIEF IS A SOUND RESEARCH CONTRACT"
                if exc.gate_id == "approve_problem_brief"
                else "WHY THIS OPTION SPACE IS COMPLETE"
            )
            rationale_hint_hu = (
                "MIÉRT MEGALAPOZOTT KUTATÁSI SZERZŐDÉS EZ A PROBLÉMAFELVETÉS"
                if exc.gate_id == "approve_problem_brief"
                else "MIÉRT TELJES EZ AZ OPCIÓTÉR"
            )
            print(
                "\nProduction run paused at the declared human gate.\n"
                f"Gate: {gate_label}\n"
                f"Candidate hash: {exc.candidate_hash}\n"
                f"Review request: {exc.request_path}\n"
                "Approve only after reviewing the exact candidate:\n"
                f"  .venv/bin/python scripts/v2_gate.py {gate_command} --topic {topic} "
                f"--run-tag {args.run_tag} --candidate-hash {exc.candidate_hash} "
                f"--decided-by YOUR_NAME --rationale-en '{rationale_hint_en}' "
                f"--rationale-hu '{rationale_hint_hu}'\n"
                "Then relaunch the same production command.",
                file=sys.stderr,
            )
            return 2
        entries.append({
            "topic": topic,
            "output_root": str(topic_root.relative_to(ROOT)),
            "run_id": summary["run_id"],
            "package_ref": summary["package_ref"],
            "evaluation_ref": summary["evaluation_ref"],
            "readiness_ref": summary["readiness_ref"],
            "evaluation_total": summary["evaluation"]["total"],
            "readiness_verdict": summary["readiness"]["verdict"],
        })
        write_json(run_root / "catalog.json", {
            "architecture_version": "3.0.0",
            "run_tag": args.run_tag,
            "topics": entries,
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
