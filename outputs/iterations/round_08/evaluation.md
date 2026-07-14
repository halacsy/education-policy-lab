# Evaluation — round 8

Total: **9.146** (delta -0.362)

| dimension | score | method | det | llm mean | llm var |
|---|---|---|---|---|---|
| scenario_completeness | 10.0 | deterministic | 10.0 | — | — |
| evidence_discipline | 8.176 | mixed (0.7 det + 0.3 llm) | 7.823 | 9.0 | 0.0 |
| critic_concreteness | 10.0 | deterministic (LLM diverged; flagged for human) | 10.0 | 5.51 | 0.0021 |
| layer_separation | 8.947 | deterministic | 8.947 | — | — |
| meta_system_eval | 10.0 | deterministic (LLM diverged; flagged for human) | 10.0 | 4.693 | 0.014 |
| disagreement_preservation | 9.38 | mixed (0.7 det + 0.3 llm) | 9.4 | 9.333 | 0.2222 |
| uncertainty_explicitness | 10.0 | deterministic | 10.0 | — | — |
| translation_fidelity | 6.667 | deterministic (LLM diverged; flagged for human) | 6.667 | 4.0 | 0.0 |

Generator: anthropic; judge: openai (cross-family; judge-side artifacts scored by the generator provider — see docs/decisions.md D-14).
Divergence-flagged dimensions (sent to human review): ['critic_concreteness', 'translation_fidelity', 'meta_system_eval'].
Steps that degraded to the deterministic mock: ['voice:pedagogus_erdekvedo', 'voice:eselyegyenlosegi_civil', 'voice:oktataspolitikai_reformmozgalom'].

Note: the meta-critique was written before the final total existed; it saw the seven content dimensions and the previous round's total.
