# Improvement plan — round 8

## What got better?
- Baseline round; nothing to compare yet. Total: 9.232.

## What is still weak?
- Weakest dimension: **evidence_discipline** (7.359); strongest: scenario_completeness (10.0).

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
- **scenario_crossref** targeting weakest dimension *layer_separation* (score 7.701).
- Specific change: append directive to final_brief_writer.
- Directive: The brief must be self-contained: right after the introduction, add a scenario key section ('## Scenario key' / HU: '## Forgatókönyv-kulcs') listing each scenario id with its one-line title and a reference to the full scenario document (scenarios.en.md / scenarios.hu.md), so no recommendation refers to an id the reader cannot resolve.
- Expected effect: +0.2 on layer_separation (per-dimension), consulting attempts_log.jsonl showed this change was never tried before.

## Continue, stop, or ask a human?
- Stop: --max-rounds 8 reached.
