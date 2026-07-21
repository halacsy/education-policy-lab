#!/usr/bin/env python3
"""Definition-of-done checks for the artifact-first v2 vertical slice."""

from __future__ import annotations

import ast
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402
from policy_lab.jsonio import content_hash  # noqa: E402


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


class HungarianTextParser(HTMLParser):
    """Collect text visible in the default Hungarian view."""

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__()
        self.skip_stack: list[bool] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        inherited = self.skip_stack[-1] if self.skip_stack else False
        skip = inherited or attributes.get("lang") == "en" or "lang-en" in classes or tag in {"script", "style"}
        if tag not in self.VOID_TAGS:
            self.skip_stack.append(skip)

    def handle_endtag(self, tag: str) -> None:
        if tag not in self.VOID_TAGS and self.skip_stack:
            self.skip_stack.pop()

    def handle_data(self, data: str) -> None:
        if not (self.skip_stack and self.skip_stack[-1]) and data.strip():
            self.text.append(" ".join(data.split()))


def flatten_messages(value: object, prefix: str = "") -> dict[str, str]:
    if isinstance(value, str):
        return {prefix: value}
    if not isinstance(value, dict):
        raise AssertionError(f"Localization value at {prefix or '<root>'} must be a string or object")
    flattened: dict[str, str] = {}
    for key, child in value.items():
        child_prefix = f"{prefix}.{key}" if prefix else key
        flattened.update(flatten_messages(child, child_prefix))
    return flattened


def verify_localization(site_root: Path) -> tuple[int, int]:
    locale_root = ROOT / "config" / "v2" / "locales"
    schema = json.loads((locale_root / "catalog.schema.json").read_text(encoding="utf-8"))
    catalogs = {
        locale: json.loads((locale_root / f"{locale}.json").read_text(encoding="utf-8"))
        for locale in ("en", "hu")
    }
    validator = Draft202012Validator(schema)
    for locale, catalog in catalogs.items():
        errors = sorted(validator.iter_errors(catalog), key=lambda error: list(error.path))
        if errors:
            raise AssertionError(f"Invalid {locale} localization catalog: {errors[0].message}")
        if catalog["locale"] != locale:
            raise AssertionError(f"Localization catalog identity mismatch: {locale}")
        for replacement in catalog["content_replacements"]:
            try:
                re.compile(replacement["pattern"])
            except re.error as error:
                raise AssertionError(f"Invalid {locale} content-replacement regex: {error}") from error
    versions = {catalog["catalog_version"] for catalog in catalogs.values()}
    if len(versions) != 1:
        raise AssertionError(f"Localization catalog versions differ: {sorted(versions)}")
    message_sets = {
        locale: flatten_messages(catalog["messages"])
        for locale, catalog in catalogs.items()
    }
    if message_sets["en"].keys() != message_sets["hu"].keys():
        missing_hu = sorted(message_sets["en"].keys() - message_sets["hu"].keys())
        missing_en = sorted(message_sets["hu"].keys() - message_sets["en"].keys())
        raise AssertionError(f"Localization key mismatch; missing HU={missing_hu}, missing EN={missing_en}")

    builder = ast.parse((ROOT / "scripts" / "build_v2_site.py").read_text(encoding="utf-8"))
    for node in ast.walk(builder):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "bi"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            raise AssertionError(
                f"Static bilingual copy must use the locale catalog, not bi() (build_v2_site.py:{node.lineno})"
            )

    forbidden = re.compile(
        r"(?i)(?<![\w-])(?:lens(?:es)?|verdicts?|evidence|confidence|medium|findings?|"
        r"transformation proposal|organization|strong|artifacts?|assessments?|baseline|"
        r"cache hits?|decision packages?|research questions?|monitoring|status quo|"
        r"downstream|pilot)(?![\w-])"
    )
    checked_pages = 0
    for page in site_root.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        if '<html lang="hu"' not in source:
            raise AssertionError(f"Hungarian must be the default website language: {page}")
        parser = HungarianTextParser()
        parser.feed(source)
        visible_hungarian = " ".join(parser.text)
        match = forbidden.search(visible_hungarian)
        if match:
            raise AssertionError(f"Raw English UI term in Hungarian view of {page}: {match.group(0)!r}")
        checked_pages += 1
    return len(message_sets["hu"]), checked_pages


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


def verify_production_runs(schemas: SchemaRegistry) -> tuple[int, int, int]:
    """Validate the two fresh production DAGs and their publication boundary."""

    root = ROOT / "v2" / "production" / "2026-07-20-live"
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    expected_topics = {"korai-szelekcio", "rural-school-closures"}
    actual_topics = {item["topic"] for item in catalog["topics"]}
    if actual_topics != expected_topics:
        raise AssertionError(f"Production catalog topics differ: {sorted(actual_topics)}")

    artifact_count = 0
    call_count = 0
    for item in catalog["topics"]:
        topic_root = root / item["topic"]
        repository = ArtifactRepository(topic_root, schemas)
        roots = (item["package_ref"], item["evaluation_ref"], item["readiness_ref"])
        repository.validate_graph(roots)
        records = repository.list()
        artifact_count += len(records)

        manifest = json.loads((topic_root / "production_manifest.json").read_text(encoding="utf-8"))
        summary = manifest["summary"]
        if summary["execution"]["nodes"] != 31 or summary["execution"]["failed"] != 0:
            raise AssertionError(f"Production DAG is incomplete for {item['topic']}")
        if summary["counts"]["lens_definition"] != 12:
            raise AssertionError(f"Production panel must contain 12 admitted lenses for {item['topic']}")
        if summary["counts"]["lens_assessment"] != 72:
            raise AssertionError(f"Every lens must assess all six proposals for {item['topic']}")
        if summary["counts"]["finding"] < 84:
            raise AssertionError(f"Research breadth floor failed for {item['topic']}")

        coverage = repository.get_current("CL-live-approved-frames")["content"]
        approved_frames = json.loads(
            (ROOT / "topics" / item["topic"] / "topic.json").read_text(encoding="utf-8")
        )["frames"]["scenarios"]
        expected_directions = {frame["id"] for frame in approved_frames}
        actual_directions = {entry["direction_id"] for entry in coverage["entries"]}
        if coverage["verdict"] != "complete" or coverage["critical_attrition_count"] != 0:
            raise AssertionError(f"Approved-frame coverage gate failed for {item['topic']}")
        if actual_directions != expected_directions:
            raise AssertionError(f"Approved-frame identities differ for {item['topic']}")

        package = repository.get_current(item["package_ref"])
        if len(package["content"]["evidence_appendix"]) < 1:
            raise AssertionError(f"Evidence appendix is empty for {item['topic']}")
        if package["content"]["summary"].count("[F-") < summary["counts"]["transformation_proposal"]:
            raise AssertionError(f"Inline claim-to-source carriage failed for {item['topic']}")

        readiness = repository.get_current(item["readiness_ref"])["content"]
        if readiness["verdict"] != "ready_with_conditions":
            raise AssertionError(f"Unexpected readiness verdict for {item['topic']}")
        if readiness["human_external_use_gate"] != "pending":
            raise AssertionError(f"Machine output bypassed the human external-use gate for {item['topic']}")

        bundle = json.loads((topic_root / "localization" / "hu.json").read_text(encoding="utf-8"))
        if bundle["locale"] != "hu" or bundle["source_package_hash"] != content_hash(package):
            raise AssertionError(f"Hungarian localization is not hash-bound to the current package for {item['topic']}")
        if not bundle["translations"]:
            raise AssertionError(f"Hungarian localization bundle is empty for {item['topic']}")

        calls = [
            json.loads(line)
            for line in (topic_root / "backend_calls.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        call_count += len(calls)
        if any(call.get("backend") == "mock" for call in calls):
            raise AssertionError(f"Production run contains a mock call for {item['topic']}")
        providers = {call.get("provider") for call in calls if call.get("backend") != "failed"}
        if not {"anthropic", "openai"}.issubset(providers):
            raise AssertionError(f"Cross-family generation/judging missing for {item['topic']}")

    return len(catalog["topics"]), artifact_count, call_count


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
    localized_messages, localized_pages = verify_localization(ROOT / "site" / "v2")
    live_artifacts, live_calls = verify_live_experiment(schemas)
    production_topics, production_artifacts, production_calls = verify_production_runs(schemas)
    print(f"PASS schemas: {len(schemas.available())} versioned record types")
    print(f"PASS graph: {len(records)} current artifacts, {len(roots)} decision roots")
    print("PASS language boundary: no en/hu objects in canonical artifact content")
    print("PASS runs: 2 topics × 6 node manifests")
    print(f"PASS site: {checked_links} local links/assets resolved")
    print(f"PASS localization: {localized_messages} paired messages, {localized_pages} Hungarian pages free of raw UI terms")
    print(f"PASS live experiment: {live_artifacts} current artifacts, {live_calls} audited calls, position carriage green")
    print(f"PASS production: {production_topics} topics, {production_artifacts} current artifacts, {production_calls} audited calls, human gate preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
