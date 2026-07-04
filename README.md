# Education Policy Lab

A self-improving, bilingual (HU/EN), multi-agent policy-design system — an
experiment in whether AI agents plus human experts can dramatically accelerate
education policy design. AI does the information processing (comparison,
synthesis, critique, scenario generation); **humans keep judgment, values,
risk assessment and decisions**.

Demonstration question (not the target — the pipeline is reusable):

> What should Hungary do with early academic selection and the 6- and 8-year
> secondary grammar school (gimnázium) system?

## Run it

```bash
python3 scripts/run_iteration_loop.py --max-rounds 5   # the real loop (commits each round)
python3 scripts/verify.py                              # definition of done; exits 0 iff met
python3 scripts/run_mock_sprint.py                     # 1 deterministic round, no keys, no commits
python3 scripts/evaluate_outputs.py --round 2          # re-score an existing round
git log --oneline                                      # the self-improvement audit trail
```

Providers: `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` (read from `.env`;
`GENERATOR_PROVIDER`=google, `JUDGE_PROVIDER`=anthropic by default — they must
differ). Without keys, everything runs on a deterministic mock built from the
curated briefing pack in `scripts/lab/knowledge.py`.

## How it works

Each round: **experts → scenario builder → editor synthesis → translator →
critics (incl. translation_checker) → meta-critic → evaluation → improvement
plan → git commit**. The next round *applies* the plan's single change
(verified by byte-level diff of the `system_state/` snapshot), consults the
Reflexion/ADAS archive (`outputs/archive/attempts_log.jsonl`) to never repeat
a failed change, and re-measures. Changes that regress are reverted and
archived as failures.

Design docs: `docs/architecture.md` (pattern basis + cautions),
`docs/workflow.md`, `docs/methodology.md` (the Level-4 method),
`docs/human_role.md`, `docs/decisions.md` (every consequential decision),
`docs/glossary.md` (controlled HU↔EN terminology).

## Guarantees enforced by `scripts/verify.py`

Rounds are real (byte-diffed), scores strictly improve then stay
non-decreasing, scenarios carry all ten required fields, critics name
scenario+field, the meta-critic judges gaming explicitly, deliverables are
genuinely bilingual (id/structure/glossary parity, no untranslated copies),
generator≠judge (cross-family), no safety/evidence/critic constraint may be
removed, and held-out qualitative checks (invisible to the improvement step)
guard against Goodharting.
