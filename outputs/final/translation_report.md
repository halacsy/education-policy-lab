# Translation report (final)

# Critique: translation_checker — round 7

Deterministic HU↔EN parity checks (glossary: docs/glossary.md).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4'], HU ['S1', 'S2', 'S3', 'S4'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary/back-translation violations:
  - EN 'teacher shortage' present but HU 'pedagógushiány' missing

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "argument_map [mock]": 3,
  "brief [mock]": 6,
  "build_scenarios [anthropic:claude-opus-4-8]": 1,
  "build_scenarios [anthropic:claude-sonnet-5]": 1,
  "build_scenarios [mock]": 2,
  "critic [mock]": 24,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 10,
  "discourse_reciprocity [anthropic:claude-opus-4-8]": 1,
  "discourse_reciprocity [mock]": 22,
  "discourse_voice [anthropic:claude-haiku-4-5]": 10,
  "discourse_voice [mock]": 20,
  "expert_analysis [anthropic:claude-haiku-4-5]": 3,
  "expert_analysis [mock]": 6,
  "grade_arguments [mock]": 3,
  "judge_score [mock]": 45,
  "meta_critique [mock]": 3,
  "rejected_framings [anthropic:claude-haiku-4-5]": 1,
  "rejected_framings [mock]": 2,
  "synthesis [anthropic:claude-opus-4-8]": 1,
  "synthesis [anthropic:claude-sonnet-5]": 1,
  "synthesis [mock]": 2,
  "translate_ledger [mock]": 3,
  "translate_scenarios [mock]": 3
}
