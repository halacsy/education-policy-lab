#!/usr/bin/env python3
"""Render the public Education Policy Atlas from accepted v2 production artifacts."""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.i18n import BILINGUAL_VERSION, is_localized_text  # noqa: E402
from policy_lab.jsonio import content_hash  # noqa: E402
from policy_lab.render import (  # noqa: E402
    PUBLIC_RECORD_TYPES,
    canonical_url,
    href_between,
    record_index_route,
    record_route,
    topic_route,
)
from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402

ASSET_VERSION = "d60-record-pages"
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
SITE_URL = PUBLICATION["site_url"]
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


def localize_hungarian(value: Any) -> str:
    localized = str(value)
    for replacement in CATALOGS["hu"]["content_replacements"]:
        localized = re.sub(replacement["pattern"], replacement["replacement"], localized)
    return localized


def bi(english: Any, hungarian: Any, tag: str = "span") -> str:
    localized = localize_hungarian(hungarian)
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


def page(
    title: dict[str, str],
    body: str,
    *,
    route: str,
    description: dict[str, str] | None = None,
    record_meta: dict[str, str] | None = None,
) -> str:
    depth = len(Path(route).parent.parts)
    prefix = "../" * depth
    asset_prefix = f"{prefix}v2/assets/"
    home = f"{prefix}index.html"
    description = description or {
        "en": msg("en", "public_site.home_deck"),
        "hu": msg("hu", "public_site.home_deck"),
    }
    title_hu = localize_hungarian(title["hu"])
    description_hu = localize_hungarian(description["hu"])
    canonical = canonical_url(SITE_URL, route)
    metadata = "".join(
        f' data-record-{esc(key.replace("_", "-"))}="{esc(value)}"'
        for key, value in (record_meta or {}).items()
    )
    return f'''<!doctype html>
<html lang="hu" data-language="hu" data-title-en="{esc(title['en'])} · Education Policy Atlas" data-title-hu="{esc(title_hu)} · Oktatáspolitikai Atlasz"{metadata}>
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{esc(description_hu)}" data-description-en="{esc(description['en'])}" data-description-hu="{esc(description_hu)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:type" content="article"><meta property="og:url" content="{esc(canonical)}">
  <meta property="og:title" content="{esc(title_hu)} · Oktatáspolitikai Atlasz"><meta property="og:description" content="{esc(description_hu)}">
  <title>{esc(title_hu)} · Oktatáspolitikai Atlasz</title>
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
    plan_meta = manifest.get("run_plan")
    if not str(manifest.get("architecture_version", "")).startswith("3.") or not plan_meta:
        raise ValueError(f"Published result is not backed by an explicit v3 RunPlan: {topic}")
    run_plan = load(root / plan_meta["path"])
    summary = manifest["summary"]
    records = repository.list()
    records_by_id = {record["id"]: record for record in records}
    records_by_type: dict[str, list[dict[str, Any]]] = {}
    outgoing_by_id: dict[str, list[Any]] = {}
    incoming_by_id: dict[str, list[tuple[str, Any]]] = {}
    for record in records:
        records_by_type.setdefault(record["record_type"], []).append(record)
        references = list(schemas.references(record))
        outgoing_by_id[record["id"]] = references
        for reference in references:
            incoming_by_id.setdefault(reference.target_id, []).append((record["id"], reference))
    package = records_by_id[summary["package_ref"]]
    if package["schema_version"] != BILINGUAL_VERSION:
        raise ValueError(f"Published package is not canonical bilingual v2.1: {topic}")
    topic_data = load(ROOT / "topics" / topic / "topic.json")
    briefs = records_by_type.get("problem_brief", [])
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
        "records_by_id": records_by_id,
        "records_by_type": records_by_type,
        "outgoing_by_id": outgoing_by_id,
        "incoming_by_id": incoming_by_id,
        "summary": summary,
        "package": package,
        "evaluation": records_by_id[summary["evaluation_ref"]],
        "readiness": records_by_id[summary["readiness_ref"]],
        "manifest": manifest,
        "run_plan": run_plan,
        "run_tag": PUBLIC_TOPICS[topic],
    }


def v3_lineage(data: dict[str, Any], *, href: str) -> str:
    plan = data["run_plan"]
    manifest = data["manifest"]
    plan_hash = manifest["run_plan"]["content_hash"]
    return f'''<div class="v3-lineage"><div class="v3-seal"><b>V3</b><span>{ui('public_site.v3_badge')}</span></div><div class="v3-route"><strong>{ui('public_site.v3_route')}</strong><small>DagSpec {esc(plan['dag_version'])} · {len(plan['nodes'])} {ui('public_site.v3_nodes')} · {len(plan['edges'])} {ui('public_site.v3_edges')} · RunPlan {esc(plan_hash[:10])}…</small></div><a href="{esc(href)}">{ui('public_site.v3_open_dag')} ↗</a></div>'''


def list_bi(record: dict[str, Any], field: str) -> str:
    return "".join(
        f"<li>{semantic(value)}</li>"
        for value in record["content"].get(field, [])
    )


PUBLIC_PAGE_TYPES = tuple(
    record_type
    for record_type in PUBLIC_RECORD_TYPES
    if record_type != "canonical_claim"
)


def localized_value(value: dict[str, str], language: str) -> str:
    if not is_localized_text(value):
        raise ValueError(f"Expected localized text, got {value!r}")
    return str(value[language])


def record_title(record: dict[str, Any]) -> dict[str, str]:
    content = record["content"]
    key_by_type = {
        "finding": "claim",
        "canonical_claim": "statement",
        "transformation_proposal": "title",
        "research_question": "question",
        "policy_question": "question",
        "problem_brief": "title",
        "problem_brief_proposal": "title",
        "dilemma": "title",
    }
    key = key_by_type.get(record["record_type"])
    if key and is_localized_text(content.get(key)):
        return content[key]
    type_key = f"record_page.types.{record['record_type']}"
    return {
        "en": f"{msg('en', type_key)} · {record['id']}",
        "hu": f"{msg('hu', type_key)} · {record['id']}",
    }


def record_description(record: dict[str, Any]) -> dict[str, str]:
    content = record["content"]
    for key in ("claim", "goal", "why_it_matters", "problem_statement", "tension", "derivation_notice"):
        if is_localized_text(content.get(key)):
            return content[key]
    return record_title(record)


def enum_ui(group: str, value: str) -> str:
    return ui(f"record_page.enum.{group}.{value}")


def semantic_list(values: list[Any], *, ordered: bool = False, class_name: str = "") -> str:
    tag = "ol" if ordered else "ul"
    class_attr = f' class="{class_name}"' if class_name else ""
    items = "".join(f"<li>{semantic(value)}</li>" for value in values)
    return f"<{tag}{class_attr}>{items}</{tag}>"


def record_href(data: dict[str, Any], source_route: str, record: dict[str, Any]) -> str:
    target = record_route(data["manifest"]["topic"], record["record_type"], record["id"])
    return href_between(source_route, target)


def record_anchor(
    data: dict[str, Any], source_route: str, record_id: str, *, label: Any | None = None
) -> str:
    target = data["records_by_id"].get(record_id)
    if target is None:
        return f"<code>{esc(record_id)}</code>"
    if target["record_type"] not in PUBLIC_PAGE_TYPES:
        return f"<code>{esc(record_id)}</code>"
    title = semantic(label) if is_localized_text(label) else semantic(record_title(target))
    return f'<a href="{esc(record_href(data, source_route, target))}">{title}</a>'


def record_reference_list(
    data: dict[str, Any], source_route: str, record_ids: list[str], *, class_name: str = "record-links"
) -> str:
    if not record_ids:
        return f'<p class="empty">{ui("record_page.no_relationships")}</p>'
    return f'<ul class="{class_name}">' + "".join(
        f"<li>{record_anchor(data, source_route, record_id)}</li>"
        for record_id in record_ids
    ) + "</ul>"


def artifact_section(label_key: str, content: str, *, class_name: str = "artifact-section") -> str:
    return f'<section class="{class_name}"><h2>{ui(label_key)}</h2>{content}</section>'


def related_excerpt(record: dict[str, Any]) -> Any | None:
    content = record["content"]
    for key in ("statement", "question", "rationale", "reduction_path", "title"):
        if is_localized_text(content.get(key)):
            return content[key]
    return None


def supporting_notes(data: dict[str, Any], ids: list[str]) -> str:
    notes = []
    for record_id in ids:
        related = data["records_by_id"].get(record_id)
        if related is None:
            notes.append(f"<li><code>{esc(record_id)}</code></li>")
            continue
        excerpt = related_excerpt(related)
        rendered = semantic(excerpt) if excerpt else ""
        notes.append(f"<li><code>{esc(record_id)}</code>{rendered}</li>")
    return '<ul class="supporting-notes">' + "".join(notes) + "</ul>"


def render_finding_record(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    content = record["content"]
    sources = []
    for source_id in content["source_refs"]:
        source = data["records_by_id"][source_id]
        source_content = source["content"]
        source_title = semantic(source_content["title"])
        if source_content["url"].startswith(("https://", "http://")):
            source_title = f'<a href="{esc(source_content["url"])}" rel="noopener">{source_title} ↗</a>'
        sources.append(
            f'''<article class="source-card"><code>{esc(source_id)}</code><h3>{source_title}</h3><dl><div><dt>{ui('record_page.source_type')}</dt><dd>{esc(source_content['source_type'])}</dd></div><div><dt>{ui('record_page.accessed')}</dt><dd>{esc(source_content['accessed_at'])}</dd></div><div><dt>{ui('record_page.license')}</dt><dd>{esc(source_content['license_status'])}</dd></div></dl></article>'''
        )
    profile = f'''<dl class="evidence-profile"><div><dt>{ui('record_page.kind')}</dt><dd>{enum_ui('kind', content['kind'])}</dd></div><div><dt>{ui('record_page.evidence_strength')}</dt><dd>{ui('enum.evidence.' + content['evidence_strength'])}</dd></div><div><dt>{ui('record_page.transferability')}</dt><dd>{enum_ui('transferability', content['transferability'])}</dd></div><div><dt>{ui('record_page.time_scope')}</dt><dd>{semantic(content['time_scope'])}</dd></div><div><dt>{ui('record_page.population')}</dt><dd>{semantic(content['population'])}</dd></div><div><dt>{ui('record_page.domain_tags')}</dt><dd>{' · '.join(f'<code>{esc(tag)}</code>' for tag in content['domain_tags'])}</dd></div></dl>'''
    sections = [
        artifact_section("record_page.evidence_profile", profile),
        artifact_section("record_page.context", f"<p>{semantic(content['context'])}</p>"),
        artifact_section("record_page.source", '<div class="source-grid">' + "".join(sources) + "</div>"),
    ]
    if content["limitations"]:
        sections.append(artifact_section("record_page.limitations", semantic_list(content["limitations"])))
    if content["assumption_ids"]:
        sections.append(artifact_section("record_page.assumptions", supporting_notes(data, content["assumption_ids"])))
    if content["uncertainty_ids"]:
        sections.append(artifact_section("record_page.uncertainties", supporting_notes(data, content["uncertainty_ids"])))
    return '<aside class="claim-contract">' + ui("record_page.canonical_claim_note") + "</aside>" + "".join(sections)


def render_transformation_record(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    content = record["content"]
    steps = "".join(
        f'''<li><time>{semantic(step['timeline'])}</time><div><b>{semantic(step['actor'])}</b><p>{semantic(step['action'])}</p></div></li>'''
        for step in content["implementation_steps"]
    )
    profile = f'''<dl class="evidence-profile"><div><dt>{ui('record_page.change_level')}</dt><dd>{ui('enum.change_level.' + content['change_level'])}</dd></div><div><dt>{ui('record_page.evidence_strength')}</dt><dd>{ui('enum.evidence.' + content['evidence_status'])}</dd></div><div><dt>{ui('record_page.identifier')}</dt><dd><code>{esc(record['id'])}</code></dd></div></dl>'''
    return "".join([
        artifact_section("record_page.proposal_goal", f'<p class="record-lead">{semantic(content["goal"])}</p>{profile}'),
        artifact_section("record_page.mechanisms", semantic_list(content["mechanisms"], ordered=True, class_name="mechanisms")),
        artifact_section("record_page.implementation", f'<ol class="record-timeline">{steps}</ol>'),
        '<div class="artifact-split">' + artifact_section("record_page.benefits", semantic_list(content["expected_benefits"])) + artifact_section("record_page.costs", semantic_list(content["costs"])) + "</div>",
        '<div class="artifact-split">' + artifact_section("record_page.risks", semantic_list(content["risks"])) + artifact_section("record_page.equity", f'<p>{semantic(content["equity_impact"])}</p>') + "</div>",
        artifact_section("record_page.supporting_findings", record_reference_list(data, route, content["finding_refs"])),
    ])


def render_research_question_record(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    content = record["content"]
    profile = f'''<dl class="evidence-profile"><div><dt>{ui('record_page.decision_impact')}</dt><dd>{enum_ui('impact', content['decision_impact'])}</dd></div><div><dt>{ui('record_page.answerability')}</dt><dd>{enum_ui('answerability', content['answerability'])}</dd></div></dl>'''
    return "".join([
        artifact_section("record_page.research_why", f'<p class="record-lead">{semantic(content["why_it_matters"])}</p>{profile}'),
        artifact_section("record_page.research_method", f'<p>{semantic(content["method"])}</p>'),
        artifact_section("record_page.related_proposals", record_reference_list(data, route, content["proposal_refs"])),
        artifact_section("record_page.uncertainties", supporting_notes(data, content["uncertainty_refs"])),
    ])


def render_dilemma_record(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    content = record["content"]
    poles = "".join(f'<li>{semantic(value)}</li>' for value in content["value_poles"])
    return "".join([
        f'<aside class="dilemma-type">{bi(content["dilemma_type"], msg("hu", "enum.dilemma_type." + content["dilemma_type"]))}</aside>',
        artifact_section("record_page.dilemma_tension", f'<p class="record-lead">{semantic(content["tension"])}</p>'),
        artifact_section("record_page.value_poles", f'<ul class="value-poles">{poles}</ul>'),
        '<div class="artifact-split">' + artifact_section("record_page.affected_groups", semantic_list(content["affected_groups"])) + artifact_section("record_page.decision_question", f'<p>{semantic(content["decision_question"])}</p>') + "</div>",
        artifact_section("record_page.evidence_boundary", f'<p>{semantic(content["evidence_boundary"])}</p>'),
        artifact_section("record_page.related_proposals", record_reference_list(data, route, content["proposal_refs"])),
        artifact_section("record_page.supporting_findings", record_reference_list(data, route, content["finding_refs"])),
    ])


def render_policy_question_record(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    content = record["content"]
    directions = content.get("research_directions")
    parts = [
        artifact_section("record_page.policy_submission_context", f'<p class="record-lead">{semantic(content["submission_context"])}</p>'),
        artifact_section("record_page.approval_basis", f'<p>{semantic(content["approval_basis"])}</p>'),
    ]
    if directions:
        direction_body = "".join([
            f'<h3>{ui("record_page.hypotheses")}</h3>{semantic_list(directions["hypotheses_to_test"])}',
            f'<h3>{ui("record_page.inquiry_priorities")}</h3>{semantic_list(directions["inquiry_priorities"])}',
            f'<h3>{ui("record_page.response_domains")}</h3>{semantic_list(directions["candidate_response_domains"])}',
        ])
        parts.append(artifact_section("record_page.research_directions", direction_body))
    return "".join(parts)


def render_brief_record(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    content = record["content"]
    parts = [
        artifact_section("record_page.brief_problem", f'<p class="record-lead">{semantic(content["problem_statement"])}</p>'),
        '<div class="artifact-split">' + artifact_section("record_page.learning_goals", semantic_list(content["learning_goals"], ordered=True)) + artifact_section("record_page.scope", f'<p>{semantic(content["scope"])}</p>') + "</div>",
    ]
    if content.get("framing_notes"):
        parts.append(artifact_section("record_page.framing_notes", semantic_list(content["framing_notes"])))
    if content.get("approval_basis"):
        parts.append(artifact_section("record_page.approval_basis", f'<p>{semantic(content["approval_basis"])}</p>'))
    if content.get("seed_sources"):
        source_items = "".join(f'<li><code>{esc(source)}</code></li>' for source in content["seed_sources"])
        parts.append(artifact_section("record_page.seed_sources", f'<ul class="record-links">{source_items}</ul>'))
    return "".join(parts)


def render_option_space_record(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    content = record["content"]
    directions = "".join(
        f'''<article class="direction-card"><code>{esc(direction['id'])}</code><h3>{semantic(direction['title'])}</h3><p>{semantic(direction['scope'])}</p>{record_reference_list(data, route, direction['finding_refs'])}</article>'''
        for direction in content["directions"]
    )
    rejected = "".join(
        f'''<li><b>{semantic(item['framing'])}</b><p>{semantic(item['reason'])}</p></li>'''
        for item in content["rejected_framings"]
    )
    parts = [
        artifact_section("record_page.derivation_notice", f'<p class="record-lead">{semantic(content["derivation_notice"])}</p>'),
        artifact_section("record_page.option_directions", f'<div class="direction-grid">{directions}</div>'),
    ]
    if rejected:
        parts.append(artifact_section("record_page.rejected_framings", f'<ul class="rejected-list">{rejected}</ul>'))
    return "".join(parts)


def render_record_content(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    renderers = {
        "finding": render_finding_record,
        "transformation_proposal": render_transformation_record,
        "research_question": render_research_question_record,
        "dilemma": render_dilemma_record,
        "policy_question": render_policy_question_record,
        "problem_brief": render_brief_record,
        "problem_brief_proposal": render_brief_record,
        "option_space_proposal": render_option_space_record,
    }
    try:
        renderer = renderers[record["record_type"]]
    except KeyError as exc:
        raise ValueError(f"No public renderer for {record['record_type']}") from exc
    return renderer(data, record, route)


def graph_links(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    outgoing = []
    for reference in data["outgoing_by_id"].get(record["id"], []):
        target = data["records_by_id"].get(reference.target_id)
        if target is None:
            continue
        if target["record_type"] in PUBLIC_PAGE_TYPES:
            outgoing.append((reference.field, target))
    incoming = []
    for source_id, reference in data["incoming_by_id"].get(record["id"], []):
        source = data["records_by_id"][source_id]
        if source["record_type"] in PUBLIC_PAGE_TYPES:
            incoming.append((reference.field, source))

    def items(rows: list[tuple[str, dict[str, Any]]]) -> str:
        if not rows:
            return f'<p class="empty">{ui("record_page.no_relationships")}</p>'
        return '<ul class="graph-links">' + "".join(
            f'''<li><code>{esc(field)}</code><a href="{esc(record_href(data, route, target))}"><span>{ui('record_page.types.' + target['record_type'])}</span><b>{semantic(record_title(target))}</b></a></li>'''
            for field, target in rows
        ) + "</ul>"

    return f'''<section class="record-graph"><p class="eyebrow">{ui('record_page.relationships')}</p><div><section><h2>{ui('record_page.references')}</h2>{items(outgoing)}</section><section><h2>{ui('record_page.used_by')}</h2>{items(incoming)}</section></div></section>'''


def record_identity(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    digest = content_hash(record)
    lineage_hashes = []
    version = record
    while version:
        lineage_hashes.append(content_hash(version))
        supersedes = version.get("supersedes")
        version = data["repo"].get_by_hash(supersedes) if supersedes else None
    versions = "".join(
        f'<li class="{"is-current" if index == 0 else ""}"><b>{ui("record_page.current_version") if index == 0 else ui("record_page.versions")}</b><code>{esc(version_hash)}</code></li>'
        for index, version_hash in enumerate(lineage_hashes)
    )
    audit_href = href_between(route, "audit.html") + (
        f"?topic={quote(data['manifest']['topic'])}&run={quote(data['manifest']['run_id'])}"
        f"&node={quote('record:' + digest)}"
    )
    return f'''<section class="record-identity"><div><p class="eyebrow">{ui('record_page.technical_identity')}</p><dl><div><dt>{ui('record_page.type')}</dt><dd>{ui('record_page.types.' + record['record_type'])}</dd></div><div><dt>{ui('record_page.status')}</dt><dd>{enum_ui('status', record['status'])}</dd></div><div><dt>{ui('record_page.identifier')}</dt><dd><code>{esc(record['id'])}</code></dd></div><div><dt>{ui('record_page.created')}</dt><dd>{esc(record['created_at'])}</dd></div><div><dt>{ui('record_page.content_hash')}</dt><dd><code>{esc(digest)}</code></dd></div></dl><a class="text-action" href="{esc(audit_href)}">{ui('record_page.audit')} ↗</a></div><div><p class="eyebrow">{ui('record_page.versions')}</p><ol class="version-list">{versions}</ol></div></section>'''


def record_navigation(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    peers = data["records_by_type"].get(record["record_type"], [])
    index = next(index for index, peer in enumerate(peers) if peer["id"] == record["id"])
    links = []
    for label, offset in (("previous", -1), ("next", 1)):
        peer_index = index + offset
        if 0 <= peer_index < len(peers):
            peer = peers[peer_index]
            links.append(
                f'''<a class="record-nav-{label}" href="{esc(record_href(data, route, peer))}"><span>{ui('record_page.' + label)}</span><b>{semantic(record_title(peer))}</b></a>'''
            )
        else:
            links.append(f'<span class="record-nav-{label}"></span>')
    return '<nav class="record-navigation" aria-label="Record navigation">' + "".join(links) + "</nav>"


def render_record_page(data: dict[str, Any], record: dict[str, Any], route: str) -> str:
    topic = data["manifest"]["topic"]
    topic_href = href_between(route, topic_route(topic))
    index_href = href_between(route, record_index_route(topic))
    digest = content_hash(record)
    status_note = "admitted_note" if record["status"] == "admitted" else "candidate_note"
    return f'''<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="{esc(topic_href)}">{semantic(data['topic']['problem_brief']['title'])}</a><span>→</span><a href="{esc(index_href)}">{ui('record_page.records_title')}</a><span>→</span><code>{esc(record['id'])}</code></nav><article class="record-page"><header class="record-hero blueprint-grid"><div><p class="eyebrow">{ui('record_page.types.' + record['record_type'])} · {esc(record['id'])}</p><h1>{semantic(record_title(record))}</h1></div><aside><span class="record-status status-{esc(record['status'])}">{enum_ui('status', record['status'])}</span><b>{ui('record_page.' + status_note)}</b><code>{esc(digest[:16])}…</code></aside></header><aside class="record-boundary">{ui('record_page.external_gate')}</aside><div class="record-body">{render_record_content(data, record, route)}</div>{graph_links(data, record, route)}{record_identity(data, record, route)}{record_navigation(data, record, route)}</article>'''


def render_record_index(data: dict[str, Any], route: str) -> str:
    topic = data["manifest"]["topic"]
    topic_href = href_between(route, topic_route(topic))
    groups = []
    for record_type in PUBLIC_PAGE_TYPES:
        records = data["records_by_type"].get(record_type, [])
        if not records:
            continue
        cards = "".join(
            f'''<li><a href="{esc(record_href(data, route, record))}"><code>{esc(record['id'])}</code><b>{semantic(record_title(record))}</b><span>{enum_ui('status', record['status'])}</span></a></li>'''
            for record in records
        )
        groups.append(
            f'''<section class="record-index-group"><header><h2>{ui('record_page.types.' + record_type)}</h2><b>{len(records)}</b></header><ol>{cards}</ol></section>'''
        )
    return f'''<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="{esc(topic_href)}">{semantic(data['topic']['problem_brief']['title'])}</a><span>→</span><code>{ui('record_page.records_title')}</code></nav><section class="record-index-hero blueprint-grid"><p class="eyebrow">{ui('record_page.records_title')}</p><h1>{ui('record_page.records_title')}</h1><p>{ui('record_page.records_note')}</p></section><div class="record-index">{''.join(groups)}</div>'''


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
    assessments = data["records_by_type"].get("lens_assessment", [])
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
    topic_slug = data["manifest"]["topic"]
    route = topic_route(topic_slug)
    problem = topic["problem_brief"]
    package = data["package"]
    records_by_id = data["records_by_id"]
    summary = data["summary"]
    proposals = [records_by_id[ref] for ref in package["content"]["proposal_refs"]]
    dilemmas = [records_by_id[ref] for ref in package["content"]["dilemma_refs"]]
    questions = [records_by_id[ref] for ref in package["content"]["research_question_refs"]]
    coverage = records_by_id[package["content"]["coverage_ledger_refs"][0]]

    cards = []
    for proposal in proposals:
        content = proposal["content"]
        proposal_id = proposal["id"]
        proposal_href = record_href(data, route, proposal)
        steps = "".join(
            f"<li><time>{semantic(step['timeline'])}</time><b>{semantic(step['actor'])}</b><p>{semantic(step['action'])}</p></li>"
            for step in content["implementation_steps"]
        )
        cards.append(f'''<article class="proposal-sheet"><header><div class="proposal-code">{esc(proposal_id.split('-')[-1].upper())}<small>{ui('public_site.proposal_short')}</small></div><div><h2>{semantic(content['title'])}</h2><p class="proposal-goal">{semantic(content['goal'])}</p><a class="canonical-record-link" href="{esc(proposal_href)}">{ui('record_page.open_record')} →</a></div><span class="evidence evidence-{esc(content['evidence_status'])}">{bi(content['evidence_status'], msg('hu','enum.evidence.'+content['evidence_status']))}</span></header><details class="proposal-detail"><summary>{ui('public_site.proposal_details')}</summary><div class="proposal-grid"><section><h3>{ui('production.mechanisms')}</h3><ol class="mechanisms">{list_bi(proposal, 'mechanisms')}</ol></section><section><h3>{ui('production.implementation')}</h3><ol class="timeline">{steps}</ol></section></div><div class="proposal-grid"><section><h3>{ui('production.benefits')}</h3><ul>{list_bi(proposal,'expected_benefits')}</ul><h3>{ui('production.equity')}</h3><p>{semantic(content['equity_impact'])}</p></section><section><h3>{ui('production.costs')}</h3><ul>{list_bi(proposal,'costs')}</ul><h3>{ui('production.risks')}</h3><ul>{list_bi(proposal,'risks')}</ul></section></div></details></article>''')

    coverage_items = "".join(
        f"<li><b>{entry['direction_id']}</b> {semantic(entry['direction_title'])} → {esc(', '.join(entry['proposal_refs']))}</li>"
        for entry in coverage["content"]["entries"]
    )
    dilemma_cards = "".join(
        f'''<article class="dilemma"><span>{bi(record['content']['dilemma_type'],msg('hu','enum.dilemma_type.'+record['content']['dilemma_type']))}</span><h4><a href="{esc(record_href(data, route, record))}">{semantic(record['content']['title'])}</a></h4><p>{semantic(record['content']['tension'])}</p><small>{semantic(record['content']['evidence_boundary'])}</small></article>'''
        for record in dilemmas
    )
    research_items = "".join(
        f'''<li><b><a href="{esc(record_href(data, route, record))}">{semantic(record['content']['question'])}</a></b><p>{semantic(record['content']['why_it_matters'])}</p></li>'''
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
        f'''<li><b>{esc(entry['finding_ref'])}</b> <a href="{esc(record_href(data, route, records_by_id[entry['finding_ref']]))}">{semantic(entry['claim'])}</a><div>{source_links(entry)}</div></li>'''
        for entry in package["content"]["evidence_appendix"]
    )
    concerns = list_bi(data["evaluation"], "concerns")
    matrix = render_perspective_matrix(data, proposals)
    audit_href = f"../audit.html?topic={data['manifest']['topic']}&run={data['manifest']['run_id']}&view=execution"
    lineage = v3_lineage(data, href=audit_href)
    record_index_href = href_between(route, record_index_route(topic_slug))
    briefs = data["records_by_type"].get("problem_brief", [])
    brief_link = (
        f'<a class="text-action" href="{esc(record_href(data, route, briefs[0]))}">{ui("record_page.open_record")} →</a>'
        if briefs else ""
    )

    return f'''<section class="topic-hero blueprint-grid"><div><p class="eyebrow">{ui('public_site.topic_eyebrow')}</p><h1>{semantic(problem['public_question'])}</h1><p class="hero-deck">{semantic(problem['problem_statement'])}</p></div><div class="topic-stats"><span><b>{len(proposals)}</b>{ui('public_site.proposal_count')}</span><span><b>{summary['counts']['finding']}</b>{ui('production.fresh_findings')}</span><span><b>{len(dilemmas)}</b>{ui('public_site.dilemma_count')}</span></div></section><aside class="migration-note"><b>{ui('production.readiness')}</b>{ui('production.ready_with_conditions')} · {ui('production.external_gate')}</aside><div class="topic-lineage-wrap">{lineage}</div><section class="record-directory-callout"><div><p class="eyebrow">{ui('record_page.records_title')}</p><h2>{ui('record_page.records_title')}</h2><p>{ui('record_page.records_note')}</p></div><a class="primary-action" href="{esc(record_index_href)}">{ui('record_page.open_records')} →</a></section>{change_spine()}<section class="comparison-section split" id="overview"><div><p class="eyebrow">01 / {ui('public_site.problem_title')}</p><h2>{ui('public_site.problem_title')}</h2><p class="result-lead">{semantic(problem['problem_statement'])}</p>{brief_link}</div><div><h3>{ui('public_site.learning_title')}</h3><ul>{learning_goals}</ul></div><details class="full-summary"><summary>{ui('public_site.full_summary')}</summary><p>{semantic(package['content']['summary'])}</p></details></section><section class="proposal-stack" id="options"><div class="section-heading"><div><p class="eyebrow">02 / {ui('production.proposals')}</p><h2>{ui('production.proposals')}</h2></div></div>{''.join(cards)}</section>{matrix}<section class="comparison-section"><h2>{ui('production.coverage')}</h2><ul>{coverage_items}</ul></section><section class="comparison-section decisions" id="dilemmas"><p class="eyebrow">04 / {ui('production.dilemmas')}</p><h2>{ui('production.dilemmas')}</h2>{dilemma_cards}</section><section class="comparison-section" id="research"><p class="eyebrow">05 / {ui('production.research')}</p><h2>{ui('production.research')}</h2><ol class="research-list">{research_items}</ol></section><section class="comparison-section"><h2>{ui('production.conditions')}</h2><ul>{concerns}</ul></section><section class="comparison-section" id="evidence"><details><summary><h2>{ui('production.evidence')} · {len(package['content']['evidence_appendix'])}</h2></summary><p>{ui('public_site.sources_note')}</p><ol class="research-list">{appendix}</ol></details></section>'''


def render_home(data: dict[str, dict[str, Any]]) -> str:
    cards = []
    for index, (topic, item) in enumerate(data.items(), 1):
        problem = item["topic"]["problem_brief"]
        audit_href = f"audit.html?topic={topic}&run={item['manifest']['run_id']}&view=execution"
        lineage = v3_lineage(item, href=audit_href)
        cards.append(f'''<article class="topic-sheet"><span class="sheet-index">{index:02d}</span><p class="eyebrow">{bi('QUESTION','KÉRDÉS')} {index:02d}</p><h2>{bi(problem['public_question']['en'],problem['public_question']['hu'])}</h2><p class="lead">{bi(short_intro(problem['problem_statement']['en']),short_intro(problem['problem_statement']['hu']))}</p>{lineage}<div class="mini-metrics"><span>{item['summary']['counts']['transformation_proposal']}<small>{ui('public_site.proposal_count')}</small></span><span>{item['summary']['counts']['dilemma']}<small>{ui('public_site.dilemma_count')}</small></span></div><a class="arrow-link" href="questions/{topic}.html">{ui('production.open')} →</a></article>''')

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
    generated_routes = ["index.html"]

    def write(route: str, source: str) -> None:
        target = OUT / route
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")

    home_title = {"en": msg("en", "public_site.home_title"), "hu": msg("hu", "public_site.home_title")}
    write("index.html", page(home_title, render_home(data), route="index.html"))
    record_page_count = 0
    for topic, item in data.items():
        generated_directory = QUESTION_OUT / topic
        if generated_directory.exists():
            shutil.rmtree(generated_directory)
        problem = item["topic"]["problem_brief"]
        dossier_route = topic_route(topic)
        write(
            dossier_route,
            page(
                problem["public_question"],
                render_topic(item),
                route=dossier_route,
                description=problem["problem_statement"],
            ),
        )
        generated_routes.append(dossier_route)

        index_route = record_index_route(topic)
        index_title = {
            "en": f"{msg('en', 'record_page.records_title')} · {problem['title']['en']}",
            "hu": f"{msg('hu', 'record_page.records_title')} · {problem['title']['hu']}",
        }
        write(
            index_route,
            page(index_title, render_record_index(item, index_route), route=index_route),
        )
        generated_routes.append(index_route)

        for record_type in PUBLIC_PAGE_TYPES:
            for record in item["records_by_type"].get(record_type, []):
                route = record_route(topic, record_type, record["id"])
                digest = content_hash(record)
                write(
                    route,
                    page(
                        record_title(record),
                        render_record_page(item, record, route),
                        route=route,
                        description=record_description(record),
                        record_meta={
                            "id": record["id"],
                            "type": record_type,
                            "topic": topic,
                            "content_hash": digest,
                        },
                    ),
                )
                generated_routes.append(route)
                record_page_count += 1

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"  <url><loc>{esc(canonical_url(SITE_URL, route))}</loc></url>\n"
        for route in sorted(generated_routes)
    ) + "</urlset>\n"
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {canonical_url(SITE_URL, 'sitemap.xml')}\n",
        encoding="utf-8",
    )
    print(
        f"Built the Atlas homepage, {len(PUBLIC_TOPICS)} dossiers, "
        f"{len(PUBLIC_TOPICS)} record indexes, and {record_page_count} canonical record pages in {OUT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
