# Improvement plan — round 1

## What got better?
- Baseline round; nothing to compare yet. Total: 7.51.

## What is still weak?
- Weakest dimension: **uncertainty_explicitness** (3.589); strongest: layer_separation (10.0).

## Which agent failed? Which workflow step failed?
- No step failed; all artifacts were produced by the live backends and passed format validation.

## Which critique was too vague?
- Critics below the 2-targeted-objection bar: none.

## Was any translation inconsistent?
- Deterministic parity ok=True; glossary violations: none; untranslated fields: none.

## Did the two judges disagree anywhere?
- Divergence-flagged dimensions: ['evidence_discipline', 'critic_concreteness', 'disagreement_preservation', 'meta_system_eval'] (deterministic score used; flagged to human_questions.md).

## Are score gains genuine or rubric-gaming?
- See meta_critique.md '## Gaming judgment' — the meta-critic must answer this explicitly each round; the held-out checks (not visible to this planning step) re-test it at verify time.

## What changes next round?
- **uncertainty_quantify** targeting weakest dimension *uncertainty_explicitness* (score 3.589).
- Specific change: append directive to scenario_builder, translator, hungarian_education_system, international_comparison, finnish_reform....
- Directive: For every uncertainty item, state a confidence level (confidence: low|medium|high) and name what evidence would reduce it ('would be reduced by: ...'). In Hungarian output use 'megbízhatóság: alacsony|közepes|magas' and 'csökkentené: ...'.
- Expected effect: +0.8 on uncertainty_explicitness (per-dimension), consulting attempts_log.jsonl showed this change was never tried before.

## Continue, stop, or ask a human?
- Continue: apply uncertainty_quantify next round; no blocking human question is open (open questions are tracked in human_questions.md).
