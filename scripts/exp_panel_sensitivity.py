#!/usr/bin/env python3
"""Expert-panel sensitivity experiment.

Question: does adding ONE perspective expert (conservative_education) shift
the synthesis — the disagreement map, the scenarios, the brief? Owner concern:
the editor's majority/minority framing is headcount-based, so panel
composition could tilt the picture (docs/experiments report + tracker issue).

Design: A/B with fixed inputs. The 12 canonical expert analyses are taken
verbatim from round_05 (identical in both arms). The new expert's analysis is
generated live ONCE. Then editor → scenario_builder → final_brief_writer run
live in both arms with identical prompts (copied verbatim from lab/pipeline):

  arm A (control):   digest of the 12 canonical analyses
  arm B (treatment): the same 12 + conservative_education

Every step must be served by a live backend — a mock fallback would make the
comparison meaningless, so the script aborts instead. One sample per arm:
residual sampling noise is acknowledged in the report, not hidden.

Run:  GOOGLE_BACKEND=agy python3 scripts/exp_panel_sensitivity.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lab import knowledge as K  # noqa: E402
from lab import llm  # noqa: E402
from lab.agents import build_prompt  # noqa: E402
from lab.pipeline import (BRIEF_HEADERS_EN, SCENARIO_ANCHORS,  # noqa: E402
                          SCENARIO_SCHEMA_HINT, parse_json_block,
                          render_scenarios_md, valid_scenarios)
from lab.util import ROOT, load_config, read, write, write_json  # noqa: E402

NEW = "conservative_education"
RD5 = ROOT / "outputs" / "iterations" / "round_05"
OUT = ROOT / "outputs" / "experiments" / "panel_sensitivity"

CORRECTIVE = ("PREVIOUS ATTEMPT FAILED FORMAT VALIDATION. Follow the output "
              "format EXACTLY as specified, with no surrounding commentary.")


def live(step, prompt_kwargs, validate, max_tokens, postprocess=lambda t: t):
    """One live generation step: validation, one escalated retry, NO mock
    fallback (an experiment served by the mock is not an experiment)."""
    for attempt in (0, 1):
        kw = dict(prompt_kwargs)
        if attempt:
            kw["instructions"] = kw.get("instructions", "") + "\n" + CORRECTIVE
        text = llm.call_model(build_prompt(**kw), "generator",
                              max_tokens=max_tokens, escalation=attempt)
        backend = llm.CALL_LOG[-1]["backend"]
        if backend == "mock":
            raise SystemExit(f"[abort] {step}: no live backend served the call")
        try:
            result = postprocess(text)
            if validate(result):
                print(f"[ok] {step} ({backend}:{llm.CALL_LOG[-1]['model']})",
                      flush=True)
                return result
        except Exception as e:  # noqa: BLE001 — retry with corrective
            print(f"[retry] {step}: {type(e).__name__}: {e}", flush=True)
    raise SystemExit(f"[abort] {step}: live output failed validation twice")


def curated_sources(name):
    fids = K.EXPERT_BRIEFS.get(name, {}).get("findings", [])
    if not fids:
        return ""
    rows = [f"- [{K.FACTS[f]['evidence']}] {K.FACTS[f]['en']} "
            f"(source: {K.FACTS[f]['source']})" for f in fids]
    return ("\nCURATED SOURCES (registry-backed; cite these with their "
            "evidence grade; anything beyond them must be flagged as "
            "model knowledge):\n" + "\n".join(rows))


def main():
    cfg = load_config()
    question = cfg["policy_question"]
    OUT.mkdir(parents=True, exist_ok=True)

    base = {p.stem: read(p)
            for p in sorted((RD5 / "expert_outputs").glob("*.md"))}
    if NEW in base or len(base) != 12:
        raise SystemExit(f"unexpected round_05 panel: {sorted(base)}")

    # 1. the new expert's analysis (generated once, shared by arm B)
    new_path = OUT / f"{NEW}.md"
    validate_expert = (lambda t: "[evidence:" in t and "## Position" in t
                       and "## Uncertainties" in t)
    if new_path.exists() and validate_expert(read(new_path)):
        new_text = read(new_path)
        print(f"[reuse] expert:{NEW} (existing valid output)", flush=True)
    else:
        new_text = live(
            f"expert:{NEW}",
            dict(task="expert_analysis", agent=NEW, round_n=5,
                 instructions=(
                     f"Policy question: {question}\n"
                     "Write your analysis following your Output template. "
                     "Sections required: '## Findings (evidence)' (each "
                     "finding with an inline [evidence: ...] tag and source), "
                     "'## Interpretation', '## Assumptions', '## Position', "
                     "'## Uncertainties'." + curated_sources(NEW))),
            validate_expert, 3000)
        write(new_path, new_text)

    # 2. both arms: editor → scenario_builder → final_brief_writer
    arms = {"control": dict(base), "treatment": {**base, NEW: new_text}}
    for arm, experts in arms.items():
        digest = "\n\n".join(f"----- {name} -----\n{text}"
                             for name, text in experts.items())

        synth_path = OUT / f"synthesis.{arm}.md"
        if synth_path.exists():
            synth = read(synth_path)
            print(f"[reuse] {arm}:editor", flush=True)
        else:
            synth = live(
                f"{arm}:editor",
                dict(task="synthesis", agent="editor", round_n=5,
                     instructions=(
                         "Synthesize the expert record. Required sections: "
                         "'## Overview', '## Disagreement map' (each entry: "
                         "'- **<holders>**: <position> Why: <rationale>'; mark the "
                         "minority side '(minority)'), '## What the experts agree on'. "
                         "Add any section your ## Directives require. Do NOT resolve "
                         "disagreements."),
                     inputs=digest),
                lambda t: "## Disagreement map" in t and t.count("Why:") >= 3,
                4000)
            write(synth_path, synth)

        scen_path = OUT / f"scenarios.{arm}.json"
        if scen_path.exists():
            scen = json.loads(read(scen_path))
            print(f"[reuse] {arm}:scenario_builder", flush=True)
        else:
            scen = live(
                f"{arm}:scenario_builder",
                dict(task="build_scenarios", agent="scenario_builder",
                     lang="en", round_n=5,
                     instructions=(
                         f"Policy question: {question}\n{SCENARIO_ANCHORS}\n"
                         "Return ONLY a JSON object with this exact schema (all ten "
                         f"fields, every field non-empty):\n{SCENARIO_SCHEMA_HINT}"),
                     inputs=digest),
                valid_scenarios, 16000, parse_json_block)
            write_json(scen_path, scen)

        brief_path = OUT / f"brief.{arm}.md"
        if brief_path.exists():
            print(f"[reuse] {arm}:final_brief_writer", flush=True)
        else:
            scen_md = render_scenarios_md(scen, "en")
            brief = live(
                f"{arm}:final_brief_writer",
                dict(task="brief", agent="final_brief_writer", lang="en",
                     round_n=5,
                     instructions=(
                         "Write the policy brief. It MUST contain exactly these "
                         "sections in order: "
                         + ", ".join(f"'{h}'" for h in BRIEF_HEADERS_EN)
                         + ". Every bullet in Evidence carries an [evidence: ...] tag; "
                         "Interpretation bullets carry [interpretation]; Assumptions "
                         "carry [assumption]. Recommendations must NOT pick a single "
                         "scenario as the answer. Open questions lists what needs "
                         "human judgment. Add any section your ## Directives require."),
                     inputs=scen_md + "\n\n" + synth),
                lambda t: all(h in t for h in BRIEF_HEADERS_EN), 4000)
            write(brief_path, brief)

    write_json(OUT / "backend_usage.json", llm.backend_stats())
    print("backend usage:", llm.backend_stats())
    print(f"done — artifacts in {OUT}")


if __name__ == "__main__":
    main()
