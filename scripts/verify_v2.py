#!/usr/bin/env python3
"""Definition-of-done checks for the artifact-first v2 vertical slice."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.schema_registry import SchemaRegistry  # noqa: E402
from policy_lab.store import ArtifactRepository  # noqa: E402
from policy_lab.jsonio import content_hash  # noqa: E402
from policy_lab.render import (  # noqa: E402
    PUBLIC_RECORD_TYPES,
    canonical_url,
    href_between,
    record_index_route,
    record_route,
    topic_route,
)
from policy_lab.i18n import (  # noqa: E402
    BILINGUAL_VERSION, load_field_map, suspicious_identity, text,
    values_at_path,
)
from policy_lab.coverage import validate_exact_coverage  # noqa: E402


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
        skip = inherited or attributes.get("lang") == "en" or "lang-en" in classes or tag in {"script", "style", "cite"}
        if tag not in self.VOID_TAGS:
            self.skip_stack.append(skip)

    def handle_endtag(self, tag: str) -> None:
        if tag not in self.VOID_TAGS and self.skip_stack:
            self.skip_stack.pop()

    def handle_data(self, data: str) -> None:
        if not (self.skip_stack and self.skip_stack[-1]) and data.strip():
            self.text.append(" ".join(data.split()))


class RecordPageParser(HTMLParser):
    """Collect the identity contract and links of one generated record page."""

    def __init__(self) -> None:
        super().__init__()
        self.html_attrs: dict[str, str] = {}
        self.canonical: str | None = None
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.html_attrs = attributes
        if tag == "link" and attributes.get("rel") == "canonical":
            self.canonical = attributes.get("href")
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])


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


def verify_canonical_record_pages(schemas: SchemaRegistry) -> tuple[int, int]:
    """Require one stable, self-identifying page for every public semantic record."""

    publication = json.loads(
        (ROOT / "config" / "v2" / "publication.json").read_text(encoding="utf-8")
    )
    site_url = publication.get("site_url")
    if not isinstance(site_url, str) or not site_url.startswith("https://"):
        raise AssertionError("Publication manifest requires an absolute HTTPS site_url")

    public_types = set(PUBLIC_RECORD_TYPES) - {"canonical_claim"}
    expected_pages: dict[str, dict] = {}
    expected_sitemap_routes = {"index.html"}
    for item in publication["topics"]:
        topic = item["topic"]
        root = ROOT / "v2" / "production" / item["run_tag"] / topic
        repository = ArtifactRepository(root, schemas)
        records = repository.list()
        records_by_id = {record["id"]: record for record in records}
        expected_sitemap_routes.add(topic_route(topic))
        expected_sitemap_routes.add(record_index_route(topic))
        for record in records:
            if record["record_type"] not in public_types:
                continue
            route = record_route(topic, record["record_type"], record["id"])
            if route in expected_pages:
                raise AssertionError(f"Two semantic records resolve to one public route: {route}")
            expected_pages[route] = record
            expected_sitemap_routes.add(route)

        index_path = ROOT / "site" / record_index_route(topic)
        if not index_path.exists():
            raise AssertionError(f"Missing canonical record index: {index_path}")
        index_parser = LinkParser()
        index_parser.feed(index_path.read_text(encoding="utf-8"))
        index_route = record_index_route(topic)
        expected_index_links = {
            href_between(index_route, route)
            for route in expected_pages
            if route.startswith(f"questions/{topic}/")
        }
        missing_index_links = expected_index_links - set(index_parser.links)
        if missing_index_links:
            raise AssertionError(
                f"Canonical record index omits {len(missing_index_links)} pages for {topic}"
            )

        for route, record in list(expected_pages.items()):
            if record["topic"] != topic:
                continue
            page_path = ROOT / "site" / route
            if not page_path.exists():
                raise AssertionError(f"Missing canonical page for {record['id']}: {route}")
            parser = RecordPageParser()
            parser.feed(page_path.read_text(encoding="utf-8"))
            expected_attrs = {
                "data-record-id": record["id"],
                "data-record-type": record["record_type"],
                "data-record-topic": topic,
                "data-record-content-hash": content_hash(record),
            }
            for attribute, expected in expected_attrs.items():
                if parser.html_attrs.get(attribute) != expected:
                    raise AssertionError(
                        f"Record identity mismatch in {route}: {attribute}"
                    )
            expected_canonical = canonical_url(site_url, route)
            if parser.canonical != expected_canonical:
                raise AssertionError(f"Wrong canonical URL in {route}: {parser.canonical}")

            for reference in schemas.references(record):
                target = records_by_id.get(reference.target_id)
                if target is None or target["record_type"] not in public_types:
                    continue
                target_route = record_route(topic, target["record_type"], target["id"])
                expected_href = href_between(route, target_route)
                if expected_href not in parser.links:
                    raise AssertionError(
                        f"Typed public reference is not linked: {record['id']} -> {target['id']}"
                    )

    actual_record_routes = {
        str(path.relative_to(ROOT / "site")).replace("\\", "/")
        for item in publication["topics"]
        for path in (ROOT / "site" / "questions" / item["topic"]).glob("*/*.html")
    }
    if actual_record_routes != set(expected_pages):
        missing = sorted(set(expected_pages) - actual_record_routes)
        stale = sorted(actual_record_routes - set(expected_pages))
        raise AssertionError(f"Canonical page coverage differs: missing={missing[:3]}, stale={stale[:3]}")

    sitemap_root = ET.parse(ROOT / "site" / "sitemap.xml").getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    actual_sitemap = {
        element.text for element in sitemap_root.findall("sm:url/sm:loc", namespace)
    }
    expected_sitemap = {
        canonical_url(site_url, route) for route in expected_sitemap_routes
    }
    if actual_sitemap != expected_sitemap:
        raise AssertionError(
            f"Sitemap differs from publication boundary: expected {len(expected_sitemap)}, "
            f"found {len(actual_sitemap)}"
        )
    return len(expected_pages), len(expected_sitemap)


def verify_bilingual_records(records: list[dict], label: str) -> None:
    field_map = load_field_map(ROOT)
    non_bilingual = [
        record["id"] for record in records
        if record["record_type"] in field_map
        and record["schema_version"] != BILINGUAL_VERSION
    ]
    if non_bilingual:
        raise AssertionError(
            f"{label} semantic artifacts are not canonical bilingual v2.1: "
            f"{non_bilingual[:5]}"
        )
    copied = []
    for record in records:
        if record["record_type"] not in field_map:
            continue
        for path in field_map[record["record_type"]]:
            for parent, key in values_at_path(record["content"], path):
                if suspicious_identity(record["record_type"], path, parent[key]):
                    copied.append(f"{record['id']}.{path}")
    if copied:
        raise AssertionError(
            f"{label} contains long unchanged English/Hungarian prose: {copied[:5]}"
        )


def verify_live_experiment(schemas: SchemaRegistry) -> tuple[int, int]:
    root = ROOT / "v2" / "experiments" / "2026-07-20-psychology-lens-live"
    repository = ArtifactRepository(root, schemas)
    live_roots = (
        "DP-live-baseline", "EV-live-baseline",
        "DP-live-psychology", "EV-live-psychology",
    )
    repository.validate_graph(live_roots)
    live_records = repository.list()
    verify_bilingual_records(live_records, "Psychology experiment")
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
        words = len(text(repository.get_current(f"DP-live-{arm}")["content"]["summary"], "en").split())
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
    return len(live_records), len(calls)


def verify_production_runs(schemas: SchemaRegistry) -> tuple[int, int, int]:
    """Validate every explicitly published production DAG and its publication boundary."""

    publication = json.loads(
        (ROOT / "config" / "v2" / "publication.json").read_text(encoding="utf-8")
    )
    items = publication["topics"]
    if len({item["topic"] for item in items}) != len(items):
        raise AssertionError("Publication manifest contains duplicate topics")

    artifact_count = 0
    call_count = 0
    for item in items:
        topic_root = ROOT / "v2" / "production" / item["run_tag"] / item["topic"]
        repository = ArtifactRepository(topic_root, schemas)
        manifest = json.loads((topic_root / "production_manifest.json").read_text(encoding="utf-8"))
        summary = manifest["summary"]
        roots = (summary["package_ref"], summary["evaluation_ref"], summary["readiness_ref"])
        repository.validate_graph(roots)
        records = repository.list()
        artifact_count += len(records)

        declared_nodes = verify_declared_run_plan(topic_root, manifest, repository)
        expected_nodes = declared_nodes or 31
        if summary["execution"]["nodes"] != expected_nodes or summary["execution"]["failed"] != 0:
            raise AssertionError(f"Production DAG is incomplete for {item['topic']}")
        if len(repository.list(record_type="lens_definition")) != 12:
            raise AssertionError(f"Production panel must contain 12 admitted lenses for {item['topic']}")
        expected_assessments = 12 * summary["counts"]["transformation_proposal"]
        if summary["counts"]["lens_assessment"] != expected_assessments:
            raise AssertionError(f"Every lens must assess every proposal for {item['topic']}")
        if summary["counts"]["finding"] < 84:
            raise AssertionError(f"Research breadth floor failed for {item['topic']}")

        coverage = repository.get_current("CL-live-approved-frames")["content"]
        if declared_nodes:
            approved_frames = repository.get_current(
                f"AO-live-{item['topic']}"
            )["content"]["directions"]
            if coverage["gate_basis"] != "approved_option_space":
                raise AssertionError(
                    f"Fresh RunPlan bypassed approved option space for {item['topic']}"
                )
        else:
            approved_frames = json.loads(
                (ROOT / "topics" / item["topic"] / "topic.json").read_text(encoding="utf-8")
            )["frames"]["scenarios"]
        expected_directions = {frame["id"] for frame in approved_frames}
        actual_directions = {entry["direction_id"] for entry in coverage["entries"]}
        if coverage["verdict"] != "complete" or coverage["critical_attrition_count"] != 0:
            raise AssertionError(f"Approved-frame coverage gate failed for {item['topic']}")
        if actual_directions != expected_directions:
            raise AssertionError(f"Approved-frame identities differ for {item['topic']}")

        if manifest.get("architecture_version") == "3.2.0":
            normalization = repository.get_current(
                "CL-live-evidence-normalization"
            )["content"]
            finding_ids = {
                record["id"] for record in repository.list(record_type="finding")
            }
            validate_exact_coverage(
                normalization, finding_ids, basis="evidence_normalization"
            )
            seed_records = repository.list(record_type="option_seed")
            seed_coverage = repository.get_current("CL-live-option-seeds")["content"]
            validate_exact_coverage(
                seed_coverage, {record["id"] for record in seed_records},
                basis="option_seed_clustering",
                direction_ids=expected_directions,
            )
            proposals = repository.list(record_type="transformation_proposal")
            if any(not proposal["content"].get("canonical_claim_refs") for proposal in proposals):
                raise AssertionError(
                    f"A transformation bypassed normalized claims for {item['topic']}"
                )

        package = repository.get_current(summary["package_ref"])
        if len(package["content"]["evidence_appendix"]) < 1:
            raise AssertionError(f"Evidence appendix is empty for {item['topic']}")
        if text(package["content"]["summary"], "en").count("[F-") < summary["counts"]["transformation_proposal"]:
            raise AssertionError(f"Inline claim-to-source carriage failed for {item['topic']}")

        readiness = repository.get_current(summary["readiness_ref"])["content"]
        if readiness["verdict"] != "ready_with_conditions":
            raise AssertionError(f"Unexpected readiness verdict for {item['topic']}")
        if readiness["human_external_use_gate"] != "pending":
            raise AssertionError(f"Machine output bypassed the human external-use gate for {item['topic']}")

        verify_bilingual_records(records, f"Published {item['topic']}")

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

    return len(items), artifact_count, call_count


def verify_declared_run_plan(
    topic_root: Path,
    production_manifest: dict,
    repository: ArtifactRepository,
) -> int | None:
    """Prove that a fresh run executed the exact persisted plan and attempts."""

    plan_meta = production_manifest.get("run_plan")
    architecture = production_manifest.get("architecture_version")
    if not plan_meta:
        if architecture == "3.0.0":
            raise AssertionError("Architecture 3 production manifest has no RunPlan")
        return None
    plan_path = topic_root / plan_meta["path"]
    if not plan_path.exists():
        raise AssertionError(f"Missing persisted RunPlan: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_hash = content_hash(plan)
    if plan_hash != plan_meta["content_hash"]:
        raise AssertionError(f"RunPlan hash mismatch: {plan_path}")
    if architecture != plan["dag_version"]:
        raise AssertionError("Production manifest and RunPlan architecture differ")

    run_dir = topic_root / "runs" / production_manifest["run_id"]
    manifests = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in (run_dir / "nodes").glob("*.json")
    }
    declared = {node["id"]: node for node in plan["nodes"]}
    if set(manifests) != set(declared):
        raise AssertionError(
            f"Executed nodes differ from RunPlan: missing={sorted(set(declared)-set(manifests))}, "
            f"extra={sorted(set(manifests)-set(declared))}"
        )

    outputs: dict[str, list[dict]] = {}
    root_outputs = {
        f"root:{name}": refs for name, refs in plan["roots"].items()
    }
    provenance = {
        record["id"]: record
        for record in repository.list(record_type="provenance")
    }
    for root_refs in root_outputs.values():
        for ref in root_refs:
            record = repository.get_by_hash(ref["content_hash"])
            if (record["id"], record["record_type"]) != (ref["id"], ref["record_type"]):
                raise AssertionError("RunPlan root metadata differs from stored artifact")

    for node_id, node in declared.items():
        node_manifest = manifests[node_id]
        if node_manifest.get("run_plan_hash") != plan_hash:
            raise AssertionError(f"Node {node_id} was not bound to this RunPlan")
        expected_inputs: dict[str, list[str]] = {}
        for binding in node["inputs"]:
            refs = []
            for source in binding["sources"]:
                source_refs = root_outputs[source] if source.startswith("root:") else outputs[source]
                refs.extend(
                    ref for ref in source_refs
                    if ref["record_type"] in binding["record_types"]
                )
            count = len(refs)
            if count < binding["minimum"] or (
                binding["maximum"] is not None and count > binding["maximum"]
            ):
                raise AssertionError(f"RunPlan input cardinality failed at {node_id}.{binding['name']}")
            expected_inputs[binding["name"]] = [ref["content_hash"] for ref in refs]
        if node_manifest["input_artifacts"] != expected_inputs:
            raise AssertionError(f"Manifest inputs differ from RunPlan at {node_id}")
        node_outputs = node_manifest["output_artifacts"]
        undeclared = {
            ref["record_type"] for ref in node_outputs
        } - set(node["output_types"])
        if undeclared or not node_outputs:
            raise AssertionError(f"Node {node_id} output contract failed: {sorted(undeclared)}")
        for ref in node_outputs:
            record = repository.get_by_hash(ref["content_hash"])
            if (record["id"], record["record_type"]) != (ref["id"], ref["record_type"]):
                raise AssertionError(f"Stored output differs at {node_id}")
            provenance_record = provenance.get(record["provenance_ref"])
            if not provenance_record:
                raise AssertionError(f"Missing provenance for {ref['id']}")
            contract = provenance_record["content"]
            if contract.get("run_plan_hash") != plan_hash:
                raise AssertionError(f"Artifact provenance has wrong RunPlan at {ref['id']}")
            if node["kind"] == "llm":
                _verify_attempts(run_dir, node_id, contract)
        outputs[node_id] = node_outputs

    approved = repository.get_current(
        f"AO-live-{production_manifest['topic']}"
    )["content"]
    decision = repository.get_current(approved["decision_ref"])["content"]
    candidate = repository.get_current(approved["candidate_ref"])
    if approved["candidate_hash"] != content_hash(candidate):
        raise AssertionError("Approved option-space hash differs from candidate")
    if decision["candidate_hash"] != approved["candidate_hash"] or decision["decision"] != "approved":
        raise AssertionError("Human gate decision is not bound to approved option space")
    return len(declared)


def _verify_attempts(run_dir: Path, node_id: str, provenance: dict) -> None:
    attempts = provenance.get("attempts", [])
    if not attempts:
        raise AssertionError(f"LLM node {node_id} has no exact prompt/response attempts")
    execution_id = provenance["execution_id"]
    attempt_root = run_dir / "attempts" / node_id / execution_id
    for attempt in attempts:
        stage_dirs = list(attempt_root.glob(f"{attempt['stage']}-{attempt['prompt_hash'][:16]}"))
        if len(stage_dirs) != 1:
            raise AssertionError(f"Missing immutable attempt files for {node_id}.{attempt['stage']}")
        prompt = stage_dirs[0] / "prompt.md"
        responses = list(stage_dirs[0].glob("response.*"))
        if hashlib.sha256(prompt.read_bytes()).hexdigest() != attempt["prompt_hash"]:
            raise AssertionError(f"Prompt hash mismatch for {node_id}.{attempt['stage']}")
        if len(responses) != 1 or hashlib.sha256(responses[0].read_bytes()).hexdigest() != attempt["response_hash"]:
            raise AssertionError(f"Response hash mismatch for {node_id}.{attempt['stage']}")


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
    bilingual_types = load_field_map(ROOT)
    semantic_records = [record for record in records if record["record_type"] in bilingual_types]
    verify_bilingual_records(records, "Canonical v2")
    if len(semantic_records) != 1002:
        raise AssertionError(
            f"Expected 1002 current semantic artifacts, found {len(semantic_records)}"
        )
    for topic in catalog["topics"]:
        node_dir = ROOT / "v2" / "runs" / topic["run_id"] / "nodes"
        if len(list(node_dir.glob("*.json"))) != 6:
            raise AssertionError(f"Expected six node manifests for {topic['topic']}")
    canonical_pages, sitemap_urls = verify_canonical_record_pages(schemas)
    checked_links = verify_links(ROOT / "site")
    localized_messages, localized_pages = verify_localization(ROOT / "site")
    live_artifacts, live_calls = verify_live_experiment(schemas)
    production_topics, production_artifacts, production_calls = verify_production_runs(schemas)
    print(f"PASS schemas: {len(schemas.available())} versioned record types")
    print(f"PASS graph: {len(records)} current artifacts, {len(roots)} decision roots")
    print("PASS language contract: every current semantic artifact is canonical bilingual v2.1")
    print("PASS runs: 2 topics × 6 node manifests")
    print(
        f"PASS canonical pages: {canonical_pages} typed records have stable URLs; "
        f"sitemap has {sitemap_urls} exact publication URLs"
    )
    print(f"PASS site: {checked_links} local links/assets resolved")
    print(f"PASS localization: {localized_messages} paired messages, {localized_pages} Hungarian pages free of raw UI terms")
    print(f"PASS live experiment: {live_artifacts} current artifacts, {live_calls} audited calls, position carriage green")
    print(
        f"PASS production: {production_topics} topics, {production_artifacts} current artifacts, "
        f"{production_calls} audited calls; legacy runs remain explicitly incomplete, "
        "fresh runs require an exact RunPlan, bilingual semantic records, and hash-bound human gate"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
