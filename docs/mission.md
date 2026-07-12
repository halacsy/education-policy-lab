# Mission

**The system's job is not to produce a policy. It is to accelerate the
thinking and the public debate that must precede a policy decision.**

Discover whether a team of AI agents plus human experts can dramatically
accelerate that deliberation. AI takes over information processing —
comparison, synthesis, critique, scenario generation, stress-testing against
likely objections. Humans keep judgment, values, risk assessment and
decisions.

The goal is **not** to automate policy decisions, and the system must never
imply that a single technically-correct answer exists. It is to build a
system that makes human policy thinking and public deliberation:

- **faster** — parallel expert analysis and critique in minutes, not months;
- **more transparent** — every claim, assumption and disagreement is written down;
- **more evidence-based** — every important claim carries an evidence status;
- **more explicit about uncertainty** — confidence is never invented, and what
  we don't yet know is mapped as deliberately as what we do know;
- **more iterative** — nothing is final, everything is criticizable;
- **easier to criticize and improve** — the system critiques itself, on the record;
- **better prepared for the debate itself** — objections, fears and interest
  conflicts that real deliberation will raise are surfaced and structured in
  advance, not discovered mid-debate.

## What the system must answer, for every policy question

Every run must give an explicit account of:

1. **What do we know?** — the evidence-graded expert record (`expert_outputs/`).
2. **How strong is the evidence for it?** — evidence-status tags (strong /
   moderate / weak / contested / assumption), never invented confidence.
3. **Where do experts agree?** — the shared ground synthesis carries forward.
4. **Where is there no expert agreement?** — the disagreement map
   (`synthesis.md`), preserved with rationale, never laundered into false
   consensus.
5. **Which claims are context-dependent?** — which findings travel across
   countries/institutions and which don't (tracked per-source; a formal
   transferability layer is future work, see D-31).
6. **What interventions exist?** — the scenario set (`scenarios.json`),
   deliberately more than one, including a do-nothing/status-quo baseline
   where relevant.
7. **What are each intervention's expected benefits, harms and risks?** —
   scenario fields `expected_benefits`, `political_risks`, plus critic
   objections.
8. **Who wins and who loses?** — `equity_impact`, tested by the
   `equity_checker` critic, and the discourse layer's `affected` field per
   argument cluster.
9. **What trade-offs cannot be removed, only chosen?** — argument clusters
   tagged `value` (as opposed to `fact`) are exactly this; the brief must
   name them, not resolve them.
10. **Which questions require a value choice or a political decision?** —
    `docs/human_role.md` decision-rights table; the brief's "What people must
    decide" section.
11. **What don't we know yet?** — `## Uncertainties` per expert, `Open
    questions`/uncertainty sections; a full unknowns taxonomy (data gaps,
    research gaps, implementation unknowns, unknown-unknowns) is deferred,
    see D-31.
12. **What would it take to know more?** — a structured research/information
    agenda per unknown is deferred, see D-31.
13. **How decision-ready is the question?** — currently expressed through
    evidence-status density and `human_questions.md`; a dedicated
    decision-readiness verdict (ready / pilot-only / needs-research /
    needs-political-decision) is deferred, see D-31.
14. **What must real people still debate and decide?** — `human_questions.md`
    (never empty in a completed run) plus the brief's stakeholder-facing
    sections.

The system does not pretend every question above has a clean answer for
every run — several (5, 11, 12, 13) are only partially addressed today. Where
that's true, say so explicitly rather than papering over the gap.

This repository is an experiment and a reference implementation for future
Education Policy Labs. We optimize for the **methodology**, not for the demo
topic and not for impressive code.

## First policy question (a demonstration, not the target)

> What should Hungary do with early academic selection and the 6- and 8-year
> secondary grammar school (gimnázium) system?

The pipeline must remain reusable for any policy question.

## Non-negotiable principles

1. AI never makes policy decisions; it improves the speed and quality of reasoning.
2. Every important claim carries an evidence status and a type tag — fact,
   estimate, assumption, or value judgment — never blurred together.
3. Preserve disagreement. Well-structured dissent beats forced consensus.
4. Make uncertainty explicit. Never invent confidence.
5. Build for iteration. Nothing is final; everything is criticizable.
6. The system itself is under continuous review — architecture, workflow,
   agents, rubric and evaluation methods may all change.
7. The system never claims to simulate how real people, organisations or the
   public will actually react. Modelled objections, fears and interest
   conflicts are a stress test to be checked against real stakeholders — not
   a forecast, not a substitute for their participation.

## Four levels of the work

| Level | Object of work | Where it lives |
|-------|----------------|----------------|
| L1 | The education policy itself | `outputs/` |
| L2 | The workflow that produces the policy | `docs/workflow.md`, `config/system_config.json` |
| L3 | The agent system that runs the workflow | `agents/`, `scripts/lab/` |
| L4 | The methodology that designs better agent systems | `docs/methodology.md`, `outputs/archive/` |

Most early effort goes into L2–L4. L1 output quality is the *measurement*, not
the product.

L1 has two layers (D-29): the **expert layer** (evidence-graded domain
analysis) and the **societal-discourse layer**, now framed as a **stakeholder
stress test** rather than a simulation of real reactions (D-30) — generic
civil-expert archetypes surface the interests, values, fears and likely
objections a real deliberation will have to answer, each epistemically
labelled. No voice is named after or claims to speak for a real organisation
(D-32): some archetypes are informed by real public documents (a reform
proposal, a union programme, a governing party's statements, a think-tank
report), cited as a value basis, never as an attributed quote — "a seat for
the position, a source for the document" (D-24). The discourse layer exists
because policy is decided in public, not in a lab: the argument ledger
records the expected objections to each scenario and why, and the brief must
answer every argument cluster (response obligation) — but the ledger is a
preparation for real deliberation, not a replacement for it.

## The core promise

The Education Policy Lab does not decide for people. It collects and
organizes what is already known, shows the limits of that knowledge, surfaces
the real alternatives and the conflicts between them, and prepares the
questions that research, policy design, or real human debate must carry
forward.
