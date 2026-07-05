# Translation report (final)

# Critique: translation_checker — round 5

Deterministic HU↔EN parity checks (glossary: docs/glossary.md).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4'], HU ['S1', 'S2', 'S3', 'S4'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary + back-translation key-term checks: no violations

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "brief [mock]": 10,
  "build_scenarios [mock]": 4,
  "critic [anthropic]": 40,
  "exec_summary [mock]": 2,
  "expert_analysis [mock]": 12,
  "judge_score [anthropic]": 45,
  "judge_score [mock]": 30,
  "meta_critique [anthropic]": 5,
  "rejected_framings [mock]": 4,
  "synthesis [mock]": 4,
  "translate_scenarios [mock]": 5
}
