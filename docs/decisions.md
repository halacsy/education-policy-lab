# Decision log

Every consequential design decision, with rationale. Newest at the bottom.
Format: `D-NN — decision — rationale — date`.

---

**D-01 — `lab/` package lives at `scripts/lab/`.**
The layout sketch lists `lab/` under `scripts/`; placing it there lets every
entry point (`python scripts/run_iteration_loop.py`) import `lab` without
path manipulation, since Python puts the script's directory on `sys.path`.
(2026-07-04)

**D-02 — Provider split: `GENERATOR_PROVIDER=google`, `JUDGE_PROVIDER=anthropic` (defaults).**
Cross-family generator/judge split limits self-preference bias. Direction:
Claude models have, in our experience, stronger Hungarian fluency and
translation judgment, and the judge is what scores `translation_fidelity` —
so Anthropic is the judge. Swappable in one line in
`config/system_config.json` (`providers` block). (2026-07-04)

**D-03 — Mock backend reads `DIRECTIVE:` markers from the prompt.**
With no API keys, `call_model` composes deterministic outputs from the curated
briefing pack. Crucially, output richness depends on directive markers that
the improvement step writes into agent specs, and the specs are embedded in
prompts. This keeps the improvement loop causal (system change → behaviour
change → score change) instead of simulated, and it is exactly how a real
LLM would respond to a prompt change — just deterministic. (2026-07-04)

**D-04 — One substantive system change per round.**
Attribution: with multiple simultaneous changes the actual-delta column of
`attempts_log.jsonl` would be meaningless and the archive could not prevent
repeating failed changes. (2026-07-04)

**D-05 — Each round snapshots the full system state into `round_XX/system_state/`.**
Verification check 4 (anti-faking) needs a byte-level diff of "the system as
it was when the round ran". Snapshotting agent specs + config + rubric into
the round folder makes the audit trail self-contained and survives later
edits to the live files. (2026-07-04)

**D-06 — Scenario content is authored bilingually in the briefing pack.**
In mock mode a translator model is unavailable, but fabricating Hungarian by
mechanical transformation would violate the "no untranslated/garbage HU copy"
rule in spirit. The curated pack carries human-authored HU and EN versions of
every scenario field and key fact; the mock translator assembles the HU
deliverable from those, applying the glossary. The `translation_checker`
still runs its full deterministic parity + glossary + back-translation-key
checks, because they must work identically once a real API is connected.
(2026-07-04)

**D-07 — Four scenarios, not three.**
The definition of done needs ≥3. Four (admission reform / phase-down /
comprehensive-to-14 / equity compensation without structural change) spans
the real disagreement geometry: structural vs. non-structural reform is the
main axis of expert dissent, and with only three the "keep structure,
compensate" minority position would collapse into the status quo. (2026-07-04)

**D-08 — Judge divergence threshold = 1.5 points (0–10 scale).**
Below ~1.5 the two mock provider passes differ by heuristic-emphasis noise;
above it the disagreement is structural and a human should adjudicate rather
than average. Recorded in `config/system_config.json`
(`judge_divergence_threshold`). (2026-07-04)

**D-09 — Plateau rule: total delta < 0.15 for two consecutive rounds.**
On a 0–10 total, 0.15 is under the mock judge's trial-to-trial variance band,
i.e. gains smaller than measurement noise do not justify another round.
(2026-07-04)

**D-10 — Verbosity control: length-linked sub-scores are hard-capped.**
Count-based heuristics (uncertainty markers, evidence tags) saturate at a
per-scenario cap, so producing more text cannot raise a score once the cap is
reached; density (tags per claim), not volume, is what scores. (2026-07-04)

**D-11 — `config/` directory added to the layout.**
The workflow, stopping logic and provider routing need one machine-readable,
diffable home (`config/system_config.json`) so that verify check 4 can diff
"workflow/stopping logic" as bytes and rounds can version it. A markdown-only
workflow spec would force the code to parse prose. (2026-07-04)

**D-12 — Held-out checks live in code but are excluded from improvement input.**
`lab/holdout_checks.py` is imported only by `verify.py` and the meta-critique
step; `lab/improve.py` never reads its results. The rubric stays a necessary-
not-sufficient signal. (2026-07-04)

**D-14 — Cross-family scoring without self-judging.**
Generator-side artifacts (expert outputs, scenarios, synthesis, translations,
briefs — produced by the generator provider) are LLM-scored by the judge
provider. Judge-side artifacts (critic outputs, meta_critique — produced by
the judge provider) are LLM-scored by the *generator* provider in a separate
pass, so no model ever scores its own generations. Because a legal
second-provider pass on the same artifact would always be self-scoring, the
divergence cross-check compares each dimension's LLM mean against its
deterministic component; divergence beyond threshold flags the dimension to
`human_questions.md`. (2026-07-04)

**D-15 — Deterministic components dominate every dimension (weight ≥ 0.6).**
LLM-judged sub-scores get ≤ 0.4 weight. This keeps round-over-round score
movement attributable to real structural changes rather than judge noise, per
the evaluator-circularity caution in `docs/architecture.md`. (2026-07-04)

**D-16 — Regressing changes are reverted, logged, and replaced in-round.**
If an applied change lowers the total score, the iteration manager reverts it,
records the attempt with its negative actual delta in `attempts_log.jsonl`
(so it is never retried), selects the next candidate, and re-runs the round.
Committed history therefore shows non-decreasing totals while the archive
preserves the honest record of failures. (2026-07-04)

**D-17 — Real providers with per-call mock fallback and circuit breaker.**
API keys were provided mid-build; the harness uses Gemini (generator) and
Claude (judge) live, with models `gemini-2.5-flash` and `claude-opus-4-8`.
Any call that fails validation/retries degrades to the deterministic mock for
that call and is recorded in the call log; three consecutive provider
failures degrade that provider for the rest of the run. The final report
lists exactly which tasks were served by which backend. (2026-07-04)

**D-18 — Generator model: `gemini-2.5-flash-lite`.**
The provided free-tier Google key caps `gemini-2.5-flash` at 20 requests/day
(observed: `GenerateRequestsPerDayPerProjectPerModel-FreeTier = 20`), which a
5-round run (~100+ generator calls) exhausts mid-round-1. `flash-lite` has a
separate, larger daily pool and passed a full scenario-builder task test.
Overridable via `GOOGLE_MODEL`. Transient 503/"high demand" responses are
treated like rate limits (wait and retry, no circuit-breaker penalty).
(2026-07-05)

**D-19 — Expert outputs are reused across rounds when their spec is unchanged.**
An expert's output is a function of (spec, question, briefing); if its spec is
byte-identical to the previous round's snapshot and the previous output was
produced live (not a fallback), the output is reused and marked `reused` in
round_log.json. This is caching of a deterministic-input step, not round
faking: check 4 diffs system_state, which still changes every round, and any
directive touching an expert forces a re-run. Motivation: daily API quota.
(2026-07-05)

**D-20 — Human feedback enters through the same change machinery as the loop.**
A reader found that the final brief referenced "the S1 pilot" without defining
S1 anywhere in the document. The fix was applied as a catalog change
(`scenario_crossref`, origin recorded in attempts_log.jsonl): a directive on
`final_brief_writer` and `translator` requiring a scenario-key section, then
regeneration of the affected deliverables. Human critique is a first-class
input to Level 4, not an out-of-band edit to Level 1 outputs. (2026-07-05)

**D-21 — Episodic memory is deterministic distillation, not model paraphrase.**
Per-agent memory (agents/memory/<name>.md, issue #1) is written by code from
the round's actual artifacts: objections received, resolution status (field
text changed or not), parity results, meta-critique mentions. A model-written
memory could drift or flatter; a distilled record is auditable. Memory is part
of the effective prompt, so it is versioned in every system_state snapshot,
invalidates expert-output reuse (D-19), and is pruned to the newest 5 round
sections per agent. Retention policy and the critic-anchoring question are
flagged as open human decisions. (2026-07-05)

**D-22 — knowledge/registry.json is the canonical source registry (v1).**
FACTS in lab/knowledge.py now load from the registry; expert prompts inject
their registry-backed sources with evidence grades; the evidence_checker
receives the registry and must flag claims graded above it or citing
unregistered sources as model knowledge. Storage/retrieval at scale, source
admissibility policy and update governance are CTO-level decisions (issue #2)
— v1 deliberately stays flat-file and PR-governed. (2026-07-05)

**D-23 — The public knowledge page is generated, never hand-edited.**
site/knowledge.html is built by scripts/build_site_kb.py from the registry +
glossary on every Pages deploy and is gitignored locally, so the public
credibility surface cannot drift from what the agents actually use.
(2026-07-05)

**D-24 — Knowledge base v2: per-source files, generated index, two-layer
knowledge, human admission gate (owner decisions, issue #2).**
`knowledge/sources/*.md` (one file per source, human-reviewable) is the
truth; `registry.json` is generated by `scripts/build_registry.py` and CI
fails if stale. Knowledge has two layers: FACTS (short, citable, bilingual,
graded — what prompts inject and the evidence_checker verifies) and LIBRARY
documents (`knowledge/library/` — full papers/reports/datasets facts are
extracted from; retrieval over the library produces *candidate* facts, never
direct prompt input). Agents may only PROPOSE (`knowledge/proposals/`,
template provided); admission to sources/ requires human PR review. This
slows growth deliberately — credibility is the product. (2026-07-05)

**D-25 — Critics are memoryless (owner decision).**
Fresh eyes beat consistent escalation: a critic with memory anchors on its
past objections. Objection follow-through is tracked instead in the
scenario_builder's memory, which carries UNRESOLVED objections forward until
the criticized field actually changes (relevance-based retention, hard cap
of 40 carried lines; small recipients keep newest-3 sections). This replaces
the age-based newest-5-rounds rule. (2026-07-05)

**D-26 — Per-task model ladder: cheapest model that is still good enough
(owner decision; assignment by Claude Fable 5).**
Each provider has a cost ladder (google: flash-lite → flash → pro; anthropic:
haiku-4-5 → sonnet-5 → opus-4-8); each task gets the lowest adequate rung in
`config/system_config.json: models.task_tiers`. Assignment rationale:
- tier 0 (cheapest): `expert_analysis` (structured domain summary, validated
  format, registry-grounded — flash-lite passed it in testing);
  `rejected_framings` (simple enumeration); `judge_score` (two-line output,
  0.3 weight, deterministic component dominates, variance recorded).
- tier 1: `build_scenarios` (heaviest structured JSON), `synthesis`
  (disagreement mapping), `translate_scenarios`/`brief` (Hungarian quality),
  `exec_summary` (public-facing), `critic` (targeted objections need real
  reasoning); `translation_fidelity` scoring is raised to tier 1 via
  dimension_tier_overrides (cross-language judging is fragile).
- tier 2 (strongest): `meta_critique` only — system-level gaming judgment is
  the hardest call and the evaluator-circularity guard depends on it.
"Still good enough" is enforced empirically, not just by judgment: a
validation-failure retry escalates one rung (Step.run passes the attempt
number), so a too-cheap model is replaced immediately and the call log
records which model actually served each task. Env overrides
(GOOGLE_MODEL/ANTHROPIC_MODEL) pin a provider to one model and bypass the
ladder (needed while the free-tier key is in use). The ladder lives in
config → snapshotted per round → tier changes are diffable system changes.
(2026-07-05)

**D-27 — Circuit breaker is per (provider, model), with ladder climb.**
Daily free-tier quotas are per model, so a "PerDay" quota error kills only the
affected rung; call_model climbs to the next live rung on the D-26 ladder and
degrades to mock only when every rung is dead. This also makes judge-swap
experiments feasible within free quotas. (2026-07-06)

**D-28 — Directives are validated contracts, not polite requests (issue #11).**
The 2026-07-07 panel-sensitivity experiment showed the cheapest ladder rung
silently dropping the round-04 `minority_report` section in BOTH experiment
arms — a forbidden regression (D-16) passing format validation unnoticed.
Therefore every directive change in the improvement catalog declares its
deterministically checkable output markers (`checks` in improve.CATALOG), and
pipeline.Step composes the markers of the agent's active directives into the
step validator. A dropped section is now a validation failure that escalates
the model ladder (D-26); the mock backend already honors directives, so the
fallback also satisfies the contract. Markers guard against total omission;
partial-compliance quality stays with the judges. (2026-07-07)

**D-29 — Societal-discourse layer: the argument ledger (issues #13, #12, #9).**
Owner decision (2026-07-08): the system models the societal debate as a second
layer beside the expert layer. Ten voices (6 interest/value archetypes + 4
named actors with documented positions) react to the scenarios; a mediator
builds an argument map; the evidence layer grades factual claims; a
reciprocity pass makes voices answer their strongest counter-argument; the
brief answers every argument cluster. The evaluation model is a synthesis of
four international practices: CNDP débat public (response obligation — no
argument disappears silently), OECD deliberative standards (representativeness
+ transparency), Discourse Quality Index (justification required, reciprocity,
explicit change-conditions) and the Habermas Machine (argument aggregation
without head-counting). Epistemic labels are mandatory and validated (D-28):
documented (source) / value_modeled (basis) / no_position — no_position is
legitimate; presenting extrapolation as an organisation's stated view is the
layer's one unforgivable failure. Named-actor position summaries are sent to
the organisations for review before public claims are made about them
(issue #12). Not yet a scored rubric dimension (comparability with earlier
rounds); quality metrics are reported in round_log/meta instead. (2026-07-08)

**D-13 — Round 1 starts from an honest baseline, not a sandbagged one.**
The baseline agent specs already satisfy hard constraints (all scenario
fields present, critics name scenario id + field). Improvement therefore has
to come from real depth increases (quantified uncertainty, severity-ranked
critiques, minority-report synthesis), not from fixing artificial omissions.
(2026-07-04)
