#!/usr/bin/env python3
"""Run the self-improving iteration loop.

    python scripts/run_iteration_loop.py --max-rounds 5

Each round: (apply previous plan) → experts → scenarios → synthesis →
translation → critics → meta-critic → score → improvement plan → git commit.
Stops on max rounds, plateau, exhausted change catalog, or a blocking human
question. A change that lowers the total is reverted, archived as a failure,
replaced, and the round is re-run (docs/decisions.md D-16).
"""
import argparse
import sys
import time

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from lab import agents, evaluation, finalize, gitutil, improve, llm, memory, pipeline
from lab.util import load_config, read_json, round_dir


def meta_payload(n, dims7, prev_eval, artifacts, applied):
    provisional = round(sum(d["score"] for d in dims7.values()) / len(dims7), 3)
    return {
        "round": n,
        "prev_total": prev_eval["total"] if prev_eval else None,
        "total": provisional,
        "note": "total is provisional over the 7 content dimensions",
        "dimension_scores": {k: v["score"] for k, v in dims7.items()},
        "prev_dimension_scores": ({k: v["score"] for k, v in
                                   prev_eval["dimensions"].items()}
                                  if prev_eval else None),
        "weakest": min(dims7, key=lambda k: dims7[k]["score"]),
        "applied_change": ({"id": applied["id"], "dimension": applied["dimension"],
                            "targets": applied["targets"][:6]} if applied else None),
        "translation": {k: artifacts["translation"][k] for k in
                        ("id_sets_equal", "structure_equal", "glossary_violations")},
        "discourse": artifacts.get("discourse"),
        "fallbacks": artifacts["fallbacks"],
        "judge_divergence": None,  # known only after finalize; prior rounds' flags:
        "prev_divergence_flagged": (prev_eval or {}).get("divergence_flagged"),
    }


def evaluate_round(n, prev_eval, applied):
    artifacts = pipeline.run_round(n)
    dims7 = evaluation.score_seven(artifacts, n)
    payload = meta_payload(n, dims7, prev_eval, artifacts, applied)
    meta_text = pipeline.run_meta_critic(n, artifacts, payload)
    dims = dict(dims7)
    dims["meta_system_eval"] = evaluation.meta_dimension(meta_text, artifacts, n)
    ev = evaluation.finalize(n, dims, artifacts,
                             prev_eval["total"] if prev_eval else None)
    return artifacts, ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-rounds", type=int, default=5)
    ap.add_argument("--start-round", type=int, default=1,
                    help="restart an interrupted run: completed rounds before "
                         "this are loaded from disk, the interrupted round "
                         "resumes from its valid artifacts")
    args = ap.parse_args()
    cfg = load_config()
    plateau_delta = cfg["stopping"]["plateau_delta"]
    plateau_rounds = cfg["stopping"]["plateau_rounds"]

    created = agents.scaffold()
    if created:
        print(f"scaffolded {len(created)} agent specs")

    history = []
    prev_eval = None
    planned = None
    stop_reason = None

    if args.start_round > 1:
        for k in range(1, args.start_round):
            history.append(read_json(round_dir(k) / "evaluation.json"))
        prev_eval = history[-1]
        plan = read_json(round_dir(args.start_round - 1) / "plan.json")
        planned = next((c for c in improve.CATALOG
                        if c["id"] == plan.get("next_change_id")), None)
        print(f"restarting at round {args.start_round} "
              f"(prev total {prev_eval['total']}, planned change: "
              f"{planned['id'] if planned else 'none'})")

    for n in range(args.start_round, args.max_rounds + 1):
        t0 = time.time()
        applied, touched = None, []
        if planned is not None:
            touched = improve.apply_change(planned, n)
            applied = planned
            print(f"[round {n:02d}] applied change {planned['id']} "
                  f"({len(touched)} specs touched)")

        excluded, artifacts, ev = [], None, None
        for retry in range(3):
            artifacts, ev = evaluate_round(n, prev_eval, applied)
            if applied is not None:
                improve.set_actual_delta(applied["id"], n, ev["delta"])
            if applied is None or ev["delta"] is None or ev["delta"] >= -0.02:
                break
            # regression: revert, archive the failure, try the next candidate
            print(f"[round {n:02d}] change {applied['id']} regressed "
                  f"({ev['delta']:+.3f}) — reverting and replacing")
            improve.set_actual_delta(applied["id"], n, ev["delta"], reverted=True)
            improve.revert_change(applied)
            excluded.append(applied["id"])
            replacement = improve.select_change(prev_eval, exclude=excluded)
            if replacement is None:
                stop_reason = ("Stopped: every remaining catalog change for "
                               "the weak dimensions regressed or is exhausted "
                               "(see attempts_log.jsonl).")
                applied, touched = None, []
                artifacts, ev = evaluate_round(n, prev_eval, None)
                break
            applied = replacement
            touched = improve.apply_change(replacement, n)

        rd = round_dir(n)
        improve.write_change_docs(rd, n, applied, touched, prev_eval)
        history.append(ev)

        # stopping decision (before writing the plan, so the plan records it)
        next_change = improve.select_change(ev)
        deltas = [e["delta"] for e in history if e["delta"] is not None]
        if stop_reason:
            decision = stop_reason
        elif n == args.max_rounds:
            decision = f"Stop: --max-rounds {args.max_rounds} reached."
        elif (len(deltas) >= plateau_rounds
              and all(abs(d) < plateau_delta for d in deltas[-plateau_rounds:])):
            decision = (f"Stop: total-score delta below {plateau_delta} for "
                        f"{plateau_rounds} consecutive rounds (marginal "
                        "improvement; see final report).")
        elif next_change is None:
            decision = ("Stop: no untried, non-forbidden change remains in "
                        "the catalog (archive consulted); further gains need "
                        "a human decision on new change types.")
        else:
            decision = (f"Continue: apply {next_change['id']} next round; no "
                        "blocking human question is open (open questions are "
                        "tracked in human_questions.md).")

        improve.write_plan(rd, n, ev, next_change, artifacts, applied, decision)
        memory.update_memories(n, artifacts)

        if applied:
            msg = (f"round-{n:02d}: apply {applied['id']} to "
                   f"{applied['dimension']} (weakest last round) — total "
                   f"{ev['prev_total']}->{ev['total']}")
        else:
            msg = (f"round-{n:02d}: baseline run (total {ev['total']}); plan: "
                   + (f"add {next_change['id']} for weakest dimension "
                      f"{next_change['dimension']}" if next_change else
                      "no further change available"))
        gitutil.commit(msg)
        print(f"[round {n:02d}] total={ev['total']} "
              f"delta={ev['delta']} ({int(time.time() - t0)}s) — committed")

        prev_eval = ev
        planned = next_change
        if not decision.startswith("Continue"):
            print(decision)
            break

    finalize.write_final(artifacts, history)
    gitutil.commit(
        f"final: bilingual deliverables + scorecard after {len(history)} rounds "
        f"(total {history[0]['total']}->{history[-1]['total']})")
    print("final outputs written to outputs/final/ and committed")
    print("backend usage:", llm.backend_stats())
    u = llm.token_stats()
    print("token usage (this process):", u["total"])
    for k, v in u["per_model"].items():
        print(f"  {k}: {v['calls']} calls, {v['tokens_in']} in / "
              f"{v['tokens_out']} out tokens, {v['ms']/1000:.0f}s"
              + (" (estimated)" if v["estimated"] else ""))


if __name__ == "__main__":
    main()
