#!/usr/bin/env python3
"""Dry-run one round entirely on the deterministic mock backend, into a
scratch folder (outputs/mock_sprint/) — no git commits, no API calls. Used to
test the pipeline plumbing and as the no-keys demo path."""
import os
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
os.environ["LAB_FORCE_MOCK"] = "1"

from lab import agents, evaluation, pipeline, util

util.ITER_DIR = util.OUTPUTS_DIR / "mock_sprint"


def main():
    agents.scaffold()
    artifacts = pipeline.run_round(1)
    dims7 = evaluation.score_seven(artifacts, 1)
    payload = {"round": 1, "prev_total": None,
               "total": round(sum(d["score"] for d in dims7.values()) / 7, 3),
               "dimension_scores": {k: v["score"] for k, v in dims7.items()},
               "weakest": min(dims7, key=lambda k: dims7[k]["score"]),
               "translation": artifacts["translation"],
               "fallbacks": artifacts["fallbacks"]}
    meta_text = pipeline.run_meta_critic(1, artifacts, payload)
    dims = dict(dims7)
    dims["meta_system_eval"] = evaluation.meta_dimension(meta_text, artifacts, 1)
    ev = evaluation.finalize(1, dims, artifacts, None)
    print("mock sprint total:", ev["total"])
    for name, d in ev["dimensions"].items():
        print(f"  {name}: {d['score']} ({d['method']})")
    print("outputs in", artifacts["round_dir"])


if __name__ == "__main__":
    main()
