# Workflow

The workflow is Level 2 of the system: the repeatable process that turns a
policy question into criticizable, bilingual policy artifacts. It is itself an
object of improvement — rounds may change it (documented in
`revised_workflow.md` and versioned in `config/system_config.json`).

## The iteration loop

```
Initialize      create initial agent specs, workflow, rubric, config, glossary
Round 1  RUN     experts → scenario_builder → editor synthesis → translator
                 → critics (incl. translation_checker) → meta_critic
                 → score → improvement_plan
Round 2  IMPROVE apply the documented change → rerun → compare with round 1
Round 3+ REPEAT  until acceptance criteria met, max rounds, marginal gain,
                 or human input required
```

## Steps inside a round

| # | Step | Agents | Provider | Output |
|---|------|--------|----------|--------|
| 1 | Expert analysis | 12 experts | generator | `expert_outputs/<name>.md` |
| 2 | Scenario building | scenario_builder (>=5 scenarios incl. a "none" no-intervention baseline and a "pilot" variant, D-31 B4) | generator | `scenarios.json`, `scenarios.en.md` |
| 3 | Synthesis | editor | generator | `synthesis.md` (incl. disagreement map), `rejected_framings.md` |
| 3.5 | Societal discourse (D-29) | 10 discourse voices + discourse_mediator + evidence_checker | generator (grading: judge) | `discourse/` (voice JSONs, argument map, grades, reciprocity), `argument_ledger.en.md` / `.hu.md` |
| 4 | Translation | translator | generator | `scenarios.hu.md`, `brief.hu.md`, `argument_ledger.hu.md` |
| 5 | Critique | 9 policy critics (incl. context_transferability_checker, D-31 B1) + translation_checker | judge | `critic_outputs/<name>.md` |
| 5.5 | Unknowns + research agenda (D-31 B2/B3) | unknowns_mapper + translator | generator | `unknowns.en.md`, `unknowns.hu.md` |
| 5.6 | Decision readiness (D-31 B4) | decision_readiness_writer | generator | `decision_readiness.md` |
| 6 | Meta-critique | meta_critic | judge | `meta_critique.md` |
| 7 | Evaluation | evaluation_designer's rubric, run by `lab/evaluation.py` | judge + deterministic | `evaluation.json`, `evaluation.md` |
| 8 | Improvement planning | iteration_manager + archive | judge | `improvement_plan.md`, `revised_agents.md`, `revised_workflow.md` |
| 9 | Commit | — | — | `round-XX: <concrete change>` |

Step 3.5 (the argument ledger — a **stakeholder stress test**, not a
simulation of real reactions (D-30); model: CNDP response obligation + OECD
deliberative standards + DQI format rules + Habermas-Machine aggregation):
voices REPRESENT interests/values — they are not experts, and their output
must never be read as a prediction of what real people or organisations will
actually think. Each voice reacts to every scenario with stance {support /
oppose / conditional / no_position}, a justification, a change-condition and
an epistemic label {documented(source) / value_modeled(basis) / no_position}.
The mediator clusters arguments (A1..An, never counting heads) and decomposes
each cluster into interest / value / fear / affected actors / underlying
assumption / empirical uncertainty / decision relevance, and screens it for
"gumicsont" status (high attention, low decision-relevance); the evidence
layer grades factual claims against the registry; a reciprocity pass (config:
`discourse.reciprocity`) makes each voice answer its strongest
counter-argument. The brief MUST answer every cluster with a typed response
('## Responses to public arguments' / '## Válaszok a társadalmi érvekre') —
enforced by validation, not good will. Voice conditions feed the
political_feasibility expert's memory next round.

At the **start** of round N+1 the change planned in round N is actually applied
to the agent specs / config (verified by diff), after consulting
`outputs/archive/attempts_log.jsonl` to avoid repeating failed changes.

## Every round must answer (in `improvement_plan.md`)

- What got better? What is still weak?
- Which agent failed? Which workflow step failed?
- Which critique was too vague?
- Was any translation inconsistent?
- Did the two judges disagree anywhere?
- Are score gains genuine or rubric-gaming?
- What changes next round? Continue, stop, or ask a human?

## Stopping logic

Stop when **any** of these holds (parameters in `config/system_config.json`):

1. `--max-rounds` reached.
2. Total-score delta below `plateau_delta` for two consecutive rounds
   (marginal improvement).
3. A decision genuinely needs a human (blocking question written to
   `human_questions.md`).

Early stops are explained in the final report and in `human_questions.md`.

## Deliberation discipline (synthesis agents)

- Do not optimize for consensus. Produce a **disagreement map** listing where
  experts/critics diverge and why.
- Minority and dissenting positions survive into `final_brief` with their
  rationale, represented proportionally, never silently dropped.
- Generate multiple candidate framings of each scenario before selecting;
  rejected framings are recorded in the round folder
  (`rejected_framings.md`).

## Language flow

- System artifacts: English.
- Policy deliverables: bilingual. The translator produces `*.hu.md` from the
  English originals using `docs/glossary.md`; the `translation_checker`
  enforces ID-set parity, section-structure parity, glossary conformance and
  non-identity (a HU file byte-identical to EN fails).

## Git discipline

- One commit per round, message naming the concrete change applied
  (e.g. `round-02: add quantified-uncertainty directive to scenario_builder
  (weakest: uncertainty_explicitness)`).
- Never amend or squash across rounds. `outputs/` is committed — the
  improvement trail must be inspectable.
