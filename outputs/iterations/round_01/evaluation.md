# Evaluation — round 1

Total: **7.51** (baseline)

| dimension | score | method | det | llm mean | llm var |
|---|---|---|---|---|---|
| scenario_completeness | 7.882 | deterministic | 7.882 | — | — |
| evidence_discipline | 7.61 | deterministic (LLM diverged; flagged for human) | 7.61 | 9.333 | 0.2222 |
| critic_concreteness | 5.0 | deterministic (LLM diverged; flagged for human) | 5.0 | 7.667 | 0.2222 |
| layer_separation | 10.0 | deterministic | 10.0 | — | — |
| meta_system_eval | 10.0 | deterministic (LLM diverged; flagged for human) | 10.0 | 8.333 | 0.2222 |
| disagreement_preservation | 6.0 | deterministic (LLM diverged; flagged for human) | 6.0 | 9.667 | 0.2222 |
| uncertainty_explicitness | 3.589 | deterministic | 3.589 | — | — |
| translation_fidelity | 9.997 | mixed (0.7 det + 0.3 llm) | 10.0 | 9.99 | 0.0 |

Generator: anthropic; judge: google (cross-family; judge-side artifacts scored by the generator provider — see docs/decisions.md D-14).
Divergence-flagged dimensions (sent to human review): ['evidence_discipline', 'critic_concreteness', 'disagreement_preservation', 'meta_system_eval'].
Steps that degraded to the deterministic mock: none.

Note: the meta-critique was written before the final total existed; it saw the seven content dimensions and the previous round's total.
