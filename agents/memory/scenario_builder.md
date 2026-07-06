# Episodic memory: scenario_builder

Deterministic distillation from previous rounds (lab/memory.py); fed back into this agent's prompt. Unresolved items persist until the criticized field changes; resolved items drop.


## round 02 — received
- received [devil_advocate on S3.mechanism]: The asymmetric-peer-effect claim is the load-bearing wall of S3 and it is tagged 'contested'; if peer effects are symmetric, S3 redistributes rather than creates learning.
- received [devil_advocate on S4.goal]: S4's premise that early selection is 'politically fixed' is itself a political judgment, not evidence; treating it as fixed forecloses the option space prematurely.
- received [evidence_checker on S2.mechanism]: The claim that advanced programmes retain ambitious families in general schools cites only 'expert inference'; magnet-school analogues are US-specific and not verified for Hungary.
- received [evidence_checker on S1.expected_benefits]: 'Reduced test-preparation arms race' benefit carries a 'weak' tag but is presented in the same list as moderately evidenced items without visual distinction.
- received [assumption_checker on S3.assumptions]: The assumption 'political ownership survives two electoral cycles' contradicts the political_feasibility expert's stated position that no such window exists; the tension is unresolved in the scenario.
- received [assumption_checker on S4.assumptions]: 'Compensation can offset, not just mask' is doing all the work in S4, yet no country evidence exists at Hungary's selection age — the assumption should be flagged as unverifiable ex ante.
- received [equity_checker on S1.equity_impact]: S1 helps high-ability low-SES pupils only; the equity_impact field understates that the non-selected majority sees zero direct benefit, which conflicts with the mission's equity criterion.
- received [equity_checker on S3.equity_impact]: S3's equity_impact names middle-class exit as a risk but gives no threshold at which the reform becomes equity-negative; without it the field is not decision-ready.
- received [feasibility_checker on S3.implementation_steps]: Step 2 requires nationwide differentiation retraining in years 1-4 while the teacher shortage is worst in exactly the schools that need it; throughput capacity is asserted, not shown.
- received [feasibility_checker on S2.implementation_steps]: The felmenő rendszer guarantee in step 1 interacts with annual caps: schools with mixed cohorts face split timetables for a decade — the steps do not name who plans this.
- received [cost_checker on S3.cost_categories]: Two 'high' one-off items (retraining, network reconfiguration) lack even order-of-magnitude ranges, though the education_finance expert explicitly asked for published ranges.
- received [cost_checker on S4.cost_categories]: S4's recurring cost is the package itself, yet no fiscal sensitivity (what happens at -30% budget) is given despite budget vulnerability being S4's own top political risk.
- received [political_risk_checker on S2.political_risks]: Reversal risk is listed but not mitigated: the scenario has no design feature that raises the cost of freezing the cap trajectory for a successor government.
- received [political_risk_checker on S1.political_risks]: The maintainer-exemption risk is understated: if church schools are exempt, S1 creates an incentive to shift selective intake there, worsening the problem it targets.
- received [coherence_checker on S2.goal]: S2's goal says freed capacity is 'invested in strong programmes', but its cost_categories show political capital 'high and sustained' with no corresponding implementation step securing that capital — goal and steps are m
- received [coherence_checker on S1.mechanism]: Mechanism claim 3 (weaker test-prep incentives) presupposes lottery weight large enough to matter, but nothing elsewhere in S1 fixes the lottery weight — an internal free variable.

## round 02 — resolved from previous round
- RESOLVED [assumption_checker on S3.assumptions] (field changed)
- RESOLVED [assumption_checker on S4.assumptions] (field changed)
- RESOLVED [coherence_checker on S1.mechanism] (field changed)
- RESOLVED [coherence_checker on S2.assumptions] (field changed)
- RESOLVED [coherence_checker on S3.expected_benefits] (field changed)
- RESOLVED [coherence_checker on S4.equity_impact] (field changed)
- RESOLVED [cost_checker on S1.cost_categories] (field changed)
- RESOLVED [cost_checker on S2.cost_categories] (field changed)
- RESOLVED [cost_checker on S3.cost_categories] (field changed)
- RESOLVED [cost_checker on S4.cost_categories] (field changed)
- RESOLVED [devil_advocate on S1.expected_benefits] (field changed)
- RESOLVED [devil_advocate on S2.assumptions] (field changed)
- RESOLVED [devil_advocate on S3.expected_benefits] (field changed)
- RESOLVED [devil_advocate on S4.equity_impact] (field changed)
- RESOLVED [equity_checker on S1.equity_impact] (field changed)
- RESOLVED [equity_checker on S2.equity_impact] (field changed)
- RESOLVED [equity_checker on S3.equity_impact] (field changed)
- RESOLVED [equity_checker on S4.equity_impact] (field changed)
- RESOLVED [evidence_checker on S1.mechanism] (field changed)
- RESOLVED [evidence_checker on S1.expected_benefits] (field changed)
- RESOLVED [evidence_checker on S3.assumptions] (field changed)
- RESOLVED [feasibility_checker on S1.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S2.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S3.implementation_steps] (field changed)
- RESOLVED [feasibility_checker on S4.implementation_steps] (field changed)
- RESOLVED [political_risk_checker on S2.political_risks] (field changed)
- RESOLVED [political_risk_checker on S1.political_risks] (field changed)
