"""Canonical declarative DAG for fresh education-policy analysis runs."""

from __future__ import annotations

from typing import Iterable

from policy_lab.dag.spec import DagNode, DagSpec, InputBinding, RootPort


VERSION = "3.2.0"
EVIDENCE_TYPES = ("source", "finding", "assumption", "uncertainty")


def _schemas(*names: str) -> tuple[str, ...]:
    return (
        *(f"schemas/v2/{name}.schema.json" for name in names),
        "schemas/v2/bilingual.schema.json",
        "config/v2/bilingual_fields.json",
    )


def _node(
    node_id: str,
    *,
    kind: str,
    role: str,
    stage: str,
    title: str,
    description: str,
    handler: str,
    inputs: tuple[InputBinding, ...],
    outputs: tuple[str, ...],
    schemas: tuple[str, ...],
    provider: str = "anthropic",
    model: str = "claude-sonnet-5",
    generation_parameters: tuple[tuple[str, object], ...] = (),
) -> DagNode:
    return DagNode(
        id=node_id,
        version="1.0.0",
        kind=kind,
        role=role,
        stage=stage,
        title=title,
        description=description,
        handler=handler,
        inputs=inputs,
        output_types=outputs,
        schema_files=schemas,
        provider=provider,
        model=model,
        generation_parameters=generation_parameters,
    )


def build_policy_analysis_dag(
    lens_ids: Iterable[str], *, brief_mode: str = "approved_root"
) -> DagSpec:
    """Build the question-independent logical DAG for one admitted lens set."""

    lens_ids = tuple(lens_ids)
    if brief_mode not in {"approved_root", "draft_and_approve"}:
        raise ValueError(f"Unknown brief mode: {brief_mode}")
    roots = [
        RootPort(
            "problem_brief" if brief_mode == "approved_root" else "policy_question",
            ("problem_brief",) if brief_mode == "approved_root" else ("policy_question",),
        )
    ]
    roots.extend(
        RootPort(f"lens_{lens_id}", ("lens_definition",))
        for lens_id in lens_ids
    )

    brief_nodes: tuple[DagNode, ...] = ()
    problem_source = "root:problem_brief"
    if brief_mode == "draft_and_approve":
        draft_brief = _node(
            "draft_problem_brief",
            kind="llm",
            role="generator",
            stage="problem_framing",
            title="Draft problem brief",
            description=(
                "Turn the admitted raw policy question into a bounded, "
                "epistemically neutral problem-brief proposal."
            ),
            handler="draft_problem_brief",
            inputs=(
                InputBinding(
                    "question", ("root:policy_question",),
                    ("policy_question",), maximum=1,
                ),
            ),
            outputs=("problem_brief_proposal",),
            schemas=_schemas("problem_brief_proposal"),
            generation_parameters=(("max_tokens", 6000),),
        )
        approve_brief = _node(
            "approve_problem_brief",
            kind="human_gate",
            role="deterministic",
            stage="human_gate",
            title="Approve problem brief",
            description=(
                "A human approves one exact problem-brief candidate hash before "
                "any research node may start."
            ),
            handler="approve_problem_brief",
            inputs=(
                InputBinding(
                    "candidate", ("draft_problem_brief",),
                    ("problem_brief_proposal",), maximum=1,
                ),
            ),
            outputs=("problem_brief_decision", "problem_brief"),
            schemas=_schemas("problem_brief_decision", "problem_brief"),
            provider="human",
            model="human-decision",
        )
        brief_nodes = (draft_brief, approve_brief)
        problem_source = "approve_problem_brief"

    research_nodes = tuple(
        _node(
            f"research_{lens_id}",
            kind="llm",
            role="research",
            stage="research",
            title=f"Research: {lens_id.replace('_', ' ')}",
            description=(
                "Research the approved problem through one admitted lens and "
                "produce sourced atomic evidence artifacts."
            ),
            handler="research",
            inputs=(
                InputBinding("problem", (problem_source,), ("problem_brief",), maximum=1),
                InputBinding("lens", (f"root:lens_{lens_id}",), ("lens_definition",), maximum=1),
            ),
            outputs=EVIDENCE_TYPES,
            schemas=_schemas("source", "finding", "assumption", "uncertainty"),
            provider="anthropic",
            model="anthropic-task-ladder",
            generation_parameters=(("search_max_tokens", 10000), ("analysis_max_tokens", 16000)),
        )
        for lens_id in lens_ids
    )
    research_ids = tuple(node.id for node in research_nodes)

    normalize_evidence = _node(
        "normalize_evidence",
        kind="llm",
        role="generator",
        stage="evidence_normalization",
        title="Normalize evidence",
        description=(
            "Turn atomic findings into bounded canonical claims and explicit "
            "evidence conflicts, with an exact disposition for every finding."
        ),
        handler="normalize_evidence",
        inputs=(
            InputBinding("problem", (problem_source,), ("problem_brief",), maximum=1),
            InputBinding("evidence", research_ids, ("finding", "assumption", "uncertainty")),
        ),
        outputs=("canonical_claim", "evidence_conflict", "coverage_ledger"),
        schemas=_schemas("canonical_claim", "evidence_conflict", "coverage_ledger"),
        generation_parameters=(("max_tokens", 30000),),
    )
    option_seeds = _node(
        "derive_option_seeds",
        kind="llm",
        role="generator",
        stage="option_seeds",
        title="Derive option seeds",
        description=(
            "Derive possible change levers from normalized claims and conflicts "
            "without yet clustering them into policy directions."
        ),
        handler="derive_option_seeds",
        inputs=(
            InputBinding("problem", (problem_source,), ("problem_brief",), maximum=1),
            InputBinding("normalized", ("normalize_evidence",), ("canonical_claim", "evidence_conflict")),
            InputBinding("evidence", research_ids, ("finding", "assumption", "uncertainty")),
        ),
        outputs=("option_seed",),
        schemas=_schemas("option_seed"),
        generation_parameters=(("max_tokens", 16000),),
    )
    option_space = _node(
        "cluster_option_seeds",
        kind="llm",
        role="generator",
        stage="option_space",
        title="Cluster option seeds",
        description=(
            "Cluster the complete option-seed set into candidate directions and "
            "record an exact disposition for every seed before human approval."
        ),
        handler="cluster_option_seeds",
        inputs=(
            InputBinding("problem", (problem_source,), ("problem_brief",), maximum=1),
            InputBinding("seeds", ("derive_option_seeds",), ("option_seed",)),
        ),
        outputs=("option_space_proposal", "coverage_ledger"),
        schemas=_schemas("option_space_proposal", "coverage_ledger"),
        generation_parameters=(("max_tokens", 12000),),
    )
    gate = _node(
        "approve_option_space",
        kind="human_gate",
        role="deterministic",
        stage="human_gate",
        title="Approve option space",
        description=(
            "A human approves one exact candidate hash or returns it for a new "
            "derivation. The gate never edits generated content in place."
        ),
        handler="approve_option_space",
        inputs=(
            InputBinding("candidate", ("cluster_option_seeds",), ("option_space_proposal",), maximum=1),
        ),
        outputs=("human_gate_decision", "approved_option_space"),
        schemas=_schemas("human_gate_decision", "approved_option_space"),
        provider="human",
        model="human-decision",
    )
    transformations = _node(
        "derive_transformations",
        kind="llm",
        role="generator",
        stage="transformations",
        title="Derive transformations",
        description=(
            "Build concrete proposals from fresh evidence and one exact "
            "human-approved option-space artifact."
        ),
        handler="derive_transformations",
        inputs=(
            InputBinding("problem", (problem_source,), ("problem_brief",), maximum=1),
            InputBinding("evidence", research_ids, ("finding", "assumption", "uncertainty")),
            InputBinding("normalized", ("normalize_evidence",), ("canonical_claim", "evidence_conflict")),
            InputBinding("option_seeds", ("derive_option_seeds",), ("option_seed",)),
            InputBinding("option_space", ("approve_option_space",), ("approved_option_space",), maximum=1),
        ),
        outputs=(
            "assumption", "uncertainty", "transformation_proposal",
            "transformation_family", "coverage_ledger",
        ),
        schemas=_schemas(
            "assumption", "uncertainty", "transformation_proposal",
            "transformation_family", "coverage_ledger",
        ),
        generation_parameters=(("max_tokens", 30000),),
    )

    assessment_nodes = tuple(
        _node(
            f"assess_{lens_id}",
            kind="llm",
            role="generator",
            stage="assessment",
            title=f"Assess: {lens_id.replace('_', ' ')}",
            description=(
                "Assess every transformation through one admitted lens using "
                "only the proposal and that lens's evidence artifacts."
            ),
            handler="assess_lens",
            inputs=(
                InputBinding("lens", (f"root:lens_{lens_id}",), ("lens_definition",), maximum=1),
                InputBinding("proposals", ("derive_transformations",), ("transformation_proposal",)),
                InputBinding("evidence", (f"research_{lens_id}",), ("finding",)),
            ),
            outputs=("lens_assessment",),
            schemas=_schemas("lens_assessment"),
            generation_parameters=(("max_tokens", 16000),),
        )
        for lens_id in lens_ids
    )
    assessment_ids = tuple(node.id for node in assessment_nodes)

    dilemmas = _node(
        "identify_decision_dilemmas",
        kind="llm", role="generator", stage="synthesis",
        title="Identify decision dilemmas",
        description="Separate evidence-resolvable disputes from residual value conflicts.",
        handler="identify_dilemmas",
        inputs=(
            InputBinding("proposals", ("derive_transformations",), ("transformation_proposal",)),
            InputBinding("assessments", assessment_ids, ("lens_assessment",)),
            InputBinding("findings", research_ids, ("finding",)),
        ),
        outputs=("dilemma",), schemas=_schemas("dilemma"),
        generation_parameters=(("max_tokens", 16000),),
    )
    agenda = _node(
        "build_research_agenda",
        kind="llm", role="generator", stage="synthesis",
        title="Build research agenda",
        description="Turn decision-critical uncertainties into concrete research questions.",
        handler="build_research_agenda",
        inputs=(
            InputBinding("proposals", ("derive_transformations",), ("transformation_proposal",)),
            InputBinding("assessments", assessment_ids, ("lens_assessment",)),
            InputBinding("uncertainties", (*research_ids, "derive_transformations"), ("uncertainty",)),
        ),
        outputs=("research_question",), schemas=_schemas("research_question"),
        generation_parameters=(("max_tokens", 12000),),
    )
    package = _node(
        "assemble_decision_package",
        kind="llm", role="generator", stage="decision_package",
        title="Assemble decision package",
        description="Assemble a public decision package from exact upstream artifacts.",
        handler="assemble_decision_package",
        inputs=(
            InputBinding("problem", (problem_source,), ("problem_brief",), maximum=1),
            InputBinding(
                "transformations", ("derive_transformations",),
                ("transformation_family", "transformation_proposal", "coverage_ledger"),
            ),
            InputBinding("lenses", tuple(f"root:lens_{value}" for value in lens_ids), ("lens_definition",)),
            InputBinding("assessments", assessment_ids, ("lens_assessment",)),
            InputBinding("dilemmas", ("identify_decision_dilemmas",), ("dilemma",)),
            InputBinding("agenda", ("build_research_agenda",), ("research_question",)),
            InputBinding("findings", research_ids, ("finding",)),
            InputBinding("sources", research_ids, ("source",)),
        ),
        outputs=("decision_package",), schemas=_schemas("decision_package"),
        generation_parameters=(("max_tokens", 20000),),
    )
    evaluation = _node(
        "evaluate_decision_package",
        kind="llm", role="judge", stage="evaluation",
        title="Evaluate decision package",
        description="Cross-family evaluation of the visible decision package and its graph.",
        handler="evaluate_decision_package",
        inputs=(
            InputBinding("package", ("assemble_decision_package",), ("decision_package",), maximum=1),
            InputBinding("proposals", ("derive_transformations",), ("transformation_proposal",)),
            InputBinding("assessments", assessment_ids, ("lens_assessment",)),
            InputBinding("dilemmas", ("identify_decision_dilemmas",), ("dilemma",)),
            InputBinding("agenda", ("build_research_agenda",), ("research_question",)),
        ),
        outputs=("evaluation",), schemas=_schemas("evaluation"),
        provider="openai", model="gpt-5-mini",
        generation_parameters=(("max_tokens", 8000),),
    )
    readiness = _node(
        "assess_decision_readiness",
        kind="deterministic", role="deterministic", stage="readiness",
        title="Assess decision readiness",
        description="Apply the deterministic external-use and readiness gate.",
        handler="assess_decision_readiness",
        inputs=(
            InputBinding("package", ("assemble_decision_package",), ("decision_package",), maximum=1),
            InputBinding("evaluation", ("evaluate_decision_package",), ("evaluation",), maximum=1),
            InputBinding("proposals", ("derive_transformations",), ("transformation_proposal",)),
            InputBinding("dilemmas", ("identify_decision_dilemmas",), ("dilemma",)),
            InputBinding("agenda", ("build_research_agenda",), ("research_question",)),
        ),
        outputs=("decision_readiness",), schemas=_schemas("decision_readiness"),
        provider="local", model="deterministic-1.0.0",
    )

    dag = DagSpec(
        id="policy_analysis",
        version=VERSION,
        roots=tuple(roots),
        nodes=(
            *brief_nodes, *research_nodes, normalize_evidence, option_seeds,
            option_space, gate, transformations,
            *assessment_nodes, dilemmas, agenda, package, evaluation, readiness,
        ),
    )
    dag.validate()
    return dag
