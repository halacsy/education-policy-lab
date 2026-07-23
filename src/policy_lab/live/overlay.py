"""Audited architecture-3.2 overlay over an immutable 3.0/3.1 snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from policy_lab.dag import DagNode, DagSpec, InputBinding, NodeExecutor, RootPort
from policy_lab.i18n import localized
from policy_lab.jsonio import content_hash, write_json
from policy_lab.live.dag_spec import VERSION as BASE_ARCHITECTURE_VERSION
from policy_lab.live.experiment import ArtifactDagRunner, _now
from policy_lab.store import ArtifactRef, ArtifactRepository


OVERLAY_VERSION = "3.2.0-overlay.1"
EVIDENCE_TYPES = ("finding", "assumption", "uncertainty")


def _schemas(*names: str) -> tuple[str, ...]:
    return (
        *(f"schemas/v2/{name}.schema.json" for name in names),
        "schemas/v2/bilingual.schema.json",
        "config/v2/bilingual_fields.json",
    )


def _node(
    node_id: str, *, kind: str, role: str, handler: str,
    inputs: tuple[InputBinding, ...], outputs: tuple[str, ...],
    schemas: tuple[str, ...], max_tokens: int | None = None,
) -> DagNode:
    return DagNode(
        id=node_id, version="1.0.0", kind=kind, role=role,
        stage="architecture_overlay", title=node_id.replace("_", " ").title(),
        description=(
            "Architecture-3.2 overlay node over exact source-architecture "
            "snapshot roots; it never mutates the source store."
        ),
        handler=handler, inputs=inputs, output_types=outputs,
        schema_files=schemas,
        provider="anthropic" if kind == "llm" else "local",
        model="claude-sonnet-5" if kind == "llm" else "deterministic-1.0.0",
        generation_parameters=(("max_tokens", max_tokens),) if max_tokens else (),
    )


def build_snapshot_overlay_dag() -> DagSpec:
    """Build the four-node overlay DAG with exact legacy artifacts as roots."""

    normalize = _node(
        "normalize_evidence", kind="llm", role="generator",
        handler="normalize_evidence",
        inputs=(
            InputBinding("problem", ("root:problem_brief",), ("problem_brief",), maximum=1),
            InputBinding("evidence", ("root:research_snapshot",), EVIDENCE_TYPES),
        ),
        outputs=("canonical_claim", "evidence_conflict", "coverage_ledger"),
        schemas=_schemas("canonical_claim", "evidence_conflict", "coverage_ledger"),
        max_tokens=30000,
    )
    seeds = _node(
        "derive_option_seeds", kind="llm", role="generator",
        handler="derive_option_seeds",
        inputs=(
            InputBinding("problem", ("root:problem_brief",), ("problem_brief",), maximum=1),
            InputBinding("normalized", ("normalize_evidence",), ("canonical_claim", "evidence_conflict")),
            InputBinding("evidence", ("root:research_snapshot",), EVIDENCE_TYPES),
        ),
        outputs=("option_seed",), schemas=_schemas("option_seed"),
        max_tokens=16000,
    )
    cluster = _node(
        "cluster_option_seeds", kind="llm", role="generator",
        handler="cluster_option_seeds",
        inputs=(
            InputBinding("problem", ("root:problem_brief",), ("problem_brief",), maximum=1),
            InputBinding("seeds", ("derive_option_seeds",), ("option_seed",)),
        ),
        outputs=("option_space_proposal", "coverage_ledger"),
        schemas=_schemas("option_space_proposal", "coverage_ledger"),
        max_tokens=12000,
    )
    compare = _node(
        "compare_to_v31", kind="deterministic", role="deterministic",
        handler="compare_to_v31",
        inputs=(
            InputBinding("normalized", ("normalize_evidence",), ("evidence_conflict", "coverage_ledger")),
            InputBinding("seeds", ("derive_option_seeds",), ("option_seed",)),
            InputBinding("candidate", ("cluster_option_seeds",), ("option_space_proposal", "coverage_ledger")),
            InputBinding("legacy_option_space", ("root:legacy_option_space",), ("approved_option_space",), maximum=1),
            InputBinding("legacy_proposals", ("root:legacy_proposals",), ("transformation_proposal",)),
        ),
        outputs=("architecture_overlay",), schemas=_schemas("architecture_overlay"),
    )
    dag = DagSpec(
        id="policy_analysis_snapshot_overlay", version=OVERLAY_VERSION,
        roots=(
            RootPort("problem_brief", ("problem_brief",)),
            RootPort("research_snapshot", EVIDENCE_TYPES, maximum=None),
            RootPort("legacy_option_space", ("approved_option_space",)),
            RootPort("legacy_proposals", ("transformation_proposal",), maximum=None),
        ),
        nodes=(normalize, seeds, cluster, compare),
    )
    dag.validate()
    return dag


@dataclass(frozen=True)
class SnapshotSelection:
    """Exact source-run artifacts admitted to one overlay."""

    source_root: Path
    source_run_tag: str
    source_architecture_version: str
    source_manifest_hash: str
    source_run_plan_hash: str
    problem_ref: ArtifactRef
    evidence_refs: tuple[ArtifactRef, ...]
    legacy_option_ref: ArtifactRef
    legacy_proposal_refs: tuple[ArtifactRef, ...]

    def roots(self) -> dict[str, tuple[ArtifactRef, ...]]:
        return {
            "problem_brief": (self.problem_ref,),
            "research_snapshot": self.evidence_refs,
            "legacy_option_space": (self.legacy_option_ref,),
            "legacy_proposals": self.legacy_proposal_refs,
        }

    def seed_refs(self) -> tuple[ArtifactRef, ...]:
        return (
            self.problem_ref, *self.evidence_refs, self.legacy_option_ref,
            *self.legacy_proposal_refs,
        )


def _manifest_output_ref(
    repository: ArtifactRepository, run_dir: Path, node_id: str,
    record_type: str, run_plan_hash: str,
) -> ArtifactRef:
    """Resolve one exact typed output through its source node manifest."""

    node_manifest = ArtifactDagRunner._load(
        run_dir / "nodes" / f"{node_id}.json"
    )
    if node_manifest.get("run_plan_hash") != run_plan_hash:
        raise ValueError(f"Source node manifest has wrong RunPlan at {node_id}")
    matches = [
        item for item in node_manifest["output_artifacts"]
        if item["record_type"] == record_type
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Source node {node_id} must emit exactly one {record_type}, "
            f"got {len(matches)}"
        )
    item = matches[0]
    ref = repository.ref_by_hash(item["content_hash"])
    if (ref.id, ref.record_type) != (item["id"], item["record_type"]):
        raise ValueError(f"Source node manifest differs from artifact at {node_id}")
    return ref


def select_source_snapshot(
    source_root: str | Path, source_run_tag: str,
) -> tuple[ArtifactRepository, SnapshotSelection]:
    """Resolve exact 3.0/3.1 research and comparison roots from a store."""

    source_root = Path(source_root)
    from policy_lab.schema_registry import SchemaRegistry

    schemas = SchemaRegistry(source_root.parents[3] / "schemas" / "v2")
    # Production roots normally live below the repository. Fall back to cwd
    # layout when a test fixture uses a different depth.
    if not (source_root.parents[3] / "schemas" / "v2").exists():
        schemas = SchemaRegistry(Path(__file__).resolve().parents[3] / "schemas" / "v2")
    repository = ArtifactRepository(source_root, schemas)
    manifest_path = source_root / "production_manifest.json"
    manifest = ArtifactDagRunner._load(manifest_path)
    source_architecture_version = manifest.get("architecture_version")
    if source_architecture_version not in {"3.0.0", "3.1.0"}:
        raise ValueError(
            "Snapshot overlay requires architecture 3.0.0 or 3.1.0, got "
            f"{source_architecture_version}"
        )
    plan_path = source_root / manifest["run_plan"]["path"]
    plan = ArtifactDagRunner._load(plan_path)
    if content_hash(plan) != manifest["run_plan"]["content_hash"]:
        raise ValueError("Source RunPlan hash differs from production manifest")

    run_dir = source_root / "runs" / manifest["run_id"]
    if source_architecture_version == "3.1.0":
        problem_meta = plan["roots"].get("problem_brief", [])
        if len(problem_meta) != 1:
            raise ValueError(
                "3.1 snapshot must contain exactly one problem brief root"
            )
        problem_ref = repository.ref_by_hash(problem_meta[0]["content_hash"])
    else:
        # Architecture 3.0 starts from a raw policy question. The admitted
        # problem brief is therefore selected through the human-gate node
        # manifest, whose RunPlan binding is checked above and below.
        problem_ref = _manifest_output_ref(
            repository, run_dir, "approve_problem_brief", "problem_brief",
            content_hash(plan),
        )

    evidence_refs: list[ArtifactRef] = []
    research_nodes = sorted(
        node["id"] for node in plan["nodes"] if node["id"].startswith("research_")
    )
    if len(research_nodes) != 12:
        raise ValueError(f"3.1 snapshot requires 12 research nodes, got {len(research_nodes)}")
    for node_id in research_nodes:
        node_manifest = ArtifactDagRunner._load(run_dir / "nodes" / f"{node_id}.json")
        if node_manifest.get("run_plan_hash") != content_hash(plan):
            raise ValueError(
                f"Source node manifest has wrong RunPlan at {node_id}"
            )
        for item in node_manifest["output_artifacts"]:
            if item["record_type"] not in EVIDENCE_TYPES:
                continue
            ref = repository.ref_by_hash(item["content_hash"])
            if (ref.id, ref.record_type) != (item["id"], item["record_type"]):
                raise ValueError(f"Source node manifest differs from artifact at {node_id}")
            evidence_refs.append(ref)
    if len({ref.id for ref in evidence_refs}) != len(evidence_refs):
        raise ValueError("Research snapshot contains duplicate semantic ids")

    topic = manifest["topic"]
    legacy_option = repository.get_current(f"AO-live-{topic}")
    legacy_option_ref = repository.ref_by_hash(content_hash(legacy_option))
    legacy_proposal_refs = tuple(
        repository.ref_by_hash(content_hash(record))
        for record in repository.list(record_type="transformation_proposal")
    )
    selection = SnapshotSelection(
        source_root=source_root, source_run_tag=source_run_tag,
        source_architecture_version=source_architecture_version,
        source_manifest_hash=content_hash(manifest),
        source_run_plan_hash=content_hash(plan), problem_ref=problem_ref,
        evidence_refs=tuple(evidence_refs), legacy_option_ref=legacy_option_ref,
        legacy_proposal_refs=legacy_proposal_refs,
    )
    return repository, selection


def select_v31_snapshot(
    source_root: str | Path, source_run_tag: str,
) -> tuple[ArtifactRepository, SnapshotSelection]:
    """Backward-compatible name for the version-aware snapshot selector."""

    repository, selection = select_source_snapshot(source_root, source_run_tag)
    if selection.source_architecture_version != "3.1.0":
        raise ValueError(
            "select_v31_snapshot requires architecture 3.1.0, got "
            f"{selection.source_architecture_version}"
        )
    return repository, selection


def import_transitive_closure(
    source: ArtifactRepository, target: ArtifactRepository,
    refs: Iterable[ArtifactRef],
) -> int:
    """Copy exact inputs, typed dependencies, and audited successor chains.

    A source node manifest can legitimately point to an immutable monolingual
    predecessor while the published store exposes an audited bilingual
    successor. The overlay still binds the predecessor hash as its exact
    analytical input, but its isolated store must also preserve the complete
    successor chain so the same canonical current record remains current.
    """

    records = source.list(include_superseded=True)
    by_hash = {content_hash(record): record for record in records}
    versions_by_id: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        versions_by_id.setdefault(record["id"], []).append(record)
    current_by_id: dict[str, dict[str, Any]] = {}
    successor_by_hash: dict[str, dict[str, Any]] = {}
    for record_id, versions in versions_by_id.items():
        for record in versions:
            predecessor = record.get("supersedes")
            if predecessor is None:
                continue
            if predecessor in successor_by_hash:
                raise ValueError(
                    f"Source snapshot has branching successors for {predecessor}"
                )
            successor_by_hash[predecessor] = record
        superseded = {
            record["supersedes"] for record in versions
            if record.get("supersedes") is not None
        }
        current = [
            record for record in versions
            if content_hash(record) not in superseded
        ]
        if len(current) != 1:
            raise ValueError(
                f"Source snapshot has {len(current)} current versions for {record_id}"
            )
        current_by_id[record_id] = current[0]

    pending = [ref.content_hash for ref in refs]
    copied: set[str] = set()
    while pending:
        digest = pending.pop()
        if digest in copied:
            continue
        try:
            record = by_hash[digest]
        except KeyError as exc:
            raise ValueError(f"Snapshot dependency hash is missing: {digest}") from exc
        target.put(record)
        copied.add(digest)
        predecessor = record.get("supersedes")
        if predecessor:
            pending.append(predecessor)
        successor = successor_by_hash.get(digest)
        if successor is not None:
            pending.append(content_hash(successor))
        for reference in source.schemas.references(record):
            try:
                dependency = current_by_id[reference.target_id]
            except KeyError as exc:
                raise ValueError(
                    f"Snapshot reference target is missing: {reference.target_id}"
                ) from exc
            dependency_hash = content_hash(dependency)
            pending.append(dependency_hash)
    return len(copied)


def build_trace_overlap_content(
    *, source: SnapshotSelection, legacy_option: dict[str, Any],
    legacy_proposals: list[dict[str, Any]], seeds: list[dict[str, Any]],
    conflicts: list[dict[str, Any]], new_option: dict[str, Any],
    normalization_coverage_ref: str, seed_coverage_ref: str,
) -> dict[str, Any]:
    """Compare exact finding lineage; never claim semantic equivalence."""

    old_directions = legacy_option["content"]["directions"]
    old_direction_findings = {
        item["id"]: set(item.get("finding_refs", [])) for item in old_directions
    }
    proposal_findings = {
        item["id"]: set(item["content"]["finding_refs"])
        for item in legacy_proposals
    }
    seed_by_id = {item["id"]: item for item in seeds}

    def overlaps(findings: set[str]) -> tuple[list[str], list[str], list[str]]:
        directions = sorted(
            key for key, values in old_direction_findings.items()
            if findings.intersection(values)
        )
        proposals = sorted(
            key for key, values in proposal_findings.items()
            if findings.intersection(values)
        )
        shared = sorted(
            finding for finding in findings
            if any(finding in values for values in (*old_direction_findings.values(), *proposal_findings.values()))
        )
        return directions, proposals, shared

    seed_entries = []
    for seed in seeds:
        directions, proposals, shared = overlaps(set(seed["content"]["finding_refs"]))
        status = (
            "covered_by_proposal" if proposals
            else "legacy_direction_only" if directions
            else "uncovered"
        )
        seed_entries.append({
            "option_seed_ref": seed["id"], "status": status,
            "legacy_direction_ids": directions,
            "legacy_proposal_refs": proposals,
            "overlap_finding_refs": shared,
            "rationale": localized(
                f"Trace overlap found {len(proposals)} legacy proposals and {len(directions)} legacy directions through {len(shared)} exact finding ids.",
                f"A nyomvonal-átfedés {len(proposals)} régi javaslatot és {len(directions)} régi irányt talált {len(shared)} pontos findingazonosítón keresztül.",
            ),
        })

    direction_entries = []
    for direction in new_option["content"]["directions"]:
        findings = {
            finding
            for seed_id in direction["option_seed_refs"]
            for finding in seed_by_id[seed_id]["content"]["finding_refs"]
        }
        directions, proposals, shared = overlaps(findings)
        status = (
            "covered_by_proposal" if proposals
            else "legacy_direction_only" if directions
            else "novel_gap"
        )
        direction_entries.append({
            "direction_id": direction["id"], "status": status,
            "legacy_direction_ids": directions,
            "legacy_proposal_refs": proposals,
            "overlap_finding_refs": shared,
            "rationale": localized(
                f"The new direction shares exact finding lineage with {len(proposals)} legacy proposals and {len(directions)} legacy directions.",
                f"Az új irány pontos finding-nyomvonala {len(proposals)} régi javaslattal és {len(directions)} régi iránnyal közös.",
            ),
        })

    conflict_entries = []
    for conflict in conflicts:
        _, proposals, shared = overlaps(set(conflict["content"]["finding_refs"]))
        conflict_entries.append({
            "evidence_conflict_ref": conflict["id"],
            "status": "touches_legacy_proposal" if proposals else "no_legacy_proposal",
            "legacy_proposal_refs": proposals,
            "overlap_finding_refs": shared,
            "rationale": localized(
                f"The conflict touches {len(proposals)} legacy proposals through {len(shared)} exact finding ids.",
                f"A konfliktus {len(proposals)} régi javaslatot érint {len(shared)} pontos findingazonosítón keresztül.",
            ),
        })

    return {
        "mode": "trace_overlap",
        "source_architecture_version": source.source_architecture_version,
        "source_run_tag": source.source_run_tag,
        "source_manifest_hash": source.source_manifest_hash,
        "source_run_plan_hash": source.source_run_plan_hash,
        "legacy_option_space_ref": legacy_option["id"],
        "new_option_space_ref": new_option["id"],
        "normalization_coverage_ref": normalization_coverage_ref,
        "seed_coverage_ref": seed_coverage_ref,
        "seed_entries": seed_entries,
        "direction_entries": direction_entries,
        "conflict_entries": conflict_entries,
        "summary": {
            "seed_count": len(seed_entries),
            "uncovered_seed_count": sum(item["status"] == "uncovered" for item in seed_entries),
            "new_direction_count": len(direction_entries),
            "novel_gap_count": sum(item["status"] == "novel_gap" for item in direction_entries),
            "evidence_conflict_count": len(conflict_entries),
            "conflicts_without_legacy_proposal_count": sum(
                item["status"] == "no_legacy_proposal" for item in conflict_entries
            ),
        },
        "limitation": localized(
            "This overlay measures shared exact finding lineage, not semantic equivalence, current evidence freshness, or policy quality. It is an internal architecture comparison and not a new production decision package.",
            "Ez az overlay a pontos finding-nyomvonal közösségét méri, nem a szemantikai azonosságot, a bizonyítékok jelenlegi frissességét vagy a szakpolitikai minőséget. Belső architektúra-összehasonlítás, nem új produkciós döntési csomag.",
        ),
    }


class SnapshotOverlayRunner(ArtifactDagRunner):
    """Run only the new 3.2 middle layer over exact 3.0/3.1 roots."""

    def repair_existing_attempt_provenance(self) -> dict[str, Any]:
        """Repair exact-attempt carriage without executing any DAG node."""

        manifest = self._load(self.output_root / "overlay_manifest.json")
        plan = self._load(self.output_root / manifest["run_plan"]["path"])
        run_dir = self.output_root / "runs" / manifest["run_id"]
        executor = NodeExecutor(
            repository=self.repository, run_dir=run_dir, source_root=self.root,
            run_id=manifest["run_id"], artifact_created_at=self.created_at,
            topic=self.topic,
            run_plan_hash=manifest["run_plan"]["content_hash"],
        )
        self._repair_missing_attempt_provenance(
            executor, run_dir,
            tuple(node["id"] for node in plan["nodes"] if node["kind"] == "llm"),
        )
        self.repository.validate_graph((manifest["overlay_ref"],))
        return manifest

    def run_overlay(self, *, source_root: str | Path, source_run_tag: str) -> dict[str, Any]:
        source_repository, snapshot = select_source_snapshot(
            source_root, source_run_tag
        )
        imported = import_transitive_closure(
            source_repository, self.repository, snapshot.seed_refs()
        )
        dag = build_snapshot_overlay_dag()
        plan = dag.compile(topic=self.topic, root_artifacts=snapshot.roots())
        source_short = snapshot.source_architecture_version.replace(".", "")[:2]
        run_id = f"overlay-{self.topic}-v{source_short}-to-v32"
        run_dir = self.output_root / "runs" / run_id
        plan_path = run_dir / "run_plan.json"
        if plan_path.exists():
            if self._load(plan_path) != plan.as_dict():
                raise ValueError(f"Overlay RunPlan changed for {run_id}; use a new output root")
        else:
            plan.write(plan_path)
        executor = NodeExecutor(
            repository=self.repository, run_dir=run_dir, source_root=self.root,
            run_id=run_id, artifact_created_at=self.created_at, topic=self.topic,
            run_plan_hash=plan.hash,
        )
        outputs: dict[str, tuple[ArtifactRef, ...]] = {}
        common = {
            "topic": self.topic, "run_plan_hash": plan.hash,
            "source_manifest_hash": snapshot.source_manifest_hash,
            "source_run_plan_hash": snapshot.source_run_plan_hash,
        }

        node = plan.node("normalize_evidence")
        inputs = plan.resolve_inputs(node.id, outputs)
        outputs[node.id] = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=common,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("normalize_evidence_v1"),
            builder=lambda pv: self._normalize_evidence_records(
                inputs["problem"][0], inputs["evidence"], pv,
                node=node.id, run_dir=run_dir, arm="overlay",
            ),
        )
        self._report_node(run_dir, node.id)

        node = plan.node("derive_option_seeds")
        inputs = plan.resolve_inputs(node.id, outputs)
        outputs[node.id] = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=common,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("derive_option_seeds_v1"),
            builder=lambda pv: self._option_seed_records(
                inputs["problem"][0], inputs["normalized"], inputs["evidence"], pv,
                node=node.id, run_dir=run_dir, arm="overlay",
            ),
        )
        self._report_node(run_dir, node.id)

        node = plan.node("cluster_option_seeds")
        inputs = plan.resolve_inputs(node.id, outputs)

        def overlay_cluster(provenance: str) -> list[dict[str, Any]]:
            records = self._cluster_option_seed_records(
                inputs["problem"][0], inputs["seeds"], provenance,
                node=node.id, run_dir=run_dir, arm="overlay",
            )
            for record in records:
                if record["record_type"] == "option_space_proposal":
                    record["id"] = f"OS-overlay-{self.topic}"
                elif record["record_type"] == "coverage_ledger":
                    record["id"] = "CL-overlay-option-seeds"
            return records

        outputs[node.id] = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=common,
            provider=node.provider, model=node.model,
            generation_parameters=dict(node.generation_parameters),
            prompt_hash=self._contract_hash("cluster_option_seeds_v1"),
            builder=overlay_cluster,
        )
        self._report_node(run_dir, node.id)

        node = plan.node("compare_to_v31")
        inputs = plan.resolve_inputs(node.id, outputs)

        def comparison_record(provenance: str) -> list[dict[str, Any]]:
            normalized = [
                self.repository.get_by_hash(ref.content_hash)
                for ref in inputs["normalized"]
            ]
            candidates = [
                self.repository.get_by_hash(ref.content_hash)
                for ref in inputs["candidate"]
            ]
            normalization_ledger = next(
                record for record in normalized
                if record["record_type"] == "coverage_ledger"
            )
            seed_ledger = next(
                record for record in candidates
                if record["record_type"] == "coverage_ledger"
            )
            new_option = next(
                record for record in candidates
                if record["record_type"] == "option_space_proposal"
            )
            content = build_trace_overlap_content(
                source=snapshot,
                legacy_option=self.repository.get_by_hash(
                    inputs["legacy_option_space"][0].content_hash
                ),
                legacy_proposals=[
                    self.repository.get_by_hash(ref.content_hash)
                    for ref in inputs["legacy_proposals"]
                ],
                seeds=[
                    self.repository.get_by_hash(ref.content_hash)
                    for ref in inputs["seeds"]
                ],
                conflicts=[
                    record for record in normalized
                    if record["record_type"] == "evidence_conflict"
                ],
                new_option=new_option,
                normalization_coverage_ref=normalization_ledger["id"],
                seed_coverage_ref=seed_ledger["id"],
            )
            return [self._record(
                f"OV-{self.topic}-v{source_short}-to-v32",
                "architecture_overlay",
                provenance, content,
            )]

        outputs[node.id] = executor.run(
            node.node_spec(), inputs=inputs, relevant_config=common,
            provider=node.provider, model=node.model,
            generation_parameters={},
            prompt_hash=content_hash({"handler": "compare_to_v31", "version": "1.0.0"}),
            builder=comparison_record,
        )
        self._report_node(run_dir, node.id)
        plan.assert_complete(outputs)
        self._repair_missing_attempt_provenance(
            executor, run_dir,
            tuple(
                planned.id for planned in plan.nodes
                if planned.kind == "llm"
            ),
        )
        overlay_ref = outputs[node.id][0]
        self.repository.validate_graph((overlay_ref.id,))
        overlay = self.repository.get_by_hash(overlay_ref.content_hash)
        self._write_cost_report()
        manifest = {
            "architecture_version": OVERLAY_VERSION,
            "base_architecture_version": BASE_ARCHITECTURE_VERSION,
            "topic": self.topic, "run_id": run_id,
            "run_plan": {"content_hash": plan.hash, "path": f"runs/{run_id}/run_plan.json"},
            "source": {
                "architecture_version": snapshot.source_architecture_version,
                "run_tag": source_run_tag,
                "manifest_hash": snapshot.source_manifest_hash,
                "run_plan_hash": snapshot.source_run_plan_hash,
                "imported_artifact_count": imported,
                "research_artifact_count": len(snapshot.evidence_refs),
            },
            "overlay_ref": overlay_ref.id,
            "overlay_hash": overlay_ref.content_hash,
            "summary": overlay["content"]["summary"],
            "completed_at": _now(),
        }
        write_json(self.output_root / "overlay_manifest.json", manifest)
        return manifest

    def _repair_missing_attempt_provenance(
        self, executor: NodeExecutor, run_dir: Path, node_ids: tuple[str, ...],
    ) -> None:
        """Adopt one unambiguous historical attempt set after exact replay.

        Early overlay execution predated cross-cache-key attempt adoption.
        This deterministic repair enriches only provenance records that have
        no attempts and for which exactly one completed historical execution
        exists. It never changes semantic output content.
        """

        repairs = []
        for node_id in node_ids:
            manifest_path = run_dir / "nodes" / f"{node_id}.json"
            manifest = self._load(manifest_path)
            provenance_ids = {
                self.repository.get_by_hash(item["content_hash"])["provenance_ref"]
                for item in manifest["output_artifacts"]
            }
            if len(provenance_ids) != 1:
                raise ValueError(f"{node_id} outputs do not share one provenance")
            provenance = self.repository.get_current(provenance_ids.pop())
            if provenance["content"].get("attempts"):
                continue
            execution_id = provenance["content"]["execution_id"]
            attempts_root = run_dir / "attempts" / node_id
            sources = [
                path for path in attempts_root.iterdir()
                if path.is_dir() and path.name != execution_id
                and (path / "index.jsonl").exists()
            ]
            if len(sources) != 1:
                raise ValueError(
                    f"Cannot unambiguously recover attempts for {node_id}: "
                    f"{[path.name for path in sources]}"
                )
            current_path = attempts_root / "current.json"
            write_json(current_path, {"execution_id": execution_id})
            try:
                entries = [
                    json.loads(line)
                    for line in (sources[0] / "index.jsonl").read_text(
                        encoding="utf-8"
                    ).splitlines()
                    if line.strip()
                ]
                for entry in entries:
                    leaf = (
                        sources[0]
                        / f"{entry['stage']}-{entry['prompt_hash'][:16]}"
                    )
                    prompt = (leaf / "prompt.md").read_text(encoding="utf-8")
                    responses = list(leaf.glob("response.*"))
                    if len(responses) != 1:
                        raise ValueError(f"Ambiguous response files in {leaf}")
                    self._persist_attempt(
                        run_dir, node_id, entry["stage"], prompt,
                        responses[0].read_bytes(),
                        responses[0].suffix.removeprefix("."),
                    )
            finally:
                if current_path.exists():
                    current_path.unlink()
            attempts = executor._attempts(node_id, execution_id)
            if not attempts:
                raise ValueError(f"Attempt recovery produced no index for {node_id}")
            enriched = dict(provenance)
            enriched["content"] = {
                **provenance["content"], "attempts": attempts,
            }
            enriched["supersedes"] = content_hash(provenance)
            self.repository.put(enriched)
            repairs.append({
                "node_id": node_id,
                "source_execution_id": sources[0].name,
                "target_execution_id": execution_id,
                "attempt_count": len(attempts),
            })
        if repairs:
            write_json(run_dir / "attempt_recovery.json", {
                "repair": "adopt_exact_replayed_attempts",
                "actions": repairs,
            })
