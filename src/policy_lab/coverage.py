"""Exact coverage gates for lossy normalization and clustering steps."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


class CoverageValidationError(ValueError):
    """Raised when an artifact disappears or receives an invalid disposition."""


def validate_exact_coverage(
    content: dict[str, Any], expected_ids: Iterable[str], *, basis: str,
    direction_ids: Iterable[str] = (),
) -> None:
    """Validate identity equality, disposition semantics, and critical attrition."""

    expected = set(expected_ids)
    entries = content.get("entries", [])
    if content.get("gate_basis") != basis:
        raise CoverageValidationError(
            f"Coverage basis must be {basis}, got {content.get('gate_basis')}"
        )
    field = {
        "evidence_normalization": "finding_ref",
        "option_seed_clustering": "option_seed_ref",
    }.get(basis)
    if field is None:
        raise CoverageValidationError(f"Unsupported exact-coverage basis: {basis}")
    identities = [entry.get(field) for entry in entries]
    duplicates = sorted(
        identity for identity, count in Counter(identities).items() if count > 1
    )
    actual = set(identities)
    if duplicates or actual != expected:
        raise CoverageValidationError(
            f"{basis} identities differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}, duplicates={duplicates}"
        )

    critical_attrition = 0
    directions = set(direction_ids)
    for entry in entries:
        status = entry.get("status")
        if basis == "evidence_normalization":
            if status == "carried_forward" and not entry.get("canonical_claim_refs"):
                raise CoverageValidationError(
                    f"{entry[field]} is carried forward without a canonical claim"
                )
            if status == "conflict_recorded" and not entry.get("evidence_conflict_refs"):
                raise CoverageValidationError(
                    f"{entry[field]} records no evidence conflict"
                )
            if status == "duplicate_of" and (
                not entry.get("duplicate_of_ref")
                or entry["duplicate_of_ref"] == entry[field]
            ):
                raise CoverageValidationError(
                    f"{entry[field]} has an invalid duplicate disposition"
                )
            attrition_statuses = {"rejected", "out_of_scope", "needs_review"}
        else:
            unknown_directions = set(entry.get("direction_ids", [])) - directions
            if unknown_directions:
                raise CoverageValidationError(
                    f"{entry[field]} cites unknown directions: {sorted(unknown_directions)}"
                )
            if status in {"clustered_into", "retained_as_counterfactual"} and not entry.get("direction_ids"):
                raise CoverageValidationError(
                    f"{entry[field]} is retained without a direction"
                )
            if status == "merged_with" and (
                not entry.get("merged_into_ref")
                or entry["merged_into_ref"] == entry[field]
            ):
                raise CoverageValidationError(
                    f"{entry[field]} has an invalid merge disposition"
                )
            attrition_statuses = {"rejected", "out_of_scope", "human_review"}
        if entry.get("critical") and status in attrition_statuses:
            critical_attrition += 1

    if content.get("critical_attrition_count") != critical_attrition:
        raise CoverageValidationError(
            "Stored critical_attrition_count differs from recomputed count"
        )
    expected_verdict = "complete" if critical_attrition == 0 else "incomplete"
    if content.get("verdict") != expected_verdict:
        raise CoverageValidationError(
            f"Coverage verdict must be {expected_verdict}"
        )
