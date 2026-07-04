"""Write outputs/final/* from the completed rounds."""
import json
import re

from . import knowledge as K
from . import llm
from .evaluation import DIMENSIONS
from .improve import read_attempts
from .pipeline import Step
from .util import FINAL_DIR, read, read_json, round_dir, write


def _exec_summaries(artifacts, n):
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    step = Step(FINAL_DIR, resume=True)
    en, _ = step.run(
        "executive_summary_writer",
        dict(task="exec_summary", agent="executive_summary_writer", lang="en",
             round_n=n,
             instructions=(
                 "Write a one-page executive summary (<= 350 words) of the "
                 "policy work below. It must: name all four scenarios with "
                 "their ids, state the central expert disagreement WITHOUT "
                 "resolving it, carry at least one [evidence: ...] tag, and "
                 "end with the immediate no-regret moves."),
             inputs=artifacts["brief_en"] + "\n\n" + artifacts["synthesis"]),
        validate=lambda t: all(s in t for s in ("S1", "S2", "S3", "S4"))
                           and len(t) > 400,
        out_path=FINAL_DIR / "executive_summary.en.md", max_tokens=1500)
    hu, _ = step.run(
        "executive_summary_translator",
        dict(task="exec_summary", agent="translator", lang="hu", round_n=n,
             instructions=(
                 "Translate this executive summary into Hungarian using the "
                 "glossary in docs/glossary.md strictly (e.g. korai "
                 "szelekció, méltányosság, egységes alapiskola). Keep the "
                 "scenario ids S1-S4. Translate evidence tags as "
                 "[bizonyíték: ...]."),
             inputs=en),
        validate=lambda t: all(s in t for s in ("S1", "S4"))
                           and t.strip() != en.strip() and "szelekció" in t,
        out_path=FINAL_DIR / "executive_summary.hu.md", max_tokens=1500)
    return en, hu


def _scorecard(history):
    lines = ["# Final scorecard", "",
             "| dimension | " + " | ".join(f"r{e['round']:02d}" for e in history) + " |",
             "|---|" + "---|" * len(history)]
    for dim in DIMENSIONS:
        row = [f"{e['dimensions'][dim]['score']}" for e in history]
        lines.append(f"| {dim} | " + " | ".join(row) + " |")
    lines.append("| **total** | " + " | ".join(f"**{e['total']}**" for e in history) + " |")
    lines += ["", "Per-dimension methods, LLM trial means and variances are in "
              "each round's evaluation.json. Divergence-flagged dimensions "
              "used the deterministic score and were sent to human review."]
    return "\n".join(lines) + "\n"


def _change_logs(history):
    attempts = read_attempts()
    agent_lines = ["# Agent change log", "",
                   "Every attempted system change, with expected and actual "
                   "effect (from outputs/archive/attempts_log.jsonl; "
                   "pre/post spec versions in outputs/archive/agent_versions/).",
                   ""]
    if not attempts:
        agent_lines.append("- No changes were applied (single-round run).")
    for a in attempts:
        status = "REVERTED" if a.get("reverted") else "kept"
        agent_lines.append(
            f"- round {a['round_applied']:02d}: `{a['id']}` → "
            f"{a['dimension']} (targets: {len(a['targets'])} agents; "
            f"expected +{a['expected_delta']}, actual "
            f"{a['actual_delta']}, {status}) — {a['what']}")
    wf_lines = ["# Workflow change log", ""]
    wf_lines.append("The workflow steps (docs/workflow.md, "
                    "config/system_config.json) were stable across rounds; "
                    "all applied changes were agent-spec directives (see "
                    "agent_change_log.md). Each round's effective workflow is "
                    "snapshotted in round_XX/system_state/system_config.json.")
    return "\n".join(agent_lines) + "\n", "\n".join(wf_lines) + "\n"


def _disagreement_map(artifacts):
    m = re.search(r"(## Disagreement map.*?)(\n## (?!#)|\Z)",
                  artifacts["synthesis"], re.S)
    body = m.group(1) if m else artifacts["synthesis"]
    return ("# Disagreement map (final)\n\n"
            "Preserved per the Habermas-machine principle: mapped, not "
            "collapsed into consensus. Minority positions also appear in the "
            "final brief.\n\n" + body + "\n")


def _human_questions(history):
    lines = ["# Questions requiring human expert judgment", "",
             "The system does not decide these; they block or bound the "
             "policy decision (see docs/human_role.md).", ""]
    for q in K.HUMAN_QUESTIONS:
        lines += [f"## {q['context']}" + (" (blocking)" if q["blocking"] else ""),
                  q["question"],
                  f"Input needed: {q['needed']}", ""]
    flags = []
    for e in history:
        for dim in e.get("divergence_flagged", []):
            flags.append(f"- Round {e['round']}: judge/deterministic divergence on "
                         f"`{dim}` — human should adjudicate which signal to trust.")
    if flags:
        lines += ["## Judge divergences (evaluator protocol)"] + flags + [""]
    lines += ["## Standing translation review",
              "Native-speaker review of register and connotation in the HU "
              "deliverables (flagged by translation_checker each round; "
              "mechanical parity checks all pass but nuance is not "
              "machine-verifiable)."]
    return "\n".join(lines) + "\n"


def write_final(artifacts, history):
    n = history[-1]["round"]
    rd = round_dir(n)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    write(FINAL_DIR / "final_brief.en.md", artifacts["brief_en"])
    write(FINAL_DIR / "final_brief.hu.md", artifacts["brief_hu"])
    write(FINAL_DIR / "scenarios.en.md", artifacts["scenarios_en_md"])
    write(FINAL_DIR / "scenarios.hu.md", artifacts["scenarios_hu_md"])

    _exec_summaries(artifacts, n)  # writes executive_summary.{en,hu}.md

    write(FINAL_DIR / "final_scorecard.md", _scorecard(history))
    agent_log, wf_log = _change_logs(history)
    write(FINAL_DIR / "agent_change_log.md", agent_log)
    write(FINAL_DIR / "workflow_change_log.md", wf_log)
    write(FINAL_DIR / "disagreement_map.md", _disagreement_map(artifacts))
    write(FINAL_DIR / "translation_report.md",
          "# Translation report (final)\n\n"
          + read(rd / "critic_outputs" / "translation_checker.md")
          + "\nBackend note: " + json.dumps(llm.backend_stats(), indent=2) + "\n")
    write(FINAL_DIR / "human_questions.md", _human_questions(history))
