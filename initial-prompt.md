# Education Policy Lab — build a self-improving, bilingual, multi-agent policy-design system

You are not building an application. You are inventing a reusable methodology
for humans and AI to design education policy together. Your highest priority is
a working, self-improving iteration loop. Everything else serves that loop.

## Mission
Discover whether a team of AI agents plus human experts can dramatically
accelerate education policy design. AI takes over information processing
(comparison, synthesis, critique, scenario generation); humans keep judgment,
values, risk assessment and decisions. The goal is NOT to automate policy
decisions — it is to build a system that makes human policy thinking faster,
more transparent, more evidence-based, more explicit about uncertainty, more
iterative, and easier to criticize and improve.

This repo is an experiment and a reference implementation for future Education
Policy Labs. Optimize for the methodology, not for this one topic or for
impressive code.

## First policy question (a demonstration, not the target)
> What should Hungary do with early academic selection and the 6- and 8-year
> secondary grammar school (gimnázium) system?
Do not overfit to this question. Build a reusable pipeline.

## Design basis (build on known patterns, do not reinvent)
This system deliberately instantiates established research patterns. Name them
in `docs/architecture.md` and respect their documented cautions:
- Orchestrator-workers + evaluator-optimizer (Anthropic, "Building Effective
  Agents"): experts are workers under an orchestrator; the critic→improvement
  cycle is evaluator-optimizer. Caution: evaluator-optimizer becomes circular if
  the evaluator cannot reliably tell good from bad — so ground evaluation in
  objective checks and a debiased judge (see Evaluator protocol).
- Self-Refine / Reflexion: keep episodic memory of past failures and feed it
  into the next round.
- ADAS / Meta Agent Search: the Level-4 meta layer proposes better agents from a
  growing ARCHIVE of prior designs and their scores; never repeat a change the
  archive shows already failed. Safety caveat from ADAS: the meta layer must
  refuse to create dishonest, unsafe, or evidence-weakening agents.
- Habermas Machine (Tessler et al., Science 2024) for synthesis: incorporate
  opinions AND critiques, represent minority viewpoints proportionally, and do
  NOT collapse into forced consensus (per principle 3). Prefer mapping the
  geometry of disagreement over distilling a single consensus.

## Language policy
- The system itself — code, `docs/`, agent specifications, templates, rubric,
  evaluation files, git commit messages — is written in **English** for
  stability and reuse by other labs.
- The **policy deliverables are bilingual (Hungarian + English)** so Hungarian
  stakeholders and EU colleagues can both use them. Specifically the scenario
  set, `final_brief` and `executive_summary` each exist in both `*.hu.md` and
  `*.en.md`.
- Maintain a controlled bilingual terminology glossary at `docs/glossary.md`
  (e.g. gimnázium, korai szelekció / early selection, egységes alapiskola /
  comprehensive school). The `translator` uses it; the `translation_checker`
  enforces it.

## Your role and autonomy
Act as a senior AI architect, research director and multi-agent systems
designer. You are expected to challenge the design itself.
- Work autonomously and continuously. **Do NOT ask for clarification.** Make
  reasonable decisions and record each one, with its rationale, in
  `docs/decisions.md`.
- **First design the architecture in `docs/`, then implement the minimal working
  loop based on that architecture.** Do not stop at documentation.
- Priorities, in order: (1) a better *process*, (2) better *agents*,
  (3) better *workflows*, (4) only then policy outputs.
- Prefer the simplest design that passes `verify.py`. An agent that does not
  measurably raise any rubric dimension across two rounds must be flagged in
  `meta_critique.md` as a removal candidate, with the evidence.

## Non-negotiable principles
1. AI never makes policy decisions; it improves speed and quality of reasoning.
2. Every important claim carries an evidence status. Keep evidence,
   interpretation, assumption and recommendation strictly separated.
3. Preserve disagreement. Well-structured dissent beats forced consensus.
4. Make uncertainty explicit. Never invent confidence.
5. Build for iteration. Nothing is final; everything is criticizable.
6. The system itself is under continuous review — architecture, workflow,
   agents, rubric and evaluation methods may all change.

## Four levels — spend most early effort on 2–4
- L1: the education policy itself
- L2: the workflow that produces the policy
- L3: the agent system that runs the workflow
- L4: the methodology that designs better agent systems

## Primary deliverable: a loop that improves the system that makes the policy
The project is complete only when ALL of these succeed:
```bash
python scripts/run_iteration_loop.py --max-rounds 5
python scripts/verify.py       # exits 0 only if the definition of done is met
git log --oneline              # shows one commit per round, naming each change
```
`run_iteration_loop.py` must actually run rounds and write real files. Each round
must produce policy content AND at least one documented change to the system.

## LLM harness (two providers, generator ≠ judge)
Route every model call through a single function `call_model(prompt, role, ...)`
in `lab/llm.py`. Two provider backends are configured via env vars:
- `ANTHROPIC_API_KEY`  -> Claude backend
- `GOOGLE_API_KEY`     -> Gemini backend
- `GENERATOR_PROVIDER` (default "google") and `JUDGE_PROVIDER`
  (default "anthropic") must resolve to DIFFERENT providers; `verify.py` fails
  if they are equal. The direction is swappable in one line; document the choice
  in `docs/decisions.md`. (Note: whichever model handles Hungarian better is the
  better default JUDGE for translation_fidelity — record the rationale.)
If neither key is set, fall back to deterministic mock outputs built from a
small curated briefing pack in `lab/knowledge.py`. No agent may call a model any
other way. Generation agents (experts, synthesis, translator) use the generator
provider; scoring agents (critics, evaluator, meta_critic) use the judge
provider. State clearly in the final report what is still mocked.

## Evaluator protocol (mitigate LLM-as-judge bias)
- Generator and judge providers MUST differ (cross-family) to limit
  self-preference / family bias.
- Prefer deterministic/rule-based checks over LLM judgment wherever a rubric
  item is mechanically checkable (field presence, structure, glossary, diffs).
- For any LLM-scored dimension: run N>=3 trials, RANDOMIZE option/order each
  trial (position debiasing), and record mean AND variance in `evaluation.json`.
- Never let a model judge its own generations. Role rotation is allowed ONLY as
  a robustness cross-check (each provider scores the other's output in a
  separate pass); never as self-scoring and never naively averaged.
- Cross-check rule: if the two providers' scores on a dimension diverge beyond a
  stated threshold, do NOT average — flag that dimension for human review in
  `human_questions.md` and lower its confidence.
- If more than two judges are ever used, aggregate with a ROBUST estimator
  (trimmed mean / median), not a plain mean, and require disjoint model families.
- Control for verbosity: length alone must not raise a score.
- `translation_fidelity` must not rely on an LLM judge alone (judge reliability
  degrades across languages): use deterministic parity + glossary + a
  back-translation check, and flag residual uncertainty for a human.

## Git (version every iteration — the audit trail of self-improvement)
- `git init` at the start; commit the initial scaffold as
  `init: architecture + scaffold`.
- After Initialize and after EVERY round, commit with a message naming the
  concrete change applied, e.g.
  `round-02: add uncertainties+equity fields to scenarios (weakest dimension)`.
- Never amend or squash across rounds; the history must show the progression.
- Add a `.gitignore` for Python caches / local env. Do NOT ignore `outputs/` —
  the generated rounds must be committed so the improvement trail is inspectable.

## Definition of done — encode as assertions in `scripts/verify.py`
`verify.py` must exit non-zero unless ALL of the following are objectively true.
Do not weaken the checks to pass them; fix the system instead.
1. At least 2 complete rounds ran and their folders exist.
2. Each round wrote a machine-readable `evaluation.json` with numeric
   per-dimension scores (with variance where LLM-judged) and a `total`.
3. `total(round_02) > total(round_01)` (strictly). More generally, scores are
   non-decreasing across rounds until they plateau.
4. Each round after the first differs from the previous by a real change to at
   least one of: agent prompts, workflow, rubric, critic criteria, synthesis
   format, or stopping logic. `verify.py` diffs the relevant files/config
   between rounds and FAILS if they are byte-identical (anti-faking).
5. At least 3 policy scenarios exist, each containing every field: goal,
   mechanism, evidence_status, assumptions, expected_benefits, equity_impact,
   cost_categories, implementation_steps, political_risks, uncertainties.
6. Critic outputs contain concrete, targeted objections (each naming a specific
   scenario id AND a specific field), not generic feedback.
7. A meta-critic output evaluates the agent SYSTEM itself, not just the policy.
8. The final brief separates evidence, interpretation, assumptions,
   recommendations and open questions into distinct sections.
9. The system explicitly states where human expert judgment is required
   (`human_questions.md` is non-empty).
10. The repo is a git repository with at least one commit per completed round,
    and commit messages name the change applied that round. `verify.py` reads
    `git log` and fails if rounds are not represented.
11. Policy deliverables are bilingual: the scenario set, `final_brief` and
    `executive_summary` each exist as both `*.hu.md` and `*.en.md`.
12. A `translation_checker` output verifies HU↔EN parity: identical scenario-id
    sets, matching section structure, no missing sections, terminology
    consistent with `docs/glossary.md`. `verify.py` FAILS if a language version
    is byte-identical to the other (untranslated copy) or if structure or
    scenario-id sets differ between languages.
13. `GENERATOR_PROVIDER != JUDGE_PROVIDER`.
14. No core safety/evidence/critic constraint was removed to raise a score
    (anti-gaming, see below).

## Anti-faking and anti-gaming (Goodhart) rules
- Do not copy an output into a new folder and call it a new round. Do not
  produce a HU file that is just a copy of the EN file. Do not tune `verify.py`
  to pass without real improvement.
- The rubric is a necessary, not sufficient, signal. Hold out a subset of
  qualitative checks NOT visible to the improvement step.
- Each round the `meta_critic` must judge whether score gains reflect genuine
  quality or rubric-gaming, and say so explicitly.
- Improvements that raise the score by weakening evidence discipline, removing a
  critic, or reducing preserved disagreement are prohibited and must be reverted.
- If no meaningful improvement is possible, stop and explain why. Each real
  round must contain a diffable change and its own commit.

## What "measurably better" means (operational)
- The evaluation rubric is code plus a spec in `templates/evaluation_rubric.md`.
- Dimensions must include at least: scenario_completeness, evidence_discipline,
  critic_concreteness, layer_separation, meta_system_eval,
  disagreement_preservation, uncertainty_explicitness, and translation_fidelity.
- Every round writes `outputs/iterations/round_XX/evaluation.json` and a
  human-readable `evaluation.md`.
- The `improvement_plan.md` for a round must name the weakest rubric dimension,
  the specific change to make, and the expected effect — then the NEXT round
  must actually apply it (verified by diff, per check 4), consulting the archive
  first to avoid repeating a failed change.
- Stopping logic: stop when max rounds is reached, OR the total-score delta is
  below a stated threshold for two consecutive rounds (marginal improvement),
  OR a decision genuinely needs a human. If you stop early, explain why in the
  final report and in `human_questions.md`.

## The iteration loop
```
Initialize      create initial agent specs, workflow, rubric, config, glossary
Round 1  RUN     run experts → synthesis → translator → critics (incl.
                 translation_checker) → meta-critic → score → improvement_plan
Round 2  IMPROVE apply the documented change → rerun → compare with round 1
Round 3+ REPEAT  until acceptance criteria met, max rounds, marginal gain,
                 or human input required
```
Every round must answer, in `improvement_plan.md`: What got better? What is
still weak? Which agent failed? Which workflow step failed? Which critique was
too vague? Was any translation inconsistent? Did the two judges disagree
anywhere? Are score gains genuine or rubric-gaming? What changes next round?
Continue, stop, or ask a human?

## Deliberation discipline (synthesis agents)
- Do not optimize for consensus. Produce a "disagreement map" listing where
  experts/critics diverge and why.
- Minority and dissenting positions must survive into `final_brief` with their
  rationale, represented proportionally, never silently dropped.
- Generate multiple candidate framings of each scenario before selecting; record
  the rejected framings in the round folder.

## Repository layout
```
education-policy-lab/
  README.md
  .gitignore
  docs/            mission.md architecture.md workflow.md methodology.md
                   human_role.md decisions.md glossary.md
  agents/          meta/ experts/ critics/ synthesis/
  templates/       agent_template.md scenario_template.md evaluation_rubric.md
  scripts/         run_iteration_loop.py run_mock_sprint.py evaluate_outputs.py
                   verify.py   lab/ (supporting package: llm.py knowledge.py ...)
  outputs/         (generated, committed)
```

## Required agents
Meta: policy_architect, workflow_designer, agent_designer, evaluation_designer,
iteration_manager, meta_critic.
Experts: hungarian_education_system, international_comparison, finnish_reform,
polish_reform, portuguese_reform, equity_and_social_mobility, demography,
school_network_planning, education_finance, legal_and_governance,
political_feasibility, implementation_planning.
Critics: devil_advocate, evidence_checker, assumption_checker, equity_checker,
feasibility_checker, cost_checker, political_risk_checker, coherence_checker,
translation_checker.
Synthesis: editor, scenario_builder, translator, final_brief_writer,
executive_summary_writer.

Each agent file must include: Name, Role, Mission, Inputs, Outputs, Rules,
Evidence discipline, Uncertainty discipline, Failure modes, Self-critique
questions, Output template. For `translator` and `translation_checker`, also
specify how they use and update `docs/glossary.md`.

## Round, archive, and final outputs
```
outputs/iterations/round_XX/
  expert_outputs/  synthesis.md  critic_outputs/  meta_critique.md
  evaluation.json  evaluation.md  improvement_plan.md
  revised_agents.md  revised_workflow.md  rejected_framings.md
outputs/archive/
  agent_versions/      every agent version with its round and score
  attempts_log.jsonl   each attempted change: what, expected delta, actual delta
outputs/final/
  final_brief.en.md         final_brief.hu.md
  executive_summary.en.md   executive_summary.hu.md
  scenarios.en.md           scenarios.hu.md
  final_scorecard.md  agent_change_log.md  workflow_change_log.md
  disagreement_map.md  translation_report.md  human_questions.md
```
The improvement step MUST read `attempts_log.jsonl` and avoid re-trying changes
that previously produced no gain (Reflexion/ADAS-style memory).

## Work plan (proceed through these without stopping to ask)
0. `git init`; write `docs/architecture.md`, `workflow.md`, `methodology.md`,
   `human_role.md`, `glossary.md`, `decisions.md`; commit `init: architecture + scaffold`.
1. Scaffold the repo, agent specs, templates, `lab/` package.
2. Implement the loop, two-provider mock harness, rubric, evaluation (with the
   Evaluator protocol), improvement logic, archive, translator and
   translation_checker.
3. Run `run_iteration_loop.py --max-rounds 3`; confirm files appear; commit each
   round with a message naming its change.
4. Run `verify.py`. If it fails, improve the SYSTEM (not the test) and rerun,
   iterating until it passes and gains go marginal.
5. Write the report below.

## Constraints
Plain Python (standard library only for the mock path) and Markdown unless there
is a strong, documented reason otherwise. Real LLM calls may use the official
`anthropic` and `google-genai` SDKs, imported lazily so the mock path needs no
dependencies. No web app. No unnecessary dependencies. `git` may be invoked via
subprocess.

## After building, report
1. What you created. 2. How the loop works. 3. What improved between rounds
   (cite the numeric scores). 4. What is still mocked. 5. What to connect to
   real LLM APIs next. 6. What the next human decision is.
