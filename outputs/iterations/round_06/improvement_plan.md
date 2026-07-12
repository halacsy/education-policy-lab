# Improvement plan — round 6

## What got better?
- Total 9.265 → 9.478 (delta +0.213).
- Applied change `implementation_detail` targeted *scenario_completeness*: score now 10.0.

## What is still weak?
- Weakest dimension: **evidence_discipline** (6.744); strongest: scenario_completeness (10.0).

## Which agent failed? Which workflow step failed?
- Steps degraded to deterministic mock fallback: voice:egyhazi_fenntartoi, voice:tisza_kormany, grade_arguments, translate_ledger, final_brief_writer, translator_brief, critic:assumption_checker — these agents' prompts/validators are the weakest links.

## Which critique was too vague?
- Critics below the 2-targeted-objection bar: none.

## Was any translation inconsistent?
- Deterministic parity ok=True; glossary violations: none; untranslated fields: none.

## Did the two judges disagree anywhere?
- Divergence-flagged dimensions: ['critic_concreteness', 'disagreement_preservation', 'meta_system_eval'] (deterministic score used; flagged to human_questions.md).

## Are score gains genuine or rubric-gaming?
- See meta_critique.md '## Gaming judgment' — the meta-critic must answer this explicitly each round; the held-out checks (not visible to this planning step) re-test it at verify time.

## What changes next round?
- **layer_tighten** targeting weakest dimension *layer_separation* (score 9.102).
- Specific change: append directive to final_brief_writer, translator.
- Directive: Every bullet in Evidence/Interpretation/Assumptions carries its status tag inline; a bullet without a tag is a defect.
- Expected effect: +0.3 on layer_separation (per-dimension), consulting attempts_log.jsonl showed this change was never tried before.

## Continue, stop, or ask a human?
- Stop: --max-rounds 6 reached.
