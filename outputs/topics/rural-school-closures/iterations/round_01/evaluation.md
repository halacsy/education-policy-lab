# Evaluation — round 1

Total: **9.482** (baseline)

| dimension | score | method | det | llm mean | llm var |
|---|---|---|---|---|---|
| scenario_completeness | 10.0 | deterministic | 10.0 | — | — |
| evidence_discipline | 7.693 | deterministic (LLM diverged; flagged for human) | 7.693 | 9.667 | 0.2222 |
| critic_concreteness | 10.0 | deterministic (LLM diverged; flagged for human) | 10.0 | 8.0 | 0.0 |
| layer_separation | 8.165 | deterministic | 8.165 | — | — |
| meta_system_eval | 10.0 | deterministic (LLM diverged; flagged for human) | 10.0 | 8.333 | 0.2222 |
| disagreement_preservation | 10.0 | mixed (0.7 det + 0.3 llm) | 10.0 | 10.0 | 0.0 |
| uncertainty_explicitness | 10.0 | deterministic | 10.0 | — | — |
| translation_fidelity | 10.0 | mixed (0.7 det + 0.3 llm) | 10.0 | 10.0 | 0.0 |

Generator: anthropic; judge: openai (cross-family; judge-side artifacts scored by the generator provider — see docs/decisions.md D-14).
Divergence-flagged dimensions (sent to human review): ['evidence_discipline', 'critic_concreteness', 'meta_system_eval'].
Steps that failed and needed a relaunch (D-34, no mock fallback): none.

Note: the meta-critique was written before the final total existed; it saw the seven content dimensions and the previous round's total.
