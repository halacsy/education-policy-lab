# Improvement plan — round 3

## What got better?
- Total 7.752 → 8.551 (delta +0.799).
- Applied change `critic_fix_severity` targeted *critic_concreteness*: score now 10.0.

## What is still weak?
- Weakest dimension: **evidence_discipline** (5.917); strongest: critic_concreteness (10.0).

## Which agent failed? Which workflow step failed?
- No step failed; all artifacts were produced by the live backends and passed format validation.

## Which critique was too vague?
- Critics below the 2-targeted-objection bar: none.

## Was any translation inconsistent?
- Deterministic parity ok=False; glossary violations: ["EN 'school choice' present but HU 'iskolaválasztás' missing"]; untranslated fields: none.

## Did the two judges disagree anywhere?
- Divergence-flagged dimensions: ['evidence_discipline', 'critic_concreteness', 'disagreement_preservation', 'meta_system_eval'] (deterministic score used; flagged to human_questions.md).

## Are score gains genuine or rubric-gaming?
- See meta_critique.md '## Gaming judgment' — the meta-critic must answer this explicitly each round; the held-out checks (not visible to this planning step) re-test it at verify time.

## What changes next round?
- **evidence_tag_all** targeting weakest dimension *evidence_discipline* (score 5.917).
- Specific change: append directive to scenario_builder, translator.
- Directive: Attach an inline evidence tag ([evidence: strong|moderate|weak|contested]; HU: [bizonyíték: ...]) to EVERY mechanism claim and EVERY expected benefit, not only the core ones.
- Expected effect: +0.4 on evidence_discipline (per-dimension), consulting attempts_log.jsonl showed this change was never tried before.

## Continue, stop, or ask a human?
- Continue: apply evidence_tag_all next round; no blocking human question is open (open questions are tracked in human_questions.md).
