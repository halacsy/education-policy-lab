# Live v2 acceptance: educational-psychology lens

Date: 2026-07-20
Branch: `codex/artifact-dag-v2`
Topic: `korai-szelekcio`
Treatment source: PR #29, imported as a test-only scientific lens

## Result

The artifact-first v2 architecture completed a fresh live baseline and a
dependency-localized educational-psychology treatment. The accepted artifact
graphs are valid, contain no mock output, and preserve the cross-family
generator/judge boundary (Anthropic generator, OpenAI `gpt-5-mini` judge).

| Measure | Baseline | + educational psychology |
|---|---:|---:|
| Current findings | 84 | 90 |
| Scientific lenses | 12 | 13 |
| Transformation proposals | 6 | 6 |
| Lens assessments | 72 | 78 |
| Dilemmas | 6 | 6 |
| Research questions | 10 | 10 |
| Judge score | 8.000 | 7.667 |

All six transformation content hashes were identical across arms. The final
accepted treatment reused 27 of 32 nodes and executed only the psychology
assessment plus four downstream nodes. The first clean treatment, before the
package-contract correction, matched the plan exactly: 26 cache hits and six
executed nodes, including deterministic lens registration.

The score delta is -0.333. It is descriptive only: one stochastic pair cannot
estimate a stable treatment effect. Four of six judge dimensions were
unchanged; evidence discipline and dilemma clarity each fell by one point in
the treatment sample.

## What the lens changed

The lens did not create a transformation family and was not allowed to rewrite
the option space. It changed how the six fixed proposals were evaluated:

- status quo monitoring retains early-ranking, labeling, and reference-group
  costs;
- delaying selection to 14-16 received conditional support because it reduces
  early high-stakes ranking, subject to implementation quality;
- admissions-only reform was judged mostly to redistribute who experiences
  selection costs rather than remove the mechanism;
- zoning/choice reform affects school composition but leaves the selection
  psychology largely intact;
- quota and outreach expansion received a substantive caution: wider access
  can place disadvantaged students into a selective reference group with a
  documented big-fish-little-pond risk to academic self-concept, especially if
  the track's value-added benefit is small or contested;
- the comprehensive de-tracking pilot most directly addresses labeling and
  performance-orientation mechanisms, but its benefit remains
  implementation-dependent.

The accepted decision package explicitly carries big-fish-little-pond,
academic self-concept, self-determination theory, and early-labeling mechanisms.
The primary substantive contribution is therefore not a new solution. It is a
new decision-relevant warning about access-only reform.

## Failures found and system-level fixes

### 1. Provider schema mismatch

Anthropic structured output rejected array `minItems` above one and all
`maxItems`. Provider-facing schemas now express only supported structure;
semantic count ranges are enforced by an audited retry validator. The first
overfilled output (five assumptions where four were requested) was rejected
rather than truncated by hand.

### 2. Position-carriage failure reproduced, then gated

The first treatment decision package stopped at 316 words and contained none
of the named psychology mechanisms, although all six psychology assessments
and one downstream dilemma contained them. This reproduced PR #29's central
v1 failure at a different boundary: the assessment survived, but the final
package lost the mechanism.

The failed package remains in immutable lineage. A system-level decision
package contract now requires 500-900 words and, in the treatment arm, at
least one named psychology mechanism. The accepted rerun contains 664 words
and passes position carriage.

### 3. Semantic-id version fork

Changing the live node implementation produced new content under existing
semantic ids, while the executor did not set `supersedes`. Graph validation
correctly rejected two current versions. `ArtifactRepository.put_successor()`
now links changed node outputs automatically. The 126 pre-fix fork artifacts
and six stale cache manifests were moved to a recoverable audit archive rather
than deleted.

### 4. Global report counts

Arm summaries originally counted the whole shared repository, so an already
registered treatment lens leaked into the baseline count. Counts now derive
from each arm's node manifests. The reports-only rebuild path regenerates
summaries and comparison data without model calls.

## Cost and audit boundary

The complete engineering acceptance audit contains 96 logged calls and an
estimated cost of $9.51:

- baseline and its system-fix reruns: $8.58;
- both psychology treatment attempts: $0.93.

This total intentionally includes failed pre-generation schema requests,
semantic retries, and the contract-fix rerun. Search notes were persisted and
reused; the expensive live searches were not repeated when implementation
code changed. The final graph contains 516 current artifacts.

## Architecture verdict

The live run validates the central D-37 claims:

1. transformations can remain stable while a new disciplinary lens changes
   only assessments and their descendants;
2. expert identity is unnecessary in the product model; the lens method,
   evidence, limitations, and confidence carry the useful information;
3. value dilemmas and empirical research questions can remain separate;
4. explicit artifact coverage and position-carriage gates can detect the
   information loss that was opaque in v1;
5. immutable lineage and node manifests make failed attempts inspectable.

It also exposes the next architectural correction: the live runner currently
declares one monolithic `experiment.py` as a spec dependency for many nodes.
A decision-package validator change therefore invalidated research analyses
and lens assessments even though their contracts did not change. The web
search cache prevented duplicate searches, but the dependency boundary is
still too broad. Production v2 must split node prompts/contracts/spec hashes
by node before replacing v1.

The judge's repeated concern about absent inline bibliographic citations is a
second follow-up: package references are graph-valid but not sufficiently
visible in the prose view. Add a deterministic evidence appendix or typed
claim-to-source projection rather than asking the summary model to recreate
citations from memory.

PR #29's lens remains test-only. Knowledge/panel admission still requires the
existing human gate.
