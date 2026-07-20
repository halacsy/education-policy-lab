"""Provider-facing structured-output contracts for live v2 nodes."""

from __future__ import annotations

from typing import Any


def array(items: dict[str, Any], minimum: int = 1, maximum: int | None = None) -> dict[str, Any]:
    # Anthropic's structured-output grammar accepts only minItems 0 or 1 and
    # rejects maxItems. Semantic cardinalities are checked by node validators
    # and reinforced in the prompts.
    return {
        "type": "array", "items": items, "minItems": min(minimum, 1)
    }


TEXT = {"type": "string", "minLength": 1}
STRENGTH = {"type": "string", "enum": ["strong", "moderate", "weak", "contested"]}

RESEARCH_OUTPUT = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "findings": array({
            "type": "object", "additionalProperties": False,
            "properties": {
                "claim": TEXT, "evidence_strength": STRENGTH,
                "source_title": TEXT, "source_url": TEXT,
                "limitations": array(TEXT, 1, 3),
            },
            "required": ["claim", "evidence_strength", "source_title", "source_url", "limitations"],
        }, 4, 7),
        "assumptions": array(TEXT, 1, 4),
        "uncertainties": array({
            "type": "object", "additionalProperties": False,
            "properties": {"question": TEXT, "reduction_path": TEXT},
            "required": ["question", "reduction_path"],
        }, 2, 4),
    },
    "required": ["findings", "assumptions", "uncertainties"],
}


def transformation_output(finding_ids: list[str], direction_ids: list[str] | None = None) -> dict[str, Any]:
    direction_ids = direction_ids or []
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "proposals": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "key": {"type": "string", "pattern": "^T[1-6]$"},
                    "title": TEXT, "goal": TEXT,
                    "change_level": {"type": "string", "enum": ["practice", "organization", "network", "governance", "system"]},
                    "system_problem": TEXT, "change_lever": TEXT, "boundary": TEXT,
                    "mechanisms": array(TEXT, 2, 5),
                    "implementation_steps": array({
                        "type": "object", "additionalProperties": False,
                        "properties": {"actor": TEXT, "action": TEXT, "timeline": TEXT},
                        "required": ["actor", "action", "timeline"],
                    }, 2, 6),
                    "expected_benefits": array(TEXT, 1, 5),
                    "costs": array(TEXT, 1, 5), "risks": array(TEXT, 1, 5),
                    "equity_impact": TEXT, "evidence_status": STRENGTH,
                    "finding_refs": array({"type": "string", "enum": finding_ids}, 2, 20),
                    "assumptions": array(TEXT, 1, 4),
                    "uncertainties": array(TEXT, 1, 4),
                },
                "required": ["key", "title", "goal", "change_level", "system_problem", "change_lever", "boundary", "mechanisms", "implementation_steps", "expected_benefits", "costs", "risks", "equity_impact", "evidence_status", "finding_refs", "assumptions", "uncertainties"],
            }, 4, 6),
            "coverage": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "direction_id": {"type": "string", "enum": direction_ids},
                    "proposal_keys": array({"type": "string", "pattern": "^T[1-6]$"}, 1, 6),
                    "rationale": TEXT,
                },
                "required": ["direction_id", "proposal_keys", "rationale"],
            }, len(direction_ids), len(direction_ids)),
        },
        "required": ["proposals", "coverage"],
    }


def assessment_output(proposal_ids: list[str], finding_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "assessments": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "proposal_ref": {"type": "string", "enum": proposal_ids},
                    "assessment": TEXT,
                    "strengths": array(TEXT, 1, 3), "weaknesses": array(TEXT, 1, 3),
                    "opportunities": array(TEXT, 1, 3), "threats": array(TEXT, 1, 3),
                    "verdict": {"type": "string", "enum": ["supports", "supports_with_conditions", "neutral", "cautions", "insufficient_evidence"]},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "finding_refs": array({"type": "string", "enum": finding_ids}, 1, 12),
                },
                "required": ["proposal_ref", "assessment", "strengths", "weaknesses", "opportunities", "threats", "verdict", "confidence", "finding_refs"],
            }, len(proposal_ids), len(proposal_ids)),
        },
        "required": ["assessments"],
    }


def dilemma_output(proposal_ids: list[str], finding_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "dilemmas": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "title": TEXT, "tension": TEXT,
                    "dilemma_type": {"type": "string", "enum": ["value_conflict", "irreducible_tradeoff", "mixed", "empirical_open_question"]},
                    "value_poles": array(TEXT, 2, 3), "affected_groups": array(TEXT, 1, 8),
                    "decision_question": TEXT, "evidence_boundary": TEXT,
                    "proposal_refs": array({"type": "string", "enum": proposal_ids}, 1, 4),
                    "finding_refs": array({"type": "string", "enum": finding_ids}, 1, 10),
                },
                "required": ["title", "tension", "dilemma_type", "value_poles", "affected_groups", "decision_question", "evidence_boundary", "proposal_refs", "finding_refs"],
            }, 3, 8),
        },
        "required": ["dilemmas"],
    }


def agenda_output(proposal_ids: list[str], uncertainty_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "questions": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "question": TEXT, "why_it_matters": TEXT, "method": TEXT,
                    "decision_impact": {"type": "string", "enum": ["high", "medium", "low"]},
                    "answerability": {"type": "string", "enum": ["answerable_now", "requires_new_data", "requires_pilot", "not_empirically_resolvable"]},
                    "proposal_refs": array({"type": "string", "enum": proposal_ids}, 1, 4),
                    "uncertainty_refs": array({"type": "string", "enum": uncertainty_ids}, 1, 6),
                },
                "required": ["question", "why_it_matters", "method", "decision_impact", "answerability", "proposal_refs", "uncertainty_refs"],
            }, 4, 10),
        },
        "required": ["questions"],
    }


PACKAGE_OUTPUT = {
    "type": "object", "additionalProperties": False,
    "properties": {"summary": TEXT}, "required": ["summary"],
}

EVALUATION_OUTPUT = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "dimensions": {
            "type": "object", "additionalProperties": False,
            "properties": {name: {"type": "number", "minimum": 0, "maximum": 10} for name in [
                "artifact_integrity", "evidence_discipline", "transformation_specificity",
                "lens_traceability", "dilemma_clarity", "decision_usefulness",
            ]},
            "required": ["artifact_integrity", "evidence_discipline", "transformation_specificity", "lens_traceability", "dilemma_clarity", "decision_usefulness"],
        },
        "strengths": array(TEXT, 1, 5), "concerns": array(TEXT, 0, 5),
        "verdict": {"type": "string", "enum": ["accept", "accept_with_caveats", "revise", "reject"]},
    },
    "required": ["dimensions", "strengths", "concerns", "verdict"],
}
