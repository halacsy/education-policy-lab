#!/usr/bin/env python3
"""Record an explicit human decision for one exact v2 gate candidate hash."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_lab.jsonio import write_json  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Approve one exact candidate at a declared v2 human gate."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("approve", "approve-brief"):
        approve = subparsers.add_parser(command)
        approve.add_argument("--topic", required=True)
        approve.add_argument("--run-tag", required=True)
        approve.add_argument("--candidate-hash")
        approve.add_argument("--decided-by", required=True)
        approve.add_argument("--rationale", required=True)
        approve.add_argument(
            "--output-root", type=Path, default=ROOT / "v2" / "production"
        )
    args = parser.parse_args()

    gate_id = (
        "approve_problem_brief" if args.command == "approve-brief"
        else "approve_option_space"
    )
    gate_dir = (
        args.output_root / args.run_tag / args.topic / "runs"
        / f"live-{args.topic}-production" / "gates" / gate_id
    )
    requests = sorted(gate_dir.glob("*.request.json"))
    if args.candidate_hash:
        requests = [
            path for path in requests
            if path.name == f"{args.candidate_hash}.request.json"
        ]
    if len(requests) != 1:
        raise SystemExit(
            f"Expected exactly one matching gate request in {gate_dir}, "
            f"found {len(requests)}. Pass --candidate-hash explicitly."
        )
    request_path = requests[0]
    request = _load(request_path)
    decision_path = request_path.with_name(
        request_path.name.replace(".request.json", ".decision.json")
    )
    if decision_path.exists():
        existing = _load(decision_path)
        expected_identity = {
            "gate_id": request["gate_id"],
            "candidate_ref": request["candidate_ref"],
            "candidate_hash": request["candidate_hash"],
            "decision": "approved",
            "decided_by": args.decided_by.strip(),
            "rationale": args.rationale.strip(),
        }
        if all(existing.get(key) == value for key, value in expected_identity.items()):
            print(f"Decision already recorded: {decision_path}")
            return 0
        raise SystemExit(f"Decision already exists and is immutable: {decision_path}")
    decision = {
        "gate_id": request["gate_id"],
        "candidate_ref": request["candidate_ref"],
        "candidate_hash": request["candidate_hash"],
        "decision": "approved",
        "decided_by": args.decided_by.strip(),
        "decided_at": _now(),
        "rationale": args.rationale.strip(),
    }
    if not decision["decided_by"] or not decision["rationale"]:
        raise SystemExit("--decided-by and --rationale must not be empty")
    write_json(decision_path, decision)
    print(f"Approved {decision['candidate_ref']} @ {decision['candidate_hash']}")
    print(f"Decision: {decision_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
