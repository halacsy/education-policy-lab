# Translation report (final)

# Critique: translation_checker — round 8

Deterministic HU↔EN parity checks (glossary: docs/glossary.md).

- Scenario-id sets equal: True (EN ['S0', 'S1', 'S2', 'S3', 'S4'], HU ['S0', 'S1', 'S2', 'S3', 'S4'])
- Section structure equal: False
- Byte-identical document pairs: none
- Untranslated (identical) fields: none
- Glossary/back-translation violations:
  - EN 'teacher shortage' present but HU 'pedagógushiány' missing

Residual uncertainty (register, connotation — e.g. the historical load of 'egységes alapiskola') cannot be verified mechanically and is flagged for native-speaker review in human_questions.md.

Backend note: {
  "argument_decompose [anthropic(claude-code):claude-opus-4-8]": 11,
  "argument_decompose [mock]": 5,
  "argument_map [anthropic(claude-code):claude-sonnet-5]": 1,
  "brief [mock]": 2,
  "critic [openai(codex):]": 9,
  "decision_readiness [mock]": 1,
  "discourse_reciprocity [mock]": 10,
  "discourse_voice [anthropic(claude-code):claude-haiku-4-5]": 10,
  "discourse_voice [anthropic(claude-code):claude-sonnet-5]": 8,
  "exec_summary [mock]": 2,
  "grade_arguments [openai(codex):]": 1,
  "judge_score [mock]": 6,
  "judge_score [openai(codex):]": 9,
  "meta_critique [openai(codex):]": 1,
  "rejected_framings [anthropic(claude-code):claude-haiku-4-5]": 1,
  "rejected_framings [anthropic(claude-code):claude-sonnet-5]": 1,
  "translate_cluster [mock]": 16,
  "translate_reciprocity [mock]": 10,
  "translate_scenarios [mock]": 1,
  "translate_unknowns [mock]": 1,
  "translate_voice [mock]": 10,
  "unknowns_map [mock]": 1
}
Token usage: {
  "by_task_backend": {},
  "total_input_tokens": 0,
  "total_output_tokens": 0,
  "total_tokens": 0,
  "metered_calls": 0,
  "unmetered_calls": 117
}
Errors seen: {
  "argument_decompose [mock]": [
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: "
  ],
  "discourse_reciprocity [mock]": [
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: ",
    "RuntimeError: claude CLI failed: "
  ]
}
