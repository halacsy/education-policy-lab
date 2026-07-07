"""Canonical agent definitions. `agents.scaffold()` renders these into
`agents/<type>/<name>.md`; after scaffolding, the markdown files are the
working specs (the improvement step edits them, and they are versioned into
each round's system_state snapshot)."""

EXPERTS = {
    "hungarian_education_system": "The structure and sorting mechanisms of the Hungarian school system: school choice, catchments, maintainers, admission rules, and how the 6/8-year gimnázium tracks interact with them.",
    "international_comparison": "Cross-country evidence on selection age, tracking and equity (PISA gradients, difference-in-differences literature) and its transferability to Hungary.",
    "finnish_reform": "The Finnish peruskoulu comprehensive-school reform: what it bundled, what carried the equity effect, and what is and is not transferable.",
    "polish_reform": "Poland's 1999 delayed-tracking reform and its 2016-2019 reversal: measured effects and the political-durability lesson.",
    "portuguese_reform": "Portugal's non-structural improvement path (standards, TEIP targeted support, retention reduction) as an alternative or complement to structural reform.",
    "equity_and_social_mobility": "Distributional effects of early selection: SES gradients, selection vs value-added, peer effects on non-selected pupils.",
    "demography": "Cohort decline and its forcing effect on school-network decisions through 2040.",
    "school_network_planning": "Town-by-town feasibility: school-size economics, building stock, commuting tolerances under each scenario.",
    "education_finance": "Steady-state and transition costs; honest order-of-magnitude ranges and what drives them.",
    "legal_and_governance": "Statutory anchoring (Nkt.), maintainer plurality, felmenő rendszer guarantees, and the legally feasible speed of change.",
    "political_feasibility": "Stakeholder mobilisation, reversal risk, and what makes education reforms politically durable in Hungary.",
    "implementation_planning": "Sequencing, teacher-supply constraints, administrative bandwidth, and realistic timelines.",
    "conservative_education": "The conservative case in the selection debate: parental school choice as a right, subsidiarity, talent development and institutional autonomy. Steel-man the strongest argument for keeping structured early tracks — under the same evidence discipline as every other expert.",
}

CRITICS = {
    "devil_advocate": "Attack each scenario's load-bearing claim; find the assumption whose failure collapses the scenario.",
    "evidence_checker": "Verify every evidence tag: is the cited support real, current, and correctly graded? Flag claims tagged stronger than their source warrants.",
    "assumption_checker": "Find hidden or unverifiable assumptions, and contradictions between a scenario's assumptions and the expert record.",
    "equity_checker": "Test each scenario's equity_impact field: who is actually reached, who is left out, and where could the scenario be equity-negative?",
    "feasibility_checker": "Test implementation_steps against real capacity: teacher supply, administrative bandwidth, legal lead times.",
    "cost_checker": "Test cost_categories: missing items, missing ranges, fiscal sensitivity, transition vs steady-state confusion.",
    "political_risk_checker": "Test political_risks: unmitigated reversal risks, understated opposition, missing entrenchment design.",
    "coherence_checker": "Find internal contradictions within and between scenario fields (goal vs steps, mechanism vs costs).",
}

SYNTHESIS = {
    "editor": "Synthesize expert outputs into a coherent picture WITHOUT forcing consensus: produce the disagreement map and preserve minority positions with their rationale.",
    "scenario_builder": "Build the policy scenarios (S1..S4) with every required field, from the expert record — candidate framings first, then select.",
    "translator": "Produce the Hungarian versions of all policy deliverables using docs/glossary.md; mirror structure and scenario ids exactly.",
    "final_brief_writer": "Write the policy brief with strictly separated layers: Evidence / Interpretation / Assumptions / Recommendations / Open questions.",
    "executive_summary_writer": "Write a one-page executive summary that preserves the central disagreement instead of resolving it.",
}

META = {
    "policy_architect": "Own the overall architecture: the four levels, the pattern basis (orchestrator-workers, evaluator-optimizer, Reflexion, ADAS, Habermas Machine) and their documented cautions.",
    "workflow_designer": "Own docs/workflow.md and config/system_config.json: propose workflow-step changes when the meta-critique shows a step failing.",
    "agent_designer": "Own agent specs: propose new/changed/removed agents from the archive of prior versions and scores; never repeat an archived failure; never create dishonest, unsafe or evidence-weakening agents.",
    "evaluation_designer": "Own the rubric (templates/evaluation_rubric.md + lab/evaluation.py): keep deterministic checks primary and the judge protocol debiased.",
    "iteration_manager": "Orchestrate rounds: apply the previous plan, run the workflow, evaluate, plan the next change, decide continue/stop/ask-human.",
    "meta_critic": "Each round, evaluate the agent SYSTEM itself: which agent or workflow step failed, whether critiques were concrete, whether score gains are genuine or rubric-gaming, and which agents are removal candidates.",
}

TYPE_RULES = {
    "expert": [
        "Tag every factual claim with an evidence status: [evidence: strong|moderate|weak|contested] plus the source.",
        "Keep Findings (evidence), Interpretation, Assumptions, Position and Uncertainties in separate sections; never mix layers.",
        "Never invent statistics or citations; if you do not know, say so as an explicit uncertainty.",
        "State your Position in one sentence so the disagreement map can cite it.",
        "Stay under ~450 words; density beats volume (length is not rewarded).",
    ],
    "critic": [
        "Every objection MUST name a specific scenario id AND field, as a heading: `## S<n>.<field>`.",
        "Follow each heading with `Objection: <the concrete flaw>` — generic feedback is a failure.",
        "2-4 objections; pick the most consequential, not the easiest.",
        "Attack content, not style; never object to phrasing.",
        "Do not soften: if a scenario's core claim is unsupported, say exactly that.",
    ],
    "synthesis": [
        "Never force consensus: disagreement is signal, not noise to remove.",
        "Preserve every evidence tag from the inputs; never upgrade an evidence status.",
        "Keep scenario ids (S1..S4) stable and identical across languages.",
        "Follow every line in the ## Directives section strictly.",
    ],
    "meta": [
        "Judge the SYSTEM (agents, workflow, rubric), not the policy content.",
        "Never propose removing a critic, weakening evidence discipline, or reducing preserved disagreement — these are forbidden regressions.",
        "Consult outputs/archive/attempts_log.jsonl before proposing any change; never repeat an archived failure.",
        "State explicitly whether score gains are GENUINE or RUBRIC-GAMING, with reasons.",
    ],
}

TYPE_EVIDENCE = {
    "expert": "Labels: strong / moderate / weak / contested / assumption. A claim without a tag is treated as unsupported by the evidence_checker.",
    "critic": "Objections must engage the evidence tags: an objection that a tag is too strong must say what the source actually supports.",
    "synthesis": "Carry tags through verbatim; assumptions stay labelled [assumption]; recommendations never masquerade as evidence.",
    "meta": "Claims about system performance must cite the round's numeric scores or concrete artifacts.",
}

TYPE_UNCERTAINTY = {
    "expert": "List what you do not know in ## Uncertainties. Never state confidence you do not have.",
    "critic": "If an objection is speculative, mark it (speculative). Distinguish 'wrong' from 'unsupported'.",
    "synthesis": "Uncertainties survive synthesis; a synthesis with fewer uncertainties than its inputs is broken.",
    "meta": "Attribution of score deltas is uncertain with one change per round at n=1; say so.",
}

TYPE_FAILURES = {
    "expert": ["Overclaiming from thin evidence", "Hedging everything into uselessness", "Drifting outside the assigned domain"],
    "critic": ["Generic feedback naming no scenario/field", "Style nitpicks", "Repeating another critic's objection without adding force"],
    "synthesis": ["Consensus laundering (dropping minority views)", "Upgrading evidence status while summarising", "Structure drift between language versions"],
    "meta": ["Judging the policy instead of the system", "Rubber-stamping score gains as genuine without evidence", "Proposing changes the archive shows already failed"],
}

TYPE_SELFCRIT = {
    "expert": ["Is every claim tagged?", "Would a domain expert call any claim overstated?", "Is my Position falsifiable?"],
    "critic": ["Does each objection name id+field?", "Would fixing my objections actually improve the scenario?", "Did I attack the strongest version of the claim?"],
    "synthesis": ["Did any dissent disappear?", "Are the language versions structurally identical?", "Did I add any claim not present in the inputs?"],
    "meta": ["Did I evaluate the system, not the policy?", "Is my gaming judgment backed by artifact evidence?", "Did I check the archive?"],
}

TYPE_TEMPLATE = {
    "expert": "# Expert analysis: <name>\\n## Findings (evidence)\\n- <claim> [evidence: <status> — <source>]\\n## Interpretation\\n## Assumptions\\n- <assumption> [assumption]\\n## Position\\n## Uncertainties\\n- <unknown>",
    "critic": "# Critique: <name>\\n## S<n>.<field>\\nObjection: <concrete flaw>",
    "synthesis": "(per agent — see Mission; scenario_builder/translator return the scenarios JSON schema, editor returns synthesis.md with '## Disagreement map', final_brief_writer returns the 5-section brief)",
    "meta": "# Meta-critique — round <n>\\n## Agent performance\\n## Workflow\\n## Critique quality\\n## Gaming judgment (explicit)\\n## Translation consistency",
}

EXTRA_SECTIONS = {
    "translator": (
        "## Glossary use\n"
        "Read the term table in docs/glossary.md before translating. Every EN "
        "term appearing in the source MUST be rendered with its listed HU "
        "equivalent (and vice versa for back-translation checks). If a needed "
        "term is missing from the glossary, add a proposal to the round's "
        "improvement_plan notes rather than improvising silently; the "
        "translation_checker will flag undocumented terminology.\n"),
    "translation_checker": (
        "## Glossary use\n"
        "Enforce docs/glossary.md mechanically: for each glossary pair, if one "
        "side appears in one language version, the counterpart must appear in "
        "the other. Report violations per scenario id. Also verify: identical "
        "scenario-id sets, matching section structure, and that no HU file is "
        "a byte-identical copy of the EN file. Deterministic checks are "
        "primary; add LLM judgment only as a flagged, low-confidence note.\n"),
}


def all_agents():
    """Yield (type, name, focus) for every agent."""
    for name, focus in EXPERTS.items():
        yield "experts", name, focus
    for name, focus in CRITICS.items():
        yield "critics", name, focus
    yield "critics", "translation_checker", (
        "Verify HU↔EN parity of all bilingual deliverables: id sets, section "
        "structure, glossary conformance, non-identity, back-translation "
        "key-term check.")
    for name, focus in SYNTHESIS.items():
        yield "synthesis", name, focus
    for name, focus in META.items():
        yield "meta", name, focus


TYPE_OF_DIR = {"experts": "expert", "critics": "critic",
               "synthesis": "synthesis", "meta": "meta"}

PROVIDER_ROLE = {"expert": "generator", "synthesis": "generator",
                 "critic": "judge", "meta": "judge"}
