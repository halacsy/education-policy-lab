TASK: synthesis
AGENT: political_feasibility
LANG: en


Apply one reusable scientific lens to every unchanged transformation proposal. The proposal is the object of evaluation; do not simulate a person or attribute authority to a speaker. Work in English only.

LENS: Political feasibility
DISCIPLINE: political economy of reform
QUESTIONS: Which coalitions can enact and sustain the proposal?; How exposed is it to reversal or strategic resistance?
CRITERIA: coalition support; opposition intensity; reversal risk; public legitimacy
LIMITATIONS: Political forecasts are time-sensitive and intrinsically uncertain.


LENS EVIDENCE:
- F-live-political_feasibility-01 [strong]: Between 2010 and 2020, the proportion of students identified with special educational needs in Hungarian primary education rose from 6.7% to 7.7%, and in secondary education from 3.9% to 6.2%.
- F-live-political_feasibility-02 [moderate]: 83.6% of a sample of 121 Hungarian primary school teachers reported an increase in students requiring developmental support, as of 2023.
- F-live-political_feasibility-03 [strong]: Diagnosis of special educational needs in Hungary is legally gatekept by expert committees (szakértői bizottságok) operating at county or district level, and parental consent is required to initiate investigation in all cases.
- F-live-political_feasibility-04 [strong]: Since 2012–13, the state centralized diagnostic and support infrastructure from municipalities to regional pedagogical assistance services, removing local authority control over assessment networks.
- F-live-political_feasibility-05 [moderate]: More than 60% of participating Hungarian schools reported needing additional special education teachers, psychologists, or pedagogical assistants; the number of such specialist staff doubled from 2010 to approximately 2023, but geographic distribution remains uneven, with one county reporting an average of 39.6 students per special education teacher.
- F-live-political_feasibility-06 [strong]: The European Court of Human Rights issued a judgment against Hungary in March 2023 for racial segregation of Romani children in education, finding violation of right to education and non-discrimination; Hungary was ordered to desegregate and pay damages. As of 2024, the Committee of Ministers monitoring implementation reports the case remains open due to insufficient Hungarian government compliance.
- F-live-political_feasibility-07 [strong]: In July 2023, the Hungarian government enacted a unified legal status law for teachers across all provider types (state, church, private, foundation schools) without adequate union consultation, restricting strike rights and granting employers unilateral authority to reassign educators to different schools to address teacher shortages.
- F-live-political_feasibility-08 [moderate]: Hungarian schools have discretion to admit students from outside their catchment area, creating asymmetric ability to include or exclude depending on institutional incentive; this mechanism has been exercised to exclude Roma students seeking transfer to non-segregated schools.
- F-live-political_feasibility-09 [moderate]: The European Commission opened an infringement procedure against Hungary in 2016 for segregation of Romani children in schools, naming segregated church schools as a contributing factor. As of 2024, this procedure remains formally open with no public resolution announced.
- F-live-political_feasibility-10 [moderate]: The EU suspended €32 billion in funding to Hungary but released €10.2 billion in cohesion funds in December 2023 following judicial reforms. Multiple observers criticized the release decision as politically transactional, coinciding with Budapest's withdrawal of a veto on Ukraine aid, and the Commission has not deployed sector-specific SEN/education conditionality despite the open infringement procedure.

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
