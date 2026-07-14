# Evaluation — round 7

Total: **9.508** (delta -0.132)

| dimension | score | method | det | llm mean | llm var |
|---|---|---|---|---|---|
| scenario_completeness | 10.0 | deterministic | 10.0 | — | — |
| evidence_discipline | 8.271 | mixed (0.7 det + 0.3 llm) [rescored: scripts/rescore_round.py] | 7.959 | 9.0 | 0.0 |
| critic_concreteness | 9.6 | mixed (0.7 det + 0.3 llm) | 10.0 | 8.667 | 0.2222 |
| layer_separation | 9.053 | deterministic (rescored: scripts/rescore_round.py) | 9.053 | — | — |
| meta_system_eval | 9.6 | mixed (0.7 det + 0.3 llm) | 10.0 | 8.667 | 0.2222 |
| disagreement_preservation | 9.844 | mixed (0.7 det + 0.3 llm) | 9.778 | 10.0 | 0.0 |
| uncertainty_explicitness | 10.0 | deterministic | 10.0 | — | — |
| translation_fidelity | 9.7 | mixed (0.7 det + 0.3 llm) | 10.0 | 9.0 | 0.0 |

Generator: anthropic; judge: openai.
Divergence-flagged dimensions (sent to human review): none.
Steps that degraded to the deterministic mock: ['translate_voice:eselyegyenlosegi_civil', 'translate_voice:pedagogus_erdekvedo', 'translate_voice:kisgyerekes_szuloi', 'translate_voice:konzervativ_ertekvedo', 'translate_voice:digitalisgazdasagi', 'translate_voice:egyhazi_fenntartoi', 'translate_voice:oktataspolitikai_reformmozgalom', 'translate_voice:pedagogus_szakszervezeti_hang', 'translate_voice:kormanyzati_reformrealizmus', 'translate_voice:fuggetlen_szakpolitikai_kutatomuhely', 'translate_reciprocity:pedagogus_erdekvedo', 'translate_reciprocity:kisgyerekes_szuloi', 'translate_reciprocity:digitalisgazdasagi', 'translate_reciprocity:egyhazi_fenntartoi', 'translate_reciprocity:oktataspolitikai_reformmozgalom', 'translate_reciprocity:kormanyzati_reformrealizmus', 'translate_reciprocity:fuggetlen_szakpolitikai_kutatomuhely'].

Rescored by scripts/rescore_round.py after a scorer bug fix (total was 9.508 before rescoring).
