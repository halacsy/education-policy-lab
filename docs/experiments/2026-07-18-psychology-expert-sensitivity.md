# Experiment: expert-panel sensitivity v2 (adding educational_psychology)

**Date:** 2026-07-18 · **Branch:** `exp/educational-psychology-expert` · **Tracker:** issues #19, #9
**Script:** `scripts/exp_panel_sensitivity.py` · **Artifacts:** `outputs/experiments/psychology_panel_sensitivity/`

## Question (issue #19, protocol from #9)

Does adding ONE expert — `educational_psychology` (learning science + the
social psychology of selection: BFLPE, labeling/expectancy, stereotype
threat, goal orientation) — shift the synthesis: the disagreement map, the
scenarios, the brief? The v1 experiment (conservative_education, 2026-07-07)
found the risk is not a majority flip but **selective attrition** (the new
voice survives the map, then dies before the brief), and that single-sample
noise is comparable to the panel effect. v2 therefore adds a control
replicate to measure the noise floor.

## Design

A/B with fixed inputs, on the current structured/bilingual/multi-topic
architecture (D-34/D-35), one sample per arm plus a replicate:

- The 12 canonical expert analyses are taken **verbatim from korai-szelekcio
  round_09** (the sourced-era baseline) — byte-identical digests in all arms.
- The new expert's analysis was generated live once (two-phase, as in the
  pipeline: 5 live web searches, then a schema-constrained bilingual
  analysis over the 6 curated registry facts admitted with this branch).
- `scenario_builder → editor → final_brief_writer` ran live per arm, prompts
  verbatim from `lab/pipeline.py`, against the topic's FROZEN frames (S1–S5,
  D-36) and round_09's argument ledger (16 clusters, identical in all arms).
- **arm A1 (control):** 12 experts · **arm A2 (replicate):** identical inputs
  to A1 · **arm B (treatment):** 12 + educational_psychology.
- All 11 calls live on the Anthropic API (sonnet-5; `expert_analysis` on
  haiku-4.5 — ladder tier 0, same as canonical rounds). Zero mock, zero
  failed, zero retries; ~581K input / ~289K output tokens (≈$6). Validators
  imported from `lab.pipeline` — every arm passed the same definition of
  done as a live round.

## Findings

**1. The new seat's own output is high-quality and genuinely NEW.**
The live analysis used the curated facts with their honest grades (the
contested labels on stereotype threat, labeling and growth mindset were
preserved, not inflated), added sourced web findings (Horn's tracking
studies, PISA 2022, OECD), and stated a falsifiable position whose novel
component — the big-fish-little-pond effect, i.e. selective environments
depress academic self-concept **even for the admitted "winners"** — is
covered by none of the 12 sitting experts. The D-24 test ("a seat for a NEW
position") is met at the expert layer.

**2. Attrition is one layer deeper than in v1: the holder survives, the
position dies at the editor.** In v1 the new position was carried in the
disagreement map and attrited before the brief. Here `educational_psychology`
appears as a **holder name** on two treatment disagreement sides (the
value-added dispute; the Poland/Finland transferability dispute, minority
side) and in one brief minority position — but both sides argue entirely on
other experts' grounds (value-added heterogeneity, segregation,
transferability), and the seat's own psychological substance is absent from
**every** downstream artifact: zero self-concept/BFLPE/labeling/motivation
content in the treatment synthesis overview, agreements, scenarios (all 5,
all fields) and brief (the only "psycholog" hits are the holder name
itself). The editor absorbed the new holder into existing coalitions by
headcount instead of opening a side for the genuinely new position — the
exact failure mode issue #9 describes.

**3. The noise floor (A1↔A2) swallows every structural delta except the
holder itself.** Identical inputs produced: 5 vs 4 disagreements, 10 vs 8
agreements, 5 vs 3 brief minority positions, and evidence-label flips on
the same scenarios (S1 `weak`↔`moderate`, S5 `strong`↔`moderate`). The
treatment's structural counts (4 disagreements, 8 agreements, 4 minority
positions) sit inside this noise. The only above-noise signal is the
presence of `educational_psychology` as a holder (impossible in the
controls) — and the absence of its substance.

**4. Coalition arithmetic is unstable across identical runs (v1 finding
replicated).** The same 12-expert record clustered into different
disagreement topics and different side compositions in A1 vs A2. Any
headcount-based reading of "how many experts are on each side" remains
untrustworthy at n=1, now demonstrated on the strongest generator tier.

**5. Response-obligation layer is robust.** All three arms answered all 16
ledger clusters with typed responses, with near-identical type
distributions (value_conflict 3-4, policy_design_fixable 4-5,
irreducible_tradeoff 2) — the D-30 typed-response mechanism is insensitive
to panel composition, as designed.

## Answer to the admission question (D-24)

The seat **does** bring a new, sensitivity-tested position, and the
knowledge-registry path works (curated facts cited with honest grades). But
admitting the seat alone will NOT surface that position in the public
deliverables: the synthesis layer demonstrably strips it while keeping the
holder's name — which is worse than dropping it outright, because the map
then *looks* like the psychology view was weighed. Admission should be
paired with the system-level fix v1 already recommended and #9 tracks: a
deterministic **position-carriage check** (every seated expert's stated
position must be identifiable — as its own side or an explicit minority
position — in the synthesis, not merely as a holder name appended to
someone else's argument).

## Recommended follow-ups

1. (#9, unchanged since v1, now more urgent) Deterministic position-carriage
   validation at the synthesis step; holder-name-only carriage should FAIL.
2. Editor spec/directive: a new-position holder may only be merged into an
   existing side if that side's `position` text subsumes the expert's stated
   position; otherwise open a new side.
3. After admission, the first canonical round with the 13-expert panel
   re-tests carriage under the fixed editor (one documented change per
   round: the carriage fix is that round's change).

## Caveats

Single treatment sample (the replicate bounds noise on the control side
only); critics, discourse voices and the meta-critic were not re-run (the
ledger was held fixed by design — voice-layer sensitivity to the new expert
is untested); judge/evaluation scores were not computed (this experiment
compares artifacts, not rubric scores). The HU halves of the bilingual
artifacts were spot-checked, not systematically compared.
