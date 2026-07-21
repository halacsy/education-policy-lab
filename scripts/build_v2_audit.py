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
ASSET_VERSION = "d58-bilingual"
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.jsonio import content_hash  # noqa: E402
from policy_lab.i18n import is_localized_text, load_field_map, text  # noqa: E402
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
    "problem_brief": ("Problem brief", "Problémafelvetés", "The exact human-admitted question and scope compiled into the run.", "A futásba fordított, ember által jóváhagyott pontos kérdés és hatókör."),
    "policy_question": ("Raw policy question", "Nyers szakpolitikai kérdés", "The admitted question before its scope and premises are normalized.", "A befogadott kérdés, mielőtt a hatókörét és előfeltevéseit pontosítanánk."),
    "problem_brief_proposal": ("Problem-brief proposal", "Problémafelvetés-javaslat", "A bounded research contract awaiting human review.", "Körülhatárolt kutatási szerződés, amely emberi felülvizsgálatra vár."),
    "problem_brief_decision": ("Problem-brief decision", "Problémafelvetés-döntés", "A human decision bound to one exact problem-brief candidate hash.", "Egy pontos problémafelvetés-jelölthashhez kötött emberi döntés."),
    "option_space_proposal": ("Option-space proposal", "Opciótér-javaslat", "Directions derived from fresh research before human approval.", "Friss kutatásból, emberi jóváhagyás előtt levezetett irányok."),
    "human_gate_decision": ("Human gate decision", "Emberi kapudöntés", "A decision bound to one exact candidate hash.", "Egy pontos jelölthashhez kötött emberi döntés."),
    "approved_option_space": ("Approved option space", "Jóváhagyott opciótér", "The immutable option-space candidate admitted by the human gate.", "Az emberi kapun változtatás nélkül befogadott opciótér-jelölt."),
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
    "derive_option_space": ("Derive option space", "Opciótér levezetése"),
    "approve_option_space": ("Approve option space", "Opciótér jóváhagyása"),
    "draft_problem_brief": ("Draft problem brief", "Problémafelvetés tervezete"),
    "approve_problem_brief": ("Approve problem brief", "Problémafelvetés jóváhagyása"),
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
    "problem_brief": ("title", "public_question"),
    "policy_question": ("question",),
    "problem_brief_proposal": ("title", "public_question"),
    "problem_brief_decision": ("decision", "rationale"),
    "option_space_proposal": ("derivation_notice",),
    "human_gate_decision": ("decision", "rationale"),
    "approved_option_space": ("candidate_ref",),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


BASE_LENSES = load_json(ROOT / "config" / "v2" / "lenses.json")["lenses"]
LENS_BY_ID = {lens["id"]: lens for lens in BASE_LENSES}
LENS_HU = load_json(ROOT / "config" / "v2" / "locales" / "hu.json")["messages"]["lens"]


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def text_pair(english: str, hungarian: str, tag: str = "span") -> str:
    return (
        f'<{tag} class="lang lang-hu" lang="hu">{esc(hungarian)}</{tag}>'
        f'<{tag} class="lang lang-en" lang="en">{esc(english)}</{tag}>'
    )


def topic_titles(topic: str) -> dict[str, str]:
    topic_data = load_json(ROOT / "topics" / topic / "topic.json")
    if "problem_brief" in topic_data:
        raw = topic_data["problem_brief"]["title"]
    else:
        raw = topic_data["raw_question"]["question"]
    if isinstance(raw, dict):
        return {"en": str(raw.get("en", topic)), "hu": str(raw.get("hu", raw.get("en", topic)))}
    return {"en": str(raw), "hu": str(raw)}


def discover_runs() -> list[RunSource]:
    runs: list[RunSource] = []
    production_root = ROOT / "v2" / "production"
    for manifest_path in sorted(production_root.glob("*/*/production_manifest.json")):
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
    latest: dict[str, str] = {}
    for record_type, version in registry.available():
        latest[record_type] = max(latest.get(record_type, version), version)
    bilingual_paths = load_field_map(ROOT)
    for record_type, version in sorted(latest.items()):
        schema = registry.schema_for(record_type, version)
        content = schema_content(schema)
        copy = TYPE_COPY.get(record_type, (record_type, record_type, "", ""))
        required = set(content.get("required", []))
        localized = bilingual_paths.get(record_type, ())
        fields = []
        for name, prop in content.get("properties", {}).items():
            shape = property_shape(prop)
            if name in localized:
                shape = "localized_text{en,hu}"
            elif f"{name}.*" in localized and prop.get("type") == "array":
                shape = "localized_text{en,hu}[]"
            fields.append({
                "name": name, "shape": shape, "required": name in required,
            })
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
            "localized_paths": list(localized),
        })
    return {"nodes": types, "edges": sorted(edges.values(), key=lambda item: (item["from"], item["to"]))}


def record_preview(record: dict[str, Any]) -> dict[str, str]:
    content = record.get("content", {})
    for name in PREVIEW_FIELDS.get(record["record_type"], ()):
        value = content.get(name)
        if is_localized_text(value):
            return {
                "en": text(value, "en").strip()[:360],
                "hu": text(value, "hu").strip()[:360],
            }
        if isinstance(value, str) and value.strip():
            preview = value.strip()[:360]
            return {"en": preview, "hu": preview}
    for value in content.values():
        if is_localized_text(value):
            return {
                "en": text(value, "en").strip()[:360],
                "hu": text(value, "hu").strip()[:360],
            }
        if isinstance(value, str) and value.strip() and not value.startswith(("F-", "TP-", "AS-", "PV-")):
            preview = value.strip()[:360]
            return {"en": preview, "hu": preview}
    return {"en": record["id"], "hu": record["id"]}


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


def bilingual(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        english = str(value.get("en", value.get("hu", "")))
        return {"en": english, "hu": str(value.get("hu", english))}
    return {"en": str(value), "hu": str(value)}


def agent_profile(
    node_id: str,
    calls: list[dict[str, Any]],
    exact_lenses: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    lens_id = ""
    if node_id.startswith("research_"):
        lens_id = node_id.removeprefix("research_")
    elif node_id.startswith("assess_"):
        lens_id = node_id.removeprefix("assess_")
    lens = (exact_lenses or {}).get(lens_id) or LENS_BY_ID.get(lens_id)
    if lens:
        return {
            "id": lens_id,
            "name": {"en": lens["name"], "hu": LENS_HU.get(lens_id, lens["name"])},
            "discipline": lens["discipline"],
            "questions": lens["questions"],
            "criteria": lens["criteria"],
            "limitations": lens["limitations"],
            "definition_source": (
                "RunPlan root artifact" if lens_id in (exact_lenses or {})
                else "config/v2/lenses.json"
            ),
        }
    call = calls[-1] if calls else {}
    agent_id = call.get("agent") or node_id
    return {
        "id": agent_id,
        "name": {"en": agent_id.replace("_", " "), "hu": agent_id.replace("_", " ")},
        "discipline": call.get("task", "deterministic workflow"),
        "questions": [],
        "criteria": [],
        "limitations": [],
        "definition_source": "recorded prompt" if calls else "deterministic node contract",
    }


def prompt_files(run_dir: Path, node_id: str) -> list[dict[str, str]]:
    paths = sorted((run_dir / "prompts").glob(f"{node_id}.*.md"))
    base_paths = [path for path in paths if "semantic-retry" not in path.name]
    if base_paths:
        paths = base_paths
    return [
        {
            "name": path.name,
            "stage": path.name.removeprefix(f"{node_id}.").removesuffix(".md"),
            "text": path.read_text(encoding="utf-8"),
        }
        for path in paths
    ]


def build_run(source: RunSource, registry: SchemaRegistry) -> dict[str, Any]:
    repository = ArtifactRepository(source.repository_root, registry)
    topic_data = load_json(ROOT / "topics" / source.topic / "topic.json")
    production_manifest = load_json(source.repository_root / "production_manifest.json")
    plan_path = source.run_dir / "run_plan.json"
    run_plan = load_json(plan_path) if plan_path.exists() else None
    expected_plan_hash = production_manifest.get("run_plan", {}).get("content_hash")
    actual_plan_hash = content_hash(run_plan) if run_plan else None
    if run_plan and expected_plan_hash != actual_plan_hash:
        raise AssertionError(
            f"RunPlan hash mismatch for {source.run_id}: "
            f"manifest={expected_plan_hash}, actual={actual_plan_hash}"
        )
    provenance_status = "complete" if run_plan else "incomplete_provenance"
    plan_node_by_id = {
        node["id"]: node for node in (run_plan or {}).get("nodes", [])
    }
    plan_sequence = {
        node["id"]: index for index, node in enumerate((run_plan or {}).get("nodes", []), 1)
    }
    manifest_paths = sorted((source.run_dir / "nodes").glob("*.json"))
    manifests = [load_json(path) for path in manifest_paths]
    events_path = source.run_dir / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    calls_path = source.repository_root / "backend_calls.jsonl"
    backend_calls = [
        json.loads(line)
        for line in calls_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if calls_path.exists() else []
    calls_by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for call in backend_calls:
        if call.get("arm") == "production" and call.get("node_id"):
            calls_by_node[call["node_id"]].append(call)

    artifact_hashes: set[str] = set()
    producer_by_hash: dict[str, str] = {}
    for root_name, refs in (run_plan or {}).get("roots", {}).items():
        for ref in refs:
            artifact_hashes.add(ref["content_hash"])
            producer_by_hash[ref["content_hash"]] = f"root:{root_name}"
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

    record_by_hash = {digest: record for digest, record in stored}
    record_by_id = {record["id"]: (digest, record) for digest, record in stored}
    exact_lenses = {}
    for digest, record in stored:
        if record["record_type"] != "lens_definition" or not producer_by_hash.get(
            digest, ""
        ).startswith("root:lens_"):
            continue
        current_lens = repository.get_current(record["id"])
        exact_lenses[record["id"].removeprefix("L-live-")] = current_lens["content"]

    def summarize_record(digest: str, record: dict[str, Any]) -> dict[str, Any]:
        refs = []
        for ref in registry.references(record):
            target = record_by_id.get(ref.target_id)
            refs.append({
                "id": ref.target_id,
                "type": ref.target_type,
                "field": ref.field,
                "producer": producer_by_hash.get(target[0]) if target else None,
            })
        summary = {
            "id": record["id"],
            "hash": digest,
            "type": record["record_type"],
            "status": record["status"],
            "preview": record_preview(record),
            "producer": producer_by_hash.get(digest),
            "provenance_ref": record.get("provenance_ref"),
            "references": refs,
        }
        if record["record_type"] == "transformation_proposal":
            content = record["content"]
            summary["proposal"] = {
                "title": content["title"],
                "goal": content["goal"],
                "change_level": content["change_level"],
                "evidence_status": content["evidence_status"],
                "finding_refs": content["finding_refs"],
                "assumption_refs": content["assumption_refs"],
                "uncertainty_refs": content["uncertainty_refs"],
                "mechanisms": content["mechanisms"],
                "implementation_steps": content["implementation_steps"],
            }
        return summary

    # Execution inspection stays bound to the immutable RunPlan hashes above.
    # The database view separately shows the current semantic successors,
    # including D-58 bilingual retrofit records and their migration provenance.
    current_stored = [
        (content_hash(record), record)
        for record in repository.list(topic=source.topic)
    ]
    type_records: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for digest, record in current_stored:
        type_records[record["record_type"]].append((digest, record))

    database_nodes = []
    for schema_type in sorted({record_type for record_type, _ in registry.available()}):
        rows = type_records.get(schema_type, [])
        example = None
        if rows:
            digest, record = sorted(rows, key=lambda pair: pair[1]["id"])[0]
            refs = registry.references(record)
            incoming = 0
            for _, candidate in current_stored:
                incoming += sum(1 for ref in registry.references(candidate) if ref.target_id == record["id"])
            example = {
                "id": record["id"], "hash": digest, "status": record["status"],
                "preview": record_preview(record), "outgoing": len(refs), "incoming": incoming,
                "created_at": record["created_at"], "provenance_ref": record.get("provenance_ref"),
                "schema_version": record["schema_version"],
            }
        database_nodes.append({"id": schema_type, "count": len(rows), "example": example})

    database_edges: dict[tuple[str, str], int] = Counter()
    known_ids = {record["id"] for _, record in current_stored}
    for _, record in current_stored:
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
        declared = plan_node_by_id.get(node_id, {})
        node_calls = calls_by_node.get(node_id, [])
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
        node_inputs = {
            group: [digest for digest in values if digest in record_by_hash]
            for group, values in manifest.get("input_artifacts", {}).items()
        }
        node_outputs = [
            output["content_hash"] for output in manifest.get("output_artifacts", [])
            if output["content_hash"] in record_by_hash
        ]
        provenance = next((
            record for record in provenance_by_id.values()
            if record["content"].get("node_id") == node_id
            and record["content"].get("execution_id") == manifest.get("cache_key")
        ), None)
        run_nodes.append({
            "id": node_id,
            "title": bilingual(declared.get("title")) if declared else node_title(node_id),
            "description": declared.get("description", ""),
            "stage": declared.get("stage", "legacy"),
            "disposition": manifest.get("disposition", "unknown"),
            "start": start, "finish": finish, "duration_seconds": duration,
            "sequence": plan_sequence.get(
                node_id, min((event["sequence"] for event in node_events), default=9999)
            ),
            "input_count": sum(len(values) for values in manifest.get("input_artifacts", {}).values()),
            "output_count": len(manifest.get("output_artifacts", [])), "output_types": dict(sorted(output_counts.items())),
            "cache_hits": len(cache_hits), "failures": len(failures), "cache_key": manifest.get("cache_key", ""),
            "kind": declared.get("kind", "llm" if node_calls else "deterministic"),
            "agent": agent_profile(node_id, node_calls, exact_lenses),
            "calls": [{
                key: call[key] for key in (
                    "agent", "task", "provider", "backend", "model", "role", "input_tokens",
                    "output_tokens", "ms", "web_searches", "recorded_at",
                ) if key in call
            } for call in node_calls],
            "prompts": prompt_files(source.run_dir, node_id),
            "inputs": node_inputs,
            "outputs": node_outputs,
            "contract": provenance["content"] if provenance else {},
        })

    if run_plan:
        root_nodes = []
        for index, (root_name, refs) in enumerate(run_plan["roots"].items()):
            output_counts = Counter(ref["record_type"] for ref in refs)
            root_nodes.append({
                "id": f"root:{root_name}",
                "title": bilingual(root_name.replace("_", " ")),
                "description": "Exact admitted root artifact compiled into the RunPlan.",
                "stage": "root",
                "disposition": "admitted",
                "start": None, "finish": None, "duration_seconds": None,
                "sequence": -1000 + index,
                "input_count": 0, "output_count": len(refs),
                "output_types": dict(sorted(output_counts.items())),
                "cache_hits": 0, "failures": 0, "cache_key": "",
                "kind": "root",
                "agent": {
                    "id": "human_admission", "name": bilingual("human admission"),
                    "discipline": "declared external run input", "questions": [],
                    "criteria": [], "limitations": [],
                    "definition_source": "run_plan.json",
                },
                "calls": [], "prompts": [], "inputs": {},
                "outputs": [ref["content_hash"] for ref in refs],
                "contract": {"run_plan_hash": actual_plan_hash},
            })
        run_nodes = [*root_nodes, *run_nodes]

    run_edges: dict[tuple[str, str], int] = Counter()
    if run_plan:
        for edge in run_plan["edges"]:
            run_edges[(edge["from"], edge["to"])] += 1
    else:
        for manifest in manifests:
            for values in manifest.get("input_artifacts", {}).values():
                for digest in values:
                    producer = producer_by_hash.get(digest)
                    if producer and producer != manifest["node_id"]:
                        run_edges[(producer, manifest["node_id"])] += 1

    problem_records = [record for _, record in stored if record["record_type"] == "problem_brief"]
    option_records = [record for _, record in stored if record["record_type"] == "approved_option_space"]
    if problem_records:
        brief = problem_records[0]["content"]
    else:
        brief = topic_data["problem_brief"]
    if option_records:
        frames = option_records[0]["content"]["directions"]
        direction_source = "approved_option_space"
    else:
        frames = topic_data.get("frames", {}).get("scenarios", [])
        direction_source = "legacy_topic_snapshot"
    execution_records = [
        summarize_record(digest, record)
        for digest, record in stored
        if record["record_type"] != "provenance"
    ]

    return {
        "id": source.run_id, "topic": source.topic, "kind": source.kind,
        "label": {"en": source.label_en, "hu": source.label_hu},
        "notice": {
            "en": source.notice_en + (
                " This historical run has no persisted RunPlan; displayed execution "
                "edges are reconstructed and its provenance is incomplete."
                if provenance_status == "incomplete_provenance" else
                " The displayed graph is read from the exact persisted RunPlan."
            ),
            "hu": source.notice_hu + (
                " Ehhez a korábbi futáshoz nem maradt perzisztált RunPlan; a bemutatott "
                "futási élek rekonstruáltak, ezért az eredetleírás hiányos."
                if provenance_status == "incomplete_provenance" else
                " A megjelenített gráf forrása a pontosan eltárolt RunPlan."
            ),
        },
        "provenance_status": provenance_status,
        "run_plan_hash": actual_plan_hash,
        "database": {
            "nodes": database_nodes,
            "edges": [{"from": key[0], "to": key[1], "count": count} for key, count in sorted(database_edges.items())],
            "artifact_count": len(stored),
        },
        "execution": {
            "nodes": sorted(run_nodes, key=lambda node: (node["sequence"], node["id"])),
            "edges": [{"from": key[0], "to": key[1], "count": count} for key, count in sorted(run_edges.items())],
            "event_count": len(events),
            "context": {
                "title": bilingual(brief["title"]),
                "public_question": bilingual(brief["public_question"]),
                "problem_statement": bilingual(brief["problem_statement"]),
                "scope": bilingual(brief["scope"]),
                "frames": [{
                    "id": frame["id"],
                    "title": bilingual(frame["title"]),
                    "scope": bilingual(frame["scope"]),
                } for frame in frames],
                "direction_source": direction_source,
            },
            "records": sorted(execution_records, key=lambda record: (record["type"], record["id"])),
            "proposals": sorted(
                record["hash"] for record in execution_records
                if record["type"] == "transformation_proposal"
                and record["producer"] == "derive_transformations"
            ),
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
