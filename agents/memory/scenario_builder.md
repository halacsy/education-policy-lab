# Episodic memory: scenario_builder

Deterministic distillation from previous rounds (lab/memory.py); fed back into this agent's prompt. Unresolved items persist until the criticized field changes; resolved items drop.


## round 07 — received
- received [devil_advocate on S3.mechanism]: S3’s core mechanism rests on asymmetric peer effects, but the scenario admits that this claim is contested and unverified for Hungary. The strong international evidence supports delayed tracking reducing inequality, not 
- received [devil_advocate on S2.implementation_steps]: The “multi-party pact / legislative lock” is treated as an implementation step, but the evidence cited actually shows the opposite risk: Poland’s reform was reversed despite earlier gains. Nothing in the scenario support
- received [devil_advocate on S4.mechanism]: The load-bearing claim that compensation can offset early-selection segregation is unsupported. Portugal’s TEIP and curriculum evidence supports gains without changing selection age in Portugal, but it does not support o
- received [devil_advocate on S1.expected_benefits]: “No loss of value-added for admitted pupils” is stronger than the evidence supports. Evidence that current advantages are largely selection effects weakens the case for large track-specific value-added, but it does not p
- received [evidence_checker on S1.mechanism]: The claim that “centrally standardised admission assessment replaces teacher-level gatekeeping” is not supported at [evidence: moderate]. The registry-backed `gimn_share` source says 6/8-year gimnazium entry is already s
- received [evidence_checker on S2.mechanism]: The claim that a felmenő rendszer guarantee “lowers legal and parental resistance” is tagged [evidence: strong], but the registry does not support that strength. `legal` strongly supports that phase-out requires legislat
- received [evidence_checker on S3.expected_benefits]: The “0.15–0.25 SD equity gain range in comparable systems” is tagged [evidence: moderate], but that numeric range is not in the curated registry. The registry supports a general inequality effect from earlier tracking (`
- received [evidence_checker on S4.uncertainties]: The uncertainty “Do TEIP/curriculum mechanisms transfer given Hungarian teacher shortages?” is marked [confidence: high], but the scenario’s own evidence base only supports Portugal’s improvement as moderate and teacher 
- received [assumption_checker on S1.assumptions]: The scenario assumes “SES classification / coaching-resistance can be audited with ≥85% accuracy,” but the expert record only supports a proposed gate for SES-classification accuracy. It does not support auditing “coachi
- received [assumption_checker on S1.mechanism]: The claim that maintainer-uniform admission rules “prevent selective intake from migrating” is stronger than the evidence supports. The expert record strongly supports maintainer fragmentation and the risk that non-state
- received [assumption_checker on S2.implementation_steps]: The first step assumes a “multi-party pact / legislative lock” can secure sustained political capital and protect the cap trajectory, but the expert record explicitly cites Poland’s 2016–2019 reversal as evidence that ev
- received [assumption_checker on S4.uncertainties]: The uncertainty “Do TEIP/curriculum mechanisms transfer given Hungarian teacher shortages? [confidence: high]” contradicts the scenario’s own evidence status. The scenario says transfer to Hungary is an assumption and th
- received [equity_checker on S1.equity_impact]: The field correctly says the non-selected 88–92% majority receives no direct benefit, but it still claims S1 “directly helps high-ability low-SES pupils” without confronting the likely exclusion of low-SES pupils who are
- received [equity_checker on S2.equity_impact]: The field says S2 “widens the pool exposed to mixed-ability lower-secondary,” but it does not identify who may be harmed during the decade-long transition. Cohorts in schools losing selective-track prestige or resources 
- received [equity_checker on S3.equity_impact]: The equity-negative threshold focuses on top-SES exit, but it ignores a second equity-negative pathway: disadvantaged pupils could be concentrated in the weakest comprehensive schools if teacher shortages and catchment c
- received [equity_checker on S4.equity_impact]: The field says S4 improves absolute outcomes for the non-selected majority in disadvantaged schools, but the evidence only supports targeted funding and curriculum mechanisms moderately in Portugal, not in Hungary under 
- received [feasibility_checker on S1.implementation_steps]: The year 2-4 step to “negotiate and legislate maintainer-uniform admission rules covering church/foundation schools” is operationally under-specified and likely too compressed. The evidence base says maintainer fragmenta
- received [feasibility_checker on S2.implementation_steps]: The step “Government + legislature — enact a multi-party pact / legislative lock” in year 1 is unsupported as an implementation capacity claim. The evidence supports that Poland’s reform was reversed and that political d
- received [feasibility_checker on S3.implementation_steps]: The teacher-supply sequence is internally infeasible: S3 requires a 10-year teacher-supply forecast before rollout, but also schedules differentiation retraining in shortage-worst schools during years 1-4. The implementa
- received [feasibility_checker on S4.cost_categories]: S4 identifies recurring targeted funding as the dominant cost but gives no administrative or teacher-capacity cost for delivering TEIP-style intensive support under Hungarian shortages. The Portugal evidence supports non
- received [cost_checker on S1.cost_categories]: The one-off cost range “low tens of HUF billion” for designing and validating a central assessment instrument is unsupported by the evidence presented. The scenario tags it [evidence: weak] but still gives a specific ord
- received [cost_checker on S2.cost_categories]: The cost categories confuse freed capacity with usable fiscal space. “Reinvestment into general-school advanced programmes” is listed as recurring and scaling with phase-down pace, but the scenario does not price whether
- received [cost_checker on S3.cost_categories]: The field lists major one-off transition costs but omits the likely recurring cost of maintaining smaller-group differentiation, support staff, counselling, remedial provision, and teacher retention incentives after roll
- received [cost_checker on S4.cost_categories]: The −30% budget sensitivity is directionally useful but under-specified: it asserts that TEIP-style targeting loses the “intensity threshold Portugal relied on” without naming the threshold or showing that Portugal’s evi
- received [political_risk_checker on S1.political_risks]: The maintainer-exemption risk is named but not entrenched. The scenario says maintainer-uniform admission rules mitigate migration to church/foundation schools, yet the evidence tag is explicitly [evidence: contested] an
- received [political_risk_checker on S2.political_risks]: The “multi-party pact / legislative lock” is asserted as a reversal mitigation, but the evidence base does not support that it would be durable in Hungary. The scenario itself marks durability of a multi-party pact as lo
- received [political_risk_checker on S3.political_risks]: Reversal risk is underdeveloped for the scenario with the highest political capital demand. S3 names “reversal under electoral turnover despite measurable gains,” but offers no entrenchment design comparable to its scale
- received [political_risk_checker on S4.political_risks]: The scenario understates the political risk that compensatory funding becomes a legitimising cover for continued stratification. It notes selection skew persists and targeted funding is vulnerable, but does not connect t
- received [coherence_checker on S1.mechanism]: The mechanism claims maintainer-uniform admission rules prevent selective intake from migrating to church/foundation schools, but the scenario simultaneously treats maintainer exemption/migration as severe and only conti
- received [coherence_checker on S2.implementation_steps]: Step 1 says the government and legislature will enact a multi-party pact / legislative lock securing sustained political capital against reversal, but the political_risks and uncertainties admit durability against electo
- received [coherence_checker on S3.expected_benefits]: “No mean-performance loss where late-tracking evidence holds” is tagged `[evidence: moderate]`, but S3’s own mechanism says the load-bearing Hungarian claim is contested: if peer effects are symmetric, S3 redistributes l
- received [coherence_checker on S4.uncertainties]: The uncertainty “Do TEIP/curriculum mechanisms transfer given Hungarian teacher shortages?” is marked `[confidence: high]`, but the surrounding scenario repeatedly says transferability is assumed, budget-elastic, and onl

## round 07 — resolved from previous round
- RESOLVED [assumption_checker on S3.assumptions] (field changed)
- RESOLVED [assumption_checker on S4.assumptions] (field changed)
- RESOLVED [coherence_checker on S1.mechanism] (field changed)
- RESOLVED [coherence_checker on S1.expected_benefits] (field changed)
- RESOLVED [coherence_checker on S2.equity_impact] (field changed)
- RESOLVED [coherence_checker on S3.assumptions] (field changed)
- RESOLVED [cost_checker on S1.cost_categories] (field changed)
- RESOLVED [cost_checker on S2.cost_categories] (field changed)
- RESOLVED [cost_checker on S3.cost_categories] (field changed)
- RESOLVED [cost_checker on S4.cost_categories] (field changed)
- RESOLVED [devil_advocate on S1.assumptions] (field changed)
- RESOLVED [devil_advocate on S1.expected_benefits] (field changed)
- RESOLVED [devil_advocate on S2.assumptions] (field changed)
- RESOLVED [devil_advocate on S2.expected_benefits] (field changed)
- RESOLVED [devil_advocate on S3.assumptions] (field changed)
- RESOLVED [devil_advocate on S3.expected_benefits] (field changed)
- RESOLVED [devil_advocate on S4.assumptions] (field changed)
- RESOLVED [devil_advocate on S4.expected_benefits] (field changed)
- RESOLVED [equity_checker on S1.equity_impact] (field changed)
- RESOLVED [equity_checker on S2.equity_impact] (field changed)
- RESOLVED [equity_checker on S3.equity_impact] (field changed)
- RESOLVED [equity_checker on S4.equity_impact] (field changed)
- RESOLVED [evidence_checker on S1.goal] (field changed)
- RESOLVED [evidence_checker on S1.mechanism] (field changed)
- RESOLVED [evidence_checker on S1.expected_benefits] (field changed)
- RESOLVED [evidence_checker on S2.mechanism] (field changed)
- RESOLVED [evidence_checker on S3.mechanism] (field changed)
- RESOLVED [evidence_checker on S3.equity_impact] (field changed)
- RESOLVED [evidence_checker on S4.mechanism] (field changed)
- RESOLVED [feasibility_checker on S1.assumptions] (field changed)
- RESOLVED [feasibility_checker on S1.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S2.assumptions] (field changed)
- RESOLVED [feasibility_checker on S3.assumptions] (field changed)
- RESOLVED [political_risk_checker on S1.political_risks] (field changed)
- RESOLVED [political_risk_checker on S2.political_risks] (field changed)
- RESOLVED [political_risk_checker on S3.political_risks] (field changed)
- RESOLVED [political_risk_checker on S4.political_risks] (field changed)
