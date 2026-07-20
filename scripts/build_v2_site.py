#!/usr/bin/env python3
"""Render the v2 artifact graph as the Transformation Observatory website."""

from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402

OUT = ROOT / "site" / "v2"
LOCALE_ROOT = ROOT / "config" / "v2" / "locales"
TOPIC_ROUNDS = {
    "korai-szelekcio": "round_09",
    "rural-school-closures": "round_02",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


CATALOGS = {
    locale: load_json(LOCALE_ROOT / f"{locale}.json")
    for locale in ("en", "hu")
}


def message(locale: str, key: str, **values: Any) -> str:
    current: Any = CATALOGS[locale]["messages"]
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Missing {locale} localization message: {key}")
        current = current[part]
    if not isinstance(current, str):
        raise TypeError(f"Localization message is not a string: {locale}:{key}")
    return current.format(**values)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def en(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("en", ""))
    return str(value or "")


def hu(value: Any) -> str:
    if isinstance(value, dict):
        localized = str(value.get("hu") or value.get("en", ""))
    else:
        localized = str(value or "")
    for replacement in CATALOGS["hu"]["content_replacements"]:
        localized = re.sub(replacement["pattern"], replacement["replacement"], localized)
    return localized


def bi(english: Any, hungarian: Any | None = None, *, tag: str = "span") -> str:
    hungarian = english if hungarian is None else hungarian
    return (
        f'<{tag} class="lang lang-hu" lang="hu">{esc(hungarian)}</{tag}>'
        f'<{tag} class="lang lang-en" lang="en">{esc(english)}</{tag}>'
    )


def ui(key: str, *, tag: str = "span", **values: Any) -> str:
    return bi(message("en", key, **values), message("hu", key, **values), tag=tag)


def label(record_type: str, count: int) -> str:
    suffix = "one" if count == 1 else "many"
    return ui(f"artifact.{record_type}_{suffix}")


def enum_label(group: str, value: str) -> str:
    return ui(f"enum.{group}.{value}")


def lens_label(value: str) -> str:
    return ui(f"lens.{value}")


def localized_option(value: str, key: str) -> str:
    english = message("en", key)
    hungarian = message("hu", key)
    return (
        f'<option value="{esc(value)}" data-label-en="{esc(english)}" '
        f'data-label-hu="{esc(hungarian)}">{esc(hungarian)}</option>'
    )


def page(title_en: str, title_hu: str, body: str, *, depth: int = 0) -> str:
    prefix = "../" * depth
    description_en = message("en", "meta.description")
    description_hu = message("hu", "meta.description")
    return f"""<!doctype html>
<html lang="hu" data-language="hu" data-title-en="{esc(title_en)} · Transformation Observatory" data-title-hu="{esc(title_hu)} · Transformation Observatory">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{esc(description_hu)}" data-description-en="{esc(description_en)}" data-description-hu="{esc(description_hu)}">
  <title>{esc(title_hu)} · Transformation Observatory</title>
  <link rel="stylesheet" href="{prefix}assets/v2.css">
</head>
<body>
  <a class="skip" href="#content">{ui('nav.skip')}</a>
  <header class="masthead">
    <a class="brand" href="{prefix}index.html" aria-label="{esc(message('hu','nav.home_label'))}" data-label-en="{esc(message('en','nav.home_label'))}" data-label-hu="{esc(message('hu','nav.home_label'))}">
      <span class="brand-mark" aria-hidden="true">↳</span>
      <span><b>TRANSFORMATION</b><em>OBSERVATORY · EPL v2</em></span>
    </a>
    <nav aria-label="{esc(message('hu','nav.primary_label'))}" data-label-en="{esc(message('en','nav.primary_label'))}" data-label-hu="{esc(message('hu','nav.primary_label'))}">
      <a href="{prefix}index.html">{ui('nav.portfolio')}</a>
      <a href="{prefix}comparison.html">V1 ↔ V2</a>
      <a href="{prefix}experiments/psychology-lens.html">{ui('nav.live_test')}</a>
    </nav>
    <div class="language-switch" role="group" aria-label="{esc(message('hu','nav.language_label'))}" data-label-en="{esc(message('en','nav.language_label'))}" data-label-hu="{esc(message('hu','nav.language_label'))}">
      <button type="button" data-set-language="hu" aria-pressed="true">HU</button>
      <button type="button" data-set-language="en" aria-pressed="false">EN</button>
    </div>
  </header>
  <main id="content">{body}</main>
  <footer><span>{ui('footer.architecture')}</span><span>v2.0.0 · 2026-07-20</span></footer>
  <script src="{prefix}assets/v2.js"></script>
</body></html>"""


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
          <p class="eyebrow">{esc(topic)} · {counts['transformation_proposal']} {label('transformation_proposal', counts['transformation_proposal'])}</p>
          <h2>{bi(en(problem['title']), hu(problem['title']))}</h2>
          <p class="lead">{bi(en(problem['public_question']), hu(problem['public_question']))}</p>
          <div class="mini-metrics"><span>{counts['finding']}<small>{label('finding', counts['finding'])}</small></span><span>{counts['lens_assessment']}<small>{label('lens_assessment', counts['lens_assessment'])}</small></span><span>{counts['dilemma']}<small>{label('dilemma', counts['dilemma'])}</small></span></div>
          <a class="arrow-link" href="topics/{esc(topic)}.html">{ui('index.open_map')} <span>→</span></a>
        </article>""")
    return f"""
    <section class="hero blueprint-grid">
      <div class="hero-copy">
        <p class="eyebrow">{ui('index.architecture_eyebrow')}</p>
        <h1>{ui('index.hero_title')}</h1>
        <p class="hero-deck">{ui('index.hero_deck')}</p>
        <a class="primary-action" href="#portfolio">{ui('index.explore')} ↓</a>
      </div>
      <div class="hero-instrument" aria-label="v2-korpusz összegzése" data-label-en="v2 corpus summary" data-label-hu="v2-korpusz összegzése">
        <span class="registration">{ui('index.live_slice')}</span>
        <strong>{total}</strong><small>{ui('index.typed_records')}</small>
        <div class="instrument-line"></div>
        <p>{ui('index.repeat_build')}</p>
      </div>
    </section>
    <section class="change-system" aria-labelledby="system-title">
      <div class="section-number">01</div><div>
      <p class="eyebrow">{ui('index.change_spine')}</p>
      <h2 id="system-title">{ui('index.conclusion_address')}</h2>
      <div class="dag-flow">
        <div><b>01</b><span>{label('finding', 1)}</span><small>{ui('index.finding_description')}</small></div>
        <div><b>02</b><span>{label('transformation_family', 1)}</span><small>{ui('index.family_description')}</small></div>
        <div><b>03</b><span>{label('transformation_proposal', 1)}</span><small>{ui('index.proposal_description')}</small></div>
        <div><b>04</b><span>{label('lens_definition', 1)}</span><small>{ui('index.perspective_description')}</small></div>
        <div><b>05</b><span>{label('dilemma', 1)}</span><small>{ui('index.dilemma_description')}</small></div>
        <div><b>06</b><span>{label('decision_package', 1)}</span><small>{ui('index.package_description')}</small></div>
      </div></div>
    </section>
    <section id="portfolio" class="portfolio">
      <div class="section-heading"><div><p class="eyebrow">{ui('index.portfolio_eyebrow')}</p><h2>{ui('index.fields')}</h2></div><a href="comparison.html">{ui('index.comparison_link')} →</a></div>
      <div class="topic-grid">{''.join(topic_cards)}</div>
    </section>
    <section class="live-launch"><div><p class="eyebrow">{ui('index.live_eyebrow')}</p><h2>{ui('index.live_title')}</h2><p>{ui('index.live_deck')}</p></div><a class="arrow-link" href="experiments/psychology-lens.html">{ui('index.live_open')} →</a></section>
    <aside class="honesty-band"><b>{ui('index.migration_boundary')}</b><p>{ui('index.migration_copy')}</p></aside>"""


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
            f'<tr data-verdict="{esc(a["content"]["verdict"])}"><th>{lens_label(a["content"]["lens_ref"].split(f"L-{topic}-",1)[-1])}</th><td><span class="verdict verdict-{esc(a["content"]["verdict"])}">{enum_label("verdict", a["content"]["verdict"])}</span></td><td>{len(a["content"]["finding_refs"])} {label("finding", len(a["content"]["finding_refs"]))}</td><td>{enum_label("confidence", a["content"]["confidence"])}</td></tr>'
            for a in related_assessments
        )
        dilemma_cards = "".join(
            f'<article class="dilemma"><span>{esc(d["content"]["legacy_cluster_id"])}</span><h4>{enum_label("dilemma_type", d["content"]["dilemma_type"])}</h4><p>{bi(d["content"]["tension"], hu(next((c["claim"] for c in data["clusters"] if c["id"]==d["content"]["legacy_cluster_id"]), d["content"]["tension"])))}</p><small>{ui("topic.evidence_value_note")}</small></article>'
            for d in related_dilemmas
        ) or f'<p class="empty">{ui("topic.no_dilemma")}</p>'
        research_items = "".join(f"<li>{bi(q['content']['question'], hu(data['brief']['what_research_could_resolve'][int(q['id'].rsplit('-',1)[-1])-1]))}</li>" for q in related_questions)
        sheets.append(f"""
        <article id="{sid.lower()}" class="proposal-sheet">
          <header><div class="proposal-code">{sid}<small>{enum_label('change_level', content['change_level'])}</small></div><div><p class="eyebrow">{ui('topic.proposal_eyebrow')}</p><h2>{bi(content['title'],hu(source['title']))}</h2><p class="proposal-goal">{bi(content['goal'],hu(source['goal']))}</p></div><span class="evidence evidence-{esc(content['evidence_status'])}">{enum_label('evidence', content['evidence_status'])}</span></header>
          <div class="proposal-grid"><section><h3>01 / {ui('topic.mechanism')}</h3><ol class="mechanisms">{mechanisms}</ol></section><section><h3>02 / {ui('topic.implementation_path')}</h3><ol class="timeline">{steps}</ol></section></div>
          <section class="lens-section"><div class="subhead"><div><h3>03 / {ui('topic.perspective_matrix')}</h3><p>{ui('topic.perspective_explainer')}</p></div><label>{ui('common.filter')} <select data-lens-filter>{localized_option('all','common.all_assessments')}{localized_option('supports_with_conditions','common.conditional_support')}{localized_option('insufficient_evidence','common.insufficient_evidence')}{localized_option('cautions','common.cautions')}</select></label></div><div class="table-wrap"><table><thead><tr><th>{ui('topic.perspective_column')}</th><th>{ui('topic.verdict_column')}</th><th>{ui('topic.evidence_column')}</th><th>{ui('topic.confidence_column')}</th></tr></thead><tbody>{lens_rows}</tbody></table></div></section>
          <div class="proposal-grid decisions"><section><h3>04 / {ui('topic.human_dilemmas')}</h3>{dilemma_cards}</section><section><h3>05 / {ui('topic.research_change_choice')}</h3><ol class="research-list">{research_items}</ol></section></div>
          <p class="audit-line">{esc(proposal['id'])} · {len(content['finding_refs'])} {ui('topic.finding_refs')} · {len(content['assumption_refs'])} {ui('topic.assumption_refs')} · {len(content['uncertainty_refs'])} {ui('topic.uncertainty_refs')}</p>
        </article>""")
    return f"""
    <section class="topic-hero blueprint-grid"><div><p class="eyebrow">{ui('topic.decision_package')} · {esc(topic)}</p><h1>{bi(en(problem['title']),hu(problem['title']))}</h1><p class="hero-deck">{bi(en(problem['public_question']),hu(problem['public_question']))}</p></div><div class="topic-stats"><span><b>{manifest['artifact_counts']['finding']}</b> {label('finding', manifest['artifact_counts']['finding'])}</span><span><b>{manifest['artifact_counts']['lens_assessment']}</b> {label('lens_assessment', manifest['artifact_counts']['lens_assessment'])}</span><span><b>{manifest['artifact_counts']['dilemma']}</b> {label('dilemma', manifest['artifact_counts']['dilemma'])}</span></div></section>
    <aside class="migration-note"><b>V1 → V2</b>{ui('topic.migration_note')}</aside>
    <nav class="change-spine" aria-label="{esc(message('hu','topic.change_nav_label'))}" data-label-en="{esc(message('en','topic.change_nav_label'))}" data-label-hu="{esc(message('hu','topic.change_nav_label'))}">{spine}</nav>
    <div class="proposal-stack">{''.join(sheets)}</div>"""


def render_comparison(records: list[dict[str, Any]], manifests: list[dict[str, Any]]) -> str:
    counts = Counter(r["record_type"] for r in records)
    total = sum(counts.values())
    row_keys = (
        "primary_unit", "canonical_language", "change_object",
        "professional_scrutiny", "value_conflict", "invalidation",
        "repeat_build", "audit_root",
    )
    row_values = {
        "proposals": counts["transformation_proposal"],
        "families": counts["transformation_family"],
        "assessments": counts["lens_assessment"],
        "dilemmas": counts["dilemma"],
    }
    table_rows = "".join(
        f"<tr><th>{ui(f'comparison.row.{key}.name', **row_values)}</th>"
        f"<td>{ui(f'comparison.row.{key}.v1', **row_values)}</td>"
        f"<td>{ui(f'comparison.row.{key}.v2', **row_values)}</td></tr>"
        for key in row_keys
    )
    artifact_bars = "".join(
        f'<div><span>{label(name, value)}</span><i style="--amount:{max(3,round(value/max(counts.values())*100))}%"></i><b>{value}</b></div>'
        for name,value in counts.most_common()
    )
    return f"""
    <section class="comparison-hero blueprint-grid"><div><p class="eyebrow">{ui('comparison.measured')}</p><h1>V1 <span>↔</span> V2</h1><p class="hero-deck">{ui('comparison.hero_deck')}</p></div><div class="hero-instrument"><span class="registration">{ui('comparison.current_slice')}</span><strong>{total}</strong><small>{ui('comparison.records_two_topics')}</small></div></section>
    <section class="comparison-section"><div class="section-heading"><div><p class="eyebrow">{ui('comparison.information_model')}</p><h2>{ui('comparison.actual_change')}</h2></div></div><div class="table-wrap"><table class="comparison-table"><thead><tr><th>{ui('comparison.dimension')}</th><th>V1</th><th>V2</th></tr></thead><tbody>{table_rows}</tbody></table></div></section>
    <section class="comparison-section split"><div><p class="eyebrow">{ui('comparison.corpus')}</p><h2>{ui('comparison.database_visible')}</h2><div class="artifact-bars">{artifact_bars}</div></div><aside class="verdict-panel"><span>{ui('comparison.verdict')}</span><h3>{ui('comparison.verdict_title')}</h3><p>{ui('comparison.verdict_copy')}</p></aside></section>
    <section class="comparison-section"><p class="eyebrow">{ui('comparison.limits')}</p><h2>{ui('comparison.limits_title')}</h2><div class="limit-grid"><article><b>01</b><p>{ui('comparison.limit_one')}</p></article><article><b>02</b><p>{ui('comparison.limit_two')}</p></article><article><b>03</b><p>{ui('comparison.limit_three')}</p></article></div></section>"""


def render_live_experiment() -> str:
    experiment_root = ROOT / "v2" / "experiments" / "2026-07-20-psychology-lens-live"
    comparison = load_json(experiment_root / "comparison.json")
    costs = load_json(experiment_root / "cost_report.json")["arms"]
    baseline_summary = load_json(experiment_root / "runs" / "live-korai-szelekcio-baseline" / "arm_summary.json")
    psychology_summary = load_json(experiment_root / "runs" / "live-korai-szelekcio-psychology" / "arm_summary.json")
    repository = ArtifactRepository(experiment_root, SchemaRegistry(ROOT / "schemas" / "v2"))
    psychology_assessments = sorted(
        (
            record for record in repository.list(record_type="lens_assessment")
            if record["content"]["lens_ref"] == "L-live-educational_psychology"
        ),
        key=lambda record: record["content"]["proposal_ref"],
    )
    baseline_package = repository.get_current("DP-live-baseline")["content"]["summary"]
    psychology_package = repository.get_current("DP-live-psychology")["content"]["summary"]
    baseline_eval = comparison["baseline_evaluation"]
    psychology_eval = comparison["psychology_evaluation"]
    cards = []
    for assessment in psychology_assessments:
        content = assessment["content"]
        proposal_ref = content["proposal_ref"]
        proposal_key = proposal_ref.removeprefix("TP-live-")
        cards.append(f"""
        <article class="impact-card">
          <header><b>{esc(proposal_key.upper())}</b><span class="verdict verdict-{esc(content['verdict'])}">{enum_label('verdict', content['verdict'])}</span></header>
          <h3>{ui(f'experiment.proposal.{proposal_key}.title')}</h3>
          <p class="impact-summary">{ui(f'experiment.proposal.{proposal_key}.impact')}</p>
          <details><summary>{ui('common.open_english_source')}</summary><p lang="en">{esc(content['assessment'])}</p></details>
          <small>{enum_label('confidence', content['confidence'])} {ui('common.confidence')} · {len(content['finding_refs'])} {ui('topic.finding_refs')}</small>
        </article>""")
    judge_rows = "".join(
        f"<tr><th>{ui(f'experiment.judge_dimension.{name}')}</th><td>{baseline_eval['dimensions'][name]:.1f}</td><td>{psychology_eval['dimensions'][name]:.1f}</td><td>{psychology_eval['dimensions'][name]-baseline_eval['dimensions'][name]:+.1f}</td></tr>"
        for name in baseline_eval["dimensions"]
    )
    total_cost = sum(arm["estimated_usd"] for arm in costs.values())
    return f"""
    <section class="experiment-hero blueprint-grid">
      <div><p class="eyebrow">{ui('experiment.eyebrow')}</p><h1>{ui('experiment.hero_title')}</h1><p class="hero-deck">{ui('experiment.hero_deck')}</p></div>
      <aside class="score-ticket"><span>{ui('experiment.descriptive_pair')}</span><div><b>{baseline_eval['total']:.3f}</b><small>{ui('experiment.baseline_perspectives')}</small></div><i>→</i><div><b>{psychology_eval['total']:.3f}</b><small>{ui('experiment.added_psychology')}</small></div><strong>{comparison['evaluation_delta']:+.3f}</strong></aside>
    </section>
    <aside class="live-boundary"><b>{ui('experiment.live_boundary')}</b><span>{ui('experiment.boundary_copy')}</span></aside>
    <section class="experiment-section">
      <p class="eyebrow">{ui('experiment.dependency_treatment')}</p><h2>{ui('experiment.option_title')}</h2>
      <div class="branch-rig" aria-label="Az alapváltozat és a pszichológiai változat függőségi gráfja" data-label-en="Baseline and psychology treatment DAG" data-label-hu="Az alapváltozat és a pszichológiai változat függőségi gráfja">
        <div class="branch-common"><b>12</b><span>{ui('experiment.research_steps')}</span></div>
        <div class="branch-common"><b>6</b><span>{ui('experiment.identical_transformations')}</span></div>
        <div class="branch-split"><div><b>12</b><span>{ui('experiment.baseline_lenses')}</span></div><div><b>+1</b><span>{ui('experiment.psychology_lens')}</span></div></div>
        <div class="branch-common"><b>5</b><span>{ui('experiment.rerun_descendants')}</span></div>
      </div>
      <div class="truth-stamps"><article><b>{ui('common.pass')}</b><span>{ui('experiment.hashes_identical')}</span></article><article><b>{ui('common.pass')}</b><span>{ui('experiment.six_assessments')}</span></article><article><b>{ui('common.pass')}</b><span>{ui('experiment.mechanism_reached')}</span></article></div>
    </section>
    <section class="experiment-section impact-zone">
      <div class="section-heading"><div><p class="eyebrow">{ui('experiment.proposal_psychology')}</p><h2>{ui('experiment.readings_title')}</h2></div><p>{ui('experiment.perspective_rule')}</p></div>
      <div class="impact-grid">{''.join(cards)}</div>
    </section>
    <section class="experiment-section split-results">
      <div><p class="eyebrow">{ui('experiment.substantive_effect')}</p><h2>{ui('experiment.warning_title')}</h2><p class="result-lead">{ui('experiment.warning_copy')}</p><blockquote>{ui('experiment.warning_quote')}</blockquote></div>
      <aside class="mechanism-index"><span>{ui('experiment.named_mechanisms')}</span><b>{ui('experiment.mechanism.bflpe')}</b><b>{ui('experiment.mechanism.self_concept')}</b><b>{ui('experiment.mechanism.self_determination')}</b><b>{ui('experiment.mechanism.labeling')}</b><small>{comparison['psychology_assessment_count']} {ui('experiment.assessment_count')} · {ui('experiment.package_carriage')}: {ui('common.pass') if comparison['position_carriage_passed'] else ui('experiment.fail')}</small></aside>
    </section>
    <section class="experiment-section">
      <p class="eyebrow">{ui('experiment.cross_family_judge')}</p><h2>{ui('experiment.lower_score')}</h2><p>{ui('experiment.judge_copy')}</p>
      <div class="table-wrap"><table class="score-table"><thead><tr><th>{ui('common.dimension')}</th><th>{ui('common.baseline')}</th><th>{ui('common.psychology_variant')}</th><th>Δ</th></tr></thead><tbody>{judge_rows}</tbody></table></div>
    </section>
    <section class="experiment-section package-pair">
      <p class="eyebrow">{ui('experiment.decision_package_pair')}</p><h2>{ui('experiment.outputs_title')}</h2>
      <div><details><summary>{ui('experiment.baseline_package')} · {len(baseline_package.split())} {ui('common.words')}</summary><p lang="en">{esc(baseline_package)}</p></details><details><summary>{ui('experiment.psychology_package')} · {len(psychology_package.split())} {ui('common.words')}</summary><p lang="en">{esc(psychology_package)}</p></details></div>
    </section>
    <section class="experiment-section audit-summary">
      <div><p class="eyebrow">{ui('experiment.run_audit')}</p><h2>{ui('experiment.audit_title')}</h2><p>{ui('experiment.audit_copy')}</p></div>
      <dl><div><dt>{ui('common.live_calls')}</dt><dd>{sum(arm['calls'] for arm in costs.values())}</dd></div><div><dt>{ui('common.audit_cost')}</dt><dd>${total_cost:.2f}</dd></div><div><dt>{ui('common.treatment_cache')}</dt><dd>{psychology_summary['execution']['cache_hits']}/32</dd></div><div><dt>{ui('common.failed_current_nodes')}</dt><dd>{psychology_summary['execution']['failed']}</dd></div></dl>
    </section>
    <aside class="honesty-band"><b>{ui('experiment.interpretation_limit')}</b><p>{ui('experiment.interpretation_copy')}</p></aside>"""


def main() -> int:
    schemas = SchemaRegistry(ROOT / "schemas" / "v2")
    repository = ArtifactRepository(ROOT / "v2", schemas)
    records = repository.list()
    catalog = load_json(ROOT / "v2" / "catalog" / "topics.json")
    manifests = catalog["topics"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "topics").mkdir(exist_ok=True)
    (OUT / "experiments").mkdir(exist_ok=True)
    (OUT / "index.html").write_text(
        page(message("en", "meta.portfolio_title"), message("hu", "meta.portfolio_title"), render_index(records, manifests)),
        encoding="utf-8",
    )
    for manifest in manifests:
        topic = manifest["topic"]
        body = render_topic(topic, records, manifest)
        problem_title = legacy(topic)["topic"]["problem_brief"]["title"]
        (OUT / "topics" / f"{topic}.html").write_text(
            page(en(problem_title), hu(problem_title), body, depth=1), encoding="utf-8"
        )
    (OUT / "comparison.html").write_text(page("V1 ↔ V2", "V1 ↔ V2", render_comparison(records, manifests)), encoding="utf-8")
    (OUT / "experiments" / "psychology-lens.html").write_text(
        page(message("en", "meta.live_test_title"), message("hu", "meta.live_test_title"), render_live_experiment(), depth=1),
        encoding="utf-8",
    )
    print(f"Rendered {len(manifests) + 3} pages from {len(records)} migrated artifacts plus the live experiment into {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
