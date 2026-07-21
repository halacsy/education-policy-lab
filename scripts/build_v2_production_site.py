#!/usr/bin/env python3
"""Render fresh production v2 runs from canonical artifacts and localized bundles."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from policy_lab.jsonio import content_hash  # noqa: E402
from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402

RUN_TAG = "2026-07-20-live"
RUN_ROOT = ROOT / "v2" / "production" / RUN_TAG
OUT = ROOT / "site" / "v2" / "production"
TOPICS = ("korai-szelekcio", "rural-school-closures")
V1_ROUNDS = {"korai-szelekcio": "round_09", "rural-school-closures": "round_02"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


CATALOGS = {lang: load(ROOT / "config" / "v2" / "locales" / f"{lang}.json") for lang in ("en", "hu")}


def msg(lang: str, key: str) -> str:
    value: Any = CATALOGS[lang]["messages"]
    for part in key.split("."):
        value = value[part]
    return str(value)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def bi(en: Any, hu: Any, tag: str = "span") -> str:
    localized = str(hu)
    for replacement in CATALOGS["hu"]["content_replacements"]:
        localized = re.sub(replacement["pattern"], replacement["replacement"], localized)
    return f'<{tag} class="lang lang-hu" lang="hu">{esc(localized)}</{tag}><{tag} class="lang lang-en" lang="en">{esc(en)}</{tag}>'


def ui(key: str, tag: str = "span") -> str:
    return bi(msg("en", key), msg("hu", key), tag)


def page(title: dict[str, str], body: str, depth: int = 0) -> str:
    prefix = "../" * depth
    return f'''<!doctype html><html lang="hu" data-language="hu" data-title-en="{esc(title['en'])} · Transformation Observatory" data-title-hu="{esc(title['hu'])} · Transformation Observatory"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title['hu'])} · Transformation Observatory</title><link rel="stylesheet" href="{prefix}assets/v2.css"></head><body>
<a class="skip" href="#content">{ui('nav.skip')}</a><header class="masthead"><a class="brand" href="{prefix}index.html"><span class="brand-mark">↳</span><span><b>TRANSFORMATION</b><em>OBSERVATORY · EPL v2</em></span></a><nav><a href="index.html">{ui('nav.portfolio')}</a><a href="comparison.html">V1 ↔ V2</a><a href="../audit.html">{ui('common.audit_log')}</a></nav><div class="language-switch"><button type="button" data-set-language="hu" aria-pressed="true">HU</button><button type="button" data-set-language="en" aria-pressed="false">EN</button></div></header><main id="content">{body}</main><footer><span>{ui('footer.architecture')}</span><span>v2.0.0 · {RUN_TAG}</span></footer><script src="{prefix}assets/v2.js"></script></body></html>'''


def dataset(topic: str, schemas: SchemaRegistry) -> dict[str, Any]:
    root = RUN_ROOT / topic
    repo = ArtifactRepository(root, schemas)
    manifest = load(root / "production_manifest.json")
    summary = manifest["summary"]
    package = repo.get_current(summary["package_ref"])
    bundle = load(root / "localization" / "hu.json")
    if bundle["source_package_hash"] != content_hash(package):
        raise ValueError(f"Stale localization bundle: {topic}")
    tr = bundle["translations"]
    return {
        "topic": load(ROOT / "topics" / topic / "topic.json"), "repo": repo,
        "summary": summary, "package": package, "evaluation": repo.get_current(summary["evaluation_ref"]),
        "readiness": repo.get_current(summary["readiness_ref"]), "tr": tr,
    }


def tx(data: dict[str, Any], key: str, english: str) -> str:
    try:
        return bi(english, data["tr"][key])
    except KeyError as error:
        raise KeyError(f"Missing public localization: {key}") from error


def list_bi(data: dict[str, Any], record: dict[str, Any], field: str) -> str:
    return "".join(f"<li>{tx(data, f'{record['id']}.{field}.{i}', text)}</li>" for i, text in enumerate(record["content"].get(field, [])))


def render_topic(data: dict[str, Any]) -> str:
    topic = data["topic"]; problem = topic["problem_brief"]; package = data["package"]; repo = data["repo"]
    summary = data["summary"]; proposals = [repo.get_current(ref) for ref in package["content"]["proposal_refs"]]
    dilemmas = [repo.get_current(ref) for ref in package["content"]["dilemma_refs"]]
    questions = [repo.get_current(ref) for ref in package["content"]["research_question_refs"]]
    coverage = repo.get_current(package["content"]["coverage_ledger_refs"][0])
    cards = []
    for proposal in proposals:
        c = proposal["content"]; pid = proposal["id"]
        steps = "".join(f"<li><time>{tx(data,f'{pid}.implementation_steps.{i}.timeline',s['timeline'])}</time><b>{tx(data,f'{pid}.implementation_steps.{i}.actor',s['actor'])}</b><p>{tx(data,f'{pid}.implementation_steps.{i}.action',s['action'])}</p></li>" for i,s in enumerate(c["implementation_steps"]))
        cards.append(f'''<article class="proposal-sheet"><header><div class="proposal-code">{esc(pid.split('-')[-1].upper())}</div><div><h2>{tx(data,pid+'.title',c['title'])}</h2><p class="proposal-goal">{tx(data,pid+'.goal',c['goal'])}</p></div><span class="evidence evidence-{esc(c['evidence_status'])}">{bi(c['evidence_status'],msg('hu','enum.evidence.'+c['evidence_status']))}</span></header><div class="proposal-grid"><section><h3>{ui('production.mechanisms')}</h3><ol class="mechanisms">{list_bi(data,proposal,'mechanisms')}</ol></section><section><h3>{ui('production.implementation')}</h3><ol class="timeline">{steps}</ol></section></div><div class="proposal-grid"><section><h3>{ui('production.benefits')}</h3><ul>{list_bi(data,proposal,'expected_benefits')}</ul><h3>{ui('production.equity')}</h3><p>{tx(data,pid+'.equity_impact',c['equity_impact'])}</p></section><section><h3>{ui('production.costs')}</h3><ul>{list_bi(data,proposal,'costs')}</ul><h3>{ui('production.risks')}</h3><ul>{list_bi(data,proposal,'risks')}</ul></section></div></article>''')
    frame_hu = {frame["id"]: frame["title"]["hu"] for frame in topic["frames"]["scenarios"]}
    cov = "".join(f"<li><b>{e['direction_id']}</b> {bi(e['direction_title'],frame_hu[e['direction_id']])} → {esc(', '.join(e['proposal_refs']))}</li>" for e in coverage["content"]["entries"])
    ds = "".join(f'''<article class="dilemma"><span>{bi(d['content']['dilemma_type'],msg('hu','enum.dilemma_type.'+d['content']['dilemma_type']))}</span><h4>{tx(data,d['id']+'.title',d['content']['title'])}</h4><p>{tx(data,d['id']+'.tension',d['content']['tension'])}</p><small>{tx(data,d['id']+'.evidence_boundary',d['content']['evidence_boundary'])}</small></article>''' for d in dilemmas)
    qs = "".join(f"<li><b>{tx(data,q['id']+'.question',q['content']['question'])}</b><p>{tx(data,q['id']+'.why_it_matters',q['content']['why_it_matters'])}</p></li>" for q in questions)
    def source_links(entry: dict[str, Any]) -> str:
        return " · ".join(
            f'<a href="{esc(source["url"])}">{bi(source["title"], msg("hu", "production.sources") + " " + str(index))}</a>'
            if source["url"].startswith("http")
            else bi(source["title"], msg("hu", "production.sources") + " " + str(index))
            for index, source in enumerate(entry["sources"], 1)
        )
    appendix = "".join(f"<li><b>{esc(e['finding_ref'])}</b> {tx(data,e['finding_ref']+'.claim',e['claim'])}<div>{source_links(e)}</div></li>" for e in package["content"]["evidence_appendix"])
    concerns = list_bi(data,data["evaluation"],"concerns")
    return f'''<section class="topic-hero blueprint-grid"><div><p class="eyebrow">{ui('production.eyebrow')}</p><h1>{bi(problem['title']['en'],problem['title']['hu'])}</h1><p class="hero-deck">{bi(problem['public_question']['en'],problem['public_question']['hu'])}</p></div><div class="topic-stats"><span><b>{summary['evaluation']['total']:.3f}</b>{ui('production.score')}</span><span><b>{summary['counts']['finding']}</b>{ui('production.fresh_findings')}</span><span><b>{summary['counts']['lens_assessment']}</b>{ui('production.assessments')}</span></div></section><aside class="migration-note"><b>{ui('production.readiness')}</b>{ui('production.ready_with_conditions')} · {ui('production.external_gate')}</aside><section class="comparison-section"><h2>{ui('production.summary')}</h2><p class="result-lead">{tx(data,package['id']+'.summary',package['content']['summary'])}</p></section><section class="comparison-section"><h2>{ui('production.coverage')}</h2><ul>{cov}</ul></section><section class="proposal-stack"><h2>{ui('production.proposals')}</h2>{''.join(cards)}</section><section class="comparison-section decisions"><h2>{ui('production.dilemmas')}</h2>{ds}</section><section class="comparison-section"><h2>{ui('production.research')}</h2><ol class="research-list">{qs}</ol></section><section class="comparison-section"><h2>{ui('production.conditions')}</h2><ul>{concerns}</ul></section><section class="comparison-section"><details><summary><h2>{ui('production.evidence')} · {len(package['content']['evidence_appendix'])}</h2></summary><ol class="research-list">{appendix}</ol></details></section>'''


def main() -> int:
    schemas = SchemaRegistry(ROOT / "schemas" / "v2"); OUT.mkdir(parents=True, exist_ok=True)
    data = {topic: dataset(topic, schemas) for topic in TOPICS}
    cards = "".join(f'''<article class="topic-sheet"><p class="eyebrow">{esc(topic)}</p><h2>{bi(d['topic']['problem_brief']['title']['en'],d['topic']['problem_brief']['title']['hu'])}</h2><div class="mini-metrics"><span>{d['summary']['evaluation']['total']:.3f}<small>{ui('production.score')}</small></span><span>{d['summary']['counts']['finding']}<small>{ui('production.fresh_findings')}</small></span></div><a class="arrow-link" href="{topic}.html">{ui('production.open')} →</a></article>''' for topic,d in data.items())
    index = f'''<section class="hero blueprint-grid"><div class="hero-copy"><p class="eyebrow">{ui('production.eyebrow')}</p><h1>{ui('production.title')}</h1><p class="hero-deck">{ui('production.deck')}</p></div></section><section class="portfolio"><div class="topic-grid">{cards}</div><p><a class="primary-action" href="comparison.html">{ui('production.comparison')} →</a></p></section>'''
    (OUT / "index.html").write_text(page({"en":msg("en","production.title"),"hu":msg("hu","production.title")},index,1),encoding="utf-8")
    for topic,d in data.items():
        title=d['topic']['problem_brief']['title']; (OUT/f"{topic}.html").write_text(page(title,render_topic(d),1),encoding="utf-8")
    rows=[]
    for topic,d in data.items():
        v1=load(ROOT/"outputs"/"topics"/topic/"iterations"/V1_ROUNDS[topic]/"evaluation.json")
        rows.append(f"<tr><th>{bi(d['topic']['problem_brief']['title']['en'],d['topic']['problem_brief']['title']['hu'])}</th><td>{v1['total']:.3f}</td><td>{d['summary']['evaluation']['total']:.3f}</td><td>{d['summary']['counts']['finding']}</td><td>{ui('production.coverage_pass')}</td></tr>")
    comp=f'''<section class="comparison-hero blueprint-grid"><div><p class="eyebrow">V1 ↔ V2</p><h1>{ui('production.comparison')}</h1><p class="hero-deck">{ui('production.not_comparable')}</p></div></section><section class="comparison-section"><table class="comparison-table"><thead><tr><th>{ui('nav.portfolio')}</th><th>{ui('production.v1_score')}</th><th>{ui('production.v2_score')}</th><th>{ui('production.fresh_findings')}</th><th>{ui('production.coverage')}</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>'''
    (OUT/"comparison.html").write_text(page({"en":msg('en','production.comparison'),"hu":msg('hu','production.comparison')},comp,1),encoding="utf-8")
    print(f"Built {len(TOPICS)+2} production pages in {OUT}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
