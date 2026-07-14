# Improvement plan — round 8

## What got better?
- Total 9.508 → 9.146 (delta -0.362).

## What is still weak?
- Weakest dimension: **translation_fidelity** (6.667); strongest: scenario_completeness (10.0).

## Which agent failed? Which workflow step failed?
- Steps degraded to deterministic mock fallback: voice:pedagogus_erdekvedo, voice:eselyegyenlosegi_civil, voice:oktataspolitikai_reformmozgalom — these agents' prompts/validators are the weakest links.

## Which critique was too vague?
- Critics below the 2-targeted-objection bar: none.

## Was any translation inconsistent?
- Deterministic parity ok=False; glossary violations: ["EN 'teacher shortage' present but HU 'pedagógushiány' missing"]; untranslated fields: none.

## Did the two judges disagree anywhere?
- Divergence-flagged dimensions: ['critic_concreteness', 'translation_fidelity', 'meta_system_eval'] (deterministic score used; flagged to human_questions.md).

## Are score gains genuine or rubric-gaming?
- See meta_critique.md '## Gaming judgment' — the meta-critic must answer this explicitly each round; the held-out checks (not visible to this planning step) re-test it at verify time.

## What changes next round?
- **glossary_selfcheck** targeting weakest dimension *translation_fidelity* (score 6.667).
- Specific change: append directive to translator.
- Directive: Before returning, verify every glossary term mapping you used against docs/glossary.md and correct deviations.
- Expected effect: +0.2 on translation_fidelity (per-dimension), consulting attempts_log.jsonl showed this change was never tried before.

## Continue, stop, or ask a human?
- Stop: --max-rounds 8 reached.
