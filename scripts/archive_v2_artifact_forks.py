#!/usr/bin/env python3
"""Archive stale branches created before automatic artifact succession existed."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    artifact_dir = args.output_root / "artifacts"
    run_dir = args.output_root / "runs" / args.run_id
    selected = {
        item["content_hash"]
        for manifest_path in (run_dir / "nodes").glob("*.json")
        for item in load(manifest_path)["output_artifacts"]
    }
    by_id: dict[str, list[tuple[str, Path, dict]]] = defaultdict(list)
    for path in artifact_dir.glob("*/*.json"):
        record = load(path)
        by_id[record["id"]].append((path.stem, path, record))

    stale: list[tuple[str, str, Path]] = []
    for record_id, versions in by_id.items():
        superseded = {
            record["supersedes"] for _, _, record in versions
            if record.get("supersedes") is not None
        }
        current = [item for item in versions if item[0] not in superseded]
        if len(current) <= 1:
            continue
        chosen = [item for item in current if item[0] in selected]
        if len(chosen) != 1:
            raise RuntimeError(
                f"Cannot resolve {record_id}: {len(current)} current, "
                f"{len(chosen)} selected by latest manifests"
            )
        stale.extend((record_id, digest, path) for digest, path, _ in current if digest != chosen[0][0])

    stale_hashes = {digest for _, digest, _ in stale}
    cache_files = []
    for path in (args.output_root / "cache").glob("*/*.json"):
        payload = load(path)
        if stale_hashes.intersection(payload.get("output_artifact_hashes", [])):
            cache_files.append(path)

    report = {
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_id": args.run_id,
        "selected_hash_count": len(selected),
        "archived_artifacts": [
            {"id": record_id, "content_hash": digest, "path": str(path.relative_to(args.output_root))}
            for record_id, digest, path in stale
        ],
        "archived_cache_files": [str(path.relative_to(args.output_root)) for path in cache_files],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if not args.apply:
        return 0

    archive = args.output_root / "archive" / "pre-lineage-forks"
    for _, _, path in stale:
        target = archive / "artifacts" / path.parent.name / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        path.replace(target)
    for path in cache_files:
        target = archive / "cache" / path.parent.name / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        path.replace(target)
    report_path = archive / "archive_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
