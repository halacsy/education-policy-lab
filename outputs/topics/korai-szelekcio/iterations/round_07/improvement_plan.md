# Improvement plan — round 7

## What got better?
- Total 9.478 → 8.995 (delta -0.483).

## What is still weak?
- Weakest dimension: **evidence_discipline** (6.216); strongest: scenario_completeness (10.0).

## Which agent failed? Which workflow step failed?
- Steps degraded to deterministic mock fallback: translate_voice:eselyegyenlosegi_civil, translate_voice:pedagogus_erdekvedo, translate_voice:kisgyerekes_szuloi, translate_voice:konzervativ_ertekvedo, translate_voice:digitalisgazdasagi, translate_voice:egyhazi_fenntartoi, translate_voice:oktataspolitikai_reformmozgalom, translate_voice:pedagogus_szakszervezeti_hang, translate_voice:kormanyzati_reformrealizmus, translate_voice:fuggetlen_szakpolitikai_kutatomuhely, translate_reciprocity:pedagogus_erdekvedo, translate_reciprocity:kisgyerekes_szuloi, translate_reciprocity:digitalisgazdasagi, translate_reciprocity:egyhazi_fenntartoi, translate_reciprocity:oktataspolitikai_reformmozgalom, translate_reciprocity:kormanyzati_reformrealizmus, translate_reciprocity:fuggetlen_szakpolitikai_kutatomuhely — these agents' prompts/validators are the weakest links.

## Which critique was too vague?
- Critics below the 2-targeted-objection bar: none.

## Was any translation inconsistent?
- Deterministic parity ok=True; glossary violations: none; untranslated fields: none.

## Did the two judges disagree anywhere?
- Divergence-flagged dimensions: ['evidence_discipline'] (deterministic score used; flagged to human_questions.md).

## Are score gains genuine or rubric-gaming?
- See meta_critique.md '## Gaming judgment' — the meta-critic must answer this explicitly each round; the held-out checks (not visible to this planning step) re-test it at verify time.

## What changes next round?
- **layer_tighten** targeting weakest dimension *layer_separation* (score 7.0).
- Specific change: append directive to final_brief_writer, translator.
- Directive: Every substantive claim across the brief's 10 sections carries a claim-kind tag ([fact]/[estimate]/[assumption]/[value], unchanged in every language); a substantive claim without one is a defect.
- Expected effect: +0.3 on layer_separation (per-dimension), consulting attempts_log.jsonl showed this change was never tried before.

## Continue, stop, or ask a human?
- Stop: --max-rounds 7 reached.
