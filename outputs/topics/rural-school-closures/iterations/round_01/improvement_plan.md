# Improvement plan — round 1

## What got better?
- Baseline round; nothing to compare yet. Total: 9.482.

## What is still weak?
- Weakest dimension: **evidence_discipline** (7.693); strongest: scenario_completeness (10.0).

## Which agent failed? Which workflow step failed?
- No step failed; all artifacts were produced by the live backends and passed validation.

## Which critique was too vague?
- Critics below the 2-targeted-objection bar: none.

## Was any translation inconsistent?
- Deterministic parity ok=True; glossary violations: none; untranslated fields: none.

## Did the two judges disagree anywhere?
- Divergence-flagged dimensions: ['evidence_discipline', 'critic_concreteness', 'meta_system_eval'] (deterministic score used; flagged to human_questions.md).

## Are score gains genuine or rubric-gaming?
- See meta_critique.md '## Gaming judgment' — the meta-critic must answer this explicitly each round; the held-out checks (not visible to this planning step) re-test it at verify time.

## What changes next round?
- **evidence_tag_all** targeting weakest dimension *evidence_discipline* (score 7.693).
- Specific change: append directive to scenario_builder.
- Directive: Attach an inline evidence tag ([evidence: strong|moderate|weak|contested]; HU: [bizonyíték: ...]) to EVERY mechanism claim and EVERY expected benefit, not only the core ones.
- Expected effect: +0.4 on evidence_discipline (per-dimension), consulting attempts_log.jsonl showed this change was never tried before.

## Continue, stop, or ask a human?
- Stop: --max-rounds 1 reached.
