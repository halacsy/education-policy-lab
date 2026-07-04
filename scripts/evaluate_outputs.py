#!/usr/bin/env python3
"""Re-evaluate an existing round folder from disk (no generation):

    python scripts/evaluate_outputs.py --round 2 [--write]

Recomputes deterministic components and LLM-judge trials on the stored
artifacts; with --write, overwrites the round's evaluation.json/md."""
import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from lab import evaluation
from lab.loadround import load_artifacts
from lab.util import read_json, round_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    n = args.round
    a = load_artifacts(n)
    dims = evaluation.score_seven(a, n)
    dims["meta_system_eval"] = evaluation.meta_dimension(a["meta"], a, n)
    prev = None
    prev_path = round_dir(n - 1) / "evaluation.json"
    if n > 1 and prev_path.exists():
        prev = read_json(prev_path)["total"]
    if args.write:
        ev = evaluation.finalize(n, dims, a, prev)
        print(f"re-evaluated round {n}: total {ev['total']} (written)")
    else:
        import statistics
        total = round(statistics.fmean(d["score"] for d in dims.values()), 3)
        print(f"round {n} re-evaluation (dry run): total {total}")
        for name, d in dims.items():
            print(f"  {name}: {d['score']} ({d['method']})")


if __name__ == "__main__":
    main()
