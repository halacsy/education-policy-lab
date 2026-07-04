# Critique: assumption_checker

## S3.evidence_status
Objection: The tag "contested" is defensible, but the mechanism labels contradict it in a way that overstates the case. Mechanism line 1 ("Later between-school selection weakens the SES-performance link") is tagged [evidence: strong], yet the expert record's disagreement map shows this is precisely the contested core between the majority and the portuguese_reform/political_feasibility minority. Cross-country tracking evidence supports the *direction*, but attributing "strong" to the causal claim for the Hungarian context — where implementation capacity is disputed — conflates external evidence with local applicability. The source supports "the direction of effect is strong in cross-country studies," not "strong for Hungary."
Severity: high
Suggested revision: Downgrade mechanism line 1 to [evidence: moderate] with the qualifier "cross-country tracking evidence strong; Hungarian applicability contested," aligning it with the evidence_status tag.

## S3.assumptions
Objection: The assumption "Sorting does not simply migrate to school choice between general schools and to non-state maintainers" is stated as an assumption but is actively contradicted by the scenario's own equity_impact and political_risks fields, which treat middle-class exit to non-state schools as a live, high-probability threat ("segregation could worsen relative to baseline"). Listing as an assumption something you elsewhere flag as a likely failure mode is internally contradictory — it is not an assumption, it is the central unresolved risk.
Severity: high
Suggested revision: Remove this from assumptions and reframe as the primary uncertainty/risk (which it already partly is), or restate the assumption conditionally: "sorting migration can be contained *if* non-state maintainer exemptions are legally closed."

## S4.expected_benefits
Objection: The benefit "Politically inexpensive; implementable under any government" is tagged [evidence: strong], but this is an unsupported claim, not a strong-evidence one. The cost_categories field itself lists targeted funding as "high" (recurring) and teacher premia as "medium-high," and the political_risks field states compensation lines "are the first cut in fiscal consolidation." A policy whose core funding is fiscally vulnerable is not "politically inexpensive" in any durable sense; the [evidence: strong] tag cannot attach to a claim the scenario's own fields undercut.
Severity: high
Suggested revision: Split the claim: retain "low political-capital cost to enact [evidence: moderate]" but drop "inexpensive/durable" framing and downgrade to [evidence: weak], cross-referencing the budget-vulnerability risk.

## S2.assumptions
Objection: The assumption "Caps are enforceable across state, church and private maintainers" is treated as a binary condition, but the political_risks and uncertainties fields treat church-maintainer exemption/litigation as a serious live threat, and the synthesis notes non-state maintainer growth. The scenario's mechanical sorting-reduction claim [evidence: strong] depends entirely on this assumption holding across all maintainer types — if church/private caps fail, the "strong" mechanical effect degrades to state-sector-only, which is unsupported for the system-level goal.
Severity: medium
Suggested revision: Condition the [evidence: strong] mechanism tag on maintainer coverage: state "mechanical reduction is strong for capped places; system-level effect depends on non-state maintainer inclusion (contested)."