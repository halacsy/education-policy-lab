TASK: synthesis
AGENT: hungarian_education_system
LANG: en


Apply one reusable scientific lens to every unchanged transformation proposal. The proposal is the object of evaluation; do not simulate a person or attribute authority to a speaker. Work in English only.

LENS: Hungarian education system
DISCIPLINE: education system analysis
QUESTIONS: How does the proposal interact with current Hungarian institutions?; Which existing selection, access, or governance mechanisms remain unchanged?
CRITERIA: institutional fit; system coverage; unintended sorting; administrative compatibility
LIMITATIONS: Institutional description does not establish causal impact.


LENS EVIDENCE:
- F-live-hungarian_education_system-01 [strong]: The number of children identified as SNI (special educational needs) in Hungary grew from 92,800 to 97,300 in a single year (2021/2022), representing the largest year-on-year increase in at least 12 years, and the 2023/2024 figure reached approximately 63,000 or 8.8% of primary-school pupils, with a 40% rise over the preceding 20 years.
- F-live-hungarian_education_system-02 [strong]: Composition of SNI growth is uneven: severe learning disorders increased 12% in 2021/2022 alone (45,300 children); boys are classified SNI at 11% versus girls at 6.1%; and county-level variation ranges from 5.4% to 14%, a 2.6-fold spread far larger than plausible true prevalence differences.
- F-live-hungarian_education_system-03 [strong]: BTMN (integration, learning, behavioral difficulty) is a distinct Hungarian legal category defined in Act CXC of 2011, legally milder than SNI, with 2.1% prevalence among preschool children (2018/2019) but 9.5% among school-age children—a nearly five-fold jump attributed by sources to either genuine emergence of difficulties at school entry or differential screening sensitivity between settings.
- F-live-hungarian_education_system-04 [strong]: The expert committee system (pedagógiai szakszolgálat) operates as a sole nationwide gatekeeper for both SNI determination and BTMN designation, with authority to recommend integrated versus segregated placement, but this gatekeeping structure has not been restructured despite rising caseloads and documented waiting lists of several months for diagnostic assessment.
- F-live-hungarian_education_system-05 [moderate]: A shortage of special-education teachers (gyógypedagógus) exists with the largest concentration of unfilled positions in Budapest (45 advertised positions) and unequal regional distribution, while applications to the state-subsidized special-education degree program rose 15% from 2025 to 2026 cohorts (from 3,270 to 3,768 first-choice applicants).
- F-live-hungarian_education_system-06 [moderate]: The December 2023 anti-segregation law does not address free parental school choice under the voucher-financing model (Act Nkt.) or the selective six- and eight-grade gimnázium tracks, which critics argue remain the structural channels through which segregation strategies operate independent of SEN identification policy.
- F-live-hungarian_education_system-07 [strong]: European Court of Human Rights rulings in Horváth and Kiss v. Hungary (2013) and Szolcsán v. Hungary (ongoing) found discrimination in segregation of Roma children and called for safeguards against misclassification; an ongoing EU Commission infringement procedure addresses systemic segregation, yet Hungary has not provided requested data on whether new diagnostic procedures have reduced misclassification of Roma students.
- F-live-hungarian_education_system-08 [moderate]: A tightening of school-readiness rules from January 2020, which restricted school-start deferral and required six-year-olds to enter school rather than remain in kindergarten, is cited in sources as one plausible non-exclusive explanation for part of the observed SNI growth, implying that policy changes in adjacent domains (school-entry age) can measurably affect SEN identification without intent to change SEN policy itself.
- F-live-hungarian_education_system-09 [weak]: NGO advocacy sources estimate that two-thirds of Roma children in Hungary are taught separately in segregated schools, classes, or special institutions, and that a large proportion of Roma children are misclassified as mildly intellectually disabled, making this a major mechanism of educational segregation, yet these figures are unaudited advocacy estimates rather than official statistics.

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
