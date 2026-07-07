# Critique: assumption_checker

## S4.assumptions
Objection: The assumption "compensation can meaningfully offset, not just mask, the effects of early sorting" directly contradicts S4's own uncertainties field, which states "no country has demonstrated it at Hungary's selection age" — i.e., the scenario assumes as a working premise the very claim it elsewhere labels unconfirmed and low-confidence. The Portuguese evidence cited in mechanism/expected_benefits supports compensation working *without* early selection at Hungary's age; it does not support the offset claim at Hungary's much earlier selection point. The assumption should be downgraded to a stated open question, not an operating assumption the mechanism depends on.
Severity: high
Suggested revision: Rewrite the assumption as "It is unknown whether compensation can offset selection at age 10-12; Portugal's evidence applies to a later selection age" and flag expected_benefits accordingly (weak, not moderate, for the offset-specific claim).

## S3.assumptions
Objection: The assumption "sorting does not simply migrate to school choice between general schools and to non-state maintainers" is asserted with no supporting evidence tag, yet S3's own equity_impact field calls exactly this migration "the largest risk" and the synthesis's minority position (political_feasibility, hungarian_education_system) cites "growth of non-state maintainers" as active evidence this is already happening. The scenario cannot simultaneously assume away the risk in assumptions and treat it as a live, evidenced threat in equity_impact.
Severity: high
Suggested revision: Remove this as a background assumption; move it to uncertainties with the migration risk quantified from existing non-state enrolment trends, and revise equity_impact/expected_benefits to be conditional on this uncertainty.

## S1.assumptions
Objection: "A workable SES indicator exists at application time" is asserted as a plain assumption with no evidence tag and no source — unlike other assumptions across the scenario set, this one is neither flagged as uncertain nor supported by the "moderate" evidence status claimed for admission-rule effects abroad. Foreign SES-indicator systems (e.g., free/reduced lunch proxies, postcode indices) are not shown to be transferable to the Hungarian administrative context, and the whole mechanism (weighted lottery / district quotas) is unworkable without this indicator existing and being non-gameable.
Severity: high
Suggested revision: Either cite a concrete candidate Hungarian SES proxy (e.g., existing HHH/HH status categories) with evidence, or move this to uncertainties with an explicit confidence rating and a research step to test candidate indicators before piloting.

## S2.assumptions
Objection: "General schools can absorb and challenge high-achievers if funded for it" is treated as an assumption underpinning the mechanism, but evidence_status explicitly calls this "the unevidenced link," and expected_benefits nonetheless claims "stronger peer composition" at moderate evidence — the moderate rating applies to peer-composition effects generally, not to whether funded general-school programmes specifically retain high-achieving families, which uncertainties rates as low-confidence. The expected_benefits tag is therefore inconsistent with the assumption's actual evidentiary support.
Severity: medium
Suggested revision: Split expected_benefits into the mechanically certain (falling early-sorting share, strong evidence) and the retention-dependent claim (peer composition), re-tagging the latter as weak/contested until the tracked cohort study referenced in uncertainties exists.