# Evaluation — round 1

Total: **7.322** (baseline)

| dimension | score | method | det | llm mean | llm var |
|---|---|---|---|---|---|
| scenario_completeness | 7.5 | deterministic | 7.5 | — | — |
| evidence_discipline | 8.476 | mixed (0.7 det + 0.3 llm) | 8.68 | 8.0 | 0.0 |
| critic_concreteness | 5.0 | deterministic (LLM diverged; flagged for human) | 5.0 | 9.667 | 0.2222 |
| layer_separation | 10.0 | deterministic | 10.0 | — | — |
| meta_system_eval | 10.0 | mixed (0.7 det + 0.3 llm) | 10.0 | 10.0 | 0.0 |
| disagreement_preservation | 5.25 | deterministic (LLM diverged; flagged for human) | 5.25 | 8.0 | 0.0 |
| uncertainty_explicitness | 2.35 | deterministic | 2.35 | — | — |
| translation_fidelity | 10.0 | mixed (0.7 det + 0.3 llm) | 10.0 | 10.0 | 0.0 |

Generator: google; judge: anthropic (cross-family; judge-side artifacts scored by the generator provider — see docs/decisions.md D-14).
Divergence-flagged dimensions (sent to human review): ['critic_concreteness', 'disagreement_preservation'].
Steps that degraded to the deterministic mock: none.

Note: the meta-critique was written before the final total existed; it saw the seven content dimensions and the previous round's total.
