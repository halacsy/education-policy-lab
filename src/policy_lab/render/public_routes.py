"""Stable, language-neutral routes for the public Education Policy Atlas."""

from __future__ import annotations

import posixpath
import re
from pathlib import PurePosixPath


# The route is based on the immutable semantic id, not mutable display text.
# ``canonical_claim`` is reserved for the normalization artifact described by
# the v2 proposal; current production stores expose atomic claims as Findings.
PUBLIC_RECORD_TYPES: dict[str, str] = {
    "finding": "findings",
    "canonical_claim": "claims",
    "transformation_proposal": "proposals",
    "option_space_proposal": "proposals",
    "problem_brief_proposal": "proposals",
    "research_question": "research-questions",
    "policy_question": "policy-questions",
    "problem_brief": "problem-briefs",
    "dilemma": "dilemmas",
}

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


def _segment(value: str, *, label: str) -> str:
    if not value or not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError(f"Unsafe {label} for public route: {value!r}")
    return value.lower()


def topic_route(topic: str) -> str:
    """Return a topic dossier route relative to the published site root."""

    return f"questions/{_segment(topic, label='topic')}.html"


def record_index_route(topic: str) -> str:
    """Return the canonical-record directory route for one topic."""

    return f"questions/{_segment(topic, label='topic')}/records.html"


def record_route(topic: str, record_type: str, record_id: str) -> str:
    """Return the stable canonical route for one semantic record."""

    try:
        collection = PUBLIC_RECORD_TYPES[record_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported public record type: {record_type}") from exc
    return (
        f"questions/{_segment(topic, label='topic')}/{collection}/"
        f"{_segment(record_id, label='record id')}.html"
    )


def href_between(source_route: str, target_route: str) -> str:
    """Return a relative href from one generated page to another."""

    source_parent = str(PurePosixPath(source_route).parent)
    return posixpath.relpath(target_route, start=source_parent)


def canonical_url(site_url: str, route: str) -> str:
    """Join an absolute configured site root and a generated route."""

    if not site_url.startswith(("https://", "http://")):
        raise ValueError(f"site_url must be absolute: {site_url!r}")
    return f"{site_url.rstrip('/')}/{route.lstrip('/')}"
