"""Deterministic mock backend.

Composes agent outputs from the curated briefing pack in `knowledge.py`.
Crucially, output structure depends on `DIRECTIVE:` markers found in the
prompt (the improvement step appends directives to agent specs, and specs are
embedded in prompts), so system changes causally change outputs — the same
mechanism a real LLM backend exhibits, made deterministic.
"""
import json
import re

from . import knowledge as K
from . import ledger as LG
from .util import stable_jitter

DIRECTIVE_RE = re.compile(r"DIRECTIVE:([a-z_]+)")
HEADER_RE = re.compile(r"^(TASK|AGENT|LANG|ROUND|PROVIDER):\s*(.+)$", re.M)


def _headers(prompt):
    return {k.lower(): v.strip() for k, v in HEADER_RE.findall(prompt)}


def _directives(prompt):
    return set(DIRECTIVE_RE.findall(prompt))


def _payload(prompt):
    m = re.search(r"=== INPUT JSON ===\n(.*?)\n=== END INPUT ===", prompt, re.S)
    return json.loads(m.group(1)) if m else {}


def compose(prompt, role):
    h = _headers(prompt)
    task = h.get("task", "")
    d = _directives(prompt)
    fn = {
        "expert_analysis": lambda: expert_analysis(h["agent"], d),
        "build_scenarios": lambda: scenarios_json(d),
        "synthesis": lambda: synthesis(d),
        "rejected_framings": lambda: rejected_framings(),
        "brief": lambda: brief(d, prompt),
        "exec_summary": lambda: K.EXEC_SUMMARY[h.get("lang", "en")],
        "critic": lambda: critic(h["agent"], d),
        "meta_critique": lambda: meta_critique(_payload(prompt), d),
        "judge_score": lambda: judge_score(prompt, h, _payload(prompt)),
        "discourse_voice": lambda: discourse_voice(h["agent"]),
        "argument_map": lambda: argument_map(),
        "argument_decompose": lambda: argument_decompose(prompt),
        "grade_arguments": lambda: grade_arguments(prompt),
        "discourse_reciprocity": lambda: discourse_reciprocity(h["agent"]),
    }.get(task)
    if fn is None:
        raise ValueError(f"mock backend: unknown task {task!r}")
    return fn()


# -- experts ----------------------------------------------------------------

def _hu_pair(en, hu=None):
    """Bilingual leaf; the curated pack is EN-only for some expert fields,
    so the mock's HU side is an honestly-labelled placeholder there."""
    return {"en": en, "hu": hu if hu is not None else "(HU) " + en}


def expert_analysis(agent, d):
    b = K.EXPERT_BRIEFS[agent]
    findings = []
    for fid in b["findings"]:
        f = K.FACTS[fid]
        findings.append(dict(claim={"en": f["en"], "hu": f["hu"]},
                             evidence=f["evidence"], source=f["source"]))
    return json.dumps(dict(
        findings=findings,
        interpretation=_hu_pair(b["interpretation"]),
        assumptions=[_hu_pair(a) for a in b["assumptions"]],
        position=_hu_pair(b["position"]),
        uncertainties=[dict(text=_hu_pair(u["text"]),
                            confidence=u["confidence"],
                            reduced_by=_hu_pair(u["reducer"]))
                       for u in b["uncertainties"]],
    ), ensure_ascii=False, indent=2)


# -- scenarios ---------------------------------------------------------------

def _pair(x):
    """Project a curated {en, hu, ...} record to a bilingual leaf pair."""
    return {"en": x["en"], "hu": x["hu"]}


def scenarios_json(d):
    """Bilingual structured scenarios (D-34) from the curated pack."""
    scenarios = []
    for s in K.SCENARIOS:
        scenarios.append(dict(
            id=s["id"], title=_pair(s["title"]), goal=_pair(s["goal"]),
            mechanism=[dict(text=_pair(c), evidence=c["evidence"])
                       for c in s["mechanism"]],
            evidence_status=dict(label=s["evidence_status"]["label"],
                                 note=_pair(s["evidence_status"])),
            assumptions=[_pair(a) for a in s["assumptions"]],
            expected_benefits=[dict(text=_pair(b), evidence=b["evidence"])
                               for b in s["expected_benefits"]],
            equity_impact=_pair(s["equity_impact"]),
            cost_categories=[_pair(c) for c in s["cost_categories"]],
            implementation_steps=[dict(actor=_pair(st["actor"]),
                                       action=_pair(st["action"]),
                                       timeline=_pair(st["timeline"]))
                                  for st in s["implementation_steps"]],
            political_risks=[_pair(r) for r in s["political_risks"]],
            uncertainties=[dict(text=_pair(u), confidence=u["confidence"],
                                reduced_by=_pair(u["reducer"]))
                           for u in s["uncertainties"]],
        ))
    return json.dumps({"scenarios": scenarios}, ensure_ascii=False, indent=2)


# -- synthesis ---------------------------------------------------------------

def synthesis(d):
    disagreements = []
    for dis in K.DISAGREEMENTS:
        sides = [dict(holders=list(side["holders"]),
                      position=_pair(side["position"]),
                      rationale=_pair(side["rationale"]),
                      minority=(i == dis["minority_index"]))
                 for i, side in enumerate(dis["sides"])]
        disagreements.append(dict(topic=_hu_pair(dis["topic"]), sides=sides))
    return json.dumps(dict(
        overview=_hu_pair(
            "Four scenarios span the real option space: reform the entry "
            "gate (S1), shrink early-selective intake gradually (S2), end "
            "between-school selection before 14 (S3), or compensate without "
            "structural change (S4). The scenarios are not mutually "
            "exclusive: S1 and S4 are cheap, reversible pilots that inform "
            "the structural choice between S2 and S3."),
        disagreements=disagreements,
        agreements=[
            dict(text=_hu_pair("Annual publication of intake-composition "
                               "data is a no-regret move under every "
                               "scenario."), evidence="strong"),
            dict(text=_hu_pair("Transition capacity (teachers, legal notice "
                               "periods) binds any structural variant to a "
                               "6-12 year horizon."), evidence="strong"),
        ],
    ), ensure_ascii=False, indent=2)


def rejected_framings():
    scenarios = []
    for s in K.SCENARIOS:
        chosen = next(f["en"] for f in s["framings"] if f["chosen"])
        rejected = [dict(framing=f["en"], reason=f["reject_reason"])
                    for f in s["framings"] if not f["chosen"]]
        scenarios.append(dict(id=s["id"], chosen=chosen, rejected=rejected))
    return json.dumps({"scenarios": scenarios}, ensure_ascii=False, indent=2)


# -- brief -------------------------------------------------------------------

_LIKELY = [
    {"en": "The Hungarian SES gradient is consistent with the causal "
           "tracking evidence, but country-level causality is an "
           "inference, not a measured fact.",
     "hu": "A magyar társadalmi-gazdasági gradiens összhangban áll az "
           "oksági tracking-kutatásokkal, de az országszintű okság "
           "következtetés, nem mért tény."},
    {"en": "The gimnázium tracks' raw advantage is mostly selection "
           "effect; their causal value added is modest.",
     "hu": "A gimnáziumi képzések nyers előnye főként szelekciós hatás; "
           "oksági hozzáadott értékük szerény."},
]

_UNKNOWN = [
    {"en": "Whether institutional capacity for a structural reform can be "
           "built within a decade is unresolved.",
     "hu": "Nyitott, hogy egy szerkezeti reform intézményi kapacitása "
           "felépíthető-e egy évtizeden belül."},
    {"en": "Whether published intake data would stay accurate and "
           "politically survivable is untested.",
     "hu": "Nem próbált még ki, hogy a közzétett bekerülési adatok "
           "pontosak és politikailag fenntarthatók maradnának-e."},
]

_RESPONSE_REASONS = {
    "policy_design_fixable": dict(
        en="a design change (guarantee, phase-in, compensation) reduces this",
        hu="egy tervezési változtatás (garancia, fokozatosság, kompenzáció) csökkenti ezt"),
    "evidence_answerable": dict(
        en="the registry evidence settles this claim",
        hu="a regiszter-evidencia eldönti ezt az állítást"),
    "value_conflict": dict(
        en="legitimate values collide here; there is no technical fix",
        hu="itt legitim értékek ütköznek; nincs technikai megoldás"),
    "needs_more_info": dict(
        en="not yet decidable from the current evidence",
        hu="a jelenlegi evidenciából még nem dönthető el"),
    "not_decision_relevant": dict(
        en="attention-worthy but would not change the decision (see gumicsontok)",
        hu="figyelmet érdemel, de nem változtatna a döntésen (lásd: gumicsontok)"),
    "irreducible_tradeoff": dict(
        en="improving one goal here necessarily costs another",
        hu="az egyik cél javítása itt szükségképpen ront egy másikon"),
    "communication_fixable": dict(
        en="already addressed but not visibly or legibly enough",
        hu="már kezelve van, de nem eléggé láthatóan vagy érthetően"),
}


def brief(d, prompt=""):
    """The bilingual 10-section deliberation deliverable (D-30/D-34).
    Answers every REAL cluster id in THIS round's ledger — the mock must
    stay valid regardless of the live cluster count."""
    curated_by_id = {c["id"]: c for c in K.ARGUMENT_CLUSTERS}
    real_ids = sorted(set(re.findall(r"\*\*(A\d+)\*\*", prompt)),
                      key=lambda s: int(s[1:])) or list(curated_by_id)
    responses = []
    for cid in real_ids:
        cur = curated_by_id.get(cid)
        if cur:
            restatement, rtype = _pair(cur["claim"]), cur["response_type"]
        else:
            restatement = {"en": "(see argument ledger)",
                           "hu": "(lásd az érv-főkönyvet)"}
            rtype = "needs_more_info"
        responses.append(dict(cluster_id=cid, restatement=restatement,
                              response_type=rtype,
                              reason=dict(_RESPONSE_REASONS[rtype])))
    sinks = [dict(cluster_id=c["id"], text=_pair(c["claim"]))
             for c in K.ARGUMENT_CLUSTERS
             if LG.is_gumicsont(c) and c["id"] in set(real_ids)]

    disagree, minority = [], []
    for dis in K.DISAGREEMENTS:
        positions = []
        for i, side in enumerate(dis["sides"]):
            positions.append(dict(holders=list(side["holders"]),
                                  position=_pair(side["position"]),
                                  why=_pair(side["rationale"]),
                                  minority=(i == dis["minority_index"])))
            if i == dis["minority_index"]:
                minority.append(dict(holders=list(side["holders"]),
                                     position=_pair(side["position"]),
                                     rationale=_pair(side["rationale"])))
        disagree.append(dict(topic=_hu_pair(dis["topic"]), positions=positions))

    unknown = [dict(text=dict(u), kind="assumption") for u in _UNKNOWN]
    for s in K.SCENARIOS[:2]:
        if s["uncertainties"]:
            unknown.append(dict(text=_pair(s["uncertainties"][0]),
                                kind="assumption"))

    costs = []
    for s in K.SCENARIOS:
        cost = s["cost_categories"][0] if s["cost_categories"] else None
        risk = s["political_risks"][0] if s["political_risks"] else None
        text = {L: " — ".join(filter(None, [
                    s["equity_impact"][L],
                    cost[L] if cost else None,
                    risk[L] if risk else None]))
                for L in ("en", "hu")}
        costs.append(dict(scenario_id=s["id"], text=text, kind="estimate"))

    return json.dumps(dict(
        intro=_pair(K.BRIEF_INTRO),
        scenario_key=[dict(id=s["id"], title=_pair(s["title"]))
                      for s in K.SCENARIOS],
        what_we_know=[dict(text=_pair(K.FACTS[fid]), kind="fact",
                           evidence=K.FACTS[fid]["evidence"])
                      for fid in ["pisa_escs", "tracking_inequality",
                                  "gimn_share", "poland_reform", "demography"]],
        what_we_consider_likely=[dict(text=dict(x), kind="estimate")
                                 for x in _LIKELY],
        where_experts_disagree=disagree,
        what_we_dont_know=unknown,
        what_could_be_done=[dict(scenario_id=s["id"], title=_pair(s["title"]),
                                 summary=_pair(s["goal"]))
                            for s in K.SCENARIOS],
        what_each_option_costs=costs,
        what_research_could_resolve=[_pair(r) for r in K.RECOMMENDATIONS],
        what_people_must_decide=[_hu_pair(q["question"])
                                 for q in K.HUMAN_QUESTIONS],
        stakeholder_responses=responses,
        attention_sinks=sinks,
        minority_positions=minority,
    ), ensure_ascii=False, indent=2)


# -- critics -----------------------------------------------------------------

def critic(agent, d):
    return json.dumps({"objections": [
        dict(scenario=o["scenario"], field=o["field"],
             objection=o["objection"], severity=o["severity"],
             suggested_revision=o["fix"])
        for o in K.CRITIQUES[agent]]}, ensure_ascii=False, indent=2)


# -- societal discourse (D-29) ------------------------------------------------

def discourse_voice(name):
    v = K.DISCOURSE_VOICES[name]
    reactions = []
    for sid in ("S1", "S2", "S3", "S4"):
        r = v["reactions"][sid]
        reactions.append(dict(
            scenario=sid, stance=r["stance"], label=r["label"],
            source=r.get("source", ""), basis=r.get("basis", ""),
            interest=_pair(v["interest"]),
            public_good_frame=_pair(v["frame"]),
            argument=_pair(r["argument"]),
            condition_to_change=_pair(r["condition"])))
    return json.dumps(dict(voice=name, reactions=reactions),
                      ensure_ascii=False, indent=2)


def argument_map():
    clusters = [dict(id=c["id"], scenario=c["scenario"], kind=c["kind"],
                     side=c["side"], claim=_pair(c["claim"]),
                     raised_by=list(c["raised_by"]))
                for c in K.ARGUMENT_CLUSTERS]
    return json.dumps({"clusters": clusters}, ensure_ascii=False, indent=2)


def _pair_list(x):
    """Curated {'en': [...], 'hu': [...]} parallel lists -> [{en, hu}, ...]."""
    return [{"en": e, "hu": h} for e, h in zip(x["en"], x["hu"])]


def argument_decompose(prompt):
    """Decompose ONE cluster (phase 2 of the D-30 split). Curated ids get
    their curated decomposition; a live cluster id outside the curated pack
    gets an honest, generic templated decomposition instead of failing
    outright — a single unmatched cluster degrades alone."""
    m = re.search(r"argument cluster (A\d+)", prompt)
    cid = m.group(1) if m else None
    curated = {c["id"]: c for c in K.ARGUMENT_CLUSTERS}
    cur = curated.get(cid)
    if cur:
        return json.dumps(dict(
            interest=_pair(cur["interest"]), value=_pair(cur["value"]),
            fear=_pair(cur["fear"]), affected=_pair_list(cur["affected"]),
            assumption=_pair(cur["assumption"]),
            empirical_uncertainty=_pair(cur["empirical_uncertainty"]),
            decision_relevance=cur["decision_relevance"],
            attention=dict(cur["attention"]),
        ), ensure_ascii=False, indent=2)
    names = re.findall(r"^- (\S+) \(", prompt, re.M) or ["unspecified stakeholders"]
    return json.dumps(dict(
        interest=_hu_pair(f"the concern(s) raised by {', '.join(names)}"),
        value=_hu_pair("a trade-off between the scenario's stated goal and "
                       "the concern raised"),
        fear=_hu_pair("the benefit claimed will not materialise as described"),
        affected=[_hu_pair(nm) for nm in names],
        assumption=_hu_pair("the claim's premise holds under implementation "
                            "as designed"),
        empirical_uncertainty=_hu_pair("not independently graded here — see "
                                       "the evidence layer"),
        decision_relevance="medium",
        attention=dict(high_attention=len(names) >= 3, new_information=False,
                       changes_evaluation=True, already_answered=False,
                       primarily_rhetorical=False),
    ), ensure_ascii=False, indent=2)


def grade_arguments(prompt):
    """Grade the clusters ACTUALLY in the prompt (a live argument map's ids
    differ from the curated pack's): known curated ids get their curated
    grade, everything else is honestly marked not_registry_backed."""
    curated = {c["id"]: c for c in K.ARGUMENT_CLUSTERS}
    m = re.search(r"=== INPUTS ===\n(.*)", prompt, re.S)
    try:
        clusters = json.loads(m.group(1)) if m else K.ARGUMENT_CLUSTERS
    except (json.JSONDecodeError, AttributeError):
        clusters = K.ARGUMENT_CLUSTERS
    grades = []
    for c in clusters:
        if c.get("kind") not in ("fact", "mixed"):
            continue
        cur = curated.get(c.get("id"))
        if cur and cur.get("grade"):
            f = K.FACTS[cur["grade_source"]]
            grades.append(dict(cluster_id=c["id"], status=cur["grade"],
                               source=f["source"],
                               note=f"registry fact {cur['grade_source']}"))
        else:
            grades.append(dict(cluster_id=c["id"],
                               status="not_registry_backed", source="",
                               note="no curated source supports this claim"))
    return json.dumps({"grades": grades}, ensure_ascii=False, indent=2)


def discourse_reciprocity(name):
    r = K.DISCOURSE_VOICES[name]["response"]
    return json.dumps(dict(voice=name, responses=[dict(
        cluster=r["cluster"], response=_pair(r), outcome=r["outcome"],
        new_condition={"en": "", "hu": ""})]), ensure_ascii=False, indent=2)


# -- meta critique -----------------------------------------------------------

def meta_critique(payload, d):
    rnd = payload.get("round", 1)
    prev = payload.get("prev_total")
    total = payload.get("total")
    weakest = payload.get("weakest", "?")
    applied = payload.get("applied_change")
    lines = [f"# Meta-critique — round {rnd}", "",
             "## Scope",
             "This evaluates the agent SYSTEM (agents, workflow, critique "
             "quality), not the policy content.", "",
             "## Agent performance"]
    if applied:
        lines.append(f"- The change applied this round ({applied['id']}, "
                     f"targeting {applied['dimension']}) modified: "
                     f"{', '.join(applied['targets'])}.")
    lines += [
        "- Weakest rubric dimension this round: "
        f"**{weakest}** — the agents most responsible for it should be the "
        "target of the next change.",
        "- The `international_comparison` and `hungarian_education_system` "
        "experts partially overlap in findings; if neither uniquely raises a "
        "dimension across two rounds, one becomes a removal candidate "
        "(insufficient evidence yet — tracking).",
    ]
    lines += ["", "## Workflow"]
    lines.append("- No workflow step failed this round; all artifacts were "
                 "produced." if not payload.get("fallbacks") else
                 f"- Steps degraded to mock fallback: {payload['fallbacks']} — "
                 "these are the weakest workflow links.")
    lines += ["", "## Critique quality"]
    lines.append("- All critic objections name a scenario id and field. "
                 + ("Severity and suggested revisions are present, making "
                    "them actionable." if "critic_fix_severity" in d else
                    "They lack severity ranking and suggested revisions — a "
                    "candidate improvement for critic_concreteness."))
    lines += ["", "## Gaming judgment (explicit)"]
    if prev is None:
        lines.append("- First scored round; there is no gain to certify as "
                     "GENUINE or RUBRIC-GAMING yet. Baseline scores come from "
                     "deterministic, verbosity-capped checks on real "
                     "artifacts, so the baseline itself is not gameable by "
                     "length.")
    else:
        delta = round(total - prev, 3) if total is not None else None
        lines.append(
            f"- Total moved {prev} → {total} (delta {delta}). I judge this "
            "gain GENUINE, not rubric-gaming: the underlying artifacts changed "
            "structurally (diffable in system_state/ and the round outputs), "
            "the scoring components are density-based and capped so added "
            "verbosity alone cannot raise them, and no critic, evidence rule "
            "or disagreement section was removed (verified by check 14).")
    lines += ["", "## Translation consistency"]
    tc = payload.get("translation", {})
    lines.append(f"- Deterministic parity: id_sets_equal={tc.get('id_sets_equal')}, "
                 f"structure_equal={tc.get('structure_equal')}, "
                 f"glossary_violations={tc.get('glossary_violations')}. "
                 "Residual nuance (register, connotation) remains flagged for "
                 "a human in human_questions.md.")
    if payload.get("judge_divergence"):
        lines += ["", "## Judge divergence",
                  f"- Dimensions flagged for divergence: "
                  f"{payload['judge_divergence']} — not averaged; sent to "
                  "human review."]
    return "\n".join(lines) + "\n"


# -- judge -------------------------------------------------------------------

def judge_score(prompt, h, payload):
    """Deterministic heuristic judge over the artifact text in the prompt.

    Scores by density of discipline markers (capped — verbosity cannot raise
    the score), with small order-dependent jitter so randomized trials show
    honest variance. The two provider passes weight sub-signals differently.
    """
    dim = payload.get("dimension", "")
    provider = h.get("provider", "anthropic")
    m = re.search(r"=== ARTIFACT ===\n(.*)", prompt, re.S)
    text = m.group(1) if m else ""
    n_units = max(1, text.count("## "))

    def density(pattern, per_unit_cap=3.0):
        count = len(re.findall(pattern, text, re.M))
        return min(count / n_units, per_unit_cap) / per_unit_cap  # 0..1

    signals = {
        "evidence_discipline": 0.7 * density(r"\[(evidence|bizonyíték|assumption|interpretation|értelmezés|feltevés|fact|estimate|becslés|érték|value)") +
                               0.3 * density(r"(interpretation|értelmezés)"),
        "critic_concreteness": 0.5 * density(r"S\d+\.[a-z_]+") +
                               0.25 * density(r"Severity:") +
                               0.25 * density(r"Suggested revision:"),
        "disagreement_preservation": 0.5 * density(r"minority|Minority|különvélemén") +
                                     0.5 * density(r"Why:|Rationale:|Miért:"),
        "uncertainty_explicitness": 0.6 * density(r"confidence:|megbízhatóság:") +
                                    0.4 * density(r"reduce|csökkenten"),
        "meta_system_eval": 0.4 * density(r"agent|workflow") +
                            0.3 * density(r"GENUINE|gaming") +
                            0.3 * density(r"removal candidate"),
        "layer_separation": density(r"## (What we know|What we consider likely|"
                                    r"Where experts disagree|What we don't know|"
                                    r"What could be done|What each option costs|"
                                    r"What research could resolve|What people must decide|"
                                    r"What to verify with real stakeholders|"
                                    r"Where the red herrings are|"
                                    r"Amit már tudunk|Amit valószínűnek tartunk|"
                                    r"Amiben nincs szakértői egyetértés|Amit nem tudunk|"
                                    r"Mit lehetne tenni|Mi az egyes alternatívák ára|"
                                    r"Mit lehet még kutatással eldönteni|"
                                    r"Mit kell embereknek eldönteniük|"
                                    r"Mit kell valódi stakeholderekkel ellenőrizni|"
                                    r"Hol vannak a gumicsontok)", 10.0),
        "scenario_completeness": density(r"\*\*", 10.0),
        "translation_fidelity": density(r"gimnázium|szelekció", 2.0),
    }
    base = 3.0 + 7.0 * signals.get(dim, 0.5)
    # provider-specific emphasis: the google pass rewards coverage counts a
    # touch more, the anthropic pass rewards rationale markers.
    if provider == "google":
        base += 0.3 * density(r"^- ", 8.0)
    else:
        base += 0.3 * density(r"(Why:|because|rationale|Rationale)")
    score = max(0.0, min(10.0, base + stable_jitter(prompt, spread=0.3)))
    return (f"SCORE: {score:.2f}\n"
            f"REASON: {dim} judged from marker density across {n_units} "
            f"sections ({provider} pass; verbosity-capped).")
