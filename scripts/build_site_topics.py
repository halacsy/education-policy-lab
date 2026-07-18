#!/usr/bin/env python3
"""Generate the public topic pages (D-35, sprint deliverable 5).

For every topic in topics/*/topic.json:
- site/topics/<slug>/index.html — the topic's page: problem brief, frozen
  frames, run state, transparency (time/token/cost from the final
  cost_report.json), links to the explorer page and the raw record;
- the topic-card list injected between the TOPICS:START/END markers in
  site/index.html, plus the data-driven Atlas inventory between the
  ATLAS-INVENTORY markers. Both are regenerated on every deploy.

Run by the Pages workflow on every deploy — generated from repo data,
never hand-maintained. Standard library only (lab/ is local and stdlib).

Since the linkability pass the topic page also carries a "what the system
surfaced" section: the dilemmas, attention sinks and disagreement axes of
the topic's last round, each deep-linking into the explorer's anchors
(#cluster-<id>, #axis-<n>, #expert-<name>) via the shared lab/site_data
loaders — no hand-picked highlights, everything derived from the round
artifacts."""
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from lab.site_data import (DECOMP_FIELDS, KIND_HU, REL_HU, SIDE_HU,
                           VERDICT_HU, VERDICT_GROUP, canonical_expert_name,
                           debate_filename, dilemma_filename, expert_filename,
                           expert_label, is_gumicsont, last_round, list_experts,
                           load_structured_discourse,
                           load_structured_disagreements, topic_order)

TOPICS_DIR = ROOT / "topics"
OUT_ROOT = ROOT / "outputs" / "topics"

CSS = """
  :root { --paper:#F7F8F6; --ink:#1A2321; --muted:#5A6662; --line:#D8DDD9;
          --evidence:#1F6E5C; --dissent:#A34A26; --panel:#EEF1EE; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--paper); color:var(--ink);
         font-family: Charter, Georgia, 'Times New Roman', serif;
         font-size:1.0325rem; line-height:1.6; }
  .wrap { max-width: 52rem; margin: 0 auto; padding: 0 1.25rem; }
  h1,h2,h3 { font-family: -apple-system,'Helvetica Neue',Arial,sans-serif;
             line-height:1.15; text-wrap:balance; letter-spacing:-0.015em; }
  h1 { font-size: clamp(1.6rem,4.5vw,2.3rem); font-weight:750; margin:0 0 1rem; }
  h2 { font-size:1.35rem; font-weight:700; margin:0 0 1rem; }
  h3 { font-size:1.02rem; font-weight:700; margin:0 0 .5rem; }
  p { margin:0 0 1rem; }
  a { color: var(--evidence); text-underline-offset:2px; }
  .eyebrow { font-family: ui-monospace,'SF Mono',Menlo,monospace; font-size:.72rem;
             letter-spacing:.14em; text-transform:uppercase; color:var(--evidence);
             margin:0 0 .75rem; }
  header.site { border-bottom:1px solid var(--line); padding:1rem 0;
                font-family: ui-monospace,'SF Mono',Menlo,monospace; font-size:.8rem; }
  header.site .wrap { display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; }
  section { padding: 2.5rem 0; border-bottom: 1px solid var(--line); }
  .card { background:#fff; border:1px solid var(--line); border-radius:6px;
          padding:1.15rem 1.3rem; margin-bottom:1rem; }
  .card .id { font-family: ui-monospace,Menlo,monospace; font-weight:700;
              color:var(--evidence); margin-right:.5rem; }
  .note { font-size:.85rem; color: var(--muted); }
  table { border-collapse: collapse; width:100%; font-size:.9rem; background:#fff; }
  th,td { padding:.5rem .75rem; border-bottom:1px solid var(--line); text-align:left; }
  tr:last-child td { border-bottom:none; }
  .tablebox { overflow-x:auto; border:1px solid var(--line); border-radius:6px; }
  footer { padding:2rem 0 3rem; font-size:.85rem; color:var(--muted); }
  nav.topicnav { border-bottom:1px solid var(--line); background:var(--panel);
                 font-family: ui-monospace,'SF Mono',Menlo,monospace; font-size:.78rem; }
  nav.topicnav .wrap { display:flex; justify-content:space-between; align-items:baseline;
                       gap:1rem; padding-top:.5rem; padding-bottom:.5rem; }
  nav.topicnav a { text-decoration:none; }
  nav.topicnav a:hover { text-decoration:underline; }
  .cta { display:inline-block; background:var(--evidence); color:#fff;
         font-family:-apple-system,'Helvetica Neue',Arial,sans-serif; font-weight:700;
         font-size:.95rem; padding:.55rem 1.15rem; border-radius:4px;
         text-decoration:none; margin:.2rem 0 .4rem; }
  .cta:hover { opacity:.92; }
  ul.findings { list-style:none; margin:0 0 1rem; padding:0; }
  ul.findings li { background:#fff; border:1px solid var(--line); border-radius:6px;
                   padding:.6rem .85rem; margin-bottom:.5rem; font-size:.92rem; }
  ul.findings a { text-decoration:none; }
  ul.findings a:hover { text-decoration:underline; }
  .chip { display:inline-block; font-family:ui-monospace,'SF Mono',Menlo,monospace;
          font-size:.74rem; background:var(--panel); border:1px solid var(--line);
          padding:.12rem .5rem; border-radius:3px; text-decoration:none;
          color:var(--ink); margin:0 .25rem .35rem 0; }
  .chip:hover { background:#fff; color:var(--evidence); }
  .tally { display:flex; gap:1.2rem; flex-wrap:wrap; font-size:.85rem; color:var(--muted);
           background:var(--panel); border-radius:6px; padding:.6rem .9rem; margin:0 0 1rem; }
  .tally b { color:var(--ink); }
"""


def esc(x):
    return html.escape(str(x), quote=True)


def topic_state(slug):
    """Run state from the committed outputs: era rounds, last total,
    cost report (None when the topic has not run yet)."""
    base = OUT_ROOT / slug
    state = {"rounds": 0, "last_total": None, "cost": None,
             "has_final": (base / "final" / "final_brief.hu.md").exists()}
    it = base / "iterations"
    if it.exists():
        cfg = json.loads((TOPICS_DIR / slug / "topic.json").read_text(encoding="utf-8"))
        era = cfg.get("evaluation", {}).get("era_start_round", 1)
        rounds = sorted(int(p.name.split("_")[1]) for p in it.glob("round_*")
                        if int(p.name.split("_")[1]) >= era)
        state["rounds"] = len(rounds)
        if rounds:
            ev = it / f"round_{rounds[-1]:02d}" / "evaluation.json"
            if ev.exists():
                state["last_total"] = json.loads(
                    ev.read_text(encoding="utf-8")).get("total")
    cr = base / "final" / "cost_report.json"
    if cr.exists():
        state["cost"] = json.loads(cr.read_text(encoding="utf-8"))
    return state


def fmt_dur(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h} ó {m} p" if h else f"{m} p {s} mp"


def cost_line(state):
    c = state["cost"]
    if not c or not c.get("has_data"):
        return ("feldolgozási idő/költség: erre az érára nincs mért adat "
                "(a mérés a következő teljes körtől él)")
    return (f"feldolgozás: {fmt_dur(c['wall_clock_s'])} · "
            f"{c['total_tokens']:,} token · ~${c['total_usd']:.2f} USD "
            "(becslés)").replace(",", " ")


STATUS_HU = {"active": "aktív", "draft": "előkészítés alatt",
             "final": "lezárva"}

DILEMMA_CAP = 6
REL_ORDER = {"high": 0, "medium": 1, "low": 2}


def load_findings(slug, lang="hu"):
    """The last round's structured discourse record for the "what the
    system surfaced" section; None when the topic has no D-34 round yet."""
    it = OUT_ROOT / slug / "iterations"
    if not it.exists():
        return None
    n = last_round(it)
    if n is None:
        return None
    rd = it / f"round_{n:02d}"
    sd = load_structured_discourse(rd, lang)
    if not sd:
        return None
    return dict(round=n, sd=sd,
                axes=load_structured_disagreements(rd, lang) or [],
                experts=list_experts(rd))


def findings_block(f):
    """Deep-linking highlights section, fully derived from round data:
    verdict tally, human-decision dilemmas, attention sinks (gumicsont),
    disagreement axes, expert record — every item an anchor into
    explorer.html (the anchors are minted by build_site_explorer from the
    same lab/site_data loaders)."""
    if not f:
        return ""
    sd = f["sd"]
    counts = {"fix": 0, "human": 0, "open": 0}
    for c in sd["clusters"]:
        v = sd["verdicts"].get(c["id"])
        if v:
            counts[VERDICT_GROUP[v["response_type"]]] += 1
    tally = f"""    <div class="tally">
      <span>felvetett érv: <b>{len(sd['clusters'])}</b></span>
      <span>evidenciával/tervezéssel kezelhető: <b>{counts['fix']}</b></span>
      <span>emberi (érték)döntést kér: <b>{counts['human']}</b></span>
      <span>nyitott / nem döntésreleváns: <b>{counts['open']}</b></span>
    </div>"""

    dil = [(c, sd["verdicts"][c["id"]]) for c in sd["clusters"]
           if sd["verdicts"].get(c["id"])
           and VERDICT_GROUP[sd["verdicts"][c["id"]]["response_type"]] == "human"]
    dil.sort(key=lambda cv: (
        0 if cv[1]["response_type"] == "irreducible_tradeoff" else 1,
        REL_ORDER.get(cv[0].get("decision_relevance"), 3), cv[0]["id"]))
    dil_items = "\n".join(
        f'      <li><a href="explorer.html#cluster-{esc(c["id"])}">'
        f'<strong>{esc(c["id"])}</strong> · {esc(c["claim"])}</a><br>'
        f'<span class="note">{esc(VERDICT_HU[v["response_type"]])} — '
        f'a záróanyag indoklással válaszol rá (kattints)</span></li>'
        for c, v in dil[:DILEMMA_CAP])
    dil_more = (f'<p class="note">…és további {len(dil) - DILEMMA_CAP} '
                f'hasonló dilemma a feltáróban.</p>'
                if len(dil) > DILEMMA_CAP else "")

    gumik = [c for c in sd["clusters"] if is_gumicsont(c)]
    gumi_html = ""
    if gumik:
        gumi_items = "\n".join(
            f'      <li><a href="explorer.html#cluster-{esc(c["id"])}">'
            f'<strong>{esc(c["id"])}</strong> · {esc(c["claim"])}</a><br>'
            f'<span class="note">{esc(sd["sinks"].get(c["id"], ""))}</span></li>'
            for c in gumik)
        gumi_html = f"""    <h3>Gumicsont-érvek — sok figyelem, kevés döntési tét</h3>
    <p class="note">A vitában nagy figyelmet kapó érvek, amelyek megoldása
    a rendszer elemzése szerint nem változtatna azon, melyik irányt érdemes
    választani.</p>
    <ul class="findings">
{gumi_items}
    </ul>"""

    axes_html = ""
    if f["axes"]:
        axis_items = "\n".join(
            f'      <li><a href="explorer.html#axis-{i + 1}">{esc(ax["topic"])}</a></li>'
            for i, ax in enumerate(f["axes"]))
        axes_html = f"""    <h3>Ahol a szakértői panel nem ért egyet</h3>
    <p class="note">A rendszer nem szavaztat és nem simítja el a vitát:
    ezek a kérdések nyitva maradnak, mindkét oldal indoklásával.</p>
    <ul class="findings">
{axis_items}
    </ul>"""

    expert_chips = "".join(
        f'<a class="chip" href="szakerto/{esc(expert_filename(n))}">'
        f'{_both({"hu": expert_label(n, "hu"), "en": expert_label(n, "en")})}</a>'
        for n in f["experts"])

    return f"""<section>
  <div class="wrap">
    <p class="eyebrow">Amit a rendszer feltárt — {f['round']}. kör</p>
    <h2>Dilemmák és érdekességek, közvetlenül linkelhetően</h2>
    <p class="note">Minden alábbi elem a futás nyers kimeneteiből generálódik
    (nem kézzel válogatott), és a linkje közvetlenül a feltáró megfelelő
    kártyájára visz — vitához, idézéshez, megosztáshoz.</p>
{tally}
    <h3>A valódi dilemmák — ezeket nem dönti el se evidencia, se AI</h3>
    <p class="note">A társadalmi vita érveiből a rendszer kiszűri, mi
    kezelhető evidenciával vagy jobb szakpolitikai tervezéssel — ami marad,
    az tényleges értékválasztás, ami emberi döntést igényel.</p>
    <ul class="findings">
{dil_items}
    </ul>
    {dil_more}
{gumi_html}
{axes_html}
    <h3>A szakértői rekord</h3>
    <p class="note">A {len(f['experts'])} szakértő-ágens teljes elemzése
    megnyitható — a név egyben a hivatkozható link.</p>
    <p>{expert_chips}</p>
  </div>
</section>"""


def topic_card(cfg, state, num):
    slug = cfg["slug"]
    b = cfg["problem_brief"]
    frames = cfg.get("frames", {}).get("scenarios", [])
    question = b.get("public_question", b["title"])
    def summary(text, limit=250):
        first = text.split(". ", 1)[0].strip()
        if first and not first.endswith("."):
            first += "."
        if len(first) <= limit:
            return first
        return first[:limit - 1].rsplit(" ", 1)[0] + "…"
    n = len(frames)
    branches = "".join('<span class="route-map__branch"></span>'
                       for _ in range(min(n, 5)))
    return f"""    <a class="topic-entry" href="topics/{esc(slug)}/">
      <div class="topic-entry__index"><span>Dosszié</span><strong>{num:02d}</strong></div>
      <div class="topic-entry__body">
        <div>
          <h3 data-lang="hu">{esc(question['hu'])}</h3>
          <h3 data-lang="en">{esc(question['en'])}</h3>
          <p data-lang="hu">{esc(summary(b['problem_statement']['hu']))}</p>
          <p data-lang="en">{esc(summary(b['problem_statement']['en']))}</p>
        </div>
        <div class="topic-entry__meta">
          <span>{n} válaszút / routes</span>
          <span>{"Részletes elemzés elérhető" if state['has_final'] else "Feldolgozás alatt"}</span>
          <span>Megnyitás →</span>
        </div>
      </div>
      <div class="topic-entry__route" aria-hidden="true">
        <span class="route-map"><span class="route-map__start"></span>{branches}</span>
        <span class="route-map__label">{n} lehetséges<br>válaszút</span>
      </div>
    </a>"""


def _nav_title(cfg, limit=44):
    t = cfg["problem_brief"]["title"]["hu"]
    return t if len(t) <= limit else t[:limit - 1].rstrip() + "…"


def topic_page(cfg, state, num, total, prev_cfg, next_cfg):
    slug = cfg["slug"]
    b = cfg["problem_brief"]
    findings_html = findings_block(load_findings(slug)) if state["has_final"] else ""
    prev_link = (f'<a href="../{esc(prev_cfg["slug"])}/">← {num - 1}. '
                 f'{esc(_nav_title(prev_cfg))}</a>' if prev_cfg else "<span></span>")
    next_link = (f'<a href="../{esc(next_cfg["slug"])}/">{num + 1}. '
                 f'{esc(_nav_title(next_cfg))} →</a>' if next_cfg else "<span></span>")
    topicnav = f"""<nav class="topicnav" aria-label="Témák közötti navigáció">
  <div class="wrap">
    {prev_link}
    <a href="../../index.html#temak">összes téma</a>
    {next_link}
  </div>
</nav>"""
    goals = "\n".join(f"      <li>{esc(g['hu'])}</li>"
                      for g in b["learning_goals"])
    frames = cfg.get("frames", {}).get("scenarios", [])
    if frames:
        frames_html = "\n".join(
            f"""    <div class="card"><p><span class="id">{esc(f['id'])}</span>
      <strong>{esc(f['title']['hu'])}</strong></p>
      <p class="note" style="margin-bottom:0">{esc(f['scope']['hu'])}</p></div>"""
            for f in frames)
        derived = cfg.get("frames", {}).get("derived_from", "")
        frames_block = f"""<section>
  <div class="wrap">
    <p class="eyebrow">Opciótér — emberi jóváhagyással befagyasztva</p>
    <h2>A vizsgált megoldási keretek</h2>
    <p class="note">A kereteket a rendszer a szakértői elemzésből derivája
    (emergens keretezés), és emberi jóváhagyás után rögzíti — nem kézzel
    írott lista. Eredet: {esc(derived)}</p>
{frames_html}
  </div>
</section>"""
    else:
        frames_block = """<section>
  <div class="wrap">
    <p class="eyebrow">Opciótér</p>
    <h2>A megoldási keretek még nem születtek meg</h2>
    <p>Az 1. kör szakértői elemzése fogja derivalni őket; emberi jóváhagyás
    után jelennek meg itt.</p>
  </div>
</section>"""

    links = []
    if state["has_final"]:
        links.append('<a class="cta" href="explorer.html">Forgatókönyv-feltáró '
                     'megnyitása →</a>')
        links.append(f'<a href="https://github.com/halacsy/education-policy-lab/'
                     f'blob/main/outputs/topics/{esc(slug)}/final/final_brief.hu.md">'
                     'Záró összefoglaló (HU, nyers) →</a>')
    links.append('<a href="audit.html">Műhely-napló: minden lépés kimenete '
                 '(keresések, szakértői válaszok, elutasítások) →</a>')
    links.append(f'<a href="https://github.com/halacsy/education-policy-lab/'
                 f'tree/main/outputs/topics/{esc(slug)}">A teljes auditálható '
                 'rekord a GitHubon →</a>')
    links_html = "<br>\n    ".join(links)

    c = state["cost"]
    if c and c.get("has_data"):
        rows = "\n".join(
            f"        <tr><td>{esc(m)}</td>"
            f"<td>{v['input_tokens']:,}</td><td>{v['output_tokens']:,}</td>"
            f"<td>{'$%.2f' % v['usd'] if v.get('usd') is not None else 'nincs ár'}</td></tr>"
            for m, v in sorted(c["by_model"].items())).replace(",", " ")
        cost_block = f"""    <p><strong>Falióra-idő:</strong> {fmt_dur(c['wall_clock_s'])} ·
    <strong>tokenek:</strong> {f"{c['total_tokens']:,}".replace(',', ' ')} ·
    <strong>becsült költség:</strong> ${c['total_usd']:.2f} USD</p>
    <div class="tablebox"><table>
      <thead><tr><th>modell</th><th>bemeneti token</th><th>kimeneti token</th><th>becsült USD</th></tr></thead>
      <tbody>
{rows}
      </tbody>
    </table></div>
    <p class="note">Az USD-érték konfigurálható ártáblából számolt becslés,
    nem számla; forrás: <code>outputs/topics/{esc(slug)}/final/cost_report.json</code>.</p>"""
    else:
        cost_block = """    <p>Ehhez az érához nem áll rendelkezésre mért token-adat (a futások a
    körönkénti mérés bevezetése előtt készültek) — a költség nem ismert, nem
    nulla. A következő teljes kör már mért adatokat rögzít.</p>"""

    status = STATUS_HU.get(cfg.get("status", "active"), cfg.get("status"))
    run_state = (f"{state['rounds']} kör az aktuális érában"
                 + (f", utolsó összpontszám: {state['last_total']}"
                    if state["last_total"] is not None else "")
                 if state["rounds"] else "még nem futott teljes kör")

    return f"""<!DOCTYPE html>
<html lang="hu">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(b['title']['hu'])} — Education Policy Lab</title>
<meta name="description" content="{esc(b['problem_statement']['hu'][:150])}">
<style>{CSS}</style>
</head>
<body>
<header class="site">
  <div class="wrap">
    <span><a href="../../index.html">← Education Policy Lab</a></span>
    <span>{num}/{total}. téma · <code>{esc(slug)}</code> · állapot: {esc(status)}</span>
  </div>
</header>

{topicnav}

<section>
  <div class="wrap">
    <p class="eyebrow">Probléma-lap — a rendszer bemenete</p>
    <h1>{esc(b['title']['hu'])}</h1>
    <p>{esc(b['problem_statement']['hu'])}</p>
    <h3>Tanulási célok</h3>
    <ul>
{goals}
    </ul>
    <h3>Scope</h3>
    <p>{esc(b['scope']['hu'])}</p>
    <p class="note">Futási állapot: {esc(run_state)}.</p>
    <p>{links_html}</p>
  </div>
</section>

{frames_block}

{findings_html}

<section>
  <div class="wrap">
    <p class="eyebrow">Átláthatóság</p>
    <h2>Mennyi időbe és mennyibe került ennek a problémának a feldolgozása</h2>
{cost_block}
  </div>
</section>

<footer>
  <div class="wrap">
    <p>Generálva a repóból (<code>topics/{esc(slug)}/topic.json</code> +
    <code>outputs/topics/{esc(slug)}/</code>) minden publikáláskor — semmi
    sem kézzel szerkesztett.</p>
  </div>
</footer>
</body>
</html>
"""


EVIDENCE_HU = {"strong": "erős", "moderate": "mérsékelt",
               "weak": "gyenge", "contested": "vitatott"}


def _pair(value, lang):
    if isinstance(value, dict):
        return value.get(lang) or value.get("hu") or value.get("en") or ""
    return value or ""


def _both(value, tag="span", cls=""):
    class_attr = f' class="{cls}"' if cls else ""
    return (f'<{tag}{class_attr} data-lang="hu">{esc(_pair(value, "hu"))}</{tag}>'
            f'<{tag}{class_attr} data-lang="en">{esc(_pair(value, "en"))}</{tag}>')


def latest_scenarios(slug):
    it = OUT_ROOT / slug / "iterations"
    n = last_round(it) if it.exists() else None
    if n is None:
        return None, []
    path = it / f"round_{n:02d}" / "scenarios.json"
    if not path.exists():
        return n, []
    try:
        return n, json.loads(path.read_text(encoding="utf-8")).get("scenarios", [])
    except (json.JSONDecodeError, OSError):
        return n, []


def evidence_tag(label):
    label = label or "weak"
    suffix = "" if label == "strong" else f" evidence-tag--{esc(label)}"
    return (f'<span class="evidence-tag{suffix}">'
            f'{esc(EVIDENCE_HU.get(label, label))} / {esc(label)}</span>')


def atlas_findings_block(slug):
    f = load_findings(slug)
    if not f:
        return ""
    sd = f["sd"]
    counts = {"fix": 0, "human": 0, "open": 0}
    for cluster in sd["clusters"]:
        verdict = sd["verdicts"].get(cluster["id"])
        if verdict:
            counts[VERDICT_GROUP[verdict["response_type"]]] += 1

    dilemmas = [(c, sd["verdicts"][c["id"]]) for c in sd["clusters"]
                if sd["verdicts"].get(c["id"])
                and VERDICT_GROUP[sd["verdicts"][c["id"]]["response_type"]] == "human"]
    dilemmas.sort(key=lambda cv: (
        0 if cv[1]["response_type"] == "irreducible_tradeoff" else 1,
        REL_ORDER.get(cv[0].get("decision_relevance"), 3), cv[0]["id"]))
    dilemma_items = "\n".join(
        f'''<li><a href="dilemma/{esc(dilemma_filename(c["id"], c["claim"]))}">
          <span class="finding-list__id">{esc(c["id"])}</span>
          <span>{esc(c["claim"])}<small>{esc(VERDICT_HU[v["response_type"]])} · önálló dilemmaoldal →</small></span>
        </a></li>''' for c, v in dilemmas[:DILEMMA_CAP])

    gumik = [c for c in sd["clusters"] if is_gumicsont(c)]
    gumi_html = ""
    if gumik:
        items = "\n".join(
            f'''<li><a href="explorer.html#cluster-{esc(c["id"])}">
              <span class="finding-list__id">{esc(c["id"])}</span>
              <span>{esc(c["claim"])}<small>Miért nem változtatja meg a döntést? →</small></span>
            </a></li>''' for c in gumik)
        gumi_html = f'''<div class="finding-group">
          <div class="finding-group__head"><h3>Gumicsontok</h3><p class="atlas-note">Sok figyelmet kapnak, de az elemzés szerint kevéssé változtatják meg a döntést.</p></div>
          <ul class="finding-list">{items}</ul>
        </div>'''

    axes_html = ""
    if f["axes"]:
        items = "\n".join(
            f'''<li><a href="vita/{esc(debate_filename(i + 1, ax["topic"]))}"><span class="finding-list__id">V{i + 1:02d}</span><span>{esc(ax["topic"])}<small>Önálló vitaoldal · mindkét álláspont indoklása →</small></span></a></li>'''
            for i, ax in enumerate(f["axes"]))
        axes_html = f'''<div class="finding-group">
          <div class="finding-group__head"><h3>Ahol a szakértők nem értenek egyet</h3><p class="atlas-note">A különvélemény nem tűnik el a szintézisben.</p></div>
          <ul class="finding-list">{items}</ul>
        </div>'''

    expert_links = "".join(
        f'<a href="szakerto/{esc(expert_filename(name))}">'
        f'{_both({"hu": expert_label(name, "hu"), "en": expert_label(name, "en")})}</a>'
        for name in f["experts"])

    return f'''<section class="atlas-section" id="vitak">
      <div class="atlas-shell">
        <div class="catalog-head"><div><p class="atlas-kicker atlas-kicker--dissent">Viták és döntési dilemmák</p><h2>Ahol a térkép nem jelöl egyetlen helyes irányt.</h2></div><p class="atlas-note">A {f["round"]}. kör nyilvános érvanyagából, automatikusan generálva.</p></div>
        <div class="finding-summary">
          <div class="finding-stat"><b>{counts["fix"]}</b><span>evidenciával vagy tervezéssel kezelhető</span></div>
          <div class="finding-stat"><b>{counts["human"]}</b><span>emberi értékdöntést kér</span></div>
          <div class="finding-stat"><b>{counts["open"]}</b><span>nyitott vagy nem döntésreleváns</span></div>
        </div>
        <div class="finding-group">
          <div class="finding-group__head"><h3>Valódi dilemmák</h3><p class="atlas-note">Ezeket nem oldja fel több adat vagy jobb technikai tervezés.</p></div>
          <ul class="finding-list">{dilemma_items}</ul>
        </div>
        {axes_html}{gumi_html}
        <div class="finding-group" id="szakertok"><div class="finding-group__head"><h3>A szakértői rekord</h3><p class="atlas-note">A teljes elemzések közvetlenül megnyithatók.</p></div><div class="expert-links">{expert_links}</div></div>
      </div>
    </section>'''


DECOMP_EN = {
    "interest": "Whose interest is at stake",
    "value": "Which values conflict",
    "fear": "Which fear drives it",
    "assumption": "Which assumption it rests on",
    "empirical_uncertainty": "Empirical uncertainty",
}


def _record_pager_link(record, direction, kind_hu, kind_en):
    if not record:
        return ""
    is_next = direction == "next"
    label_hu = f'{"Következő" if is_next else "Előző"} {kind_hu}'
    label_en = f'{"Next" if is_next else "Previous"} {kind_en}'
    arrow = "→" if is_next else "←"
    return f'''<a class="record-pagination__link record-pagination__link--{direction}" rel="{direction}" href="{esc(record["filename"])}">
      <span><span data-lang="hu">{esc(label_hu)}</span><span data-lang="en">{esc(label_en)}</span> {arrow}</span>
      {_both(record["title"], "strong")}
    </a>'''


def _record_shell(cfg, title, description, record_id, kind_hu, kind_en,
                  body, explorer_anchor, round_n, nav_kind_hu, nav_kind_en,
                  nav_group_hu, nav_group_en, previous_record=None,
                  next_record=None, title_as_claim=False):
    slug = cfg["slug"]
    question = cfg["problem_brief"].get(
        "public_question", cfg["problem_brief"]["title"])
    title_length = max(len(str(_pair(title, lang))) for lang in ("hu", "en"))
    if title_length > 180:
        title_class = "record-title record-title--extended"
    elif title_length > 110:
        title_class = "record-title record-title--long"
    else:
        title_class = "record-title"
    previous_link = _record_pager_link(
        previous_record, "prev", nav_kind_hu, nav_kind_en)
    next_link = _record_pager_link(
        next_record, "next", nav_kind_hu, nav_kind_en)
    pagination = f'''<nav class="record-pagination" aria-label="Rekordok közötti navigáció"><div class="atlas-shell record-pagination__grid">
      {previous_link}{next_link}
      <a class="record-pagination__all" href="../#vitak"><span data-lang="hu">Összes vita és dilemma</span><span data-lang="en">All debates and dilemmas</span></a>
    </div></nav>'''
    if title_as_claim:
        record_heading = f'''<h1 class="record-hero__id"><span>{esc(record_id)}</span><strong data-lang="hu">{esc(kind_hu)}</strong><strong data-lang="en">{esc(kind_en)}</strong></h1>'''
        title_markup = _both(title, "p", "record-claim")
    else:
        record_heading = f'''<div class="record-hero__id"><span>{esc(record_id)}</span><strong data-lang="hu">{esc(kind_hu)}</strong><strong data-lang="en">{esc(kind_en)}</strong></div>'''
        title_markup = _both(title, "h1", title_class)
    return f'''<!doctype html><html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(record_id)} — {esc(_pair(title, "hu"))} — Oktatáspolitikai Atlasz</title>
<meta name="description" content="{esc(_pair(description, "hu")[:155])}"><link rel="stylesheet" href="../../../assets/atlas.css"></head>
<body class="atlas record-page"><header class="site-header"><div class="atlas-shell site-header__inner"><a class="site-brand" href="../../../index.html"><span class="site-brand__mark" aria-hidden="true"></span><span class="site-brand__name">Oktatáspolitikai<br>Atlasz</span></a><button class="nav-toggle" type="button" data-nav-toggle aria-expanded="false" aria-controls="site-nav">Menü</button><nav class="site-nav" id="site-nav" data-site-nav><a href="../">← Kérdésoldal</a><a href="../#vitak">Viták és dilemmák</a><div class="lang-switch"><button type="button" data-set-lang="hu" aria-pressed="true">HU</button><button type="button" data-set-lang="en" aria-pressed="false">EN</button></div></nav></div></header>
<main><section class="record-context"><div class="atlas-shell record-context__inner"><nav class="record-breadcrumb" aria-label="Morzsamenü"><a href="../../../index.html#temak"><span data-lang="hu">Kérdések</span><span data-lang="en">Questions</span></a><span aria-hidden="true">/</span><a href="../">{_both(question)}</a><span aria-hidden="true">/</span><a href="../#vitak"><span data-lang="hu">{esc(nav_group_hu)}</span><span data-lang="en">{esc(nav_group_en)}</span></a><span aria-hidden="true">/</span><strong aria-current="page">{esc(record_id)}</strong></nav><p class="record-context__round"><span data-lang="hu">{round_n}. feldolgozási kör</span><span data-lang="en">Processing round {round_n}</span></p></div></section>
<section class="topic-hero"><div class="atlas-shell record-hero">{record_heading}<div>{title_markup}<div class="record-hero__actions"><a class="text-link" href="../explorer.html#{esc(explorer_anchor)}"><span data-lang="hu">Teljes rekord az érvfeltáróban</span><span data-lang="en">Full record in the explorer</span></a></div></div></div></section>
{body}{pagination}</main>
<footer class="site-footer"><div class="atlas-shell"><div class="site-footer__grid"><h2>{esc(_pair(question, "hu"))}</h2><nav><a href="../#vitak">Összes vita és dilemma</a><a href="../explorer.html#{esc(explorer_anchor)}">Teljes érvfeltáró</a></nav><nav><a href="../../../about.html">Az Atlaszról</a><a href="../../../tech.html">Módszertan</a></nav></div><p class="site-footer__meta">{esc(slug)} · {esc(record_id)} · {round_n}. KÖR · KANONIKUS, GENERÁLT REKORD</p></div></footer><script src="../../../assets/atlas.js"></script></body></html>'''


def debate_page(cfg, ax_hu, ax_en, index, round_n, previous_record=None,
                next_record=None):
    title = {"hu": ax_hu["topic"], "en": ax_en["topic"]}
    cards = []
    en_positions = ax_en.get("positions", [])
    for pos_index, pos_hu in enumerate(ax_hu.get("positions", [])):
        pos_en = en_positions[pos_index] if pos_index < len(en_positions) else pos_hu
        minority = bool(pos_hu.get("minority"))
        holder_links = []
        for holder in pos_hu.get("holders", []):
            canonical = canonical_expert_name(holder)
            if canonical:
                holder_links.append(
                    f'<a href="../szakerto/{esc(expert_filename(canonical))}">'
                    f'{_both({"hu": expert_label(canonical, "hu"), "en": expert_label(canonical, "en")})}</a>')
            else:
                holder_links.append(f'<span>{esc(holder)}</span>')
        holders = "".join(holder_links)
        label_hu = "Kisebbségi álláspont" if minority else "Álláspont"
        label_en = "Minority position" if minority else "Position"
        cards.append(f'''<article class="position-card{' position-card--minority' if minority else ''}">
          <p class="position-card__label"><span data-lang="hu">{label_hu}</span><span data-lang="en">{label_en}</span></p>
          {_both({"hu": pos_hu.get("position", ""), "en": pos_en.get("position", "")}, "h2")}
          <div class="position-card__why"><h3><span data-lang="hu">Miért ezt állítják?</span><span data-lang="en">Why do they argue this?</span></h3>{_both({"hu": pos_hu.get("why", ""), "en": pos_en.get("why", "")}, "p")}</div>
          <div class="position-card__holders"><span data-lang="hu">Ezt az álláspontot képviseli</span><span data-lang="en">Experts holding this position</span><div>{holders}</div></div>
        </article>''')
    record_id = f"V{index:02d}"
    body = f'''<section class="atlas-section atlas-section--paper"><div class="atlas-shell"><div class="record-intro"><p class="atlas-kicker atlas-kicker--dissent"><span data-lang="hu">Megőrzött nézeteltérés</span><span data-lang="en">Preserved disagreement</span></p><p class="atlas-lede"><span data-lang="hu">A szakértői elemzések ugyanarról a kérdésről eltérő oksági vagy értékelési következtetésre jutottak. Az Atlasz nem mossa össze őket: mindkét indoklást külön mutatja.</span><span data-lang="en">Expert analyses reached different causal or evaluative conclusions about the same question. The Atlas preserves both lines of reasoning separately.</span></p></div><div class="position-grid">{''.join(cards)}</div></div></section>'''
    return _record_shell(
        cfg, title, title, record_id, "Vitatott kérdés", "Contested question",
        body, f"axis-{index}", round_n, "vita", "debate", "Viták", "Debates",
        previous_record, next_record)


def dilemma_page(cfg, c_hu, c_en, v_hu, v_en, round_n,
                 previous_record=None, next_record=None):
    title = {"hu": c_hu["claim"], "en": c_en["claim"]}
    verdict = v_hu["response_type"]
    decomp = []
    for field, label_hu in DECOMP_FIELDS:
        hu_value = str(c_hu.get(field, "")).strip()
        en_value = str(c_en.get(field, "")).strip()
        if hu_value or en_value:
            decomp.append(f'''<div><dt><span data-lang="hu">{esc(label_hu)}</span><span data-lang="en">{esc(DECOMP_EN[field])}</span></dt><dd>{_both({"hu": hu_value, "en": en_value})}</dd></div>''')
    affected_hu = c_hu.get("affected", [])
    affected_en = c_en.get("affected", [])
    if affected_hu:
        people = "".join(
            f'<li>{_both({"hu": person, "en": affected_en[i] if i < len(affected_en) else person})}</li>'
            for i, person in enumerate(affected_hu))
        decomp.append(f'''<div><dt><span data-lang="hu">Kiket érint</span><span data-lang="en">Who is affected</span></dt><dd><ul>{people}</ul></dd></div>''')
    kind = c_hu.get("kind", "")
    side = c_hu.get("side", "")
    relevance = c_hu.get("decision_relevance", "")
    raised = "".join(
        f'<span>{esc(name.replace("_", " "))}</span>'
        for name in c_hu.get("raised_by", []))
    reason = {"hu": v_hu.get("reason", ""), "en": v_en.get("reason", "")}
    body = f'''<section class="atlas-section atlas-section--paper"><div class="atlas-shell record-grid"><div><p class="atlas-kicker atlas-kicker--dissent"><span data-lang="hu">Miért emberi döntés?</span><span data-lang="en">Why does this need human judgement?</span></p><div class="record-verdict"><strong data-lang="hu">{esc(VERDICT_HU[verdict])}</strong><strong data-lang="en">{esc(verdict.replace("_", " "))}</strong>{_both(reason, "p")}</div><div class="record-facts"><span>{esc(KIND_HU.get(kind, kind))} / {esc(kind)}</span><span>{esc(SIDE_HU.get(side, side))} / {esc(side)}</span><span>{esc(REL_HU.get(relevance, relevance))} döntésrelevancia / {esc(relevance)} relevance</span></div><div class="position-card__holders"><span data-lang="hu">Felvetette</span><span data-lang="en">Raised by</span><div>{raised}</div></div></div><dl class="record-decomp">{''.join(decomp)}</dl></div></section>'''
    return _record_shell(
        cfg, title, reason, c_hu["id"], "Döntési dilemma", "Decision dilemma",
        body, f"cluster-{c_hu['id']}", round_n, "dilemma", "dilemma",
        "Dilemmák", "Dilemmas", previous_record, next_record,
        title_as_claim=True)


def write_finding_pages(cfg):
    """Mint canonical, semantic URLs for every disagreement axis and every
    cluster that the brief classifies as requiring human judgement."""
    slug = cfg["slug"]
    findings_hu = load_findings(slug, "hu")
    findings_en = load_findings(slug, "en")
    if not findings_hu or not findings_en:
        return 0, 0
    round_n = findings_hu["round"]
    debate_dir = ROOT / "site" / "topics" / slug / "vita"
    dilemma_dir = ROOT / "site" / "topics" / slug / "dilemma"
    for directory in (debate_dir, dilemma_dir):
        directory.mkdir(parents=True, exist_ok=True)
        for stale in directory.glob("*.html"):
            stale.unlink()
    debate_records = [
        {"id": f"V{i:02d}",
         "title": {"hu": ax_hu["topic"],
                   "en": findings_en["axes"][i - 1]["topic"]},
         "filename": debate_filename(i, ax_hu["topic"])}
        for i, ax_hu in enumerate(findings_hu["axes"], 1)
    ]
    for i, ax_hu in enumerate(findings_hu["axes"], 1):
        ax_en = findings_en["axes"][i - 1]
        dest = debate_dir / debate_records[i - 1]["filename"]
        previous_record = debate_records[i - 2] if i > 1 else None
        next_record = debate_records[i] if i < len(debate_records) else None
        dest.write_text(debate_page(cfg, ax_hu, ax_en, i, round_n,
                                    previous_record, next_record),
                        encoding="utf-8")
        print(f"wrote {dest}")
    human_hu = [(c, findings_hu["sd"]["verdicts"][c["id"]])
                for c in findings_hu["sd"]["clusters"]
                if findings_hu["sd"]["verdicts"].get(c["id"])
                and VERDICT_GROUP[findings_hu["sd"]["verdicts"][c["id"]]["response_type"]] == "human"]
    human_hu.sort(key=lambda cv: (
        0 if cv[1]["response_type"] == "irreducible_tradeoff" else 1,
        REL_ORDER.get(cv[0].get("decision_relevance"), 3), cv[0]["id"]))
    clusters_en = {c["id"]: c for c in findings_en["sd"]["clusters"]}
    verdicts_en = findings_en["sd"]["verdicts"]
    dilemma_records = [
        {"id": cluster_hu["id"],
         "title": {"hu": cluster_hu["claim"],
                   "en": clusters_en[cluster_hu["id"]]["claim"]},
         "filename": dilemma_filename(cluster_hu["id"], cluster_hu["claim"])}
        for cluster_hu, _ in human_hu
    ]
    for position, (cluster_hu, verdict_hu) in enumerate(human_hu):
        cid = cluster_hu["id"]
        dest = dilemma_dir / dilemma_records[position]["filename"]
        previous_record = dilemma_records[position - 1] if position else None
        next_record = (dilemma_records[position + 1]
                       if position + 1 < len(dilemma_records) else None)
        dest.write_text(dilemma_page(cfg, cluster_hu, clusters_en[cid],
                                     verdict_hu, verdicts_en[cid], round_n,
                                     previous_record, next_record),
                        encoding="utf-8")
        print(f"wrote {dest}")
    return len(findings_hu["axes"]), len(human_hu)


def _markdown_section(text, heading):
    match = re.search(
        rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text,
        re.M | re.S)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _research_urls(text):
    urls = []
    seen = set()
    for match in re.findall(r"https?://[^\s<>\"']+", text):
        url = match.rstrip(".,;]")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _expert_debates(name, axes_hu, axes_en):
    records = []
    for axis_index, axis_hu in enumerate(axes_hu, 1):
        axis_en = axes_en[axis_index - 1] if axis_index <= len(axes_en) else axis_hu
        en_positions = axis_en.get("positions", [])
        for pos_index, pos_hu in enumerate(axis_hu.get("positions", [])):
            if name not in [canonical_expert_name(holder)
                            for holder in pos_hu.get("holders", [])]:
                continue
            pos_en = en_positions[pos_index] if pos_index < len(en_positions) else pos_hu
            records.append({
                "id": f"V{axis_index:02d}",
                "title": {"hu": axis_hu["topic"], "en": axis_en["topic"]},
                "position": {
                    "hu": pos_hu.get("position", ""),
                    "en": pos_en.get("position", ""),
                },
                "why": {
                    "hu": pos_hu.get("why", ""),
                    "en": pos_en.get("why", ""),
                },
                "minority": bool(pos_hu.get("minority")),
                "filename": debate_filename(axis_index, axis_hu["topic"]),
            })
    return records


def expert_page(cfg, profile, previous_record, next_record, round_n):
    slug = cfg["slug"]
    name = profile["name"]
    data = profile["data"]
    labels = {"hu": expert_label(name, "hu"), "en": expert_label(name, "en")}
    question = cfg["problem_brief"].get(
        "public_question", cfg["problem_brief"]["title"])
    findings = data.get("findings", [])
    assumptions = data.get("assumptions", [])
    uncertainties = data.get("uncertainties", [])
    debates = profile["debates"]
    urls = profile["urls"]
    curated = profile["curated"]
    strong_count = sum(1 for item in findings if item.get("evidence") == "strong")

    findings_html = "".join(f'''<li><div class="expert-finding">
      <div class="expert-finding__meta">{evidence_tag(item.get("evidence"))}<span>{esc(item.get("source", ""))}</span></div>
      {_both(item.get("claim", {}), "p")}
    </div></li>''' for item in findings)

    assumptions_html = "".join(
        f"<li>{_both(item)}</li>" for item in assumptions)
    confidence_hu = {"low": "alacsony", "medium": "közepes", "high": "magas"}
    uncertainties_html = "".join(f'''<article class="expert-unknown">
      <p class="expert-unknown__confidence"><span data-lang="hu">{esc(confidence_hu.get(item.get("confidence"), item.get("confidence", "")))} bizonytalanság</span><span data-lang="en">{esc(item.get("confidence", ""))} uncertainty</span></p>
      {_both(item.get("text", {}), "p")}
      <div><strong><span data-lang="hu">Ezt csökkentené</span><span data-lang="en">What would reduce it</span></strong>{_both(item.get("reduced_by", {}), "p")}</div>
    </article>''' for item in uncertainties)

    debate_html = "".join(f'''<a class="expert-debate" href="../vita/{esc(item["filename"])}">
      <div><span>{esc(item["id"])}</span><small><span data-lang="hu">{'kisebbségi álláspont' if item["minority"] else 'álláspont'}</span><span data-lang="en">{'minority position' if item["minority"] else 'position'}</span></small></div>
      {_both(item["title"], "h3")}
      {_both(item["position"], "p")}
      <span class="text-link"><span data-lang="hu">A teljes vita →</span><span data-lang="en">Open the full debate →</span></span>
    </a>''' for item in debates)
    if not debate_html:
        debate_html = '''<p class="expert-empty"><span data-lang="hu">A végső brief ebben a körben egyetlen nézeteltérési tengelyen sem nevezte meg külön ezt a szakértőt. Ez nem azt jelenti, hogy a munkája nem került be a szintézisbe.</span><span data-lang="en">The final brief did not name this expert on a disagreement axis in this round. This does not mean the synthesis ignored the analysis.</span></p>'''

    curated_html = "".join(f'''<article class="expert-source-card">
      <div><code>{esc(fid)}</code>{evidence_tag(fact.get("evidence"))}</div>
      {_both(fact, "p")}
      <small>{esc(fact.get("source", ""))}</small>
    </article>''' for fid, fact in curated)
    if not curated_html:
        curated_html = '''<p class="expert-empty"><span data-lang="hu">Ehhez a szakértőhöz ennél a kérdésnél nem volt előre hozzárendelt, ember által jóváhagyott registry-tétel. A megállapítások az élő kutatási jegyzetekből és a modell háttértudásából készültek; utóbbi nem számít registry-alátámasztásnak.</span><span data-lang="en">No human-approved registry fact was assigned to this expert for this question. Findings came from live research notes and model background knowledge; the latter does not count as registry backing.</span></p>'''

    url_html = "".join(f'''<li><a href="{esc(url)}" target="_blank" rel="noreferrer"><strong>{i:02d} · {esc(urlparse(url).netloc.removeprefix("www."))}</strong><span>{esc(url)}</span></a></li>'''
                       for i, url in enumerate(urls, 1))
    if not url_html:
        url_html = '''<li class="expert-empty"><span data-lang="hu">Ehhez a körhöz nem maradt URL-t tartalmazó élő kutatási jegyzet.</span><span data-lang="en">No URL-bearing live research note was preserved for this round.</span></li>'''

    previous_link = _record_pager_link(
        previous_record, "prev", "szakértő", "expert")
    next_link = _record_pager_link(next_record, "next", "szakértő", "expert")
    pagination = f'''<nav class="record-pagination" aria-label="Szakértők közötti navigáció"><div class="atlas-shell record-pagination__grid">
      {previous_link}{next_link}
      <a class="record-pagination__all" href="../#szakertok"><span data-lang="hu">Összes szakértő</span><span data-lang="en">All experts</span></a>
    </div></nav>'''

    github_root = ("https://github.com/halacsy/education-policy-lab/blob/main/"
                   f"outputs/topics/{slug}/iterations/round_{round_n:02d}")
    research_link = (f'<a href="{github_root}/research/{esc(name)}.md">'
                     '<span data-lang="hu">Élő kutatási jegyzet</span>'
                     '<span data-lang="en">Live research note</span></a>'
                     if profile["has_research"] else "")
    role = profile["role"] or "No role section was preserved in the round snapshot."
    provider = profile["provider"] or "n/a"

    return f'''<!doctype html><html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(labels["hu"])} — szakértői profil — Oktatáspolitikai Atlasz</title>
<meta name="description" content="{esc(_pair(data.get("position", {}), "hu")[:155])}"><link rel="stylesheet" href="../../../assets/atlas.css"></head>
<body class="atlas expert-page"><header class="site-header"><div class="atlas-shell site-header__inner"><a class="site-brand" href="../../../index.html"><span class="site-brand__mark" aria-hidden="true"></span><span class="site-brand__name">Oktatáspolitikai<br>Atlasz</span></a><button class="nav-toggle" type="button" data-nav-toggle aria-expanded="false" aria-controls="site-nav">Menü</button><nav class="site-nav" id="site-nav" data-site-nav><a href="../">← Kérdésoldal</a><a href="../#szakertok">Szakértők</a><div class="lang-switch"><button type="button" data-set-lang="hu" aria-pressed="true">HU</button><button type="button" data-set-lang="en" aria-pressed="false">EN</button></div></nav></div></header>
<main><section class="record-context"><div class="atlas-shell record-context__inner"><nav class="record-breadcrumb" aria-label="Morzsamenü"><a href="../../../index.html#temak"><span data-lang="hu">Kérdések</span><span data-lang="en">Questions</span></a><span aria-hidden="true">/</span><a href="../">{_both(question)}</a><span aria-hidden="true">/</span><a href="../#szakertok"><span data-lang="hu">Szakértők</span><span data-lang="en">Experts</span></a><span aria-hidden="true">/</span><strong aria-current="page">{esc(name)}</strong></nav><p class="record-context__round"><span data-lang="hu">{round_n}. feldolgozási kör</span><span data-lang="en">Processing round {round_n}</span></p></div></section>
<section class="expert-hero"><div class="atlas-shell expert-hero__grid"><div><p class="atlas-kicker">Szakértő-ágens / expert agent</p>{_both(labels, "h1")}<code class="expert-agent-id">{esc(name)}</code><p class="expert-role-label"><span data-lang="hu">A futáskor használt szerepleírás · angol eredeti</span><span data-lang="en">Role used during the run</span></p><p class="expert-role">{esc(role)}</p></div><aside class="expert-disclosure"><strong><span data-lang="hu">Ez nem személy vagy intézmény.</span><span data-lang="en">This is not a person or institution.</span></strong><p><span data-lang="hu">Egy körülhatárolt nézőpontú modell-ágens. A profil csak a mentett inputokat, állításokat és explicit attribúciókat mutatja; nem rekonstruál rejtett gondolatmenetet.</span><span data-lang="en">It is a model agent with a bounded analytical remit. This profile shows saved inputs, claims and explicit attribution only; it does not reconstruct hidden reasoning.</span></p><dl class="expert-stats"><div><dt>{len(findings)}</dt><dd><span data-lang="hu">megállapítás</span><span data-lang="en">findings</span></dd></div><div><dt>{strong_count}</dt><dd><span data-lang="hu">erős evidencia</span><span data-lang="en">strong evidence</span></dd></div><div><dt>{len(urls)}</dt><dd><span data-lang="hu">kutatási URL</span><span data-lang="en">research URLs</span></dd></div><div><dt>{len(debates)}</dt><dd><span data-lang="hu">név szerinti vita</span><span data-lang="en">named debates</span></dd></div></dl></aside></div></section>
<section class="expert-lineage-section"><div class="atlas-shell"><p class="atlas-kicker"><span data-lang="hu">Működési lánc</span><span data-lang="en">Operating chain</span></p><div class="expert-lineage"><div><b>01</b><strong><span data-lang="hu">Szerepspecifikáció</span><span data-lang="en">Role specification</span></strong><span><span data-lang="hu">Körülhatárolja a vizsgált területet és a hibamódokat.</span><span data-lang="en">Bounds the domain and failure modes.</span></span></div><div><b>02</b><strong><span data-lang="hu">Kurált tételek</span><span data-lang="en">Curated facts</span></strong><span>{len(curated)} <span data-lang="hu">emberileg jóváhagyott bemenet</span><span data-lang="en">human-approved inputs</span></span></div><div><b>03</b><strong><span data-lang="hu">Élő webkutatás</span><span data-lang="en">Live web research</span></strong><span>{len(urls)} <span data-lang="hu">megőrzött URL</span><span data-lang="en">preserved URLs</span></span></div><div><b>04</b><strong><span data-lang="hu">Strukturált elemzés</span><span data-lang="en">Structured analysis</span></strong><span><span data-lang="hu">Kétnyelvű állítások, források és bizonytalanságok.</span><span data-lang="en">Bilingual claims, sources and uncertainties.</span></span></div><div><b>05</b><strong><span data-lang="hu">Szintézis és vita</span><span data-lang="en">Synthesis and debate</span></strong><span><span data-lang="hu">A szerkesztő megőrzi a nézeteltéréseket.</span><span data-lang="en">The editor preserves disagreements.</span></span></div></div><p class="expert-run-note"><span data-lang="hu">Generátor-szolgáltató ebben a körben:</span><span data-lang="en">Generator provider in this round:</span> <code>{esc(provider)}</code></p></div></section>
<section class="atlas-section atlas-section--paper"><div class="atlas-shell expert-position-grid"><div><p class="atlas-kicker"><span data-lang="hu">A szakértő álláspontja</span><span data-lang="en">Expert position</span></p><blockquote class="expert-position-quote">{_both(data.get("position", {}), "p")}</blockquote></div><div><p class="atlas-kicker"><span data-lang="hu">Összértelmezés</span><span data-lang="en">Interpretation</span></p>{_both(data.get("interpretation", {}), "p", "expert-interpretation")}</div></div></section>
<section class="atlas-section" id="vitak"><div class="atlas-shell"><div class="catalog-head"><div><p class="atlas-kicker atlas-kicker--dissent"><span data-lang="hu">Hol volt fontos szerepe?</span><span data-lang="en">Where did this expert matter?</span></p><h2><span data-lang="hu">Név szerint megőrzött vitapozíciók.</span><span data-lang="en">Debate positions preserved by name.</span></h2></div><p class="atlas-note"><span data-lang="hu">Csak az explicit holder-attribúciókat mutatjuk. A forgatókönyv-építő minden szakértői outputot megkapott, de a jelenlegi séma nem őriz állításszintű provenance-et minden forgatókönyvhöz.</span><span data-lang="en">Only explicit holder attribution is shown. The scenario builder received every expert output, but the current schema does not preserve claim-level provenance for every scenario.</span></p></div><div class="expert-debate-grid">{debate_html}</div></div></section>
<section class="atlas-section atlas-section--paper" id="forrasok"><div class="atlas-shell"><div class="catalog-head"><div><p class="atlas-kicker"><span data-lang="hu">Tudásbázis</span><span data-lang="en">Knowledge base</span></p><h2><span data-lang="hu">Mire támaszkodott ebben a kérdésben?</span><span data-lang="en">What supported this analysis?</span></h2></div><p class="atlas-note"><span data-lang="hu">A kurált registry és az élő kutatás külön marad: a webes találat nem kerül automatikusan az emberileg jóváhagyott tudásbázisba.</span><span data-lang="en">The curated registry and live research remain separate: web results are never automatically admitted to the human-approved knowledge base.</span></p></div><div class="expert-source-grid"><div><h3><span data-lang="hu">Kurált evidencia</span><span data-lang="en">Curated evidence</span></h3><div class="expert-source-stack">{curated_html}</div><a class="text-link" href="../../../knowledge.html"><span data-lang="hu">A teljes kurált tudásbázis →</span><span data-lang="en">Open the curated knowledge base →</span></a></div><div><h3><span data-lang="hu">Élő kutatás URL-jei</span><span data-lang="en">Live research URLs</span></h3><ol class="expert-url-list">{url_html}</ol></div></div></div></section>
<section class="atlas-section" id="allitasok"><div class="atlas-shell"><div class="catalog-head"><div><p class="atlas-kicker"><span data-lang="hu">Mit mondott?</span><span data-lang="en">What did the expert say?</span></p><h2><span data-lang="hu">Minden strukturált megállapítás.</span><span data-lang="en">Every structured finding.</span></h2></div><p class="atlas-note"><span data-lang="hu">Az evidenciafokozat állításonként értendő; a forrás megnevezése nem jelent automatikus registry-jóváhagyást.</span><span data-lang="en">Evidence grades apply per claim; naming a source does not imply registry approval.</span></p></div><ol class="expert-findings">{findings_html}</ol></div></section>
<section class="atlas-section atlas-section--paper"><div class="atlas-shell expert-limits-grid"><div><p class="atlas-kicker atlas-kicker--dissent"><span data-lang="hu">Feltevések</span><span data-lang="en">Assumptions</span></p><h2><span data-lang="hu">Minek kell igaznak lennie?</span><span data-lang="en">What must be true?</span></h2><ul class="detail-list">{assumptions_html}</ul></div><div><p class="atlas-kicker atlas-kicker--dissent"><span data-lang="hu">Bizonytalanságok</span><span data-lang="en">Uncertainties</span></p><h2><span data-lang="hu">Mit nem tudott?</span><span data-lang="en">What did the expert not know?</span></h2><div class="expert-unknowns">{uncertainties_html}</div></div></div></section>
<section class="expert-raw"><div class="atlas-shell"><p><span data-lang="hu">Ellenőrizhető nyers rekordok:</span><span data-lang="en">Inspectable raw records:</span></p><nav><a href="{github_root}/expert_outputs/{esc(name)}.json">JSON output</a>{research_link}<a href="{github_root}/system_state/agents/experts/{esc(name)}.md"><span data-lang="hu">Futáskori szerepspecifikáció</span><span data-lang="en">Round-time role specification</span></a><a href="../explorer.html#expert-{esc(name)}"><span data-lang="hu">Teljes érvfeltáró</span><span data-lang="en">Full argument explorer</span></a></nav></div></section>{pagination}</main>
<footer class="site-footer"><div class="atlas-shell"><div class="site-footer__grid">{_both(question, "h2")}<nav><a href="../#szakertok">Összes szakértő</a><a href="../#vitak">Viták és dilemmák</a></nav><nav><a href="../../../about.html">Az Atlaszról</a><a href="../../../tech.html">Módszertan</a></nav></div><p class="site-footer__meta">{esc(slug)} · {esc(name)} · {round_n}. KÖR · GENERÁLT SZAKÉRTŐI PROFIL</p></div></footer><script src="../../../assets/atlas.js"></script></body></html>'''


def write_expert_pages(cfg):
    slug = cfg["slug"]
    iterations = OUT_ROOT / slug / "iterations"
    round_n = last_round(iterations) if iterations.exists() else None
    if round_n is None:
        return 0
    rd = iterations / f"round_{round_n:02d}"
    names = list_experts(rd)
    if not names:
        return 0
    axes_hu = load_structured_disagreements(rd, "hu") or []
    axes_en = load_structured_disagreements(rd, "en") or []
    registry_path = ROOT / "knowledge" / "registry.json"
    registry = (json.loads(registry_path.read_text(encoding="utf-8"))
                .get("facts", {})) if registry_path.exists() else {}
    meta_path = rd / "round_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    starts = meta.get("starts", [])
    provider = starts[-1].get("generator_provider", "") if starts else ""
    records = [{
        "id": name,
        "title": {"hu": expert_label(name, "hu"),
                  "en": expert_label(name, "en")},
        "filename": expert_filename(name),
    } for name in names]
    out_dir = ROOT / "site" / "topics" / slug / "szakerto"
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.html"):
        stale.unlink()
    for index, record in enumerate(records):
        name = record["id"]
        data_path = rd / "expert_outputs" / f"{name}.json"
        if not data_path.exists():
            continue
        spec_path = rd / "system_state" / "agents" / "experts" / f"{name}.md"
        research_path = rd / "research" / f"{name}.md"
        spec = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""
        research = (research_path.read_text(encoding="utf-8")
                    if research_path.exists() else "")
        curated = [(fid, registry[fid])
                   for fid in cfg.get("expert_facts", {}).get(name, [])
                   if fid in registry]
        profile = {
            "name": name,
            "data": json.loads(data_path.read_text(encoding="utf-8")),
            "role": _markdown_section(spec, "Role"),
            "urls": _research_urls(research),
            "curated": curated,
            "debates": _expert_debates(name, axes_hu, axes_en),
            "provider": provider,
            "has_research": research_path.exists(),
        }
        previous_record = records[index - 1] if index else None
        next_record = records[index + 1] if index + 1 < len(records) else None
        dest = out_dir / record["filename"]
        dest.write_text(expert_page(cfg, profile, previous_record, next_record,
                                    round_n), encoding="utf-8")
        print(f"wrote {dest}")
    return len(records)


def _scenario_cards(cfg, scenarios):
    if scenarios:
        cards = []
        for scenario in scenarios:
            label = scenario.get("evidence_status", {}).get("label", "weak")
            cards.append(f'''<a class="option-card" href="scenarios/{esc(scenario["id"].lower())}.html">
              <span class="option-card__id">{esc(scenario["id"])}</span>
              <div>{_both(scenario["title"], "h3")}{_both(scenario["goal"], "p")}{evidence_tag(label)}</div>
            </a>''')
        return "".join(cards)
    frames = cfg.get("frames", {}).get("scenarios", [])
    return "".join(f'''<div class="option-card"><span class="option-card__id">{esc(frame["id"])}</span><div>{_both(frame["title"], "h3")}{_both(frame["scope"], "p")}</div></div>''' for frame in frames)


def topic_page(cfg, state, num, total, prev_cfg, next_cfg):
    slug = cfg["slug"]
    brief = cfg["problem_brief"]
    question = brief.get("public_question", brief["title"])
    round_n, scenarios = latest_scenarios(slug)
    goals = "".join(f'<li>{_both(goal)}</li>' for goal in brief["learning_goals"])
    scenario_cards = _scenario_cards(cfg, scenarios)
    findings_html = atlas_findings_block(slug) if state["has_final"] else ""
    status = STATUS_HU.get(cfg.get("status", "active"), cfg.get("status"))
    run_state = (f'{state["rounds"]} kör · utolsó összpontszám {state["last_total"]}'
                 if state["rounds"] and state["last_total"] is not None
                 else "feldolgozás alatt")
    cost = state["cost"]
    if cost and cost.get("has_data"):
        cost_text = (f'{fmt_dur(cost["wall_clock_s"])} · '
                     f'{cost["total_tokens"]:,} token · ~${cost["total_usd"]:.2f} USD').replace(",", " ")
    else:
        cost_text = "ehhez az érához nincs teljes mért költségadat"
    prev_link = (f'<a href="../{esc(prev_cfg["slug"])}/">← előző kérdés</a>'
                 if prev_cfg else "")
    next_link = (f'<a href="../{esc(next_cfg["slug"])}/">következő kérdés →</a>'
                 if next_cfg else "")

    return f'''<!doctype html>
<html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(_pair(question, "hu"))} — Oktatáspolitikai Atlasz</title>
<meta name="description" content="{esc(brief["problem_statement"]["hu"][:150])}">
<link rel="stylesheet" href="../../assets/atlas.css"></head>
<body class="atlas">
<header class="site-header"><div class="atlas-shell site-header__inner">
  <a class="site-brand" href="../../index.html"><span class="site-brand__mark" aria-hidden="true"></span><span class="site-brand__name">Oktatáspolitikai<br>Atlasz</span></a>
  <button class="nav-toggle" type="button" data-nav-toggle aria-expanded="false" aria-controls="site-nav">Menü</button>
  <nav class="site-nav" id="site-nav" data-site-nav><a href="../../index.html#temak">Kérdések</a><a href="../../about.html">Az Atlaszról</a><a href="../../tech.html">Módszertan</a><div class="lang-switch"><button type="button" data-set-lang="hu" aria-pressed="true">HU</button><button type="button" data-set-lang="en" aria-pressed="false">EN</button></div></nav>
</div></header>
<main>
  <section class="topic-hero"><div class="atlas-shell topic-hero__grid">
    <div><p class="atlas-kicker">Döntési dosszié {num:02d} / {total:02d}</p>{_both(question, "h1")}</div>
    <div class="topic-hero__summary">{_both(brief["problem_statement"], "p", "atlas-lede")}<div class="topic-meta"><span>{len(scenarios) or len(cfg.get("frames", {}).get("scenarios", []))} válaszút</span><span>{esc(status)}</span><span>{esc(run_state)}</span></div></div>
  </div></section>
  <nav class="topic-local-nav" aria-label="A kérdésoldal fejezetei"><div class="atlas-shell topic-local-nav__inner"><a href="#kerdes">A kérdés</a><a href="#valaszutak">Válaszutak</a><a href="#vitak">Viták</a><a href="#rekord">Forrás és audit</a></div></nav>
  <section class="atlas-section atlas-section--paper" id="kerdes"><div class="atlas-shell problem-grid">
    <div><p class="atlas-kicker">A vizsgálat fókusza</p><h2>{esc(brief["title"]["hu"])}</h2><div class="scope-box"><h3>Hatókör / Scope</h3>{_both(brief["scope"], "p")}</div></div>
    <div><h3>Mit kell megérteni a döntés előtt?</h3><ol class="learning-list">{goals}</ol></div>
  </div></section>
  <section class="atlas-section atlas-section--paper" id="valaszutak"><div class="atlas-shell">
    <div class="catalog-head"><div><p class="atlas-kicker">Opciótér</p><h2>Lehetséges válaszutak.</h2></div><p class="atlas-note">A kereteket a szakértői elemzésből származtatjuk, majd emberi jóváhagyással rögzítjük. Minden út saját oldalon, teljes részletességgel olvasható.</p></div>
    <div class="option-route">{scenario_cards}</div>
  </div></section>
  {findings_html}
  <section class="atlas-section atlas-section--paper" id="rekord"><div class="atlas-reading"><p class="atlas-kicker">Forrás, módszer, költség</p><h2>A teljes munkafolyamat nyilvános.</h2><p>A közzétett anyag a(z) {round_n or "—"}. kör adatából készült. Mért feldolgozás: {esc(cost_text)}.</p><div class="disclosure-links"><a class="text-link" href="explorer.html">Teljes érv- és bizonyítékfeltáró</a><a class="text-link" href="audit.html">Műhely-napló: minden kutatás és elutasítás</a><a class="text-link" href="https://github.com/halacsy/education-policy-lab/tree/main/outputs/topics/{esc(slug)}">Nyers rekord a GitHubon</a></div></div></section>
</main>
<footer class="site-footer"><div class="atlas-shell"><div class="site-footer__grid"><h2>{esc(_pair(question, "hu"))}</h2><nav>{prev_link}{next_link}<a href="../../index.html#temak">Összes kérdés</a></nav><nav><a href="../../about.html">Az Atlaszról</a><a href="../../tech.html">Módszertan</a></nav></div><p class="site-footer__meta">GENERÁLT DÖNTÉSI DOSSZIÉ · FORRÁS: topics/{esc(slug)}/topic.json + outputs/topics/{esc(slug)}/</p></div></footer>
<script src="../../assets/atlas.js"></script></body></html>'''


def _bullet_items(items, kind="pair"):
    out = []
    for item in items or []:
        if kind == "evidenced":
            out.append(f'<li><div>{_both(item.get("text", ""), "p")}{evidence_tag(item.get("evidence"))}</div></li>')
        else:
            out.append(f'<li>{_both(item, "span")}</li>')
    return "".join(out)


def scenario_page(cfg, scenario, scenarios, round_n):
    slug = cfg["slug"]
    question = cfg["problem_brief"].get("public_question", cfg["problem_brief"]["title"])
    problem = cfg["problem_brief"]["problem_statement"]
    def problem_excerpt(text, limit=280):
        first = text.split(". ", 1)[0].strip()
        if first and not first.endswith("."):
            first += "."
        if len(first) <= limit:
            return first
        return first[:limit - 1].rsplit(" ", 1)[0] + "…"
    problem_short = {lang: problem_excerpt(problem[lang])
                     for lang in ("hu", "en")}
    idx = scenarios.index(scenario)
    label = scenario.get("evidence_status", {}).get("label", "weak")
    evidence_note = scenario.get("evidence_status", {}).get("note", "")
    implementation = "".join(f'''<li><span class="implementation__time">{esc(_pair(step.get("timeline"), "hu"))}</span><div><strong>{esc(_pair(step.get("actor"), "hu"))}</strong>{_both(step.get("action"), "p")}</div></li>''' for step in scenario.get("implementation_steps", []))
    uncertainties = "".join(f'''<article class="uncertainty-card"><span class="question-card__context">bizonyosság: {esc(u.get("confidence", "—"))}</span>{_both(u.get("text"), "p")}<p class="atlas-note"><strong>Mi csökkentené?</strong> {esc(_pair(u.get("reduced_by"), "hu"))}</p></article>''' for u in scenario.get("uncertainties", []))
    prev_link = (f'<a href="{esc(scenarios[idx - 1]["id"].lower())}.html">← {esc(scenarios[idx - 1]["id"])}</a>' if idx else "")
    next_link = (f'<a href="{esc(scenarios[idx + 1]["id"].lower())}.html">{esc(scenarios[idx + 1]["id"])} →</a>' if idx + 1 < len(scenarios) else "")
    return f'''<!doctype html><html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(scenario["id"])} — {esc(_pair(scenario["title"], "hu"))} — Oktatáspolitikai Atlasz</title><meta name="description" content="{esc(_pair(scenario["goal"], "hu")[:155])}"><link rel="stylesheet" href="../../../assets/atlas.css"></head>
<body class="atlas scenario-page"><header class="site-header"><div class="atlas-shell site-header__inner"><a class="site-brand" href="../../../index.html"><span class="site-brand__mark" aria-hidden="true"></span><span class="site-brand__name">Oktatáspolitikai<br>Atlasz</span></a><button class="nav-toggle" type="button" data-nav-toggle aria-expanded="false" aria-controls="site-nav">Menü</button><nav class="site-nav" id="site-nav" data-site-nav><a href="../">← Kérdésoldal</a><a href="../explorer.html#{esc(scenario["id"])}">Érvek és kritikák</a><div class="lang-switch"><button type="button" data-set-lang="hu" aria-pressed="true">HU</button><button type="button" data-set-lang="en" aria-pressed="false">EN</button></div></nav></div></header>
<main>
  <section class="scenario-origin" aria-labelledby="scenario-origin-title"><div class="atlas-shell scenario-origin__grid">
    <p class="scenario-origin__label" id="scenario-origin-title"><span data-lang="hu">Kiinduló probléma</span><span data-lang="en">The problem</span></p>
    <a class="scenario-origin__question" href="../">{_both(question)}</a>
    <div class="scenario-origin__summary">{_both(problem_short, "p")}<a href="../#kerdes"><span data-lang="hu">A teljes probléma és az összes válaszút →</span><span data-lang="en">Full problem and all available routes →</span></a></div>
  </div></section>
  <section class="topic-hero"><div class="atlas-shell topic-hero__grid"><div><p class="atlas-kicker">{esc(scenario["id"])} · {idx + 1}/{len(scenarios)}. válaszút</p>{_both(scenario["title"], "h1")}</div><div class="topic-hero__summary">{_both(scenario["goal"], "p", "atlas-lede")}<div class="topic-meta">{evidence_tag(label)}<span>{round_n}. kör</span></div></div></div></section>
  <nav class="topic-local-nav"><div class="atlas-shell topic-local-nav__inner"><a href="#mukodes">Működés</a><a href="#merleg">Előnyök és méltányosság</a><a href="#vegigvitel">Megvalósítás</a><a href="#kockazatok">Kockázatok</a><a href="#nyitott">Bizonytalanságok</a></div></nav>
  <section class="atlas-section atlas-section--paper" id="mukodes"><div class="atlas-shell detail-grid"><div><p class="atlas-kicker">Mechanizmus</p><h2>Hogyan működne?</h2><p class="atlas-note">Az egyes elemek saját bizonyítékfokozatot viselnek.</p></div><ol class="detail-list detail-list--evidenced">{_bullet_items(scenario.get("mechanism"), "evidenced")}</ol></div></section>
  <section class="atlas-section" id="merleg"><div class="atlas-shell"><div class="catalog-head"><div><p class="atlas-kicker">Mérleg</p><h2>Mit nyerhetünk — és kinek?</h2></div><div>{evidence_tag(label)}{_both(evidence_note, "p", "atlas-note")}</div></div><div class="detail-columns"><div><h3>Várható előnyök</h3><ol class="detail-list detail-list--evidenced">{_bullet_items(scenario.get("expected_benefits"), "evidenced")}</ol></div><div><h3>Méltányossági hatás</h3><div class="callout-box">{_both(scenario.get("equity_impact"), "p")}</div><h3>Költségkategóriák</h3><ul class="detail-list">{_bullet_items(scenario.get("cost_categories"))}</ul></div></div></div></section>
  <section class="atlas-section atlas-section--paper" id="vegigvitel"><div class="atlas-shell detail-grid"><div><p class="atlas-kicker">Megvalósítás</p><h2>Ki, mit, mikor?</h2></div><ol class="implementation">{implementation}</ol></div></section>
  <section class="atlas-section" id="kockazatok"><div class="atlas-shell detail-columns"><div><p class="atlas-kicker atlas-kicker--dissent">Feltételezések</p><h2>Minek kell igaznak lennie?</h2><ul class="detail-list">{_bullet_items(scenario.get("assumptions"))}</ul></div><div><p class="atlas-kicker atlas-kicker--dissent">Politikai kockázatok</p><h2>Hol akadhat el?</h2><ul class="detail-list detail-list--risk">{_bullet_items(scenario.get("political_risks"))}</ul></div></div></section>
  <section class="atlas-section atlas-section--paper" id="nyitott"><div class="atlas-shell"><div class="catalog-head"><div><p class="atlas-kicker atlas-kicker--dissent">Nyitott kérdések</p><h2>Amit még nem tudunk.</h2></div><p class="atlas-note">Minden bizonytalanság mellett ott van az a kutatás vagy adat, amely csökkenthetné.</p></div><div class="uncertainty-grid">{uncertainties}</div><div class="disclosure-links"><a class="button-link" href="../explorer.html#{esc(scenario["id"])}">Az út kritikái és teljes bizonyítékai →</a><a class="text-link" href="https://github.com/halacsy/education-policy-lab/blob/main/outputs/topics/{esc(slug)}/iterations/round_{round_n:02d}/scenarios.json">Nyers forgatókönyv-rekord</a></div></div></section>
</main><footer class="site-footer"><div class="atlas-shell"><div class="site-footer__grid"><h2>{esc(_pair(question, "hu"))}</h2><nav>{prev_link}{next_link}<a href="../">Összes válaszút</a></nav><nav><a href="../explorer.html#{esc(scenario["id"])}">Érvek és kritikák</a><a href="../audit.html">Műhely-napló</a></nav></div><p class="site-footer__meta">{esc(slug)} · {esc(scenario["id"])} · {round_n}. KÖR · GENERÁLT OLDAL</p></div></footer><script src="../../../assets/atlas.js"></script></body></html>'''


def write_scenario_pages(cfg):
    round_n, scenarios = latest_scenarios(cfg["slug"])
    if not scenarios:
        return 0
    out_dir = ROOT / "site" / "topics" / cfg["slug"] / "scenarios"
    out_dir.mkdir(parents=True, exist_ok=True)
    for scenario in scenarios:
        dest = out_dir / f'{scenario["id"].lower()}.html'
        dest.write_text(scenario_page(cfg, scenario, scenarios, round_n), encoding="utf-8")
        print(f"wrote {dest}")
    return len(scenarios)


def inject_index_cards(cards_html):
    idx = ROOT / "site" / "index.html"
    text = idx.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(<!-- TOPICS:START[^>]*-->).*?(<!-- TOPICS:END -->)", re.S)
    if not pattern.search(text):
        print("WARNING: TOPICS markers missing from site/index.html — "
              "card list not injected", file=sys.stderr)
        return False
    new = pattern.sub(lambda m: m.group(1) + "\n" + cards_html + "\n    "
                      + m.group(2), text)
    idx.write_text(new, encoding="utf-8")
    return True


def atlas_inventory(topics):
    """Render the public collection-level contents from committed records.

    These are not promotional counters: every number is derived from the
    same per-topic artifacts that feed the topic, scenario and explorer
    pages. The inventory therefore grows automatically with the Atlas.
    """
    totals = {"topics": len(topics), "scenarios": 0, "arguments": 0,
              "dilemmas": 0, "axes": 0, "experts": 0,
              "unknowns": 0, "facts": 0}
    first_slug = topics[0]["slug"] if topics else ""
    first_scenario = "s1"
    for cfg in topics:
        slug = cfg["slug"]
        _, scenarios = latest_scenarios(slug)
        totals["scenarios"] += len(scenarios)
        totals["unknowns"] += sum(len(s.get("uncertainties", []))
                                  for s in scenarios)
        if scenarios and not first_scenario:
            first_scenario = scenarios[0]["id"].lower()
        findings = load_findings(slug)
        if not findings:
            continue
        sd = findings["sd"]
        totals["arguments"] += len(sd["clusters"])
        totals["axes"] += len(findings["axes"])
        totals["experts"] += len(findings["experts"])
        for cluster in sd["clusters"]:
            verdict = sd["verdicts"].get(cluster["id"])
            if verdict and VERDICT_GROUP[verdict["response_type"]] == "human":
                totals["dilemmas"] += 1
    registry = ROOT / "knowledge" / "registry.json"
    if registry.exists():
        try:
            totals["facts"] = len(json.loads(
                registry.read_text(encoding="utf-8")).get("facts", {}))
        except (json.JSONDecodeError, OSError):
            pass

    first_topic = f"topics/{esc(first_slug)}/" if first_slug else "#temak"
    rows = [
        ("topics", "döntési kérdés", "decision questions",
         "Mindegyik önálló probléma-leírással, scope-pal és ember által jóváhagyott opciótérrel.",
         "Each has its own problem brief, scope and human-approved option space.",
         "#temak"),
        ("scenarios", "részletes válaszút", "detailed response routes",
         "Cél, mechanizmus, előny, méltányosság, költség, végrehajtás, kockázat és bizonytalanság.",
         "Goal, mechanism, benefits, equity, cost, implementation, risk and uncertainty.",
         f"{first_topic}#valaszutak"),
        ("arguments", "összevont érvklaszter", "consolidated argument clusters",
         "Érdek, érték, félelem, érintett csoport, feltevés és döntési relevancia szerint felbontva.",
         "Decomposed by interest, value, fear, affected group, assumption and decision relevance.",
         f"{first_topic}explorer.html#diskurzus"),
        ("dilemmas", "emberi döntést kérő dilemma", "dilemmas requiring human judgement",
         "Amit több evidencia vagy jobb technikai tervezés sem dönthet el helyettünk.",
         "Questions that neither more evidence nor better technical design can decide for us.",
         f"{first_topic}#vitak"),
        ("axes", "megőrzött nézeteltérési tengely", "preserved disagreement axes",
         "A szakértői többség és kisebbség indoklása egymás mellett, kényszerkonszenzus nélkül.",
         "Expert majority and minority reasoning side by side, without forced consensus.",
         f"{first_topic}explorer.html#nezetelteres"),
        ("experts", "szakértői kutatási dosszié", "expert research dossiers",
         "Teljes elemzések, keresések és források — nem csak a végső összefoglaló.",
         "Full analyses, searches and sources—not merely the final synthesis.",
         f"{first_topic}#szakertok"),
        ("unknowns", "kimondott bizonytalanság", "explicit unknowns",
         "Mindegyik mellett ott van, milyen adat vagy kutatás csökkenthetné.",
         "Each states what data or research could reduce it.",
         f"{first_topic}scenarios/{first_scenario}.html#nyitott"),
        ("facts", "emberileg kurált evidencia-tétel", "human-curated evidence records",
         "Forrással, bizonyítékfokozattal és kétnyelvű állítással; bővítés csak emberi kapun át.",
         "With source, evidence grade and bilingual claim; admission remains human-gated.",
         "knowledge.html"),
    ]
    row_html = "\n".join(f'''<a class="inventory-row" href="{href}">
      <span class="inventory-row__count">{totals[key]}</span>
      <span class="inventory-row__name"><span data-lang="hu">{hu}</span><span data-lang="en">{en}</span></span>
      <span class="inventory-row__description"><span data-lang="hu">{hu_desc}</span><span data-lang="en">{en_desc}</span></span>
      <span class="inventory-row__arrow" aria-hidden="true">→</span>
    </a>''' for key, hu, en, hu_desc, en_desc, href in rows)
    return f'''<div class="inventory-head">
      <div>
        <p class="atlas-kicker" data-lang="hu">Az Atlasz jelenlegi állománya</p>
        <p class="atlas-kicker" data-lang="en">What the Atlas contains today</p>
        <h2 data-lang="hu">{totals["topics"]} kérdés — de nem {totals["topics"]} cikk.</h2>
        <h2 data-lang="en">{totals["topics"]} questions—but not {totals["topics"]} articles.</h2>
      </div>
      <div class="inventory-head__note">
        <p class="atlas-lede" data-lang="hu">Minden kérdés mögött egy bejárható, forrásokkal hivatkozott döntési adatbázis áll.</p>
        <p class="atlas-lede" data-lang="en">Behind every question sits a navigable decision database with traceable sources.</p>
      </div>
    </div>
    <div class="inventory-ledger">{row_html}</div>
    <div class="inventory-foot"><span>Élő állományjegyzék · a publikált rekordokból generálva</span><span>Nem kézzel vezetett számlálók</span></div>'''


def inject_index_inventory(inventory_html):
    idx = ROOT / "site" / "index.html"
    text = idx.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(<!-- ATLAS-INVENTORY:START[^>]*-->).*?"
        r"(<!-- ATLAS-INVENTORY:END -->)", re.S)
    if not pattern.search(text):
        print("WARNING: ATLAS-INVENTORY markers missing from site/index.html",
              file=sys.stderr)
        return False
    new = pattern.sub(lambda m: m.group(1) + "\n" + inventory_html + "\n        "
                      + m.group(2), text)
    idx.write_text(new, encoding="utf-8")
    return True


def main():
    topics = topic_order(TOPICS_DIR)
    total = len(topics)
    cards = []
    for i, cfg in enumerate(topics):
        slug = cfg["slug"]
        state = topic_state(slug)
        out = ROOT / "site" / "topics" / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(topic_page(cfg, state, i + 1, total,
                                  topics[i - 1] if i else None,
                                  topics[i + 1] if i + 1 < total else None),
                       encoding="utf-8")
        write_scenario_pages(cfg)
        write_finding_pages(cfg)
        write_expert_pages(cfg)
        cards.append(topic_card(cfg, state, i + 1))
        print(f"wrote {out}")
    inject_index_cards("\n".join(cards))
    inject_index_inventory(atlas_inventory(topics))
    print(f"injected {len(cards)} topic card(s) into site/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
