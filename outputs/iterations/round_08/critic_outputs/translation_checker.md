# Critique: translation_checker — round 8

Deterministic HU↔EN parity checks (glossary: docs/glossary.md).

- Scenario-id sets equal: True (EN ['S0', 'S1', 'S2', 'S3', 'S4'], HU ['S0', 'S1', 'S2', 'S3', 'S4'])
- Section structure equal: False
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary/back-translation violations:
  - EN 'teacher shortage' present but HU 'pedagógushiány' missing

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.
