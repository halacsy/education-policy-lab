#!/usr/bin/env python3
"""Render the v2 artifact graph as the Transformation Observatory website."""

from __future__ import annotations

import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402

OUT = ROOT / "site" / "v2"
TOPIC_ROUNDS = {
    "korai-szelekcio": "round_09",
    "rural-school-closures": "round_02",
}
LENS_HU = {
    "demography": "demográfia",
    "education_finance": "oktatásfinanszírozás",
    "equity_and_social_mobility": "méltányosság és mobilitás",
    "finnish_reform": "finn rendszerreform",
    "hungarian_education_system": "magyar oktatási rendszer",
    "implementation_planning": "megvalósítástervezés",
    "international_comparison": "nemzetközi összehasonlítás",
    "legal_and_governance": "jog és kormányzás",
    "polish_reform": "lengyel rendszerreform",
    "political_feasibility": "politikai megvalósíthatóság",
    "portuguese_reform": "portugál rendszerreform",
    "school_network_planning": "iskolahálózat-tervezés",
}
VERDICT_HU = {
    "supports": "támogatja", "supports_with_conditions": "feltételekkel támogatja",
    "neutral": "semleges", "cautions": "óvatosságra int",
    "insufficient_evidence": "nincs elég evidencia",
}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def en(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("en", ""))
    return str(value or "")


def hu(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("hu") or value.get("en", ""))
    return str(value or "")


def bi(english: Any, hungarian: Any | None = None, *, tag: str = "span") -> str:
    hungarian = english if hungarian is None else hungarian
    return (
        f'<{tag} class="lang lang-hu" lang="hu">{esc(hungarian)}</{tag}>'
        f'<{tag} class="lang lang-en" lang="en">{esc(english)}</{tag}>'
    )


def page(title: str, body: str, *, depth: int = 0) -> str:
    prefix = "../" * depth
    return f"""<!doctype html>
<html lang="hu" data-language="hu">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="Education transformation proposals, scientific lenses, dilemmas and research questions.">
  <title>{esc(title)} · Transformation Observatory</title>
  <link rel="stylesheet" href="{prefix}assets/v2.css">
</head>
<body>
  <a class="skip" href="#content">Ugrás a tartalomra / Skip to content</a>
  <header class="masthead">
    <a class="brand" href="{prefix}index.html" aria-label="Transformation Observatory home">
      <span class="brand-mark" aria-hidden="true">↳</span>
      <span><b>TRANSFORMATION</b><em>OBSERVATORY · EPL v2</em></span>
    </a>
    <nav aria-label="Primary navigation">
      <a href="{prefix}index.html">{bi('Portfolio','Tárház')}</a>
      <a href="{prefix}comparison.html">V1 ↔ V2</a>
    </nav>
    <div class="language-switch" role="group" aria-label="Language">
      <button type="button" data-set-language="hu" aria-pressed="true">HU</button>
      <button type="button" data-set-language="en" aria-pressed="false">EN</button>
    </div>
  </header>
  <main id="content">{body}</main>
  <footer><span>Education Policy Lab · artifact-first architecture</span><span>v2.0.0 · 2026-07-20</span></footer>
  <script src="{prefix}assets/v2.js"></script>
</body></html>"""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def legacy(topic: str) -> dict[str, Any]:
    round_path = ROOT / "outputs" / "topics" / topic / "iterations" / TOPIC_ROUNDS[topic]
    return {
        "topic": load_json(ROOT / "topics" / topic / "topic.json"),
        "scenarios": load_json(round_path / "scenarios.json")["scenarios"],
        "brief": load_json(round_path / "brief.json"),
        "clusters": load_json(round_path / "discourse" / "argument_map.json")["clusters"],
    }


def localized_scenario(data: dict[str, Any], sid: str) -> dict[str, Any]:
    return next(item for item in data["scenarios"] if item["id"] == sid)


def render_index(records: list[dict[str, Any]], manifests: list[dict[str, Any]]) -> str:
    packages = {r["topic"]: r for r in records if r["record_type"] == "decision_package"}
    total = sum(sum(m["artifact_counts"].values()) for m in manifests)
    topic_cards = []
    for topic, package in packages.items():
        data = legacy(topic)
        problem = data["topic"]["problem_brief"]
        counts = next(m["artifact_counts"] for m in manifests if m["topic"] == topic)
        topic_cards.append(f"""
        <article class="topic-sheet">
          <div class="sheet-index">{len(topic_cards)+1:02d}</div>
          <p class="eyebrow">{esc(topic)} · {counts['transformation_proposal']} TRANSFORMATIONS</p>
          <h2>{bi(en(problem['title']), hu(problem['title']))}</h2>
          <p class="lead">{bi(en(problem['public_question']), hu(problem['public_question']))}</p>
          <div class="mini-metrics"><span>{counts['finding']}<small>findings</small></span><span>{counts['lens_assessment']}<small>lens tests</small></span><span>{counts['dilemma']}<small>dilemmas</small></span></div>
          <a class="arrow-link" href="topics/{esc(topic)}.html">{bi('Open transformation map','Transzformációs térkép megnyitása')} <span>→</span></a>
        </article>""")
    return f"""
    <section class="hero blueprint-grid">
      <div class="hero-copy">
        <p class="eyebrow">EDUCATION POLICY LAB · ARCHITECTURE V2</p>
        <h1>{bi('From debate to a library of change.','A vitától a változtatások tárházáig.')}</h1>
        <p class="hero-deck">{bi(
            'Evidence does not vote. It supports findings, tests transformations through scientific lenses, and marks the choices that remain human.',
            'Az evidencia nem szavaz. Findingokat támaszt alá, tudományos nézőpontokból teszteli a változtatásokat, és megjelöli az emberi döntésként megmaradó kérdéseket.'
        )}</p>
        <a class="primary-action" href="#portfolio">{bi('Explore the portfolio','A tárház felfedezése')} ↓</a>
      </div>
      <div class="hero-instrument" aria-label="v2 corpus summary">
        <span class="registration">V2 / LIVE VERTICAL SLICE</span>
        <strong>{total}</strong><small>{bi('typed, immutable artifacts','típusos, megváltoztathatatlan artifact')}</small>
        <div class="instrument-line"></div>
        <p>{bi('2 decision packages · 12/12 cache hits on repeat build','2 decision package · ismételt buildnél 12/12 cache hit')}</p>
      </div>
    </section>
    <section class="change-system" aria-labelledby="system-title">
      <div class="section-number">01</div><div>
      <p class="eyebrow">THE CHANGE SPINE</p>
      <h2 id="system-title">{bi('Every conclusion has an address.','Minden következtetésnek van címe.')}</h2>
      <div class="dag-flow">
        <div><b>01</b><span>Finding</span><small>{bi('What the record supports','Amit az anyag alátámaszt')}</small></div>
        <div><b>02</b><span>Family</span><small>{bi('Where the system can move','Merre mozdulhat a rendszer')}</small></div>
        <div><b>03</b><span>Proposal</span><small>{bi('Mechanism and sequence','Mechanizmus és lépéssor')}</small></div>
        <div><b>04</b><span>Lens</span><small>{bi('Disciplinary scrutiny','Szakmai vizsgálat')}</small></div>
        <div><b>05</b><span>Dilemma</span><small>{bi('Evidence boundary','Az evidencia határa')}</small></div>
        <div><b>06</b><span>Package</span><small>{bi('A decision-ready map','Döntésre kész térkép')}</small></div>
      </div></div>
    </section>
    <section id="portfolio" class="portfolio">
      <div class="section-heading"><div><p class="eyebrow">02 / PORTFOLIO</p><h2>{bi('Transformation fields','Transzformációs mezők')}</h2></div><a href="comparison.html">{bi('See measured v1 comparison','Mért v1-összevetés')} →</a></div>
      <div class="topic-grid">{''.join(topic_cards)}</div>
    </section>
    <aside class="honesty-band"><b>{bi('Migration boundary','Migrációs határ')}</b><p>{bi(
        'This visible slice recompiles committed v1 research into the v2 graph. It proves the architecture and information model; it does not claim fresh research.',
        'Ez a látható szelet a már commitolt v1-kutatást fordítja át a v2-gráfba. Az architektúrát és az információs modellt bizonyítja; nem állítja, hogy új kutatási futás történt.'
    )}</p></aside>"""


def render_topic(topic: str, records: list[dict[str, Any]], manifest: dict[str, Any]) -> str:
    data = legacy(topic)
    topic_records = [r for r in records if r["topic"] == topic]
    proposals = sorted((r for r in topic_records if r["record_type"] == "transformation_proposal"), key=lambda r: r["content"]["legacy_scenario_id"])
    assessments = [r for r in topic_records if r["record_type"] == "lens_assessment"]
    dilemmas = [r for r in topic_records if r["record_type"] == "dilemma"]
    questions = [r for r in topic_records if r["record_type"] == "research_question"]
    problem = data["topic"]["problem_brief"]
    spine = "".join(
        f'<a href="#{esc(p["content"]["legacy_scenario_id"].lower())}"><b>{esc(p["content"]["legacy_scenario_id"])}</b>{bi(p["content"]["title"], hu(localized_scenario(data,p["content"]["legacy_scenario_id"])["title"]))}</a>'
        for p in proposals
    )
    sheets = []
    for proposal in proposals:
        content = proposal["content"]
        sid = content["legacy_scenario_id"]
        source = localized_scenario(data, sid)
        related_assessments = [a for a in assessments if a["content"]["proposal_ref"] == proposal["id"]]
        related_dilemmas = [d for d in dilemmas if proposal["id"] in d["content"]["proposal_refs"]]
        related_questions = [q for q in questions if proposal["id"] in q["content"]["proposal_refs"]]
        mechanisms = "".join(
            f"<li>{bi(text, hu(source['mechanism'][i].get('text', source['mechanism'][i])) if i < len(source.get('mechanism',[])) else text)}</li>"
            for i, text in enumerate(content["mechanisms"])
        )
        steps = "".join(
            f'<li><time>{bi(step["timeline"], hu(source["implementation_steps"][i]["timeline"]) if i < len(source.get("implementation_steps",[])) else step["timeline"])}</time><div><b>{bi(step["actor"], hu(source["implementation_steps"][i]["actor"]) if i < len(source.get("implementation_steps",[])) else step["actor"])}</b><p>{bi(step["action"], hu(source["implementation_steps"][i]["action"]) if i < len(source.get("implementation_steps",[])) else step["action"])}</p></div></li>'
            for i, step in enumerate(content["implementation_steps"])
        )
        lens_rows = "".join(
            f'<tr data-verdict="{esc(a["content"]["verdict"])}"><th>{bi(a["content"]["lens_ref"].split(f"L-{topic}-",1)[-1].replace("_"," ").title(), LENS_HU.get(a["content"]["lens_ref"].split(f"L-{topic}-",1)[-1],a["content"]["lens_ref"]))}</th><td><span class="verdict verdict-{esc(a["content"]["verdict"])}">{bi(a["content"]["verdict"].replace("_"," "), VERDICT_HU[a["content"]["verdict"]])}</span></td><td>{len(a["content"]["finding_refs"])} finding</td><td>{esc(a["content"]["confidence"])}</td></tr>'
            for a in related_assessments
        )
        dilemma_cards = "".join(
            f'<article class="dilemma"><span>{esc(d["content"]["legacy_cluster_id"])}</span><h4>{bi(d["content"]["dilemma_type"].replace("_"," "), "értékkonfliktus" if d["content"]["dilemma_type"]=="value_conflict" else "feloldhatatlan trade-off")}</h4><p>{bi(d["content"]["tension"], hu(next((c["claim"] for c in data["clusters"] if c["id"]==d["content"]["legacy_cluster_id"]), d["content"]["tension"])))}</p><small>{bi('Evidence can clarify consequences; it cannot rank these values.','Az evidencia tisztázhatja a következményeket, de nem rangsorolhatja ezeket az értékeket.')}</small></article>'
            for d in related_dilemmas
        ) or f'<p class="empty">{bi("No value dilemma was extracted for this proposal.","Ehhez a javaslathoz nem került külön értékdilemma a v1-anyagból.")}</p>'
        research_items = "".join(f"<li>{bi(q['content']['question'], hu(data['brief']['what_research_could_resolve'][int(q['id'].rsplit('-',1)[-1])-1]))}</li>" for q in related_questions)
        sheets.append(f"""
        <article id="{sid.lower()}" class="proposal-sheet">
          <header><div class="proposal-code">{sid}<small>{esc(content['change_level'])}</small></div><div><p class="eyebrow">TRANSFORMATION PROPOSAL</p><h2>{bi(content['title'],hu(source['title']))}</h2><p class="proposal-goal">{bi(content['goal'],hu(source['goal']))}</p></div><span class="evidence evidence-{esc(content['evidence_status'])}">{esc(content['evidence_status'])}</span></header>
          <div class="proposal-grid"><section><h3>01 / {bi('Mechanism','Mechanizmus')}</h3><ol class="mechanisms">{mechanisms}</ol></section><section><h3>02 / {bi('Implementation path','Megvalósítási út')}</h3><ol class="timeline">{steps}</ol></section></div>
          <section class="lens-section"><div class="subhead"><div><h3>03 / {bi('Scientific lens matrix','Tudományos nézőpontmátrix')}</h3><p>{bi('The proposal is the object. Disciplines are reusable evaluative lenses—not simulated people.','A vizsgálat tárgya a javaslat. A diszciplínák újrahasználható értékelési nézőpontok — nem szimulált emberek.')}</p></div><label>{bi('Filter','Szűrés')} <select data-lens-filter><option value="all">Minden értékelés / All verdicts</option><option value="supports_with_conditions">Feltételes támogatás / Conditional support</option><option value="insufficient_evidence">Nincs elég evidencia / Insufficient evidence</option><option value="cautions">Óvatosság / Cautions</option></select></label></div><div class="table-wrap"><table><thead><tr><th>Lens</th><th>Verdict</th><th>Evidence</th><th>Confidence</th></tr></thead><tbody>{lens_rows}</tbody></table></div></section>
          <div class="proposal-grid decisions"><section><h3>04 / {bi('Human dilemmas','Emberi dilemmák')}</h3>{dilemma_cards}</section><section><h3>05 / {bi('Research that could change the choice','Kutatás, amely módosíthatja a döntést')}</h3><ol class="research-list">{research_items}</ol></section></div>
          <p class="audit-line">{esc(proposal['id'])} · {len(content['finding_refs'])} finding refs · {len(content['assumption_refs'])} assumptions · {len(content['uncertainty_refs'])} uncertainties</p>
        </article>""")
    return f"""
    <section class="topic-hero blueprint-grid"><div><p class="eyebrow">DECISION PACKAGE · {esc(topic)}</p><h1>{bi(en(problem['title']),hu(problem['title']))}</h1><p class="hero-deck">{bi(en(problem['public_question']),hu(problem['public_question']))}</p></div><div class="topic-stats"><span><b>{manifest['artifact_counts']['finding']}</b> findings</span><span><b>{manifest['artifact_counts']['lens_assessment']}</b> lens tests</span><span><b>{manifest['artifact_counts']['dilemma']}</b> dilemmas</span></div></section>
    <aside class="migration-note"><b>V1 → V2</b>{bi('Deterministic corpus migration—not a fresh research run. Every proposal retains its legacy scenario id and audit path.','Determinisztikus korpuszmigráció — nem friss kutatási futás. Minden javaslat megőrzi a korábbi scenario-azonosítót és auditútvonalat.')}</aside>
    <nav class="change-spine" aria-label="Transformation proposals">{spine}</nav>
    <div class="proposal-stack">{''.join(sheets)}</div>"""


def render_comparison(records: list[dict[str, Any]], manifests: list[dict[str, Any]]) -> str:
    counts = Counter(r["record_type"] for r in records)
    total = sum(counts.values())
    rows = [
        ("Primary unit", "Expert/voice output", "Typed semantic artifact", "Szakértői/hang output", "Típusos szemantikai artifact"),
        ("Canonical language", "Bilingual JSON", "English JSON; localization downstream", "Kétnyelvű JSON", "Angol JSON; lokalizáció downstream"),
        ("Change object", "10 scenarios", f"{counts['transformation_proposal']} proposals in {counts['transformation_family']} families", "10 scenario", f"{counts['transformation_proposal']} javaslat {counts['transformation_family']} családban"),
        ("Professional scrutiny", "Implicit in expert authorship", f"{counts['lens_assessment']} proposal × lens assessments", "Implicit a szakértő személyében", f"{counts['lens_assessment']} javaslat × nézőpont értékelés"),
        ("Value conflict", "Mixed into argument clusters", f"{counts['dilemma']} explicit dilemmas", "Argument clusterekbe keverve", f"{counts['dilemma']} explicit dilemma"),
        ("Invalidation", "Round/global state hash", "Node dependency hash", "Kör-/globális state hash", "Node-függőségi hash"),
        ("Repeat build", "No equivalent artifact cache", "12/12 node cache hits", "Nincs azonos artifact-cache", "12/12 node cache hit"),
        ("Audit root", "Brief + logs", "2 decision packages + manifests + events", "Brief + naplók", "2 decision package + manifestek + események"),
    ]
    table_rows = "".join(f"<tr><th>{bi(a,a)}</th><td>{bi(b,d)}</td><td>{bi(c,e)}</td></tr>" for a,b,c,d,e in rows)
    artifact_bars = "".join(
        f'<div><span>{esc(name.replace("_"," "))}</span><i style="--amount:{max(3,round(value/max(counts.values())*100))}%"></i><b>{value}</b></div>'
        for name,value in counts.most_common()
    )
    return f"""
    <section class="comparison-hero blueprint-grid"><div><p class="eyebrow">MEASURED ARCHITECTURE COMPARISON</p><h1>V1 <span>↔</span> V2</h1><p class="hero-deck">{bi('Same committed evidence corpus. Different unit of thought.','Ugyanaz a commitolt evidenciakorpusz. Más gondolkodási alapegység.')}</p></div><div class="hero-instrument"><span class="registration">CURRENT VERTICAL SLICE</span><strong>{total}</strong><small>{bi('v2 artifacts across two topics','v2 artifact két témában')}</small></div></section>
    <section class="comparison-section"><div class="section-heading"><div><p class="eyebrow">01 / INFORMATION MODEL</p><h2>{bi('What actually changed','Mi változott ténylegesen')}</h2></div></div><div class="table-wrap"><table class="comparison-table"><thead><tr><th>Dimension</th><th>V1</th><th>V2</th></tr></thead><tbody>{table_rows}</tbody></table></div></section>
    <section class="comparison-section split"><div><p class="eyebrow">02 / V2 CORPUS</p><h2>{bi('The database is visible','Az adatbázis látható')}</h2><div class="artifact-bars">{artifact_bars}</div></div><aside class="verdict-panel"><span>ARCHITECTURE VERDICT</span><h3>{bi('Rewrite the semantic core; preserve the evidence trail.','A szemantikai magot írjuk újra; az evidenciaútvonalat őrizzük meg.')}</h3><p>{bi('The vertical slice validates the new graph, schemas, node cache, and public reading model. It does not yet validate new live-agent prompts or evidence quality beyond v1.','A függőleges szelet igazolja az új gráfot, sémákat, node-cache-t és nyilvános olvasási modellt. Az új élő agent-promptokat vagy a v1-en túli evidenciaminőséget még nem igazolja.')}</p></aside></section>
    <section class="comparison-section"><p class="eyebrow">03 / HONEST LIMITS</p><h2>{bi('What this comparison cannot claim','Amit ez az összevetés nem állíthat')}</h2><div class="limit-grid"><article><b>01</b><p>{bi('No paid model call was made, so v2 generation quality is not being compared yet.','Nem történt fizetős modellhívás, ezért a v2 generálási minőségét még nem hasonlítjuk össze.')}</p></article><article><b>02</b><p>{bi('Lens assessments are deterministic projections of v1 expert records, not fresh disciplinary reviews.','A lens assessmentek a v1 szakértői anyagok determinisztikus vetületei, nem friss diszciplináris értékelések.')}</p></article><article><b>03</b><p>{bi('Source strings were preserved but not re-verified during migration.','A forrásmegjelöléseket megőriztük, de a migráció során nem ellenőriztük újra.')}</p></article></div></section>"""


def main() -> int:
    schemas = SchemaRegistry(ROOT / "schemas" / "v2")
    repository = ArtifactRepository(ROOT / "v2", schemas)
    records = repository.list()
    catalog = load_json(ROOT / "v2" / "catalog" / "topics.json")
    manifests = catalog["topics"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "topics").mkdir(exist_ok=True)
    (OUT / "index.html").write_text(page("Transformation portfolio", render_index(records, manifests)), encoding="utf-8")
    for manifest in manifests:
        topic = manifest["topic"]
        body = render_topic(topic, records, manifest)
        (OUT / "topics" / f"{topic}.html").write_text(page(topic, body, depth=1), encoding="utf-8")
    (OUT / "comparison.html").write_text(page("V1 ↔ V2", render_comparison(records, manifests)), encoding="utf-8")
    print(f"Rendered {len(manifests) + 2} pages from {len(records)} artifacts into {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
