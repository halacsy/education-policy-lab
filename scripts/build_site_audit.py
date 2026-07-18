#!/usr/bin/env python3
"""Generate the per-topic audit pages (owner direction 2026-07-16: every
step's output must be reviewable on the site — what each expert searched
and found, what it returned, what was rejected and why, when and under
what conditions each round leg started).

For every topic in topics/*/topic.json writes
site/topics/<slug>/audit.html with one section per round (newest first):

- launches (round_meta.json): started_at, resume, providers, fresh_experts;
- run stats (round_log.json): wall clock, tokens, USD estimate, errors;
- research notes (research/*.md): the full sourced notes per seat, URLs
  made clickable;
- expert outputs (expert_outputs/*.json): findings with evidence grade and
  source, position, uncertainties (HU primary, full record linked on
  GitHub);
- rejections (rejections.jsonl): every refused output WITH its reason and
  full text;
- the step journal (steps.jsonl): which backend served each step.

Run by the Pages workflow on every deploy — generated from repo data,
never hand-maintained. Standard library only."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPICS_DIR = ROOT / "topics"
OUT_ROOT = ROOT / "outputs" / "topics"
SITE_TOPICS = ROOT / "site" / "topics"
REPO = "https://github.com/halacsy/education-policy-lab"

CSS = """
  :root { --paper:#F7F8F6; --ink:#1A2321; --muted:#5A6662; --line:#D8DDD9;
          --evidence:#1F6E5C; --dissent:#A34A26; --panel:#EEF1EE; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--paper); color:var(--ink);
         font-family: Charter, Georgia, 'Times New Roman', serif;
         font-size:1rem; line-height:1.55; }
  .wrap { max-width:56rem; margin:0 auto; padding:0 1.25rem; }
  h1,h2,h3,h4 { font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;
                line-height:1.15; letter-spacing:-0.015em; }
  h1 { font-size:clamp(1.5rem,4vw,2.1rem); font-weight:750; margin:0 0 .5rem; }
  h2 { font-size:1.3rem; font-weight:700; margin:0 0 .75rem; }
  h3 { font-size:1rem; font-weight:700; margin:0 0 .5rem; }
  a { color:var(--evidence); text-underline-offset:2px; }
  header.site { border-bottom:1px solid var(--line); padding:1rem 0;
                font-family:ui-monospace,'SF Mono',Menlo,monospace; font-size:.8rem; }
  header.site .wrap { display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; }
  section { padding:2rem 0; border-bottom:1px solid var(--line); }
  .card { background:#fff; border:1px solid var(--line); border-radius:6px;
          padding:1rem 1.2rem; margin-bottom:.9rem; }
  .muted { color:var(--muted); }
  .mono { font-family:ui-monospace,'SF Mono',Menlo,monospace; font-size:.78rem; }
  table { border-collapse:collapse; width:100%; font-size:.9rem; }
  th,td { text-align:left; padding:.3rem .6rem .3rem 0; vertical-align:top;
          border-bottom:1px solid var(--panel); }
  details { margin:.4rem 0; }
  summary { cursor:pointer; font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;
            font-weight:600; font-size:.92rem; }
  details > div, details > pre { border-left:3px solid var(--panel);
            padding:.5rem 0 .5rem .9rem; margin:.4rem 0; }
  pre { white-space:pre-wrap; word-break:break-word; font-size:.82rem;
        font-family:ui-monospace,'SF Mono',Menlo,monospace; }
  .badge { display:inline-block; font-family:ui-monospace,Menlo,monospace;
           font-size:.7rem; padding:.05rem .45rem; border-radius:99px;
           border:1px solid var(--line); background:var(--panel); }
  .badge.warn { border-color:var(--dissent); color:var(--dissent); }
  .badge.ok { border-color:var(--evidence); color:var(--evidence); }
"""


def e(s):
    return html.escape(str(s), quote=True)


def linkify(text):
    """Escape, then turn bare URLs into links (trailing punctuation kept
    outside the anchor)."""
    out = e(text)
    return re.sub(
        r"(https?://[^\s<>&\"')\]]+)",
        r'<a href="\1" rel="noopener">\1</a>', out)


def hu(pair, fallback=""):
    if isinstance(pair, dict):
        return pair.get("hu") or pair.get("en") or fallback
    return pair or fallback


def read_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_jsonl(p):
    rows = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def render_meta(rd):
    meta = read_json(rd / "round_meta.json")
    if not meta:
        return ("<p class='muted'>Ehhez a körhöz még nincs indítás-napló "
                "(a round_meta.json a 2026-07-16-i audit-réteggel jött be)."
                "</p>")
    rows = []
    for s in meta.get("starts", []):
        rows.append(
            "<tr><td class='mono'>{}</td><td>{}</td>"
            "<td class='mono'>{} / {}</td><td>{}</td></tr>".format(
                e(s.get("started_at", "?")),
                "folytatás (resume)" if s.get("resume") else "friss indítás",
                e(s.get("generator_provider", "?")),
                e(s.get("judge_provider", "?")),
                "friss szakértők" if s.get("fresh_experts") else
                "cache engedélyezve"))
    return ("<table><tr><th>indult</th><th>mód</th>"
            "<th>generátor / bíró</th><th>szakértő-cache</th></tr>"
            + "".join(rows) + "</table>")


def render_stats(rd):
    log = read_json(rd / "round_log.json")
    if not log:
        return "<p class='muted'>round_log.json még nincs (a kör fut vagy megszakadt).</p>"
    tok = log.get("tokens", {})
    usd = (log.get("usd_estimate") or {}).get("total_usd")
    wall = log.get("wall_clock_s")
    bits = []
    if wall:
        bits.append(f"falióra: {int(wall) // 60}p {int(wall) % 60}mp")
    if tok:
        bits.append(f"tokenek: {tok.get('total_tokens', '?'):,}".replace(",", " "))
    if usd is not None:
        bits.append(f"becsült USD: ${usd}")
    parts = ["<p>" + " · ".join(bits) + "</p>" if bits else ""]
    errs = log.get("errors") or {}
    if errs:
        rows = "".join(
            f"<tr><td class='mono'>{e(k)}</td><td class='mono'>{e('; '.join(v))}</td></tr>"
            for k, v in errs.items())
        parts.append("<details><summary>Hívás-hibák (retry-k által kezelve)"
                     f" — {len(errs)} task</summary><div><table>{rows}"
                     "</table></div></details>")
    fb = log.get("fallbacks") or []
    if fb:
        parts.append(f"<p class='badge warn'>mock-fallback: {e(', '.join(fb))}</p>")
    return "".join(parts)


def render_research(rd):
    rdir = rd / "research"
    if not rdir.exists():
        return ""
    items = []
    for p in sorted(rdir.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        urls = len(re.findall(r"https?://", text))
        badge = (f"<span class='badge ok'>{urls} URL</span>" if urls
                 else "<span class='badge warn'>0 URL</span>")
        items.append(
            f"<details><summary>{e(p.stem)} {badge}</summary>"
            f"<pre>{linkify(text)}</pre></details>")
    if not items:
        return ""
    return ("<h3>Kutatási jegyzetek (élő web-keresés)</h3>"
            "<p class='muted'>A szakértő strukturált elemzése előtti "
            "keresési fázis teljes, szerkesztetlen kimenete.</p>"
            + "".join(items))


def render_experts(rd, slug, n):
    edir = rd / "expert_outputs"
    if not edir.exists():
        return ""
    items = []
    for p in sorted(edir.glob("*.json")):
        obj = read_json(p)
        if not isinstance(obj, dict):
            continue
        rows = []
        for f in obj.get("findings", []):
            rows.append(
                "<tr><td>{}</td><td class='mono'>{}</td><td class='mono'>{}</td></tr>"
                .format(e(hu(f.get("claim"))), e(f.get("evidence", "?")),
                        linkify(str(f.get("source", "")))))
        finding_tbl = ("<table><tr><th>állítás (HU)</th><th>evidencia</th>"
                       "<th>forrás</th></tr>" + "".join(rows) + "</table>"
                       if rows else "")
        unc = "".join(
            f"<li>{e(hu(u.get('text')))} "
            f"<span class='badge'>{e(u.get('confidence', '?'))}</span></li>"
            for u in obj.get("uncertainties", []))
        gh = (f"{REPO}/blob/main/outputs/topics/{slug}/iterations/"
              f"round_{n:02d}/expert_outputs/{p.name}")
        items.append(
            f"<details><summary>{e(p.stem)}</summary><div>"
            f"<p><strong>Pozíció:</strong> {e(hu(obj.get('position')))}</p>"
            f"{finding_tbl}"
            + (f"<p><strong>Bizonytalanságok:</strong></p><ul>{unc}</ul>"
               if unc else "")
            + f"<p class='mono'><a href='{gh}'>teljes kétnyelvű rekord →</a></p>"
            "</div></details>")
    if not items:
        return ""
    return ("<h3>Szakértői kimenetek</h3>" + "".join(items))


def render_rejections(rd):
    rows = read_jsonl(rd / "rejections.jsonl")
    if not rows:
        return ""
    items = []
    for r in rows:
        items.append(
            "<details><summary>{} · attempt {} · {}</summary>"
            "<p class='mono muted'>ok: {} · backend: {}</p>"
            "<pre>{}</pre></details>".format(
                e(r.get("step", "?")), e(r.get("attempt", "?")),
                e(r.get("ts", "")), e(r.get("reason", "?")),
                e(r.get("backend", "?")), linkify(r.get("output", ""))))
    return ("<h3>Elutasított kimenetek</h3>"
            "<p class='muted'>Amit a validátorok visszadobtak, az okkal és "
            "a teljes szöveggel — az ágens-fejlesztés nyersanyaga "
            "(#26).</p>" + "".join(items))


def render_steps(rd):
    rows = read_jsonl(rd / "steps.jsonl")
    if not rows:
        return ""
    tr = "".join(
        "<tr><td class='mono'>{}</td><td class='mono'>{}</td></tr>".format(
            e(r.get("step", "?")), e(r.get("backend", "?")))
        for r in rows)
    return ("<details><summary>Lépés-journal "
            f"({len(rows)} bejegyzés)</summary><div><table>"
            "<tr><th>lépés</th><th>backend</th></tr>"
            + tr + "</table></div></details>")


def build_topic(slug, title):
    out_dir = OUT_ROOT / slug / "iterations"
    rounds = sorted(out_dir.glob("round_*"), reverse=True) if out_dir.exists() else []
    sections = []
    for rd in rounds:
        try:
            n = int(rd.name.split("_")[1])
        except (IndexError, ValueError):
            continue
        gh = f"{REPO}/tree/main/outputs/topics/{slug}/iterations/{rd.name}"
        sections.append(
            f"<section id='round-{n}'><h2>Kör {n}</h2>"
            + render_meta(rd) + render_stats(rd)
            + render_research(rd) + render_experts(rd, slug, n)
            + render_rejections(rd) + render_steps(rd)
            + f"<p class='mono'><a href='{gh}'>a kör teljes nyers rekordja "
              "a GitHubon →</a></p></section>")
    page = f"""<!doctype html><html lang="hu"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Műhely-napló — {e(title)}</title>
<style>{CSS}</style><link rel="stylesheet" href="../../assets/atlas.css"></head><body class="atlas">
<header class="site"><div class="wrap">
<span><a href="index.html">← {e(title)}</a></span>
<span><a href="../../index.html">Oktatáspolitikai Atlasz</a></span>
</div></header>
<div class="wrap">
<section><h1>Műhely-napló</h1>
<p>Minden kör minden lépésének kimenete: mikor és milyen beállításokkal
indult a kör, mit keresett és talált minden szakértő (kattintható
forrásokkal), mit adott vissza pontosan, és mit utasított vissza a rendszer
— okkal együtt. Semmi sincs kézzel válogatva: ez a nyers, auditálható
munkanapló.</p></section>
{''.join(sections)}
</div><script src="../../assets/atlas.js"></script></body></html>"""
    dest = SITE_TOPICS / slug / "audit.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")
    print(f"wrote {dest}")


def main():
    for tj in sorted(TOPICS_DIR.glob("*/topic.json")):
        slug = tj.parent.name
        cfg = read_json(tj) or {}
        title_pair = cfg.get("problem_brief", {}).get("title", {})
        title = title_pair.get("hu") if isinstance(title_pair, dict) else title_pair
        build_topic(slug, title or slug)


if __name__ == "__main__":
    main()
