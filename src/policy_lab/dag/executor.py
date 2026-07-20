"""Dependency-scoped, resumable execution of artifact-producing nodes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from policy_lab.dag.node import NodeSpec, compute_cache_key
from policy_lab.jsonio import write_json
from policy_lab.store.artifacts import ArtifactRef, ArtifactRepository
from policy_lab.store.events import EventLog, utc_now

RecordBuilder = Callable[[str], Sequence[dict[str, Any]]]


class NodeExecutionError(RuntimeError):
    """Raised when a node violates its declared input/output contract."""


class NodeExecutor:
    def __init__(
        self,
        *,
        repository: ArtifactRepository,
        run_dir: str | Path,
        source_root: str | Path,
        run_id: str,
        artifact_created_at: str,
    ):
        self.repository = repository
        self.run_dir = Path(run_dir)
        self.source_root = Path(source_root)
        self.run_id = run_id
        self.artifact_created_at = artifact_created_at
        self.events = EventLog(self.run_dir / "events.jsonl")

    def run(
        self,
        spec: NodeSpec,
        *,
        inputs: Mapping[str, tuple[ArtifactRef, ...]],
        builder: RecordBuilder,
        relevant_config: Mapping[str, Any] | None = None,
        provider: str | None = None,
        model: str | None = None,
        generation_parameters: Mapping[str, Any] | None = None,
    ) -> tuple[ArtifactRef, ...]:
        self._validate_inputs(spec, inputs)
        spec_hashes = self._hash_files(spec.spec_files)
        schema_hashes = self._hash_files(spec.schema_files)
        input_hashes = {
            binding: tuple(ref.content_hash for ref in refs)
            for binding, refs in inputs.items()
        }
        cache_key = compute_cache_key(
            spec,
            input_artifact_hashes=input_hashes,
            spec_hashes=spec_hashes,
            schema_hashes=schema_hashes,
            relevant_config=relevant_config or {},
            provider=provider,
            model=model,
            generation_parameters=generation_parameters or {},
        )
        cache_path = self.repository.root / "cache" / spec.name / f"{cache_key}.json"
        if cache_path.exists():
            cached = __import__("json").loads(cache_path.read_text(encoding="utf-8"))
            refs = tuple(
                self.repository.ref_by_hash(digest)
                for digest in cached["output_artifact_hashes"]
            )
            self._write_manifest(spec, cache_key, inputs, refs, "cache_hit")
            self.events.append(
                "node_cache_hit", run_id=self.run_id, node_id=spec.name,
                cache_key=cache_key, output_count=len(refs)
            )
            return refs

        self.events.append(
            "node_started", run_id=self.run_id, node_id=spec.name,
            cache_key=cache_key, input_count=sum(map(len, inputs.values()))
        )
        provenance_id = f"PV-{spec.name}-{cache_key[:16]}"
        provenance = {
            "id": provenance_id,
            "record_type": "provenance",
            "schema_version": "2.0.0",
            "topic": self._topic(inputs),
            "status": "candidate",
            "content": {
                "node_id": spec.name,
                "execution_id": cache_key,
                "input_artifact_hashes": sorted(
                    digest for values in input_hashes.values() for digest in values
                ),
                "spec_hashes": spec_hashes,
                "schema_hashes": schema_hashes,
                "prompt_hash": "0" * 64,
                "provider": provider or "local",
                "model": model or f"deterministic-{spec.version}",
                "role": spec.role,
            },
            "provenance_ref": None,
            "created_at": self.artifact_created_at,
            "supersedes": None,
        }
        self.repository.put(provenance)
        records = list(builder(provenance_id))
        refs = tuple(self.repository.put(record) for record in records)
        actual_types = tuple(sorted({ref.record_type for ref in refs}))
        unexpected = sorted(set(actual_types) - set(spec.output_types))
        if unexpected:
            raise NodeExecutionError(
                f"Node {spec.name} produced undeclared types: {unexpected}"
            )
        write_json(cache_path, {
            "cache_key": cache_key,
            "node_id": spec.name,
            "output_artifact_hashes": [ref.content_hash for ref in refs],
        })
        self._write_manifest(spec, cache_key, inputs, refs, "executed")
        self.events.append(
            "node_completed", run_id=self.run_id, node_id=spec.name,
            cache_key=cache_key, output_count=len(refs)
        )
        return refs

    def _topic(self, inputs: Mapping[str, tuple[ArtifactRef, ...]]) -> str:
        topics = {
            self.repository.get_by_hash(ref.content_hash)["topic"]
            for refs in inputs.values() for ref in refs
        }
        if len(topics) == 1:
            return topics.pop()
        configured = self.run_id.removeprefix("migration-")
        if configured:
            return configured
        raise NodeExecutionError("Cannot infer one topic for provenance")

    def _validate_inputs(
        self, spec: NodeSpec, inputs: Mapping[str, tuple[ArtifactRef, ...]]
    ) -> None:
        supplied_types = {ref.record_type for refs in inputs.values() for ref in refs}
        unexpected = supplied_types - set(spec.input_types)
        if unexpected:
            raise NodeExecutionError(
                f"Node {spec.name} received undeclared types: {sorted(unexpected)}"
            )

    def _hash_files(self, names: Sequence[str]) -> dict[str, str]:
        result = {}
        for name in names:
            path = self.source_root / name
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result

    def _write_manifest(
        self,
        spec: NodeSpec,
        cache_key: str,
        inputs: Mapping[str, tuple[ArtifactRef, ...]],
        outputs: tuple[ArtifactRef, ...],
        disposition: str,
    ) -> None:
        path = self.run_dir / "nodes" / f"{spec.name}.json"
        write_json(path, {
            "cache_key": cache_key,
            "completed_at": utc_now(),
            "disposition": disposition,
            "input_artifacts": {
                binding: [ref.content_hash for ref in refs]
                for binding, refs in inputs.items()
            },
            "node_id": spec.name,
            "node_version": spec.version,
            "output_artifacts": [
                {"content_hash": ref.content_hash, "id": ref.id,
                 "record_type": ref.record_type}
                for ref in outputs
            ],
            "run_id": self.run_id,
        })
