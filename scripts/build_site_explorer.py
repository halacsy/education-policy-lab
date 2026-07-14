#!/usr/bin/env python3
"""Generate the public scenario explorer (site/explorer.html): for each policy
scenario, drill from the headline claim down to the expert record, the
critics' objections, the preserved disagreement, and the underlying evidence.

Reads ONLY the canonical round's real artifacts (outputs/final/,
outputs/iterations/round_<last>/) — nothing here is authored by hand, so the
page can never drift from what the agents actually produced. Standard
library only; run by the Pages workflow on every deploy.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Per-topic outputs (D-35). Default: the config default_topic; a --topic
# argument selects another one (the topic browser builds every topic).
import argparse as _argparse

_ap = _argparse.ArgumentParser()
_ap.add_argument("--topic", default=None)
_ARGS, _ = _ap.parse_known_args()
_CFG = json.loads((ROOT / "config" / "system_config.json")
                  .read_text(encoding="utf-8"))
SLUG = _ARGS.topic or _CFG["default_topic"]
TOPIC_DIR = ROOT / "topics" / SLUG
FINAL = ROOT / "outputs" / "topics" / SLUG / "final"
ITER = ROOT / "outputs" / "topics" / SLUG / "iterations"

FIELD_KEYS = ["goal", "mechanism", "evidence_status", "assumptions",
              "expected_benefits", "equity_impact", "cost_categories",
              "implementation_steps", "political_risks", "uncertainties"]
FIELD_LABELS = {
    "goal": ("Cél", "Goal"),
    "mechanism": ("Mechanizmus", "Mechanism"),
    "evidence_status": ("Bizonyítékstátusz", "Evidence status"),
    "assumptions": ("Feltevések", "Assumptions"),
    "expected_benefits": ("Várható előnyök", "Expected benefits"),
    "equity_impact": ("Méltányossági hatás", "Equity impact"),
    "cost_categories": ("Költségkategóriák", "Cost categories"),
    "implementation_steps": ("Megvalósítási lépések", "Implementation steps"),
    "political_risks": ("Politikai kockázatok", "Political risks"),
    "uncertainties": ("Bizonytalanságok", "Uncertainties"),
}
SEV_HU = {"high": "magas", "medium": "közepes", "low": "alacsony"}

OBJ_SPLIT_RE = re.compile(r"\n(?=## S\d+\.)")
OBJ_HEAD_RE = re.compile(r"^## (S\d+)\.([a-z_]+)")
FIELD_RE = re.compile(r"^(Objection|Severity|Suggested revision):\s*(.*)$", re.M)

# Each axis in the brief's "## Where experts disagree" is one bullet:
# "- **<axis title>**: <prose naming who holds what, and why>". The title
# itself usually already states the opposition ("Abolish/restrict vs.
# retain"); no majority/minority framing exists here (the system does not
# decide by vote — see docs/mission.md) — every axis is just a fork.
BRIEF_DISAGREE_RE = re.compile(r"^- \*\*(.+?)\*\*:\s*(.+)$", re.M)
CAMP_SPLIT_PATTERNS = [
    re.compile(r"\.\s+Against this,\s*"),
    re.compile(r",\s+while\s+"),
    re.compile(r";\s+"),
]

POSITION_RE = re.compile(r"## Position\s*\n(.+?)(?:\n##|\Z)", re.S)


def _split_camps(body):
    """Best-effort split of one axis's prose into two opposing camps; the
    connector phrase varies (the writer isn't given a fixed template), so
    try a few in priority order and fall back to one unsplit block."""
    for pat in CAMP_SPLIT_PATTERNS:
        parts = pat.split(body, maxsplit=1)
        if len(parts) == 2 and len(parts[0].strip()) > 25 and len(parts[1].strip()) > 25:
            return parts[0].strip(), parts[1].strip()
    return None


def parse_brief_disagreement(brief_text):
    m = re.search(r"## Where experts disagree\s*\n+(.*?)(?:\n+## |\Z)",
                  brief_text, re.S)
    body = m.group(1) if m else ""
    axes = []
    for tm in BRIEF_DISAGREE_RE.finditer(body):
        title, prose = tm.group(1).strip(), tm.group(2).strip()
        title_parts = re.split(r"\s+vs\.?\s+", title, maxsplit=1)
        camps = _split_camps(prose)
        axes.append(dict(
            title=title,
            title_left=title_parts[0] if len(title_parts) == 2 else None,
            title_right=title_parts[1] if len(title_parts) == 2 else None,
            camp_a=camps[0] if camps else prose,
            camp_b=camps[1] if camps else None,
        ))
    return axes


def _highlight_experts(text, expert_names, e):
    """Turn bare expert-agent names inside prose into clickable chips (the
    same #expert-<name> anchors expert_card() below defines) — this is how
    a reader sees WHICH camp an expert is actually in, inline."""
    escaped = e(text)
    if not expert_names:
        return escaped
    names = sorted(expert_names, key=len, reverse=True)
    pat = re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b")
    return pat.sub(
        lambda m: f'<a class="expert-chip" href="#expert-{m.group(1)}">{m.group(1)}</a>',
        escaped)


def last_round():
    rounds = sorted(int(p.name.split("_")[1]) for p in ITER.glob("round_*"))
    return rounds[-1]


def parse_critic(text, critic_name):
    """-> list of dicts: scenario, field, objection, severity, fix."""
    out = []
    for chunk in OBJ_SPLIT_RE.split(text):
        m = OBJ_HEAD_RE.match(chunk.strip())
        if not m:
            continue
        fields = dict(FIELD_RE.findall(chunk))
        out.append(dict(critic=critic_name, scenario=m.group(1),
                        field=m.group(2), objection=fields.get("Objection", "").strip(),
                        severity=fields.get("Severity", "").strip().lower(),
                        fix=fields.get("Suggested revision", "").strip()))
    return out



def parse_expert(text):
    m = POSITION_RE.search(text)
    position = m.group(1).strip() if m else ""
    return position


# -- argument ledger (D-29 societal-discourse layer) --------------------------

LEDGER_VOICE_RE = re.compile(r"^- \*\*(\w+)\*\* — (.+?) \[(.+?)\] — (.*)$", re.M)
LEDGER_CLUSTER_RE = re.compile(
    r"^- \*\*(A\d+)\*\* \((S\d+), (\w+), (\w+)\): (.*?) — felvetette: (.*)$", re.M)
LEDGER_RESP_RE = re.compile(r"^- \*\*(\w+)\*\* → (A\d+): (.*) \(kimenetel: (\w+)\)$", re.M)

STANCE_CLASS = {"támogatja": "sup", "ellenzi": "opp",
                "feltételesen támogatja": "cond", "nincs álláspontja": "nop"}


def _ledger_section(text, header):
    m = re.search(rf"{re.escape(header)}\s*\n(.*?)(?=\n## |\Z)", text, re.S)
    return m.group(1) if m else ""


def parse_ledger(rd):
    p = rd / "argument_ledger.hu.md"
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    matrix = {}
    for chunk in re.split(r"(?=^### )", _ledger_section(text, "## Álláspont-mátrix"),
                          flags=re.M):
        sm = re.match(r"### (S\d+)", chunk.strip())
        if not sm:
            continue
        rows = []
        for m in LEDGER_VOICE_RE.finditer(chunk):
            arg, _, cond = m.group(4).partition(" Feltétel: ")
            rows.append(dict(voice=m.group(1), stance=m.group(2).strip(),
                             label=m.group(3), argument=arg.strip(),
                             condition=cond.strip()))
        matrix[sm.group(1)] = rows
    clusters = [dict(id=m.group(1), scenario=m.group(2), kind=m.group(3),
                     side=m.group(4), claim=m.group(5).strip(),
                     raised_by=[v.strip() for v in m.group(6).split(",")])
                for m in LEDGER_CLUSTER_RE.finditer(
                    _ledger_section(text, "## Érvklaszterek"))]
    recipro = [dict(voice=m.group(1), cluster=m.group(2),
                    response=m.group(3).strip(), outcome=m.group(4))
               for m in LEDGER_RESP_RE.finditer(
                   _ledger_section(text, "## Reciprocitás-kör"))]
    return dict(matrix=matrix, clusters=clusters, recipro=recipro)


def parse_brief_responses(brief_hu_text):
    body = _ledger_section(brief_hu_text,
                           "## Mit kell valódi stakeholderekkel ellenőrizni")
    out = {}
    for m in re.finditer(r"^- (A\d+)\s*(.*)$", body, re.M):
        out[m.group(1)] = m.group(2).strip().lstrip("(").strip()
    return out


# -- structured discourse artifacts (D-34: JSON is the source of truth) -------

VERDICT_HU = {
    "evidence_answerable": "evidenciával megválaszolható",
    "policy_design_fixable": "tervezéssel kezelhető",
    "communication_fixable": "kommunikációval kezelhető",
    "value_conflict": "értékkonfliktus",
    "irreducible_tradeoff": "feloldhatatlan trade-off",
    "needs_more_info": "több információ kell",
    "not_decision_relevant": "nem döntésreleváns",
}
# 7 verdict types -> 3 semantic groups: fixable (evidence green),
# human decision needed (rust), open/parked (muted)
VERDICT_GROUP = {
    "evidence_answerable": "fix", "policy_design_fixable": "fix",
    "communication_fixable": "fix",
    "value_conflict": "human", "irreducible_tradeoff": "human",
    "needs_more_info": "open", "not_decision_relevant": "open",
}
KIND_HU = {"fact": "tény", "value": "érték", "mixed": "vegyes"}
SIDE_HU = {"pro": "mellette", "con": "ellene", "conditional": "feltételes"}
REL_HU = {"high": "magas", "medium": "közepes", "low": "alacsony"}
DECOMP_FIELDS = [("interest", "Kinek az érdeke"), ("value", "Milyen érték ütközik"),
                 ("fear", "Milyen félelem hajtja"), ("assumption", "Milyen feltevésre épül"),
                 ("empirical_uncertainty", "Empirikus bizonytalanság")]


def load_structured_discourse(rd):
    """Cluster data straight from the D-34 JSON artifacts (no md parsing).
    Returns None for pre-D-34 rounds."""
    amap = rd / "discourse" / "argument_map.json"
    brief = rd / "brief.json"
    if not (amap.exists() and brief.exists()):
        return None
    sys.path.insert(0, str(ROOT / "scripts"))
    from lab.render import grades_dict, project
    clusters = project(json.loads(amap.read_text(encoding="utf-8"))["clusters"], "hu")
    grades_p = rd / "discourse" / "argument_grades.json"
    grades = grades_dict(json.loads(grades_p.read_text(encoding="utf-8"))) \
        if grades_p.exists() else {}
    recipro = {}
    for rp in sorted((rd / "discourse" / "responses").glob("*.json")):
        obj = project(json.loads(rp.read_text(encoding="utf-8")), "hu")
        for r in obj.get("responses", []):
            recipro.setdefault(r["cluster"], []).append(
                dict(voice=obj.get("voice", rp.stem), response=r["response"],
                     outcome=r["outcome"]))
    b = project(json.loads(brief.read_text(encoding="utf-8")), "hu")
    verdicts = {r["cluster_id"]: r for r in b.get("stakeholder_responses", [])}
    return dict(clusters=clusters, grades=grades, recipro=recipro,
                verdicts=verdicts)


def clusters_section_html(sd):
    """Grouped, scannable cluster section: per-scenario groups with a
    verdict spine, one disclosure row per argument."""
    e = html.escape
    by_scen = {}
    for c in sd["clusters"]:
        by_scen.setdefault(c["scenario"], []).append(c)

    def verdict_of(c):
        v = sd["verdicts"].get(c["id"])
        return v["response_type"] if v else None

    def is_gumicsont(c):
        attn = c.get("attention", {})
        return bool(attn.get("high_attention")) and \
            c.get("decision_relevance") == "low"

    counts = {"fix": 0, "human": 0, "open": 0}
    for c in sd["clusters"]:
        vt = verdict_of(c)
        if vt:
            counts[VERDICT_GROUP[vt]] += 1
    legend = f"""
    <div class="v-legend">
      <span><i class="v-dot v-fix"></i>kezelhető (evidenciával / tervezéssel / kommunikációval): <b>{counts['fix']}</b></span>
      <span><i class="v-dot v-human"></i>emberi döntést kér (értékkonfliktus / trade-off): <b>{counts['human']}</b></span>
      <span><i class="v-dot v-open"></i>nyitott / nem döntésreleváns: <b>{counts['open']}</b></span>
    </div>"""

    groups = []
    for sid in sorted(by_scen):
        cs = by_scen[sid]
        spine = "".join(
            f'<i class="v-seg v-{VERDICT_GROUP.get(verdict_of(c), "open")}" '
            f'title="{e(c["id"])}: {e(VERDICT_HU.get(verdict_of(c), "nincs válasz"))}"></i>'
            for c in cs)
        rows = []
        for c in cs:
            v = sd["verdicts"].get(c["id"])
            vt = v["response_type"] if v else None
            badge = (f'<span class="v-badge v-{VERDICT_GROUP[vt]}">'
                     f'{e(VERDICT_HU[vt])}</span>' if vt else "")
            gumi = ('<span class="gumi" title="Sok figyelmet kap, de nem '
                    'változtatna a döntésen">gumicsont</span>'
                    if is_gumicsont(c) else "")
            decomp = "".join(
                f'<div><dt>{label}</dt><dd>{e(c.get(f, ""))}</dd></div>'
                for f, label in DECOMP_FIELDS if str(c.get(f, "")).strip())
            affected = ", ".join(c.get("affected", []))
            if affected:
                decomp += f'<div><dt>Kiket érint</dt><dd>{e(affected)}</dd></div>'
            decomp += (f'<div><dt>Döntésrelevancia</dt>'
                       f'<dd>{e(REL_HU.get(c.get("decision_relevance"), ""))}</dd></div>')
            grade = sd["grades"].get(c["id"])
            grade_html = (f'<p class="cl-grade">Evidencia-réteg: {e(grade)}</p>'
                          if grade else "")
            rec_html = "".join(
                f'<p class="recipro"><b>{e(r["voice"])}</b> '
                f'({"fenntartja" if r["outcome"] == "maintain" else "módosítja"}): '
                f'{e(r["response"])}</p>' for r in sd["recipro"].get(c["id"], []))
            answer = ""
            if v:
                answer = (f'<p class="brief-resp"><b>A záróanyag válasza '
                          f'({e(VERDICT_HU[vt])}):</b> {e(v["reason"])}</p>')
            raised = "".join(f'<span class="expert-chip">{e(n)}</span> '
                             for n in c.get("raised_by", []))
            rows.append(f"""
      <details class="cluster-row">
        <summary><span class="cl-id">{e(c['id'])}</span>
          <span class="cl-claim">{e(c['claim'])}</span>
          {badge}{gumi}</summary>
        <div class="cl-body">
          <p class="note">Felvetette: {raised}· {e(KIND_HU.get(c['kind'], c['kind']))} állítás, {e(SIDE_HU.get(c['side'], c['side']))}</p>
          <dl class="cl-decomp">{decomp}</dl>
          {grade_html}{rec_html}{answer}
        </div>
      </details>""")
        groups.append(f"""
    <div class="cl-group">
      <div class="cl-group-head"><span class="id">{e(sid)}</span>
        <span class="cl-group-n">{len(cs)} érv</span>
        <span class="v-spine">{spine}</span></div>
      {''.join(rows)}
    </div>""")

    return (
        '<h3 style="margin-top:1.4rem">Érvklaszterek — és mi lett velük</h3>'
        '<p class="note">Fejszámlálás helyett érv-könyvelés: minden érvre a '
        'záróanyag köteles tételesen válaszolni. A válasz típusa mondja meg, '
        'mi viszi tovább az érvet: van, amit evidencia vagy tervezés kezel — '
        'és van, ami valódi értékválasztás, amit csak ember dönthet el. '
        'Kattints egy érvre a bontáshoz: kinek az érdeke, milyen félelem '
        'hajtja, mire épül, és ki hogyan válaszolt rá.</p>'
        + legend + "".join(groups))


def render_field(v):
    if isinstance(v, list):
        return "<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in v) + "</ul>"
    return f"<p>{html.escape(v)}</p>"


def _inline_md(line):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(line))


def md_html(text):
    """Minimal deterministic Markdown→HTML for agent artifacts (issue #8):
    #/##/### headings, - bullets, **bold**, blank-line paragraphs. Escaping
    happens first, so no artifact content reaches the page unescaped."""
    out, bullets = [], []

    def flush():
        if bullets:
            out.append("<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>")
            bullets.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("- "):
            bullets.append(_inline_md(line[2:]))
            continue
        flush()
        if not line:
            continue
        m = re.match(r"(#{1,4})\s+(.*)", line)
        if m:
            level = min(len(m.group(1)) + 3, 6)  # # -> h4 ... inside the card
            out.append(f"<h{level}>{_inline_md(m.group(2))}</h{level}>")
        else:
            out.append(f"<p>{_inline_md(line)}</p>")
    flush()
    return "".join(out)


def main():
    n = last_round()
    rd = ITER / f"round_{n:02d}"
    e = html.escape

    # D-34: scenarios.json is bilingual; project the legacy EN/HU views the
    # same way the pipeline renders them (no hand-authored content).
    sys.path.insert(0, str(ROOT / "scripts"))
    from lab.loadround import load_scenario_views
    scen_en, scen_hu = load_scenario_views(rd)
    hu_by_id = {s["id"]: s for s in scen_hu["scenarios"]}

    critics = {}
    all_objections = []
    for p in sorted((rd / "critic_outputs").glob("*.md")):
        if p.stem == "translation_checker":
            continue
        objs = parse_critic(p.read_text(encoding="utf-8"), p.stem)
        critics[p.stem] = objs
        all_objections.extend(objs)

    by_scenario_field = {}
    for o in all_objections:
        by_scenario_field.setdefault((o["scenario"], o["field"]), []).append(o)

    experts = {}
    for p in sorted((rd / "expert_outputs").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        experts[p.stem] = dict(position=parse_expert(text), full=text)

    brief_en = (rd / "brief.en.md").read_text(encoding="utf-8")
    disagreement = parse_brief_disagreement(brief_en)

    def sev_badge(sev):
        if not sev:
            return ""
        return (f'<span class="sev sev-{e(sev)}">{e(SEV_HU.get(sev, sev))}</span>')

    def objections_html(sid):
        blocks = []
        for field in FIELD_KEYS:
            objs = by_scenario_field.get((sid, field), [])
            if not objs:
                continue
            label_hu, _ = FIELD_LABELS[field]
            items = []
            for o in objs:
                fix = (f'<p class="fix"><b>Javasolt javítás:</b> {e(o["fix"])}</p>'
                       if o["fix"] else "")
                items.append(f"""
        <li class="objection">
          <div class="obj-head"><span class="critic-name">{e(o['critic'])}</span>{sev_badge(o['severity'])}</div>
          <p>{e(o['objection'])}</p>
          {fix}
        </li>""")
            blocks.append(f"""
      <div class="crit-field">
        <h4>{e(label_hu)}</h4>
        <ul class="obj-list">{''.join(items)}</ul>
      </div>""")
        return "".join(blocks) or '<p class="note">Nincs kifogás ehhez a forgatókönyvhöz ebben a körben.</p>'

    def scenario_card(s_en):
        sid = s_en["id"]
        s_hu = hu_by_id.get(sid, s_en)
        fields_html = []
        for field in FIELD_KEYS:
            label_hu, label_en = FIELD_LABELS[field]
            fields_html.append(f"""
        <div class="field">
          <h4>{e(label_hu)} <span class="en-label">{e(label_en)}</span></h4>
          {render_field(s_hu[field])}
        </div>""")
        n_obj = sum(1 for o in all_objections if o["scenario"] == sid)
        return f"""
    <details class="scenario" id="{e(sid)}">
      <summary>
        <span class="id">{e(sid)}</span>
        <span class="title">{e(s_hu['title'])}</span>
        <span class="count">{n_obj} kritikai észrevétel</span>
      </summary>
      <div class="scenario-body">
        <div class="fields">{''.join(fields_html)}</div>
        <div class="critique-panel">
          <h3>Kritikák mezőnként</h3>
          <p class="note">A rendszer kilenc kritikus-ágense minden állítást önállóan
          támad; minden észrevétel egy konkrét forgatókönyv-mezőt nevez meg.</p>
          {objections_html(sid)}
        </div>
      </div>
    </details>"""

    scenario_cards = "".join(scenario_card(s) for s in scen_en["scenarios"])

    expert_names = list(experts)

    def disagreement_card(d):
        camp_a_html = _highlight_experts(d["camp_a"], expert_names, e)
        if d["title_left"] and d["title_right"]:
            header_html = (f'<span class="axis-side">{e(d["title_left"])}</span>'
                          '<span class="axis-vs">vs.</span>'
                          f'<span class="axis-side">{e(d["title_right"])}</span>')
        else:
            header_html = f'<span class="axis-side">{e(d["title"])}</span>'
        if d["camp_b"]:
            camp_b_html = _highlight_experts(d["camp_b"], expert_names, e)
            body_html = (f'<div class="sides"><div class="side camp-a">'
                        f'<p class="position">{camp_a_html}</p></div>'
                        f'<div class="side camp-b"><p class="position">'
                        f'{camp_b_html}</p></div></div>')
        else:
            body_html = f'<p class="position axis-single">{camp_a_html}</p>'
        return f"""
    <div class="disagreement">
      <h3 class="axis-title">{header_html}</h3>
      {body_html}
    </div>"""

    disagreement_html = "".join(disagreement_card(d) for d in disagreement)

    def expert_card(name, data):
        body_html = md_html(data["full"])
        return f"""
    <details class="expert" id="expert-{e(name)}">
      <summary>
        <span class="expert-name">{e(name)}</span>
        <span class="expert-position">{e(data['position'][:140])}</span>
      </summary>
      <div class="expert-full">{body_html}</div>
    </details>"""

    expert_html = "".join(expert_card(k, v) for k, v in experts.items())

    # -- societal discourse: argument ledger (D-29) ---------------------------
    ledger = parse_ledger(rd)
    brief_resp = {}
    if ledger and (rd / "brief.hu.md").exists():
        brief_resp = parse_brief_responses(
            (rd / "brief.hu.md").read_text(encoding="utf-8"))

    def stance_chip(row):
        cls = STANCE_CLASS.get(row["stance"], "cond")
        cond = (f'<p class="cond-note"><b>Feltétel:</b> {e(row["condition"])}</p>'
                if row["condition"] else "")
        return f"""
        <div class="voice-row">
          <span class="voice-name">{e(row['voice'])}</span>
          <span class="stance stance-{cls}">{e(row['stance'])}</span>
          <span class="pos-label">{e(row['label'])}</span>
          <p>{e(row['argument'])}</p>
          {cond}
        </div>"""

    def discourse_section():
        if not ledger:
            return """
    <p class="note">Az érv-főkönyv a következő futástól jelenik meg itt: a
    diskurzus-réteg (D-29) most épült be a rendszerbe, a korábbi körök még a
    réteg nélkül futottak. A hangok, a szabályok és a válaszkötelezettség
    leírása: <a href="https://github.com/halacsy/education-policy-lab/blob/main/docs/workflow.md">docs/workflow.md</a>.</p>"""
        parts = []
        for sid, rows in ledger["matrix"].items():
            parts.append(f"""
    <details class="scenario">
      <summary><span class="id">{e(sid)}</span>
        <span class="title">Ki mit mond erről a forgatókönyvről?</span>
        <span class="count">{len(rows)} hang</span></summary>
      <div class="voice-grid">{''.join(stance_chip(r) for r in rows)}</div>
    </details>""")
        sd = load_structured_discourse(rd)
        if sd:
            return "".join(parts) + clusters_section_html(sd)
        # pre-D-34 fallback: clusters parsed from the rendered HU ledger
        cl_parts = []
        for c in ledger["clusters"]:
            resp = brief_resp.get(c["id"])
            resp_html = (f'<p class="brief-resp"><b>A brief válasza:</b> '
                         f'{e(resp)}</p>' if resp else "")
            rec = [r for r in ledger["recipro"] if r["cluster"] == c["id"]]
            rec_html = "".join(
                f'<p class="recipro"><b>{e(r["voice"])}</b> válasza '
                f'({e(r["outcome"])}): {e(r["response"])}</p>' for r in rec)
            cl_parts.append(f"""
      <div class="cluster">
        <div class="obj-head"><span class="critic-name">{e(c['id'])} · {e(c['scenario'])}</span>
          <span class="pos-label">{e(c['kind'])} / {e(c['side'])}</span></div>
        <p>{e(c['claim'])}</p>
        <p class="note">Felvetette: {e(', '.join(c['raised_by']))}</p>
        {rec_html}{resp_html}
      </div>""")
        return (parts and cl_parts and (
            "".join(parts)
            + '<h3 style="margin-top:1.4rem">Érvklaszterek — és mi lett velük</h3>'
            + '<p class="note">Fejszámlálás helyett érv-könyvelés: minden '
            'érvklaszterre a szakpolitikai összefoglaló köteles válaszolni '
            '(elfogad / elutasít / nyitva hagy — indoklással). A ténybeli '
            'állításokat az evidencia-réteg fokozatolja.</p>'
            + "".join(cl_parts))) or ""

    discourse_html = discourse_section()

    css = """
  :root {
    --paper:#F7F8F6; --ink:#1A2321; --muted:#5A6662; --line:#D8DDD9;
    --evidence:#1F6E5C; --evidence-bg:#EAF3F0; --dissent:#A34A26; --dissent-bg:#F6EBE5;
    --panel:#EEF1EE; --sev-high:#A34A26; --sev-medium:#95681E; --sev-low:#5A6662;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--paper); color:var(--ink);
          font-family:Charter,Georgia,'Times New Roman',serif; font-size:1.02rem; line-height:1.6; }
  .wrap { max-width:56rem; margin:0 auto; padding:0 1.25rem; }
  h1,h2,h3,h4 { font-family:-apple-system,'Helvetica Neue',Arial,sans-serif; line-height:1.2; text-wrap:balance; }
  h1 { font-size:clamp(1.5rem,4vw,2.05rem); font-weight:750; margin:0 0 .4rem; }
  h2 { font-size:1.2rem; font-weight:700; margin:2rem 0 1rem; }
  h3 { font-size:1.02rem; font-weight:700; margin:0 0 .6rem; }
  h4 { font-size:.88rem; font-weight:700; margin:0 0 .35rem; }
  p { margin:0 0 .7rem; }
  a { color:var(--evidence); }
  a:focus-visible, summary:focus-visible { outline:2px solid var(--evidence); outline-offset:2px; }
  header.top { border-bottom:1px solid var(--line); padding:1rem 0; }
  header.top .wrap { display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap;
                     font-family:ui-monospace,'SF Mono',Menlo,monospace; font-size:.8rem; }
  .eyebrow { font-family:ui-monospace,Menlo,monospace; font-size:.72rem; letter-spacing:.13em;
             text-transform:uppercase; color:var(--evidence); margin:0 0 .5rem; }
  section { padding:2rem 0; border-bottom:1px solid var(--line); }
  .lede { color:var(--muted); max-width:40rem; }

  details.scenario { background:#fff; border:1px solid var(--line); border-radius:8px;
                      margin-bottom:1rem; overflow:hidden; }
  details.scenario summary { list-style:none; cursor:pointer; padding:1rem 1.2rem;
                              display:flex; align-items:baseline; gap:.8rem; flex-wrap:wrap; }
  details.scenario summary::-webkit-details-marker { display:none; }
  details.scenario summary::before { content:"▸"; color:var(--evidence); margin-right:.2rem;
                                      transition:transform .15s; }
  details.scenario[open] summary::before { transform:rotate(90deg); }
  details.scenario .id { font-family:ui-monospace,Menlo,monospace; font-weight:700; color:var(--evidence); }
  details.scenario .title { font-family:-apple-system,'Helvetica Neue',Arial,sans-serif; font-weight:700; flex:1; }
  details.scenario .count { font-family:ui-monospace,Menlo,monospace; font-size:.74rem; color:var(--muted); }
  .scenario-body { border-top:1px solid var(--line); padding:1.1rem 1.2rem; display:grid; gap:1.5rem; }
  @media (min-width:800px) { .scenario-body { grid-template-columns:1.1fr .9fr; } }
  .field { margin-bottom:1rem; }
  .field .en-label { font-family:ui-monospace,Menlo,monospace; font-size:.68rem; color:var(--muted); font-weight:400; }
  .field ul { margin:0; padding-left:1.1rem; }
  .field li { margin-bottom:.3rem; }
  .critique-panel { background:var(--panel); border-radius:6px; padding:1rem; }
  .crit-field { margin-bottom:1rem; }
  .obj-list { list-style:none; margin:0; padding:0; display:grid; gap:.6rem; }
  li.objection { background:#fff; border:1px solid var(--line); border-radius:6px; padding:.6rem .8rem; font-size:.9rem; }
  .obj-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:.3rem; }
  .critic-name { font-family:ui-monospace,Menlo,monospace; font-size:.74rem; color:var(--muted); }
  .sev { font-family:ui-monospace,Menlo,monospace; font-size:.66rem; text-transform:uppercase;
         letter-spacing:.05em; padding:.08rem .4rem; border-radius:3px; color:#fff; }
  .sev-high { background:var(--sev-high); } .sev-medium { background:var(--sev-medium); } .sev-low { background:var(--sev-low); }
  .fix { font-size:.84rem; color:var(--muted); margin:.3rem 0 0; }

  .disagreement { margin-bottom:1.4rem; }
  .axis-title { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; font-size:1rem; margin:0 0 .5rem; }
  .axis-side { font-weight:700; }
  .axis-vs { font-size:.75rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted);
             background:var(--panel); padding:.1rem .5rem; border-radius:3px; }
  .sides { display:grid; gap:.8rem; }
  @media (min-width:700px) { .sides { grid-template-columns:1fr 1fr; } }
  .side { border-radius:6px; padding:.85rem 1rem; border:1px solid var(--line); background:#fff; }
  .side.camp-a { border-left:3px solid var(--evidence); }
  .side.camp-b { border-left:3px solid var(--dissent); }
  .expert-chip { font-family:ui-monospace,Menlo,monospace; font-size:.7rem; background:var(--panel);
                 padding:.1rem .45rem; border-radius:3px; text-decoration:none; color:var(--ink); }
  .expert-chip:hover { background:var(--evidence-bg); color:var(--evidence); }
  .position { font-size:.94rem; margin:0; }
  .axis-single { background:#fff; border:1px solid var(--line); border-radius:6px; padding:.85rem 1rem; }

  details.expert { background:#fff; border:1px solid var(--line); border-radius:6px; margin-bottom:.6rem; }
  details.expert summary { list-style:none; cursor:pointer; padding:.75rem 1rem; display:flex; gap:.8rem; align-items:baseline; }
  details.expert summary::-webkit-details-marker { display:none; }
  details.expert summary::before { content:"▸"; color:var(--evidence); }
  details.expert[open] summary::before { content:"▾"; }
  .expert-name { font-family:ui-monospace,Menlo,monospace; font-weight:700; font-size:.86rem; white-space:nowrap; }
  .expert-position { color:var(--muted); font-size:.88rem; }
  .expert-full { border-top:1px solid var(--line); padding:.9rem 1.1rem; font-size:.92rem; }
  .expert-full h4 { margin:.2rem 0 .6rem; font-size:1rem; }
  .expert-full h5 { margin:1rem 0 .35rem; font-size:.9rem; }
  .expert-full h6 { margin:.8rem 0 .3rem; font-size:.84rem; color:var(--muted); text-transform:uppercase; letter-spacing:.03em; }
  .expert-full p { margin:.35rem 0; }
  .expert-full ul { margin:.35rem 0 .6rem; padding-left:1.2rem; }
  .expert-full li { margin:.25rem 0; }

  .voice-grid { border-top:1px solid var(--line); padding:1rem 1.2rem; display:grid; gap:.8rem; }
  @media (min-width:800px) { .voice-grid { grid-template-columns:1fr 1fr; } }
  .voice-row { background:var(--panel); border-radius:6px; padding:.7rem .9rem; font-size:.9rem; }
  .voice-row p { margin:.35rem 0 0; }
  .voice-name { font-family:ui-monospace,Menlo,monospace; font-weight:700; font-size:.82rem; margin-right:.5rem; }
  .stance { display:inline-block; font-family:-apple-system,Arial,sans-serif; font-size:.74rem; font-weight:700;
            padding:.1rem .5rem; border-radius:999px; margin-right:.4rem; }
  .stance-sup { background:var(--evidence-bg); color:var(--evidence); }
  .stance-opp { background:var(--dissent-bg); color:var(--dissent); }
  .stance-cond { background:#F5EFDF; color:#95681E; }
  .stance-nop { background:#ECECEC; color:var(--muted); }
  .pos-label { font-family:ui-monospace,Menlo,monospace; font-size:.7rem; color:var(--muted); }
  .cond-note { font-size:.84rem; color:var(--muted); }
  .cluster { background:#fff; border:1px solid var(--line); border-radius:6px; padding:.8rem 1rem; margin-bottom:.7rem; }
  .cluster p { margin:.3rem 0; }
  .v-legend { display:flex; gap:1.2rem; flex-wrap:wrap; font-size:.82rem; color:var(--muted);
              background:var(--panel); border-radius:6px; padding:.6rem .9rem; margin:.8rem 0 1.1rem; }
  .v-dot { display:inline-block; width:.6rem; height:.6rem; border-radius:2px; margin-right:.35rem; vertical-align:baseline; }
  .v-fix { background:var(--evidence); } .v-human { background:var(--dissent); } .v-open { background:#9AA5A0; }
  .v-badge { font-family:-apple-system,Arial,sans-serif; font-size:.7rem; font-weight:700;
             padding:.12rem .5rem; border-radius:999px; white-space:nowrap; }
  .v-badge.v-fix { background:var(--evidence-bg); color:var(--evidence); }
  .v-badge.v-human { background:var(--dissent-bg); color:var(--dissent); }
  .v-badge.v-open { background:#ECECEC; color:var(--muted); }
  .gumi { font-family:ui-monospace,Menlo,monospace; font-size:.66rem; text-transform:uppercase;
          letter-spacing:.05em; color:var(--dissent); border:1px dashed var(--dissent);
          border-radius:3px; padding:.06rem .35rem; white-space:nowrap; }
  .cl-group { margin-bottom:1.4rem; }
  .cl-group-head { display:flex; align-items:center; gap:.7rem; margin-bottom:.5rem; }
  .cl-group-head .id { font-family:ui-monospace,Menlo,monospace; font-weight:700; color:var(--evidence); }
  .cl-group-n { font-family:ui-monospace,Menlo,monospace; font-size:.74rem; color:var(--muted); }
  .v-spine { display:flex; gap:2px; align-items:center; }
  .v-seg { width:.55rem; height:.85rem; border-radius:2px; display:inline-block; }
  .v-seg.v-fix { background:var(--evidence); } .v-seg.v-human { background:var(--dissent); }
  .v-seg.v-open { background:#C6CDC9; }
  details.cluster-row { background:#fff; border:1px solid var(--line); border-radius:6px; margin-bottom:.45rem; }
  details.cluster-row summary { list-style:none; cursor:pointer; display:flex; gap:.6rem;
                                align-items:baseline; padding:.55rem .8rem; }
  details.cluster-row summary::-webkit-details-marker { display:none; }
  details.cluster-row summary::before { content:"▸"; color:var(--evidence); flex:none; }
  details.cluster-row[open] summary::before { content:"▾"; }
  .cl-id { font-family:ui-monospace,Menlo,monospace; font-weight:700; font-size:.8rem; color:var(--muted); flex:none; }
  .cl-claim { flex:1; font-size:.92rem; }
  .cl-body { border-top:1px solid var(--line); padding:.8rem 1rem; }
  dl.cl-decomp { display:grid; gap:.5rem .9rem; margin:.7rem 0; }
  @media (min-width:700px) { dl.cl-decomp { grid-template-columns:1fr 1fr; } }
  dl.cl-decomp dt { font-family:-apple-system,Arial,sans-serif; font-size:.72rem; font-weight:700;
                    text-transform:uppercase; letter-spacing:.04em; color:var(--muted); margin:0 0 .1rem; }
  dl.cl-decomp dd { margin:0; font-size:.88rem; }
  .cl-grade { font-size:.84rem; color:var(--evidence); margin:.4rem 0; }
  .brief-resp { font-size:.88rem; background:var(--evidence-bg); border-radius:4px; padding:.4rem .6rem; }
  .recipro { font-size:.86rem; color:var(--muted); border-left:3px solid var(--line); padding-left:.6rem; }
  .note { font-size:.85rem; color:var(--muted); }
  nav.jump { display:flex; gap:1rem; font-family:ui-monospace,Menlo,monospace; font-size:.8rem; flex-wrap:wrap; }
  footer { padding:2rem 0 3rem; font-size:.85rem; color:var(--muted); }
"""

    body = f"""<!DOCTYPE html>
<html lang="hu">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forgatókönyv-feltáró — Education Policy Lab</title>
<meta name="description" content="Kattintva végigjárható: a szakpolitikai forgatókönyvektől a kritikákon és a nézeteltérés-térképen át a szakértői elemzésekig.">
<style>{css}</style>
</head>
<body>
<header class="top">
  <div class="wrap">
    <span><strong>EDUCATION POLICY LAB</strong> · forgatókönyv-feltáró</span>
    <span><a href="./">← főoldal</a> · <a href="knowledge.html">tudásbázis →</a></span>
  </div>
</header>

<section>
  <div class="wrap">
    <p class="eyebrow">Teljes átláthatóság</p>
    <h1>Kattints végig: állítástól a bizonyítékig</h1>
    <p class="lede">Minden forgatókönyv alatt megnyitható, mely kritikus mit
    kifogásolt melyik mezőben, hol volt valódi szakértői nézeteltérés — és ki
    állt melyik oldalon —, és a teljes szakértői elemzés, amiből a
    forgatókönyv épült. Az adat nem szerkesztett kivonat: közvetlenül a
    {n}. kör kimeneteiből generálódik.</p>
    <nav class="jump">
      <a href="#S1">S1</a><a href="#S2">S2</a><a href="#S3">S3</a><a href="#S4">S4</a>
      <a href="#nezetelteres">Nézeteltérés-térkép</a>
      <a href="#diskurzus">Társadalmi diskurzus</a>
      <a href="#szakertok">Szakértői elemzések</a>
    </nav>
  </div>
</section>

<section>
  <div class="wrap">
    <p class="eyebrow">Forgatókönyvek</p>
    <h2>A négy irány — nyisd meg a kritikákért</h2>
    {scenario_cards}
  </div>
</section>

<section id="nezetelteres">
  <div class="wrap">
    <p class="eyebrow">Megőrzött nézeteltérés</p>
    <h2>Hol nem ért egyet a szakértői testület — és ki melyik oldalon áll</h2>
    <p class="lede">A rendszer nem old fel vitát: minden témánál látszik a
    többségi és a kisebbségi álláspont is, indoklással. A szakértő nevére
    kattintva a teljes elemzése megnyílik lent.</p>
    {disagreement_html}
  </div>
</section>

<section id="diskurzus">
  <div class="wrap">
    <p class="eyebrow">Társadalmi diskurzus — érv-főkönyv</p>
    <h2>Ki mit mondana — és mi lett az érveikkel</h2>
    <p class="lede">A szakértői réteg mellett tíz érdek/érték-hang modellezi a
    társadalmi vitát: hat archetípus és négy valós szereplő. Minden álláspont
    episztemikus címkét visel (dokumentált forrással · értékekből modellezett ·
    nincs álláspont), és egyetlen felvetett érv sem tűnhet el válasz nélkül.</p>
    {discourse_html}
  </div>
</section>

<section id="szakertok">
  <div class="wrap">
    <p class="eyebrow">A teljes szakértői rekord</p>
    <h2>12 szakértő-ágens elemzése, teljes egészében</h2>
    {expert_html}
  </div>
</section>

<footer>
  <div class="wrap">
    <p>Generálva a repóból (<code>outputs/topics/{SLUG}/iterations/round_{n:02d}/</code>) minden
    publikáláskor. <a href="https://github.com/halacsy/education-policy-lab/tree/main/outputs/topics/{SLUG}/iterations/round_{n:02d}">Nyers adat a GitHubon</a>.</p>
  </div>
</footer>
</body>
</html>
"""
    page = body
    # per-topic output (D-35): the default topic ALSO keeps the legacy
    # site/explorer.html URL; every topic gets site/topics/<slug>/explorer.html
    out = ROOT / "site" / "topics" / SLUG / "explorer.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    if SLUG == _CFG["default_topic"]:
        (ROOT / "site" / "explorer.html").write_text(page, encoding="utf-8")
    print(f"wrote {out} (round {n}: {len(scen_en['scenarios'])} scenarios, "
          f"{len(all_objections)} objections, {len(disagreement)} disagreement "
          f"topics, {len(experts)} experts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
