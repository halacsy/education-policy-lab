# Architecture

The system deliberately instantiates established multi-agent research patterns.
Each pattern is named here with the caution its own literature documents, and
the mitigation we implement.

## Design basis (known patterns, not reinvention)

### 1. Orchestrator–workers + evaluator–optimizer
*(Anthropic, "Building Effective Agents")*

- The **iteration manager** (`scripts/run_iteration_loop.py` + `lab/pipeline.py`)
  is the orchestrator. **Experts**, **synthesis agents** and **critics** are
  workers with narrow, written specifications in `agents/`.
- The critic → evaluation → improvement cycle is an **evaluator–optimizer**
  loop: the evaluator scores each round against the rubric; the optimizer
  (improvement step) applies one targeted change to the system before the next
  round.
- **Documented caution:** evaluator–optimizer becomes circular if the evaluator
  cannot reliably tell good from bad. **Mitigation:** evaluation is grounded in
  deterministic, rule-based checks wherever a rubric item is mechanically
  checkable, and the LLM-judged remainder follows the debiased Evaluator
  protocol below (cross-family judge, N≥3 randomized trials, variance
  reporting, verbosity control, divergence → human escalation).

### 2. Self-Refine / Reflexion (episodic memory of failure)

- `outputs/archive/attempts_log.jsonl` records every attempted system change:
  what was changed, the expected score delta, and the actual delta measured in
  the following round.
- The improvement step **must read this log first** and may not re-try a change
  the archive shows already failed (produced no gain). This is the
  Reflexion-style episodic memory feeding the next round.

### 3. ADAS / Meta Agent Search (the Level-4 meta layer)

- `outputs/archive/agent_versions/` is the growing **archive** of prior agent
  designs with the round and score they participated in.
- The meta layer (improvement step + `meta_critic`) proposes better agents
  from this archive; it never repeats a change the archive shows already
  failed.
- **Safety caveat from ADAS, enforced in code:** the meta layer refuses to
  create dishonest, unsafe or evidence-weakening agents. Concretely,
  `lab/improve.py` maintains a list of *forbidden regressions* (removing a
  critic, dropping evidence-status requirements, deleting disagreement
  sections, weakening the rubric) and `scripts/verify.py` check 14 fails the
  build if any of them ever happens between rounds.

### 4. Habermas Machine (Tessler et al., Science 2024) for synthesis

- Synthesis incorporates opinions **and** critiques, represents minority
  viewpoints proportionally, and does **not** collapse into forced consensus.
- We prefer **mapping the geometry of disagreement** over distilling a single
  consensus: every round produces a *disagreement map* (who diverges, on what,
  and why), and minority positions survive into `final_brief` with their
  rationale. `verify.py` and the `disagreement_preservation` rubric dimension
  enforce this.

## Component overview

```
                       ┌─────────────────────────────────────────┐
                       │  run_iteration_loop.py  (orchestrator)  │
                       └───────────────┬─────────────────────────┘
                                       │ per round
   agents/ specs ──► lab/pipeline.py ──┼──────────────────────────────┐
                                       ▼                              │
   1 EXPERTS (12)  ── generator ──► expert_outputs/*.md               │
   2 SCENARIO_BUILDER ─ generator ─► scenarios.json + scenarios.en.md │
   3 EDITOR (synthesis) ─ generator ─► synthesis.md, rejected_framings│
   4 TRANSLATOR ── generator ──► scenarios.hu.md, brief.hu.md         │
   5 CRITICS (9, incl. translation_checker) ── judge-side inputs ──►  │
        critic_outputs/*.md  (targeted objections: scenario id+field) │
   6 META_CRITIC ── judge ──► meta_critique.md (system-level)         │
   7 EVALUATION (lab/evaluation.py) ──► evaluation.json / .md         │
        deterministic checks + debiased LLM-judge trials              │
   8 IMPROVEMENT (lab/improve.py) ──► improvement_plan.md             │
        reads attempts_log.jsonl; next round applies the change ◄─────┘
   9 git commit  round-XX: <the concrete change applied>
```

## LLM harness

Every model call goes through **one function**: `call_model(prompt, role, ...)`
in `scripts/lab/llm.py`. No agent may call a model any other way.

- `ANTHROPIC_API_KEY` → Claude backend (lazy `anthropic` SDK import).
- `GOOGLE_API_KEY` → Gemini backend (lazy `google-genai` SDK import).
- `GENERATOR_PROVIDER` (default `google`) and `JUDGE_PROVIDER` (default
  `anthropic`) **must differ**; `verify.py` fails otherwise. The direction is
  swappable in one line in `config/system_config.json`; rationale in
  `docs/decisions.md` (the stronger Hungarian-language model should judge
  `translation_fidelity`).
- Generation agents (experts, synthesis, translator) use the generator
  provider. Scoring agents (critics, evaluator, meta_critic) use the judge
  provider. A model never judges its own generations.
- If neither key is set, `call_model` falls back to **deterministic mock
  outputs** composed from the curated briefing pack in `scripts/lab/knowledge.py`.
  The mock backend reads the agent specification embedded in the prompt —
  including `DIRECTIVE:` markers added by the improvement step — so prompt
  changes causally change outputs. This keeps the improvement loop *real* (a
  measured behavioural consequence of a system change), not simulated.

## Evaluator protocol (LLM-as-judge bias mitigation)

1. Generator and judge providers must be different model families
   (self-preference / family-bias limit).
2. Deterministic, rule-based checks are preferred wherever a rubric item is
   mechanically checkable: field presence, structure, glossary conformance,
   diffs, ID-set parity.
3. Every LLM-scored dimension runs **N ≥ 3 trials with randomized
   option/section order** (position debiasing); `evaluation.json` records
   mean **and** variance.
4. Role rotation is used only as a robustness **cross-check**: each provider
   scores the other's output in a separate pass. Never self-scoring, never
   naively averaged.
5. **Divergence rule:** if the two providers' scores on a dimension diverge
   beyond the threshold in `config/system_config.json`, the scores are NOT
   averaged; the dimension is flagged for human review in
   `human_questions.md` and its confidence is lowered.
6. If more than two judges are ever used: robust aggregation (median /
   trimmed mean) and disjoint model families required.
7. Verbosity control: length alone must not raise a score; length-linked
   sub-scores are capped.
8. `translation_fidelity` never relies on an LLM judge alone: deterministic
   structural parity + glossary conformance + a back-translation check are
   the primary signal, and residual uncertainty is flagged for a human.

## Anti-Goodhart design

The rubric is a necessary, not sufficient, signal:

- A **held-out qualitative checklist** (`scripts/lab/holdout_checks.py`) runs
  at verification time and is *not* visible to the improvement step (it is
  excluded from the weakest-dimension selection input).
- Every round the `meta_critic` explicitly judges whether score gains are
  genuine quality or rubric-gaming.
- Forbidden regressions (see ADAS caveat above) are reverted and fail
  verification.
- Byte-identical round outputs, untranslated HU copies, and unchanged system
  state between rounds all fail `verify.py`.
