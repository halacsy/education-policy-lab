# Education Policy Lab

A bilingual (HU/EN), artifact-first system for mapping education-policy
questions into sourced findings, concrete transformation proposals,
professional assessments, value dilemmas, and a research agenda. The public
site is the **Education Policy Atlas**: it is written first for interested
people who are only beginning to learn how the Hungarian education system
works. AI assists the analysis; **humans keep judgment, values, risk assessment,
knowledge admission, and policy decisions**.

Demonstration question (not the target — the pipeline is reusable):

> What should Hungary do with early academic selection and the 6- and 8-year
> secondary grammar school (gimnázium) system?

## Run it

```bash
.venv/bin/python scripts/run_v2_production.py --topic korai-szelekcio
.venv/bin/python scripts/verify_v2.py
.venv/bin/python scripts/build_v2_production_site.py
.venv/bin/python scripts/build_v2_audit.py
python3 -m http.server 8765 --directory site

# Archived v1 pipeline (kept for reproducibility, no longer the public site)
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

## How the default v2 works

Each topic follows an explicit artifact DAG: **question → sourced findings →
transformation proposals → professional-lens assessments → value dilemmas →
research agenda → decision-readiness report**. JSON Schemas define every
artifact; immutable records and lineage edges preserve how each conclusion was
produced. The website compiles only accepted production stores and exposes the
same lineage in its “How was it made?” view.

## Archived v1 loop

Each round: **experts → scenario builder → editor synthesis → societal
discourse (argument ledger) → translator → critics (incl.
translation_checker) → meta-critic → evaluation → improvement plan → git
commit**. The discourse layer (D-29) models the public debate beside the
expert one: ten voices — six interest/value archetypes and four named actors
(CKP/Tanítanék, PDSZ, Tisza, Egyensúly Intézet) — react to every scenario
with epistemically labelled positions (documented / value-modeled /
no-position), a mediator clusters the arguments without counting heads, the
evidence layer grades their factual claims, and the policy brief must answer
every argument cluster (CNDP-style response obligation). The next round *applies* the plan's single change
(verified by byte-level diff of the `system_state/` snapshot), consults the
Reflexion/ADAS archive (`outputs/topics/<slug>/archive/attempts_log.jsonl`) to never repeat
a failed change, and re-measures. Changes that regress are reverted and
archived as failures.

Design docs: `docs/architecture.md` (pattern basis + cautions),
`docs/workflow.md`, `docs/methodology.md` (the Level-4 method),
`docs/human_role.md`, `docs/decisions.md` (every consequential decision),
per-topic glossaries (`topics/<slug>/glossary.md`, controlled HU↔EN terminology).

## Guarantees enforced by `scripts/verify.py`

Rounds are real (byte-diffed), scores strictly improve then stay
non-decreasing, scenarios carry all ten required fields, critics name
scenario+field, the meta-critic judges gaming explicitly, deliverables are
genuinely bilingual (id/structure/glossary parity, no untranslated copies),
generator≠judge (cross-family), no safety/evidence/critic constraint may be
removed, and held-out qualitative checks (invisible to the improvement step)
guard against Goodharting.
