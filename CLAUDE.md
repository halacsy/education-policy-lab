# CLAUDE.md — Education Policy Lab

Working notes for Claude Code sessions. The owner works in Hungarian; write
user-facing text (issues, PRs, reports, website) in Hungarian, code and
commits in English. This is a PUBLIC repo — never commit secrets or personal
data.

## What this is

A self-improving, bilingual (HU/EN), multi-agent policy-design lab. First
question: early academic selection and the 6/8-year gimnázium in Hungary.
Architecture: orchestrator-workers + evaluator-optimizer, Reflexion/ADAS
archive, Habermas-Machine disagreement preservation. Read `docs/architecture.md`,
`docs/workflow.md`, and the decision log `docs/decisions.md` (D-01…D-29) —
the decision log is the single source of truth for design rationale.

## Ground rules (owner-set, do not violate)

- **Cross-family generator ≠ judge** (verify check 13). Never let one model
  family grade its own output. Role-swap is allowed and validated
  (docs/experiments/2026-07-06-role-swap-robustness.md).
- **One documented change per round**, committed per round; regressions are
  reverted and archived (attempts_log.jsonl). Never weaken verify.py.
- **Fix at system level, not by hand-editing artifacts** ("javítsd
  rendszerszinten" — standing owner instruction).
- **Knowledge admission is human-gated** (D-24): agents propose
  (knowledge/proposals/), humans admit via PR. Same gate for panel changes:
  seat only for a NEW position (sensitivity-tested), documents become
  sources otherwise (issue #12; "szék a pozíciónak, forrás a dokumentumnak").
- **Discourse layer naming** (D-29): agents named for positions/archetypes;
  real organisations only get attributed positions with epistemic labels
  (documented/source, value_modeled/basis, no_position). Unlabelled
  attribution is a validation failure, not a style issue.
- **Only legally redistributable documents** go into knowledge/library/
  (public repo!). Unclear/copyrighted → POINTER.md + link. The stakeholder
  program PDFs (Tanítanék, PDSZ, Tisza, Egyensúly Intézet) are all
  default-copyright: permission contacts recorded in
  knowledge/proposals/2026-07-07-stakeholder-programs.md.
- The `agy` (Antigravity) CLI is an agentic tool: always run it in an
  isolated temp cwd, never in the repo (see lab/llm.py).

## How to run

```
.venv/bin/python scripts/run_mock_sprint.py      # scratch dry-run (gitignored output)
.venv/bin/python scripts/verify.py               # definition-of-done gate (must stay green)
.venv/bin/python scripts/run_iteration_loop.py --max-rounds N [--start-round K]
python3 scripts/build_registry.py --check        # knowledge freshness gate (CI)
```

- `.env` (gitignored — COPY IT MANUALLY to a new machine): GOOGLE_API_KEY,
  ANTHROPIC_API_KEY, GOOGLE_MODEL pin. Use the repo `.venv` (has google-genai).
- Backends: default = API keys. `ANTHROPIC_BACKEND=claude-code` → `claude -p`
  on the subscription. `GOOGLE_BACKEND=agy` → Antigravity CLI (subscription).
  Set `GOOGLE_MODEL=` (empty) to un-pin and let the D-26 ladder work.
- Role swap: `GENERATOR_PROVIDER=anthropic JUDGE_PROVIDER=google`.
- Interrupted runs RESUME (state-hash gate + steps.jsonl); quota limits are
  survivable — relaunch the same command.

## Quota facts (as of 2026-07-08)

- Antigravity (agy) individual quota exhausted by the 2026-07-07 full run;
  resets ~2026-07-14.
- Gemini free-tier API: 20 req/day/model; D-27 breaker spreads across the
  3-model ladder (~60/day effective).
- claude-code CLI backend runs on the owner's Claude subscription — this is
  the cheapest generator path; a discourse-enabled round ≈ 40 generator +
  15-25 judge calls (reciprocity off: −10).

## Current state (2026-07-08, end of session)

- Canonical run on main: rounds 1–5, total 7.322 → 9.265; site deployed via
  Pages (index + explorer + knowledge + tech).
- **Discourse layer (D-29) built and merged to main** (645a59f + fixes):
  10 voices (6 archetypes + CKP/Tanítanék, PDSZ, Tisza, Egyensúly Intézet),
  argument ledger, evidence-graded clusters, reciprocity pass
  (`discourse.reciprocity` toggle), brief response obligation, verify
  check D, explorer discourse view. Model: CNDP + OECD + DQI + Habermas
  Machine (see D-29 and docs/workflow.md step 3.5).
- **Branch `run/live-2026-07-08-claude-gen`**: round 6 live run (Claude
  generates via subscription CLI, Gemini judges) — the FIRST round with a
  real argument ledger (50 clusters from a live mediator). Also carries the
  grading-robustness fix (950b0e8) and the landing-page discourse/ladder
  sections (a699f03). **INTERRUPTED, RESUMABLE**: killed cleanly at the
  translate_ledger step (network switch); everything up to and including the
  10 reciprocity responses + EN ledger is live and committed as a wip
  checkpoint. Resume (the state-hash gate reuses all valid artifacts):
  `GENERATOR_PROVIDER=anthropic JUDGE_PROVIDER=google GOOGLE_MODEL=
  .venv/bin/python scripts/run_iteration_loop.py --start-round 6 --max-rounds 6`
  2026-07-09: the owner bought Anthropic API credit — the generator runs on
  the API now, NOT the claude-code CLI (the CLI's 600s subprocess timeout
  kept killing the long translate_ledger call, and the subscription usage
  cap was hit). MERGE PENDING OWNER REVIEW of results.
- **Branch `site/split-tech`**: landing page split — "what it does" stays on
  index, implementation moved to site/tech.html. Merge with/after the run
  branch (index.html conflicts trivially with a699f03: split-tech supersedes).
- **PR #10 open (owner decision)**: admit `conservative_education` expert to
  the canonical panel (branch exp/conservative-expert, sensitivity experiment
  + report attached). With the discourse layer built, an alternative is to
  close it and rely on the konzervativ_ertekvedo discourse voice instead.

## Open issues (tracker)

- #4 fully live run on billing-enabled keys
- #5 question submission before launch (LAUNCH BLOCKER)
- #6 retrieval over knowledge/library + corpus ingestion
- #7 distributed contributor runs (SETI@home-style, subscription quota)
- #9 panel-composition sensitivity mitigations (evidence-weighted sides,
  perspective-expert type — partially addressed by D-29)
- #12 stakeholder sources: 4 registry facts await human admission; position
  summaries should be SENT TO THE ORGANISATIONS for review + mirroring
  permission (contacts in the proposal file); draft emails on request
- Follow-up idea (in #13 comments): ingest Facebook/journalist voices to
  forecast civil reactions (depends on #6)

## Experiments so far

- docs/experiments/2026-07-06-role-swap-robustness.md — judge swap ±0.06
- docs/experiments/2026-07-07-expert-panel-sensitivity.md — one new expert
  doesn't flip majorities but minority voice attrits between synthesis and
  brief; cheap models silently dropped minority_report in BOTH arms → led to
  D-28 validated contracts + issue #9/#12 design

## Gotchas

- The iteration loop's git commit is `git add -A` — NEVER leave unrelated
  uncommitted work in the tree while a round is running (use a worktree).
- site/explorer.html + site/knowledge.html are GENERATED (gitignored),
  built by CI; edit the build scripts, not the HTML.
- outputs/ is deliberately committed (audit trail); outputs/mock_sprint/ is
  the gitignored scratch.
- Pyright shows false-positive import errors for lab/* relative imports —
  runtime is fine; don't "fix" them.
- knowledge/registry.json is GENERATED from knowledge/sources/*.md
  (build_registry.py); CI fails if stale.
