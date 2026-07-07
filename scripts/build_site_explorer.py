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
FINAL = ROOT / "outputs" / "final"
ITER = ROOT / "outputs" / "iterations"

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

DIS_TOPIC_RE = re.compile(r"^### (.+)$", re.M)
DIS_SIDE_RE = re.compile(
    r"^- \*\*(.+?)\*\*(\s*\(minority\))?:\s*(.+?)\s+Why:\s*(.+)$", re.M)

POSITION_RE = re.compile(r"## Position\s*\n(.+?)(?:\n##|\Z)", re.S)


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


def parse_disagreement_map(synthesis_text):
    m = re.search(r"## Disagreement map\s*\n(.*?)(?:\n## (?!#)|\Z)",
                  synthesis_text, re.S)
    body = m.group(1) if m else ""
    topics = []
    chunks = re.split(r"(?=^### )", body, flags=re.M)
    for chunk in chunks:
        tm = DIS_TOPIC_RE.match(chunk.strip())
        if not tm:
            continue
        sides = []
        for sm in DIS_SIDE_RE.finditer(chunk):
            holders = [h.strip() for h in sm.group(1).split(",")]
            sides.append(dict(holders=holders, minority=bool(sm.group(2)),
                              position=sm.group(3).strip(),
                              rationale=sm.group(4).strip()))
        if sides:
            topics.append(dict(topic=tm.group(1).strip(), sides=sides))
    return topics


def parse_expert(text):
    m = POSITION_RE.search(text)
    position = m.group(1).strip() if m else ""
    return position


def render_field(v):
    if isinstance(v, list):
        return "<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in v) + "</ul>"
    return f"<p>{html.escape(v)}</p>"


def main():
    n = last_round()
    rd = ITER / f"round_{n:02d}"
    e = html.escape

    scen_en = json.loads((rd / "scenarios.json").read_text(encoding="utf-8"))
    scen_hu = json.loads((rd / "scenarios.hu.json").read_text(encoding="utf-8"))
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

    synthesis = (rd / "synthesis.md").read_text(encoding="utf-8")
    disagreement = parse_disagreement_map(synthesis)

    experts = {}
    for p in sorted((rd / "expert_outputs").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        experts[p.stem] = dict(position=parse_expert(text), full=text)

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

    def disagreement_card(d):
        sides_html = []
        for side in d["sides"]:
            cls = "minority" if side["minority"] else "majority"
            label = "kisebbségi álláspont" if side["minority"] else "többségi álláspont"
            holders_html = "".join(
                f'<a class="expert-chip" href="#expert-{e(h)}">{e(h)}</a>'
                for h in side["holders"])
            sides_html.append(f"""
      <div class="side {cls}">
        <span class="side-label">{label}</span>
        <div class="holders">{holders_html}</div>
        <p class="position">{e(side['position'])}</p>
        <p class="rationale"><b>Miért:</b> {e(side['rationale'])}</p>
      </div>""")
        return f"""
    <div class="disagreement">
      <h3>{e(d['topic'])}</h3>
      <div class="sides">{''.join(sides_html)}</div>
    </div>"""

    disagreement_html = "".join(disagreement_card(d) for d in disagreement)

    def expert_card(name, data):
        body_html = "<br>".join(e(line) for line in data["full"].splitlines())
        return f"""
    <details class="expert" id="expert-{e(name)}">
      <summary>
        <span class="expert-name">{e(name)}</span>
        <span class="expert-position">{e(data['position'][:140])}</span>
      </summary>
      <div class="expert-full">{body_html}</div>
    </details>"""

    expert_html = "".join(expert_card(k, v) for k, v in experts.items())

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
  .sides { display:grid; gap:.8rem; }
  @media (min-width:700px) { .sides { grid-template-columns:1fr 1fr; } }
  .side { border-radius:6px; padding:.85rem 1rem; border:1px solid var(--line); background:#fff; }
  .side.majority { border-left:3px solid var(--evidence); }
  .side.minority { border-left:3px solid var(--dissent); }
  .side-label { font-family:ui-monospace,Menlo,monospace; font-size:.68rem; text-transform:uppercase;
                letter-spacing:.06em; color:var(--muted); }
  .holders { margin:.3rem 0 .5rem; display:flex; gap:.35rem; flex-wrap:wrap; }
  .expert-chip { font-family:ui-monospace,Menlo,monospace; font-size:.7rem; background:var(--panel);
                 padding:.1rem .45rem; border-radius:3px; text-decoration:none; color:var(--ink); }
  .expert-chip:hover { background:var(--evidence-bg); color:var(--evidence); }
  .position { font-size:.94rem; margin-bottom:.4rem; }
  .rationale { font-size:.84rem; color:var(--muted); margin:0; }

  details.expert { background:#fff; border:1px solid var(--line); border-radius:6px; margin-bottom:.6rem; }
  details.expert summary { list-style:none; cursor:pointer; padding:.75rem 1rem; display:flex; gap:.8rem; align-items:baseline; }
  details.expert summary::-webkit-details-marker { display:none; }
  details.expert summary::before { content:"▸"; color:var(--evidence); }
  details.expert[open] summary::before { content:"▾"; }
  .expert-name { font-family:ui-monospace,Menlo,monospace; font-weight:700; font-size:.86rem; white-space:nowrap; }
  .expert-position { color:var(--muted); font-size:.88rem; }
  .expert-full { border-top:1px solid var(--line); padding:.9rem 1.1rem; font-size:.92rem; }

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

<section id="szakertok">
  <div class="wrap">
    <p class="eyebrow">A teljes szakértői rekord</p>
    <h2>12 szakértő-ágens elemzése, teljes egészében</h2>
    {expert_html}
  </div>
</section>

<footer>
  <div class="wrap">
    <p>Generálva a repóból (<code>outputs/iterations/round_{n:02d}/</code>) minden
    publikáláskor. <a href="https://github.com/halacsy/education-policy-lab/tree/main/outputs/iterations/round_{n:02d}">Nyers adat a GitHubon</a>.</p>
  </div>
</footer>
</body>
</html>
"""
    page = body
    out = ROOT / "site" / "explorer.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} (round {n}: {len(scen_en['scenarios'])} scenarios, "
          f"{len(all_objections)} objections, {len(disagreement)} disagreement "
          f"topics, {len(experts)} experts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
