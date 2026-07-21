TASK: synthesis
AGENT: school_network_planning
LANG: en


Apply one reusable scientific lens to every unchanged transformation proposal. The proposal is the object of evaluation; do not simulate a person or attribute authority to a speaker. Work in English only.

LENS: School network planning
DISCIPLINE: education infrastructure planning
QUESTIONS: Can the school network deliver the proposal geographically?; What access, transport, and capacity constraints arise?
CRITERIA: geographic access; capacity; transport; network resilience
LIMITATIONS: Network feasibility does not by itself establish educational quality.


LENS EVIDENCE:
- F-live-school_network_planning-01 [strong]: The number of children identified with special educational needs (SNI) in Hungary exceeded 69,000 in the 2025/2026 school year according to KSH (Central Statistical Office) data, with a broader count across all education levels reaching nearly 120,000.
- F-live-school_network_planning-02 [strong]: Over the past 20 years, the number of SNI students in Hungary has increased by 40%, with autism spectrum disorder (ASD) identification rising from 30 registered students in 2001 to 9,737 by 2023—a threefold increase over the past decade.
- F-live-school_network_planning-03 [strong]: Recorded SEN prevalence varies dramatically by county, ranging from 15.6% of students in Békés county to 6.2% in Borsod-Abaúj-Zemplén county.
- F-live-school_network_planning-04 [contested]: The January 2020 tightening of school-readiness assessment and deferral rules resulted in deferral applications falling sharply to 16,400 by 2021, and KSH time-series data show SNI numbers rising markedly faster from 2021/2022 onward.
- F-live-school_network_planning-05 [strong]: Northeast Hungary had no special-education-teacher (gyógypedagógus) training program until 2017, and a 2009 early-intervention study documented substantial regional inequalities in diagnostic and service access, with particularly weak services and long waiting lists in Northern Hungary regions.
- F-live-school_network_planning-06 [strong]: Currently 4,900 special-education/conductor-role teachers work in general schools, plus 949 developmental teachers and 1,404 specialists in the traveling special-education-teacher and conductor network (approximately 7,253 total specialist positions nationally).
- F-live-school_network_planning-07 [strong]: SNI-status children and up to two accompanying persons are entitled to free intercity travel to educational institutions, but travel-support entitlements are contingent on receiving a voucher issued by an Expert Committee following successful SEN assessment.
- F-live-school_network_planning-08 [strong]: Traveling specialist-education networks show wide variance in coverage scale and capacity, ranging from networks serving 30+ institutions with 200+ children to regional networks serving 50+ institutions with 350+ children, with some networks unable to provide category-specific specialist care (e.g., sensory disabilities) locally.
- F-live-school_network_planning-09 [strong]: Children from multiply disadvantaged families are significantly more likely to have developmental problems remain unidentified or, if identified, to not receive development services; additionally, official SEN figures cover only children with formal expert opinions, implying an unquantified population of children with unmet SEN who lack formal diagnosis or assessment.
- F-live-school_network_planning-10 [moderate]: Hungary exhibits extreme school segregation in small settlements, with disadvantaged-pupil concentration ranging from 20% to 80% within the same locality, shaped by covert admissions practices, church-school choice, and parental mobility responses to changing school composition.

PROPOSALS:
TP-live-t1 — Passive baseline: no new SEN policy, observe demographic and system drift
Goal: Establish a rigorous counterfactual describing what happens to identification rates, capacity strain, and inequality if no policy changes are made to identification, gatekeeping, finance, or placement rules
Mechanisms: Continued interaction of demographic decline (shrinking cohorts) with static gatekeeping capacity and workforce numbers, as documented in the record; Persistence of existing finance architecture (per-pupil multipliers, task-based financing) and category definitions absent reform, continuing current incentive structures unchanged
Risks: Unresolved ECtHR and EU infringement obligations remain outstanding, risking further legal and financial exposure (F-live-legal_and_governance-09, F-live-political_feasibility-06, F-live-political_feasibility-09); Demographic decline combined with static specialist numbers could produce further regional service collapse, particularly in northeastern counties (F-live-demography-01, F-live-school_network_planning-05)
Evidence: strong

TP-live-t2 — Build a reconciled national SEN measurement and monitoring architecture
Goal: Establish a single, harmonized, publicly auditable statistical series and monitoring framework that disentangles prevalence change from diagnostic-practice, access, and incentive effects across SNI, BTMN, and adjacent categories
Mechanisms: Reconciliation of divergent existing series (e.g., 92,800→97,300 vs. 112,060 vs. 69,000 figures using different bases) into one definitionally consistent longitudinal dataset, as the current fragmentation is documented across multiple independent findings; Decomposition analysis separating the contribution of school-readiness rule changes, category redefinition (e.g., BTMN grading-exemption reform), and diagnostic-practice shifts from true prevalence change, using natural policy variation such as the 2018 and 2020 rule changes as identification points
Risks: Without political commitment to act on findings, reconciled data alone may not change outcomes; Data reconciliation could reveal politically inconvenient patterns (e.g., incentive-driven over-identification) that face resistance to publication
Evidence: strong

TP-live-t3 — Transition toward a non-categorical, tiered support model with restructured gatekeeping
Goal: Redesign the SNI/BTMN category architecture and expert-committee gatekeeping process to reduce waiting-list bottlenecks, definitional volatility, and diagnosis-dependent access to support, informed by transferability-tested comparative models
Mechanisms: Adoption of a tiered support structure decoupling access to support from formal categorical labeling, modeled on international evidence that non-categorical or tiered frameworks materially change measured identification rates (e.g., Wales' ALN transition and Finland's three-tier model); Restructuring or augmenting the sole nationwide expert-committee gatekeeper to address documented multi-month waiting lists, informed by evidence that gatekeeping structure itself shapes measured prevalence independent of true need
Risks: Comparative evidence shows non-categorical/tiered reforms produce large persistent regional variation even after redesign (Finland's 4%–13% municipal range), so redesign alone may not resolve Hungary's county-level disparities; Poland's experience shows rapid, non-consensual structural reform can produce severe implementation disruption and stakeholder backlash
Evidence: moderate

TP-live-t4 — Shift SEN finance architecture from diagnosis-gated to needs/census-based allocation
Goal: Reduce identification-linked fiscal incentives by redesigning per-pupil funding multipliers and normative financing so that support resources are not contingent on formal diagnostic classification
Mechanisms: Replacement or supplementation of diagnosis-triggered per-pupil multipliers with census-based or population-level allocation formulas, following the evidenced pattern that census-based systems remove fiscal incentives to over-identify while non-census systems correlate with rising identification; Introduction of stricter accountability requirements tying supplementary SNI grants to documented local service delivery rather than headcount alone, addressing the finding that weak conditionality currently limits the grants' effectiveness
Risks: No causal evidence currently links Hungary's specific financing mechanism to the documented identification rise, so the intervention rests on a plausible but untested incentive theory; Poland's contrasting experience shows disability-weighted per-pupil funding was expanded rather than removed, with subventions rising independent of prevalence, suggesting funding redesign choices are not universally convergent
Evidence: moderate

TP-live-t5 — National specialist workforce and support-capacity expansion program
Goal: Close the gap between rising numbers of identified and assessed children and the specialist workforce and support infrastructure available to serve them, with priority targeting of underserved regions
Mechanisms: Regionally targeted recruitment and retention incentives for gyógypedagógus positions in underserved areas (e.g., northeastern counties with zero specialists in some districts), addressing the documented mismatch between rising enrollment and practicing workforce supply; Investment in co-teaching and traveling specialist-network infrastructure modeled on evidenced capacity gaps, alongside monitoring of whether assessed children actually receive legally prescribed habilitation and therapy hours
Risks: Rising enrollment in special-education training does not guarantee proportional increase in practicing workforce, given documented low completion/entry rates; Broader teacher salary reforms may not specifically address specialist shortages if not targeted, since no source quantifies whether general raises reach specialist supply
Evidence: strong

TP-live-t6 — Coordinated anti-segregation and adjacent-policy alignment package
Goal: Address how SEN/BTMN identification interacts with free school choice, institutional selectivity, and adjacent non-SEN policies (school-readiness rules, rural network structure, private/church growth) to reshape school composition and deepen inequality, while meeting outstanding legal obligations
Mechanisms: Extension of anti-segregation safeguards to cover free school choice and selective gimnázium tracks, directly responding to documented evidence that these channels remain structurally unaddressed and that school-switching behavior independently alters school ethnic composition; Establishment of a cross-domain coordination mechanism reviewing how school-readiness/entry-age rules, rural school-network consolidation decisions, and private/church school growth interact with SEN identification and segregation, using documented precedent that the 2020 readiness rule change measurably affected SNI growth as a model for anticipatory impact assessment
Risks: Historical precedent (Bridge classes, unresolved ECtHR compliance since 2013/2023) suggests strong institutional resistance to structural anti-segregation reform; Private/church school growth driven by middle-class exit from public schools may continue independent of policy coordination, as documented trust-erosion dynamics are not easily reversed by administrative review alone
Evidence: strong

Return exactly one assessment per proposal. Cite only supplied finding ids. Preserve contested evidence as contested in the prose. Separate strengths, weaknesses, opportunities, and threats. The verdict must follow from this lens only; it is not an overall recommendation.
