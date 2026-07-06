# Agent change log

Every attempted system change, with expected and actual effect (from outputs/archive/attempts_log.jsonl; pre/post spec versions in outputs/archive/agent_versions/).

- round 02: `uncertainty_quantify` → uncertainty_explicitness (targets: 14 agents; expected +0.8, actual 0.723, kept) — For every uncertainty item, state a confidence level (confidence: low|medium|high) and name what evidence would reduce it ('would be reduced by: ...'). In Hunga
