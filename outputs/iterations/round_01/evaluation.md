# Evaluation — round 1

Total: **7.072** (baseline)

| dimension | score | method | det | llm mean | llm var |
|---|---|---|---|---|---|
| scenario_completeness | 7.375 | deterministic | 7.375 | — | — |
| evidence_discipline | 5.902 | deterministic (LLM diverged; flagged for human) | 5.902 | 9.0 | 0.0 |
| critic_concreteness | 4.746 | mixed (0.7 det + 0.3 llm) | 5.0 | 4.153 | 0.0008 |
| layer_separation | 10.0 | deterministic | 10.0 | — | — |
| meta_system_eval | 10.0 | deterministic (LLM diverged; flagged for human) | 10.0 | 5.05 | 0.0054 |
| disagreement_preservation | 6.0 | deterministic (LLM diverged; flagged for human) | 6.0 | 9.0 | 0.0 |
| uncertainty_explicitness | 3.233 | deterministic | 3.233 | — | — |
| translation_fidelity | 9.317 | mixed (0.7 det + 0.3 llm) | 9.167 | 9.667 | 0.2222 |

Generator: google; judge: anthropic (cross-family; judge-side artifacts scored by the generator provider — see docs/decisions.md D-14).
Divergence-flagged dimensions (sent to human review): ['evidence_discipline', 'disagreement_preservation', 'meta_system_eval'].
Steps that degraded to the deterministic mock: none.

Note: the meta-critique was written before the final total existed; it saw the seven content dimensions and the previous round's total.
