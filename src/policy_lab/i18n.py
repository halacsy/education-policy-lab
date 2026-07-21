"""D-34 bilingual semantic leaves and deterministic language projection."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable, Iterable


BILINGUAL_VERSION = "2.1.0"
LANGUAGES = ("en", "hu")


class BilingualValidationError(ValueError):
    """Raised when a semantic prose field is not an exact {en, hu} pair."""


def load_field_map(repo_root: str | Path) -> dict[str, tuple[str, ...]]:
    data = json.loads(
        (Path(repo_root) / "config" / "v2" / "bilingual_fields.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        record_type: tuple(paths)
        for record_type, paths in data["record_types"].items()
    }


def is_localized_text(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(LANGUAGES)
        and all(isinstance(value[language], str) and value[language].strip() for language in LANGUAGES)
    )


def text(value: Any, language: str = "en") -> str:
    """Project a bilingual leaf, while retaining v2.0 archive compatibility."""

    if is_localized_text(value):
        return value[language]
    if isinstance(value, str):
        return value
    raise BilingualValidationError(f"Expected text or localized text, got {type(value).__name__}")


def localized(english: str, hungarian: str) -> dict[str, str]:
    value = {"en": english.strip(), "hu": hungarian.strip()}
    if not is_localized_text(value):
        raise BilingualValidationError("Both English and Hungarian text are required")
    return value


def suspicious_identity(record_type: str, path: str, value: Any) -> bool:
    """Flag long copied prose while allowing language-neutral citations."""

    if not is_localized_text(value):
        return False
    if record_type == "source" or ".sources.*.title" in path:
        return False
    english = value["en"].strip()
    hungarian = value["hu"].strip()
    return english.casefold() == hungarian.casefold() and len(english.split()) >= 4


def values_at_path(document: Any, path: str) -> Iterable[tuple[Any, str | int]]:
    """Yield mutable parent/key pairs for a dotted path with array wildcards."""

    nodes = [document]
    tokens = path.split(".")
    for token in tokens[:-1]:
        next_nodes: list[Any] = []
        for node in nodes:
            if token == "*":
                if isinstance(node, list):
                    next_nodes.extend(node)
                continue
            if isinstance(node, dict) and token in node:
                next_nodes.append(node[token])
        nodes = next_nodes
    leaf = tokens[-1]
    for node in nodes:
        if leaf == "*" and isinstance(node, list):
            for index in range(len(node)):
                yield node, index
        elif isinstance(node, dict) and leaf in node:
            yield node, leaf


def validate_bilingual_content(
    record_type: str, content: dict[str, Any], field_map: dict[str, tuple[str, ...]]
) -> None:
    try:
        paths = field_map[record_type]
    except KeyError as exc:
        raise BilingualValidationError(
            f"No bilingual field contract for {record_type}"
        ) from exc
    for path in paths:
        for parent, key in values_at_path(content, path):
            if not is_localized_text(parent[key]):
                raise BilingualValidationError(
                    f"{record_type}.{path} must be an exact non-empty {{en, hu}} pair"
                )


def project_content(
    record_type: str,
    content: dict[str, Any],
    field_map: dict[str, tuple[str, ...]],
    language: str,
) -> dict[str, Any]:
    projected = copy.deepcopy(content)
    for path in field_map.get(record_type, ()):
        for parent, key in values_at_path(projected, path):
            parent[key] = text(parent[key], language)
    return projected


def project_record(
    record: dict[str, Any],
    field_map: dict[str, tuple[str, ...]],
    language: str,
    *,
    archive_schema_version: str | None = None,
) -> dict[str, Any]:
    projected = copy.deepcopy(record)
    projected["content"] = project_content(
        record["record_type"], record["content"], field_map, language
    )
    if archive_schema_version is not None:
        projected["schema_version"] = archive_schema_version
    return projected


def bilingualize_content(
    record_type: str,
    content: dict[str, Any],
    field_map: dict[str, tuple[str, ...]],
    translate: Callable[[str], str],
) -> dict[str, Any]:
    result = copy.deepcopy(content)
    for path in field_map[record_type]:
        for parent, key in values_at_path(result, path):
            value = parent[key]
            if is_localized_text(value):
                continue
            if not isinstance(value, str) or not value.strip():
                raise BilingualValidationError(
                    f"Cannot bilingualize {record_type}.{path}: {value!r}"
                )
            parent[key] = localized(value, translate(value))
    validate_bilingual_content(record_type, result, field_map)
    return result
