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
  "argument_decompose [anthropic:claude-opus-4-8]": 10,
  "argument_map [mock]": 1,
  "brief [anthropic:claude-opus-4-8]": 3,
  "build_scenarios [anthropic:claude-opus-4-8]": 1,
  "build_scenarios [anthropic:claude-sonnet-5]": 1,
  "critic [openai(codex):]": 8,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 10,
  "discourse_reciprocity [anthropic:claude-opus-4-8]": 2,
  "discourse_reciprocity [mock]": 3,
  "discourse_voice [anthropic:claude-haiku-4-5]": 10,
  "expert_analysis [anthropic:claude-haiku-4-5]": 3,
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
      "input_tokens": 37622,
      "output_tokens": 5691
    },
    "brief [anthropic:claude-opus-4-8]": {
      "input_tokens": 99248,
      "output_tokens": 27340
    },
    "build_scenarios [anthropic:claude-opus-4-8]": {
      "input_tokens": 18445,
      "output_tokens": 7323
    },
    "build_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 18388,
      "output_tokens": 16000
    },
    "discourse_reciprocity [anthropic:claude-haiku-4-5]": {
      "input_tokens": 80649,
      "output_tokens": 28514
    },
    "discourse_reciprocity [anthropic:claude-opus-4-8]": {
      "input_tokens": 24422,
      "output_tokens": 1503
    },
    "discourse_voice [anthropic:claude-haiku-4-5]": {
      "input_tokens": 56566,
      "output_tokens": 35301
    },
    "expert_analysis [anthropic:claude-haiku-4-5]": {
      "input_tokens": 3486,
      "output_tokens": 3043
    },
    "judge_score [anthropic:claude-haiku-4-5]": {
      "input_tokens": 18510,
      "output_tokens": 603
    },
    "rejected_framings [anthropic:claude-haiku-4-5]": {
      "input_tokens": 8133,
      "output_tokens": 2020
    },
    "synthesis [anthropic:claude-opus-4-8]": {
      "input_tokens": 14132,
      "output_tokens": 2660
    },
    "synthesis [anthropic:claude-sonnet-5]": {
      "input_tokens": 14075,
      "output_tokens": 4000
    },
    "translate_ledger [anthropic:claude-opus-4-8]": {
      "input_tokens": 138173,
      "output_tokens": 32000
    },
    "translate_scenarios [anthropic:claude-opus-4-8]": {
      "input_tokens": 10964,
      "output_tokens": 11715
    }
  },
  "total_input_tokens": 542813,
  "total_output_tokens": 177713,
  "total_tokens": 720526,
  "metered_calls": 52,
  "unmetered_calls": 23
}
Errors seen: {
  "synthesis [anthropic:claude-sonnet-5]": [
    "RuntimeError: empty response"
  ],
  "argument_map [mock]": [
    "RuntimeError: empty response",
    "RuntimeError: empty response",
    "RuntimeError: empty response",
    "RuntimeError: empty response",
    "RuntimeError: empty response"
  ],
  "discourse_reciprocity [mock]": [
    "RuntimeError: empty response",
    "RuntimeError: empty response",
    "RuntimeError: empty response"
  ]
}
