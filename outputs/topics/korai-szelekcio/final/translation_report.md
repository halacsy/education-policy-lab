# Translation report (final)

# Critique: translation_checker — round 8

Deterministic HU↔EN parity checks (glossary: docs/glossary.md).

- Scenario-id sets equal: True (EN ['S1', 'S2', 'S3', 'S4'], HU ['S1', 'S2', 'S3', 'S4'])
- Section structure equal: True
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary + back-translation key-term checks: no violations

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "exec_summary [anthropic:claude-sonnet-5]": 1,
  "judge_score [anthropic:claude-haiku-4-5]": 6,
  "judge_score [openai:]": 9
}
Token usage: {
  "by_task_backend": {
    "exec_summary [anthropic:claude-sonnet-5]": {
      "input_tokens": 16857,
      "output_tokens": 2367
    },
    "judge_score [anthropic:claude-haiku-4-5]": {
      "input_tokens": 18471,
      "output_tokens": 528
    },
    "judge_score [openai:]": {
      "input_tokens": 68736,
      "output_tokens": 4122
    }
  },
  "total_input_tokens": 104064,
  "total_output_tokens": 7017,
  "total_tokens": 111081,
  "metered_calls": 16,
  "unmetered_calls": 0
}
Errors seen: {
  "judge_score [openai:]": [
    "RuntimeError: empty response",
    "RuntimeError: empty response",
    "RuntimeError: empty response",
    "RuntimeError: empty response"
  ],
  "exec_summary [anthropic:claude-sonnet-5]": [
    "BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Grammar compilation timed out'}, 'request_id': 'req_011Cd2F6qA9MzcjNFD89Fqeg'}",
    "BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Grammar compilation timed out'}, 'request_id': 'req_011Cd2FQaGhLHzAtRe5qVVxQ'}"
  ]
}
