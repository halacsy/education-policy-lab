# Questions requiring human expert judgment

The system does not decide these; they block or bound the policy decision (see docs/human_role.md).

## Judge divergences (evaluator protocol)
- Round 1: judge/deterministic divergence on `evidence_discipline` — human should adjudicate which signal to trust.
- Round 1: judge/deterministic divergence on `critic_concreteness` — human should adjudicate which signal to trust.
- Round 1: judge/deterministic divergence on `meta_system_eval` — human should adjudicate which signal to trust.
- Round 2: judge/deterministic divergence on `evidence_discipline` — human should adjudicate which signal to trust.
- Round 3: judge/deterministic divergence on `evidence_discipline` — human should adjudicate which signal to trust.
- Round 3: judge/deterministic divergence on `critic_concreteness` — human should adjudicate which signal to trust.

## Standing translation review
Native-speaker review of register and connotation in the HU deliverables (flagged by translation_checker each round; mechanical parity checks all pass but nuance is not machine-verifiable).
