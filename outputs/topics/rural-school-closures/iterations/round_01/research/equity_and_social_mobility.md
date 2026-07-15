I attempted the research phase but must report a **tooling constraint honestly**: the `web_search` tool returned "Server tool use limit exceeded" on every one of my attempts this round (tried 6 times, including with delays, single queries, and batches) — it appears the search budget was already exhausted before my turn. I was not able to retrieve any fresh, verifiable web sources this round.

Per my domain's evidence-discipline rules ("never invent statistics or citations; if you do not know, say so"), I did not fabricate numbers, years, or URLs to fill this gap. Instead, I produced prose research notes drawing only on well-established prior domain knowledge, each explicitly flagged with a confidence level and marked as **unverified against fresh sources**. These have been saved to `expert_outputs/equity_and_social_mobility_research_notes.md`.

Summary of the 8 notes logged (all flagged moderate-or-weaker confidence, none carrying a fabricated citation):

1. Hungary's PISA/OECD record as one of the most SES-segregated school systems in the OECD (pattern known, no specific cycle/year cited).
2. EU infringement procedure against Hungary over Roma school segregation (Racial Equality Directive) — general fact, current status unverified.
3. Church/foundation takeover of former state village schools since ~2011, and Hungarian segregation-research literature (Kertesi/Kézdi) flagging possible compositional effects — general trend only, no effect size.
4. The methodological confound between selection (who remains in a depopulating village) and true value-added of small rural schools.
5. Peer-effects theory applied (not measured) to post-consolidation pupil composition.
6. Travel-burden inequity mechanism (lower-SES families less able to provide private transport) — general mechanism, no Hungary figures.
7. School-closure → depopulation feedback loop (general rural-sociology mechanism, not Hungary-verified).
8. Tanoda/NGO compensatory programs for disadvantaged pupils as a possible complementary model — existence known, scale/effectiveness data missing.

**Recommendation:** the web_search tool should be retried in a subsequent round (once the server-side budget resets) before I convert these into the final structured/graded JSON findings, so that each claim can be upgraded from "prior knowledge, unverified" to a properly sourced, honestly-graded evidence tag. I did not proceed to write the final structured JSON output this round, since doing so without any fresh source would force either unsupported "strong/moderate" tags or an unhelpfully all-"weak" registry — the task instructions specify the research phase (prose notes) as this round's deliverable, with structuring reserved for a later call.