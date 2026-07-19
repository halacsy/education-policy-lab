# Translation report (final)

# Critique: translation_checker — round 3

Deterministic HU↔EN parity checks (glossary: the topic glossary (topics/<slug>/glossary.md)).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4', 'S5'], HU ['S1', 'S2', 'S3', 'S4', 'S5'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary + back-translation key-term checks: no violations

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "argument_decompose [anthropic:claude-sonnet-5]": 22,
  "argument_map [anthropic:claude-sonnet-5]": 1,
  "brief [anthropic:claude-sonnet-5]": 1,
  "critic [openai:]": 8,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 10,
  "discourse_voice [anthropic:claude-haiku-4-5]": 1,
  "discourse_voice [anthropic:claude-sonnet-5]": 1,
  "grade_arguments [openai:]": 1,
  "judge_score [anthropic:claude-haiku-4-5]": 6,
  "judge_score [openai:]": 9,
  "meta_critique [openai:]": 1
}
Token usage: {
  "by_task_backend": {
    "argument_decompose [anthropic:claude-sonnet-5]": {
      "input_tokens": 93343,
      "output_tokens": 31289
    },
    "argument_map [anthropic:claude-sonnet-5]": {
      "input_tokens": 22735,
      "output_tokens": 7711
    },
    "brief [anthropic:claude-sonnet-5]": {
      "input_tokens": 62651,
      "output_tokens": 35988
    },
    "critic [openai:]": {
      "input_tokens": 88470,
      "output_tokens": 19416
    },
    "discourse_reciprocity [anthropic:claude-haiku-4-5]": {
      "input_tokens": 140299,
      "output_tokens": 14735
    },
    "discourse_voice [anthropic:claude-haiku-4-5]": {
      "input_tokens": 11028,
      "output_tokens": 8213
    },
    "discourse_voice [anthropic:claude-sonnet-5]": {
      "input_tokens": 16604,
      "output_tokens": 5099
    },
    "grade_arguments [openai:]": {
      "input_tokens": 10767,
      "output_tokens": 949
    },
    "judge_score [anthropic:claude-haiku-4-5]": {
      "input_tokens": 32619,
      "output_tokens": 660
    },
    "judge_score [openai:]": {
      "input_tokens": 92082,
      "output_tokens": 5879
    },
    "meta_critique [openai:]": {
      "input_tokens": 1357,
      "output_tokens": 2051
    }
  },
  "total_input_tokens": 571955,
  "total_output_tokens": 131990,
  "total_tokens": 703945,
  "metered_calls": 61,
  "unmetered_calls": 0
}
Errors seen: {}
