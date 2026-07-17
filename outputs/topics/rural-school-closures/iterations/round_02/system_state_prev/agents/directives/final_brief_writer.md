# Topic directives: final_brief_writer (rural-school-closures)

Improvement-step directives for THIS topic only (D-35): the
shared spec in agents/ never carries topic learnings; the
improvement step appends here, build_prompt() composes this
into the prompt after the spec's ## Directives header.
- [round-02] DIRECTIVE:layer_tighten — Every substantive claim across the brief's 10 sections carries a claim-kind tag ([fact]/[estimate]/[assumption]/[value], unchanged in every language); a substantive claim without one is a defect.
- [round-02] DIRECTIVE:scenario_crossref — The brief must be self-contained: right after the introduction, add a scenario key section ('## Scenario key' / HU: '## Forgatókönyv-kulcs') listing each scenario id with its one-line title and a reference to the full scenario document (scenarios.en.md / scenarios.hu.md), so no recommendation refers to an id the reader cannot resolve.
