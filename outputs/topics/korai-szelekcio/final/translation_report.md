# Translation report (final)

# Critique: translation_checker — round 10

Deterministic HU↔EN parity checks (glossary: the topic glossary (topics/<slug>/glossary.md)).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4', 'S5'], HU ['S1', 'S2', 'S3', 'S4', 'S5'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary + back-translation key-term checks: no violations

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "argument_decompose [anthropic:claude-sonnet-5]": 41,
  "argument_map [anthropic:claude-sonnet-5]": 2,
  "brief [anthropic:claude-sonnet-5]": 2,
  "build_scenarios [anthropic:claude-sonnet-5]": 1,
  "critic [openai:]": 16,
  "discourse_reciprocity [anthropic:claude-haiku-4-5]": 20,
  "discourse_voice [anthropic:claude-haiku-4-5]": 20,
  "discourse_voice [anthropic:claude-sonnet-5]": 19,
  "expert_analysis [anthropic:claude-haiku-4-5]": 13,
  "expert_research [anthropic:claude-opus-4-8]": 1,
  "expert_research [anthropic:claude-sonnet-5]": 13,
  "grade_arguments [openai:]": 2,
  "judge_score [anthropic:claude-haiku-4-5]": 12,
  "judge_score [openai:]": 18,
  "meta_critique [openai:]": 2,
  "rejected_framings [anthropic:claude-haiku-4-5]": 2,
  "rejected_framings [anthropic:claude-sonnet-5]": 1,
  "synthesis [anthropic:claude-opus-4-8]": 1,
  "synthesis [anthropic:claude-sonnet-5]": 2
}
Token usage: {
  "by_task_backend": {
    "argument_decompose [anthropic:claude-sonnet-5]": {
      "input_tokens": 254302,
      "output_tokens": 59701
    },
    "argument_map [anthropic:claude-sonnet-5]": {
      "input_tokens": 48618,
      "output_tokens": 12876
    },
    "brief [anthropic:claude-sonnet-5]": {
      "input_tokens": 129018,
      "output_tokens": 64033
    },
    "build_scenarios [anthropic:claude-sonnet-5]": {
      "input_tokens": 56188,
      "output_tokens": 33847
    },
    "critic [openai:]": {
      "input_tokens": 172036,
      "output_tokens": 38148
    },
    "discourse_reciprocity [anthropic:claude-haiku-4-5]": {
      "input_tokens": 295411,
      "output_tokens": 48787
    },
    "discourse_voice [anthropic:claude-haiku-4-5]": {
      "input_tokens": 244492,
      "output_tokens": 106052
    },
    "discourse_voice [anthropic:claude-sonnet-5]": {
      "input_tokens": 342709,
      "output_tokens": 81826
    },
    "expert_analysis [anthropic:claude-haiku-4-5]": {
      "input_tokens": 94300,
      "output_tokens": 77165
    },
    "expert_research [anthropic:claude-opus-4-8]": {
      "input_tokens": 127847,
      "output_tokens": 4344
    },
    "expert_research [anthropic:claude-sonnet-5]": {
      "input_tokens": 1350989,
      "output_tokens": 70663
    },
    "grade_arguments [openai:]": {
      "input_tokens": 25243,
      "output_tokens": 8203
    },
    "judge_score [anthropic:claude-haiku-4-5]": {
      "input_tokens": 65685,
      "output_tokens": 1206
    },
    "judge_score [openai:]": {
      "input_tokens": 167787,
      "output_tokens": 9744
    },
    "meta_critique [openai:]": {
      "input_tokens": 2744,
      "output_tokens": 5147
    },
    "rejected_framings [anthropic:claude-haiku-4-5]": {
      "input_tokens": 24342,
      "output_tokens": 3363
    },
    "rejected_framings [anthropic:claude-sonnet-5]": {
      "input_tokens": 18360,
      "output_tokens": 2079
    },
    "synthesis [anthropic:claude-opus-4-8]": {
      "input_tokens": 49965,
      "output_tokens": 8258
    },
    "synthesis [anthropic:claude-sonnet-5]": {
      "input_tokens": 98880,
      "output_tokens": 18524
    }
  },
  "total_input_tokens": 3568916,
  "total_output_tokens": 653966,
  "total_tokens": 4222882,
  "metered_calls": 188,
  "unmetered_calls": 0
}
Errors seen: {
  "discourse_voice [anthropic:claude-haiku-4-5]": [
    "APIStatusError: {'type': 'error', 'error': {'details': None, 'type': 'overloaded_error', 'message': 'Overloaded'}, 'request_id': 'req_011CdB474bXyGRr2EhprbvjS'}",
    "APIStatusError: {'type': 'error', 'error': {'details': None, 'type': 'overloaded_error', 'message': 'Overloaded'}, 'request_id': 'req_011CdB4ECJ5eXW3oVtzJCkfW'}"
  ]
}
