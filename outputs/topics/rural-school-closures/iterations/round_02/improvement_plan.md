# Improvement plan — round 2

## What got better?
- Baseline round; nothing to compare yet. Total: 9.252.

## What is still weak?
- Weakest dimension: **evidence_discipline** (7.794); strongest: scenario_completeness (10.0).

## Which agent failed? Which workflow step failed?
- No step failed; all artifacts were produced by the live backends and passed validation.

## Which critique was too vague?
- Critics below the 2-targeted-objection bar: none.

## Was any translation inconsistent?
- Deterministic parity ok=True; glossary violations: none; untranslated fields: none.

## Did the two judges disagree anywhere?
- Divergence-flagged dimensions: ['evidence_discipline'] (deterministic score used; flagged to human_questions.md).

## Are score gains genuine or rubric-gaming?
- See meta_critique.md '## Gaming judgment' — the meta-critic must answer this explicitly each round; the held-out checks (not visible to this planning step) re-test it at verify time.

## What changes next round?
- **layer_tighten** targeting weakest dimension *layer_separation* (score 8.02).
- Specific change: append directive to final_brief_writer.
- Directive: Every substantive claim across the brief's 10 sections carries a claim-kind tag ([fact]/[estimate]/[assumption]/[value], unchanged in every language); a substantive claim without one is a defect.
- Expected effect: +0.3 on layer_separation (per-dimension), consulting attempts_log.jsonl showed this change was never tried before.

## Continue, stop, or ask a human?
- Stop: --max-rounds 2 reached.
