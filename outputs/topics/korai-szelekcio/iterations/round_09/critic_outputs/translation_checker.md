# Critique: translation_checker — round 9

Deterministic HU↔EN parity checks (glossary: the topic glossary (topics/<slug>/glossary.md)).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4', 'S5'], HU ['S1', 'S2', 'S3', 'S4', 'S5'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary/back-translation violations:
  - HU 'egységes alapiskola' present but EN 'comprehensive school' missing (back-translation)

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.
