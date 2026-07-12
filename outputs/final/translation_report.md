# Translation report (final)

# Critique: translation_checker — round 6

Deterministic HU↔EN parity checks (glossary: docs/glossary.md).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4'], HU ['S1', 'S2', 'S3', 'S4'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary + back-translation key-term checks: no violations

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "argument_map [mock]": 1,
  "brief [anthropic:claude-opus-4-8]": 4,
  "build_scenarios [anthropic:claude-opus-4-8]": 1,
  "build_scenarios [anthropic:claude-sonnet-5]": 1,
  "critic [google:gemini-2.5-flash-lite]": 10,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 10,
  "discourse_reciprocity [anthropic:claude-opus-4-8]": 2,
  "discourse_reciprocity [mock]": 3,
  "discourse_voice [anthropic:claude-haiku-4-5]": 10,
  "discourse_voice [anthropic:claude-sonnet-5]": 2,
  "expert_analysis [anthropic:claude-haiku-4-5]": 2,
  "grade_arguments [google:gemini-2.5-flash-lite]": 2,
  "judge_score [anthropic:claude-haiku-4-5]": 6,
  "judge_score [google:gemini-2.5-flash-lite]": 5,
  "judge_score [mock]": 4,
  "meta_critique [mock]": 1,
  "rejected_framings [anthropic:claude-haiku-4-5]": 1,
  "synthesis [anthropic:claude-opus-4-8]": 1,
  "synthesis [anthropic:claude-sonnet-5]": 1,
  "translate_ledger [anthropic:claude-opus-4-8]": 2,
  "translate_scenarios [anthropic:claude-opus-4-8]": 1
}
