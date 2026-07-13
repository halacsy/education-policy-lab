# Translation report (final)

# Critique: translation_checker — round 7

Deterministic HU↔EN parity checks (glossary: docs/glossary.md).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4'], HU ['S1', 'S2', 'S3', 'S4'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary/back-translation violations:
  - HU 'iskolaválasztás' present but EN 'school choice' missing (back-translation)

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "argument_map [anthropic:claude-opus-4-8]": 1,
  "argument_map [anthropic:claude-sonnet-5]": 1,
  "brief [anthropic:claude-opus-4-8]": 1,
  "brief [anthropic:claude-sonnet-5]": 1,
  "brief [mock]": 1,
  "build_scenarios [anthropic:claude-opus-4-8]": 1,
  "build_scenarios [anthropic:claude-sonnet-5]": 1,
  "critic [openai(codex):]": 8,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 10,
  "discourse_reciprocity [anthropic:claude-sonnet-5]": 5,
  "discourse_voice [anthropic:claude-haiku-4-5]": 10,
  "expert_analysis [anthropic:claude-haiku-4-5]": 3,
  "grade_arguments [openai(codex):]": 1,
  "judge_score [anthropic:claude-haiku-4-5]": 6,
  "judge_score [openai(codex):]": 9,
  "meta_critique [openai(codex):]": 1,
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
      "input_tokens": 48597,
      "output_tokens": 11022
    },
    "argument_map [anthropic:claude-sonnet-5]": {
      "input_tokens": 48540,
      "output_tokens": 16000
    },
    "brief [anthropic:claude-opus-4-8]": {
      "input_tokens": 77526,
      "output_tokens": 5795
    },
    "brief [anthropic:claude-sonnet-5]": {
      "input_tokens": 77469,
      "output_tokens": 11594
    },
    "build_scenarios [anthropic:claude-opus-4-8]": {
      "input_tokens": 17055,
      "output_tokens": 7076
    },
    "build_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 16998,
      "output_tokens": 16000
    },
    "discourse_reciprocity [anthropic:claude-haiku-4-5]": {
      "input_tokens": 62756,
      "output_tokens": 27593
    },
    "discourse_reciprocity [anthropic:claude-sonnet-5]": {
      "input_tokens": 46779,
      "output_tokens": 14356
    },
    "discourse_voice [anthropic:claude-haiku-4-5]": {
      "input_tokens": 53696,
      "output_tokens": 37666
    },
    "expert_analysis [anthropic:claude-haiku-4-5]": {
      "input_tokens": 4068,
      "output_tokens": 3224
    },
    "judge_score [anthropic:claude-haiku-4-5]": {
      "input_tokens": 19698,
      "output_tokens": 553
    },
    "rejected_framings [anthropic:claude-haiku-4-5]": {
      "input_tokens": 6671,
      "output_tokens": 1602
    },
    "synthesis [anthropic:claude-opus-4-8]": {
      "input_tokens": 14474,
      "output_tokens": 2682
    },
    "synthesis [anthropic:claude-sonnet-5]": {
      "input_tokens": 14417,
      "output_tokens": 4000
    },
    "translate_ledger [anthropic:claude-opus-4-8]": {
      "input_tokens": 70262,
      "output_tokens": 16000
    },
    "translate_ledger [anthropic:claude-sonnet-5]": {
      "input_tokens": 70205,
      "output_tokens": 16000
    },
    "translate_scenarios [anthropic:claude-opus-4-8]": {
      "input_tokens": 10738,
      "output_tokens": 10494
    },
    "translate_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 10681,
      "output_tokens": 16000
    }
  },
  "total_input_tokens": 670630,
  "total_output_tokens": 217657,
  "total_tokens": 888287,
  "metered_calls": 47,
  "unmetered_calls": 20
}
