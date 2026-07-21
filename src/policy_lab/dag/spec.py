"""Declarative DAG specifications and immutable, topic-bound run plans."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from policy_lab.jsonio import content_hash, write_json
from policy_lab.dag.node import NodeSpec
from policy_lab.store.artifacts import ArtifactRef


class DagSpecError(ValueError):
    """Raised when a declarative graph or compiled run plan is inconsistent."""


class HumanGatePending(RuntimeError):
    """Raised when execution reaches a declared human gate without a decision."""

    def __init__(self, gate_id: str, candidate_hash: str, request_path: Path):
        self.gate_id = gate_id
        self.candidate_hash = candidate_hash
        self.request_path = request_path
        super().__init__(
            f"Human gate {gate_id} is pending for {candidate_hash}; "
            f"review {request_path}"
        )


@dataclass(frozen=True)
class RootPort:
    """One externally admitted artifact collection accepted by a DAG."""

    name: str
    record_types: tuple[str, ...]
    minimum: int = 1
    maximum: int | None = 1

    @property
    def source_id(self) -> str:
        return f"root:{self.name}"


@dataclass(frozen=True)
class InputBinding:
    """A named input assembled from exact upstream output or root ports."""

    name: str
    sources: tuple[str, ...]
    record_types: tuple[str, ...]
    minimum: int = 1
    maximum: int | None = None


@dataclass(frozen=True)
class DagNode:
    """One declarative node in the logical execution graph."""

    id: str
    version: str
    kind: str
    role: str
    stage: str
    title: str
    description: str
    handler: str
    inputs: tuple[InputBinding, ...]
    output_types: tuple[str, ...]
    schema_files: tuple[str, ...] = ()
    spec_files: tuple[str, ...] = ()
    config_keys: tuple[str, ...] = ()
    provider: str = "local"
    model: str = "deterministic"
    generation_parameters: tuple[tuple[str, Any], ...] = ()

    def node_spec(self) -> NodeSpec:
        """Project the declarative node into the executor's local contract."""

        return NodeSpec(
            name=self.id,
            version=self.version,
            input_types=tuple(sorted({value for item in self.inputs for value in item.record_types})),
            output_types=self.output_types,
            spec_files=self.spec_files,
            schema_files=self.schema_files,
            config_keys=self.config_keys,
            role=self.role,
            validator=self.handler,
        )

    def as_plan_dict(self) -> dict[str, Any]:
        return {
            "config_keys": list(self.config_keys),
            "description": self.description,
            "generation_parameters": dict(self.generation_parameters),
            "handler": self.handler,
            "id": self.id,
            "inputs": [
                {
                    "maximum": binding.maximum,
                    "minimum": binding.minimum,
                    "name": binding.name,
                    "record_types": list(binding.record_types),
                    "sources": list(binding.sources),
                }
                for binding in self.inputs
            ],
            "kind": self.kind,
            "model": self.model,
            "output_types": list(self.output_types),
            "provider": self.provider,
            "role": self.role,
            "schema_files": list(self.schema_files),
            "spec_files": list(self.spec_files),
            "stage": self.stage,
            "title": self.title,
            "version": self.version,
        }


@dataclass(frozen=True)
class DagSpec:
    """The versioned logical source of truth for one executable workflow."""

    id: str
    version: str
    roots: tuple[RootPort, ...]
    nodes: tuple[DagNode, ...]

    def validate(self) -> None:
        root_by_source = {root.source_id: root for root in self.roots}
        if len(root_by_source) != len(self.roots):
            raise DagSpecError("DAG root port names must be unique")
        node_by_id = {node.id: node for node in self.nodes}
        if len(node_by_id) != len(self.nodes):
            raise DagSpecError("DAG node ids must be unique")

        produced_types: dict[str, set[str]] = {
            source: set(root.record_types) for source, root in root_by_source.items()
        }
        for node in self.nodes:
            if not node.output_types:
                raise DagSpecError(f"Node {node.id} declares no output types")
            if len({binding.name for binding in node.inputs}) != len(node.inputs):
                raise DagSpecError(f"Node {node.id} has duplicate input binding names")
            for binding in node.inputs:
                if binding.maximum is not None and binding.maximum < binding.minimum:
                    raise DagSpecError(
                        f"Node {node.id} input {binding.name} has invalid cardinality"
                    )
                for source in binding.sources:
                    if source not in produced_types:
                        if source in node_by_id:
                            raise DagSpecError(
                                f"Node {node.id} depends on later node {source}; "
                                "nodes must be topologically ordered"
                            )
                        raise DagSpecError(
                            f"Node {node.id} input {binding.name} has unknown source {source}"
                        )
                    if not produced_types[source].intersection(binding.record_types):
                        raise DagSpecError(
                            f"Node {node.id} input {binding.name} cannot select any "
                            f"declared output from {source}"
                        )
            produced_types[node.id] = set(node.output_types)

        self._validate_acyclic(node_by_id)

    def _validate_acyclic(self, node_by_id: Mapping[str, DagNode]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visited:
                return
            if node_id in visiting:
                raise DagSpecError(f"Cycle detected at node {node_id}")
            visiting.add(node_id)
            for binding in node_by_id[node_id].inputs:
                for source in binding.sources:
                    if source in node_by_id:
                        visit(source)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in node_by_id:
            visit(node_id)

    def compile(
        self,
        *,
        topic: str,
        root_artifacts: Mapping[str, tuple[ArtifactRef, ...]],
    ) -> "RunPlan":
        self.validate()
        supplied = set(root_artifacts)
        expected = {root.name for root in self.roots}
        if supplied != expected:
            raise DagSpecError(
                f"Root ports differ: expected {sorted(expected)}, got {sorted(supplied)}"
            )
        roots: dict[str, tuple[ArtifactRef, ...]] = {}
        for root in self.roots:
            refs = tuple(root_artifacts[root.name])
            if len(refs) < root.minimum or (
                root.maximum is not None and len(refs) > root.maximum
            ):
                raise DagSpecError(
                    f"Root {root.name} requires {root.minimum}-"
                    f"{root.maximum if root.maximum is not None else 'many'} artifacts, "
                    f"got {len(refs)}"
                )
            unexpected = {ref.record_type for ref in refs} - set(root.record_types)
            if unexpected:
                raise DagSpecError(
                    f"Root {root.name} received unexpected types: {sorted(unexpected)}"
                )
            roots[root.name] = refs
        plan = RunPlan(
            dag_id=self.id,
            dag_version=self.version,
            topic=topic,
            roots=roots,
            nodes=self.nodes,
        )
        plan.validate()
        return plan


@dataclass(frozen=True)
class RunPlan:
    """An immutable concrete plan compiled for one topic and exact roots."""

    dag_id: str
    dag_version: str
    topic: str
    roots: Mapping[str, tuple[ArtifactRef, ...]]
    nodes: tuple[DagNode, ...]

    def validate(self) -> None:
        root_sources = {f"root:{name}" for name in self.roots}
        node_ids = {node.id for node in self.nodes}
        for node in self.nodes:
            for binding in node.inputs:
                unknown = set(binding.sources) - root_sources - node_ids
                if unknown:
                    raise DagSpecError(
                        f"Node {node.id} has unknown run-plan sources: {sorted(unknown)}"
                    )
        for name, refs in self.roots.items():
            for ref in refs:
                if len(ref.content_hash) != 64:
                    raise DagSpecError(f"Root {name} has invalid hash for {ref.id}")

    @property
    def hash(self) -> str:
        return content_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        edges = []
        for node in self.nodes:
            for binding in node.inputs:
                for source in binding.sources:
                    edges.append(
                        {
                            "binding": binding.name,
                            "from": source,
                            "record_types": list(binding.record_types),
                            "to": node.id,
                        }
                    )
        return {
            "dag_id": self.dag_id,
            "dag_version": self.dag_version,
            "edges": edges,
            "nodes": [node.as_plan_dict() for node in self.nodes],
            "roots": {
                name: [
                    {
                        "content_hash": ref.content_hash,
                        "id": ref.id,
                        "record_type": ref.record_type,
                    }
                    for ref in refs
                ]
                for name, refs in sorted(self.roots.items())
            },
            "schema_version": "1.0.0",
            "topic": self.topic,
        }

    def write(self, path: str | Path) -> None:
        self.validate()
        write_json(path, self.as_dict())

    def node(self, node_id: str) -> DagNode:
        try:
            return next(node for node in self.nodes if node.id == node_id)
        except StopIteration as exc:
            raise DagSpecError(f"Unknown run-plan node: {node_id}") from exc

    def resolve_inputs(
        self,
        node_id: str,
        outputs: Mapping[str, tuple[ArtifactRef, ...]],
    ) -> dict[str, tuple[ArtifactRef, ...]]:
        node = self.node(node_id)
        resolved: dict[str, tuple[ArtifactRef, ...]] = {}
        for binding in node.inputs:
            refs: list[ArtifactRef] = []
            for source in binding.sources:
                if source.startswith("root:"):
                    source_refs = self.roots[source.removeprefix("root:")]
                else:
                    try:
                        source_refs = outputs[source]
                    except KeyError as exc:
                        raise DagSpecError(
                            f"Node {node_id} is not ready; source {source} has no outputs"
                        ) from exc
                refs.extend(
                    ref for ref in source_refs if ref.record_type in binding.record_types
                )
            if len(refs) < binding.minimum or (
                binding.maximum is not None and len(refs) > binding.maximum
            ):
                raise DagSpecError(
                    f"Node {node_id} input {binding.name} resolved {len(refs)} "
                    f"artifacts; expected {binding.minimum}-"
                    f"{binding.maximum if binding.maximum is not None else 'many'}"
                )
            resolved[binding.name] = tuple(refs)
        return resolved

    def assert_complete(self, outputs: Mapping[str, tuple[ArtifactRef, ...]]) -> None:
        missing = [node.id for node in self.nodes if node.id not in outputs]
        unknown = sorted(set(outputs) - {node.id for node in self.nodes})
        if missing or unknown:
            raise DagSpecError(
                f"Run-plan execution differs: missing={missing}, unknown={unknown}"
            )
