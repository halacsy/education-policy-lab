# Episodic memory: scenario_builder

Deterministic distillation from previous rounds (lab/memory.py); fed back into this agent's prompt. Unresolved items persist until the criticized field changes; resolved items drop.


## round 03 — received
- received [devil_advocate on S1.assumptions]: The assumption that "middle-class parents will accept admissions quotas rather than seeking to bypass them through non-state alternatives" directly contradicts the scenario's own Political Risks section, which asserts "i
- received [devil_advocate on S2.assumptions]: The assumption that "non-state school maintainers can be restricted from absorbing the phased-out selective capacity" is flatly contradicted by the disagreement map, where the hungarian_education_system/school_network_pl
- received [devil_advocate on S3.evidence_status]: The scenario labels overall evidence_status "Strong — Supported by robust international difference-in-differences and longitudinal reform studies," yet its own Uncertainties section rates confidence as "low" on "the prec
- received [devil_advocate on S4.assumptions]: The assumption "the teacher shortage cannot be mitigated in the short term through wage increases or recruitment alone" is asserted with no evidence tag, yet it is the linchpin justifying why a compensatory (non-structur
- received [evidence_checker on S3.mechanism]: The claim that "postponing academic tracking until age 14 or 15 significantly reduces the impact of parental background on achievement" is tagged a single "strong" evidence grade backed by three citations, but two of tho
- received [evidence_checker on S1.mechanism]: The first mechanism bullet claims aligning entry requirements/quotas with equity targets and regulating non-state admissions "restricts socio-demographic sorting," tagged "moderate — hungarian_education_system findings."
- received [evidence_checker on S2.expected_benefits]: Both benefit claims — "mitigates geographic sorting" (tagged moderate, "school_network_planning findings") and "reduces the socio-economic gradient... over the long term" (tagged moderate, "international_comparison findi
- received [assumption_checker on S1.assumptions]: The assumption "Middle-class parents will accept admissions quotas rather than seeking to bypass them through non-state alternatives" is directly contradicted elsewhere in the same scenario and by the expert record. S1's
- received [assumption_checker on S2.assumptions]: The assumption "Non-state school maintainers can be restricted from absorbing the phased-out selective capacity" is unsupported and appears to contradict the expert record's agreed fact on "maintainer fragmentation" — th
- received [assumption_checker on S3.mechanism]: The mechanism claims "phasing out early selection prevents demographic cohort shrinkage from accelerating the collapse and forced consolidation of rural primary school networks" [evidence: moderate]. This contradicts the
- received [assumption_checker on S4.assumptions]: The assumption "The teacher shortage cannot be mitig
- received [equity_checker on S1.equity_impact]: The equity_impact claim treats "equity" as purely socio-economic sorting within selective tracks, but ignores who is structurally excluded from the analysis entirely: students in settlements with no non-state alternative
- received [equity_checker on S2.equity_impact]: The claim "Significantly improves equity in the long run" is stated as the headline conclusion, but it is explicitly conditioned on "non-state sectors do not absorb the phased-out capacity" — an assumption the scenario's
- received [equity_checker on S3.equity_impact]: "Maximizes educational equity" is asserted without acknowledging a distributional trade-off documented elsewhere in the same scenario: forced rural school consolidation (mentioned in cost_categories as "expanded student 
- received [equity_checker on S4.equity_impact]: The claim "improves equity for students in targeted disadvantaged schools" assumes TEIP-style targeting can accurately identify and reach Hungary's disadvantaged population, but Hungary's disadvantaged/Roma population is
- received [feasibility_checker on S2.implementation_steps]: The step assigns Klebelsberg Centre (KK) to "coordinate the shift of secondary teaching hours toward standard 4-year tracks," treating teacher redeployment as an administrative logistics task. But the expert record's imp
- received [feasibility_checker on S1.implementation_steps]: The step has the Ministry "issue a ministerial decree governing secondary admissions and establishing equity-based quotas," but S1's own assumptions concede "the government lacks the immediate political or legal leverage
- received [feasibility_checker on S3.implementation_steps]: The step calls for a "comprehensive legislative ban on all academic selection before grade 8, effective in a gradual teach-out system," but does not specify how this satisfies the acquired-rights constitutional constrain
- received [feasibility_checker on S4.implementation_steps]: The step directs KK to "route discretionary funding packages and deployment incentives to designated low-performing primary schools," but the synthesis explicitly characterizes Hungary's school administration as "fragile
- received [cost_checker on S1.cost_categories]: The cost list (admissions administration/monitoring/enforcement, litigation) omits the fiscal cost of the "displacement to unregulated non-state schools" risk that the scenario's own equity_impact field flags as "high." 
- received [cost_checker on S2.cost_categories]: The field conflates transition and steady-state costs, contradicting the cross-scenario agreement ("Flat steady-state operational costs: Per-pupil operational funding differences... are modest; structural reform costs ar
- received [cost_checker on S3.cost_categories]: The category list (retraining, capital expenditure, transportation) has no quantification or range despite the uncertainties section explicitly flagging cost as unresolved ("would be reduced by: detailed Ministry of Fina
- received [cost_checker on S4.cost_categories]: The recurring TEIP-style funding and retention-incentive lines are not tied to any fiscal range or duration, despite political_risks explicitly citing "risk of reform dilution due to lack of sustained budgetary commitmen
- received [political_risk_checker on S1.political_risks]: The listed risks (middle-class parent resistance, church litigation) omit the more fundamental reversal vulnerability embedded in the mechanism/implementation_steps: the reform is implemented via "ministerial decree," no
- received [political_risk_checker on S2.political_risks]: The risks named (elite-school resistance, middle-class flight) ignore the scenario's own assumption that "church and private maintainers will eventually comply with the phased contraction" — an assumption the disagreemen
- received [coherence_checker on S1.assumptions]: The assumption "Middle-class parents will accept admissions quotas rather than seeking to bypass them through non-state alternatives" directly contradicts two other fields in the same scenario: political_risks states "In
- received [coherence_checker on S2.assumptions]: The assumption "Non-state school maintainers can be restricted from absorbing the phased-out selective capacity" is contradicted by the scenario's own political_risks ("Middle-class flight to private or shadow education 
- received [coherence_checker on S3.evidence_status]: Evidence_status and expected_benefits claim "strong" support (Hanushek & Woessmann 2006; Pekkarinen et al. 2009; Jakubowski et al. 2016) for the causal effect of postponing tracking on reducing the SES gradient, yet the 
- received [coherence_checker on S4.cost_categories]: Cost_categories includes "Teacher retention and relocation incentive schemes for marginalized regions" — a wage/incentive-based intervention — while the scenario's own assumptions state "The teacher shortage cannot be mi

## round 03 — resolved from previous round
- RESOLVED [assumption_checker on S1.assumptions] (field changed)
- RESOLVED [assumption_checker on S2.assumptions] (field changed)
- RESOLVED [assumption_checker on S3.evidence_status] (field changed)
- RESOLVED [assumption_checker on S4.expected_benefits] (field changed)
- RESOLVED [coherence_checker on S1.assumptions] (field changed)
- RESOLVED [coherence_checker on S2.evidence_status] (field changed)
- RESOLVED [cost_checker on S1.cost_categories] (field changed)
- RESOLVED [cost_checker on S2.cost_categories] (field changed)
- RESOLVED [cost_checker on S3.cost_categories] (field changed)
- RESOLVED [cost_checker on S4.cost_categories] (field changed)
- RESOLVED [devil_advocate on S1.mechanism] (field changed)
- RESOLVED [devil_advocate on S2.assumptions] (field changed)
- RESOLVED [devil_advocate on S3.evidence_status] (field changed)
- RESOLVED [equity_checker on S1.equity_impact] (field changed)
- RESOLVED [equity_checker on S2.equity_impact] (field changed)
- RESOLVED [equity_checker on S3.equity_impact] (field changed)
- RESOLVED [equity_checker on S4.equity_impact] (field changed)
- RESOLVED [evidence_checker on S3.evidence_status] (field changed)
- RESOLVED [evidence_checker on S3.mechanism] (field changed)
- RESOLVED [evidence_checker on S2.mechanism] (field changed)
- RESOLVED [feasibility_checker on S1.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S2.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S3.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S4.cost_categories] (field changed)
- RESOLVED [political_risk_checker on S1.political_risks] (field changed)
- RESOLVED [political_risk_checker on S2.political_risks] (field changed)
- RESOLVED [political_risk_checker on S3.political_risks] (field changed)
- RESOLVED [political_risk_checker on S4.political_risks] (field changed)
