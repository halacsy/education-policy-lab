"""Static node contracts and dependency-scoped cache keys."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from policy_lab.jsonio import content_hash

NODE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
ROLES = {"deterministic", "generator", "judge", "localizer", "research"}


@dataclass(frozen=True)
class NodeSpec:
    name: str
    version: str
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    spec_files: tuple[str, ...] = ()
    schema_files: tuple[str, ...] = ()
    config_keys: tuple[str, ...] = ()
    role: str = "deterministic"
    validator: str = ""

    def __post_init__(self) -> None:
        if not NODE_NAME.fullmatch(self.name):
            raise ValueError(f"Node name must be English snake_case: {self.name}")
        if self.role not in ROLES:
            raise ValueError(f"Unknown node role: {self.role}")
        for value in (*self.input_types, *self.output_types, *self.config_keys):
            if not NODE_NAME.fullmatch(value.replace(".", "_")):
                raise ValueError(f"Node contract name must be English: {value}")


def compute_cache_key(
    spec: NodeSpec,
    *,
    input_artifact_hashes: Mapping[str, tuple[str, ...]],
    spec_hashes: Mapping[str, str],
    schema_hashes: Mapping[str, str],
    relevant_config: Mapping[str, Any],
    provider: str | None,
    model: str | None,
    generation_parameters: Mapping[str, Any],
    prompt_hash: str | None = None,
) -> str:
    """Hash only the dependencies explicitly declared by the node."""

    payload = {
        "generation_parameters": dict(generation_parameters),
        "input_artifact_hashes": {
            binding: sorted(hashes)
            for binding, hashes in input_artifact_hashes.items()
        },
        "model": model,
        "node": asdict(spec),
        "provider": provider,
        "prompt_hash": prompt_hash,
        "relevant_config": dict(relevant_config),
        "schema_hashes": dict(schema_hashes),
        "spec_hashes": dict(spec_hashes),
    }
    return content_hash(payload)
