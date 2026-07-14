# Critique: coherence_checker

## S4.expected_benefits
Objection: The claim "Politically inexpensive; implementable under any government [evidence: strong]" directly contradicts S4.political_risks, which states "Budget vulnerability: compensation lines are the first cut in fiscal consolidation." A policy whose funding line is the first casualty of fiscal consolidation is not "implementable under any government" in any durable sense — at most the evidence supports low *initial* political cost of adoption, not sustained implementability. The "strong" tag is applied to the wrong claim: Portugal's TEIP experience supports ease of launch, not durability across fiscal cycles.
Severity: high
Suggested revision: Split the benefit into two separately-tagged claims — "low adoption cost [evidence: strong]" and "durability across governments/budgets [evidence: weak]" — and cross-reference the budget-vulnerability risk directly in expected_benefits so the two fields cannot be read as contradicting each other.

## S2.mechanism
Objection: "Annual entry-place caps reduce the share of a cohort selected at 10/12, mechanically lowering early sorting [evidence: strong]" treats the cap as self-enforcing, but S2.assumptions ("Caps are enforceable across state, church and private maintainers") and S2.political_risks ("Church maintainers may litigate or negotiate exemptions") both flag maintainer compliance as an open, contested question. The "strong" evidence tag is only warranted for the arithmetic identity (fewer places → fewer selected) under full compliance; it says nothing about the real-world sorting reduction if church/private maintainers secure exemptions, which the scenario itself treats as a live political risk, not a settled assumption.
Severity: high
Suggested revision: Downgrade the mechanism tag to "strong (conditional on full maintainer compliance); moderate otherwise" and add a sub-claim on partial-compliance scenarios, quantifying the sorting reduction if e.g. church-maintained gimnaziums are exempted.

## S3.political_risks
Objection: S3.