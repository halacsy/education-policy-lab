# Agent change log

Every attempted system change, with expected and actual effect (from outputs/archive/attempts_log.jsonl; pre/post spec versions in outputs/archive/agent_versions/).

- round 02: `uncertainty_quantify` → uncertainty_explicitness (targets: 14 agents; expected +0.8, actual 0.731, kept) — For every uncertainty item, state a confidence level (confidence: low|medium|high) and name what evidence would reduce it ('would be reduced by: ...'). In Hunga
- round 03: `critic_fix_severity` → critic_concreteness (targets: 8 agents; expected +0.6, actual 0.745, kept) — For every objection add a line 'Severity: high|medium|low' and a line 'Suggested revision: <concrete fix>'.
- round 04: `minority_report` → disagreement_preservation (targets: 3 agents; expected +0.5, actual 0.24, kept) — Include a '## Minority positions' section (HU: '## Különvélemények') carrying every minority/dissenting position with its holders and rationale, proportionally,
- round 05: `evidence_tag_all` → evidence_discipline (targets: 2 agents; expected +0.4, actual 0.227, kept) — Attach an inline evidence tag ([evidence: strong|moderate|weak|contested]; HU: [bizonyíték: ...]) to EVERY mechanism claim and EVERY expected benefit, not only 
