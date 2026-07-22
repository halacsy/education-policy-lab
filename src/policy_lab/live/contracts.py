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


TEXT_VALUE = {"type": "string", "minLength": 1}
TEXT = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"en": TEXT_VALUE, "hu": TEXT_VALUE},
    "required": ["en", "hu"],
}
STRENGTH = {"type": "string", "enum": ["strong", "moderate", "weak", "contested"]}


PROBLEM_BRIEF_OUTPUT = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "title": TEXT,
        "public_question": TEXT,
        "problem_statement": TEXT,
        "learning_goals": array(TEXT, 3, 7),
        "scope": TEXT,
        "seed_sources": array(TEXT_VALUE, 0, 12),
        "framing_notes": array(TEXT, 1, 7),
    },
    "required": [
        "title", "public_question", "problem_statement", "learning_goals",
        "scope", "seed_sources", "framing_notes",
    ],
}

RESEARCH_OUTPUT = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "findings": array({
            "type": "object", "additionalProperties": False,
            "properties": {
                "claim": TEXT, "evidence_strength": STRENGTH,
                "source_title": TEXT, "source_url": TEXT_VALUE,
                "limitations": array(TEXT, 1, 3),
            },
            "required": ["claim", "evidence_strength", "source_title", "source_url", "limitations"],
        }, 7, 10),
        "assumptions": array(TEXT, 1, 4),
        "uncertainties": array({
            "type": "object", "additionalProperties": False,
            "properties": {"question": TEXT, "reduction_path": TEXT},
            "required": ["question", "reduction_path"],
        }, 2, 4),
    },
    "required": ["findings", "assumptions", "uncertainties"],
}


def option_space_output(finding_ids: list[str]) -> dict[str, Any]:
    """Provider contract for evidence-derived, pre-approval option space."""

    finding_ref = {"type": "string", "enum": finding_ids}
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "directions": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "pattern": "^S[1-7]$"},
                    "title": TEXT,
                    "scope": TEXT,
                    "finding_refs": array(finding_ref, 1, 20),
                },
                "required": ["id", "title", "scope", "finding_refs"],
            }, 2, 7),
            "rejected_framings": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "framing": TEXT,
                    "reason": TEXT,
                    "finding_refs": array(finding_ref, 0, 20),
                },
                "required": ["framing", "reason", "finding_refs"],
            }, 1, 7),
        },
        "required": ["directions", "rejected_framings"],
    }


def evidence_normalization_output(
    finding_ids: list[str], assumption_ids: list[str], uncertainty_ids: list[str]
) -> dict[str, Any]:
    """Normalize atomic findings without allowing any finding to disappear."""

    finding_ref = {"type": "string", "enum": finding_ids}
    assumption_ref = {"type": "string", "enum": assumption_ids}
    uncertainty_ref = {"type": "string", "enum": uncertainty_ids}
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "claims": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "key": {"type": "string", "pattern": "^C[1-9][0-9]*$"},
                    "statement": TEXT,
                    "claim_type": {"type": "string", "enum": ["descriptive", "causal", "mechanistic", "forecasting"]},
                    "population": TEXT, "context": TEXT, "time_scope": TEXT,
                    "evidence_strength": STRENGTH,
                    "transferability": {"type": "string", "enum": ["direct", "conditional", "analogy_only", "not_transferable"]},
                    "supporting_finding_refs": array(finding_ref, 1, 30),
                    "contradicting_finding_refs": array(finding_ref, 0, 30),
                    "assumption_refs": array(assumption_ref, 0, 20),
                    "uncertainty_refs": array(uncertainty_ref, 0, 20),
                },
                "required": ["key", "statement", "claim_type", "population", "context", "time_scope", "evidence_strength", "transferability", "supporting_finding_refs", "contradicting_finding_refs", "assumption_refs", "uncertainty_refs"],
            }, 1, 60),
            "conflicts": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "key": {"type": "string", "pattern": "^E[1-9][0-9]*$"},
                    "title": TEXT,
                    "conflict_type": {"type": "string", "enum": ["direct_contradiction", "context_dependence", "measurement_difference", "temporal_change", "causal_interpretation", "population_difference", "transferability"]},
                    "description": TEXT,
                    "resolvability": {"type": "string", "enum": ["answerable_now", "requires_new_data", "context_specific", "not_empirically_resolvable"]},
                    "research_question": TEXT, "decision_relevance": TEXT,
                    "finding_refs": array(finding_ref, 1, 20),
                    "claim_keys": array({"type": "string", "pattern": "^C[1-9][0-9]*$"}, 1, 10),
                },
                "required": ["key", "title", "conflict_type", "description", "resolvability", "research_question", "decision_relevance", "finding_refs", "claim_keys"],
            }, 0, 30),
            "coverage": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "finding_ref": finding_ref,
                    "status": {"type": "string", "enum": ["carried_forward", "duplicate_of", "context_only", "conflict_recorded", "assumption_only", "out_of_scope", "rejected", "needs_review"]},
                    "claim_keys": array({"type": "string", "pattern": "^C[1-9][0-9]*$"}, 0, 20),
                    "conflict_keys": array({"type": "string", "pattern": "^E[1-9][0-9]*$"}, 0, 20),
                    "duplicate_of_refs": array(finding_ref, 0, 1),
                    "critical": {"type": "boolean"},
                    "rationale": TEXT,
                },
                "required": ["finding_ref", "status", "claim_keys", "conflict_keys", "duplicate_of_refs", "critical", "rationale"],
            }, len(finding_ids), len(finding_ids)),
        },
        "required": ["claims", "conflicts", "coverage"],
    }


def option_seed_output(
    claim_ids: list[str], conflict_ids: list[str], finding_ids: list[str],
    assumption_ids: list[str], uncertainty_ids: list[str],
) -> dict[str, Any]:
    """Provider contract for evidence-derived levers before clustering."""

    conflict_ref = (
        {"type": "string", "enum": conflict_ids}
        if conflict_ids
        else {"type": "string", "pattern": "^EC-[A-Za-z0-9._-]+$"}
    )
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "seeds": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "key": {"type": "string", "pattern": "^O[1-9][0-9]*$"},
                    "title": TEXT, "system_problem": TEXT, "change_lever": TEXT,
                    "scope": TEXT,
                    "seed_type": {"type": "string", "enum": ["structural", "regulatory", "funding", "organizational", "practice", "information", "counterfactual"]},
                    "canonical_claim_refs": array({"type": "string", "enum": claim_ids}, 1, 20),
                    "evidence_conflict_refs": array(conflict_ref, 0, 10),
                    "finding_refs": array({"type": "string", "enum": finding_ids}, 1, 30),
                    "assumption_refs": array({"type": "string", "enum": assumption_ids}, 0, 20),
                    "uncertainty_refs": array({"type": "string", "enum": uncertainty_ids}, 0, 20),
                },
                "required": ["key", "title", "system_problem", "change_lever", "scope", "seed_type", "canonical_claim_refs", "evidence_conflict_refs", "finding_refs", "assumption_refs", "uncertainty_refs"],
            }, 4, 20),
        },
        "required": ["seeds"],
    }


def clustered_option_space_output(seed_ids: list[str]) -> dict[str, Any]:
    """Cluster every option seed into a bounded candidate option space."""

    seed_ref = {"type": "string", "enum": seed_ids}
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "directions": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "pattern": "^S[1-7]$"},
                    "title": TEXT, "scope": TEXT,
                    "option_seed_refs": array(seed_ref, 1, 20),
                },
                "required": ["id", "title", "scope", "option_seed_refs"],
            }, 2, 7),
            "rejected_framings": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "framing": TEXT, "reason": TEXT,
                    "option_seed_refs": array(seed_ref, 0, 20),
                },
                "required": ["framing", "reason", "option_seed_refs"],
            }, 1, 7),
            "coverage": array({
                "type": "object", "additionalProperties": False,
                "properties": {
                    "option_seed_ref": seed_ref,
                    "status": {"type": "string", "enum": ["clustered_into", "merged_with", "retained_as_counterfactual", "rejected", "out_of_scope", "human_review"]},
                    "direction_ids": array({"type": "string", "pattern": "^S[1-7]$"}, 0, 7),
                    "merged_into_refs": array(seed_ref, 0, 1),
                    "critical": {"type": "boolean"},
                    "rationale": TEXT,
                },
                "required": ["option_seed_ref", "status", "direction_ids", "merged_into_refs", "critical", "rationale"],
            }, len(seed_ids), len(seed_ids)),
        },
        "required": ["directions", "rejected_framings", "coverage"],
    }


def transformation_output(
    finding_ids: list[str], direction_ids: list[str] | None = None,
    canonical_claim_ids: list[str] | None = None,
) -> dict[str, Any]:
    direction_ids = direction_ids or []
    canonical_claim_ids = canonical_claim_ids or []
    contract = {
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
    if canonical_claim_ids:
        proposal = contract["properties"]["proposals"]["items"]
        proposal["properties"]["canonical_claim_refs"] = array(
            {"type": "string", "enum": canonical_claim_ids}, 1, 20
        )
        proposal["required"].append("canonical_claim_refs")
    return contract


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
