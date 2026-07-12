# Evaluation — round 6

Total: **9.478** (delta +0.213)

| dimension | score | method | det | llm mean | llm var |
|---|---|---|---|---|---|
| scenario_completeness | 10.0 | deterministic | 10.0 | — | — |
| evidence_discipline | 6.744 | mixed (0.7 det + 0.3 llm) | 6.349 | 7.667 | 0.2222 |
| critic_concreteness | 10.0 | deterministic (LLM diverged; flagged for human) | 10.0 | 7.0 | 0.0 |
| layer_separation | 9.102 | deterministic | 9.102 | — | — |
| meta_system_eval | 10.0 | deterministic (LLM diverged; flagged for human) | 10.0 | 8.333 | 0.2222 |
| disagreement_preservation | 10.0 | deterministic (LLM diverged; flagged for human) | 10.0 | 6.977 | 2.0944 |
| uncertainty_explicitness | 10.0 | deterministic | 10.0 | — | — |
| translation_fidelity | 9.976 | mixed (0.7 det + 0.3 llm) | 10.0 | 9.92 | 0.0 |

Generator: anthropic; judge: google (cross-family; judge-side artifacts scored by the generator provider — see docs/decisions.md D-14).
Divergence-flagged dimensions (sent to human review): ['critic_concreteness', 'disagreement_preservation', 'meta_system_eval'].
Steps that degraded to the deterministic mock: ['voice:egyhazi_fenntartoi', 'voice:tisza_kormany', 'grade_arguments', 'translate_ledger', 'final_brief_writer', 'translator_brief', 'critic:assumption_checker'].

Note: the meta-critique was written before the final total existed; it saw the seven content dimensions and the previous round's total.
