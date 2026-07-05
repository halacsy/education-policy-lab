# Proposal: <short title>

proposed_by: <agent name or human>
date: <YYYY-MM-DD>
rationale: <why this fact/source is needed — which scenario/expert lacks grounding>
target_source: <existing source slug, or "new source: <name>">
library_doc: <path under knowledge/library/ if the full document is attached, else none>

## Facts

### <fact_id>
- evidence: strong|moderate|weak|contested
- used_by: <expert names>
- en: <one-sentence citable claim in English>
- hu: <ugyanez magyarul>

<!-- Human review checklist (approver fills):
[ ] source admissible for this domain
[ ] evidence grade justified by the source
[ ] HU/EN pair faithful
On approval: move the fact blocks into knowledge/sources/<slug>.md,
run scripts/build_registry.py, delete this proposal. -->
