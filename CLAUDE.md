# CLAUDE.md — Education Policy Lab

Working notes for Claude Code sessions. The owner works in Hungarian; write
user-facing text (issues, PRs, reports, website) in Hungarian, code and
commits in English. This is a PUBLIC repo — never commit secrets or personal
data.

## What this is

A self-improving, bilingual (HU/EN), multi-agent, MULTI-TOPIC
deliberation-acceleration lab: many policy problems run through the same
system and shared expert hub (D-35), each as a topic under `topics/<slug>/`.
First topic: `korai-szelekcio` (early academic selection and the 6/8-year
gimnázium). Architecture: orchestrator-workers + evaluator-optimizer,
Reflexion/ADAS archive, Habermas-Machine disagreement preservation. Read
`docs/architecture.md`, `docs/workflow.md`, and the decision log
`docs/decisions.md` (D-01…D-36) — the decision log is the single source of
truth for design rationale.

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

Multi-topic since D-35: every entry point takes `--topic <slug>` (default:
config `default_topic` = korai-szelekcio). New topic (D-36): `new_topic.py
draft` (free text → problem-brief proposal) → human `approve` → round 1
stops at the emergent-framing gate → human `approve-frames` → relaunch
resumes with the expert outputs reused.

```
.venv/bin/python scripts/run_mock_sprint.py [--topic S]   # scratch dry-run (gitignored)
.venv/bin/python scripts/verify.py [--topic S]            # definition-of-done gate, PER TOPIC
.venv/bin/python scripts/run_iteration_loop.py [--topic S] --max-rounds N [--start-round K]
.venv/bin/python scripts/new_topic.py draft --text "..."  # intake; then: approve, approve-frames
python3 scripts/build_registry.py --check                 # knowledge freshness gate (CI)
python3 scripts/build_site_topics.py                      # topic-browser pages (CI)
```

- `.env` (gitignored — COPY IT MANUALLY to a new machine): GOOGLE_API_KEY,
  ANTHROPIC_API_KEY, GOOGLE_MODEL pin. Use the repo `.venv` (has google-genai).
- Backends: default = API keys. `ANTHROPIC_BACKEND=claude-code` → `claude -p`
  on the subscription. `GOOGLE_BACKEND=agy` → Antigravity CLI (subscription).
  `OPENAI_BACKEND=codex` → `codex exec` on the ChatGPT subscription (D-33;
  third provider, no API key needed — auth is `codex login`'s own stored
  credentials). Set `GOOGLE_MODEL=` (empty) to un-pin and let the D-26
  ladder work (openai has no ladder yet — omit `OPENAI_MODEL` to use the
  account's default model).
- Role swap: `GENERATOR_PROVIDER=anthropic JUDGE_PROVIDER=google` (or
  `JUDGE_PROVIDER=openai OPENAI_BACKEND=codex` to judge on Codex instead —
  useful when Gemini's free-tier daily cap is exhausted).
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

## Current state (2026-07-15, end of session)

- **MULTI-TOPIC SPRINT DONE on main (D-35 + D-36, 2026-07-15, pushed;
  commits 2558dc8..7acbc59).** Per-topic config/state/outputs + scoped
  round commits; problem-brief intake + emergent framing (SCENARIO_ANCHORS
  deleted, human gates via scripts/new_topic.py); per-topic time/token/USD
  metering (lab/metering.py, final/cost_report); topic-browser site
  (build_site_topics.py). API keys ROTATED (owner-confirmed 2026-07-15).
- **kisiskolák LIVE ACCEPTANCE PASSED (2026-07-15, this session, on
  main; #21 CLOSED).** Topic `rural-school-closures` ran the full D-36
  path live: intake draft → owner approved the problem brief → round 1
  stopped at the frames gate → owner sent the proposal BACK (missing
  frame) → re-derivation → owner approved 5 frames → round completed,
  total 9.482 (new-era baseline, delta=None), zero mock/failed steps in
  the final journal; verify green on BOTH topics (regressziómentesség);
  topic page published. Generator anthropic (sonnet + haiku for
  reciprocity), judge openai gpt-5-mini.
  **New mechanism born from the gate (db5c947): `new_topic.py reframe
  --topic S --feedback "..."`** — the sanctioned alternative to
  hand-editing frames: feedback lands in proposals/frames-feedback.md
  (dated audit trail), frames_proposal.json is removed, the relaunched
  run re-derives at the gate. First use: the owner asked for a
  grade-structure frame (alsó tagozat a faluban, felső/ISCED 2 a
  városban); it was derivable (polish_reform's 1999 structural-reform
  record) and came back emergently as S2.
  Acceptance findings to fix (system-level, not yet done — FILED as
  issues #22 metering, #23 web-search dropout, #24 verify check 13,
  #25 env bootstrap, 2026-07-15; #4/#16/#17/#18/#21 CLOSED as solved):
  (a) METERING UNDERCOUNT on resumed rounds — metering.update_round_log
  OVERWRITES round_log tokens per leg, so a gate-stopped/resumed round
  only reports the LAST leg (cost_report says $1.02/493K tokens/40m for
  what was really 3 live legs, ~95 min round compute; leg-1 expert
  web-search tokens, the priciest part, are unreported). True total
  estimated ~$8-12 (well under the $40 ceiling), verifiable on provider
  consoles.
  (b) pricing.usd_per_mtok in config lacks gpt-5-mini, so openai judge
  tokens show in totals but are silently unpriced in the per-model table.
  (c) WEB SEARCH WAS DOWN FOR THE WHOLE ROUND (correction of an earlier
  in-session claim that 11/12 searched live): "server tool-use limit
  exceeded" in 8/12 research files, 0 URLs in ALL 12 — the round ran on
  domain knowledge. The system was honest about it (agents flagged it,
  the brief carries it as a strong-evidence fact, affected claims tagged
  weak) — but don't cite this round's numbers as freshly sourced. #23
  has the full picture; a later sourced round is the fix, not rewriting
  the baseline.
  (d) `openai` pip package was missing from THIS machine's .venv (the
  round-8 machine had it) — installed 2026-07-15; add to a requirements
  note. Also: verify check 13 reads config defaults (generator=google,
  judge=anthropic), not the env vars the round actually ran with — it
  passed, but it validates the wrong thing for env-overridden runs.
  Extra API quirks beyond the round-8 lessons below (learned live, easy to
  re-hit): a "Grammar compilation timed out" 400 is TRANSIENT (retry works),
  unlike "compiled grammar too large"; models over-fill unbounded arrays —
  cap list sizes in instruction prose, not just token budgets; gpt-5-mini
  judge occasionally returns an empty response (the retry loop handles it).
- **Branch `refactor/structured-agents`** (D-34, MERGED to main 3187c5b;
  detail below kept for archaeology) (was: this session, off
  refactor/deliberation-mission): structured/bilingual/tool-using agent
  refactor. Owner-approved plan + evidence in
  `docs/proposals/2026-07-14-structured-bilingual-agents.md` (owner answers
  recorded: API cost OK, rounds 1-7 closed as archive era, web search rides
  with Phase 2). **Phase 1 DONE** (8f81df8): `llm.call_structured()`
  (output_config.format / Gemini response_schema), silent mock fallback
  REMOVED — StepFailed + resume instead; mock only under LAB_FORCE_MOCK=1.
  Session findings that motivated it: round 6's brief was entirely
  mock-written (inflated scores); all 17 round-7 fallbacks were translate_*
  steps (CLI 600s timeout on ~180K-token batches); instruction-based
  bilingual output does NOT work, schema-constrained does (test scripts on
  the branch); web search upgrades expert evidence weak→strong
  (test_websearch_expert.py, includes the pause_turn loop). **Phase 2 + P4
  DONE** (this session, task-by-task commits d03ac7d..): every
  generator/judge artifact is bilingual {en,hu} schema-constrained JSON
  (`lab/schemas.py`), every .md a deterministic view (`lab/render.py`;
  `project()` collapses bilingual→monolingual for legacy consumers); ALL
  translate_* steps deleted (round: 88→~58 steps); translator agent
  RETIRED (spec+memory deleted, CATALOG retargeted); Step.run(schema=) +
  anthropic streaming for >8K-token calls; web search live
  (`research.web_search`, two-phase expert call: free search call with
  pause_turn loop → structured call; D-24 gate intact). Artifacts:
  scenarios.json/synthesis.json/brief.json/meta_critique.json bilingual;
  expert_outputs/*.json; discourse/* bilingual; both ledgers rendered from
  one data set. **Phase 3 NEXT**: evaluation/verify on JSON fields,
  translation_fidelity→bilingual_parity, two-era scorecard (1–7 archive,
  8+ new baseline; era_start_round=8 is already in config and the loop —
  the baseline-round logic is DONE, only scorecard labelling remains),
  remove evaluation.py's judge-score mock fallback (~line 199) +
  SCORE:-regex→structured judge. **ROUND 8 ACCEPTANCE PASSED**
  (2026-07-14/15): total 9.232 (new-era baseline, delta=None by design),
  zero fallbacks/failed steps in the final log, all 12 experts ran live
  web search (fresh KSH/Portugal/Poland numbers with sources in the
  outputs), native-quality HU brief with 36 typed cluster responses.
  Generator: anthropic API; judge finished on the NEW OpenAI API backend
  (JUDGE_PROVIDER=openai, gpt-5-mini default, structured via json_schema
  strict) after the Gemini free tier exhausted mid-round. Acceptance
  lessons (all committed as fixes): bilingual structured outputs need
  ~2-3x the monolingual token budgets (expert 16K, voice 24K, reciprocity
  16K + max-3-answers cap, brief 64K); very large schemas must use
  $defs/$ref (inline BRIEF hit 'compiled grammar too large'; $ref version
  compiles — but llm._gemini_schema does NOT resolve refs, keep BRIEF off
  Gemini); the era boundary must disable delta/regression-revert (a bogus
  cross-era -0.28 triggered a full revert-and-rerun before the fix).
  NOTE: the keys exposed in the 2026-07-14 transcript were ROTATED
  (owner-confirmed 2026-07-15). OPENAI_API_KEY is in .env (billing-enabled).
- **Branch `refactor/deliberation-mission`** (D-30, 2026-07-11; MERGED to
  main via the structured-agents chain, 3187c5b): mission
  reframed from "produce a policy" to "accelerate deliberation"; discourse
  layer relabelled as a stakeholder stress test (explicit disclaimer in
  every discourse-facing instruction + the ledger itself); argument clusters
  decomposed (interest/value/fear/affected/assumption/empirical_uncertainty/
  decision_relevance) and screened for gumicsont (attention-sink) status;
  brief response obligation is now typed (7-way: evidence_answerable /
  policy_design_fixable / communication_fixable / value_conflict /
  irreducible_tradeoff / needs_more_info / not_decision_relevant); final
  brief restructured from the 5-layer Evidence/.../Open-questions split into
  the 10-section deliberation deliverable. Also directly updated the
  committed `agents/**/*.md` specs (agent_defs.py only seeds them once;
  scaffold(force=False) never touches existing files — the canonical run's
  specs still had pre-refactor language baked in). `run_mock_sprint.py`
  passes clean end to end. `verify.py` checks 8 and 12 now correctly FAIL
  against the old-schema canonical rounds 1-5 on disk (expected — those
  rounds don't meet the new definition of done); a real round run under the
  new code is needed before merging to main. D-31 records Phase B
  (deliberately deferred: context/transferability tagging, unknowns
  taxonomy, research agenda, decision-readiness) as follow-up.
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
  `GENERATOR_PROVIDER=anthropic JUDGE_PROVIDER=google
  ANTHROPIC_BACKEND=claude-code GOOGLE_MODEL=
  .venv/bin/python scripts/run_iteration_loop.py --start-round 6 --max-rounds 6`
  Note: translate_ledger (HU translation of a 50-cluster ledger) repeatedly
  hit the 600s CLI timeout — if it keeps timing out on resume, consider
  splitting the translation or letting it degrade to the (logged) mock
  fallback and re-translating later. MERGE PENDING OWNER REVIEW of results.
- **Branch `site/split-tech`**: landing page split — "what it does" stays on
  index, implementation moved to site/tech.html. NOTE (2026-07-15):
  index.html has since been restructured into the topic browser (D-35) —
  if this branch is still wanted, it needs a rebase/rework, not a merge.
- **PR #10 open (owner decision)**: admit `conservative_education` expert to
  the canonical panel (branch exp/conservative-expert, sensitivity experiment
  + report attached). With the discourse layer built, an alternative is to
  close it and rely on the konzervativ_ertekvedo discourse voice instead.

## Open issues (tracker)

- **MULTI-TOPIC SPRINT (2026-07-15, this session, on main): CODE DONE —
  D-35 + D-36.** Delivered: per-topic config/state/outputs + scoped round
  commits (D-35); problem-brief intake + emergent framing with human gates,
  SCENARIO_ANCHORS deleted (D-36, closes the #21 mechanism); per-topic
  time/token/USD metering (lab/metering.py, cost_report in final + site);
  topic-browser site (build_site_topics.py). Mock e2e green for a 3-frame
  test topic; verify green on korai-szelekcio; #21/#18 commented.
  The kisiskolák LIVE end-to-end acceptance PASSED 2026-07-15
  (rural-school-closures; details + follow-up findings in Current state) —
  #21 closed, #18 updated. Owner also clarified the
  country experts (finnish/polish/portuguese_reform) are WHOLE-SYSTEM
  reform experts, not gimnázium-specific — hub specs generalized
  accordingly; use the FULL 12-expert roster for kisiskolák.
- **OWNER DIRECTION (2026-07-14): multi-topic a cél** — sok policy-kérdés
  ugyanazzal a rendszerrel és expert-csoporttal, SEMMI kérdés-specifikus
  hardkód; az opcióteret (mit lehet csinálni) is a szakértői válaszokból
  kell derivalni. Példa következő kérdés: elnéptelenedő falvak kisiskolái.
  A `refactor/deliberation-phase-b` branch (másik gép) D-31 Phase B munkát
  hordoz (unknowns/research-agenda/decision-readiness + saját round 6-8
  outputok a RÉGI sémával) — merge-nél a KÓD érdekes, az outputjai a main
  round 8-cal ütköznek; owner döntsön.
- #5 question submission before launch (LAUNCH BLOCKER)
- #22 metering multi-leg undercount + gpt-5-mini pricing; #23 expert
  web-search dropout; #24 verify check 13 env-override; #25 requirements/
  env bootstrap (all filed from the 2026-07-15 live acceptance)
- #6 retrieval over knowledge/library + corpus ingestion
- #7 distributed contributor runs (SETI@home-style, subscription quota)
- #20 Phase 3 (D-34): evaluation/verify a JSON-mezőkön, bilingual_parity, strukturált judge
- #9 panel-composition sensitivity mitigations (evidence-weighted sides,
  perspective-expert type — partially addressed by D-29)
- #12 stakeholder sources: 4 registry facts await human admission for the
  expert/evidence layer; mirroring their PDFs into knowledge/library/ still
  needs permission (contacts in the proposal file, draft emails on request)
  — this is now the ONLY open part of #12. The discourse-layer half (voices
  named after these orgs, needing their pre-publication review) is resolved
  by D-32 (2026-07-12): the voices were genericized into civil-expert
  archetypes that cite the documents as a source, not an identity.
- Follow-up idea (in #13 comments): ingest Facebook/journalist voices to
  forecast civil reactions (depends on #6)
- D-31 Phase B (deliberation-acceleration refactor, follow-up): evidence
  context/transferability tagging, an explicit unknowns taxonomy artifact,
  a research/information agenda artifact, mandatory no-intervention/pilot
  scenario variants, and a decision-readiness verdict. Each is a net-new
  subsystem (own agent/schema/verify-gate); no GitHub issue opened yet —
  ask if you want one filed.

## Experiments so far

- docs/experiments/2026-07-06-role-swap-robustness.md — judge swap ±0.06
- docs/experiments/2026-07-07-expert-panel-sensitivity.md — one new expert
  doesn't flip majorities but minority voice attrits between synthesis and
  brief; cheap models silently dropped minority_report in BOTH arms → led to
  D-28 validated contracts + issue #9/#12 design

## Gotchas

- Round commits are PATH-SCOPED since D-35 (topics/<slug> +
  outputs/topics/<slug> + config/system_config.json) — the old `git add -A`
  sweep is gone; concurrent topics don't cross-commit.
- Everything question-specific is per-topic: problem brief/frames/rosters/
  expert_facts/human_questions in topics/<slug>/topic.json; glossary in
  topics/<slug>/glossary.md (docs/glossary.md MOVED there, incl. the
  machine-checked pairs section); episodic memory in
  topics/<slug>/agents/memory/; improvement directives in
  topics/<slug>/agents/directives/ (the shared agents/**/*.md specs never
  carry topic learnings); attempts_log + era_start_round per topic under
  outputs/topics/<slug>/.
- Approved frames are FROZEN: change them only via new_topic.py
  approve-frames (the round state hash deliberately excludes the frames
  block, so a manual topic.json edit could silently reuse stale scenario
  artifacts — D-36).
- site/explorer.html + site/knowledge.html + site/topics/ are GENERATED
  (gitignored), built by CI; site/index.html is committed but its
  TOPICS:START/END region is regenerated by build_site_topics.py.
- outputs/ is deliberately committed (audit trail); outputs/mock_sprint/ is
  the gitignored scratch.
- Pyright shows false-positive import errors for lab/* relative imports —
  runtime is fine; don't "fix" them.
- knowledge/registry.json is GENERATED from knowledge/sources/*.md
  (build_registry.py); CI fails if stale.
