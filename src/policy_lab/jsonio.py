"""Canonical JSON serialization for immutable v2 artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically and reject non-standard numbers."""

    text = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    )
    return (text + "\n").encode("utf-8")


def content_hash(value: Any) -> str:
    """Return the SHA-256 hash of the canonical JSON representation."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def write_json(path: str | Path, value: Any) -> None:
    """Atomically write deterministic, human-readable JSON."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(canonical_json_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
