#!/usr/bin/env python3
"""Recompute the deterministic-only dimensions of a completed round from its
existing (real, live-generated) artifacts on disk, using the current
evaluation.py scoring functions, and rewrite evaluation.json/.md through the
same write helpers the pipeline itself uses.

Use this ONLY after fixing a bug in a deterministic scorer (evaluation.py's
det_* functions with method == "deterministic", not "mixed"/LLM-scored) —
it re-derives a score from real artifacts under corrected code, it does not
invent or hand-set a value. LLM-scored dimensions are left untouched: fixing
those honestly requires a real re-run, not a recompute.

    scripts/rescore_round.py 6 7
"""
import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lab import evaluation as ev
from lab.util import read, read_json, round_dir, write, write_json


def load_artifacts(n):
    rd = round_dir(n)
    return {
        "round_dir": rd,
        "brief_en": read(rd / "brief.en.md"),
        "experts": {p.stem: read(p) for p in (rd / "expert_outputs").glob("*.md")},
        "scenarios_en": read_json(rd / "scenarios.json"),
    }


def rescore(n):
    rd = round_dir(n)
    a = load_artifacts(n)
    data = read_json(rd / "evaluation.json")
    changed = []

    for dim, fn in (("layer_separation", ev.det_layer_separation),
                    ("evidence_discipline", ev.det_evidence_discipline)):
        entry = data["dimensions"][dim]
        if "llm" in entry:
            raise SystemExit(f"round {n}: {dim} is LLM-scored (method="
                              f"{entry['method']!r}) — this script only "
                              "recomputes deterministic-only dimensions.")
        new_det = round(fn(a), 3)
        if new_det != entry["deterministic"]:
            changed.append((dim, entry["score"], new_det))
            entry["deterministic"] = new_det
            entry["score"] = new_det
            entry["method"] = "deterministic (rescored: scripts/rescore_round.py)"

    new_total = round(statistics.fmean(d["score"] for d in data["dimensions"].values()), 3)
    old_total = data["total"]
    data["delta"] = None if data["prev_total"] is None else round(new_total - data["prev_total"], 3)
    data["total"] = new_total
    write_json(rd / "evaluation.json", data)

    lines = [f"# Evaluation — round {n}", "",
             f"Total: **{new_total}**" + (f" (delta {data['delta']:+.3f})" if data["delta"] is not None else " (baseline)"),
             "",
             "| dimension | score | method | det | llm mean | llm var |",
             "|---|---|---|---|---|---|"]
    for name, d in data["dimensions"].items():
        L = d.get("llm", {})
        lines.append(f"| {name} | {d['score']} | {d['method']} | "
                     f"{d['deterministic']} | {L.get('mean', '—')} | "
                     f"{L.get('variance', '—')} |")
    lines += ["",
              f"Generator: {data['generator_provider']}; judge: {data['judge_provider']}.",
              f"Divergence-flagged dimensions (sent to human review): "
              f"{data['divergence_flagged'] or 'none'}.",
              f"Steps that degraded to the deterministic mock: "
              f"{data['step_fallbacks'] or 'none'}.",
              "",
              f"Rescored by scripts/rescore_round.py after a scorer bug fix "
              f"(total was {old_total} before rescoring)."]
    write(rd / "evaluation.md", "\n".join(lines) + "\n")

    print(f"round {n}: total {old_total} -> {new_total}")
    for dim, old_score, new_det in changed:
        print(f"  {dim}: score {old_score} -> {new_det}")
    if not changed:
        print("  (no dimension changed under the current code)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rounds", nargs="+", type=int)
    args = ap.parse_args()
    for n in args.rounds:
        rescore(n)


if __name__ == "__main__":
    main()
