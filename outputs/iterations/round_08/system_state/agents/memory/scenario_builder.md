# Episodic memory: scenario_builder

Deterministic distillation from previous rounds (lab/memory.py); fed back into this agent's prompt. Unresolved items persist until the criticized field changes; resolved items drop.


## round 07 — received
- received [devil_advocate on S3.goal]: The claim that abolition would “align Hungary with the international evidence base on delayed tracking and equity” is overstated. The cited evidence supports an association between later tracking and lower SES gradients 
- received [devil_advocate on S2.expected_benefits]: The benefit “stronger peer composition in urban general-school upper grades” rests on the weakest causal link in the scenario. The evidence tags admit the peer-effect mechanism is contested, and the scenario’s own equity
- received [devil_advocate on S4.goal]: The phrase “neutralize its socio-economic inequities” is unsupported. The Portuguese evidence supports system-level improvement under a broad reform bundle, not neutralization of inequities caused by selection at ages 10
- received [devil_advocate on S1.mechanism]: The mechanism depends on a “less preparation-sensitive assessment,” but the cited evidence does not show that aptitude, portfolio, or lottery-among-qualified designs would resist SES advantage in Hungary. Kertesi & Kezdi
- received [evidence_checker on S1.goal]: The tag is too strong and cites the wrong registry fact. The registry’s `gimn_share [strong]` supports that roughly 8-12% of a cohort enters 6-/8-year tracks through admissions statistics; it does not itself support the 
- received [evidence_checker on S2.mechanism]: The first mechanism claim is overgraded. The registry’s `legal [strong]` supports that 6/8-year forms are anchored in law and phase-out requires legislative change, but it does not support that “year-on-year caps” are a 
- received [evidence_checker on S3.political_risks]: The teacher-union risk cites a “Round 06 discourse analysis” as strong evidence, but that source is not in the curated registry. The registry only gives `teacher_shortage [strong]`, which supports a sustained teacher sho
- received [evidence_checker on S4.uncertainties]: The confidence label is internally and evidentially wrong. The uncertainty asks whether Hungary’s teacher shortage will blunt Portuguese-style interventions, but marks confidence as high while saying it would be reduced 
- received [assumption_checker on S1.assumptions]: The scenario treats “uniform admission-equity rules across state, church and foundation maintainers” as a difficult but administratively solvable assumption, while the expert record frames maintainer plurality as a struc
- received [assumption_checker on S2.goal]: The goal claims that a gradual phase-down will “lower the share of the cohort exposed to early sorting,” but the scenario’s own assumptions and uncertainties concede that non-state maintainers may absorb displaced demand
- received [assumption_checker on S3.mechanism]: The first mechanism overstates what Hanushek & Woessmann 2006 supports. That evidence supports a general cross-national association between early tracking and stronger SES gradients; it does not establish that abolishing
- received [assumption_checker on S4.expected_benefits]: The benefit that non-structural reforms can “potentially narrow outcome gaps even without altering entry rules” relies on Portuguese PISA trends, but the evidence tag admits TEIP’s independent contribution is not isolate
- received [equity_checker on S2.equity_impact]: The field correctly identifies residual selective places becoming more SES-skewed, but it underplays who is left out: lower-SES pupils in general schools who lose access to selective seats without receiving any compensat
- received [equity_checker on S3.equity_impact]: The claim that this scenario has the "largest expected aggregate equity gain" is too strong for the evidence cited. The field itself says the largest risk is relocation of sorting into non-state, private, catchment, and 
- received [equity_checker on S4.equity_impact]: The field says equity gains are bounded by the depth and permanence of funding commitments, but that is incomplete: the scenario may be equity-negative by legitimizing and stabilizing the early selection mechanism while 
- received [equity_checker on S1.equity_impact]: The field names non-applicants as left out but does not identify the likely distributional losers among applicants: middle-SES or rural pupils without qualifying SES proxy status may face reduced access if quotas are imp
- received [feasibility_checker on S1.implementation_steps]: The timeline assumes a validated, less-coachable national assessment can be designed, piloted, psychometrically validated, legally accepted, and nationally rolled out in 4-5 years, but the scenario’s own evidence tags sa
- received [feasibility_checker on S1.implementation_steps]: The SES-weighting/quota step is administratively under-specified: the assumptions admit Hungary lacks a usable student-level SES register at application time, yet the implementation plan moves directly to legal testing a
- received [feasibility_checker on S3.implementation_steps]: The teacher-retraining plan is not feasible against the scenario’s own capacity evidence. It gives the Ministry years 1-4 to retrain for heterogeneous classrooms, while assumptions and political risks say Hungary’s teach
- received [feasibility_checker on S4.implementation_steps]: The plan assigns national rollout of grade-retention-reduction and diagnostic supports to KK in years 2-4, but the scenario’s own political_risks state that teacher shortage strongly undermines credible delivery. The Por
- received [cost_checker on S1.cost_categories]: The SES-proxy data infrastructure cost is understated as merely "medium" and lacks a range for the two materially different options: a verified self-report workflow versus an administrative data-linkage/register build. T
- received [cost_checker on S2.cost_categories]: The cost list omits a major fiscal exposure: compensatory funding or capacity controls for general schools absorbing retained high-achievers and displaced pupils during the phase-down. The scenario assumes peer-compositi
- received [cost_checker on S3.cost_categories]: The categories correctly label several items "high" but still confuse scale with budget exposure by omitting fiscal ranges and duration. "Early diagnostic and remedial support system build-out" is tagged high and recurri
- received [cost_checker on S4.cost_categories]: The TEIP-style targeted funding line is too aggregated to test fiscal sensitivity. The evidence tag says no numeric range is available, while the political-risk field says this is likely the first line cut in consolidati
- received [political_risk_checker on S1.political_risks]: The risk that non-state maintainers resist uniform equity mandates is understated as merely "weak" and framed as inferred from maintainer plurality. The synthesis says maintainer fragmentation is treated as a major compl
- received [political_risk_checker on S2.implementation_steps]: The implementation plan says the Ministry will "monitor non-state maintainer intake for offsetting expansion and adjust regulatory levers if detected," but it never names the regulatory levers. This leaves the scenario's
- received [political_risk_checker on S3.political_risks]: The reversal risk is named but not mitigated. The field correctly cites the Polish 1999-2016/19 reversal as moderate evidence, but the scenario's only entrenchment device is a vague "multi-party political pact" in implem
- received [political_risk_checker on S4.political_risks]: The budget-vulnerability risk is under-evidenced but still central enough that the scenario should not treat "politically less disruptive" as a plausible expected benefit. The cited source only supports an inference that
- received [coherence_checker on S2.goal]: The goal says the phase-down will lower the share of the cohort exposed to early sorting, but the scenario's own assumptions, equity_impact, political_risks, and uncertainties all state that church/foundation maintainers
- received [coherence_checker on S3.assumptions]: The assumption that sorting does not simply migrate to school choice or non-state maintainers is directly contradicted by S3.equity_impact, S3.political_risks, and S3.uncertainties, all of which identify migration of sor
- received [coherence_checker on S4.goal]: The goal claims the package will “neutralize” socio-economic inequities while retaining the 6/8-year system unchanged, but S4.evidence_status says offsetting Hungary’s age-10/12 selection gradient has no direct precedent
- received [coherence_checker on S1.implementation_steps]: The steps put national rollout in years 4-5, but the assumptions and uncertainties say no validated Hungarian less-coachable assessment exists and no workable gaming-resistant SES proxy exists. The timeline treats two un

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
