# Two-topic full live acceptance: educational_psychology (issue #19, PR #29)

**Date:** 2026-07-18/19/20 · **Branch:** `exp/educational-psychology-expert` · **Tracker:** #19, #9, #30, #31

## What this is

Owner direction on PR #29 (2026-07-18): the smaller A/B sensitivity experiment
(`docs/experiments/2026-07-18-psychology-expert-sensitivity.md`) is useful
admission evidence but does not substitute for running the expanded
13-expert panel through a full canonical round on both live topics, start to
finish (experts → scenarios → synthesis → discourse → brief → critics →
meta-critic → evaluation), with a fresh live 13-expert phase
(`LAB_FRESH_EXPERTS=1`) and a separate option-space (frame) sensitivity
check, stopping at the human gate. This report covers that full run.

## Rounds run

- `korai-szelekcio` round_10 (era baseline round_09, total 9.45)
- `rural-school-closures` round_03 (era baseline round_02, total 9.252)

Both under `GENERATOR_PROVIDER=anthropic JUDGE_PROVIDER=openai
LAB_FRESH_EXPERTS=1`.

## Results

| | korai-szelekcio round_10 | rural-school-closures round_03 |
|---|---|---|
| total score | 9.366 (Δ **-0.084**) | 9.451 (Δ **+0.199**) |
| verify.py | **FAILED** (check 3: era non-decreasing) | PASSED |
| mock/failed steps (final commit) | 0 | 0 |
| documented directive change | none (meta_quant applied then reverted, no replacement found — see below) | layer_tighten (unrelated, pre-existing plan) |
| relaunches | 4 (round_meta.json starts) | 4 |
| this round's own metered cost (issue #22 caveat: undercounts resumed legs) | ~$11.17 (2,614,798 in / 393,599 out tokens) | ~$2.09 (571,955 in / 131,990 out) |

## 1. Frame/option-space stability: unaffected by the panel expansion

`new_topic.py propose-frames` was run on both topics' fresh 13-expert
records (round_10, round_03), per the sanctioned D-36 diagnostic path — NOT
approved, NOT hand-edited, the run stopped at the human gate as required.

**Both topics' freshly-derived 5-frame proposals map 1:1 onto the currently
approved, frozen frames** — same five policy families, same rejected
framings (full abolition, pure deregulation, retention-based selection,
etc.), just reworded. No sixth frame emerged; none of the five disappeared.
**Conclusion: adding the psychology expert did not change either topic's
option space.**

## 2. korai-szelekcio's -0.084 regression: root-caused, not a real panel effect

### It is NOT a directive-confound

Round 10's launch auto-applied round 9's planned change (`meta_quant`,
targeting only `meta_critic`'s spec). It regressed (-0.189 in the
intermediate attempt) and was reverted; `improve.select_change` found no
replacement candidate, so the **final committed round_10 is a clean
baseline** (`plan.json`: `"next_change_id": null`; `revised_agents.md`:
"Baseline round: no system change applied yet"). Verified byte-identical:
`agents/synthesis/{editor,scenario_builder,final_brief_writer}.md` between
round_09's snapshot and the current tree. The only variable versus round_09
is the panel (12→13) and ordinary expert-rerun variance.

### Where the -0.084 concentrates

Per-dimension delta (unweighted average of 8 = the -0.084 total):

| dimension | Δ |
|---|---|
| uncertainty_explicitness | **-0.800** |
| layer_separation | -0.182 |
| evidence_discipline | -0.173 |
| meta_system_eval | -0.100 |
| translation_fidelity | **+0.583** |
| scenario_completeness, critic_concreteness, disagreement_preservation | 0 |

`uncertainty_explicitness` alone drives nearly the whole delta.
`det_uncertainty_explicitness` (`lab/evaluation.py`) is a **deterministic**
formula: `10 × (0.3·has + 0.25·conf_en + 0.17·conf_hu + 0.28·reducer)`,
where `has` = (scenario uncertainty-item count) / (3 × scenario count).
Round_09: 15/15 items (has=1.0). Round_10: 11/15 (has=0.733). The
`conf_en`/`conf_hu` terms are 0 in **both** rounds (a pre-existing, branch-
independent scoring quirk: `confidence` is a separate schema field, never a
literal "confidence:" substring — worth its own issue, not filed here).
Solving the formula confirms the delta is arithmetically exact: this single
`has` term change explains -0.8 points on its own.

### Ablation: panel effect or metric noise?

Four ablation cells (fixed prompts/schema, one live `scenario_builder` call
each): **A** = round_09's old 12 experts, **B** = old 12 + the live psych
expert (reusing the PR #29 sensitivity artifact), **C** = round_10's fresh
12 (no psych), **D** = round_10's fresh 12 + psych (= the actual round_10
scenario_builder call).

| cell | at 48,000 max_tokens | at 64,000 max_tokens |
|---|---|---|
| A (old 12) | 15/15 | 15/15 |
| B (old 12 + psych) | — | 15/15 |
| C (fresh 12) | 15/15 | **13/15** |
| D (fresh 12 + psych) | **11/15** | **15/15** |

At 48K the pattern looked like a clean panel effect (A=C=15, only D drops).
At 64K the pattern **inverts** (C drops, D recovers) — proof that neither
expert count nor token budget alone explains the item count; this is
**single-sample LLM output variance** in how many uncertainties the model
enumerates per scenario, not a reproducible effect of the psychology
expert. Content check: C's two under-filled scenarios (S2, S5) are missing
one **arbitrary** sub-question each — no thematic pattern, no evidence the
missing item was ever "crowded out" by psychology content (C has no
psychology expert in its digest at all). Full detail: issue #30 comment
(2026-07-19) and `outputs/experiments/{cell_c_fresh12_no_psych,
four_cells_64k}/`.

**Conclusion:** the -0.084 total is real (it is what got committed and
scored) but its primary driver is a metric-level artifact, not a
reproducible cost of the panel expansion. The verify.py failure is
understood and, in the owner's judgment, does not block treating round_10
as valid acceptance evidence — no further live round was run to "fix" the
score, since doing so would not isolate anything additional (issue #30
tracks the general fix: never trust this class of single-sample metric
without replicates).

## 3. Position carriage: confirmed a third time, at full-round scale

In **both** full rounds, `educational_psychology` is carried as a **holder
name** into the synthesis disagreement map (3 sides in korai, 1 in rural)
but **zero** occurrences of psychology-specific content (self-concept,
BFLPE, labeling, stereotype threat, motivation, goal orientation) appear
anywhere in either round's synthesis or brief text, and the expert never
appears in either brief's `minority_positions`. This exactly replicates the
smaller PR #29 A/B experiment's finding, now confirmed independently in two
full, live, 13-expert canonical rounds. This is the strongest evidence yet
for #9's carriage-fix priority: the editor absorbs a new holder into
existing coalitions by apparent topical proximity, not by verifying the
side's stated position actually subsumes the new expert's own claim.

## 4. Infra fixes made mid-run (not part of the panel-expansion variable)

- `discourse` voice step: `max_tokens` 40,000 → 56,000 (rural's
  `digitalisgazdasagi` voice hit a fatal structured-output truncation under
  the 5-frame scenario set).
- `scenario_builder` step: `max_tokens` 48,000 → 64,000 (found via the
  ablation above; a real, if now understood to be non-decisive, headroom
  constraint under a growing digest).

Both committed to `scripts/lab/pipeline.py`, documented in commit messages,
applied uniformly (shared code, both topics).

## 5. Operational incidents (both fully resolved via the sanctioned resume path)

- A ~4-hour live-API ReadTimeout window (both topics simultaneously)
  crashed one expert each (`ex.map()`'s in-order `.result()` re-raise
  propagates the first failed future once the round otherwise finishes) —
  relaunching the same command resumed everything else and only retried
  the failed expert(s).
- A recurring real machine-sleep cycle (`pmset` log: repeated ~15-17 min
  "Maintenance Sleep" windows from 01:14 onward) defeated `caffeinate -i`
  (idle-sleep only); switching to `caffeinate -s -i` (full system-sleep
  prevention) fixed it for the remainder of the run.
- korai-szelekcio's `political_feasibility` expert hit the same
  ReadTimeout pattern once more later in a separate window; same resume
  recovery.

Each topic shows 4 launch attempts in `round_meta.json`'s `starts` — the
audit trail is complete and matches CLAUDE.md's documented "quota limits
are survivable — relaunch the same command" guidance exactly.

## Cost summary

- korai-szelekcio round_10 (this round's own metering; **known to
  undercount** per issue #22, since the round went through a full second
  live pass after the meta_quant revert — true cost is plausibly ~2×):
  ~$11.17.
- rural-school-closures round_03 (single clean pass after the voice-budget
  fix): ~$2.09.
- Diagnostic experiments (this report): Cell C ~$1, four-cell ablation
  ~$4-5 (not separately itemized — see `backend_usage` absent for these ad
  hoc scripts, another instance of issue #31's motivation).
- Smaller PR #29 A/B sensitivity experiment (prior report): $5.43.

## New issues filed from this work

- **#30** (updated): the `uncertainty_explicitness` / scenario-item-count
  metric is unreliable at n=1; the four-cell ablation is the concrete
  evidence. Any future panel-sensitivity or ablation experiment using this
  class of metric needs replicates, not single samples.
- **#31** (new): no step's exact prompt is ever persisted to disk; this
  cost real debugging time in this session (a first ad hoc diagnostic
  silently used the wrong generator provider because there was nothing to
  check it against). Proposed: `Step.run()` writes each built prompt
  alongside its other outputs.

## Recommendation

- **Admission**: the frame-stability result (§1) and the double-confirmed
  carriage failure (§3) are the two decision-relevant findings. The seat
  brings no new frame risk; it does bring the same carriage problem #9
  already flagged, now proven at full-round scale twice more.
- **korai-szelekcio's verify.py failure**: accept as a documented,
  root-caused exception (§2) rather than spend further live-round budget
  chasing a metric-noise artifact — recommend the owner formally waive
  check 3 for this round in the merge decision, or re-run once more *only*
  after #9's carriage fix lands (which is likely to change the score
  picture anyway, per D-16/one-change-per-round discipline).
- **#9's carriage fix is now the highest-priority follow-up**, not #30 or
  #31 — those are real but lower-stakes findings.
