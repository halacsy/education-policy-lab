#!/usr/bin/env python3
"""Definition-of-done checks for the artifact-first v2 vertical slice."""

from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"] or "")
        if tag in {"script", "link"}:
            candidate = attributes.get("src") or attributes.get("href")
            if candidate:
                self.links.append(candidate)


def has_language_object(value: object) -> bool:
    if isinstance(value, dict):
        if "en" in value or "hu" in value:
            return True
        return any(has_language_object(item) for item in value.values())
    if isinstance(value, list):
        return any(has_language_object(item) for item in value)
    return False


def verify_links(site_root: Path) -> int:
    checked = 0
    for page in site_root.rglob("*.html"):
        parser = LinkParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for link in parser.links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc or link.startswith(('#', 'mailto:')):
                continue
            target = (page.parent / parts.path).resolve()
            if parts.path.endswith("/"):
                target /= "index.html"
            if not target.exists():
                raise AssertionError(f"Broken local link in {page}: {link}")
            checked += 1
    return checked


def verify_live_experiment(schemas: SchemaRegistry) -> tuple[int, int]:
    root = ROOT / "v2" / "experiments" / "2026-07-20-psychology-lens-live"
    repository = ArtifactRepository(root, schemas)
    live_roots = (
        "DP-live-baseline", "EV-live-baseline",
        "DP-live-psychology", "EV-live-psychology",
    )
    repository.validate_graph(live_roots)
    comparison = json.loads((root / "comparison.json").read_text(encoding="utf-8"))
    if not comparison["transformation_hashes_identical"]:
        raise AssertionError("Psychology treatment changed the transformation portfolio")
    if comparison["psychology_assessment_count"] != 6:
        raise AssertionError("Psychology lens must assess all six proposals")
    if not comparison["position_carriage_passed"]:
        raise AssertionError("Named psychology mechanism did not reach the decision package")
    if (comparison["baseline_lens_count"], comparison["psychology_lens_count"]) != (12, 13):
        raise AssertionError("Live arm lens counts must be 12 and 13")
    for arm, expected_nodes in (("baseline", 30), ("psychology", 32)):
        run_dir = root / "runs" / f"live-korai-szelekcio-{arm}"
        manifests = list((run_dir / "nodes").glob("*.json"))
        if len(manifests) != expected_nodes:
            raise AssertionError(f"{arm} requires {expected_nodes} current node manifests")
        summary = json.loads((run_dir / "arm_summary.json").read_text(encoding="utf-8"))
        if summary["execution"]["failed"]:
            raise AssertionError(f"{arm} has failed current nodes")
    if comparison["treatment_execution"]["cache_hits"] < 26:
        raise AssertionError("Psychology treatment did not localize dependencies")
    for arm in ("baseline", "psychology"):
        words = len(repository.get_current(f"DP-live-{arm}")["content"]["summary"].split())
        if not 500 <= words <= 900:
            raise AssertionError(f"{arm} package has {words} words; expected 500-900")
    calls = [
        json.loads(line) for line in (root / "backend_calls.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    active_backends = {item.get("provider") for item in calls if item.get("backend") != "failed"}
    if not {"anthropic", "openai"}.issubset(active_backends):
        raise AssertionError("Live experiment must use Anthropic generation and OpenAI judging")
    if any(item.get("backend") == "mock" for item in calls):
        raise AssertionError("Live experiment contains a mock backend call")
    return len(repository.list()), len(calls)


def main() -> int:
    schemas = SchemaRegistry(ROOT / "schemas" / "v2")
    repository = ArtifactRepository(ROOT / "v2", schemas)
    catalog = json.loads(
        (ROOT / "v2" / "catalog" / "topics.json").read_text(encoding="utf-8")
    )
    roots = tuple(
        ref for topic in catalog["topics"] for ref in topic["decision_package_refs"]
    )
    repository.validate_graph(roots)
    records = repository.list()
    if any(has_language_object(record["content"]) for record in records):
        raise AssertionError("Canonical v2 JSON contains a bilingual en/hu object")
    if len(records) != 1014:
        raise AssertionError(f"Expected 1014 current artifacts, found {len(records)}")
    for topic in catalog["topics"]:
        node_dir = ROOT / "v2" / "runs" / topic["run_id"] / "nodes"
        if len(list(node_dir.glob("*.json"))) != 6:
            raise AssertionError(f"Expected six node manifests for {topic['topic']}")
    checked_links = verify_links(ROOT / "site" / "v2")
    live_artifacts, live_calls = verify_live_experiment(schemas)
    print(f"PASS schemas: {len(schemas.available())} versioned record types")
    print(f"PASS graph: {len(records)} current artifacts, {len(roots)} decision roots")
    print("PASS language boundary: no en/hu objects in canonical artifact content")
    print("PASS runs: 2 topics × 6 node manifests")
    print(f"PASS site: {checked_links} local links/assets resolved")
    print(f"PASS live experiment: {live_artifacts} current artifacts, {live_calls} audited calls, position carriage green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
