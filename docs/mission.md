# Mission

Discover whether a team of AI agents plus human experts can dramatically
accelerate education policy design. AI takes over information processing —
comparison, synthesis, critique, scenario generation. Humans keep judgment,
values, risk assessment and decisions.

The goal is **not** to automate policy decisions. It is to build a system that
makes human policy thinking:

- **faster** — parallel expert analysis and critique in minutes, not months;
- **more transparent** — every claim, assumption and disagreement is written down;
- **more evidence-based** — every important claim carries an evidence status;
- **more explicit about uncertainty** — confidence is never invented;
- **more iterative** — nothing is final, everything is criticizable;
- **easier to criticize and improve** — the system critiques itself, on the record.

This repository is an experiment and a reference implementation for future
Education Policy Labs. We optimize for the **methodology**, not for the demo
topic and not for impressive code.

## First policy question (a demonstration, not the target)

> What should Hungary do with early academic selection and the 6- and 8-year
> secondary grammar school (gimnázium) system?

The pipeline must remain reusable for any policy question.

## Non-negotiable principles

1. AI never makes policy decisions; it improves the speed and quality of reasoning.
2. Every important claim carries an evidence status. Evidence, interpretation,
   assumption and recommendation are strictly separated.
3. Preserve disagreement. Well-structured dissent beats forced consensus.
4. Make uncertainty explicit. Never invent confidence.
5. Build for iteration. Nothing is final; everything is criticizable.
6. The system itself is under continuous review — architecture, workflow,
   agents, rubric and evaluation methods may all change.

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
analysis) and the **societal-discourse layer** (voices that REPRESENT
interests and values — archetypes and named actors with epistemically
labelled positions). The discourse layer exists because policy is decided in
public, not in a lab: the argument ledger records who would support, oppose
or conditionally accept each scenario and why, and the brief must answer
every argument (response obligation).
