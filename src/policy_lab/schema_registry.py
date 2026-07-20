"""Versioned JSON Schema registry for canonical v2 artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

TECHNICAL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class SchemaValidationError(ValueError):
    """Raised when an artifact or schema violates the v2 contract."""


@dataclass(frozen=True)
class ArtifactReference:
    """One typed semantic-id reference extracted from an artifact."""

    field: str
    target_id: str
    target_type: str


class SchemaRegistry:
    """Load, validate, and apply versioned record schemas."""

    def __init__(self, schema_dir: str | Path):
        self.schema_dir = Path(schema_dir)
        self._schemas: dict[tuple[str, str], dict[str, Any]] = {}
        self._resources: list[tuple[str, Resource[Any]]] = []
        self._load()

    def _load(self) -> None:
        paths = sorted(self.schema_dir.glob("*.schema.json"))
        if not paths:
            raise SchemaValidationError(
                f"No JSON schemas found in {self.schema_dir}"
            )

        raw_schemas = []
        for path in paths:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            schema_id = schema.get("$id")
            if not schema_id:
                raise SchemaValidationError(f"Schema lacks $id: {path}")
            raw_schemas.append((path, schema))
            self._resources.append(
                (schema_id, Resource.from_contents(schema))
            )

        self._registry = Registry().with_resources(self._resources)
        for path, schema in raw_schemas:
            record_type = schema.get("x-record-type")
            version = schema.get("x-schema-version")
            if not record_type and path.name != "common.schema.json":
                raise SchemaValidationError(
                    f"Record schema lacks x-record-type: {path}"
                )
            if record_type:
                if not TECHNICAL_NAME.fullmatch(record_type):
                    raise SchemaValidationError(
                        f"Record type must be an English snake_case name: {record_type}"
                    )
                if not version:
                    raise SchemaValidationError(
                        f"Record schema lacks x-schema-version: {path}"
                    )
                key = (record_type, version)
                if key in self._schemas:
                    raise SchemaValidationError(f"Duplicate record schema: {key}")
                self._schemas[key] = schema

        if not self._schemas:
            raise SchemaValidationError("No record schemas were registered")

    def available(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._schemas))

    def schema_for(self, record_type: str, version: str) -> dict[str, Any]:
        try:
            return self._schemas[(record_type, version)]
        except KeyError as exc:
            raise SchemaValidationError(
                f"Unknown record schema: {record_type}@{version}"
            ) from exc

    def validate(self, record: dict[str, Any]) -> None:
        if not isinstance(record, dict):
            raise SchemaValidationError("Artifact must be a JSON object")
        record_type = record.get("record_type")
        version = record.get("schema_version")
        schema = self.schema_for(record_type, version)
        validator = Draft202012Validator(
            schema,
            registry=self._registry,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        if errors:
            details = "; ".join(
                f"/{'/'.join(map(str, error.path))}: {error.message}"
                for error in errors
            )
            raise SchemaValidationError(
                f"Invalid {record_type}@{version} artifact: {details}"
            )

    def references(self, record: dict[str, Any]) -> tuple[ArtifactReference, ...]:
        schema = self.schema_for(record["record_type"], record["schema_version"])
        specs = schema.get("x-artifact-references", [])
        references = []
        for spec in specs:
            for value in _values_at_path(record, spec["path"]):
                if value is None:
                    continue
                if not isinstance(value, str):
                    raise SchemaValidationError(
                        f"Artifact reference at {spec['path']} must be a string"
                    )
                references.append(
                    ArtifactReference(
                        field=spec["path"],
                        target_id=value,
                        target_type=spec["record_type"],
                    )
                )
        return tuple(references)


def _values_at_path(document: Any, path: str) -> Iterable[Any]:
    """Resolve a small JSON-pointer subset with `*` array expansion."""

    if not path.startswith("/"):
        raise SchemaValidationError(f"Reference path must start with '/': {path}")
    values = [document]
    for token in path.split("/")[1:]:
        next_values = []
        for value in values:
            if token == "*":
                if not isinstance(value, list):
                    raise SchemaValidationError(
                        f"Reference wildcard expects an array at {path}"
                    )
                next_values.extend(value)
            else:
                if not isinstance(value, dict) or token not in value:
                    raise SchemaValidationError(
                        f"Reference path does not exist: {path}"
                    )
                next_values.append(value[token])
        values = next_values
    return values
