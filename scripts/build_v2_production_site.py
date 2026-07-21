#!/usr/bin/env python3
"""Render the public Education Policy Atlas from accepted v2 production artifacts."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.i18n import BILINGUAL_VERSION, is_localized_text  # noqa: E402
from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402

ASSET_VERSION = "d58"
OUT = ROOT / "site"
QUESTION_OUT = OUT / "questions"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


CATALOGS = {
    language: load(ROOT / "config" / "v2" / "locales" / f"{language}.json")
    for language in ("en", "hu")
}
PUBLICATION = load(ROOT / "config" / "v2" / "publication.json")
PUBLICATION_LABEL = PUBLICATION["label"]
PUBLIC_TOPICS = {
    item["topic"]: item["run_tag"]
    for item in PUBLICATION["topics"]
}


def msg(language: str, key: str) -> str:
    value: Any = CATALOGS[language]["messages"]
    for part in key.split("."):
        value = value[part]
    return str(value)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def bi(english: Any, hungarian: Any, tag: str = "span") -> str:
    localized = str(hungarian)
    for replacement in CATALOGS["hu"]["content_replacements"]:
        localized = re.sub(replacement["pattern"], replacement["replacement"], localized)
    return (
        f'<{tag} class="lang lang-hu" lang="hu">{esc(localized)}</{tag}>'
        f'<{tag} class="lang lang-en" lang="en">{esc(english)}</{tag}>'
    )


def semantic(value: Any, tag: str = "span") -> str:
    """Render one canonical D-34 semantic leaf in both languages."""

    if not is_localized_text(value):
        raise ValueError(f"Public semantic text is not an exact {{en, hu}} pair: {value!r}")
    return bi(value["en"], value["hu"], tag)


def ui(key: str, tag: str = "span") -> str:
    return bi(msg("en", key), msg("hu", key), tag)


def short_intro(value: str, sentence_count: int = 2) -> str:
    """Keep catalogue cards introductory; the dossier preserves the full brief."""
    sentences = re.split(r"(?<=[.!?])\s+", value.strip())
    return " ".join(sentences[:sentence_count])


def page(title: dict[str, str], body: str, *, depth: int = 0, description: dict[str, str] | None = None) -> str:
    prefix = "../" * depth
    asset_prefix = f"{prefix}v2/assets/"
    home = f"{prefix}index.html"
    description = description or {
        "en": msg("en", "public_site.home_deck"),
        "hu": msg("hu", "public_site.home_deck"),
    }
    return f'''<!doctype html>
<html lang="hu" data-language="hu" data-title-en="{esc(title['en'])} · Education Policy Atlas" data-title-hu="{esc(title['hu'])} · Oktatáspolitikai Atlasz">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{esc(description['hu'])}" data-description-en="{esc(description['en'])}" data-description-hu="{esc(description['hu'])}">
  <title>{esc(title['hu'])} · Oktatáspolitikai Atlasz</title>
  <link rel="stylesheet" href="{asset_prefix}v2.css?v={ASSET_VERSION}">
</head>
<body>
  <a class="skip" href="#content">{ui('nav.skip')}</a>
  <header class="masthead">
    <a class="brand" href="{home}" aria-label="Oktatáspolitikai Atlasz — főoldal" data-label-en="Education Policy Atlas home" data-label-hu="Oktatáspolitikai Atlasz — főoldal">
      <span class="brand-mark" aria-hidden="true">↳</span><span><b>{bi('EDUCATION POLICY','OKTATÁSPOLITIKAI')}</b><em>{bi('ATLAS · EPL','ATLASZ · EPL')}</em></span>
    </a>
    <nav aria-label="Elsődleges navigáció" data-label-en="Primary navigation" data-label-hu="Elsődleges navigáció">
      <a href="{home}#questions">{ui('nav.portfolio')}</a><a href="{home}#about">{ui('nav.about')}</a><a href="{prefix}audit.html">{ui('nav.method')}</a>
    </nav>
    <div class="language-switch" role="group" aria-label="Nyelv" data-label-en="Language" data-label-hu="Nyelv"><button type="button" data-set-language="hu" aria-pressed="true">HU</button><button type="button" data-set-language="en" aria-pressed="false">EN</button></div>
  </header>
  <main id="content">{body}</main>
  <footer><span>{ui('footer.architecture')}</span><span>Oktatáspolitikai Atlasz · {PUBLICATION_LABEL}</span></footer>
  <script src="{asset_prefix}v2.js?v={ASSET_VERSION}"></script>
</body></html>'''


def dataset(topic: str, schemas: SchemaRegistry) -> dict[str, Any]:
    root = ROOT / "v2" / "production" / PUBLIC_TOPICS[topic] / topic
    repository = ArtifactRepository(root, schemas)
    manifest = load(root / "production_manifest.json")
    summary = manifest["summary"]
    package = repository.get_current(summary["package_ref"])
    if package["schema_version"] != BILINGUAL_VERSION:
        raise ValueError(f"Published package is not canonical bilingual v2.1: {topic}")
    topic_data = load(ROOT / "topics" / topic / "topic.json")
    briefs = repository.list(record_type="problem_brief")
    if len(briefs) == 1:
        brief = briefs[0]
        if brief["schema_version"] != BILINGUAL_VERSION:
            raise ValueError(f"Published problem brief is not canonical bilingual v2.1: {topic}")
        content = brief["content"]
    elif not briefs and "problem_brief" in topic_data:
        # The two pre-RunPlan production stores admitted their already-bilingual
        # topic brief outside the artifact database. D-58 does not invent a
        # retroactive root record; it keeps using that exact admitted source.
        content = topic_data["problem_brief"]
    else:
        raise ValueError(f"Expected one admitted problem brief for {topic}, found {len(briefs)}")
    topic_data["problem_brief"] = {
        field: content[field]
        for field in ("title", "public_question", "problem_statement", "learning_goals", "scope")
    }
    return {
        "topic": topic_data,
        "repo": repository,
        "summary": summary,
        "package": package,
        "evaluation": repository.get_current(summary["evaluation_ref"]),
        "readiness": repository.get_current(summary["readiness_ref"]),
    }


def list_bi(record: dict[str, Any], field: str) -> str:
    return "".join(
        f"<li>{semantic(value)}</li>"
        for value in record["content"].get(field, [])
    )


def change_spine() -> str:
    steps = (
        ("01", "question", "#overview"),
        ("02", "options", "#options"),
        ("03", "tests", "#perspectives"),
        ("04", "dilemmas", "#dilemmas"),
        ("05", "unknowns", "#research"),
    )
    return '<nav class="change-spine" aria-label="A dosszié olvasási útvonala">' + "".join(
        f'<a href="{anchor}"><b>{number}</b>{ui(f"public_site.step_{key}")}</a>'
        for number, key, anchor in steps
    ) + "</nav>"


def render_perspective_matrix(data: dict[str, Any], proposals: list[dict[str, Any]]) -> str:
    repository = data["repo"]
    assessments = repository.list(record_type="lens_assessment")
    by_pair = {
        (record["content"]["lens_ref"], record["content"]["proposal_ref"]): record
        for record in assessments
    }
    lens_refs = sorted({record["content"]["lens_ref"] for record in assessments})
    header = "".join(
        f'<th scope="col"><span>{ui("public_site.proposal_short")}</span> {esc(proposal["id"].split("-")[-1].upper())}</th>'
        for proposal in proposals
    )
    rows = []
    for lens_ref in lens_refs:
        lens_key = lens_ref.removeprefix("L-live-")
        cells = []
        for proposal in proposals:
            assessment = by_pair[(lens_ref, proposal["id"])]
            verdict = assessment["content"]["verdict"]
            confidence = assessment["content"]["confidence"]
            title_en = f"{msg('en', 'enum.verdict.' + verdict)}; {msg('en', 'public_site.confidence_short')}: {msg('en', 'enum.confidence.' + confidence)}"
            title_hu = f"{msg('hu', 'enum.verdict.' + verdict)}; {msg('hu', 'public_site.confidence_short')}: {msg('hu', 'enum.confidence.' + confidence)}"
            cells.append(
                f'<td><span class="verdict verdict-{esc(verdict)}" title="{esc(title_hu)}" data-title-en="{esc(title_en)}" data-title-hu="{esc(title_hu)}">{ui("enum.verdict." + verdict)}</span></td>'
            )
        rows.append(f'<tr><th scope="row">{ui("lens." + lens_key)}</th>{"".join(cells)}</tr>')
    return f'''<section class="lens-section" id="perspectives"><div class="subhead"><div><p class="eyebrow">03 / {ui('production.perspectives')}</p><h2>{ui('public_site.perspective_title')}</h2><p>{ui('public_site.perspective_note')}</p></div></div><div class="table-wrap"><table class="perspective-matrix"><thead><tr><th scope="col">{ui('production.perspectives')}</th>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>'''


def render_topic(data: dict[str, Any]) -> str:
    topic = data["topic"]
    problem = topic["problem_brief"]
    package = data["package"]
    repository = data["repo"]
    summary = data["summary"]
    proposals = [repository.get_current(ref) for ref in package["content"]["proposal_refs"]]
    dilemmas = [repository.get_current(ref) for ref in package["content"]["dilemma_refs"]]
    questions = [repository.get_current(ref) for ref in package["content"]["research_question_refs"]]
    coverage = repository.get_current(package["content"]["coverage_ledger_refs"][0])

    cards = []
    for proposal in proposals:
        content = proposal["content"]
        proposal_id = proposal["id"]
        steps = "".join(
            f"<li><time>{semantic(step['timeline'])}</time><b>{semantic(step['actor'])}</b><p>{semantic(step['action'])}</p></li>"
            for step in content["implementation_steps"]
        )
        cards.append(f'''<article class="proposal-sheet"><header><div class="proposal-code">{esc(proposal_id.split('-')[-1].upper())}<small>{ui('public_site.proposal_short')}</small></div><div><h2>{semantic(content['title'])}</h2><p class="proposal-goal">{semantic(content['goal'])}</p></div><span class="evidence evidence-{esc(content['evidence_status'])}">{bi(content['evidence_status'], msg('hu','enum.evidence.'+content['evidence_status']))}</span></header><details class="proposal-detail"><summary>{ui('public_site.proposal_details')}</summary><div class="proposal-grid"><section><h3>{ui('production.mechanisms')}</h3><ol class="mechanisms">{list_bi(proposal, 'mechanisms')}</ol></section><section><h3>{ui('production.implementation')}</h3><ol class="timeline">{steps}</ol></section></div><div class="proposal-grid"><section><h3>{ui('production.benefits')}</h3><ul>{list_bi(proposal,'expected_benefits')}</ul><h3>{ui('production.equity')}</h3><p>{semantic(content['equity_impact'])}</p></section><section><h3>{ui('production.costs')}</h3><ul>{list_bi(proposal,'costs')}</ul><h3>{ui('production.risks')}</h3><ul>{list_bi(proposal,'risks')}</ul></section></div></details></article>''')

    coverage_items = "".join(
        f"<li><b>{entry['direction_id']}</b> {semantic(entry['direction_title'])} → {esc(', '.join(entry['proposal_refs']))}</li>"
        for entry in coverage["content"]["entries"]
    )
    dilemma_cards = "".join(
        f'''<article class="dilemma"><span>{bi(record['content']['dilemma_type'],msg('hu','enum.dilemma_type.'+record['content']['dilemma_type']))}</span><h4>{semantic(record['content']['title'])}</h4><p>{semantic(record['content']['tension'])}</p><small>{semantic(record['content']['evidence_boundary'])}</small></article>'''
        for record in dilemmas
    )
    research_items = "".join(
        f"<li><b>{semantic(record['content']['question'])}</b><p>{semantic(record['content']['why_it_matters'])}</p></li>"
        for record in questions
    )
    learning_goals = "".join(
        f"<li>{bi(goal['en'], goal['hu'])}</li>" for goal in problem["learning_goals"]
    )

    def source_links(entry: dict[str, Any]) -> str:
        return " · ".join(
            f'<a href="{esc(source["url"])}">{semantic(source["title"], "cite")}</a>'
            if source["url"].startswith("http")
            else semantic(source["title"], "cite")
            for source in entry["sources"]
        )

    appendix = "".join(
        f"<li><b>{esc(entry['finding_ref'])}</b> {semantic(entry['claim'])}<div>{source_links(entry)}</div></li>"
        for entry in package["content"]["evidence_appendix"]
    )
    concerns = list_bi(data["evaluation"], "concerns")
    matrix = render_perspective_matrix(data, proposals)

    return f'''<section class="topic-hero blueprint-grid"><div><p class="eyebrow">{ui('public_site.topic_eyebrow')}</p><h1>{semantic(problem['public_question'])}</h1><p class="hero-deck">{semantic(problem['problem_statement'])}</p></div><div class="topic-stats"><span><b>{len(proposals)}</b>{ui('public_site.proposal_count')}</span><span><b>{summary['counts']['finding']}</b>{ui('production.fresh_findings')}</span><span><b>{len(dilemmas)}</b>{ui('public_site.dilemma_count')}</span></div></section><aside class="migration-note"><b>{ui('production.readiness')}</b>{ui('production.ready_with_conditions')} · {ui('production.external_gate')}</aside>{change_spine()}<section class="comparison-section split" id="overview"><div><p class="eyebrow">01 / {ui('public_site.problem_title')}</p><h2>{ui('public_site.problem_title')}</h2><p class="result-lead">{semantic(problem['problem_statement'])}</p></div><div><h3>{ui('public_site.learning_title')}</h3><ul>{learning_goals}</ul></div><details class="full-summary"><summary>{ui('public_site.full_summary')}</summary><p>{semantic(package['content']['summary'])}</p></details></section><section class="proposal-stack" id="options"><div class="section-heading"><div><p class="eyebrow">02 / {ui('production.proposals')}</p><h2>{ui('production.proposals')}</h2></div></div>{''.join(cards)}</section>{matrix}<section class="comparison-section"><h2>{ui('production.coverage')}</h2><ul>{coverage_items}</ul></section><section class="comparison-section decisions" id="dilemmas"><p class="eyebrow">04 / {ui('production.dilemmas')}</p><h2>{ui('production.dilemmas')}</h2>{dilemma_cards}</section><section class="comparison-section" id="research"><p class="eyebrow">05 / {ui('production.research')}</p><h2>{ui('production.research')}</h2><ol class="research-list">{research_items}</ol></section><section class="comparison-section"><h2>{ui('production.conditions')}</h2><ul>{concerns}</ul></section><section class="comparison-section" id="evidence"><details><summary><h2>{ui('production.evidence')} · {len(package['content']['evidence_appendix'])}</h2></summary><p>{ui('public_site.sources_note')}</p><ol class="research-list">{appendix}</ol></details></section>'''


def render_home(data: dict[str, dict[str, Any]]) -> str:
    cards = []
    for index, (topic, item) in enumerate(data.items(), 1):
        problem = item["topic"]["problem_brief"]
        cards.append(f'''<article class="topic-sheet"><span class="sheet-index">{index:02d}</span><p class="eyebrow">{bi('QUESTION','KÉRDÉS')} {index:02d}</p><h2>{bi(problem['public_question']['en'],problem['public_question']['hu'])}</h2><p class="lead">{bi(short_intro(problem['problem_statement']['en']),short_intro(problem['problem_statement']['hu']))}</p><div class="mini-metrics"><span>{item['summary']['counts']['transformation_proposal']}<small>{ui('public_site.proposal_count')}</small></span><span>{item['summary']['counts']['dilemma']}<small>{ui('public_site.dilemma_count')}</small></span></div><a class="arrow-link" href="questions/{topic}.html">{ui('production.open')} →</a></article>''')

    totals = {
        "questions": len(data),
        "proposals": sum(item["summary"]["counts"]["transformation_proposal"] for item in data.values()),
        "findings": sum(item["summary"]["counts"]["finding"] for item in data.values()),
        "assessments": sum(item["summary"]["counts"]["lens_assessment"] for item in data.values()),
        "dilemmas": sum(item["summary"]["counts"]["dilemma"] for item in data.values()),
        "research": sum(item["summary"]["counts"]["research_question"] for item in data.values()),
    }
    inventory = "".join(
        f'<div><b>{totals[key]}</b>{ui("public_site.inventory_" + key)}</div>'
        for key in ("questions", "proposals", "findings", "assessments", "dilemmas", "research")
    )
    guide = "".join(
        f'<div><b>{index:02d}</b><span>{ui("public_site.step_"+key)}</span><small>{ui("public_site.step_"+key+"_note")}</small></div>'
        for index, key in enumerate(("question", "options", "tests", "dilemmas", "unknowns"), 1)
    )
    return f'''<section class="hero public-hero blueprint-grid"><div class="hero-copy"><p class="eyebrow">{ui('public_site.home_eyebrow')}</p><h1>{ui('public_site.home_title')}</h1><p class="hero-deck">{ui('public_site.home_deck')}</p><a class="primary-action" href="#questions">{ui('public_site.start')} ↓</a></div><div class="hero-route" aria-hidden="true"><span>?</span><i></i><b>6</b><i></i><strong>≠</strong></div></section><section class="portfolio" id="questions"><div class="section-heading"><div><p class="eyebrow">{ui('public_site.questions_eyebrow')}</p><h2>{ui('public_site.questions_title')}</h2></div><p>{ui('public_site.questions_note')}</p></div><div class="topic-grid">{''.join(cards)}</div></section><section class="change-system public-guide"><div class="section-number">→</div><div><p class="eyebrow">{ui('public_site.guide_eyebrow')}</p><h2>{ui('public_site.guide_title')}</h2><div class="dag-flow">{guide}</div></div></section><section class="public-about blueprint-grid" id="about"><div><p class="eyebrow">{ui('public_site.about_eyebrow')}</p><h2>{ui('public_site.about_title')}</h2></div><div><p class="result-lead">{ui('public_site.about_body')}</p><p class="boundary-copy">{ui('public_site.about_boundary')}</p></div></section><section class="inventory-section"><div class="section-heading"><div><p class="eyebrow">{ui('public_site.inventory_eyebrow')}</p><h2>{ui('public_site.inventory_title')}</h2></div></div><div class="public-inventory">{inventory}</div></section><section class="trust-band"><div><p class="eyebrow">{ui('nav.method')}</p><h2>{ui('public_site.trust_title')}</h2><p>{ui('public_site.trust_body')}</p></div><a class="primary-action" href="audit.html">{ui('public_site.open_method')} →</a></section>'''


def main() -> int:
    schemas = SchemaRegistry(ROOT / "schemas" / "v2")
    OUT.mkdir(parents=True, exist_ok=True)
    QUESTION_OUT.mkdir(parents=True, exist_ok=True)
    data = {topic: dataset(topic, schemas) for topic in PUBLIC_TOPICS}
    home_title = {"en": msg("en", "public_site.home_title"), "hu": msg("hu", "public_site.home_title")}
    (OUT / "index.html").write_text(page(home_title, render_home(data)), encoding="utf-8")
    for topic, item in data.items():
        problem = item["topic"]["problem_brief"]
        (QUESTION_OUT / f"{topic}.html").write_text(
            page(problem["public_question"], render_topic(item), depth=1, description=problem["problem_statement"]),
            encoding="utf-8",
        )
    print(f"Built the default Atlas homepage and {len(PUBLIC_TOPICS)} question dossiers in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
