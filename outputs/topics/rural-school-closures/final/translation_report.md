# Translation report (final)

# Critique: translation_checker — round 2

Deterministic HU↔EN parity checks (glossary: the topic glossary (topics/<slug>/glossary.md)).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4', 'S5'], HU ['S1', 'S2', 'S3', 'S4', 'S5'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary + back-translation key-term checks: no violations

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "argument_decompose [anthropic:claude-sonnet-5]": 23,
  "argument_map [anthropic:claude-sonnet-5]": 1,
  "brief [anthropic:claude-sonnet-5]": 1,
  "build_scenarios [anthropic:claude-sonnet-5]": 1,
  "critic [openai:]": 8,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 10,
  "discourse_voice [anthropic:claude-haiku-4-5]": 10,
  "discourse_voice [anthropic:claude-sonnet-5]": 9,
  "expert_analysis [anthropic:claude-haiku-4-5]": 12,
  "expert_research [anthropic:claude-opus-4-8]": 1,
  "expert_research [anthropic:claude-sonnet-5]": 12,
  "grade_arguments [openai:]": 1,
  "judge_score [anthropic:claude-haiku-4-5]": 6,
  "judge_score [openai:]": 9,
  "meta_critique [openai:]": 1,
  "rejected_framings [anthropic:claude-haiku-4-5]": 1,
  "synthesis [anthropic:claude-sonnet-5]": 1
}
Token usage: {
  "by_task_backend": {
    "argument_decompose [anthropic:claude-sonnet-5]": {
      "input_tokens": 94608,
      "output_tokens": 31751
    },
    "argument_map [anthropic:claude-sonnet-5]": {
      "input_tokens": 24147,
      "output_tokens": 7976
    },
    "brief [anthropic:claude-sonnet-5]": {
      "input_tokens": 58916,
      "output_tokens": 34447
    },
    "build_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 45855,
      "output_tokens": 29330
    },
    "critic [openai:]": {
      "input_tokens": 72502,
      "output_tokens": 18108
    },
    "discourse_reciprocity [anthropic:claude-haiku-4-5]": {
      "input_tokens": 141726,
      "output_tokens": 11279
    },
    "discourse_voice [anthropic:claude-haiku-4-5]": {
      "input_tokens": 93726,
      "output_tokens": 58308
    },
    "discourse_voice [anthropic:claude-sonnet-5]": {
      "input_tokens": 127233,
      "output_tokens": 40425
    },
    "expert_analysis [anthropic:claude-haiku-4-5]": {
      "input_tokens": 63947,
      "output_tokens": 63690
    },
    "expert_research [anthropic:claude-opus-4-8]": {
      "input_tokens": 138908,
      "output_tokens": 5429
    },
    "expert_research [anthropic:claude-sonnet-5]": {
      "input_tokens": 1303228,
      "output_tokens": 62305
    },
    "grade_arguments [openai:]": {
      "input_tokens": 10678,
      "output_tokens": 1194
    },
    "judge_score [anthropic:claude-haiku-4-5]": {
      "input_tokens": 30741,
      "output_tokens": 656
    },
    "judge_score [openai:]": {
      "input_tokens": 81180,
      "output_tokens": 5585
    },
    "meta_critique [openai:]": {
      "input_tokens": 1249,
      "output_tokens": 1656
    },
    "rejected_framings [anthropic:claude-haiku-4-5]": {
      "input_tokens": 9979,
      "output_tokens": 1608
    },
    "synthesis [anthropic:claude-sonnet-5]": {
      "input_tokens": 40004,
      "output_tokens": 7749
    }
  },
  "total_input_tokens": 2338627,
  "total_output_tokens": 381496,
  "total_tokens": 2720123,
  "metered_calls": 107,
  "unmetered_calls": 0
}
Errors seen: {
  "expert_analysis [anthropic:claude-haiku-4-5]": [
    "APIStatusError: {'type': 'error', 'error': {'details': None, 'type': 'overloaded_error', 'message': 'Overloaded'}, 'request_id': 'req_011Cd7GBgDAEhJEGR9GC2kTs'}"
  ],
  "brief [anthropic:claude-sonnet-5]": [
    "APIStatusError: {'type': 'error', 'error': {'details': None, 'type': 'overloaded_error', 'message': 'Overloaded'}, 'request_id': 'req_011Cd7JjncW1UChVrj3LKKNE'}"
  ]
}
