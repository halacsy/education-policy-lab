"""Improvement engine (Level 4): weakest-dimension selection, change catalog,
Reflexion/ADAS archive, safety gate, apply/revert.

One substantive change per round (D-04). Never repeats a change the archive
shows produced no gain. Never applies a forbidden regression (ADAS caveat).
"""
import json
import shutil

from . import agent_defs as D
from .agents import append_directive, remove_directive, spec_path
from .util import ARCHIVE_DIR, load_config, save_config, write

ATTEMPTS_LOG = ARCHIVE_DIR / "attempts_log.jsonl"
AGENT_VERSIONS = ARCHIVE_DIR / "agent_versions"

ALL_EXPERTS = list(D.EXPERTS)
ALL_CRITICS = list(D.CRITICS)

# Every directive change declares its deterministically checkable output
# markers in `checks` (issue #11, D-28): {<task> or "<task>:<lang>": [marker,
# ...]}. A directive in a spec is a validation requirement, not a polite
# request — pipeline.Step composes these into the step validator, so a cheap
# model that silently drops a promised section fails format validation and
# triggers the normal D-26 escalation instead of passing unnoticed. Markers
# are necessary-not-sufficient guards: they catch total omission (the observed
# failure mode), not partial compliance — that remains the judges' job.

CATALOG = [
    dict(id="uncertainty_quantify", dimension="uncertainty_explicitness",
         kind="directive",
         targets=["scenario_builder", "translator"] + ALL_EXPERTS,
         text=("For every uncertainty item, state a confidence level "
               "(confidence: low|medium|high) and name what evidence would "
               "reduce it ('would be reduced by: ...'). In Hungarian output "
               "use 'megbízhatóság: alacsony|közepes|magas' and "
               "'csökkentené: ...'."),
         # structured-output era (D-34): the marker is checked against the
         # JSON dump of the artifact, where the schema guarantees a
         # "confidence" field — total omission is impossible by construction
         checks={"expert_analysis": ['"confidence":'],
                 "build_scenarios": ['"confidence":']},
         expected_delta=0.8),
    dict(id="minority_report", dimension="disagreement_preservation",
         kind="directive", targets=["editor", "final_brief_writer", "translator"],
         text=("Include a '## Minority positions' section (HU: "
               "'## Különvélemények') carrying every minority/dissenting "
               "position with its holders and rationale, proportionally, "
               "never resolved away."),
         checks={"synthesis": ["## Minority positions"],
                 "brief:en": ["## Minority positions"],
                 "brief:hu": ["## Különvélemények"]},
         expected_delta=0.5),
    dict(id="critic_fix_severity", dimension="critic_concreteness",
         kind="directive", targets=ALL_CRITICS,
         text=("For every objection add a line 'Severity: high|medium|low' "
               "and a line 'Suggested revision: <concrete fix>'."),
         checks={"critic": ['"severity":', '"suggested_revision":']},
         expected_delta=0.6),
    dict(id="evidence_tag_all", dimension="evidence_discipline",
         kind="directive", targets=["scenario_builder", "translator"],
         text=("Attach an inline evidence tag ([evidence: "
               "strong|moderate|weak|contested]; HU: [bizonyíték: ...]) to "
               "EVERY mechanism claim and EVERY expected benefit, not only "
               "the core ones."),
         checks={"build_scenarios": ['"evidence":']},
         expected_delta=0.4),
    dict(id="implementation_detail", dimension="scenario_completeness",
         kind="directive", targets=["scenario_builder", "translator"],
         text=("Give every implementation step an explicit timeline in "
               "parentheses, e.g. '(timeline: year 1-2)'; HU: "
               "'(ütemezés: 1-2. év)'."),
         checks={"build_scenarios": ['"timeline":']},
         expected_delta=0.5),
    dict(id="layer_tighten", dimension="layer_separation",
         kind="directive", targets=["final_brief_writer", "translator"],
         text=("Every substantive claim across the brief's 10 sections "
               "carries a claim-kind tag ([fact]/[estimate]/[assumption]/"
               "[value], unchanged in every language); a substantive claim "
               "without one is a defect."),
         checks={"brief:en": ["[estimate]", "[assumption]"],
                 "brief:hu": ["[estimate]", "[assumption]"]},
         expected_delta=0.3),
    dict(id="meta_quant", dimension="meta_system_eval",
         kind="directive", targets=["meta_critic"],
         text=("Quantify: cite per-dimension scores versus the previous "
               "round and name the agent(s) most responsible for the weakest "
               "dimension and any removal candidate."),
         checks={"meta_critique": ["removal candidate"]},
         expected_delta=0.3),
    dict(id="glossary_selfcheck", dimension="translation_fidelity",
         kind="directive", targets=["translator"],
         text=("Before returning, verify every glossary term mapping you "
               "used against docs/glossary.md and correct deviations."),
         # self-check leaves no output marker; enforced by translation.check
         expected_delta=0.2),
    dict(id="scenario_crossref", dimension="layer_separation",
         kind="directive", targets=["final_brief_writer", "translator"],
         text=("The brief must be self-contained: right after the "
               "introduction, add a scenario key section ('## Scenario key' / "
               "HU: '## Forgatókönyv-kulcs') listing each scenario id with "
               "its one-line title and a reference to the full scenario "
               "document (scenarios.en.md / scenarios.hu.md), so no "
               "recommendation refers to an id the reader cannot resolve."),
         checks={"brief:en": ["## Scenario key"],
                 "brief:hu": ["## Forgatókönyv-kulcs"]},
         expected_delta=0.2,
         origin="human feedback 2026-07-05: brief referenced 'S1 felvételi "
                "kísérlet' without defining S1 anywhere in the document"),
]


def required_markers(agent, task, lang=None):
    """Output markers mandated by the directives currently in `agent`'s spec
    for this task (issue #11, D-28). Composed into the step validator by
    lab.pipeline so a silently dropped section is a validation failure that
    escalates the model ladder, never a silent pass."""
    from .agents import directives_of
    if not agent or not task:
        return []
    try:
        active = directives_of(agent)
    except FileNotFoundError:
        return []
    keys = {task, f"{task}:{lang}"} if lang else {task}
    markers = []
    for change in CATALOG:
        if change["id"] in active:
            for key in keys:
                markers.extend(change.get("checks", {}).get(key, []))
    return markers

# ADAS safety caveat: edits that would raise scores by weakening the system.
FORBIDDEN = (
    "Removing a critic; weakening or removing evidence-status requirements; "
    "removing disagreement/minority preservation; deleting rubric dimensions; "
    "relaxing verify.py. Enforced by verify check 14 across system_state "
    "snapshots.")


def read_attempts():
    if not ATTEMPTS_LOG.exists():
        return []
    return [json.loads(line) for line in
            ATTEMPTS_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_attempts(attempts):
    ATTEMPTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPTS_LOG.write_text(
        "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in attempts),
        encoding="utf-8")


def log_attempt(entry):
    attempts = read_attempts()
    attempts.append(entry)
    _write_attempts(attempts)


def set_actual_delta(change_id, round_applied, actual_delta, reverted=False):
    attempts = read_attempts()
    for a in attempts:
        if a["id"] == change_id and a["round_applied"] == round_applied:
            a["actual_delta"] = round(actual_delta, 3)
            a["reverted"] = reverted
    _write_attempts(attempts)


def select_change(evaluation, exclude=()):
    """Pick the next change: weakest dimension first, archive-aware.

    Reflexion/ADAS memory: a change whose recorded actual_delta <= 0 is never
    retried; an already-applied change is not reapplied.
    """
    attempts = read_attempts()
    failed = {a["id"] for a in attempts
              if a.get("actual_delta") is not None and a["actual_delta"] <= 0}
    applied = {a["id"] for a in attempts if not a.get("reverted")}
    dims_sorted = sorted(evaluation["dimensions"].items(),
                         key=lambda kv: kv[1]["score"])
    for dim_name, _ in dims_sorted:
        for change in CATALOG:
            if change["dimension"] != dim_name:
                continue
            if change["id"] in failed or change["id"] in applied:
                continue
            if change["id"] in exclude:
                continue
            return change
    return None


def apply_change(change, round_n):
    """Apply next round's change; archive every touched agent version."""
    AGENT_VERSIONS.mkdir(parents=True, exist_ok=True)
    touched = []
    for target in change["targets"]:
        src = spec_path(target)
        shutil.copy(src, AGENT_VERSIONS / f"round_{round_n:02d}__pre__{src.name}")
        if append_directive(target, change["id"], change["text"], round_n):
            touched.append(target)
            shutil.copy(spec_path(target),
                        AGENT_VERSIONS / f"round_{round_n:02d}__post__{src.name}")
    if change.get("config_path"):
        cfg = load_config()
        node = cfg
        for key in change["config_path"][:-1]:
            node = node[key]
        node[change["config_path"][-1]] = change["config_value"]
        save_config(cfg)
    # idempotent on restart: the attempt may already be logged for this round
    if any(a["id"] == change["id"] and a["round_applied"] == round_n
           for a in read_attempts()):
        return [t for t in change["targets"]]
    entry = dict(round_applied=round_n, id=change["id"],
                 dimension=change["dimension"], kind=change["kind"],
                 targets=touched,
                 expected_delta=change["expected_delta"],
                 actual_delta=None, reverted=False,
                 what=change["text"][:160])
    if change.get("origin"):
        entry["origin"] = change["origin"]
    log_attempt(entry)
    return touched


def revert_change(change):
    """Remove the change's directives; the loop records the measured negative
    delta via set_actual_delta so the archive remembers the failure."""
    for target in change["targets"]:
        remove_directive(target, change["id"])


def write_change_docs(rd, round_n, change, touched, evaluation_prev):
    if change is None:
        write(rd / "revised_agents.md",
              f"# Revised agents — round {round_n}\n\nBaseline round: no "
              "system change applied yet. The change proposed for the next "
              "round is in improvement_plan.md.\n")
        write(rd / "revised_workflow.md",
              f"# Revised workflow — round {round_n}\n\nBaseline workflow as "
              "specified in docs/workflow.md and config/system_config.json "
              "(snapshotted in system_state/).\n")
        return
    write(rd / "revised_agents.md", "\n".join([
        f"# Revised agents — round {round_n}", "",
        f"Applied change: **{change['id']}** (targets dimension "
        f"*{change['dimension']}*, selected in round {round_n - 1} because it "
        "was the weakest dimension).", "",
        f"Directive appended to: {', '.join(touched)}.", "",
        f"Directive text: {change['text']}", "",
        "Pre/post versions of every touched spec are archived in "
        "outputs/archive/agent_versions/.",
    ]) + "\n")
    write(rd / "revised_workflow.md", "\n".join([
        f"# Revised workflow — round {round_n}", "",
        "Workflow steps unchanged this round (the change targeted agent "
        "specs); the effective system state, including config, is "
        "snapshotted in system_state/ and diffable against round "
        f"{round_n - 1}.",
    ]) + "\n")


def write_plan(rd, round_n, evaluation, next_change, artifacts, applied_change,
               stop_decision):
    ev = evaluation
    dims = ev["dimensions"]
    weakest = min(dims, key=lambda k: dims[k]["score"])
    strongest = max(dims, key=lambda k: dims[k]["score"])
    lines = [f"# Improvement plan — round {round_n}", ""]
    lines += ["## What got better?"]
    if ev["delta"] is None:
        lines.append("- Baseline round; nothing to compare yet. "
                     f"Total: {ev['total']}.")
    else:
        lines.append(f"- Total {ev['prev_total']} → {ev['total']} "
                     f"(delta {ev['delta']:+.3f}).")
        if applied_change:
            lines.append(f"- Applied change `{applied_change['id']}` targeted "
                         f"*{applied_change['dimension']}*: score now "
                         f"{dims[applied_change['dimension']]['score']}.")
    lines += ["", "## What is still weak?",
              f"- Weakest dimension: **{weakest}** "
              f"({dims[weakest]['score']}); strongest: {strongest} "
              f"({dims[strongest]['score']})."]
    lines += ["", "## Which agent failed? Which workflow step failed?"]
    if artifacts["fallbacks"]:
        lines.append(f"- Steps degraded to deterministic mock fallback: "
                     f"{', '.join(artifacts['fallbacks'])} — these agents' "
                     "prompts/validators are the weakest links.")
    else:
        lines.append("- No step failed; all artifacts were produced by the "
                     "live backends and passed format validation.")
    lines += ["", "## Which critique was too vague?"]
    from .pipeline import CRITIC_HEADING_RE
    vague = [name for name, text in artifacts["critics"].items()
             if len(CRITIC_HEADING_RE.findall(text)) < 2]
    lines.append(f"- Critics below the 2-targeted-objection bar: "
                 f"{', '.join(vague) if vague else 'none'}.")
    lines += ["", "## Was any translation inconsistent?"]
    tr = artifacts["translation"]
    lines.append(f"- Deterministic parity ok={tr['ok']}; glossary violations: "
                 f"{tr['glossary_violations'] or 'none'}; untranslated "
                 f"fields: {tr['untranslated_fields'] or 'none'}.")
    lines += ["", "## Did the two judges disagree anywhere?"]
    lines.append(f"- Divergence-flagged dimensions: "
                 f"{ev['divergence_flagged'] or 'none'}"
                 + (" (deterministic score used; flagged to "
                    "human_questions.md)." if ev["divergence_flagged"] else "."))
    lines += ["", "## Are score gains genuine or rubric-gaming?",
              "- See meta_critique.md '## Gaming judgment' — the meta-critic "
              "must answer this explicitly each round; the held-out checks "
              "(not visible to this planning step) re-test it at verify time."]
    lines += ["", "## What changes next round?"]
    if next_change:
        lines += [f"- **{next_change['id']}** targeting weakest dimension "
                  f"*{next_change['dimension']}* "
                  f"(score {dims[next_change['dimension']]['score']}).",
                  f"- Specific change: append directive to "
                  f"{', '.join(next_change['targets'][:5])}"
                  + ("..." if len(next_change['targets']) > 5 else "") + ".",
                  f"- Directive: {next_change['text']}",
                  f"- Expected effect: +{next_change['expected_delta']} on "
                  f"{next_change['dimension']} (per-dimension), consulting "
                  "attempts_log.jsonl showed this change was never tried "
                  "before."]
    else:
        lines.append("- No untried, non-forbidden change remains in the "
                     "catalog for the weak dimensions (archive consulted).")
    lines += ["", "## Continue, stop, or ask a human?", f"- {stop_decision}"]
    write(rd / "improvement_plan.md", "\n".join(lines) + "\n")
    write(rd / "plan.json", json.dumps(
        {"next_change_id": next_change["id"] if next_change else None},
        indent=2) + "\n")
