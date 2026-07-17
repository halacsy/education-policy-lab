# Topic directives: final_brief_writer (korai-szelekcio)

Improvement-step directives for THIS topic only (D-35): the
shared spec in agents/ never carries topic learnings; the
improvement step appends here, build_prompt() composes this
into the prompt after the spec's ## Directives header.

- [round-04] DIRECTIVE:minority_report — Fill minority_positions with every minority/dissenting position (holders + rationale), proportionally, never resolved away.
- [round-07] DIRECTIVE:layer_tighten — Every substantive claim carries an honest kind field (fact/estimate/assumption/value — rendered as the language-independent claim-kind tag); a substantive claim without one is a defect.
- [round-09] DIRECTIVE:scenario_crossref — The brief must be self-contained: right after the introduction, add a scenario key section ('## Scenario key' / HU: '## Forgatókönyv-kulcs') listing each scenario id with its one-line title and a reference to the full scenario document (scenarios.en.md / scenarios.hu.md), so no recommendation refers to an id the reader cannot resolve.
