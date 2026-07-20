# Live v2 acceptance plan: educational-psychology lens

Date: 2026-07-20
Branch: `codex/artifact-dag-v2`
Treatment source: PR #29 (`educational_psychology`)
Topic: `korai-szelekcio`

## Requirement

Run the artifact-first v2 architecture end to end, then add PR #29's
educational-psychology contribution as a scientific lens and measure both the
substantive output change and the DAG invalidation boundary.

## Experimental design

The experiment has two arms over one shared artifact repository.

### A — baseline

- fresh live research through the 12 existing domains;
- evidence-derived transformation families and proposals;
- one batched assessment of every proposal through each of 12 lenses;
- explicit dilemmas, research agenda, decision package;
- cross-family evaluation.

### B — psychology treatment

- reuse baseline research, transformations, 12 lens definitions, and their
  assessments by content-addressed cache;
- register the test-only `educational_psychology` lens from PR #29 with its
  six curated evidence notes and contested labels intact;
- assess every unchanged proposal through that lens;
- regenerate only lens-dependent dilemmas, research agenda, decision package,
  and cross-family evaluation.

The treatment is not an admission of the lens to the canonical registry. It is
an explicitly scoped sensitivity test.

## Expected invalidation

```text
12 research nodes ─────────────── cache hit ─┐
                                             ├─ transformations ─ cache hit
baseline lens registry ───────── cache hit ─┤
12 baseline assessments ──────── cache hit ─┤
                                             │
psychology lens registration ─── execute ───┐
psychology assessment ────────── execute ───┼─ dilemmas ─ agenda ─ package ─ judge
```

Expected treatment result: 26 cache hits and 6 executed nodes. If an upstream
research or transformation node executes, the dependency contract is wrong.

## Provider and cost boundary

- generator: Anthropic API, task ladder (Haiku for research analysis; Sonnet
  for synthesis/assessment tasks);
- judge: OpenAI API, `gpt-5-mini`;
- cross-family generator/judge invariant is mandatory;
- no mock fallback; failed calls stop and resume from the last valid node;
- prompts, raw search notes, events, per-node manifests, token use, and
  estimated cost are persisted.

The v1 PR #29 acceptance cost is not the budget target: the v2 run batches all
proposal assessments per lens and should require 41 baseline calls plus 5
treatment calls rather than recreating an expert/social-discourse simulation.

## Decision questions

1. Does the lens surface BFLPE, academic self-concept, labeling, motivation,
   or goal-orientation mechanisms in canonical assessments and the final
   decision package?
2. Does it create a new transformation family, or only change the evaluation
   of existing proposals? By design the second arm cannot change the already
   compiled family set; any claimed family change would be an architectural
   violation.
3. Does it create or sharpen dilemmas and research questions?
4. Does any psychology-specific content disappear between assessment and
   decision package, reproducing the v1 position-carriage failure?
5. Does the node cache localize recomputation exactly as predicted?
