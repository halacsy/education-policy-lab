# Improvement plan — round 7

## What got better?
- Total 9.478 → 9.203 (delta -0.275).

## What is still weak?
- Weakest dimension: **evidence_discipline** (6.307); strongest: scenario_completeness (10.0).

## Which agent failed? Which workflow step failed?
- Steps degraded to deterministic mock fallback: decompose:A3, decompose:A2, decompose:A4, decompose:A1, decompose:A5, decompose:A6, decompose:A7, decompose:A8, decompose:A9, decompose:A10, translate_ledger, final_brief_writer — these agents' prompts/validators are the weakest links.

## Which critique was too vague?
- Critics below the 2-targeted-objection bar: none.

## Was any translation inconsistent?
- Deterministic parity ok=False; glossary violations: ["HU 'társadalmi mobilitás' present but EN 'social mobility' missing (back-translation)"]; untranslated fields: none.

## Did the two judges disagree anywhere?
- Divergence-flagged dimensions: ['evidence_discipline'] (deterministic score used; flagged to human_questions.md).

## Are score gains genuine or rubric-gaming?
- See meta_critique.md '## Gaming judgment' — the meta-critic must answer this explicitly each round; the held-out checks (not visible to this planning step) re-test it at verify time.

## What changes next round?
- **layer_tighten** targeting weakest dimension *layer_separation* (score 9.102).
- Specific change: append directive to final_brief_writer, translator.
- Directive: Every substantive claim across the brief's 10 sections carries a claim-kind tag ([fact]/[estimate]/[assumption]/[value], unchanged in every language); a substantive claim without one is a defect.
- Expected effect: +0.3 on layer_separation (per-dimension), consulting attempts_log.jsonl showed this change was never tried before.

## Continue, stop, or ask a human?
- Stop: --max-rounds 7 reached.
