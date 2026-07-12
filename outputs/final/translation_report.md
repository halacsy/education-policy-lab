# Translation report (final)

# Critique: translation_checker — round 7

Deterministic HU↔EN parity checks (glossary: docs/glossary.md).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4'], HU ['S1', 'S2', 'S3', 'S4'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary + back-translation key-term checks: no violations

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "argument_map [anthropic:claude-opus-4-8]": 1,
  "argument_map [anthropic:claude-sonnet-5]": 1,
  "brief [anthropic:claude-opus-4-8]": 1,
  "brief [anthropic:claude-sonnet-5]": 2,
  "build_scenarios [anthropic:claude-opus-4-8]": 1,
  "build_scenarios [anthropic:claude-sonnet-5]": 1,
  "critic [mock]": 8,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 10,
  "discourse_reciprocity [anthropic:claude-sonnet-5]": 3,
  "discourse_voice [anthropic:claude-haiku-4-5]": 10,
  "discourse_voice [anthropic:claude-sonnet-5]": 1,
  "expert_analysis [anthropic:claude-haiku-4-5]": 3,
  "grade_arguments [google:gemini-2.5-flash-lite]": 1,
  "grade_arguments [mock]": 1,
  "judge_score [anthropic:claude-haiku-4-5]": 6,
  "judge_score [mock]": 9,
  "meta_critique [mock]": 1,
  "rejected_framings [anthropic:claude-haiku-4-5]": 1,
  "synthesis [anthropic:claude-opus-4-8]": 1,
  "synthesis [anthropic:claude-sonnet-5]": 1,
  "translate_ledger [anthropic:claude-opus-4-8]": 1,
  "translate_ledger [anthropic:claude-sonnet-5]": 1,
  "translate_scenarios [anthropic:claude-opus-4-8]": 1,
  "translate_scenarios [anthropic:claude-sonnet-5]": 1
}
Token usage: {
  "by_task_backend": {
    "argument_map [anthropic:claude-opus-4-8]": {
      "input_tokens": 45228,
      "output_tokens": 10050
    },
    "argument_map [anthropic:claude-sonnet-5]": {
      "input_tokens": 45171,
      "output_tokens": 16000
    },
    "brief [anthropic:claude-opus-4-8]": {
      "input_tokens": 79502,
      "output_tokens": 5897
    },
    "brief [anthropic:claude-sonnet-5]": {
      "input_tokens": 87549,
      "output_tokens": 19198
    },
    "build_scenarios [anthropic:claude-opus-4-8]": {
      "input_tokens": 18291,
      "output_tokens": 7361
    },
    "build_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 18234,
      "output_tokens": 16000
    },
    "discourse_reciprocity [anthropic:claude-haiku-4-5]": {
      "input_tokens": 60444,
      "output_tokens": 25513
    },
    "discourse_reciprocity [anthropic:claude-sonnet-5]": {
      "input_tokens": 28295,
      "output_tokens": 8170
    },
    "discourse_voice [anthropic:claude-haiku-4-5]": {
      "input_tokens": 56626,
      "output_tokens": 36788
    },
    "discourse_voice [anthropic:claude-sonnet-5]": {
      "input_tokens": 8621,
      "output_tokens": 3255
    },
    "expert_analysis [anthropic:claude-haiku-4-5]": {
      "input_tokens": 3486,
      "output_tokens": 2897
    },
    "grade_arguments [google:gemini-2.5-flash-lite]": {
      "input_tokens": 3552,
      "output_tokens": 169
    },
    "judge_score [anthropic:claude-haiku-4-5]": {
      "input_tokens": 6351,
      "output_tokens": 450
    },
    "rejected_framings [anthropic:claude-haiku-4-5]": {
      "input_tokens": 8139,
      "output_tokens": 2359
    },
    "synthesis [anthropic:claude-opus-4-8]": {
      "input_tokens": 13978,
      "output_tokens": 3123
    },
    "synthesis [anthropic:claude-sonnet-5]": {
      "input_tokens": 13921,
      "output_tokens": 4000
    },
    "translate_ledger [anthropic:claude-opus-4-8]": {
      "input_tokens": 71490,
      "output_tokens": 16000
    },
    "translate_ledger [anthropic:claude-sonnet-5]": {
      "input_tokens": 71433,
      "output_tokens": 16000
    },
    "translate_scenarios [anthropic:claude-opus-4-8]": {
      "input_tokens": 11045,
      "output_tokens": 11343
    },
    "translate_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 10988,
      "output_tokens": 16000
    }
  },
  "total_input_tokens": 662344,
  "total_output_tokens": 220573,
  "total_tokens": 882917,
  "metered_calls": 48,
  "unmetered_calls": 19
}
