# Critique: evidence_checker

## S3.mechanism
Objection: The asymmetric peer-effects claim is tagged [evidence: contested], but the mechanism bullet states as fact that common-school composition "raises outcomes of disadvantaged pupils more than it lowers those of advantaged ones." A contested tag cannot support a directional magnitude claim stated declaratively. The actual literature (e.g., peer-effect meta-analyses) shows mixed and setting-dependent signs, with several studies finding roughly symmetric or even net-negative effects for high-achievers in fully de-tracked settings. The tag correctly says "contested" but the sentence asserts the favorable resolution of the very dispute it flags.
Severity: high
Suggested revision: Rephrase to reflect the contest: "Common-school composition *may* raise disadvantaged-pupil outcomes; whether gains to the disadvantaged exceed losses to advantaged pupils is disputed [evidence: contested]." Do not state the asymmetry as an established mechanism.

## S2.mechanism
Objection: The lead bullet is tagged [evidence: strong] on the basis that "annual entry-place caps... mechanically lower early sorting." The mechanical arithmetic (fewer places = fewer sorted) is indeed near-tautological, but the [evidence: strong] tag is doing double duty — a reader takes it as strong empirical support for a *policy outcome*, when it only supports an accounting identity. The genuinely load-bearing causal claim (freed capacity reinvestment retains demand in general schools) is the unevidenced link the evidence_status field itself admits. Grading the tautological half "strong" inflates the apparent evidentiary standing of the mechanism as a whole.
Severity: medium
Suggested revision: Split the tag: label the accounting effect "[evidence: strong (definitional)]" and explicitly tag the behavioural retention link "[evidence: weak/unevidenced]" within the same bullet, so the strong tag cannot be read as endorsing the policy's effectiveness.

## S4.expected_benefits
Objection: "Politically inexpensive; implementable under any government [evidence: strong]" — the [evidence: strong] tag is misapplied to a forward-looking political-feasibility prediction, which is not the kind of claim empirical evidence can grade "strong." At most the low-political-capital cost is an informed judgment; meanwhile S4's own political_risks field concedes budget lines are "the first cut in fiscal consolidation," which directly contradicts "implementable under any government." The tag overstates certainty on precisely the dimension the scenario elsewhere flags as fragile.
Severity: high
Suggested revision: Downgrade to "[evidence: moderate]" or reframe as an assumption, and reconcile with the political_risks field — e.g., "low up-front political cost, but durability across fiscal cycles is uncertain."

## S1.expected_benefits
Objection: "More balanced intake into selective tracks within 2-3 admission cycles [evidence: moderate]" attaches a moderate tag to a specific timeline (2-3 cycles) whose evidence base (admission-rule effects abroad) does not speak to Hungarian-specific speed. The evidence_status field itself notes effects are "well documented abroad" but "system-level equity are indirect" — nothing there supports the 2-3-cycle pace, which also depends on the compliance assumption the uncertainties field rates confidence "low." The magnitude/direction may be moderate; the *timeline* is not moderately evidenced.
Severity: medium
Suggested revision: Detach the timeline from the tag: "More balanced intake into selective tracks [evidence: moderate]; the 2-3-cycle pace is an estimate contingent on elite-school compliance (see uncertainties)."