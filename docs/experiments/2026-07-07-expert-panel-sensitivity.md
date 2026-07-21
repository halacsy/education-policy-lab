# Experiment: expert-panel sensitivity (adding one perspective expert)

**Date:** 2026-07-07 · **Branch:** `exp/conservative-expert` · **Tracker:** issue #9
**Script:** `scripts/exp_panel_sensitivity.py` · **Artifacts:** `outputs/experiments/panel_sensitivity/`

## Question (owner)

The disagreement map's majority/minority framing is headcount-based. Does
adding ONE perspective expert — `conservative_education` (parental choice,
subsidiarity, talent development; steel-manning the case for keeping the
tracks) — shift the synthesis, the scenarios, or the brief?

## Design

A/B with fixed inputs, single sample per arm (noise acknowledged, not hidden):

- The 12 canonical expert analyses are taken **verbatim from round_05** and are
  byte-identical in both arms.
- The new expert's analysis is generated live once (shared by arm B).
- `editor → scenario_builder → final_brief_writer` run live in both arms with
  prompts copied verbatim from `lab/pipeline.py`.
- **arm A (control):** 12 experts · **arm B (treatment):** 12 + conservative_education.
- All 7 calls served live by `google:gemini-2.5-flash-lite` (the Antigravity
  subscription quota was exhausted by the 2026-07-07 full live run — resets in
  ~6.5 days — so the API path was used). No mock fallback occurred; the script
  aborts rather than fall back.

## Findings

**1. The new voice IS preserved at the disagreement-map layer.**
`conservative_education` appears in the treatment map as its own side
("Maintaining early selective tracks … is essential for respecting parental
rights … and institutional diversity"), with its rationale. The
Habermas-machine design works where it was designed to work.

**2. But it dies between synthesis and brief (selective attrition, not a vote flip).**
Zero traces of the conservative position in the treatment scenarios.json.
In the treatment brief, parental choice appears only as *political risk* and
as an interpretation bullet explicitly arguing **against** it — never as a
value position to be weighed, and no open question poses the
equity-vs-parental-choice trade-off. The observed failure mode is subtler
than the feared majority flip: the minority voice survives the map and is
then attrited away downstream.

**3. The guardrail that would prevent this was silently dropped by the cheap model.**
Both arms' editor and brief outputs OMIT the required `## Minority positions`
section, despite the round-04 `minority_report` directive being embedded in
their specs. The experiment's validators (copied from the pipeline) check only
the 5 base headers, so the omission passed. Minority carriage is therefore
**model-tier-dependent**: at flash-lite tier the safeguard does not hold. The
canonical run (stronger models) did produce the section.

**4. Coalition framing is unstable — headcount is not a robust majority signal.**
Control produced ~10 fine-grained sides; treatment consolidated to 6 coalition
sides, absorbing `polish_reform` into the large phase-out coalition (6
holders). Same inputs for those 12 experts — different coalition arithmetic.
Any reading of "how many experts are on each side" is run-dependent at n=1.

**5. Sampling noise is comparable to the panel effect at field level.**
S3's `evidence_status` moved from hedged (control) to "strongly supported by
international evidence" (treatment) — the *opposite* direction of an
ideological-drift hypothesis. Field-level wording differences cannot be
attributed to panel composition from a single sample.

## Answers to the owner's question

Adding one conservative expert did **not** flip any majority position, and its
position was faithfully carried in the disagreement map. The real sensitivity
found is different and worse-hidden: (a) coalition headcounts are unstable
across runs, so a headcount-based majority framing is not trustworthy evidence
of anything; (b) minority carriage into the final brief depends on a directive
the cheapest model silently ignores.

## Recommended follow-ups (issue #9)

1. Deterministic **minority-carriage check**: every disagreement-map side must
   be referenced in the brief (Minority positions or Open questions) —
   validation-level, not judge-level, so no model tier can drop it silently.
2. Characterise disagreement-map sides by **evidence weight** (registry-graded
   facts per side), not by holder headcount.
3. A declared **perspective-expert type** whose positions are labelled
   value-based rather than evidence-based, handled explicitly by the editor.
4. Panel changes are system changes: PR review + mandatory sensitivity rerun
   (this script) before admission to the canonical panel.

## Caveats

Single sample per arm; generator model at the cheapest ladder rung; critics
and the meta-critic were not run (quota conservation) — objection-level shifts
are untested. HU translation layer untested.
