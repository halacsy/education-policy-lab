# Experiment report: judge/generator role swap (robustness check)

**Question (external reviewer, 2026-07-06):** if the model roles are swapped —
Claude generates, Gemini judges — does the score trajectory reproduce, or was
the 9.23 an artifact of one judge? "If the swapped result is very different
from 9.23, the method may not be robust."

**Answer in one line:** the scores are robust to the swap — the final total
moved by +0.06 (9.230 → 9.290) under a full judge swap on identical
artifacts, and the improvement trajectory reproduced under swapped
generation — but this robustness is *by construction* (deterministic checks
dominate every dimension), so the honest claim is "the rubric is
judge-insensitive", not "any two judges agree".

## Experiment A — pure judge swap (identical artifacts, swapped scorers)

Rounds 1 and 5 of the committed main run were re-scored with roles swapped
(`JUDGE_PROVIDER=google`, `GENERATOR_PROVIDER=anthropic`; per-task model
ladder, all 30 LLM trials served live: gemini-2.5-flash/flash-lite and
claude-haiku-4-5). Deterministic components are identical by design; only the
LLM-judged 0.3-weight slice and the divergence flags could move.

| | original total | swapped total | Δ |
|---|---|---|---|
| round 1 | 7.072 | 7.041 | −0.031 |
| round 5 | 9.230 | 9.290 | +0.060 |
| improvement r1→r5 | +2.158 | +2.249 | +0.091 |

Where the judges actually disagreed, the protocol — not luck — kept the total
stable: in round 1 three dimensions diverged beyond threshold
(`evidence_discipline`, `critic_concreteness`, `disagreement_preservation`;
e.g. Gemini scored critic outputs 9.0 where the original pass had 4.15) and
were resolved to their deterministic score with a human-review flag, exactly
as the evaluator protocol prescribes. In round 5 no dimension diverged.

## Experiment B — swapped generation run (branch `experiment/swapped-roles`)

Fresh 2-round run from baseline agent specs: Claude generates (first fully
live generation — all 12 experts, scenarios, synthesis, translation, briefs;
haiku/sonnet/opus per the D-26 ladder with observed escalation on validation
retries), Gemini judges (live in round 1; partially degraded to the
deterministic heuristic mid-round-2 when the free-tier daily quota died —
recorded per step in steps.jsonl).

| | main run (Gemini gen → mostly mock) | swapped run (Claude gen, live) |
|---|---|---|
| round 1 total | 7.072 | 7.510 |
| round 2 total | 7.752 | 8.233 |
| delta from the same first change (`uncertainty_quantify`) | +0.680 | +0.723 |

The improvement loop behaved identically: same weakest dimension found
(`uncertainty_explicitness`), same change selected from the catalog, similar
delta. The +0.44 baseline shift is a *content* effect (live Claude generation
vs. the curated mock pack), not a judge effect — experiment A isolates the
judge effect at ±0.06.

## Limitations

- Experiment A covers rounds 1 and 5 only (free-tier daily quota); B covers
  2 rounds. A full 5-round swapped replication needs the paid key (issue #4).
- In B, the Gemini judge degraded partway through round 2 (quota), so its
  round-2 critic scores partially come from the deterministic heuristic —
  provenance in the branch's steps.jsonl.
- The deterministic dominance (≥0.7 weight per dimension) that produces this
  robustness is itself a design choice (D-15). A rubric with LLM-dominant
  scoring would likely NOT be this stable — the raw LLM means disagreed by up
  to 4.9 points on critic_concreteness. That disagreement is real and is why
  averaging judges naively is forbidden by the protocol.

## Verdict for the reviewer

The 9.23 is not a judge artifact: swap-invariance holds to within ±0.06 on
identical artifacts, and the self-improvement dynamics reproduce under
swapped generation. The robustness comes from (1) deterministic-first scoring
and (2) the divergence rule (never average disagreeing judges; fall back to
deterministic + flag a human) — i.e., from the parts of the design built for
exactly this failure mode.
