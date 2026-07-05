#!/usr/bin/env python3
"""Generate the public, bilingual knowledge-base page (site/knowledge.html)
from the canonical source registry (knowledge/registry.json) and the
terminology glossary (docs/glossary.md).

Run by the GitHub Pages workflow on every deploy — the page is generated from
repo data, never hand-maintained (issue #3). Standard library only."""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EVIDENCE_HU = {"strong": "erős", "moderate": "mérsékelt", "weak": "gyenge",
               "contested": "vitatott"}

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
  a { color: var(--evidence); text-underline-offset:2px; }
  a:focus-visible { outline:2px solid var(--evidence); outline-offset:2px; }
  .eyebrow { font-family: ui-monospace,'SF Mono',Menlo,monospace; font-size:.72rem;
             letter-spacing:.14em; text-transform:uppercase; color:var(--evidence);
             margin:0 0 .75rem; }
  header.site { border-bottom:1px solid var(--line); padding:1rem 0;
                font-family: ui-monospace,'SF Mono',Menlo,monospace; font-size:.8rem; }
  header.site .wrap { display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; }
  section { padding: 2.75rem 0; border-bottom: 1px solid var(--line); }
  .fact { background:#fff; border:1px solid var(--line); border-radius:6px;
          padding:1.2rem 1.35rem; margin-bottom:1rem; }
  .fact .hu { margin:0 0 .6rem; }
  .fact .en { margin:0 0 .8rem; color:var(--muted); font-size:.94rem; }
  .fact .metaline { display:flex; gap:.6rem; flex-wrap:wrap; align-items:center;
          font-family: ui-monospace,Menlo,monospace; font-size:.72rem; color:var(--muted); }
  .tag { display:inline-block; padding:.1rem .45rem; border:1px solid var(--line);
         border-radius:3px; background:#fff; }
  .tag.strong    { color:var(--evidence); border-color:var(--evidence); }
  .tag.moderate  { color:var(--ink); }
  .tag.weak      { color:var(--muted); border-style:dashed; }
  .tag.contested { color:var(--dissent); border-color:var(--dissent); }
  .tablebox { overflow-x:auto; border:1px solid var(--line); border-radius:6px; background:#fff; }
  table { border-collapse:collapse; width:100%; font-size:.9rem; }
  th,td { padding:.5rem .8rem; border-bottom:1px solid var(--line); text-align:left; }
  tr:last-child td { border-bottom:none; }
  thead th { font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;
             font-size:.78rem; letter-spacing:.04em; }
  .note { font-size:.85rem; color: var(--muted); }
  footer { padding:2rem 0 3rem; font-size:.85rem; color:var(--muted); }
"""


def load_glossary_rows():
    rows, in_main = [], False
    for line in (ROOT / "docs" / "glossary.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## Evidence-status"):
            in_main = False
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|?$", line)
        if line.startswith("| English"):
            in_main = True
            continue
        if in_main and m and not set(m.group(1)) <= set("-: "):
            rows.append((m.group(1), m.group(2), m.group(3)))
    return rows


def main():
    reg = json.loads((ROOT / "knowledge" / "registry.json").read_text(encoding="utf-8"))
    facts = reg["facts"]
    e = html.escape

    repo = "https://github.com/halacsy/education-policy-lab/tree/main"
    fact_cards = []
    for fid, f in facts.items():
        ev = f["evidence"]
        used = ", ".join(f.get("used_by", [])) or "—"
        lib = f.get("library_doc")
        lib_html = (f'<a href="{repo}/{e(lib)}">teljes dokumentum</a>'
                    if lib else "")
        fact_cards.append(f"""
    <article class="fact" id="{e(fid)}">
      <p class="hu">{e(f['hu'])}</p>
      <p class="en">{e(f['en'])}</p>
      <p class="metaline">
        <span class="tag {e(ev)}">bizonyíték: {e(EVIDENCE_HU.get(ev, ev))} / {e(ev)}</span>
        <span>forrás: {e(f['source'])}</span>
        <span>használja: {e(used)}</span>
        {lib_html}
      </p>
    </article>""")

    gl_rows = "\n".join(
        f"      <tr><td>{e(en)}</td><td>{e(hu)}</td><td class=\"note\">{e(note)}</td></tr>"
        for en, hu, note in load_glossary_rows())

    page = f"""<!DOCTYPE html>
<html lang="hu">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tudásbázis — Education Policy Lab</title>
<meta name="description" content="A műhely kurált forrásjegyzéke: minden tény bizonyítékstátusszal és forrással, magyarul és angolul.">
<style>{CSS}</style>
</head>
<body>
<header class="site">
  <div class="wrap">
    <span><strong>EDUCATION POLICY LAB</strong> · tudásbázis</span>
    <span><a href="./">← vissza a főoldalra</a></span>
  </div>
</header>

<section>
  <div class="wrap">
    <p class="eyebrow">Kurált forrásjegyzék</p>
    <h1>Milyen tudásból dolgozik a rendszer?</h1>
    <p>Az alábbi jegyzék a műhely <strong>kurált tényregisztere</strong>
    (<code>knowledge/registry.json</code>): ezekre a tényekre alapoznak a
    szakértő-ágensek, ehhez képest ellenőrzi a bizonyítékcímkéket a
    bizonyíték-ellenőr kritikus, és ez az oldal is közvetlenül ebből a
    registerből generálódik minden publikáláskor — kézzel nem szerkeszthető.
    Minden tényen bizonyítékstátusz és forrás van; ami ezen túl a nyelvi
    modellek saját tudásából származik, azt a rendszer külön jelöli.</p>
    <p class="note">Jelenleg {len(facts)} tény, {len(load_glossary_rows())} szakkifejezés.
    A register bővítése pull requesttel történik, a bizonyítékfokozatok
    szabályai a <a href="https://github.com/halacsy/education-policy-lab/blob/main/templates/evaluation_rubric.md">rubrikában</a>.</p>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Tények ({len(facts)})</h2>
{"".join(fact_cards)}
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Ellenőrzött terminológia (HU ↔ EN)</h2>
    <p class="note">A fordító-ágens ezt a szószedetet köteles használni; a
    fordítás-ellenőr gépi ellenőrzéssel kényszeríti ki.</p>
    <div class="tablebox"><table>
      <thead><tr><th>English</th><th>Magyar</th><th>Megjegyzés</th></tr></thead>
      <tbody>
{gl_rows}
      </tbody>
    </table></div>
  </div>
</section>

<footer>
  <div class="wrap">
    <p>Generálva a <a href="https://github.com/halacsy/education-policy-lab">repóból</a>
    (knowledge/registry.json + docs/glossary.md) minden publikáláskor.</p>
  </div>
</footer>
</body>
</html>
"""
    out = ROOT / "site" / "knowledge.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(facts)} facts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
