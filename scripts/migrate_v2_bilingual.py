#!/usr/bin/env python3
"""Retrofit current v2 semantic records to D-34 bilingual schema successors.

The original English-only artifacts and RunPlan manifests remain immutable.
Each migrated record is a schema-version 2.1.0 successor whose prose leaves
are exact ``{en, hu}`` pairs. Future live runs create this shape natively; this
script exists only for the D-37 -> D-34 transition.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
os.environ["LOCALIZER_PROVIDER"] = "openai"
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")

from lab import llm  # noqa: E402
from policy_lab.i18n import (  # noqa: E402
    BILINGUAL_VERSION,
    bilingualize_content,
    is_localized_text,
    load_field_map,
    suspicious_identity,
    values_at_path,
)
from policy_lab.jsonio import content_hash, write_json  # noqa: E402
from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402


DEFAULT_ROOTS = (
    "v2",
    "v2/experiments/2026-07-20-psychology-lens-live",
    "v2/production/2026-07-20-live/korai-szelekcio",
    "v2/production/2026-07-20-live/rural-school-closures",
    "v2/production/2026-07-21-sni-brief-revision-2/sni-letszamnovekedes",
)
CACHE_PATH = ROOT / "v2" / "bilingual_migration" / "translation_cache.json"
AUDIT_PATH = ROOT / "v2" / "bilingual_migration" / "migration_manifest.json"
PAIR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "translations": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "key": {"type": "string"},
                    "hu": {"type": "string", "minLength": 1},
                },
                "required": ["key", "hu"],
            },
        }
    },
    "required": ["translations"],
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_pair_memory(value: Any, memory: dict[str, str]) -> None:
    if is_localized_text(value):
        memory.setdefault(value["en"], value["hu"])
    elif isinstance(value, dict):
        for child in value.values():
            collect_pair_memory(child, memory)
    elif isinstance(value, list):
        for child in value:
            collect_pair_memory(child, memory)


def get_path(value: Any, path: str) -> Any:
    current = value
    for token in path.split("."):
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def seed_translation_memory(roots: list[Path]) -> dict[str, str]:
    memory: dict[str, str] = {}
    for base in (ROOT / "topics", ROOT / "outputs"):
        for path in base.rglob("*.json"):
            try:
                collect_pair_memory(load(path), memory)
            except (json.JSONDecodeError, OSError):
                continue
    for root in roots:
        repository = ArtifactRepository(root, SchemaRegistry(ROOT / "schemas" / "v2"))
        records = {record["id"]: record for record in repository.list()}
        for record in records.values():
            collect_pair_memory(record["content"], memory)
        bundle_path = root / "localization" / "hu.json"
        if not bundle_path.exists():
            continue
        for key, hungarian in load(bundle_path)["translations"].items():
            record_id, separator, field_path = key.partition(".")
            if not separator or record_id not in records:
                continue
            try:
                english = get_path(records[record_id]["content"], field_path)
            except (KeyError, IndexError, ValueError, TypeError):
                continue
            if isinstance(english, str) and english.strip():
                memory.setdefault(english, hungarian)
    if CACHE_PATH.exists():
        memory.update(load(CACHE_PATH)["translations"])
    return memory


def required_english(
    roots: list[Path], field_map: dict[str, tuple[str, ...]]
) -> set[str]:
    required: set[str] = set()
    schemas = SchemaRegistry(ROOT / "schemas" / "v2")
    for root in roots:
        repository = ArtifactRepository(root, schemas)
        for record in repository.list():
            if record["record_type"] not in field_map:
                continue
            for path in field_map[record["record_type"]]:
                for parent, key in values_at_path(record["content"], path):
                    value = parent[key]
                    if is_localized_text(value):
                        required.add(value["en"])
                    elif isinstance(value, str) and value.strip():
                        required.add(value)
    return required


def identical_english(
    roots: list[Path], field_map: dict[str, tuple[str, ...]]
) -> set[str]:
    values: set[str] = set()
    schemas = SchemaRegistry(ROOT / "schemas" / "v2")
    for root in roots:
        repository = ArtifactRepository(root, schemas)
        for record in repository.list():
            if record["record_type"] not in field_map:
                continue
            for path in field_map[record["record_type"]]:
                for parent, key in values_at_path(record["content"], path):
                    value = parent[key]
                    if suspicious_identity(record["record_type"], path, value):
                        values.add(value["en"])
    return values


def chunks(strings: list[str], max_items: int = 20, max_words: int = 1000) -> list[list[str]]:
    result: list[list[str]] = []
    current: list[str] = []
    words = 0
    for value in strings:
        size = len(value.split())
        if current and (len(current) >= max_items or words + size > max_words):
            result.append(current)
            current, words = [], 0
        current.append(value)
        words += size
    if current:
        result.append(current)
    return result


def translate_batch(number: int, strings: list[str]) -> dict[str, str]:
    keyed = {f"k{index:03d}": value for index, value in enumerate(strings, 1)}
    schema = json.loads(json.dumps(PAIR_SCHEMA))
    schema["properties"]["translations"]["items"]["properties"]["key"]["enum"] = list(keyed)
    prompt = """TASK: retrofit_bilingual_artifacts
AGENT: hungarian_policy_editor
LANG: hu

Translate every keyed English policy-analysis string into natural, precise Hungarian. Preserve record ids, URLs, numbers, citations, evidence qualifications, and uncertainty exactly. Do not summarize, omit, soften, or add claims. Return every key exactly once.

STRINGS:
""" + "\n".join(f"{key}\t{value}" for key, value in keyed.items())
    result = llm.call_structured(prompt, schema, "localizer", max_tokens=16000)
    translated = {item["key"]: item["hu"] for item in result["translations"]}
    if set(translated) != set(keyed):
        raise ValueError(f"Translation batch {number} key coverage differs")
    return {keyed[key]: translated[key] for key in keyed}


def fill_missing(memory: dict[str, str], missing: list[str], concurrency: int) -> None:
    batches = chunks(missing)
    print(f"Translating {len(missing)} missing strings in {len(batches)} audited batches", flush=True)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {
            pool.submit(translate_batch, number, batch): number
            for number, batch in enumerate(batches, 1)
        }
        for future in as_completed(futures):
            number = futures[future]
            memory.update(future.result())
            write_json(CACHE_PATH, {
                "version": "1.0.0",
                "source": "D-34 bilingual retrofit; OpenAI localizer",
                "translations": dict(sorted(memory.items())),
                "updated_at": now(),
            })
            print(f"  batch {number}/{len(batches)} complete", flush=True)


def migrate_root(
    root: Path,
    field_map: dict[str, tuple[str, ...]],
    memory: dict[str, str],
    migrated_at: str,
) -> dict[str, Any]:
    schemas = SchemaRegistry(ROOT / "schemas" / "v2")
    repository = ArtifactRepository(root, schemas)
    current = {record["id"]: record for record in repository.list()}
    prepared: dict[str, dict[str, Any]] = {}
    for record_id, record in current.items():
        if record["record_type"] not in field_map:
            continue
        repair_paths = []
        if record["schema_version"] == BILINGUAL_VERSION:
            for path in field_map[record["record_type"]]:
                if any(
                    suspicious_identity(record["record_type"], path, parent[key])
                    for parent, key in values_at_path(record["content"], path)
                ):
                    repair_paths.append(path)
            if not repair_paths:
                continue
        successor = json.loads(json.dumps(record))
        successor["schema_version"] = BILINGUAL_VERSION
        successor["created_at"] = migrated_at
        successor["supersedes"] = content_hash(record)
        if repair_paths:
            for path in repair_paths:
                for parent, key in values_at_path(successor["content"], path):
                    value = parent[key]
                    if suspicious_identity(record["record_type"], path, value):
                        value["hu"] = memory[value["en"]]
        else:
            successor["content"] = bilingualize_content(
                record["record_type"], record["content"], field_map, memory.__getitem__
            )
        prepared[record_id] = successor

    # The successor points to a migration provenance record, not to the
    # provenance of the original English generation. The immutable predecessor
    # remains reachable through ``supersedes`` and retains its original
    # generator provenance, so the retrofit cannot be mistaken for native
    # bilingual authorship.
    provenance_by_topic: dict[str, str] = {}
    for topic in sorted({record["topic"] for record in prepared.values()}):
        source_hashes = sorted(
            content_hash(current[record_id])
            for record_id, record in prepared.items()
            if record["topic"] == topic
        )
        execution_id = content_hash({
            "migration": "d34_bilingual_retrofit",
            "root": str(root.relative_to(ROOT)),
            "topic": topic,
            "inputs": source_hashes,
            "artifact_schema_version": BILINGUAL_VERSION,
        })
        provenance_id = f"PV-bilingual-migration-{execution_id[:16]}"
        repository.put({
            "id": provenance_id,
            "record_type": "provenance",
            "schema_version": "2.0.0",
            "topic": topic,
            "status": "candidate",
            "content": {
                "node_id": "bilingual_migration",
                "execution_id": execution_id,
                "input_artifact_hashes": source_hashes,
                "spec_hashes": {
                    "config/v2/bilingual_fields.json": content_hash(
                        load(ROOT / "config" / "v2" / "bilingual_fields.json")
                    ),
                    "scripts/migrate_v2_bilingual.py": content_hash(
                        (ROOT / "scripts" / "migrate_v2_bilingual.py").read_text(
                            encoding="utf-8"
                        )
                    ),
                },
                "schema_hashes": {
                    "schemas/v2/bilingual.schema.json": content_hash(
                        load(ROOT / "schemas" / "v2" / "bilingual.schema.json")
                    )
                },
                "prompt_hash": content_hash(
                    "Faithful English-to-Hungarian D-34 retrofit; no analytical rerun"
                ),
                "provider": "openai",
                "model": os.environ["OPENAI_MODEL"],
                "role": "localizer",
                "generation_parameters": {
                    "semantic_change_allowed": False,
                    "analytical_rerun": False,
                },
                "relevant_config_hash": content_hash({
                    "artifact_schema_version": BILINGUAL_VERSION,
                    "languages": ["en", "hu"],
                }),
            },
            "provenance_ref": None,
            "created_at": migrated_at,
            "supersedes": None,
        })
        provenance_by_topic[topic] = provenance_id

    for record in prepared.values():
        record["provenance_ref"] = provenance_by_topic[record["topic"]]

    # Human approvals carry forward because the English candidate is unchanged;
    # bind the migrated decision records to the exact bilingual successor hash.
    for record in prepared.values():
        candidate_ref = record["content"].get("candidate_ref")
        if candidate_ref in prepared and "candidate_hash" in record["content"]:
            record["content"]["candidate_hash"] = content_hash(prepared[candidate_ref])

    for record in prepared.values():
        repository.put(record)

    roots = []
    manifest_path = root / "production_manifest.json"
    if manifest_path.exists():
        summary = load(manifest_path)["summary"]
        roots = [summary["package_ref"], summary["evaluation_ref"], summary["readiness_ref"]]
    repository.validate_graph(tuple(roots) if roots else None)
    bilingual = [
        record for record in repository.list()
        if record["record_type"] in field_map and record["schema_version"] == BILINGUAL_VERSION
    ]
    expected = [record for record in repository.list() if record["record_type"] in field_map]
    if len(bilingual) != len(expected):
        raise ValueError(f"Bilingual migration incomplete in {root}")
    return {
        "root": str(root.relative_to(ROOT)),
        "migrated_records": len(prepared),
        "current_bilingual_records": len(bilingual),
        "current_total_records": len(repository.list()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", dest="roots")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--repair-identical", action="store_true",
        help="replace long unchanged en/hu prose copies in current 2.1 records",
    )
    args = parser.parse_args()
    roots = [ROOT / value for value in (args.roots or DEFAULT_ROOTS)]
    field_map = load_field_map(ROOT)
    memory = seed_translation_memory(roots)
    required = required_english(roots, field_map)
    repair_required = identical_english(roots, field_map) if args.repair_identical else set()
    for value in repair_required:
        memory.pop(value, None)
    missing = sorted(required - set(memory), key=lambda value: (len(value.split()), value))
    print(
        f"Bilingual retrofit: {len(required)} unique semantic strings; "
        f"{len(required) - len(missing)} reused; {len(missing)} missing",
        flush=True,
    )
    if repair_required:
        print(f"Forced repair: {len(repair_required)} long identical prose values", flush=True)
    if args.dry_run:
        return 0
    if missing:
        fill_missing(memory, missing, args.concurrency)
    migrated_at = now()
    results = [migrate_root(root, field_map, memory, migrated_at) for root in roots]
    if args.repair_identical and AUDIT_PATH.exists():
        audit = load(AUDIT_PATH)
        audit.setdefault("repairs", []).append({
            "repair_type": "long_identical_language_copy",
            "repaired_at": migrated_at,
            "repaired_values": len(repair_required),
            "roots": results,
        })
        audit["current_state"] = results
        audit["translation_memory_size"] = len(memory)
        audit["updated_at"] = migrated_at
    else:
        audit = {
            "version": "1.0.0",
            "decision": "D-34 restored for v2 semantic artifacts",
            "migration_type": "retrospective_translation_without_analytical_rerun",
            "artifact_schema_version": BILINGUAL_VERSION,
            "migrated_at": migrated_at,
            "translation_memory_size": len(memory),
            "roots": results,
        }
    write_json(AUDIT_PATH, audit)
    for result in results:
        print(
            f"{result['root']}: {result['migrated_records']} successors; "
            f"{result['current_bilingual_records']} bilingual current records",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
