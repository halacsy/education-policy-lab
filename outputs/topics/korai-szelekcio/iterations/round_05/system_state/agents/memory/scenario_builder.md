# Episodic memory: scenario_builder

Deterministic distillation from previous rounds (lab/memory.py); fed back into this agent's prompt. Unresolved items persist until the criticized field changes; resolved items drop.


## round 04 — received
- received [devil_advocate on S3.assumptions]: The assumption "sorting does not simply migrate to school choice between general schools and to non-state maintainers" is the single load-bearing claim on which S3's entire equity case rests, yet it is asserted as a mana
- received [devil_advocate on S2.expected_benefits]: "Stronger peer composition in urban general-school upper grades [evidence: moderate]" is tagged moderate, but this benefit is mechanically downstream of the claim that "general schools can absorb and challenge high-achie
- received [devil_advocate on S4.expected_benefits]: "Politically inexpensive; implementable under any government [evidence: strong]" overclaims certainty for a claim that the scenario's own political_risks field contradicts: "Budget vulnerability: compensation lines are t
- received [devil_advocate on S1.assumptions]: "A workable SES indicator exists at application time" is listed as a bare assumption with no evidence tag and no discussion of what such an indicator would actually be in the Hungarian administrative context (address-bas
- received [evidence_checker on S2.expected_benefits]: "Steadily falling early-sorting share of each cohort (measurable annually) [evidence: strong]" is tagged strong, but no registry source actually measures the effect of entry-place caps on sorting share — this is a mechan
- received [evidence_checker on S4.expected_benefits]: "Politically inexpensive; implementable under any government [evidence: strong]" assigns the top evidence grade to a political-feasibility prediction, but nothing in the curated registry grades political implementability
- received [evidence_checker on S1.expected_benefits]: "More balanced intake into selective tracks within 2-3 admission cycles [evidence: moderate]" attaches a specific, falsifiable timeline (2-3 cycles) to a moderate tag, but the only relevant registry sources (school_choic
- received [evidence_checker on S3.expected_benefits]: "Later, better-informed track choice at 14 reduces misallocation of talent [evidence: moderate]" cites no registry source at all — poland_reform and finland_comprehensive (both moderate) discuss PISA score and equity out
- received [assumption_checker on S4.assumptions]: The assumption "compensation can meaningfully offset, not just mask, the effects of early sorting" directly contradicts S4's own uncertainties field, which states "no country has demonstrated it at Hungary's selection ag
- received [assumption_checker on S3.assumptions]: The assumption "sorting does not simply migrate to school choice between general schools and to non-state maintainers" is asserted with no supporting evidence tag, yet S3's own equity_impact field calls exactly this migr
- received [assumption_checker on S1.assumptions]: "A workable SES indicator exists at application time" is asserted as a plain assumption with no evidence tag and no source — unlike other assumptions across the scenario set, this one is neither flagged as uncertain nor 
- received [assumption_checker on S2.assumptions]: "General schools can absorb and challenge high-achievers if funded for it" is treated as an assumption underpinning the mechanism, but evidence_status explicitly calls this "the unevidenced link," and expected_benefits n
- received [equity_checker on S1.equity_impact]: The equity_impact claims gains "accrue to high-ability low-SES pupils" but this presumes a working SES indicator exists at application time — which the scenario's own assumptions section flags as unresolved ("A workable 
- received [equity_checker on S2.equity_impact]: The text concedes residual selective places "become...even more SES-skewed" absent S1-type reform — but this residual-skew effect is mechanical and near-certain (fewer seats, same demand, no admission-rule change), where
- received [equity_checker on S3.equity_impact]: The equity_impact identifies "largest expected gain" and "largest risk" (middle-class exit to non-state schools) only in aggregate terms; it never addresses distributional equity within the disadvantaged population — e.g
- received [equity_checker on S4.equity_impact]: equity_impact states compensation "narrows the SES gradient at best partially" but omits the dynamic equity cost flagged in political_risks — that compensation risks "legitimising early selection permanently." If compens
- received [feasibility_checker on S1.implementation_steps]: The step "design and pilot the new assessment in volunteer districts" gives no timeline and the cost_categories list this as "low" one-off cost. A genuinely less-coachable, age-appropriate assessment requires psychometri
- received [feasibility_checker on S2.implementation_steps]: "Legislator — enact the cap trajectory with felmenő rendszer guarantees for enrolled pupils" treats a decade-long statutory guarantee across state, church and private maintainers as a single legislative act. Church-maint
- received [feasibility_checker on S3.implementation_steps]: "Launch differentiation retraining at scale" is listed as co-occurring with "pilot comprehensive model in 2-3 districts," but national-scale retraining of the existing teaching workforce in differentiated instruction can
- received [cost_checker on S3.cost_categories]: The one-off costs for "network and building reconfiguration" are explicitly "bundled with demographic consolidation," but no incremental cost attributable to S3 alone is given. Demographic consolidation will happen regar
- received [cost_checker on S2.cost_categories]: "Recurring: advanced-programme funding in general schools (medium, formula-based)" is given as a single static value for a policy explicitly designed to run for a decade with an annually shifting cap. As caps bite and se
- received [cost_checker on S4.cost_categories]: Both recurring cost lines ("high" and "medium-high") lack any numeric range or share-of-budget estimate, which is a serious gap given that the scenario's own political-risk section flags "compensation lines are the first
- received [cost_checker on S1.cost_categories]: The cost categories list only assessment redesign and routine administration but omit any cost for the compliance-audit mechanism that the scenario's own uncertainties section says is needed ("would be reduced by: compli
- received [political_risk_checker on S1.political_risks]: The risk list names "elite-school and middle-class parent opposition" and "church/private maintainer exemption claims" but omits the private tutoring / test-prep industry as an organized political actor. This is a multi-
- received [political_risk_checker on S2.political_risks]: The scenario correctly flags "a successor government can freeze or reverse the trajectory cheaply (Polish precedent)" but no entrenchment mechanism appears anywhere in implementation_steps or cost_categories — the only c
- received [political_risk_checker on S3.political_risks]: "Highest-intensity opposition of all scenarios" is asserted but the response is limited to a pre-legislation "pact attempt" with no fallback if the pact fails — the scenario has no described contingency for what happens 
- received [coherence_checker on S4.expected_benefits]: The claim "Politically inexpensive; implementable under any government [evidence: strong]" directly contradicts S4.political_risks, which states "Budget vulnerability: compensation lines are the first cut in fiscal conso
- received [coherence_checker on S2.mechanism]: "Annual entry-place caps reduce the share of a cohort selected at 10/12, mechanically lowering early sorting [evidence: strong]" treats the cap as self-enforcing, but S2.assumptions ("Caps are enforceable across state, c
- received [coherence_checker on S3.political_risks]: S3.

## round 04 — resolved from previous round
- RESOLVED [assumption_checker on S1.assumptions] (field changed)
- RESOLVED [assumption_checker on S2.assumptions] (field changed)
- RESOLVED [assumption_checker on S3.mechanism] (field changed)
- RESOLVED [assumption_checker on S4.assumptions] (field changed)
- RESOLVED [coherence_checker on S1.assumptions] (field changed)
- RESOLVED [coherence_checker on S2.assumptions] (field changed)
- RESOLVED [coherence_checker on S3.evidence_status] (field changed)
- RESOLVED [coherence_checker on S4.cost_categories] (field changed)
- RESOLVED [cost_checker on S1.cost_categories] (field changed)
- RESOLVED [cost_checker on S2.cost_categories] (field changed)
- RESOLVED [cost_checker on S3.cost_categories] (field changed)
- RESOLVED [cost_checker on S4.cost_categories] (field changed)
- RESOLVED [devil_advocate on S1.assumptions] (field changed)
- RESOLVED [devil_advocate on S2.assumptions] (field changed)
- RESOLVED [devil_advocate on S3.evidence_status] (field changed)
- RESOLVED [devil_advocate on S4.assumptions] (field changed)
- RESOLVED [equity_checker on S1.equity_impact] (field changed)
- RESOLVED [equity_checker on S2.equity_impact] (field changed)
- RESOLVED [equity_checker on S3.equity_impact] (field changed)
- RESOLVED [equity_checker on S4.equity_impact] (field changed)
- RESOLVED [evidence_checker on S3.mechanism] (field changed)
- RESOLVED [evidence_checker on S1.mechanism] (field changed)
- RESOLVED [evidence_checker on S2.expected_benefits] (field changed)
- RESOLVED [feasibility_checker on S2.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S1.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S3.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S4.implementation_steps] (field changed)
- RESOLVED [political_risk_checker on S1.political_risks] (field changed)
- RESOLVED [political_risk_checker on S2.political_risks] (field changed)
