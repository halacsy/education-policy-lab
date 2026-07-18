#!/usr/bin/env python3
"""Expert-panel sensitivity experiment v2 (issue #19; protocol from #9).

Question: does adding ONE expert — educational_psychology (learning science
+ the social psychology of selection) — shift the synthesis: the
disagreement map, the scenarios, the brief? The v1 experiment
(exp/conservative-expert branch, 2026-07-07) found the risk is not a
majority flip but SELECTIVE ATTRITION: the new voice survives the
disagreement map, then dies before the brief. It also found single-sample
noise comparable to the panel effect — so v2 adds a control replicate.

Design: A/B with fixed inputs, rewritten for the structured/bilingual/
multi-topic architecture (D-34/D-35):

  - The 12 canonical expert analyses are taken verbatim from
    korai-szelekcio round_09 (the sourced-era baseline) — byte-identical
    digests in every arm.
  - The new expert's analysis is generated live ONCE (two-phase, like the
    pipeline: web-search research call, then a schema-constrained
    bilingual analysis), shared by the treatment arm.
  - scenario_builder -> editor -> final_brief_writer run live per arm with
    prompts copied verbatim from lab/pipeline.py, against the topic's
    FROZEN frames and round_09's argument ledger (identical in all arms).

  arm A1 (control):    digest of the 12 canonical analyses
  arm A2 (replicate):  identical inputs to A1 — the sampling-noise floor
  arm B  (treatment):  the same 12 + educational_psychology

Every call must be served by a live backend — a mock would make the
comparison meaningless, so the script aborts instead (and the current llm
layer has no silent mock fallback anyway, D-34). One sample per arm plus
the replicate; residual noise is reported, not hidden.

Run:  GENERATOR_PROVIDER=anthropic .venv/bin/python scripts/exp_panel_sensitivity.py
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lab import llm, render, topic  # noqa: E402
from lab import schemas as S  # noqa: E402
from lab.agents import build_prompt  # noqa: E402
from lab.pipeline import (valid_brief, valid_expert,  # noqa: E402
                          valid_scenarios_bi, valid_synthesis)
from lab.util import ROOT, read, read_json, write, write_json  # noqa: E402

TOPIC = "korai-szelekcio"
NEW = "educational_psychology"
BASE_ROUND = "round_09"
RD = ROOT / "outputs" / "topics" / TOPIC / "iterations" / BASE_ROUND
OUT = ROOT / "outputs" / "experiments" / "psychology_panel_sensitivity"

# The curated facts the seated expert would receive via topic.json
# expert_facts — the admission commit adds this same list, so the
# experiment reproduces exactly what a canonical round would feed the seat.
PSYCH_FACTS = ["big_fish_little_pond", "labeling_effects", "stereotype_threat",
               "goal_orientation", "self_determination", "growth_mindset"]

CORRECTIVE = ("PREVIOUS ATTEMPT FAILED FORMAT VALIDATION. Follow the output "
              "format EXACTLY as specified, with no surrounding commentary.")


def state_hash(*parts):
    """Hash the exact inputs a cached unit (the new expert; one arm's
    scenario/synthesis/brief triplet) was built from. Reuse is only valid
    if this matches the CURRENT inputs — otherwise a stale artifact from a
    prior interrupted run could silently be treated as current (the same
    class of bug pipeline.py's state-hash gate exists to prevent, #27)."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def cached(unit, files, *hash_parts):
    """True if `unit`'s saved artifacts (exact file list — never a glob, to
    avoid e.g. 'control' matching 'control2') exist AND the recorded input
    hash matches the current inputs; otherwise delete the stale files so
    they regenerate cleanly rather than silently mixing old and new."""
    hash_path = OUT / f"{unit}.hash"
    current = state_hash(*hash_parts)
    if (hash_path.exists() and hash_path.read_text().strip() == current
            and all(f.exists() for f in files)):
        return True
    for f in files:
        f.unlink(missing_ok=True)
    hash_path.unlink(missing_ok=True)
    return False


def mark_cached(unit, *hash_parts):
    write(OUT / f"{unit}.hash", state_hash(*hash_parts))


def expert_files():
    return [OUT / f"{NEW}.json", OUT / f"{NEW}.md", OUT / "research.md"]


def arm_files(arm):
    return [OUT / f"scenarios.{arm}.json", OUT / f"scenarios.{arm}.en.md",
            OUT / f"synthesis.{arm}.json", OUT / f"synthesis.{arm}.en.md",
            OUT / f"brief.{arm}.json", OUT / f"brief.{arm}.en.md"]


def live(step, prompt_kwargs, validate, max_tokens, schema=None,
         web_search=False):
    """One live generation step: validation, one escalated retry, NO mock."""
    for attempt in (0, 1):
        kw = dict(prompt_kwargs)
        if attempt:
            kw["instructions"] = kw.get("instructions", "") + "\n" + CORRECTIVE
        prompt = build_prompt(**kw)
        if schema is not None:
            result = llm.call_structured(prompt, schema, "generator",
                                         max_tokens=max_tokens,
                                         escalation=attempt)
        else:
            result = llm.call_model(prompt, "generator",
                                    max_tokens=max_tokens, escalation=attempt,
                                    web_search=web_search)
        entry = llm.CALL_LOG[-1]
        if entry["backend"] == "mock":
            raise SystemExit(f"[abort] {step}: no live backend served the call")
        try:
            if validate(result):
                print(f"[ok] {step} ({entry['backend']}:{entry['model']})",
                      flush=True)
                return result
            print(f"[retry] {step}: output failed validation", flush=True)
        except Exception as e:  # noqa: BLE001 — retry with corrective
            print(f"[retry] {step}: {type(e).__name__}: {e}", flush=True)
    raise SystemExit(f"[abort] {step}: live output failed validation twice")


def curated_sources(facts):
    rows = [f"- [{facts[f]['evidence']}] {facts[f]['en']} "
            f"(source: {facts[f]['source']})" for f in PSYCH_FACTS
            if f in facts]
    if not rows:
        raise SystemExit("[abort] none of the PSYCH_FACTS are in the "
                         "registry — run scripts/build_registry.py")
    return ("\nCURATED SOURCES (registry-backed; cite these with their "
            "evidence grade; anything beyond them must be flagged as "
            "model knowledge):\n" + "\n".join(rows))


def new_expert_live(T, question, glossary, curated):
    """The pipeline's two-phase expert call (pipeline.run_expert), verbatim
    prompts: a free web-search research call, then the structured bilingual
    analysis."""
    research_text = live(
        f"research:{NEW}",
        dict(task="expert_research", agent=NEW,
             instructions=(
                 f"Policy question: {question}\n"
                 "RESEARCH PHASE (web search enabled): search the "
                 "web for the most current, load-bearing evidence "
                 "in YOUR domain (fresh statistics, new studies, "
                 "recent policy changes). For every finding note "
                 "the claim, the number/year, and the exact source "
                 "(title + URL) — the FULL URL after each finding. "
                 "5-10 findings as prose notes — a "
                 "later call turns them into your structured "
                 "analysis. Your spec's ~450-words-per-language cap "
                 "applies to that LATER analysis, NOT to these "
                 "notes: complete URLs and full findings take "
                 "precedence over brevity here. "
                 "Return the FULL notes as the text of "
                 "your reply: you have NO persistent filesystem, "
                 "and anything written to files by result-filtering "
                 "code is DISCARDED — a finding (and its URL) that "
                 "is not in your reply text is lost. Never reply "
                 "with a summary of notes kept elsewhere. Web "
                 "findings are cited sources only; they never "
                 "enter the curated registry (knowledge admission "
                 "is human-gated).")),
        validate=lambda t: len(t.strip()) > 200 and "http" in t,
        max_tokens=16000, web_search=True)
    write(OUT / "research.md", research_text)
    research_notes = (
        "\n\nLIVE RESEARCH NOTES (from web search this round; cite "
        "them with their URL as the source and an honest evidence "
        "grade; registry-backed facts keep their registry source):\n"
        + research_text)
    obj = live(
        f"expert:{NEW}",
        dict(task="expert_analysis", agent=NEW,
             instructions=(
                 f"Policy question: {question}\n"
                 "Produce your analysis as the required JSON object, "
                 "in BOTH English and Hungarian: every {en, hu} pair "
                 "carries the SAME statement written natively in "
                 "each language (parallel authoring, never "
                 "machine-translation flavour; use the glossary "
                 "terms strictly). findings = factual claims, each "
                 "with an honest evidence grade and a named source; "
                 "position = exactly one falsifiable sentence; "
                 "uncertainties = known unknowns with confidence "
                 "and what evidence would reduce them."
                 + curated + research_notes
                 + "\n\nGLOSSARY:\n" + glossary)),
        validate=valid_expert, max_tokens=24000, schema=S.EXPERT_ANALYSIS)
    write_json(OUT / f"{NEW}.json", obj)
    write(OUT / f"{NEW}.md", render.expert_md(NEW, obj, "en"))
    return obj


def run_arm(arm, digest, T, question, glossary, ids, id_set, ids_line,
            ledger_en, cluster_ids):
    """scenario_builder -> editor -> final_brief_writer, prompts verbatim
    from lab/pipeline.run_round steps 2, 3 and 5."""
    scen_bi = live(
        f"{arm}:scenario_builder",
        dict(task="build_scenarios", agent="scenario_builder",
             instructions=(
                 f"{question}\n{T.frame_anchors()}\n{ids_line}\n"
                 "Return the scenarios in the required JSON schema, in BOTH "
                 "English and Hungarian: every {en, hu} pair carries the "
                 "SAME statement written natively in each language "
                 "(parallel authoring, never machine-translation flavour; "
                 "use the glossary terms strictly). Grade every mechanism "
                 "claim's and expected benefit's evidence honestly; give "
                 "every implementation step an actor, action and timeline; "
                 "give every uncertainty a confidence level and what "
                 "evidence would reduce it.\n\nGLOSSARY:\n" + glossary),
             inputs=digest),
        validate=lambda o: valid_scenarios_bi(o, id_set),
        max_tokens=48000, schema=S.SCENARIOS(ids))
    write_json(OUT / f"scenarios.{arm}.json", scen_bi)
    scen_en_md = render.scenarios_md(render.scenario_view(scen_bi, "en"), "en")
    write(OUT / f"scenarios.{arm}.en.md", scen_en_md)

    synthesis_obj = live(
        f"{arm}:editor",
        dict(task="synthesis", agent="editor",
             instructions=(
                 "Synthesize the expert record as the required JSON object, "
                 "in BOTH English and Hungarian: every {en, hu} pair carries "
                 "the SAME statement written natively in each language (use "
                 "the glossary strictly). overview = the coherent picture "
                 "WITHOUT forcing consensus; disagreements = the "
                 "disagreement map (per side: holders, position, rationale, "
                 "minority flag — mark the minority side, never resolve it "
                 "away); agreements = what the experts agree on, each with "
                 "an honest evidence grade.\n\nGLOSSARY:\n" + glossary),
             inputs=digest),
        validate=valid_synthesis, max_tokens=32000, schema=S.SYNTHESIS)
    write_json(OUT / f"synthesis.{arm}.json", synthesis_obj)
    synthesis_text = render.synthesis_md(synthesis_obj, "en")
    write(OUT / f"synthesis.{arm}.en.md", synthesis_text)

    brief_instr = (
        "Write the deliberation brief as the required JSON object, in BOTH "
        "English and Hungarian: every {en, hu} pair carries the SAME "
        "statement authored natively in each language (glossary strictly; "
        "never machine-translation flavour). The renderer produces the 10 "
        "public sections from your fields — fill each with substance: "
        "what_we_know = the strongest evidence-backed findings, honest "
        "evidence grades; what_we_consider_likely = weaker or "
        "indirect-evidence conclusions (kind: estimate); "
        "where_experts_disagree = the disagreement map's substance with "
        "reasons (why), minority sides marked; what_we_dont_know = the "
        "critical gaps, distinguishing known-unknowns from mere "
        "assumptions; what_could_be_done = the real alternatives (never "
        "crown a single scenario as the answer); what_each_option_costs = "
        "trade-offs, harms, risks and who wins/loses per alternative — "
        "never hide a trade-off behind neutral language; "
        "what_research_could_resolve = what new data or study would most "
        "change the decision; what_people_must_decide = the value choices "
        "and political decisions this needs — these are the honest answer, "
        "not failures; minority_positions = every minority view with "
        "holders and rationale, never resolved away; scenario_key = one "
        "line per scenario so the brief is self-contained. Set every "
        "item's kind honestly ([fact]/[estimate]/[assumption]/[value] in "
        "the rendered view) — never let a value judgment pass as a fact."
        " stakeholder_responses: answer EVERY argument cluster from "
        "the ledger by its A<i> id. response_type MUST be one of the 7 "
        "tokens: evidence_answerable (evidence settles or meaningfully "
        "refines it), policy_design_fixable (a design change, "
        "guarantee, compensation or phase-in reduces it), "
        "communication_fixable (already addressed but not visibly or "
        "legibly), value_conflict (legitimate values collide, there is "
        "no technical fix), irreducible_tradeoff (improving one goal "
        "necessarily costs another), needs_more_info (not yet "
        "decidable from the evidence), not_decision_relevant "
        "(attention-worthy but would not change the decision). Do NOT "
        "force every cluster into artificial consensus — "
        "value_conflict and irreducible_tradeoff are legitimate final "
        "answers, not failures. An argument answered by no one is a "
        "defect (response obligation). attention_sinks: the ledger's "
        "gumicsont clusters (high attention, would not change the "
        "decision) with why — so readers can tell which arguments "
        "move the decision from which mostly consume attention.")
    brief_inputs = (scen_en_md + "\n\n" + synthesis_text
                    + "\n\n=== ARGUMENT LEDGER (public arguments that "
                      "MUST each be answered) ===\n" + ledger_en)
    brief_obj = live(
        f"{arm}:final_brief_writer",
        dict(task="brief", agent="final_brief_writer",
             instructions=brief_instr + "\n" + ids_line
             + "\n\nGLOSSARY:\n" + glossary,
             inputs=brief_inputs),
        validate=lambda o: valid_brief(o, id_set, cluster_ids),
        max_tokens=64000, schema=S.BRIEF(ids))
    write_json(OUT / f"brief.{arm}.json", brief_obj)
    write(OUT / f"brief.{arm}.en.md", render.brief_md(brief_obj, "en"))


def main():
    if os.environ.get("LAB_FORCE_MOCK"):
        raise SystemExit("[abort] LAB_FORCE_MOCK set — an experiment served "
                         "by the mock is not an experiment")
    if os.environ.get("ANTHROPIC_BACKEND"):
        raise SystemExit("[abort] ANTHROPIC_BACKEND set — CLI backends "
                         "cannot serve web search or structured schemas; "
                         "unset it (API path required)")
    if llm.provider_for_role("generator") != "anthropic":
        raise SystemExit("[abort] run with GENERATOR_PROVIDER=anthropic — "
                         "the BRIEF schema ($ref) and web search require "
                         "the Anthropic API path")

    T = topic.set_current(TOPIC)
    if not T.frames_approved:
        raise SystemExit(f"[abort] topic {TOPIC} has no approved frames")
    question = T.question_block()
    glossary = T.glossary()
    facts = T.registry_facts()
    ids = tuple(T.scenario_ids)
    id_set = set(ids)
    ids_line = "SCENARIO IDS: " + ", ".join(ids)

    # fixed inputs: the round-9 canonical expert record, verbatim
    canon = sorted(p.stem for p in (RD / "expert_outputs").glob("*.json"))
    if NEW in canon:
        raise SystemExit(f"[abort] {NEW} already in the {BASE_ROUND} record "
                         "— the control arm would be contaminated")
    if len(canon) != 12:
        raise SystemExit(f"[abort] expected 12 canonical experts in "
                         f"{BASE_ROUND}, found {len(canon)}")
    blocks = {n: render.expert_md(n, read_json(RD / "expert_outputs" / f"{n}.json"), "en")
              for n in canon}
    digest_control = "\n\n".join(
        f"----- {n} -----\n{t}" for n, t in blocks.items())

    ledger_en = read(RD / "argument_ledger.en.md")
    cluster_ids = [c["id"] for c in
                   read_json(RD / "discourse" / "argument_map.json")["clusters"]]

    print(f"[exp] base: {TOPIC}/{BASE_ROUND} — {len(canon)} experts, "
          f"{len(cluster_ids)} ledger clusters, frames: {', '.join(ids)}",
          flush=True)

    curated = curated_sources(facts)
    # the new expert, live, once — reuse gated on an input-hash match
    # (question/glossary/curated facts), not mere file existence (#29 review)
    expert_hash_parts = (TOPIC, question, glossary, curated)
    if cached(NEW, expert_files(), *expert_hash_parts):
        new_obj = read_json(OUT / f"{NEW}.json")
        print(f"[exp] reusing saved {NEW} analysis (input hash matches)",
              flush=True)
    else:
        new_obj = new_expert_live(T, question, glossary, curated)
        mark_cached(NEW, *expert_hash_parts)
    digest_treatment = (digest_control + f"\n\n----- {NEW} -----\n"
                        + render.expert_md(NEW, new_obj, "en"))

    frame_anchors = T.frame_anchors()
    for arm, digest in (("control", digest_control),
                        ("control2", digest_control),
                        ("treatment", digest_treatment)):
        arm_hash_parts = (TOPIC, arm, digest, ids_line, frame_anchors,
                          glossary, ledger_en, json.dumps(cluster_ids))
        if cached(arm, arm_files(arm), *arm_hash_parts):
            print(f"[exp] arm {arm}: cached (input hash matches), skipping",
                  flush=True)
            continue
        print(f"[exp] arm {arm}: scenario_builder -> editor -> brief",
              flush=True)
        run_arm(arm, digest, T, question, glossary, ids, id_set, ids_line,
                ledger_en, cluster_ids)
        mark_cached(arm, *arm_hash_parts)

    # merge with any PRIOR invocation's calls (llm.CALL_LOG only holds THIS
    # process's calls — without merging, a resumed run would silently
    # overwrite the committed backend_usage.json with a partial history,
    # #29 review) before recomputing aggregates over the full call list.
    usage_path = OUT / "backend_usage.json"
    prior_calls = read_json(usage_path)["calls"] if usage_path.exists() else []
    all_calls = prior_calls + [
        {k: v for k, v in e.items() if k != "prompt"} for e in llm.CALL_LOG]
    saved_log, llm.CALL_LOG = llm.CALL_LOG, all_calls
    try:
        write_json(usage_path, {
            "backend_stats": llm.backend_stats(),
            "token_stats": llm.token_stats(),
            "errors": llm.error_stats(),
            "calls": all_calls,
        })
    finally:
        llm.CALL_LOG = saved_log
    print(f"[exp] done — artifacts in {OUT}", flush=True)


if __name__ == "__main__":
    main()
