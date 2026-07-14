"""Write the topic's final outputs (outputs/topics/<slug>/final/*)."""
import json
import re

from . import llm, topic
from . import schemas as S
from .evaluation import DIMENSIONS
from .improve import read_attempts
from .pipeline import Step
from .util import final_dir, read, read_json, round_dir, write


def _valid_exec_summary(o):
    if not isinstance(o, dict):
        return False
    ids = topic.current().scenario_ids
    en, hu = str(o.get("en", "")), str(o.get("hu", ""))
    return (all(sid in en and sid in hu for sid in ids)
            and len(en) > 400 and len(hu) > 400
            and en.strip() != hu.strip())


def _exec_summaries(artifacts, n):
    T = topic.current()
    fdir = final_dir()
    fdir.mkdir(parents=True, exist_ok=True)
    step = Step(fdir, resume=True)
    obj, _ = step.run(
        "executive_summary_writer",
        dict(task="exec_summary", agent="executive_summary_writer",
             round_n=n,
             instructions=(
                 "Write a one-page executive summary (<= 350 words per "
                 "language) of the policy work below, as the required JSON "
                 "object with an en and a hu field — the SAME summary "
                 "authored natively in each language (glossary strictly). "
                 f"It must: name all {len(T.scenario_ids)} scenarios with "
                 "their ids, state the central expert disagreement WITHOUT "
                 "resolving it, and end with the immediate no-regret "
                 "moves.\n\nGLOSSARY:\n" + T.glossary()),
             inputs=artifacts["brief_en"] + "\n\n" + artifacts["synthesis"]),
        validate=_valid_exec_summary,
        out_path=fdir / "executive_summary.json",
        schema=S.EXEC_SUMMARY, max_tokens=4000)
    write(fdir / "executive_summary.en.md", obj["en"])
    write(fdir / "executive_summary.hu.md", obj["hu"])
    return obj["en"], obj["hu"]


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
                   "effect (from the topic archive (outputs/topics/<slug>/archive/attempts_log.jsonl); "
                   "pre/post spec versions in the topic archive (outputs/topics/<slug>/archive/agent_versions/)).",
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
    for q in topic.current().human_questions:
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
    fdir = final_dir()
    fdir.mkdir(parents=True, exist_ok=True)

    write(fdir / "final_brief.en.md", artifacts["brief_en"])
    write(fdir / "final_brief.hu.md", artifacts["brief_hu"])
    write(fdir / "scenarios.en.md", artifacts["scenarios_en_md"])
    write(fdir / "scenarios.hu.md", artifacts["scenarios_hu_md"])

    _exec_summaries(artifacts, n)  # writes executive_summary.{en,hu}.md

    write(fdir / "final_scorecard.md", _scorecard(history))
    agent_log, wf_log = _change_logs(history)
    write(fdir / "agent_change_log.md", agent_log)
    write(fdir / "workflow_change_log.md", wf_log)
    write(fdir / "disagreement_map.md", _disagreement_map(artifacts))
    write(fdir / "translation_report.md",
          "# Translation report (final)\n\n"
          + read(rd / "critic_outputs" / "translation_checker.md")
          + "\nBackend note: " + json.dumps(llm.backend_stats(), indent=2)
          + "\nToken usage: " + json.dumps(llm.token_stats(), indent=2)
          + "\nErrors seen: " + json.dumps(llm.error_stats(), indent=2) + "\n")
    write(fdir / "human_questions.md", _human_questions(history))
