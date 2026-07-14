# Evaluation rubric (spec)

The rubric is code (`scripts/lab/evaluation.py`) plus this spec. Scores are
0–10 per dimension; `total` is the equal-weighted mean. Deterministic checks
are preferred; LLM-judged components follow the Evaluator protocol in
`docs/architecture.md` (N≥3 randomized trials, mean+variance, cross-provider
divergence flagging, verbosity caps).

| Dimension | Method | What scores |
|-----------|--------|-------------|
| scenario_completeness | deterministic | every scenario has all 10 required fields, each substantive (not a stub); implementation steps have actor+timeline |
| evidence_discipline | deterministic + judge | share of important claims carrying an evidence-status tag; strict separation of evidence / interpretation / assumption / recommendation; no confidence invented |
| critic_concreteness | deterministic + judge | each objection names a specific scenario id AND field; states the flaw; (higher levels) proposes a fix and a severity |
| layer_separation | deterministic | brief separates evidence / interpretation / assumptions / recommendations / open questions into distinct sections |
| meta_system_eval | deterministic + judge | meta_critique evaluates the agent SYSTEM (agent/workflow failures, removal candidates, gaming judgment), not just the policy |
| disagreement_preservation | deterministic + judge | disagreement map exists and is populated; minority positions appear in synthesis/brief with rationale; no forced consensus language |
| uncertainty_explicitness | deterministic | uncertainties enumerated per scenario; confidence levels present; "what would reduce this uncertainty" present at higher levels |
| translation_fidelity | deterministic + back-translation | HU/EN scenario-id set parity; section-structure parity; glossary conformance; not byte-identical; back-translation key-term check. Never LLM-judge-only |

## Scoring notes

- **Verbosity control:** all count-based components are capped per scenario /
  per critique; density, not volume, scores.
- **Variance:** LLM-judged dimensions record mean and variance over N=3
  order-randomized trials.
- **Divergence:** if the two providers' passes diverge > threshold
  (`config/system_config.json: judge_divergence_threshold`), the dimension is
  flagged to `human_questions.md` and marked low-confidence; scores are NOT
  averaged.
- **Held-out checks** (`lab/holdout_checks.py`) are not part of `total` and
  not visible to the improvement step; they gate verification only.

## Change control

Rubric changes are system changes: they must appear in a round's
`revised_workflow.md`, be snapshotted in `system_state/`, and may never
remove a dimension or weaken evidence/critic/disagreement requirements
(forbidden regression, verify check 14).
