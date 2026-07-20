"""Deterministic JSON→markdown renderers (D-34, Phase 2).

The bilingual JSON artifacts (lab/schemas.py) are the single source of
truth; every .md file is a generated view. The renderers deliberately
re-emit the legacy inline markers ([evidence: ...], 'Objection:', 'Why:',
'(minority)', the 10 brief headers, claim-kind tags) so the deterministic
evaluation (lab/evaluation.py) and the downstream prompts keep working
unchanged until Phase 3 moves them onto the JSON fields.

project() is the key migration trick: it collapses every {en, hu} leaf to
one language, so monolingual consumers (ledger renderer, digests, legacy
views) work on bilingual data without knowing about it.
"""
from . import knowledge as K

LANGS = ("en", "hu")


def is_pair(value):
    return isinstance(value, dict) and set(value) == {"en", "hu"}


def project(value, lang):
    """Recursively collapse every bilingual {en, hu} leaf to `lang`."""
    if is_pair(value):
        return value[lang]
    if isinstance(value, dict):
        return {k: project(v, lang) for k, v in value.items()}
    if isinstance(value, list):
        return [project(v, lang) for v in value]
    return value


def ev_tag(evidence, lang):
    if lang == "en":
        return f" [evidence: {evidence}]"
    return f" [bizonyíték: {K.EVIDENCE_HU[evidence]}]"


def _conf(u, lang):
    if lang == "en":
        return (f" (confidence: {u['confidence']}; would be reduced by: "
                f"{u['reduced_by']['en']})")
    return (f" (megbízhatóság: {K.CONFIDENCE_HU[u['confidence']]}; "
            f"csökkentené: {u['reduced_by']['hu']})")


# -- expert -------------------------------------------------------------------

def expert_md(name, o, lang="en"):
    L = lang
    lines = [f"# Expert analysis: {name}", "", "## Findings (evidence)"]
    for f in o["findings"]:
        label = "evidence" if L == "en" else "bizonyíték"
        ev = f["evidence"] if L == "en" else K.EVIDENCE_HU[f["evidence"]]
        lines.append(f"- {f['claim'][L]} [{label}: {ev} — {f['source']}]")
    lines += ["", "## Interpretation", o["interpretation"][L],
              "", "## Assumptions"]
    lines += [f"- {a[L]} [assumption]" for a in o["assumptions"]]
    lines += ["", "## Position", o["position"][L], "", "## Uncertainties"]
    for u in o["uncertainties"]:
        lines.append(f"- {u['text'][L]}{_conf(u, L)}")
    return "\n".join(lines) + "\n"


# -- scenarios ----------------------------------------------------------------

def scenario_view(o, lang):
    """Legacy-shape scenarios dict (strings with inline tags) for the
    monolingual consumers: evaluation, translation.check, memory,
    scenarios_md. The structured fields are flattened exactly the way the
    old pipeline produced them."""
    L = lang
    out = []
    for sc in o["scenarios"]:
        steps = []
        for st in sc["implementation_steps"]:
            tl = ("timeline" if L == "en" else "ütemezés")
            steps.append(f"{st['actor'][L]} — {st['action'][L]} "
                         f"({tl}: {st['timeline'][L]})")
        es = sc["evidence_status"]
        es_label = es["label"] if L == "en" else K.EVIDENCE_HU[es["label"]]
        out.append(dict(
            id=sc["id"],
            title=sc["title"][L],
            goal=sc["goal"][L],
            mechanism=[m["text"][L] + ev_tag(m["evidence"], L)
                       for m in sc["mechanism"]],
            evidence_status=f"{es_label} — {es['note'][L]}",
            assumptions=[a[L] for a in sc["assumptions"]],
            expected_benefits=[b["text"][L] + ev_tag(b["evidence"], L)
                               for b in sc["expected_benefits"]],
            equity_impact=sc["equity_impact"][L],
            cost_categories=[c[L] for c in sc["cost_categories"]],
            implementation_steps=steps,
            political_risks=[r[L] for r in sc["political_risks"]],
            uncertainties=[u["text"][L] + _conf(u, L)
                           for u in sc["uncertainties"]],
        ))
    return {"scenarios": out}


def scenarios_md(view, lang):
    """Render a legacy-shape scenarios view (see scenario_view) to markdown."""
    title = ("# Policy scenarios" if lang == "en"
             else "# Szakpolitikai forgatókönyvek")
    lines = [title, ""]
    for s in view["scenarios"]:
        lines.append(f"## {s['id']} — {s['title']}")
        for key in K.SCENARIO_FIELDS:
            label = K.FIELD_LABELS[key][0 if lang == "en" else 1]
            lines.append(f"**{label}**")
            v = s[key]
            if isinstance(v, list):
                lines += [f"- {item}" for item in v]
            else:
                lines.append(v)
            lines.append("")
    return "\n".join(lines)


# -- critics ------------------------------------------------------------------

def critic_md(name, o):
    lines = [f"# Critique: {name}", ""]
    for ob in o["objections"]:
        lines.append(f"## {ob['scenario']}.{ob['field']}")
        lines.append(f"Objection: {ob['objection']}")
        lines.append(f"Severity: {ob['severity']}")
        lines.append(f"Suggested revision: {ob['suggested_revision']}")
        lines.append("")
    return "\n".join(lines)


# -- synthesis ----------------------------------------------------------------

def _holders(side):
    return ", ".join(side["holders"])


def synthesis_md(o, lang="en"):
    L = lang
    if L == "en":
        H = dict(title="# Synthesis", overview="## Overview",
                 dmap="## Disagreement map", why="Why",
                 agree="## What the experts agree on",
                 minority="## Minority positions", mark=" (minority)")
    else:
        H = dict(title="# Szintézis", overview="## Áttekintés",
                 dmap="## Nézeteltérés-térkép", why="Miért",
                 agree="## Amiben a szakértők egyetértenek",
                 minority="## Különvélemények", mark=" (kisebbségi)")
    lines = [H["title"], "", H["overview"], o["overview"][L], "", H["dmap"]]
    for dis in o["disagreements"]:
        lines.append(f"### {dis['topic'][L]}")
        for side in dis["sides"]:
            mark = H["mark"] if side["minority"] else ""
            lines.append(f"- **{_holders(side)}**{mark}: {side['position'][L]} "
                         f"{H['why']}: {side['rationale'][L]}")
        lines.append("")
    lines += [H["agree"]]
    for a in o["agreements"]:
        holders = f" ({', '.join(a['holders'])})" if a.get("holders") else ""
        lines.append(f"- {a['text'][L]}{ev_tag(a['evidence'], L)}{holders}")
    minority = [side for dis in o["disagreements"] for side in dis["sides"]
                if side["minority"]]
    if minority:
        lines += ["", H["minority"]]
        for side in minority:
            lines.append(f"- ({_holders(side)}) {side['position'][L]} — "
                         f"{side['rationale'][L]}")
    return "\n".join(lines) + "\n"


def frames_md(o, T, round_n):
    """Human-readable view of an emergent-framing proposal (issue #21) —
    the file the owner reads before approving the option space."""
    lines = [f"# Javasolt forgatókönyv-keretek — {T.title('hu')}", "",
             f"A(z) {round_n}. kör szakértői elemzéséből derivált opciótér "
             f"({len(o['frames'])} keret). EMBERI JÓVÁHAGYÁSRA VÁR: "
             "szerkeszd a frames.json-t, ha kell, majd futtasd: "
             f"`scripts/new_topic.py approve-frames --topic {T.slug}`.", ""]
    for f in o["frames"]:
        lines += [f"## {f['id']} — {f['title']['hu']}",
                  f"*{f['title']['en']}*", "",
                  f"- Scope (HU): {f['scope']['hu']}",
                  f"- Scope (EN): {f['scope']['en']}", ""]
    lines += ["## Elvetett keretezések (audit)", ""]
    for r in o["rejected_framings"]:
        lines += [f"- {r['framing']['hu']} — **indok:** {r['reason']['hu']}"]
    return "\n".join(lines) + "\n"


def rejected_md(o):
    lines = ["# Rejected framings", "",
             "Candidate framings generated per scenario; one selected, the "
             "rest recorded here with the reason for rejection."]
    for sc in o["scenarios"]:
        lines.append(f"\n## {sc['id']}")
        lines.append(f"- CHOSEN: {sc['chosen']}")
        for r in sc["rejected"]:
            lines.append(f"- REJECTED: {r['framing']} — reason: {r['reason']}")
    return "\n".join(lines) + "\n"


# -- discourse ----------------------------------------------------------------

def grade_line(g):
    """One evidence-layer grade rendered in the ledger's legacy line format."""
    if g["status"] == "not_registry_backed":
        return f"[not registry-backed — treat as model knowledge] {g['note']}"
    return f"[evidence: {g['status']} — {g['source']}] {g['note']}"


def grades_dict(o):
    return {g["cluster_id"]: grade_line(g) for g in o["grades"]}


# -- brief --------------------------------------------------------------------

BRIEF_HEADERS = {
    "en": ["## What we know", "## What we consider likely",
           "## Where experts disagree", "## What we don't know",
           "## What could be done", "## What each option costs",
           "## What research could resolve", "## What people must decide",
           "## What to verify with real stakeholders",
           "## Where the red herrings are"],
    "hu": ["## Amit már tudunk", "## Amit valószínűnek tartunk",
           "## Amiben nincs szakértői egyetértés", "## Amit nem tudunk",
           "## Mit lehetne tenni", "## Mi az egyes alternatívák ára",
           "## Mit lehet még kutatással eldönteni",
           "## Mit kell embereknek eldönteniük",
           "## Mit kell valódi stakeholderekkel ellenőrizni",
           "## Hol vannak a gumicsontok"],
}

def brief_title(lang):
    """The brief's H1 comes from the topic's problem brief (D-35 — the old
    BRIEF_TITLE literal was question-specific)."""
    from . import topic
    return topic.current().brief_title(lang)


SCENARIO_KEY_HEADER = {"en": "## Scenario key (full detail: scenarios.en.md)",
                       "hu": "## Forgatókönyv-kulcs (részletesen: scenarios.hu.md)"}
MINORITY_HEADER = {"en": "## Minority positions", "hu": "## Különvélemények"}


def brief_md(o, lang):
    L = lang
    H = BRIEF_HEADERS[L]
    ev_label = "evidence" if L == "en" else "bizonyíték"
    why = "Why" if L == "en" else "Miért"
    lines = [brief_title(L), "", o["intro"][L], "", SCENARIO_KEY_HEADER[L]]
    for k in o["scenario_key"]:
        lines.append(f"- {k['id']} — {k['title'][L]}")

    lines += ["", H[0]]
    for it in o["what_we_know"]:
        ev = it["evidence"] if L == "en" else K.EVIDENCE_HU[it["evidence"]]
        lines.append(f"- {it['text'][L]} [{it['kind']}] ({ev_label}: {ev})")

    lines += ["", H[1]]
    lines += [f"- {it['text'][L]} [{it['kind']}]"
              for it in o["what_we_consider_likely"]]

    lines += ["", H[2]]
    for dis in o["where_experts_disagree"]:
        lines.append(f"### {dis['topic'][L]}")
        for p in dis["positions"]:
            mark = " (minority)" if p["minority"] else ""
            lines.append(f"- **{', '.join(p['holders'])}**{mark}: "
                         f"{p['position'][L]} [value] {why}: {p['why'][L]}")

    lines += ["", H[3]]
    lines += [f"- {it['text'][L]} [{it['kind']}]" for it in o["what_we_dont_know"]]

    lines += ["", H[4]]
    lines += [f"- **{it['scenario_id']} — {it['title'][L]}**: {it['summary'][L]}"
              for it in o["what_could_be_done"]]

    lines += ["", H[5]]
    lines += [f"- **{it['scenario_id']}**: {it['text'][L]} [{it['kind']}]"
              for it in o["what_each_option_costs"]]

    lines += ["", H[6]]
    lines += [f"- {it[L]}" for it in o["what_research_could_resolve"]]

    lines += ["", H[7]]
    lines += [f"- {it[L]} [value]" for it in o["what_people_must_decide"]]

    lines += ["", H[8]]
    for r in o["stakeholder_responses"]:
        lines.append(f"- {r['cluster_id']} ({r['restatement'][L]}): "
                     f"{r['response_type']} — {r['reason'][L]}")

    lines += ["", H[9]]
    if o["attention_sinks"]:
        lines += [f"- {a['cluster_id']}: {a['text'][L]}"
                  for a in o["attention_sinks"]]
    else:
        lines.append("- none flagged this round" if L == "en"
                     else "- ebben a körben nincs megjelölve ilyen")

    if o["minority_positions"]:
        lines += ["", MINORITY_HEADER[L]]
        lines += [f"- ({', '.join(m['holders'])}) {m['position'][L]} — "
                  f"{m['rationale'][L]}" for m in o["minority_positions"]]
    return "\n".join(lines) + "\n"


# -- meta critique --------------------------------------------------------------

def meta_md(o, round_n):
    g = o["gaming_judgment"]
    lines = [f"# Meta-critique — round {round_n}", "",
             "## Scope",
             "This evaluates the agent SYSTEM (agents, workflow, critique "
             "quality), not the policy content.", "",
             "## Agent performance"]
    lines += [f"- {x}" for x in o["agent_performance"]]
    rc = o["removal_candidates"]
    lines.append("- removal candidates: " + ("; ".join(rc) if rc else "none"))
    lines += ["", "## Workflow"]
    lines += [f"- {x}" for x in o["workflow"]]
    lines += ["", "## Critique quality"]
    lines += [f"- {x}" for x in o["critique_quality"]]
    lines += ["", "## Gaming judgment (explicit)"]
    if g["verdict"] == "NO_BASELINE":
        lines.append("- First scored round; there is no gain to certify as "
                     "GENUINE or RUBRIC-GAMING yet.")
    else:
        lines.append(f"- Verdict: {g['verdict']}")
    lines += [f"- {x}" for x in g["reasons"]]
    lines += ["", "## Translation consistency"]
    lines += [f"- {x}" for x in o["translation_consistency"]]
    return "\n".join(lines) + "\n"
