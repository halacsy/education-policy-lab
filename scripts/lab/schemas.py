"""JSON schemas for the structured, bilingual agent outputs (D-34, Phase 2).

Conventions:
- Every object carries additionalProperties: false (required by Anthropic's
  structured-output constrained decoding; the Gemini side strips it in
  llm._gemini_schema()). No min/max/length constraints — those are not
  supported by constrained decoding; content-level checks live in the
  pipeline validators instead.
- Bilingual prose is a {en, hu} leaf pair (helper B()). Language-neutral
  structure (ids, enums, evidence grades, booleans) is stored ONCE, so id
  sets, item counts and label values CANNOT diverge between the two
  languages — bilingual parity holds by construction.
- Evidence is a structured field ({claim, evidence, source}), not an inline
  [evidence: ...] tag; the deterministic renderers (lab/render.py) re-emit
  the legacy inline tags in the markdown views so evaluation keeps working
  until Phase 3 moves it onto the JSON fields.
"""

from functools import lru_cache

EVIDENCE_LEVELS = ["strong", "moderate", "weak", "contested"]
CONFIDENCE_LEVELS = ["low", "medium", "high"]
CLAIM_KINDS = ["fact", "estimate", "assumption", "value"]
STANCES = ["support", "oppose", "conditional", "no_position"]
POSITION_LABELS = ["documented", "value_modeled", "no_position"]
RELEVANCE_LEVELS = ["high", "medium", "low"]
RESPONSE_TYPES = ["evidence_answerable", "policy_design_fixable",
                  "communication_fixable", "value_conflict",
                  "irreducible_tradeoff", "needs_more_info",
                  "not_decision_relevant"]
GRADE_STATUSES = EVIDENCE_LEVELS + ["not_registry_backed"]
RECIPROCITY_OUTCOMES = ["maintain", "revise"]
GAMING_VERDICTS = ["GENUINE", "RUBRIC-GAMING", "NO_BASELINE"]
CRITIC_FIELDS = ["goal", "mechanism", "evidence_status", "assumptions",
                 "expected_benefits", "equity_impact", "cost_categories",
                 "implementation_steps", "political_risks", "uncertainties"]
SEVERITIES = ["high", "medium", "low"]


def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(required if required is not None else properties),
            "additionalProperties": False}


def arr(items):
    return {"type": "array", "items": items}


def s(description=None):
    out = {"type": "string"}
    if description:
        out["description"] = description
    return out


def enum(values, description=None):
    out = {"type": "string", "enum": list(values)}
    if description:
        out["description"] = description
    return out


def B(description=None):
    """Bilingual prose leaf: the SAME statement in native English (en) and
    native Hungarian (hu) — parallel authoring, not translation of one from
    the other. Glossary terms must follow the topic glossary (topics/<slug>/glossary.md)."""
    d = {"en": s("English version" + (f": {description}" if description else "")),
         "hu": s("Magyar változat" + (f": {description}" if description else ""))}
    return obj(d)


# -- expert_analysis ----------------------------------------------------------

EXPERT_ANALYSIS = obj({
    "findings": arr(obj({
        "claim": B("one factual finding"),
        "evidence": enum(EVIDENCE_LEVELS, "how strong the supporting evidence is"),
        "source": s("the source backing the claim (registry id, study, dataset)"),
    })),
    "interpretation": B("what the findings mean together"),
    "assumptions": arr(B("an unverified premise the analysis needs")),
    "position": B("exactly one sentence, falsifiable"),
    "uncertainties": arr(obj({
        "text": B("a known unknown"),
        "confidence": enum(CONFIDENCE_LEVELS,
                           "confidence that current knowledge suffices"),
        "reduced_by": B("what evidence would reduce this uncertainty"),
    })),
})


# -- build_scenarios ----------------------------------------------------------
# Scenario-dependent schemas are FACTORIES over the topic's frozen frame ids
# (issue #21/D-36: 2-5 frames, not a fixed four) — call with
# tuple(topic.scenario_ids); lru_cache keeps them singletons per topic.


@lru_cache(maxsize=None)
def SCENARIOS(ids):
    return obj({
    "scenarios": arr(obj({
        "id": enum(ids),
        "title": B(),
        "goal": B(),
        "mechanism": arr(obj({
            "text": B("one causal claim"),
            "evidence": enum(EVIDENCE_LEVELS),
        })),
        "evidence_status": obj({
            "label": enum(EVIDENCE_LEVELS, "overall evidence label"),
            "note": B("one-sentence justification"),
        }),
        "assumptions": arr(B()),
        "expected_benefits": arr(obj({
            "text": B("one expected benefit"),
            "evidence": enum(EVIDENCE_LEVELS),
        })),
        "equity_impact": B(),
        "cost_categories": arr(B()),
        "implementation_steps": arr(obj({
            "actor": B("who acts"),
            "action": B("what they do"),
            "timeline": B("when, e.g. 'year 1-2' / '1-2. év'"),
        })),
        "political_risks": arr(B()),
        "uncertainties": arr(obj({
            "text": B(),
            "confidence": enum(CONFIDENCE_LEVELS),
            "reduced_by": B(),
        })),
    })),
})


# -- critics (EN-only: internal QA artifacts, never published) ----------------

@lru_cache(maxsize=None)
def CRITIC(ids):
    return obj({
    "objections": arr(obj({
        "scenario": enum(ids),
        "field": enum(CRITIC_FIELDS),
        "objection": s("the concrete flaw — specific, actionable, non-generic"),
        "severity": enum(SEVERITIES),
        "suggested_revision": s("a concrete fix"),
    })),
})


# -- synthesis + rejected framings --------------------------------------------

SYNTHESIS = obj({
    "overview": B("the expert record in one coherent paragraph"),
    "disagreements": arr(obj({
        "topic": B("what the disagreement is about"),
        "sides": arr(obj({
            "holders": arr(s("expert name")),
            "position": B(),
            "rationale": B("why this side holds it"),
            "minority": {"type": "boolean",
                         "description": "true if this is the minority side"},
        })),
    })),
    "agreements": arr(obj({
        "text": B("something the experts agree on"),
        "evidence": enum(EVIDENCE_LEVELS),
    })),
})

@lru_cache(maxsize=None)
def REJECTED_FRAMINGS(ids):
    return obj({
    "scenarios": arr(obj({
        "id": enum(ids),
        "chosen": s("the framing selected"),
        "rejected": arr(obj({
            "framing": s("a candidate framing considered"),
            "reason": s("why it was rejected"),
        })),
    })),
})


# -- societal discourse (D-29) -------------------------------------------------

@lru_cache(maxsize=None)
def VOICE(ids):
    return obj({
    "voice": s("your agent name"),
    "reactions": arr(obj({
        "scenario": enum(ids),
        "stance": enum(STANCES),
        "label": enum(POSITION_LABELS),
        "source": s("document/URL — REQUIRED when label=documented, else empty"),
        "basis": s("the documented values it derives from — REQUIRED when "
                   "label=value_modeled, else empty"),
        "interest": B("whose interest you defend"),
        "public_good_frame": B("your public-good framing"),
        "argument": B("justification; a bare stance is invalid"),
        "condition_to_change": B("what would change your stance; empty only "
                                 "for no_position"),
    })),
})

@lru_cache(maxsize=None)
def CLUSTER_BASIC(ids):
    return obj({
    "clusters": arr(obj({
        "id": s("stable sequential id A1..An"),
        "scenario": enum(ids),
        "kind": enum(["fact", "value", "mixed"]),
        "side": enum(["pro", "con", "conditional"]),
        "claim": B("canonical one-sentence form of the argument"),
        "raised_by": arr(s("voice name")),
    })),
})

CLUSTER_DECOMPOSE = obj({
    "interest": B("whose interest is behind this argument"),
    "value": B("which value is in tension"),
    "fear": B("the anticipated loss or harm driving it"),
    "affected": arr(B("an affected actor group")),
    "assumption": B("the unstated assumption the claim rests on"),
    "empirical_uncertainty": B("is the factual part settled, contested or "
                               "unknown, and why"),
    "decision_relevance": enum(RELEVANCE_LEVELS),
    "attention": obj({
        "high_attention": {"type": "boolean"},
        "new_information": {"type": "boolean"},
        "changes_evaluation": {"type": "boolean"},
        "already_answered": {"type": "boolean"},
        "primarily_rhetorical": {"type": "boolean"},
    }),
})

RECIPROCITY = obj({
    "voice": s("your agent name"),
    "responses": arr(obj({
        "cluster": s("A<i> id of the argument you answer"),
        "response": B("engage the argument on its merits"),
        "outcome": enum(RECIPROCITY_OUTCOMES),
        "new_condition": B("the revised condition, if outcome=revise; else empty"),
    })),
})

GRADES = obj({
    "grades": arr(obj({
        "cluster_id": s("A<i>"),
        "status": enum(GRADE_STATUSES,
                       "registry-backed evidence grade, or not_registry_backed"),
        "source": s("the registry source — empty when not_registry_backed"),
        "note": s("one-line note"),
    })),
})


# -- brief (the 10-section deliberation deliverable, D-30) ---------------------

# The brief is the largest schema; written with inline {en, hu} objects its
# compiled constrained-decoding grammar exceeds Anthropic's size limit
# ("The compiled grammar is too large" 400, round-8 acceptance run). A
# single $defs/bi definition referenced everywhere compiles compactly.
# NOTE: $ref is Anthropic-only here — the brief runs on the generator side;
# llm._gemini_schema() does not resolve refs, so this schema must not be
# sent to the Gemini backend.
BI = {"$ref": "#/$defs/bi"}


@lru_cache(maxsize=None)
def BRIEF(ids):
    B_ = obj({
    "intro": BI,
    "scenario_key": arr(obj({"id": enum(ids), "title": BI})),
    "what_we_know": arr(obj({
        "text": BI, "kind": enum(CLAIM_KINDS), "evidence": enum(EVIDENCE_LEVELS),
    })),
    "what_we_consider_likely": arr(obj({
        "text": BI, "kind": enum(CLAIM_KINDS),
    })),
    "where_experts_disagree": arr(obj({
        "topic": BI,
        "positions": arr(obj({
            "holders": arr(s()), "position": BI, "why": BI,
            "minority": {"type": "boolean"},
        })),
    })),
    "what_we_dont_know": arr(obj({
        "text": BI, "kind": enum(CLAIM_KINDS),
    })),
    "what_could_be_done": arr(obj({
        "scenario_id": enum(ids), "title": BI, "summary": BI,
    })),
    "what_each_option_costs": arr(obj({
        "scenario_id": enum(ids), "text": BI, "kind": enum(CLAIM_KINDS),
    })),
    "what_research_could_resolve": arr(BI),
    "what_people_must_decide": arr(BI),
    "stakeholder_responses": arr(obj({
        "cluster_id": s("A<i>"),
        "restatement": BI,
        "response_type": enum(RESPONSE_TYPES),
        "reason": BI,
    })),
    "attention_sinks": arr(obj({
        "cluster_id": s("A<i>"),
        "text": BI,
    })),
    "minority_positions": arr(obj({
        "holders": arr(s()), "position": BI, "rationale": BI,
    })),
    })
    B_["$defs"] = {"bi": obj({
        "en": s("the statement in native English"),
        "hu": s("ugyanez az állítás natív magyarul"),
    })}
    return B_


# -- meta critique (EN-only: internal system-evaluation artifact) --------------

META_CRITIQUE = obj({
    "agent_performance": arr(s("one observation about a specific agent")),
    "workflow": arr(s("one observation about a workflow step")),
    "critique_quality": arr(s("one observation about the critics' output")),
    "gaming_judgment": obj({
        "verdict": enum(GAMING_VERDICTS,
                        "NO_BASELINE only on the first scored round"),
        "reasons": arr(s("grounded in the input scores/artifacts")),
    }),
    "translation_consistency": arr(s()),
    "removal_candidates": arr(s("agent name + why; empty list if none")),
})


# -- emergent scenario framing (issue #21, D-36) --------------------------------
# Round 1 derives the option space (2-5 solution frames) from the expert
# record; a human approves it (D-24 pattern) and it freezes into topic.json.

FRAMES = obj({
    "frames": arr(obj({
        "id": s("stable sequential id: S1, S2, ... (at most S5)"),
        "title": B("short frame title (what family of solutions this is)"),
        "scope": B("one sentence: what is inside this frame"),
    })),
    "rejected_framings": arr(obj({
        "framing": B("a candidate framing considered for the option space"),
        "reason": B("why it was rejected"),
    })),
})


# -- problem-brief intake (D-36) -------------------------------------------------
# scripts/new_topic.py drafts a structured problem brief from free text;
# a human approves/edits it before the topic runs.

PROBLEM_BRIEF = obj({
    "slug": s("short ascii-kebab-case slug (directory, URL, git reference)"),
    "title": B("short title for the website"),
    "problem_statement": B("1-3 paragraphs: the situation and its tension — "
                           "a described problem or opportunity, NOT a bare "
                           "question"),
    "learning_goals": arr(B("one explicit learning goal (2-4 total)")),
    "scope": B("what is in scope and what is explicitly out"),
})


# -- executive summary ---------------------------------------------------------

EXEC_SUMMARY = obj({
    "en": s("the full one-page executive summary in English (markdown prose)"),
    "hu": s("a teljes egyoldalas vezetői összefoglaló magyarul (markdown próza)"),
})
