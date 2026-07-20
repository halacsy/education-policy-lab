"""Append-only execution events for resumable artifact DAG runs."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class EventLog:
    """Write one compact JSON event per line and never rewrite history."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_type: str, **payload: Any) -> dict[str, Any]:
        event = {
            "event_type": event_type,
            "sequence": self._next_sequence(),
            "timestamp": utc_now(),
            **payload,
        }
        encoded = json.dumps(
            event, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _next_sequence(self) -> int:
        events = self.read()
        return events[-1]["sequence"] + 1 if events else 1
