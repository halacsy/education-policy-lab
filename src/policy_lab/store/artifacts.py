"""Immutable content-addressed JSON artifact repository."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from policy_lab.jsonio import canonical_json_bytes, content_hash
from policy_lab.schema_registry import ArtifactReference, SchemaRegistry


class GraphIntegrityError(ValueError):
    """Raised when semantic ids or artifact references are inconsistent."""


@dataclass(frozen=True)
class ArtifactRef:
    id: str
    record_type: str
    content_hash: str
    path: Path


@dataclass(frozen=True)
class _StoredArtifact:
    ref: ArtifactRef
    record: dict[str, Any]


class ArtifactRepository:
    """Store immutable records and query their typed reference graph."""

    def __init__(self, root: str | Path, schemas: SchemaRegistry):
        self.root = Path(root)
        self.artifact_dir = self.root / "artifacts"
        self.schemas = schemas

    def put(self, record: dict[str, Any]) -> ArtifactRef:
        self.schemas.validate(record)
        payload = canonical_json_bytes(record)
        digest = content_hash(record)
        path = self._path_for_hash(digest)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            if path.read_bytes() != payload:
                raise GraphIntegrityError(
                    f"Content-hash collision or mutated artifact at {path}"
                )
        else:
            self._atomic_write(path, payload)

        return ArtifactRef(
            id=record["id"],
            record_type=record["record_type"],
            content_hash=digest,
            path=path,
        )

    def get_by_hash(self, digest: str) -> dict[str, Any]:
        path = self._path_for_hash(digest)
        if not path.exists():
            raise KeyError(f"Unknown artifact hash: {digest}")
        record = json.loads(path.read_text(encoding="utf-8"))
        self.schemas.validate(record)
        if content_hash(record) != digest:
            raise GraphIntegrityError(f"Artifact content does not match path: {path}")
        return record

    def get_current(self, record_id: str) -> dict[str, Any]:
        stored = [item for item in self._iter_stored() if item.ref.id == record_id]
        if not stored:
            raise KeyError(f"Unknown semantic artifact id: {record_id}")
        superseded = {
            item.record["supersedes"]
            for item in stored
            if item.record.get("supersedes") is not None
        }
        current = [item for item in stored if item.ref.content_hash not in superseded]
        if len(current) != 1:
            hashes = [item.ref.content_hash for item in current]
            raise GraphIntegrityError(
                f"Semantic id {record_id} has {len(current)} current versions: {hashes}"
            )
        return current[0].record

    def get_version(self, record_id: str, digest: str) -> dict[str, Any]:
        record = self.get_by_hash(digest)
        if record["id"] != record_id:
            raise KeyError(f"Hash {digest} does not belong to {record_id}")
        return record

    def list(
        self,
        *,
        record_type: str | None = None,
        topic: str | None = None,
        status: str | None = None,
        include_superseded: bool = False,
    ) -> list[dict[str, Any]]:
        records = []
        items = (
            self._iter_stored()
            if include_superseded
            else iter(self._current_artifacts().values())
        )
        for item in items:
            record = item.record
            if record_type is not None and record["record_type"] != record_type:
                continue
            if topic is not None and record["topic"] != topic:
                continue
            if status is not None and record["status"] != status:
                continue
            records.append(record)
        return sorted(records, key=lambda record: (record["record_type"], record["id"]))

    def outgoing(
        self, record_id: str, relation_type: str | None = None
    ) -> tuple[ArtifactReference, ...]:
        record = self.get_current(record_id)
        refs = self.schemas.references(record)
        if relation_type is None:
            return refs
        return tuple(ref for ref in refs if ref.field == relation_type)

    def incoming(
        self, record_id: str, relation_type: str | None = None
    ) -> tuple[tuple[str, ArtifactReference], ...]:
        matches = []
        for item in self._current_artifacts().values():
            for ref in self.schemas.references(item.record):
                if ref.target_id != record_id:
                    continue
                if relation_type is not None and ref.field != relation_type:
                    continue
                matches.append((item.ref.id, ref))
        return tuple(sorted(matches, key=lambda pair: (pair[0], pair[1].field)))

    def lineage(self, record_id: str) -> tuple[ArtifactRef, ...]:
        stored = {item.ref.content_hash: item for item in self._iter_stored()}
        current = self.get_current(record_id)
        digest = content_hash(current)
        lineage = []
        seen = set()
        while digest:
            if digest in seen:
                raise GraphIntegrityError(f"Cycle in supersedes chain for {record_id}")
            seen.add(digest)
            try:
                item = stored[digest]
            except KeyError as exc:
                raise GraphIntegrityError(
                    f"Missing superseded artifact hash {digest} for {record_id}"
                ) from exc
            if item.ref.id != record_id:
                raise GraphIntegrityError(
                    f"Supersedes chain crosses semantic ids at {digest}"
                )
            lineage.append(item.ref)
            digest = item.record.get("supersedes")
        return tuple(lineage)

    def validate_graph(self, root_ids: tuple[str, ...] | None = None) -> None:
        current = self._current_artifacts()
        if root_ids is not None:
            missing_roots = sorted(set(root_ids) - set(current))
            if missing_roots:
                raise GraphIntegrityError(f"Missing graph roots: {missing_roots}")

        for item in current.values():
            self.lineage(item.ref.id)
            for ref in self.schemas.references(item.record):
                target = current.get(ref.target_id)
                if target is None:
                    raise GraphIntegrityError(
                        f"{item.ref.id} references missing {ref.target_type} "
                        f"artifact {ref.target_id} at {ref.field}"
                    )
                if target.ref.record_type != ref.target_type:
                    raise GraphIntegrityError(
                        f"{item.ref.id} expects {ref.target_type} at {ref.field}, "
                        f"but {ref.target_id} is {target.ref.record_type}"
                    )

    def _current_artifacts(self) -> dict[str, _StoredArtifact]:
        by_id: dict[str, list[_StoredArtifact]] = {}
        for item in self._iter_stored():
            by_id.setdefault(item.ref.id, []).append(item)
        current = {}
        for record_id, versions in by_id.items():
            superseded = {
                item.record["supersedes"]
                for item in versions
                if item.record.get("supersedes") is not None
            }
            candidates = [
                item for item in versions if item.ref.content_hash not in superseded
            ]
            if len(candidates) != 1:
                raise GraphIntegrityError(
                    f"Semantic id {record_id} has {len(candidates)} current versions"
                )
            current[record_id] = candidates[0]
        return current

    def _iter_stored(self) -> Iterator[_StoredArtifact]:
        if not self.artifact_dir.exists():
            return
        for path in sorted(self.artifact_dir.glob("*/*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            self.schemas.validate(record)
            digest = path.stem
            if content_hash(record) != digest:
                raise GraphIntegrityError(f"Artifact content does not match path: {path}")
            yield _StoredArtifact(
                ref=ArtifactRef(
                    id=record["id"],
                    record_type=record["record_type"],
                    content_hash=digest,
                    path=path,
                ),
                record=record,
            )

    def _path_for_hash(self, digest: str) -> Path:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"Invalid SHA-256 digest: {digest}")
        return self.artifact_dir / digest[:2] / f"{digest}.json"

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
