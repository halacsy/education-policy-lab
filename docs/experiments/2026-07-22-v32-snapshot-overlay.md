# Architecture 3.2 snapshot overlay over 3.1 production evidence

Date: 2026-07-22–23
Status: complete; both live overlays and independent verification passed

## Question

Can the architecture-3.2 normalization and option-space layers be evaluated
without repeating the unchanged and expensive architecture-3.1 web-research
branches?

## Design

The experiment runs on the two published 3.1 topics:

- `korai-szelekcio`;
- `rural-school-closures`.

For each topic, the overlay binds these exact roots:

- the admitted problem-brief hash from the source RunPlan;
- every finding, assumption, and uncertainty hash emitted by the twelve
  research-node manifests;
- the current 3.1 approved option-space artifact;
- the current 3.1 transformation proposals.

The source artifacts and their typed provenance/source closure are copied byte
for byte into an isolated experiment store. The overlay never writes to the
source production store.

The four-node overlay RunPlan is:

```text
normalize_evidence
  -> derive_option_seeds
  -> cluster_option_seeds
  -> compare_to_v31
```

The last node is deterministic. It compares exact finding-id lineage, not
semantic similarity. Its output distinguishes:

- seeds already touching a legacy proposal;
- seeds touching only a legacy direction;
- seeds with no legacy trace overlap;
- new directions with no legacy proposal overlap;
- explicit evidence conflicts that touch no legacy proposal.

## Interpretation boundary

This is an architecture comparison, not a 3.2 production result. The new
candidate option space is not human-approved. Evidence freshness remains that
of the source 3.1 run. No old human gate, assessment, decision package, or
evaluation is re-labelled or reused as a descendant of the new candidate.

If the overlay reveals material gaps, the next experiment is a 3.2
continuation from the same evidence snapshot: approve the new candidate and
rerun transformations and all downstream dependants. If freshness is material,
run a completely fresh 3.2 production replicate instead.

## Reproduction

```bash
.venv/bin/python scripts/run_v32_snapshot_overlay.py
```

The command is resumable through immutable attempt files and per-node caches.
Outputs are written below
`v2/experiments/2026-07-22-v32-snapshot-overlay/<topic>/`.

## Live execution

The overlay skipped 63 web-research calls from the two source runs: 35 for
`korai-szelekcio` and 28 for `rural-school-closures`. Those calls represented
about USD 9.69 in the source-run pricing report. They were not converted or
rewritten: their exact output hashes became overlay roots.

The new middle layer used nine successful Anthropic calls. One additional
connection attempt failed inside a network-restricted sandbox and is retained
in the rural call log. The final node manifests are complete and contain no
mock calls.

| Topic | findings | canonical claims | conflicts | option seeds | new directions | uncovered seeds | novel-gap directions |
|---|---:|---:|---:|---:|---:|---:|---:|
| `korai-szelekcio` | 115 | 34 | 3 | 16 | 7 | 4 | 0 |
| `rural-school-closures` | 120 | 67 | 12 | 16 | 7 | 4 | 2 |

The overlay calls cost about USD 1.53 for early selection and USD 2.52 for
rural schools under the repository price table. These are costs of the new
3.2 analysis and would also exist in a fresh 3.2 run; the avoided work is the
unchanged research layer.

### Early selection

All seven candidate directions share exact finding lineage with at least one
legacy proposal, so the new architecture does not expose a wholly unsupported
top-level direction. Four individual seeds lack exact legacy trace overlap:

- remove age-10 entry while retaining a later academic track;
- design transition capacity against double-cohort/enrolment shocks;
- restore and fund non-structural equity programmes;
- seek cross-party durability against policy reversal.

Two of three normalized evidence conflicts touch no legacy proposal. This is
the main qualitative gain: the option portfolio is broadly stable, while the
new architecture makes previously implicit tensions and implementation levers
auditable.

### Rural school closures

The candidate again contains sixteen seeds and seven directions. Four seeds
lack exact legacy trace overlap:

- demographic early warning for proactive network planning;
- non-selective, remoteness-weighted small-school funding;
- enforceable participation, appeal and response rights in closure decisions;
- the no-dedicated-intervention demographic-drift counterfactual.

Two complete directions are novel gaps by exact trace: proactive demographic
early warning and the explicit no-intervention counterfactual. Six of twelve
evidence conflicts touch no legacy proposal. This is a material architecture
finding: the old option space carried many substantive interventions, but it
did not preserve the baseline and anticipatory-planning branches as explicit
top-level alternatives.

### Normalization scaling finding

The original single-response rural normalization exceeded the provider's
45,000-token escalation ceiling. The accepted implementation uses three
40-finding shards, then a global reconciliation over their bounded claims.
That pass merged eight valid cross-shard equivalence groups, rejected four
overlapping or type-inconsistent groups, and added cross-shard conflicts. The
final gate also rejected one single-finding pseudo-conflict and retained its
finding as a claim instead. Every action is present in
`semantic_normalizations.jsonl`; no artifact was hand-edited.

This execution rule is now part of D-62. It prevents output-limit failures
without overweighting duplicated claims across shards or weakening exact
coverage.

## Conclusion

Simulating 3.2 from a 3.1 run is meaningful when the research question and
evidence freshness boundary are unchanged. The safe unit of reuse is the exact
problem brief plus the exact research artifacts—not the old option-space gate,
proposals, assessments or decision package.

The experiment supports a staged upgrade:

1. bind the admitted 3.1 evidence snapshot as immutable roots;
2. rerun normalization, option seeds and option-space clustering;
3. inspect the deterministic trace comparison;
4. if the new candidate is to become operational, obtain a new hash-bound
   human approval and rerun every downstream dependent.

The two overlay candidates remain internal. They do not replace the published
3.1 results and are not decision-ready production packages.
