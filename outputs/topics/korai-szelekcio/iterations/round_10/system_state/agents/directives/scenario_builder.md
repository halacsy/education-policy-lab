# Topic directives: scenario_builder (korai-szelekcio)

Improvement-step directives for THIS topic only (D-35): the
shared spec in agents/ never carries topic learnings; the
improvement step appends here, build_prompt() composes this
into the prompt after the spec's ## Directives header.

- [round-02] DIRECTIVE:uncertainty_quantify — For every uncertainty item, fill the confidence field (low|medium|high) and the reduced_by pair (what evidence would reduce it) in both languages.
- [round-05] DIRECTIVE:evidence_tag_all — Grade EVERY mechanism claim and EVERY expected benefit via its evidence field (strong|moderate|weak|contested), not only the core ones.
- [round-06] DIRECTIVE:implementation_detail — Give every implementation step an explicit timeline field, e.g. 'year 1-2' / '1-2. év'.
