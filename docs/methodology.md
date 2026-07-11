# Methodology (Level 4): how the system designs better agent systems

Level 4 is the reason this repository exists: a written, reusable method for
improving the agent system that improves the policy work. It combines the
evaluator–optimizer loop with ADAS-style archive search and Reflexion-style
episodic memory.

## The improvement algorithm

Each round, after evaluation:

1. **Locate the weakest signal.** Read `evaluation.json`; rank rubric
   dimensions by score (LLM-judged dimensions use the mean, and a
   high-variance or judge-divergent dimension is treated as *less trusted*,
   not lower). The held-out qualitative checks are NOT consulted here — they
   exist to catch Goodharting at verification time.
2. **Consult the archive.** Read `outputs/archive/attempts_log.jsonl`. Any
   candidate change whose (target, change-id) already produced `actual_delta
   <= 0` is disqualified. This is the "never repeat a failed change" rule
   (Reflexion / ADAS).
3. **Select one change** from the change catalog in `lab/improve.py`, mapped
   to the weakest dimension. One change per round — attribution of the score
   delta must stay unambiguous.
4. **Safety gate (ADAS caveat).** The change is rejected if it matches a
   forbidden regression: removing a critic, weakening evidence discipline,
   dropping disagreement preservation, relaxing the rubric, or any edit whose
   only plausible effect is raising a score without changing the artifact
   quality. These are also verified after the fact by `verify.py` check 14.
5. **Write the plan.** `improvement_plan.md` names the weakest dimension, the
   specific change, the expected effect (expected delta), and answers the
   mandatory round questions.
6. **Apply next round.** Round N+1 starts by applying the change (editing
   agent spec files / `config/system_config.json`), snapshotting the new
   system state into the round folder, and logging the attempt to
   `attempts_log.jsonl` with `expected_delta`. After round N+1's evaluation,
   `actual_delta` is filled in.

## Attribution discipline

- Exactly one substantive change per round.
- Every round folder contains a full snapshot of the system state
  (`system_state/`), so `diff -r round_N/system_state round_N+1/system_state`
  shows precisely what changed.
- The archive keeps every agent version with the round and total score it
  participated in (`outputs/archive/agent_versions/`).

## Agent lifecycle

- Agents are born from `templates/agent_template.md` with a written spec.
- An agent that does not measurably raise any rubric dimension across two
  rounds must be flagged in `meta_critique.md` as a **removal candidate**,
  with the evidence (which dimensions it plausibly serves, and their deltas).
- Removal of *generative* agents is allowed with evidence; removal of
  *critics* and *safety checks* is a forbidden regression.

## The discourse layer's method (argument accounting, D-29, reframed D-30)

The societal-discourse layer is a **stakeholder stress test**, not a
simulation of real reactions — it exists to surface, in advance, the
objections, fears and interest-conflicts a real deliberation will have to
answer, never to predict what real people or organisations will actually
think. It is evaluated by ARGUMENT ACCOUNTING, never head counting — a
synthesis of four documented practices: CNDP débat public (response
obligation: the brief answers every argument cluster, enforced by
validation), OECD deliberative standards (representativeness of the voice
roster; epistemic labels: documented / value-modeled / no-position),
Discourse Quality Index (a stance without justification is invalid;
reciprocity: every voice answers its strongest counter-argument; explicit
change-conditions), and the Habermas Machine (aggregation that preserves
minority arguments). Factual claims inside arguments are graded by the
evidence layer against the curated registry; value claims are marked value
questions and routed to humans. Every argument cluster is additionally
decomposed (interest, value, fear, affected actors, underlying assumption,
empirical uncertainty, decision relevance — D-30) and screened for
"gumicsont" status: high attention but low decision-relevance, so real
participants can see which debates move the decision and which are mostly
noise. Quality metrics (coverage, label counts, reciprocity outcomes) are
reported in each round's log — deliberately NOT a scored rubric dimension, so
the optimizer cannot game them.

## Anti-Goodhart measures

- **Held-out checks** (`lab/holdout_checks.py`): qualitative assertions not
  visible to the improvement step (e.g. "the brief does not recommend a
  single option as the answer", "dissents give reasons, not labels",
  "HU text is not a word-order-preserving transliteration"). Run only by
  `verify.py` and the meta_critic.
- **Gaming judgment**: every `meta_critique.md` must state explicitly whether
  the round's score gain is genuine or rubric-gaming, with reasons.
- **Plateau honesty**: if no meaningful improvement is possible, the loop
  stops and says why, instead of manufacturing diffs. (A round without a real
  diffable change may not be committed as a round.)

## What "measurably better" means

- The rubric is code (`lab/evaluation.py`) plus a spec
  (`templates/evaluation_rubric.md`).
- Dimensions: scenario_completeness, evidence_discipline, critic_concreteness,
  layer_separation, meta_system_eval, disagreement_preservation,
  uncertainty_explicitness, translation_fidelity.
- Every round writes `outputs/iterations/round_XX/evaluation.json` (numeric
  per-dimension scores, variance where LLM-judged, and a total) and a
  human-readable `evaluation.md`.

## Reuse by future labs

To run this lab on a different policy question:

1. Replace the briefing pack (`lab/knowledge.py`) or connect real APIs
   (set the two provider keys).
2. Adjust the expert roster in `agents/experts/` for the new domain.
3. Keep everything else: workflow, rubric skeleton, evaluator protocol,
   improvement algorithm, archive format, verification. Those are the
   methodology.
