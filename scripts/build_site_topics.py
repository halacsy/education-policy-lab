#!/usr/bin/env python3
"""Generate the public topic pages (D-35, sprint deliverable 5).

For every topic in topics/*/topic.json:
- site/topics/<slug>/index.html — the topic's page: problem brief, frozen
  frames, run state, transparency (time/token/cost from the final
  cost_report.json), links to the explorer page and the raw record;
- the topic-card list injected between the TOPICS:START/END markers in
  site/index.html (the committed landing page keeps the general "how it
  works" content; the card list is regenerated on every deploy).

Run by the Pages workflow on every deploy — generated from repo data,
never hand-maintained. Standard library only."""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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
"""


def esc(x):
    return html.escape(str(x), quote=True)


def load_topics():
    topics = []
    for p in sorted(TOPICS_DIR.glob("*/topic.json")):
        topics.append(json.loads(p.read_text(encoding="utf-8")))
    return topics


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


def topic_card(cfg, state):
    slug = cfg["slug"]
    b = cfg["problem_brief"]
    status = STATUS_HU.get(cfg.get("status", "active"), cfg.get("status"))
    meta = [f"állapot: {esc(status)}"]
    if state["rounds"]:
        meta.append(f"{state['rounds']} kör az aktuális érában")
    if state["last_total"] is not None:
        meta.append(f"utolsó összpontszám: {state['last_total']}")
    meta.append(cost_line(state))
    frames = cfg.get("frames", {}).get("scenarios", [])
    frames_html = ""
    if frames:
        frames_html = ("<p class=\"note\">Keretek: "
                       + " · ".join(f"<strong>{esc(f['id'])}</strong> "
                                    f"{esc(f['title']['hu'])}"
                                    for f in frames) + "</p>")
    return f"""    <div class="card">
      <h3><a href="topics/{esc(slug)}/">{esc(b['title']['hu'])}</a></h3>
      <p>{esc(b['problem_statement']['hu'])}</p>
      {frames_html}
      <p class="note">{esc(' · '.join(meta))}</p>
      <p style="margin-bottom:0"><a href="topics/{esc(slug)}/"><strong>Téma-oldal megnyitása →</strong></a></p>
    </div>"""


def topic_page(cfg, state):
    slug = cfg["slug"]
    b = cfg["problem_brief"]
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
        links.append('<a href="explorer.html"><strong>Forgatókönyv-feltáró '
                     'megnyitása →</strong></a>')
        links.append(f'<a href="https://github.com/halacsy/education-policy-lab/'
                     f'blob/main/outputs/topics/{esc(slug)}/final/final_brief.hu.md">'
                     'Záró összefoglaló (HU, nyers) →</a>')
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
    <span>téma: <code>{esc(slug)}</code> · állapot: {esc(status)}</span>
  </div>
</header>

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


def main():
    topics = load_topics()
    cards = []
    for cfg in topics:
        slug = cfg["slug"]
        state = topic_state(slug)
        out = ROOT / "site" / "topics" / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(topic_page(cfg, state), encoding="utf-8")
        cards.append(topic_card(cfg, state))
        print(f"wrote {out}")
    inject_index_cards("\n".join(cards))
    print(f"injected {len(cards)} topic card(s) into site/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
