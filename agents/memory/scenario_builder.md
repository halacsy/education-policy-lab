# Episodic memory: scenario_builder

Deterministic distillation from previous rounds (lab/memory.py); fed back into this agent's prompt. Unresolved items persist until the criticized field changes; resolved items drop.


## round 08 — received
- received [devil_advocate on S0.goal]: The core claim that S0 “avoids indefinite deferral” is unsupported. The scenario itself labels the statutory deadline mechanism as weak and admits no Hungarian education-policy precedent shows such a deadline would bind 
- received [devil_advocate on S1.mechanism]: The scenario’s load-bearing mechanism depends on a “gaming-resistant SES proxy,” but the evidence record does not support its feasibility. The scenario admits Hungary lacks a student-level SES register and that verified 
- received [devil_advocate on S2.expected_benefits]: The claimed benefit of lowering early-sorting exposure is unsupported at the national level because the scenario’s own assumptions say non-state maintainers may offset state-place reductions. The cited school_network_pla
- received [devil_advocate on S4.mechanism]: The Portugal analogy is too weak to carry S4. The cited OECD/Crato evidence supports Portugal’s bundled system-level PISA gains, but it does not support offsetting Hungary’s age-10/12 selection-driven SES gradient while 
- received [evidence_checker on S0.mechanism]: The first mechanism cites `legal_and_governance` for an audit using admission and PISA microdata, but `legal_and_governance` is not in the curated source registry. The registry supports `legal` only for statutory anchori
- received [evidence_checker on S1.mechanism]: The first mechanism is tagged `strong` for the claim that SES-weighted admissions or quotas could shift entrant composition. The registry’s `gimn_share [strong]` supports only the existence and scale of early gimnazium e
- received [evidence_checker on S2.evidence_status]: The scenario says non-state maintainers “can and likely will expand” selective places, and uses that to downgrade the central equity claim. The registry’s `governance [strong]` supports maintainer fragmentation, and `sch
- received [evidence_checker on S3.expected_benefits]: The claim that abolition “removes the specific legal exposure created by age 10-12 differentiation under Article 66/a and EU equal-treatment scrutiny” cites Hungarian Constitutional Court and EU frameworks, but no such s
- received [assumption_checker on S0.assumptions]: The scenario assumes an “independent body (e.g., Oktatási Hivatal or an external commission)” can credibly conduct the audit, but Oktatási Hivatal is not independent of the state education governance structure whose poli
- received [assumption_checker on S1.expected_benefits]: The claim that admission reform “operates within the existing legal framework for admissions rather than requiring Nkt. amendment” is too strong. The scenario’s own assumptions and political_risks state that no current l
- received [assumption_checker on S2.mechanism]: The mechanism claims a legislated year-on-year reduction in state-maintained places can lower cohort exposure to early sorting, but the scenario simultaneously concedes that non-state maintainers may absorb displaced dem
- received [assumption_checker on S4.assumptions]: The assumption that non-structural interventions are politically easier to implement and sustain than structural tracking reform is unsupported. The expert record supports that structural reform faces organized parent an
- received [equity_checker on S0.equity_impact]: The field correctly says the audit creates no equity change, but it understates the equity-negative effect of delaying action despite strong diagnostic evidence already available. The evidence base strongly supports that
- received [equity_checker on S1.equity_impact]: The field focuses on middle-SES/rural applicants who may lose out, but it does not adequately assess the largest excluded group: lower-SES pupils who never apply to selective tracks because of information, travel, tutori
- received [equity_checker on S2.equity_impact]: The field identifies non-state offsetting and residual-place competition, but it misses a direct equity-negative pathway for displaced lower- and middle-SES high achievers: as state selective places shrink, high-SES fami
- received [equity_checker on S4.equity_impact]: The field says S4 may be equity-neutral-to-negative if it entrenches selection and funding is non-durable, but it underplays who is actually reached by the compensatory package. TEIP-style funding reaches disadvantaged g
- received [feasibility_checker on S1.implementation_steps]: The year 1-2 build-and-validate step for a provisional SES proxy is not feasible as written because the scenario itself says Hungary lacks a student-level SES register and may need welfare/tax/residency linkage. That is 
- received [feasibility_checker on S2.implementation_steps]: The scenario depends on regulatory levers over non-state maintainers by year 1-2, but the record cited in the scenario says those levers do not currently exist and their legal feasibility is untested. That makes the phas
- received [feasibility_checker on S3.implementation_steps]: The teacher retraining timeline is infeasible relative to the scenario's own evidence. It says full national coverage in 4 years is unlikely, yet still lists year 1-4 as the national retraining window while simultaneousl
- received [feasibility_checker on S4.implementation_steps]: The national rollout of grade-retention reduction and diagnostic support in years 2-5 is administratively underpowered. The scenario acknowledges Hungary's teacher shortage will blunt delivery and that shortage-affected 
- received [cost_checker on S0.cost_categories]: The audit cost is materially under-specified: the scenario names “audit design and fieldwork” but omits legal/data-access costs for KSH/Oktatási Hivatal/PISA microdata linkage, privacy compliance, maintainer data acquisi
- received [cost_checker on S1.cost_categories]: The scenario correctly distinguishes verified self-report from administrative linkage, but it still fails to price the largest fiscal sensitivity: whether the SES proxy becomes a pilot-only workaround or a reusable natio
- received [cost_checker on S2.cost_categories]: The cost categories mix transition and steady-state costs in a way that obscures the fiscal case. “Compensatory funding or capacity expansion” is labeled high and recurring across the phase-down period, but the scenario 
- received [cost_checker on S3.cost_categories]: Teacher retraining is categorized as “high, recurring,” but retraining specialized gimnazium teachers for heterogeneous classrooms is primarily a transition cost, while ongoing costs would come from staffing ratios, ment
- received [political_risk_checker on S0.political_risks]: The field names the risk that parties may prefer indefinite deferral, but it does not specify any entrenchment mechanism beyond the same statutory deadline whose enforceability the scenario itself rates as weak and unsup
- received [political_risk_checker on S1.political_risks]: The opposition risk is understated because the scenario treats high-SES parent mobilization as a general resistance risk rather than as a direct threat to pilot validity. If organized families opt out, litigate, or conce
- received [political_risk_checker on S3.political_risks]: The reversal-risk discussion correctly invokes Poland but leaves the entrenchment design almost empty. A “multi-party pact” is named, while the same field admits there is no constitutional or supermajority lock. Given th
- received [political_risk_checker on S4.political_risks]: The field identifies funding cuts as a risk but does not confront the larger political-risk mechanism: S4 may create a durable coalition for preserving early selection by buying off criticism with compensatory funding. T
- received [coherence_checker on S1.expected_benefits]: The claim that S1 “operates within the existing legal framework for admissions rather than requiring Nkt. amendment” contradicts S1.assumptions and S1.political_risks, which say no current legal mechanism compels non-sta
- received [coherence_checker on S2.mechanism]: The mechanism says a phase-down can proceed “via place-count regulation without full statutory repeal,” but the same bullet concedes the forms are legally anchored and that changes require legislative action. This create
- received [coherence_checker on S3.expected_benefits]: The claim that abolition “removes the specific legal exposure created by age 10-12 differentiation under Article 66/a and EU equal-treatment scrutiny” is stronger than the evidence supports. The scenario elsewhere treats
- received [coherence_checker on S4.goal]: S4’s goal promises “narrowing outcome gaps between selected and non-selected pupils,” but the mechanism and evidence_status only support Portugal-style system-level gains and targeted support for disadvantaged general sc
- received [context_transferability_checker on S0.expected_benefits]: The claim that an audit deadline could build buy-in and reduce “reversal risk of the kind seen in Poland” over-generalizes the Polish case. The registry’s Poland transferability note says Poland’s gains were not durably 
- received [context_transferability_checker on S3.evidence_status]: The field correctly notes that Finnish/Polish evidence is conditional, but it still frames the missing bundle mainly as “teacher-training and choice/catchment reforms.” For the Polish source, the registry’s transferabili
- received [context_transferability_checker on S4.expected_benefits]: The claim that Portugal shows “system-level PISA gains achievable without the political and legal disruption of structural reform” is too transferable as written. The registry’s Portugal note says Portugal did not have H
- received [context_transferability_checker on S4.assumptions]: The assumption that Portuguese TEIP and curriculum mechanisms are transferable despite “differing selection structures and teacher-supply conditions” names the issue but does not specify the registry’s operative precondi

## round 08 — resolved from previous round
- RESOLVED [assumption_checker on S1.assumptions] (field changed)
- RESOLVED [assumption_checker on S2.goal] (field changed)
- RESOLVED [assumption_checker on S3.mechanism] (field changed)
- RESOLVED [assumption_checker on S4.expected_benefits] (field changed)
- RESOLVED [coherence_checker on S2.goal] (field changed)
- RESOLVED [coherence_checker on S3.assumptions] (field changed)
- RESOLVED [coherence_checker on S4.goal] (field changed)
- RESOLVED [coherence_checker on S1.implementation_steps] (field changed)
- RESOLVED [cost_checker on S1.cost_categories] (field changed)
- RESOLVED [cost_checker on S2.cost_categories] (field changed)
- RESOLVED [cost_checker on S3.cost_categories] (field changed)
- RESOLVED [cost_checker on S4.cost_categories] (field changed)
- RESOLVED [devil_advocate on S3.goal] (field changed)
- RESOLVED [devil_advocate on S2.expected_benefits] (field changed)
- RESOLVED [devil_advocate on S4.goal] (field changed)
- RESOLVED [devil_advocate on S1.mechanism] (field changed)
- RESOLVED [equity_checker on S2.equity_impact] (field changed)
- RESOLVED [equity_checker on S3.equity_impact] (field changed)
- RESOLVED [equity_checker on S4.equity_impact] (field changed)
- RESOLVED [equity_checker on S1.equity_impact] (field changed)
- RESOLVED [evidence_checker on S1.goal] (field changed)
- RESOLVED [evidence_checker on S2.mechanism] (field changed)
- RESOLVED [evidence_checker on S3.political_risks] (field changed)
- RESOLVED [evidence_checker on S4.uncertainties] (field changed)
- RESOLVED [feasibility_checker on S1.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S1.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S3.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S4.implementation_steps] (field changed)
- RESOLVED [political_risk_checker on S1.political_risks] (field changed)
- RESOLVED [political_risk_checker on S2.implementation_steps] (field changed)
- RESOLVED [political_risk_checker on S3.political_risks] (field changed)
- RESOLVED [political_risk_checker on S4.political_risks] (field changed)
