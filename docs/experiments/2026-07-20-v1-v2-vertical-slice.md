# V1 → V2 artifact-DAG vertical slice

Date: 2026-07-20  
Branch: `codex/artifact-dag-v2`  
Decision: D-37  
Specification: `docs/proposals/2026-07-20-artifact-first-transformation-dag-v2.md`

## Question

Can the existing Education Policy Lab corpus be represented as a simpler,
explicit artifact graph whose product is a library of education-system
transformations rather than a simulation of experts and social discourse?

## Experimental boundary

No paid model or web-search call was made. The adapter deterministically
recompiled the latest committed v1 round for each topic:

- `korai-szelekcio`: round 9
- `rural-school-closures`: round 2

Therefore this experiment tests the v2 information model, schemas, repository,
DAG execution, cache/resume behavior, audit trail, and public reading model. It
does **not** test new v2 prompts, fresh evidence collection, or whether a live v2
run produces better policy analysis than v1.

## Implementation

The vertical slice adds:

- 12 strict Draft 2020-12 JSON Schemas with typed cross-artifact references;
- an immutable, SHA-256 content-addressed JSON repository;
- semantic-id version lineage through `supersedes`;
- node contracts and dependency-scoped cache keys;
- append-only `events.jsonl` and per-node execution manifests;
- a six-node deterministic migration DAG;
- complete graph validation from each decision-package root;
- an artifact-driven bilingual static website under `site/v2/`.

The six executable nodes are:

1. `import_v1_evidence`
2. `compile_transformations`
3. `apply_scientific_lenses`
4. `identify_decision_dilemmas`
5. `build_research_agenda`
6. `assemble_decision_package`

## Measured corpus

| Artifact type | Count |
|---|---:|
| Source | 272 |
| Finding | 282 |
| Assumption | 145 |
| Uncertainty | 94 |
| Transformation family | 10 |
| Transformation proposal | 10 |
| Lens definition | 24 |
| Lens assessment | 120 |
| Dilemma | 22 |
| Research question | 21 |
| Provenance | 12 |
| Decision package | 2 |
| **Total** | **1,014** |

Topic roots and exact per-type counts are in `v2/catalog/topics.json`.

## V1 / V2 comparison

| Dimension | V1 | V2 vertical slice |
|---|---|---|
| Primary semantic unit | Expert/voice output | Typed semantic artifact |
| Authority in final content | Speaker role is structurally prominent | Claim content is primary; origin is provenance |
| Change object | 10 scenario objects | 10 proposals in 10 explicit transformation families |
| Professional perspective | Implicit in expert authorship | 120 explicit proposal × scientific-lens assessments |
| Value conflict | Mixed into 39 argument clusters | 22 explicit dilemmas with an evidence boundary |
| Research need | Brief section | 21 referenced research-question artifacts |
| Canonical language | Bilingual prose in JSON | English-only canonical JSON; HU/EN rendered downstream |
| Invalidation | Round/global state hash | Node dependency hash |
| Repeat build | No equivalent artifact cache | 12/12 node cache hits |
| Audit root | Brief plus step logs | Decision package plus graph, manifests, and events |

The scenario-to-family mapping is intentionally one-to-one in this migration.
This avoids inventing a new clustering judgment. A live v2 run can cluster
multiple independently proposed changes into a smaller or different family
set.

## Findings

1. **The old corpus contains the new product, but hides it in speaker-shaped
   containers.** The migration extracted 282 findings and 94 uncertainties
   without needing speaker identity in the semantic records.
2. **Scientific perspective and simulated person can be separated.** The same
   12 domain roles became reusable lens definitions and generated a complete
   5 × 12 matrix per topic. This preserves disciplinary judgment while making
   the proposal—not the synthetic expert—the object of analysis.
3. **Value boundaries become inspectable.** Twenty-two mixed/value clusters
   could be represented as dilemmas with explicit value poles, affected groups,
   decision questions, and statements of what evidence cannot decide.
4. **Dependency-scoped execution is operational.** Repeating the build reused
   all 12 topic-node executions from content-addressed cache entries.
5. **Repository validation initially exposed an O(n²) lineage scan.** The first
   two-topic build slowed because every artifact re-read the complete store.
   A single preloaded hash index reduced a complete cached rebuild and graph
   validation to about 1.5 seconds on the development machine. This is exactly
   the kind of coupling the explicit repository boundary makes visible.
6. **English-only canonical content is feasible without losing the Hungarian
   public surface.** The website obtains Hungarian strings only from the legacy
   localization source at render time; no Hungarian prose is written into v2
   semantic JSON or consumed by an analytical node.

## Honest limitations

- V1 source strings were preserved as source artifacts but were not re-verified.
- Migrated lens assessments project v1 expert records; they are not new
  disciplinary reviews.
- Each proposal currently references the topic's full finding set because v1
  did not carry claim-level scenario edges. A live v2 pipeline must produce
  precise support/contradict/qualify relations.
- The migration generates one lens per former expert role. A later human-gated
  lens registry should merge overlapping roles and define stable methods and
  criteria independently of the v1 roster.
- Runtime event timestamps are intentionally operational, while canonical
  artifact timestamps are frozen for deterministic migration hashes.

## Verdict

The artifact-first architecture is viable and materially simpler at the
semantic layer. It should replace the v1 generation core in controlled phases,
while the committed v1 corpus and its full audit trail remain immutable source
material. The next acceptance criterion is one live, cross-family v2 topic run
that produces precise evidence edges and is compared with the migrated golden
view before any production cutover.
