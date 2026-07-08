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
        "build_scenarios": lambda: scenarios_json("en", d),
        "translate_scenarios": lambda: scenarios_json("hu", d),
        "synthesis": lambda: synthesis(d),
        "rejected_framings": lambda: rejected_framings(),
        "brief": lambda: brief(h.get("lang", "en"), d),
        "exec_summary": lambda: K.EXEC_SUMMARY[h.get("lang", "en")],
        "critic": lambda: critic(h["agent"], d),
        "meta_critique": lambda: meta_critique(_payload(prompt), d),
        "judge_score": lambda: judge_score(prompt, h, _payload(prompt)),
        "discourse_voice": lambda: discourse_voice(h["agent"]),
        "argument_map": lambda: argument_map(),
        "grade_arguments": lambda: grade_arguments(),
        "discourse_reciprocity": lambda: discourse_reciprocity(h["agent"]),
        "translate_ledger": lambda: translate_ledger(int(h.get("round", 1))),
    }.get(task)
    if fn is None:
        raise ValueError(f"mock backend: unknown task {task!r}")
    return fn()


# -- experts ----------------------------------------------------------------

def expert_analysis(agent, d):
    b = K.EXPERT_BRIEFS[agent]
    lines = [f"# Expert analysis: {agent}", "", "## Findings (evidence)"]
    for fid in b["findings"]:
        f = K.FACTS[fid]
        lines.append(f"- {f['en']} [evidence: {f['evidence']} — {f['source']}]")
    lines += ["", "## Interpretation", b["interpretation"],
              "", "## Assumptions"]
    lines += [f"- {a} [assumption]" for a in b["assumptions"]]
    lines += ["", "## Position", b["position"]]
    lines += ["", "## Uncertainties"]
    for u in b["uncertainties"]:
        item = f"- {u['text']}"
        if "uncertainty_quantify" in d:
            item += (f" (confidence: {u['confidence']}; evidence that would"
                     f" reduce it: {u['reducer']})")
        lines.append(item)
    return "\n".join(lines) + "\n"


# -- scenarios ---------------------------------------------------------------

def _render_scenario(s, lang, d):
    L = lang
    ev_label = (lambda e: e if L == "en" else K.EVIDENCE_HU[e])
    tag = (lambda e: f" [evidence: {e}]" if L == "en"
           else f" [bizonyíték: {K.EVIDENCE_HU[e]}]")
    mech = []
    for c in s["mechanism"]:
        t = c[L]
        if c["core"] or "evidence_tag_all" in d:
            t += tag(c["evidence"])
        mech.append(t)
    benefits = [b[L] + tag(b["evidence"]) for b in s["expected_benefits"]]
    steps = []
    for st in s["implementation_steps"]:
        line = f"{st['actor'][L]} — {st['action'][L]}"
        if "implementation_detail" in d:
            line += f" ({'timeline' if L=='en' else 'ütemezés'}: {st['timeline'][L]})"
        steps.append(line)
    uncertainties = []
    for u in s["uncertainties"]:
        t = u[L]
        if "uncertainty_quantify" in d:
            if L == "en":
                t += (f" (confidence: {u['confidence']}; would be reduced by:"
                      f" {u['reducer']['en']})")
            else:
                t += (f" (megbízhatóság: {K.CONFIDENCE_HU[u['confidence']]};"
                      f" csökkentené: {u['reducer']['hu']})")
        uncertainties.append(t)
    return dict(
        id=s["id"],
        title=s["title"][L],
        goal=s["goal"][L],
        mechanism=mech,
        evidence_status=f"{ev_label(s['evidence_status']['label'])} — {s['evidence_status'][L]}",
        assumptions=[a[L] for a in s["assumptions"]],
        expected_benefits=benefits,
        equity_impact=s["equity_impact"][L],
        cost_categories=[c[L] for c in s["cost_categories"]],
        implementation_steps=steps,
        political_risks=[r[L] for r in s["political_risks"]],
        uncertainties=uncertainties,
    )


def scenarios_json(lang, d):
    return json.dumps(
        {"scenarios": [_render_scenario(s, lang, d) for s in K.SCENARIOS]},
        ensure_ascii=False, indent=2)


# -- synthesis ---------------------------------------------------------------

def synthesis(d):
    lines = ["# Synthesis", "",
             "## Overview",
             "Four scenarios span the real option space: reform the entry gate "
             "(S1), shrink early-selective intake gradually (S2), end "
             "between-school selection before 14 (S3), or compensate without "
             "structural change (S4). The scenarios are not mutually exclusive: "
             "S1 and S4 are cheap, reversible pilots that inform the structural "
             "choice between S2 and S3.",
             "",
             "## Disagreement map"]
    for dis in K.DISAGREEMENTS:
        lines.append(f"### {dis['topic']}")
        for i, side in enumerate(dis["sides"]):
            who = ", ".join(side["holders"])
            mark = " (minority)" if i == dis["minority_index"] else ""
            lines.append(f"- **{who}**{mark}: {side['position']['en']} "
                         f"Why: {side['rationale']['en']}")
        lines.append("")
    if "minority_report" in d:
        lines += ["## Minority positions (preserved in full)"]
        for dis in K.DISAGREEMENTS:
            side = dis["sides"][dis["minority_index"]]
            who = ", ".join(side["holders"])
            lines.append(f"- On *{dis['topic']}*, the minority ({who}) holds: "
                         f"{side['position']['en']} Rationale: "
                         f"{side['rationale']['en']} This position is carried "
                         f"into the final brief, not resolved away.")
        lines.append("")
    lines += ["## What the experts agree on",
              "- Annual publication of intake-composition data is a no-regret "
              "move under every scenario. [evidence: strong]",
              "- Transition capacity (teachers, legal notice periods) binds any "
              "structural variant to a 6-12 year horizon. [evidence: strong]"]
    return "\n".join(lines) + "\n"


def rejected_framings():
    lines = ["# Rejected framings", "",
             "Candidate framings generated per scenario; one selected, the "
             "rest recorded here with the reason for rejection."]
    for s in K.SCENARIOS:
        lines.append(f"\n## {s['id']} — {s['title']['en']}")
        for f in s["framings"]:
            if f["chosen"]:
                lines.append(f"- CHOSEN: {f['en']}")
            else:
                lines.append(f"- REJECTED: {f['en']} — reason: {f['reject_reason']}")
    return "\n".join(lines) + "\n"


# -- brief -------------------------------------------------------------------

def brief(lang, d):
    L = lang
    if L == "en":
        H = dict(title="# Policy brief — early selection and the 6/8-year gimnázium",
                 ev="## Evidence", interp="## Interpretation",
                 ass="## Assumptions", rec="## Recommendations",
                 open="## Open questions (for human judgment)",
                 minority="## Minority positions")
    else:
        H = dict(title="# Szakpolitikai összefoglaló — korai szelekció és a hat-/nyolcosztályos gimnázium",
                 ev="## Bizonyítékok", interp="## Értelmezés",
                 ass="## Feltevések", rec="## Ajánlások",
                 open="## Nyitott kérdések (emberi mérlegelésre)",
                 minority="## Különvélemények")
    lines = [H["title"], "", K.BRIEF_INTRO[L]]
    if "scenario_crossref" in d:
        if L == "en":
            lines += ["", "## Scenario key (full detail: scenarios.en.md)"]
            lines += [f"- {s['id']} — {s['title']['en']}" for s in K.SCENARIOS]
        else:
            lines += ["", "## Forgatókönyv-kulcs (részletesen: scenarios.hu.md)"]
            lines += [f"- {s['id']} — {s['title']['hu']}" for s in K.SCENARIOS]
    lines += ["", H["ev"]]
    for fid in ["pisa_escs", "tracking_inequality", "gimn_share", "poland_reform", "demography"]:
        f = K.FACTS[fid]
        ev = f["evidence"] if L == "en" else K.EVIDENCE_HU[f["evidence"]]
        label = "evidence" if L == "en" else "bizonyíték"
        lines.append(f"- {f[L]} [{label}: {ev}]")
    lines += ["", H["interp"]]
    if L == "en":
        lines += ["- The Hungarian SES gradient is consistent with the causal "
                  "tracking evidence, but country-level causality is an "
                  "interpretation, not a measured fact. [interpretation]",
                  "- The gimnázium tracks' raw advantage is mostly selection "
                  "effect; their causal value added is modest. [interpretation, "
                  "based on moderate evidence]"]
    else:
        lines += ["- A magyar társadalmi-gazdasági gradiens összhangban áll az "
                  "oksági tracking-kutatásokkal, de az országszintű okság "
                  "értelmezés, nem mért tény. [értelmezés]",
                  "- A gimnáziumi képzések nyers előnye főként szelekciós "
                  "hatás; oksági hozzáadott értékük szerény. [értelmezés, "
                  "mérsékelt bizonyítékra építve]"]
    lines += ["", H["ass"]]
    if L == "en":
        lines += ["- Institutional capacity for any structural reform can be "
                  "built within a decade. [assumption]",
                  "- Published intake data would be accurate and politically "
                  "survivable. [assumption]"]
    else:
        lines += ["- Bármely szerkezeti reform intézményi kapacitása egy "
                  "évtizeden belül kiépíthető. [feltevés]",
                  "- A közzétett bekerülési adatok pontosak és politikailag "
                  "fenntarthatók lennének. [feltevés]"]
    lines += ["", H["rec"]]
    for r in K.RECOMMENDATIONS:
        lines.append(f"- {r[L]}")
    # response obligation (D-29, CNDP model): answer every argument cluster
    lines += ["", "## Responses to public arguments" if L == "en"
              else "## Válaszok a társadalmi érvekre"]
    for c in K.ARGUMENT_CLUSTERS:
        claim = c["claim"][L]
        if c["kind"] == "value":
            verdict = ("left open — a value question requiring human judgment"
                       if L == "en" else
                       "nyitva marad — emberi mérlegelést igénylő értékkérdés")
        elif not c.get("grade"):
            verdict = ("rejected as evidence — no curated source backs it; "
                       "treated as unverified model knowledge" if L == "en"
                       else "bizonyítékként elutasítva — kurált forrás nem "
                       "támasztja alá; ellenőrizetlen modelltudásként kezelve")
        elif c["side"] == "con":
            verdict = ("accepted as a binding constraint on the affected "
                       "scenario" if L == "en" else
                       "elfogadva mint az érintett forgatókönyv kötelező "
                       "korlátja")
        else:
            verdict = ("accepted — reflected in the recommendations"
                       if L == "en" else "elfogadva — az ajánlások tükrözik")
        lines.append(f"- {c['id']} ({claim[:80]}…): {verdict}")
    if "minority_report" in d:
        lines += ["", H["minority"]]
        for dis in K.DISAGREEMENTS:
            side = dis["sides"][dis["minority_index"]]
            who = ", ".join(side["holders"])
            lines.append(f"- ({who}) {side['position'][L]} — {side['rationale'][L]}")
    lines += ["", H["open"]]
    for q in K.HUMAN_QUESTIONS[:3]:
        if L == "en":
            lines.append(f"- {q['question']}")
        else:
            pass
    if L == "hu":
        lines += ["- Hogyan súlyozandók a méltányossági nyereségek a jól "
                  "teljesítők kockázataival és a szülői választással szemben? "
                  "Ez értékkérdés, amelyet a rendszer nem dönthet el.",
                  "- Elfogadható-e a lengyel típusú visszafordítás kockázata, "
                  "ha a várható méltányossági nyereség nagy?",
                  "- Valóban politikailag megváltoztathatatlan-e a korai "
                  "szelekció, vagy ez a feltevés maga is döntés?"]
    return "\n".join(lines) + "\n"


# -- critics -----------------------------------------------------------------

def critic(agent, d):
    objections = K.CRITIQUES[agent]
    lines = [f"# Critique: {agent}", ""]
    for o in objections:
        lines.append(f"## {o['scenario']}.{o['field']}")
        lines.append(f"Objection: {o['objection']}")
        if "critic_fix_severity" in d:
            lines.append(f"Severity: {o['severity']}")
            lines.append(f"Suggested revision: {o['fix']}")
        lines.append("")
    return "\n".join(lines)


# -- societal discourse (D-29) ------------------------------------------------

def _voice_json(name, lang):
    v = K.DISCOURSE_VOICES[name]
    reactions = []
    for sid in ("S1", "S2", "S3", "S4"):
        r = v["reactions"][sid]
        reactions.append(dict(
            scenario=sid, stance=r["stance"], label=r["label"],
            source=r.get("source", ""), basis=r.get("basis", ""),
            interest=v["interest"][lang], public_good_frame=v["frame"][lang],
            argument=r["argument"][lang],
            condition_to_change=r["condition"][lang]))
    return dict(voice=name, reactions=reactions)


def discourse_voice(name):
    return json.dumps(_voice_json(name, "en"), ensure_ascii=False, indent=2)


def _clusters(lang):
    return [dict(id=c["id"], scenario=c["scenario"], kind=c["kind"],
                 side=c["side"], claim=c["claim"][lang],
                 raised_by=list(c["raised_by"]))
            for c in K.ARGUMENT_CLUSTERS]


def argument_map():
    return json.dumps({"clusters": _clusters("en")},
                      ensure_ascii=False, indent=2)


def grade_arguments():
    lines = []
    for c in K.ARGUMENT_CLUSTERS:
        if c["kind"] not in ("fact", "mixed"):
            continue
        if c.get("grade"):
            f = K.FACTS[c["grade_source"]]
            lines.append(f"{c['id']}: [evidence: {c['grade']} — "
                         f"{f['source']}] registry fact {c['grade_source']}")
        else:
            lines.append(f"{c['id']}: [not registry-backed — treat as model "
                         "knowledge] no curated source supports this claim")
    return "\n".join(lines) + "\n"


def _response_json(name, lang):
    r = K.DISCOURSE_VOICES[name]["response"]
    return dict(voice=name, responses=[dict(
        cluster=r["cluster"], response=r[lang], outcome=r["outcome"],
        new_condition="")])


def discourse_reciprocity(name):
    return json.dumps(_response_json(name, "en"), ensure_ascii=False, indent=2)


def translate_ledger(round_n):
    from .ledger import render_ledger
    voices = {n: _voice_json(n, "hu") for n in K.DISCOURSE_VOICES}
    grades = {}
    for line in grade_arguments().splitlines():
        cid, _, rest = line.partition(":")
        grades[cid.strip()] = rest.strip()
    responses = {n: _response_json(n, "hu") for n in K.DISCOURSE_VOICES}
    return render_ledger(round_n, voices, _clusters("hu"), grades,
                         responses, "hu")


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
        "evidence_discipline": 0.7 * density(r"\[(evidence|bizonyíték|assumption|interpretation|értelmezés|feltevés)") +
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
        "layer_separation": density(r"## (Evidence|Interpretation|Assumptions|Recommendations|Open questions|Bizonyítékok|Értelmezés|Feltevések|Ajánlások|Nyitott kérdések)", 5.0),
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
