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
  "argument_decompose [anthropic:claude-opus-4-8]": 18,
  "argument_map [anthropic:claude-opus-4-8]": 1,
  "argument_map [anthropic:claude-sonnet-5]": 1,
  "brief [anthropic:claude-opus-4-8]": 1,
  "brief [anthropic:claude-sonnet-5]": 2,
  "build_scenarios [anthropic:claude-sonnet-5]": 1,
  "critic [openai(codex):]": 8,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 10,
  "discourse_reciprocity [anthropic:claude-sonnet-5]": 9,
  "discourse_voice [anthropic:claude-haiku-4-5]": 10,
  "expert_analysis [anthropic:claude-haiku-4-5]": 3,
  "grade_arguments [openai(codex):]": 1,
  "judge_score [anthropic:claude-haiku-4-5]": 6,
  "judge_score [openai(codex):]": 9,
  "meta_critique [openai(codex):]": 1,
  "rejected_framings [anthropic:claude-haiku-4-5]": 1,
  "synthesis [anthropic:claude-sonnet-5]": 1,
  "translate_cluster [anthropic:claude-opus-4-8]": 18,
  "translate_reciprocity [anthropic:claude-opus-4-8]": 17,
  "translate_scenarios [anthropic:claude-sonnet-5]": 1,
  "translate_voice [anthropic:claude-opus-4-8]": 20
}
Token usage: {
  "by_task_backend": {
    "argument_decompose [anthropic:claude-opus-4-8]": {
      "input_tokens": 117080,
      "output_tokens": 10767
    },
    "argument_map [anthropic:claude-opus-4-8]": {
      "input_tokens": 51213,
      "output_tokens": 4185
    },
    "argument_map [anthropic:claude-sonnet-5]": {
      "input_tokens": 51156,
      "output_tokens": 5838
    },
    "brief [anthropic:claude-opus-4-8]": {
      "input_tokens": 93663,
      "output_tokens": 6669
    },
    "brief [anthropic:claude-sonnet-5]": {
      "input_tokens": 104604,
      "output_tokens": 18965
    },
    "build_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 18301,
      "output_tokens": 9303
    },
    "discourse_reciprocity [anthropic:claude-haiku-4-5]": {
      "input_tokens": 133185,
      "output_tokens": 29385
    },
    "discourse_reciprocity [anthropic:claude-sonnet-5]": {
      "input_tokens": 177860,
      "output_tokens": 11454
    },
    "discourse_voice [anthropic:claude-haiku-4-5]": {
      "input_tokens": 69156,
      "output_tokens": 39717
    },
    "expert_analysis [anthropic:claude-haiku-4-5]": {
      "input_tokens": 3486,
      "output_tokens": 2940
    },
    "judge_score [anthropic:claude-haiku-4-5]": {
      "input_tokens": 20265,
      "output_tokens": 546
    },
    "rejected_framings [anthropic:claude-haiku-4-5]": {
      "input_tokens": 9392,
      "output_tokens": 2409
    },
    "synthesis [anthropic:claude-sonnet-5]": {
      "input_tokens": 13988,
      "output_tokens": 3793
    },
    "translate_cluster [anthropic:claude-opus-4-8]": {
      "input_tokens": 83258,
      "output_tokens": 18171
    },
    "translate_reciprocity [anthropic:claude-opus-4-8]": {
      "input_tokens": 93567,
      "output_tokens": 33178
    },
    "translate_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 12933,
      "output_tokens": 14283
    },
    "translate_voice [anthropic:claude-opus-4-8]": {
      "input_tokens": 180758,
      "output_tokens": 120000
    }
  },
  "total_input_tokens": 1233865,
  "total_output_tokens": 331603,
  "total_tokens": 1565468,
  "metered_calls": 120,
  "unmetered_calls": 19
}
Errors seen: {}
