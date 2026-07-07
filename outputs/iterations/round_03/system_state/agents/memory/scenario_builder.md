# Episodic memory: scenario_builder

Deterministic distillation from previous rounds (lab/memory.py); fed back into this agent's prompt. Unresolved items persist until the criticized field changes; resolved items drop.


## round 02 — received
- received [devil_advocate on S1.mechanism]: The "moderate" evidence tag misrepresents its sources. Kertesi & Kezdi 2013 and the Berényi–Berkovits–Erőss school-choice studies document *that* sorting occurs and *how* parental choice drives it; neither evaluates a qu
- received [devil_advocate on S2.assumptions]: The assumption "non-state school maintainers can be restricted from absorbing the phased-out selective capacity" is directly contradicted by the synthesis's own hungarian_education_system disagreement note, which states 
- received [devil_advocate on S3.evidence_status]: Tagging overall evidence_status "strong" conflates two different claims. The strong/moderate citations (Hanushek & Woessmann 2006, Pekkarinen et al. 2009, Jakubowski et al. 2016) support the general cross-national findin
- received [evidence_checker on S3.evidence_status]: The overall evidence_status is tagged "strong," but this aggregates three registry entries of different strength: tracking_inequality [strong], finnish_comprehensive [moderate], and poland_reform [moderate]. Two of the t
- received [evidence_checker on S3.mechanism]: The claim "Phasing out selective tracks prevents demographic shrinkage from accelerating the collapse of rural primary school networks" is tagged [evidence: moderate — KSH demographic yearbooks; model knowledge]. The reg
- received [evidence_checker on S2.mechanism]: "Gradually reducing enrollment caps... reduces between-school sorting" cites [evidence: moderate — OECD PISA country notes; Kertesi & Kezdi 2013]. The OECD PISA country notes registry entry (pisa_escs, graded strong) doc
- received [assumption_checker on S1.assumptions]: The assumption "Elite gimnaziums will not bypass reformed admissions rules via oral exams or alternative diagnostic pathways" is directly contradicted by this same scenario's own Political risks field, which lists "Admin
- received [assumption_checker on S2.assumptions]: The assumption "Non-state school maintainers can be restricted from absorbing the phased-out selective capacity" is unsupported and conflicts with the scenario's own Equity impact statement ("depends heavily on whether m
- received [assumption_checker on S3.evidence_status]: The overall "strong" evidence_status rating is inconsistent with the scenario's own assumptions list, which flags that (a) Hungary "lacks the equivalent teacher quality and support systems that supported the Finnish tran
- received [assumption_checker on S4.expected_benefits]: The claim "Avoids the transition and friction costs of structural reorganization [evidence: weak]" mischaracterizes the scenario's own cost profile: the Cost categories field lists "recurring" TEIP-style budgets, nationa
- received [equity_checker on S1.equity_impact]: The claim of "moderately improves equity within selective tracks" rests on evidence tags (Kertesi & Kezdi 2013; Berényi-Berkovits-Erőss) that document existing sorting patterns, not the causal efficacy of admissions-quot
- received [equity_checker on S2.equity_impact]: "Significantly improves equity in the long run" is a stronger claim than the evidence_status ("moderate") or the scenario's own mechanism support (evidence: moderate — OECD PISA notes; Kertesi & Kezdi 2013) justifies, an
- received [equity_checker on S3.equity_impact]: The claim to "maximize educational equity" conflates SES-gradient reduction (well supported by Hanushek & Woessmann and Pekkarinen et al., which measure general socio-economic variance in achievement) with Roma-specific 
- received [equity_checker on S4.equity_impact]: The statement "excluding disadvantaged pupils in non-targeted schools" correctly flags a gap but understates its scale: TEIP-style targeting in Portugal operated on school-level designation, and Hungary's disadvantaged p
- received [feasibility_checker on S1.implementation_steps]: The steps rely on a "ministerial decree governing secondary admissions" enforced via Tankerületek audits, but Tankerületek only have jurisdiction over state schools. The equity_impact section itself states the reform "ru
- received [feasibility_checker on S2.implementation_steps]: "Klebelsberg Centre — Oversee the transitional staffing plans as secondary teaching hours shift toward 4-year tracks" assumes teachers currently assigned to 6-/8-year academic tracks can be redeployed into 4-year gimnazi
- received [feasibility_checker on S3.implementation_steps]: "Ministry of Education — Launch a nationwide teacher retraining program focused on differentiated instruction" is listed as a single, undated action item running in parallel with the National Assembly's "comprehensive ba
- received [feasibility_checker on S4.cost_categories]: "Teacher retention and relocation incentive schemes for marginalized regions" appears only as a cost line, with no corresponding action in implementation
- received [cost_checker on S1.cost_categories]: The cost list contains no fiscal magnitude or evidence tag at all — every item ("admissions administration," "monitoring and enforcement," "litigation") is a bare category with no order-of-magnitude estimate, while the s
- received [cost_checker on S2.cost_categories]: "Curriculum adjustments and staff reorganization within phasing-out schools" collapses what should be two distinct and large cost items — (a) one-time transition costs (retraining, contract renegotiation) and (b) a struc
- received [cost_checker on S3.cost_categories]: "Local transport adjustments" is buried as a minor sub-item under "Administrative and legal costs," but the synthesis's own agreed fact on demography ("Hungary's annual births have declined... forcing network consolidati
- received [cost_checker on S4.cost_categories]: The evidence_status paragraph explicitly identifies "Hungary's severe regional teacher shortages" as the binding constraint on transferability of the Portuguese model, yet the cost_categories list only offers a vague "te
- received [political_risk_checker on S1.political_risks]: The risk list catalogs opposition (middle-class mobilization, church-maintainer litigation, oral-exam circumvention) but omits the single most consequential reversal vector: the mechanism itself is implemented via minist
- received [political_risk_checker on S2.political_risks]: The assumptions section explicitly flags as uncertain whether "non-state school maintainers can be restricted from absorbing the phased-out selective capacity," yet the political_risks section never carries this into a r
- received [political_risk_checker on S3.political_risks]: The scenario names "High risk of a Polish-style political reversal" and the synthesis independently confirms Poland's reform was "fully reversed between 2016 and 2019" [evidence: moderate], meaning this is not a hypothet
- received [political_risk_checker on S4.political_risks]: The claim "Very low risk of middle-class backlash as elite tracks remain intact" understates opposition by only considering the demographic that benefits from tracking. TEIP-style targeted funding disproportionately rout
- received [coherence_checker on S1.assumptions]: The assumptions list asserts "Elite gimnaziums will not bypass reformed admissions rules via oral exams or alternative diagnostic pathways" and "Middle-class parents will accept admissions quotas rather than seeking to b
- received [coherence_checker on S2.evidence_status]: The mechanism claims [evidence: strong — Nkt. analysis] that a gradual phase-out satisfies constit

## round 02 — resolved from previous round
- RESOLVED [assumption_checker on S1.assumptions] (field changed)
- RESOLVED [assumption_checker on S2.equity_impact] (field changed)
- RESOLVED [assumption_checker on S3.mechanism] (field changed)
- RESOLVED [coherence_checker on S1.mechanism] (field changed)
- RESOLVED [coherence_checker on S2.assumptions] (field changed)
- RESOLVED [cost_checker on S1.cost_categories] (field changed)
- RESOLVED [cost_checker on S2.cost_categories] (field changed)
- RESOLVED [cost_checker on S3.cost_categories] (field changed)
- RESOLVED [cost_checker on S4.cost_categories] (field changed)
- RESOLVED [devil_advocate on S1.assumptions] (field changed)
- RESOLVED [devil_advocate on S1.expected_benefits] (field changed)
- RESOLVED [devil_advocate on S2.assumptions] (field changed)
- RESOLVED [devil_advocate on S2.equity_impact] (field changed)
- RESOLVED [devil_advocate on S3.mechanism] (field changed)
- RESOLVED [equity_checker on S1.equity_impact] (field changed)
- RESOLVED [equity_checker on S2.equity_impact] (field changed)
- RESOLVED [equity_checker on S3.equity_impact] (field changed)
- RESOLVED [equity_checker on S4.equity_impact] (field changed)
- RESOLVED [evidence_checker on S1.mechanism] (field changed)
- RESOLVED [evidence_checker on S2.mechanism] (field changed)
- RESOLVED [evidence_checker on S3.evidence_status] (field changed)
- RESOLVED [evidence_checker on S4.expected_benefits] (field changed)
- RESOLVED [feasibility_checker on S3.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S2.assumptions] (field changed)
- RESOLVED [feasibility_checker on S4.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S1.cost_categories] (field changed)
- RESOLVED [political_risk_checker on S1.political_risks] (field changed)
- RESOLVED [political_risk_checker on S2.political_risks] (field changed)
- RESOLVED [political_risk_checker on S3.political_risks] (field changed)
- RESOLVED [political_risk_checker on S4.political_risks] (field changed)
