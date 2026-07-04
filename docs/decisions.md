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

**D-13 — Round 1 starts from an honest baseline, not a sandbagged one.**
The baseline agent specs already satisfy hard constraints (all scenario
fields present, critics name scenario id + field). Improvement therefore has
to come from real depth increases (quantified uncertainty, severity-ranked
critiques, minority-report synthesis), not from fixing artificial omissions.
(2026-07-04)
