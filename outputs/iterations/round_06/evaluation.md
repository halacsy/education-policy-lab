# Evaluation — round 6

Total: **9.041** (delta -0.224)

| dimension | score | method | det | llm mean | llm var |
|---|---|---|---|---|---|
| scenario_completeness | 10.0 | deterministic | 10.0 | — | — |
| evidence_discipline | 6.83 | mixed (0.7 det + 0.3 llm) | 6.471 | 7.667 | 0.2222 |
| critic_concreteness | 9.7 | mixed (0.7 det + 0.3 llm) | 10.0 | 9.0 | 0.0 |
| layer_separation | 10.0 | deterministic | 10.0 | — | — |
| meta_system_eval | 9.6 | mixed (0.7 det + 0.3 llm) | 10.0 | 8.667 | 0.2222 |
| disagreement_preservation | 8.7 | mixed (0.7 det + 0.3 llm) | 9.143 | 7.667 | 0.2222 |
| uncertainty_explicitness | 10.0 | deterministic | 10.0 | — | — |
| translation_fidelity | 7.5 | deterministic (LLM diverged; flagged for human) | 7.5 | 2.0 | 0.0 |

Generator: anthropic; judge: google (cross-family; judge-side artifacts scored by the generator provider — see docs/decisions.md D-14).
Divergence-flagged dimensions (sent to human review): ['translation_fidelity'].
Steps that degraded to the deterministic mock: ['expert:international_comparison', 'expert:legal_and_governance', 'translate_ledger', 'final_brief_writer'].

Note: the meta-critique was written before the final total existed; it saw the seven content dimensions and the previous round's total.
