#!/usr/bin/env python3
"""Recompute a round's deterministic score components from its existing
(real, live-generated) artifacts on disk, using the CURRENT evaluation.py
det_* functions, then re-derive score/method exactly as
evaluation._compose() would — reusing the already-real, already-obtained LLM
judge trials stored in evaluation.json (never re-calling the LLM). Writes
through the same write_json/write helpers finalize.py uses.

Use this ONLY after fixing a bug in a det_* function. It re-derives a score
from unchanged real artifacts under corrected code; it never invents or
hand-sets a value, and it never touches the LLM side of a dimension.

    scripts/rescore_round.py 6 7
"""
import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lab import evaluation as ev
from lab import topic
from lab.util import load_config, read, read_json, round_dir, write, write_json

THRESHOLD = load_config()["evaluation"]["judge_divergence_threshold"]


def load_artifacts(n):
    rd = round_dir(n)
    return {
        "round_dir": rd,
        "brief_en": read(rd / "brief.en.md"),
        "experts": {p.stem: read(p) for p in (rd / "expert_outputs").glob("*.md")},
        "scenarios_en": read_json(rd / "scenarios.json"),
    }


def _propagate_prev_total(n, new_total):
    """Keep round n+1's stored prev_total/delta consistent if it's on disk."""
    next_path = round_dir(n + 1) / "evaluation.json"
    if not next_path.exists():
        return
    nxt = read_json(next_path)
    if nxt.get("prev_total") == new_total:
        return
    nxt["prev_total"] = new_total
    nxt["delta"] = round(nxt["total"] - new_total, 3)
    write_json(next_path, nxt)
    print(f"  (propagated: round {n + 1}'s prev_total -> {new_total}, "
          f"delta -> {nxt['delta']:+.3f})")


def rescore(n):
    rd = round_dir(n)
    a = load_artifacts(n)
    data = read_json(rd / "evaluation.json")
    changed = []

    for dim, fn in (("layer_separation", ev.det_layer_separation),
                    ("evidence_discipline", ev.det_evidence_discipline)):
        entry = data["dimensions"][dim]
        new_det = round(fn(a), 3)
        if new_det == entry["deterministic"]:
            continue
        old_score = entry["score"]
        entry["deterministic"] = new_det
        L = entry.get("llm")
        if L is None:
            entry["score"] = new_det
            entry["method"] = "deterministic (rescored: scripts/rescore_round.py)"
        else:
            flagged = abs(L["mean"] - new_det) > THRESHOLD
            L["divergence_flagged"] = flagged
            if flagged:
                entry["score"] = new_det
                entry["method"] = ("deterministic (LLM diverged; flagged for "
                                    "human) [rescored: scripts/rescore_round.py]")
            else:
                entry["score"] = round(ev.DET_WEIGHT * new_det
                                        + (1 - ev.DET_WEIGHT) * L["mean"], 3)
                entry["method"] = (f"mixed ({ev.DET_WEIGHT} det + "
                                   f"{1 - ev.DET_WEIGHT:.1f} llm) "
                                   "[rescored: scripts/rescore_round.py]")
        changed.append((dim, old_score, entry["score"]))

    new_total = round(statistics.fmean(d["score"] for d in data["dimensions"].values()), 3)
    old_total = data["total"]
    data["delta"] = None if data["prev_total"] is None else round(new_total - data["prev_total"], 3)
    data["total"] = new_total
    data["divergence_flagged"] = [name for name, d in data["dimensions"].items()
                                  if d.get("llm", {}).get("divergence_flagged")]
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
    _propagate_prev_total(n, new_total)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rounds", nargs="+", type=int)
    ap.add_argument("--topic", default=None,
                    help="topic slug; default: config default_topic")
    args = ap.parse_args()
    topic.set_current(args.topic)
    for n in sorted(args.rounds):
        rescore(n)


if __name__ == "__main__":
    main()
