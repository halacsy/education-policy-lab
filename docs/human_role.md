# The human role

AI never makes policy decisions in this system. This document states exactly
where human judgment is required, and how the system asks for it.

## Decision rights (humans only)

| Decision | Why it cannot be delegated |
|----------|---------------------------|
| Choosing between policy scenarios | Value trade-offs (equity vs. excellence vs. parental choice) are political, not analytical |
| Setting the weight of equity vs. average performance | A values question; the system only makes the trade-off explicit |
| Accepting a political risk | Risk appetite belongs to accountable decision-makers |
| Approving any recommendation for external use | The brief is decision *support*, not a decision |
| Resolving judge divergences | When two model families disagree beyond threshold, a human adjudicates |
| Confirming translation nuance | Residual translation uncertainty (connotation, register) is flagged, not auto-resolved |
| Stopping or redirecting the lab | Humans own the research agenda |

## How the system requests human input

- `outputs/final/human_questions.md` accumulates every point where the system
  identified that human expert judgment is required. It is never empty in a
  completed run — a policy design with no open human questions would itself
  be evidence of overconfidence.
- Each question states: the context, why the system cannot answer it, what
  input format is needed, and what is blocked on it.
- Blocking questions can stop the loop early (stopping rule 3 in
  `docs/workflow.md`).

## What humans should inspect each round

1. `evaluation.md` — are the scores plausible? Any judge divergence flags?
2. `meta_critique.md` — is the gaming judgment convincing?
3. `improvement_plan.md` — is the next change sensible?
4. The disagreement map — is dissent being preserved, or laundered away?

## What the AI does with human answers

Human answers are treated as **inputs with evidence status "human judgment"**,
recorded in the round folder, and never silently overwritten by later model
output.
