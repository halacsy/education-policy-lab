#!/usr/bin/env python3
"""Create audited Hungarian presentation bundles from canonical English v2 artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
os.environ["GENERATOR_PROVIDER"] = "anthropic"
os.environ["LOCALIZER_PROVIDER"] = "openai"
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")

from jsonschema import Draft202012Validator  # noqa: E402
from lab import llm  # noqa: E402
from policy_lab.jsonio import content_hash, write_json  # noqa: E402
from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402

TEXT = {"type": "string", "minLength": 1}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add_fields(items: dict[str, str], record: dict[str, Any], fields: tuple[str, ...]) -> None:
    content = record["content"]
    for field in fields:
        value = content.get(field)
        if isinstance(value, str):
            items[f"{record['id']}.{field}"] = value
        elif isinstance(value, list):
            for index, child in enumerate(value):
                if isinstance(child, str):
                    items[f"{record['id']}.{field}.{index}"] = child
                elif isinstance(child, dict):
                    for name, text in child.items():
                        if isinstance(text, str):
                            items[f"{record['id']}.{field}.{index}.{name}"] = text


def public_text(repository: ArtifactRepository, package: dict[str, Any], evaluation: dict[str, Any], readiness: dict[str, Any]) -> dict[str, str]:
    items: dict[str, str] = {f"{package['id']}.summary": package["content"]["summary"]}
    for artifact_id in package["content"]["proposal_refs"]:
        add_fields(items, repository.get_current(artifact_id), (
            "title", "goal", "mechanisms", "implementation_steps",
            "expected_benefits", "costs", "risks", "equity_impact",
        ))
    for artifact_id in package["content"]["dilemma_refs"]:
        add_fields(items, repository.get_current(artifact_id), (
            "title", "tension", "value_poles", "decision_question", "evidence_boundary",
        ))
    for artifact_id in package["content"]["research_question_refs"]:
        add_fields(items, repository.get_current(artifact_id), ("question", "why_it_matters", "method"))
    add_fields(items, evaluation, ("strengths", "concerns"))
    add_fields(items, readiness, ("rationale",))
    for entry in package["content"]["evidence_appendix"]:
        items[f"{entry['finding_ref']}.claim"] = entry["claim"]
    briefs = repository.list(record_type="problem_brief")
    if briefs:
        add_fields(items, briefs[0], (
            "title", "public_question", "problem_statement", "learning_goals", "scope",
        ))
    for coverage_ref in package["content"]["coverage_ledger_refs"]:
        coverage = repository.get_current(coverage_ref)
        for index, entry in enumerate(coverage["content"]["entries"]):
            items[f"{coverage['id']}.entries.{index}.direction_title"] = entry["direction_title"]
    return items


def translate_chunk(topic: str, chunk: dict[str, str], path: Path) -> dict[str, str]:
    if path.exists():
        cached = load(path)
        if set(cached) == set(chunk):
            return cached
    keys = list(chunk)
    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {"translations": {
            "type": "array", "minItems": 1,
            "items": {"type": "object", "additionalProperties": False,
                "properties": {"key": {"type": "string", "enum": keys}, "text": TEXT},
                "required": ["key", "text"]},
        }}, "required": ["translations"],
    }
    source = "\n".join(f"{key}\t{text}" for key, text in chunk.items())
    prompt = f"""TASK: localize_public_view
AGENT: hungarian_policy_editor
LANG: hu

Translate every keyed English string below into natural, publication-quality Hungarian. Preserve artifact ids such as [F-live-...] exactly, preserve numbers and URLs, and use established Hungarian education-policy terminology. Translate meaning, not sentence structure. Return every key exactly once and no extra key.

TOPIC: {topic}
STRINGS:
{source}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    (path.parent / f"{path.stem}.prompt.md").write_text(prompt, encoding="utf-8")
    for attempt in range(3):
        result = llm.call_structured(prompt, schema, "localizer", max_tokens=10000)
        translated = {item["key"]: item["text"] for item in result["translations"]}
        if set(translated) == set(chunk):
            write_json(path, translated)
            return translated
        prompt += f"\n\nREPAIR: return exactly these {len(keys)} keys: {', '.join(keys)}"
    raise ValueError(f"Localization key coverage failed for {topic}:{path.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tag", default="2026-07-20-live")
    parser.add_argument("--topic", action="append", dest="topics")
    args = parser.parse_args()
    topics = args.topics or ["korai-szelekcio", "rural-school-closures"]
    schemas = SchemaRegistry(ROOT / "schemas" / "v2")
    bundle_schema = load(ROOT / "config" / "v2" / "locales" / "public_content.schema.json")
    for topic in topics:
        root = ROOT / "v2" / "production" / args.run_tag / topic
        repository = ArtifactRepository(root, schemas)
        manifest = load(root / "production_manifest.json")
        package = repository.get_current(manifest["summary"]["package_ref"])
        evaluation = repository.get_current(manifest["summary"]["evaluation_ref"])
        readiness = repository.get_current(manifest["summary"]["readiness_ref"])
        strings = public_text(repository, package, evaluation, readiness)
        translations: dict[str, str] = {}
        pairs = list(strings.items())
        for number, start in enumerate(range(0, len(pairs), 20), 1):
            chunk = dict(pairs[start:start + 20])
            translations.update(translate_chunk(topic, chunk, root / "localization" / "hu" / f"chunk-{number:02d}.json"))
        bundle = {
            "locale": "hu", "bundle_version": "1.0.0",
            "source_package_hash": content_hash(package),
            "translations": translations, "generated_at": now(),
        }
        errors = list(Draft202012Validator(bundle_schema).iter_errors(bundle))
        if errors:
            raise ValueError(errors[0].message)
        write_json(root / "localization" / "hu.json", bundle)
        print(f"{topic}: {len(translations)} localized public strings", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
