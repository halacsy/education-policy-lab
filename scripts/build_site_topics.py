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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from lab.site_data import (VERDICT_HU, VERDICT_GROUP, is_gumicsont,
                           last_round, list_experts,
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


def load_findings(slug):
    """The last round's structured discourse record for the "what the
    system surfaced" section; None when the topic has no D-34 round yet."""
    it = OUT_ROOT / slug / "iterations"
    if not it.exists():
        return None
    n = last_round(it)
    if n is None:
        return None
    rd = it / f"round_{n:02d}"
    sd = load_structured_discourse(rd)
    if not sd:
        return None
    return dict(round=n, sd=sd,
                axes=load_structured_disagreements(rd) or [],
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
        f'<a class="chip" href="explorer.html#expert-{esc(n)}">{esc(n)}</a>'
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
      <div class="topic-entry__index"><span>Atlaszlap</span><strong>{num:02d}</strong></div>
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
        f'''<li><a href="explorer.html#cluster-{esc(c["id"])}">
          <span class="finding-list__id">{esc(c["id"])}</span>
          <span>{esc(c["claim"])}<small>{esc(VERDICT_HU[v["response_type"]])} · teljes érv és válasz →</small></span>
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
            f'''<li><a href="explorer.html#axis-{i + 1}"><span class="finding-list__id">V{i + 1:02d}</span><span>{esc(ax["topic"])}<small>Mindkét álláspont indoklása →</small></span></a></li>'''
            for i, ax in enumerate(f["axes"]))
        axes_html = f'''<div class="finding-group">
          <div class="finding-group__head"><h3>Ahol a szakértők nem értenek egyet</h3><p class="atlas-note">A különvélemény nem tűnik el a szintézisben.</p></div>
          <ul class="finding-list">{items}</ul>
        </div>'''

    expert_links = "".join(
        f'<a href="explorer.html#expert-{esc(name)}">{esc(name.replace("_", " "))}</a>'
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
        <div class="finding-group"><div class="finding-group__head"><h3>A szakértői rekord</h3><p class="atlas-note">A teljes elemzések közvetlenül megnyithatók.</p></div><div class="expert-links">{expert_links}</div></div>
      </div>
    </section>'''


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
    prev_link = (f'<a href="../{esc(prev_cfg["slug"])}/">← előző atlaszlap</a>'
                 if prev_cfg else "")
    next_link = (f'<a href="../{esc(next_cfg["slug"])}/">következő atlaszlap →</a>'
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
    <div><p class="atlas-kicker">Atlaszlap {num:02d} / {total:02d}</p>{_both(question, "h1")}</div>
    <div class="topic-hero__summary">{_both(brief["problem_statement"], "p", "atlas-lede")}<div class="topic-meta"><span>{len(scenarios) or len(cfg.get("frames", {}).get("scenarios", []))} válaszút</span><span>{esc(status)}</span><span>{esc(run_state)}</span></div></div>
  </div></section>
  <nav class="topic-local-nav" aria-label="Az atlaszlap fejezetei"><div class="atlas-shell topic-local-nav__inner"><a href="#kerdes">A kérdés</a><a href="#valaszutak">Válaszutak</a><a href="#vitak">Viták</a><a href="#rekord">Forrás és audit</a></div></nav>
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
<footer class="site-footer"><div class="atlas-shell"><div class="site-footer__grid"><h2>{esc(_pair(question, "hu"))}</h2><nav>{prev_link}{next_link}<a href="../../index.html#temak">Összes kérdés</a></nav><nav><a href="../../about.html">Az Atlaszról</a><a href="../../tech.html">Módszertan</a></nav></div><p class="site-footer__meta">GENERÁLT ATLASZLAP · FORRÁS: topics/{esc(slug)}/topic.json + outputs/topics/{esc(slug)}/</p></div></footer>
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
<body class="atlas scenario-page"><header class="site-header"><div class="atlas-shell site-header__inner"><a class="site-brand" href="../../../index.html"><span class="site-brand__mark" aria-hidden="true"></span><span class="site-brand__name">Oktatáspolitikai<br>Atlasz</span></a><button class="nav-toggle" type="button" data-nav-toggle aria-expanded="false" aria-controls="site-nav">Menü</button><nav class="site-nav" id="site-nav" data-site-nav><a href="../">← Atlaszlap</a><a href="../explorer.html#{esc(scenario["id"])}">Érvek és kritikák</a><div class="lang-switch"><button type="button" data-set-lang="hu" aria-pressed="true">HU</button><button type="button" data-set-lang="en" aria-pressed="false">EN</button></div></nav></div></header>
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
         f"{first_topic}explorer.html#szakertok"),
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
        cards.append(topic_card(cfg, state, i + 1))
        print(f"wrote {out}")
    inject_index_cards("\n".join(cards))
    inject_index_inventory(atlas_inventory(topics))
    print(f"injected {len(cards)} topic card(s) into site/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
