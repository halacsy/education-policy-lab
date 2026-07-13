# Translation report (final)

# Critique: translation_checker — round 7

Deterministic HU↔EN parity checks (glossary: docs/glossary.md).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4'], HU ['S1', 'S2', 'S3', 'S4'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary/back-translation violations:
  - HU 'társadalmi mobilitás' present but EN 'social mobility' missing (back-translation)

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "argument_decompose [anthropic:claude-opus-4-8]": 20,
  "argument_map [mock]": 1,
  "brief [anthropic:claude-opus-4-8]": 3,
  "build_scenarios [anthropic:claude-opus-4-8]": 1,
  "build_scenarios [anthropic:claude-sonnet-5]": 1,
  "critic [openai(codex):]": 8,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 10,
  "discourse_reciprocity [anthropic:claude-opus-4-8]": 1,
  "discourse_reciprocity [mock]": 1,
  "discourse_voice [anthropic:claude-haiku-4-5]": 10,
  "grade_arguments [openai(codex):]": 1,
  "judge_score [anthropic:claude-haiku-4-5]": 6,
  "judge_score [openai(codex):]": 9,
  "meta_critique [openai(codex):]": 1,
  "rejected_framings [anthropic:claude-haiku-4-5]": 1,
  "synthesis [anthropic:claude-opus-4-8]": 1,
  "synthesis [anthropic:claude-sonnet-5]": 1,
  "translate_ledger [anthropic:claude-opus-4-8]": 2,
  "translate_scenarios [anthropic:claude-opus-4-8]": 1
}
Token usage: {
  "by_task_backend": {
    "argument_decompose [anthropic:claude-opus-4-8]": {
      "input_tokens": 74200,
      "output_tokens": 18026
    },
    "brief [anthropic:claude-opus-4-8]": {
      "input_tokens": 169281,
      "output_tokens": 19381
    },
    "build_scenarios [anthropic:claude-opus-4-8]": {
      "input_tokens": 18597,
      "output_tokens": 6965
    },
    "build_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 18540,
      "output_tokens": 16000
    },
    "discourse_reciprocity [anthropic:claude-haiku-4-5]": {
      "input_tokens": 60999,
      "output_tokens": 23413
    },
    "discourse_reciprocity [anthropic:claude-opus-4-8]": {
      "input_tokens": 9137,
      "output_tokens": 770
    },
    "discourse_voice [anthropic:claude-haiku-4-5]": {
      "input_tokens": 54106,
      "output_tokens": 35582
    },
    "judge_score [anthropic:claude-haiku-4-5]": {
      "input_tokens": 19023,
      "output_tokens": 566
    },
    "rejected_framings [anthropic:claude-haiku-4-5]": {
      "input_tokens": 7887,
      "output_tokens": 1981
    },
    "synthesis [anthropic:claude-opus-4-8]": {
      "input_tokens": 14284,
      "output_tokens": 2968
    },
    "synthesis [anthropic:claude-sonnet-5]": {
      "input_tokens": 14227,
      "output_tokens": 4000
    },
    "translate_ledger [anthropic:claude-opus-4-8]": {
      "input_tokens": 146215,
      "output_tokens": 32000
    },
    "translate_scenarios [anthropic:claude-opus-4-8]": {
      "input_tokens": 10612,
      "output_tokens": 10818
    }
  },
  "total_input_tokens": 617108,
  "total_output_tokens": 172470,
  "total_tokens": 789578,
  "metered_calls": 58,
  "unmetered_calls": 21
}
