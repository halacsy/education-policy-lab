#!/usr/bin/env python3
"""Build the public artifact-lineage explorer from accepted v2 production runs."""

from __future__ import annotations

import html
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSET_VERSION = "d55"
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.jsonio import content_hash  # noqa: E402
from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402

SCHEMA_ROOT = ROOT / "schemas" / "v2"
OUT = ROOT / "site"


@dataclass(frozen=True)
class RunSource:
    run_id: str
    topic: str
    kind: str
    label_en: str
    label_hu: str
    notice_en: str
    notice_hu: str
    repository_root: Path
    run_dir: Path


TYPE_COPY = {
    "source": ("Source", "Forrás", "A research source or captured source record.", "A kutatásban használt vagy rögzített forrás."),
    "finding": ("Finding", "Megállapítás", "An atomic, sourced statement with context and limits.", "Forrással, kontextussal és korlátokkal ellátott elemi állítás."),
    "assumption": ("Assumption", "Feltételezés", "A condition accepted temporarily rather than established as fact.", "Nem tényként igazolt, hanem ideiglenesen elfogadott feltétel."),
    "uncertainty": ("Uncertainty", "Bizonytalanság", "A material unknown attached to evidence or a proposal.", "Bizonyítékhoz vagy javaslathoz kapcsolódó lényeges ismerethiány."),
    "transformation_family": ("Transformation family", "Változtatási irány", "A family of proposals sharing a change lever and target state.", "Közös beavatkozási eszközt és célállapotot használó javaslatcsalád."),
    "transformation_proposal": ("Transformation proposal", "Átalakítási javaslat", "A context-specific theory of change and implementation path.", "Konkrét helyzetre szabott változtatási mechanizmus és megvalósítási út."),
    "lens_definition": ("Scientific perspective", "Szakmai nézőpont", "A reusable methodological contract for assessing proposals.", "Javaslatok értékelésére használható, újrahasznosítható módszertani szerződés."),
    "lens_assessment": ("Professional assessment", "Szakmai értékelés", "One proposal examined through one scientific or professional perspective.", "Egy javaslat vizsgálata egy tudományos vagy szakmai nézőpontból."),
    "dilemma": ("Dilemma", "Dilemma", "A decision conflict that evidence cannot settle on its own.", "Olyan döntési konfliktus, amelyet a bizonyíték önmagában nem tud lezárni."),
    "research_question": ("Research question", "Kutatási kérdés", "A question whose answer could materially change the decision.", "Olyan kérdés, amelynek válasza érdemben módosíthatja a döntést."),
    "coverage_ledger": ("Coverage ledger", "Lefedettségi jegyzék", "The disposition of every required input record.", "Minden kötelező bemeneti rekord továbbvitelének vagy elutasításának nyilvántartása."),
    "decision_package": ("Decision package", "Döntési csomag", "The auditable root that assembles the decision space.", "A döntési teret összeállító, ellenőrizhető gyökérartefaktum."),
    "evaluation": ("Evaluation", "Értékelés", "A cross-family assessment of the completed decision package.", "A kész döntési csomag eltérő modellcsaládú értékelése."),
    "decision_readiness": ("Decision readiness", "Döntési készültség", "A structured verdict on what can be decided and what still blocks action.", "Strukturált ítélet arról, mi dönthető el, és mi akadályozza még a cselekvést."),
    "provenance": ("Provenance", "Eredetnapló", "The node, inputs, prompt, provider, model, and contracts behind a record.", "A rekord mögötti lépés, bemenetek, prompt, szolgáltató, modell és szerződések."),
}

NODE_COPY = {
    "import_v1_evidence": ("Import committed evidence", "Rögzített bizonyíték átemelése"),
    "compile_transformations": ("Compile transformations", "Átalakítások összeállítása"),
    "apply_scientific_lenses": ("Apply scientific perspectives", "Szakmai nézőpontok alkalmazása"),
    "identify_decision_dilemmas": ("Identify decision dilemmas", "Döntési dilemmák azonosítása"),
    "build_research_agenda": ("Build research agenda", "Kutatási agenda összeállítása"),
    "assemble_decision_package": ("Assemble decision package", "Döntési csomag összeállítása"),
    "derive_transformations": ("Derive transformations", "Átalakítások levezetése"),
    "register_baseline_lenses": ("Register baseline perspectives", "Alapnézőpontok regisztrálása"),
    "register_educational_psychology_lens": ("Register psychology perspective", "Neveléslélektani nézőpont regisztrálása"),
    "evaluate_decision_package": ("Evaluate decision package", "Döntési csomag értékelése"),
    "assess_decision_readiness": ("Assess decision readiness", "Döntési készültség vizsgálata"),
}

PREVIEW_FIELDS = {
    "source": ("title", "url", "citation"),
    "finding": ("claim",),
    "assumption": ("statement", "assumption"),
    "uncertainty": ("question", "uncertainty"),
    "transformation_family": ("title", "name", "description"),
    "transformation_proposal": ("title", "goal"),
    "lens_definition": ("title", "name", "scope"),
    "lens_assessment": ("assessment",),
    "dilemma": ("title", "tension"),
    "research_question": ("question",),
    "coverage_ledger": ("scope", "summary"),
    "decision_package": ("title", "summary"),
    "evaluation": ("summary", "verdict"),
    "decision_readiness": ("verdict", "rationale"),
    "provenance": ("node_id", "model"),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


LENS_HU = load_json(ROOT / "config" / "v2" / "locales" / "hu.json")["messages"]["lens"]


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def text_pair(english: str, hungarian: str, tag: str = "span") -> str:
    return (
        f'<{tag} class="lang lang-hu" lang="hu">{esc(hungarian)}</{tag}>'
        f'<{tag} class="lang lang-en" lang="en">{esc(english)}</{tag}>'
    )


def topic_titles(topic: str) -> dict[str, str]:
    brief = load_json(ROOT / "topics" / topic / "topic.json")["problem_brief"]
    raw = brief["title"]
    if isinstance(raw, dict):
        return {"en": str(raw.get("en", topic)), "hu": str(raw.get("hu", raw.get("en", topic)))}
    return {"en": str(raw), "hu": str(raw)}


def discover_runs() -> list[RunSource]:
    runs: list[RunSource] = []
    production_root = ROOT / "v2" / "production" / "2026-07-20-live"
    for manifest_path in sorted(production_root.glob("*/production_manifest.json")):
        manifest = load_json(manifest_path)
        topic = manifest["topic"]
        topic_root = manifest_path.parent
        runs.append(RunSource(
            run_id=manifest["run_id"], topic=topic, kind="production",
            label_en="Current sourced analysis", label_hu="Jelenlegi forrásolt elemzés",
            notice_en="Fresh sourced analysis. External policy use still requires human approval.",
            notice_hu="Friss, forrásolt elemzés. Külső szakpolitikai használatához továbbra is emberi jóváhagyás szükséges.",
            repository_root=topic_root,
            run_dir=topic_root / "runs" / manifest["run_id"],
        ))
    return runs


def schema_content(schema: dict[str, Any]) -> dict[str, Any]:
    for part in schema.get("allOf", []):
        content = part.get("properties", {}).get("content")
        if content:
            return content
    return {}


def property_shape(prop: dict[str, Any]) -> str:
    if "enum" in prop:
        return "enum"
    if prop.get("type") == "array":
        item = prop.get("items", {})
        if "pattern" in item:
            return "reference[]"
        return f"{item.get('type', 'value')}[]"
    if "oneOf" in prop:
        return " | ".join(option.get("type", "value") for option in prop["oneOf"])
    return str(prop.get("type", "value"))


def schema_catalog(registry: SchemaRegistry) -> dict[str, Any]:
    types = []
    edges: dict[tuple[str, str], dict[str, Any]] = {}
    for record_type, version in registry.available():
        schema = registry.schema_for(record_type, version)
        content = schema_content(schema)
        copy = TYPE_COPY.get(record_type, (record_type, record_type, "", ""))
        required = set(content.get("required", []))
        fields = [
            {"name": name, "shape": property_shape(prop), "required": name in required}
            for name, prop in content.get("properties", {}).items()
        ]
        id_pattern = ""
        for part in schema.get("allOf", []):
            id_pattern = part.get("properties", {}).get("id", {}).get("pattern", id_pattern)
        refs = []
        for ref in schema.get("x-artifact-references", []):
            refs.append({"target": ref["record_type"], "path": ref["path"], "many": "*" in ref["path"]})
            if ref["record_type"] != "provenance":
                key = (ref["record_type"], record_type)
                edge = edges.setdefault(key, {"from": key[0], "to": key[1], "paths": []})
                edge["paths"].append(ref["path"])
        types.append({
            "id": record_type, "version": version, "title": {"en": copy[0], "hu": copy[1]},
            "description": {"en": copy[2], "hu": copy[3]}, "schema_title": schema.get("title", record_type),
            "id_pattern": id_pattern, "fields": fields, "references": refs,
        })
    return {"nodes": types, "edges": sorted(edges.values(), key=lambda item: (item["from"], item["to"]))}


def record_preview(record: dict[str, Any]) -> str:
    content = record.get("content", {})
    for name in PREVIEW_FIELDS.get(record["record_type"], ()):
        value = content.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()[:360]
    for value in content.values():
        if isinstance(value, str) and value.strip() and not value.startswith(("F-", "TP-", "AS-", "PV-")):
            return value.strip()[:360]
    return record["id"]


def node_title(node_id: str) -> dict[str, str]:
    if node_id in NODE_COPY:
        en, hu = NODE_COPY[node_id]
    elif node_id.startswith("research_"):
        suffix = node_id.removeprefix("research_").replace("_", " ")
        lens_key = node_id.removeprefix("research_")
        en, hu = f"Research · {suffix}", f"Kutatás · {LENS_HU.get(lens_key, suffix)}"
    elif node_id.startswith("assess_"):
        suffix = node_id.removeprefix("assess_").replace("_", " ")
        lens_key = node_id.removeprefix("assess_")
        en, hu = f"Assess · {suffix}", f"Vizsgálat · {LENS_HU.get(lens_key, suffix)}"
    else:
        en = node_id.replace("_", " ")
        hu = en
    return {"en": en, "hu": hu}


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_run(source: RunSource, registry: SchemaRegistry) -> dict[str, Any]:
    repository = ArtifactRepository(source.repository_root, registry)
    manifest_paths = sorted((source.run_dir / "nodes").glob("*.json"))
    manifests = [load_json(path) for path in manifest_paths]
    events_path = source.run_dir / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    artifact_hashes: set[str] = set()
    producer_by_hash: dict[str, str] = {}
    for manifest in manifests:
        for values in manifest.get("input_artifacts", {}).values():
            artifact_hashes.update(values)
        for output in manifest.get("output_artifacts", []):
            artifact_hashes.add(output["content_hash"])
            producer_by_hash[output["content_hash"]] = manifest["node_id"]

    stored: list[tuple[str, dict[str, Any]]] = []
    for digest in sorted(artifact_hashes):
        try:
            record = repository.get_by_hash(digest)
        except KeyError:
            continue
        if record["topic"] == source.topic:
            stored.append((digest, record))
    provenance_by_id = {
        record["id"]: record
        for record in repository.list(record_type="provenance", topic=source.topic)
    }
    for _, record in list(stored):
        provenance_id = record.get("provenance_ref")
        if not provenance_id:
            continue
        provenance = provenance_by_id.get(provenance_id)
        if provenance is None:
            continue
        digest = content_hash(provenance)
        if all(existing != digest for existing, _ in stored):
            stored.append((digest, provenance))

    type_records: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for digest, record in stored:
        type_records[record["record_type"]].append((digest, record))

    database_nodes = []
    for schema_type, _ in registry.available():
        rows = type_records.get(schema_type, [])
        example = None
        if rows:
            digest, record = sorted(rows, key=lambda pair: pair[1]["id"])[0]
            refs = registry.references(record)
            incoming = 0
            for _, candidate in stored:
                incoming += sum(1 for ref in registry.references(candidate) if ref.target_id == record["id"])
            example = {
                "id": record["id"], "hash": digest, "status": record["status"],
                "preview": record_preview(record), "outgoing": len(refs), "incoming": incoming,
                "created_at": record["created_at"], "provenance_ref": record.get("provenance_ref"),
            }
        database_nodes.append({"id": schema_type, "count": len(rows), "example": example})

    database_edges: dict[tuple[str, str], int] = Counter()
    known_ids = {record["id"] for _, record in stored}
    for _, record in stored:
        if record["record_type"] == "provenance":
            continue
        for ref in registry.references(record):
            if ref.target_type == "provenance" or ref.target_id not in known_ids:
                continue
            database_edges[(ref.target_type, record["record_type"])] += 1

    events_by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event.get("node_id"):
            events_by_node[event["node_id"]].append(event)

    run_nodes = []
    for manifest in manifests:
        node_id = manifest["node_id"]
        node_events = events_by_node.get(node_id, [])
        starts = [event for event in node_events if event["event_type"] == "node_started"]
        completions = [event for event in node_events if event["event_type"] == "node_completed"]
        cache_hits = [event for event in node_events if event["event_type"] == "node_cache_hit"]
        failures = [event for event in node_events if event["event_type"] == "node_failed"]
        start = starts[0]["timestamp"] if starts else None
        finish = completions[0]["timestamp"] if completions else manifest.get("completed_at")
        start_dt, finish_dt = parse_timestamp(start), parse_timestamp(finish)
        duration = (finish_dt - start_dt).total_seconds() if start_dt and finish_dt else None
        output_counts = Counter(output["record_type"] for output in manifest.get("output_artifacts", []))
        run_nodes.append({
            "id": node_id, "title": node_title(node_id), "disposition": manifest.get("disposition", "unknown"),
            "start": start, "finish": finish, "duration_seconds": duration,
            "sequence": min((event["sequence"] for event in node_events), default=9999),
            "input_count": sum(len(values) for values in manifest.get("input_artifacts", {}).values()),
            "output_count": len(manifest.get("output_artifacts", [])), "output_types": dict(sorted(output_counts.items())),
            "cache_hits": len(cache_hits), "failures": len(failures), "cache_key": manifest.get("cache_key", ""),
        })

    run_edges: dict[tuple[str, str], int] = Counter()
    for manifest in manifests:
        for values in manifest.get("input_artifacts", {}).values():
            for digest in values:
                producer = producer_by_hash.get(digest)
                if producer and producer != manifest["node_id"]:
                    run_edges[(producer, manifest["node_id"])] += 1

    return {
        "id": source.run_id, "topic": source.topic, "kind": source.kind,
        "label": {"en": source.label_en, "hu": source.label_hu},
        "notice": {"en": source.notice_en, "hu": source.notice_hu},
        "database": {
            "nodes": database_nodes,
            "edges": [{"from": key[0], "to": key[1], "count": count} for key, count in sorted(database_edges.items())],
            "artifact_count": len(stored),
        },
        "execution": {
            "nodes": sorted(run_nodes, key=lambda node: (node["sequence"], node["id"])),
            "edges": [{"from": key[0], "to": key[1], "count": count} for key, count in sorted(run_edges.items())],
            "event_count": len(events),
        },
    }


def page(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="hu" data-language="hu" data-title-en="How it was made · Education Policy Atlas" data-title-hu="Hogyan készült? · Oktatáspolitikai Atlasz">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="A v2 artefaktumok futási, adatbázis- és sématérképe." data-description-en="Execution, database, and schema maps of v2 artifacts." data-description-hu="A v2 artefaktumok futási, adatbázis- és sématérképe.">
  <title>Hogyan készült? · Oktatáspolitikai Atlasz</title>
  <link rel="stylesheet" href="v2/assets/v2.css?v={ASSET_VERSION}"><link rel="stylesheet" href="v2/assets/audit.css?v={ASSET_VERSION}">
</head>
<body>
  <a class="skip" href="#content">{text_pair('Skip to content', 'Ugrás a tartalomra')}</a>
  <header class="masthead">
    <a class="brand" href="index.html" aria-label="Oktatáspolitikai Atlasz — főoldal" data-label-en="Education Policy Atlas home" data-label-hu="Oktatáspolitikai Atlasz — főoldal">
      <span class="brand-mark" aria-hidden="true">↳</span><span><b>{text_pair('EDUCATION POLICY','OKTATÁSPOLITIKAI')}</b><em>{text_pair('ATLAS · EPL','ATLASZ · EPL')}</em></span>
    </a>
    <nav aria-label="Elsődleges navigáció" data-label-en="Primary navigation" data-label-hu="Elsődleges navigáció">
      <a href="index.html#questions">{text_pair('Questions', 'Kérdések')}</a><a href="index.html#about">{text_pair('What is this?', 'Mi ez?')}</a><a href="audit.html" aria-current="page">{text_pair('How it was made', 'Hogyan készült?')}</a>
    </nav>
    <div class="language-switch" role="group" aria-label="Nyelv" data-label-en="Language" data-label-hu="Nyelv"><button type="button" data-set-language="hu" aria-pressed="true">HU</button><button type="button" data-set-language="en" aria-pressed="false">EN</button></div>
  </header>
  <main id="content" class="audit-page">
    <section class="audit-hero blueprint-grid">
      <div><p class="eyebrow">{text_pair('LINEAGE EXPLORER', 'EREDETTÉRKÉP')}</p><h1>{text_pair('Every conclusion leaves a trail.', 'Minden következtetés nyomot hagy.')}</h1></div>
      <p class="hero-deck">{text_pair('The schema shows what may connect. The database shows what actually connects. The run shows when and how it came into being.', 'A séma megmutatja, mi kapcsolódhat. Az adatbázis megmutatja, mi kapcsolódik ténylegesen. A futás megmutatja, mikor és hogyan jött létre.')}</p>
    </section>
    <section class="audit-workbench" aria-labelledby="workbench-title">
      <h2 id="workbench-title" class="sr-only">{text_pair('Record explorer', 'Rekordböngésző')}</h2>
      <div class="audit-controls">
        <label>{text_pair('Question', 'Kérdés')}<select id="audit-topic"></select></label>
        <label>{text_pair('Run', 'Futás')}<select id="audit-run"></select></label>
        <div class="view-switch" role="group" aria-label="Nézet" data-label-en="View" data-label-hu="Nézet">
          <button type="button" data-view="execution">{text_pair('Run', 'Futás')}</button><button type="button" data-view="database">{text_pair('Database', 'Adatbázis')}</button><button type="button" data-view="schema">{text_pair('Schema', 'Séma')}</button>
        </div>
      </div>
      <aside id="audit-notice" class="audit-notice"></aside>
      <div class="audit-layout">
        <section class="graph-stage" aria-labelledby="graph-title">
          <header class="graph-heading"><div><p id="graph-kicker" class="eyebrow"></p><h2 id="graph-title"></h2></div><p id="graph-summary"></p></header>
          <div id="audit-graph" class="audit-graph"></div>
          <p id="graph-fallback" class="sr-only" aria-live="polite"></p>
        </section>
        <aside id="audit-inspector" class="audit-inspector" aria-live="polite"></aside>
      </div>
    </section>
  </main>
  <footer><span>{text_pair('Education Policy Lab · transparent, sourced analysis', 'Education Policy Lab · átlátható, forrásolt elemzés')}</span><span>{len(payload['runs'])} {text_pair('inspectable runs', 'vizsgálható futás')}</span></footer>
  <script id="audit-data" type="application/json">{encoded}</script><script src="v2/assets/v2.js?v={ASSET_VERSION}"></script><script src="v2/assets/audit.js?v={ASSET_VERSION}"></script>
</body></html>"""


def main() -> int:
    registry = SchemaRegistry(SCHEMA_ROOT)
    sources = discover_runs()
    topics = {source.topic: topic_titles(source.topic) for source in sources}
    payload = {
        "schema": schema_catalog(registry),
        "topics": [{"id": topic, "title": title} for topic, title in sorted(topics.items())],
        "runs": [build_run(source, registry) for source in sources],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / "audit.html"
    destination.write_text(page(payload), encoding="utf-8")
    print(f"Rendered {destination} from {len(payload['runs'])} runs and {len(payload['schema']['nodes'])} schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
