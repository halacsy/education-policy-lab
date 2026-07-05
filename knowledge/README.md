# Knowledge base

The lab's curated knowledge, structured so a human can review it source by
source (owner decision, issue #2).

```
knowledge/
  sources/        one .md file per source — THE human-editable truth
  library/        full reference documents (papers, reports, data tables)
  proposals/      agent-proposed additions awaiting human approval
  registry.json   GENERATED index (scripts/build_registry.py) — do not edit
```

## The unit of knowledge

Two layers, by design:

- **Fact** (`### <fact_id>` block in a source file): a short, citable,
  bilingual claim with an evidence grade. This is what agents inject into
  prompts and what the evidence_checker verifies against. Facts are small on
  purpose — they are the *extracted, checkable* units.
- **Library document** (`library/`): the full paper/report/dataset a fact was
  extracted from. A source file's `library_doc:` field links them. Search or
  retrieval over the library (e.g. the planned corpus of two decades of
  Hungarian education research) produces *candidate* facts — it never feeds
  prompts directly.

## Governance (owner decisions, 2026-07-05)

1. **Agents propose, humans admit.** Agent-generated fact candidates go to
   `proposals/` (one file per proposal, same format as a source file, plus a
   `rationale:` line). Nothing enters `sources/` without human review.
2. **Every change to `sources/` goes through PR review.**
3. **CI freshness check**: `scripts/build_registry.py --check` fails the build
   if `registry.json` is out of sync with `sources/`.

## Editing workflow

1. Edit or add a file in `sources/` (or approve a proposal by moving it there).
2. Run `python scripts/build_registry.py`.
3. Open a PR; review covers the evidence grade and the HU/EN pair.
4. On merge, the website's knowledge page regenerates automatically.
