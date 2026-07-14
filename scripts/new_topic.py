#!/usr/bin/env python3
"""Problem-brief intake with a human gate (D-36; sprint deliverable 1).

The system's input is a DESCRIBED PROBLEM (problem brief), not a bare
question. An under-specified submission is drafted into a full structured
problem brief by the model; a human reviews/edits and approves it before
any round runs. The same gate pattern (D-24: file + explicit confirm)
approves the emergent scenario frames round 1 derives (issue #21).

    # 1. draft a problem brief from free text (one structured model call)
    scripts/new_topic.py draft --text "Mit kezdjünk a kisiskolákkal?"
    # 2. human: review/edit topics/<slug>/proposals/problem-brief.json, then
    scripts/new_topic.py approve --topic <slug>
    # 3. run round 1; it stops at the frames gate, then
    scripts/new_topic.py approve-frames --topic <slug>
"""
import argparse
import datetime

import re
import subprocess
import sys
import unicodedata

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from lab import llm, pipeline, topic
from lab import schemas as S
from lab.agents import build_prompt
from lab.util import read_json, write, write_json

GLOSSARY_SKELETON = """# Bilingual terminology glossary (HU ↔ EN) — {title}

Controlled vocabulary for this topic's deliverables. Agents MUST use these
equivalents; the translation checks enforce them. Additions require a new
row with a note; changing an existing equivalent is a system change and
must appear in a round's `revised_workflow.md`.

| English | Hungarian | Note |
|---------|-----------|------|
| evidence status | bizonyítékstátusz | strong/moderate/weak/contested — erős/mérsékelt/gyenge/vitatott |
| uncertainty | bizonytalanság | |
| policy scenario | szakpolitikai forgatókönyv | |
| implementation step | megvalósítási lépés | |
| stakeholder | érintett szereplő | |
| pilot programme | kísérleti program | |
| phase-out | fokozatos kivezetés | gradual discontinuation |

## Machine-checked key pairs

<!-- Parsed by lab/translation.py: each line "- <en> = <hu>"; alternative
     EN phrasings separated by " / "; matching is lowercase substring, so
     a trailing hyphen acts as a prefix. Add topic key terms as the
     glossary grows; an empty list simply disables the mechanical sweep. -->

- phase- = fokozatos
"""


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:40] or "topic"


def git_user():
    r = subprocess.run(["git", "config", "user.name"],
                       capture_output=True, text=True)
    return r.stdout.strip() or "owner"


def _valid_problem_brief(o):
    if not isinstance(o, dict):
        return False
    if not pipeline.pair_ok(o.get("title")) \
            or not pipeline.pair_ok(o.get("problem_statement")) \
            or not pipeline.pair_ok(o.get("scope")):
        return False
    goals = o.get("learning_goals")
    if not goals or not 2 <= len(goals) <= 4:
        return False
    return all(pipeline.pair_ok(g) for g in goals)


def draft_md(o, slug):
    lines = [f"# Probléma-lap-tervezet — {o['title']['hu']}", "",
             f"Slug: `{slug}`. EMBERI JÓVÁHAGYÁSRA VÁR: szerkeszd a "
             "problem-brief.json-t, ha kell, majd futtasd: "
             f"`scripts/new_topic.py approve --topic {slug}`.", "",
             "## Probléma-leírás", o["problem_statement"]["hu"], "",
             f"*EN: {o['problem_statement']['en']}*", "",
             "## Tanulási célok"]
    lines += [f"- {g['hu']}" for g in o["learning_goals"]]
    lines += ["", "## Scope", o["scope"]["hu"]]
    return "\n".join(lines) + "\n"


def cmd_draft(args):
    raw = args.text or open(args.file, encoding="utf-8").read()
    prompt = build_prompt(
        task="problem_brief",
        instructions=(
            "INTAKE: turn the submitted free-text problem description below "
            "into a complete, structured problem brief for a policy-"
            "deliberation lab, as the required JSON object. The brief is a "
            "DESCRIBED PROBLEM (situation + tension), never a bare "
            "question: restate what is going on, why it is contested or "
            "urgent, and what a deliberation should find out. 2-4 learning "
            "goals; an explicit in/out scope; a short ascii-kebab-case "
            "slug. Write every {en, hu} pair as the SAME statement "
            "authored natively in both languages. Do NOT propose "
            "solutions — the option space is derived later from expert "
            "analysis (emergent framing)."),
        inputs=raw)
    obj = llm.call_structured(prompt, S.PROBLEM_BRIEF, "generator",
                              max_tokens=6000)
    if not _valid_problem_brief(obj):
        raise SystemExit("the drafted problem brief failed validation — "
                         "rerun, or write the proposal file by hand")
    slug = args.slug or slugify(obj.get("slug") or obj["title"]["en"])
    tdir = topic.TOPICS_DIR / slug
    if (tdir / "topic.json").exists():
        raise SystemExit(f"topic {slug!r} already exists")
    write_json(tdir / "proposals" / "problem-brief.json",
               {"slug": slug, "status": "proposed",
                "submitted_text": raw.strip(),
                "problem_brief": {k: obj[k] for k in
                                  ("title", "problem_statement",
                                   "learning_goals", "scope")}})
    write(tdir / "proposals" / "problem-brief.md",
          draft_md(obj, slug))
    print(f"problem-brief draft written:\n"
          f"  {tdir / 'proposals' / 'problem-brief.json'}\n"
          f"  (readable view: {tdir / 'proposals' / 'problem-brief.md'})\n"
          f"HUMAN GATE — review/edit it, then approve with:\n"
          f"  .venv/bin/python scripts/new_topic.py approve --topic {slug}")


def cmd_approve(args):
    tdir = topic.TOPICS_DIR / args.topic
    prop_path = tdir / "proposals" / "problem-brief.json"
    if (tdir / "topic.json").exists():
        raise SystemExit(f"topic {args.topic!r} already approved")
    prop = read_json(prop_path)
    if not _valid_problem_brief(prop["problem_brief"]):
        raise SystemExit("the (possibly edited) problem brief fails "
                         "validation — fix the proposal file first")
    today = datetime.date.today().isoformat()
    write_json(tdir / "topic.json", {
        "slug": args.topic,
        "version": 1,
        "created": today,
        "status": "active",
        "approved_by": git_user(),
        "problem_brief": {**prop["problem_brief"], "seed_sources": []},
        "experts": None,
        "voices": None,
        "_roster_note": "null = the full shared hub (agent_defs.py); "
                        "replace with a name list to scope the roster to "
                        "this topic.",
        "registry_facts": [],
        "expert_facts": {},
        "human_questions": [],
        "evaluation": {"era_start_round": 1},
    })
    if not (tdir / "glossary.md").exists():
        write(tdir / "glossary.md", GLOSSARY_SKELETON.format(
            title=prop["problem_brief"]["title"]["hu"]))
    prop["status"] = "approved"
    prop["approved_on"] = today
    write_json(prop_path, prop)
    print(f"topic {args.topic!r} approved and created:\n"
          f"  {tdir / 'topic.json'} (rosters default to the full hub — "
          "edit experts/voices to scope)\n"
          f"  {tdir / 'glossary.md'} (skeleton — extend as the topic runs)\n"
          "next: run round 1; it will stop at the emergent-framing gate:\n"
          f"  .venv/bin/python scripts/run_iteration_loop.py "
          f"--topic {args.topic} --max-rounds 1")


def cmd_approve_frames(args):
    T = topic.Topic(args.topic)
    prop_path = T.proposals_dir / "frames.json"
    prop = read_json(prop_path)
    frames_obj = {"frames": prop["frames"],
                  "rejected_framings": prop["rejected_framings"]}
    if not pipeline.valid_frames(frames_obj):
        raise SystemExit("the (possibly edited) frames proposal fails "
                         "validation (2-5 frames, sequential S<i> ids, "
                         "bilingual title+scope, >=1 rejected framing) — "
                         "fix the proposal file first")
    today = datetime.date.today().isoformat()
    T.config["frames"] = {
        "status": "approved",
        "approved_by": git_user(),
        "approved_on": today,
        "derived_from": (f"round {prop.get('derived_from_round')} expert "
                         "record (emergent framing, issue #21/D-36); "
                         "rejected framings recorded in "
                         "proposals/frames.json"),
        "scenarios": prop["frames"],
    }
    T.save()
    prop["status"] = "approved"
    prop["approved_on"] = today
    write_json(prop_path, prop)
    # Defensive purge: the sanctioned frame-change path must never leave a
    # scenario-dependent artifact produced under DIFFERENT frames behind
    # (the state hash deliberately excludes the frames block — see
    # Topic.state_fingerprint).
    n = prop.get("derived_from_round")
    if n:
        rd = T.iter_dir / f"round_{n:02d}"
        purged = []
        for pat in ("scenarios.*", "rejected_framings.*", "synthesis*",
                    "brief.*", "argument_ledger.*", "meta_critique.*",
                    "evaluation.*"):
            for p in rd.glob(pat):
                p.unlink()
                purged.append(p.name)
        for sub in ("discourse", "critic_outputs"):
            d = rd / sub
            if d.exists():
                for p in sorted(d.rglob("*"), reverse=True):
                    p.unlink() if p.is_file() else p.rmdir()
                d.rmdir()
                purged.append(sub + "/")
        if purged:
            print(f"purged scenario-dependent artifacts from round {n}: "
                  f"{', '.join(sorted(purged))}")
    print(f"frames approved and frozen into {T.path}\n"
          "relaunch the SAME run command — the round resumes; the expert "
          "outputs are reused.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", help="draft a problem brief from free text")
    d.add_argument("--text", help="the free-text problem description")
    d.add_argument("--file", help="file containing the description")
    d.add_argument("--slug", help="override the generated slug")
    d.set_defaults(fn=cmd_draft)
    a = sub.add_parser("approve", help="approve a drafted problem brief "
                                       "(creates topics/<slug>/topic.json)")
    a.add_argument("--topic", required=True)
    a.set_defaults(fn=cmd_approve)
    f = sub.add_parser("approve-frames",
                       help="approve round 1's emergent scenario frames")
    f.add_argument("--topic", required=True)
    f.set_defaults(fn=cmd_approve_frames)
    args = ap.parse_args()
    if args.cmd == "draft" and not (args.text or args.file):
        ap.error("draft needs --text or --file")
    args.fn(args)


if __name__ == "__main__":
    main()
