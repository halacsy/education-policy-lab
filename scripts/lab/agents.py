"""Scaffold, load and render agent specifications.

Agent specs live as markdown in agents/<type>/<name>.md. They are scaffolded
once from agent_defs.py; afterwards the markdown files are the source of
truth — the improvement step appends directives to them, and every round
snapshots them into system_state/.
"""
import re

from . import agent_defs as D
from .util import AGENTS_DIR, read, write

SPEC_TEMPLATE = """# Agent: {name}

Version: 1
Type: {atype}
Provider-role: {role}

## Role
{focus}

## Mission
Within each round, produce your output so that it measurably serves the rubric
dimensions your type is responsible for; your spec (including ## Directives)
is embedded verbatim in your prompt.

## Inputs
{inputs}

## Outputs
{outputs}

## Rules
{rules}

## Evidence discipline
{evidence}

## Uncertainty discipline
{uncertainty}

## Failure modes
{failures}

## Self-critique questions
{selfcrit}

## Output template
```
{template}
```
{extra}
## Directives
<!-- Appended by the improvement step; one line per directive. -->
"""

TYPE_INPUTS = {
    "expert": "The policy question; docs/mission.md discipline; your domain knowledge.",
    "critic": "scenarios.json (EN), synthesis.md, expert outputs; for translation_checker also the HU deliverables and the topic glossary (topics/<slug>/glossary.md).",
    "synthesis": "Expert outputs (editor/scenario_builder); scenarios + synthesis + the topic glossary (topics/<slug>/glossary.md) (brief/summary writers — bilingual output); discourse reactions (discourse_mediator).",
    "meta": "The round's artifacts, evaluation.json, attempts_log.jsonl, previous round's scores.",
    "discourse": "The scenarios (EN markdown) and, where your archetype is informed by a real public document, that document as basis; in the reciprocity pass also the argument map with the strongest counter-arguments.",
}
TYPE_OUTPUTS = {
    "expert": "expert_outputs/<name>.md",
    "critic": "critic_outputs/<name>.md",
    "synthesis": "scenarios.json / scenarios.<lang>.md / synthesis.md / rejected_framings.md / brief.<lang>.md / executive_summary.<lang>.md / discourse/argument_map.json (per agent)",
    "meta": "meta_critique.md (meta_critic); design documents and config/spec edits (other meta agents, executed via lab/improve.py).",
    "discourse": "discourse/voices/<name>.json (reactions), discourse/responses/<name>.json (reciprocity pass)",
}


def _fmt(items):
    return "\n".join(f"- {i}" for i in items)


def scaffold(force=False):
    """Render all agent specs from agent_defs.py. Existing files are kept
    unless force=True (they may carry appended directives)."""
    created = []
    for dirname, name, focus in D.all_agents():
        atype = D.TYPE_OF_DIR[dirname]
        path = AGENTS_DIR / dirname / f"{name}.md"
        if path.exists() and not force:
            continue
        text = SPEC_TEMPLATE.format(
            name=name, atype=atype, role=D.PROVIDER_ROLE[atype], focus=focus,
            inputs=TYPE_INPUTS[atype], outputs=TYPE_OUTPUTS[atype],
            rules=_fmt(D.TYPE_RULES[atype]),
            evidence=D.TYPE_EVIDENCE[atype],
            uncertainty=D.TYPE_UNCERTAINTY[atype],
            failures=_fmt(D.TYPE_FAILURES[atype]),
            selfcrit=_fmt(D.TYPE_SELFCRIT[atype]),
            template=D.TYPE_TEMPLATE[atype].replace("\\n", "\n"),
            extra=D.EXTRA_SECTIONS.get(name, ""),
        )
        write(path, text)
        created.append(str(path))
    return created


def spec_path(name):
    for dirname in ("experts", "discourse", "critics", "synthesis", "meta"):
        p = AGENTS_DIR / dirname / f"{name}.md"
        if p.exists():
            return p
    raise FileNotFoundError(name)


def load_spec(name):
    return read(spec_path(name))


def overlay_path(name):
    """Per-topic directive overlay (D-35): the improvement step writes here,
    never into the shared spec — one topic's learnings must not leak into
    another topic's prompts."""
    from . import topic
    return topic.current().directives_dir / f"{name}.md"


def load_overlay(name):
    p = overlay_path(name)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def overlay_lines(name):
    return re.findall(r"^- \[round-\d+\] DIRECTIVE:[a-z_]+ — .*$",
                      load_overlay(name), re.M)


def directives_of(name):
    ids = set(re.findall(r"DIRECTIVE:([a-z_]+)", load_spec(name)))
    ids |= set(re.findall(r"DIRECTIVE:([a-z_]+)", load_overlay(name)))
    return ids


def append_directive(name, directive_id, text, round_n):
    spec_path(name)  # the target must exist in the shared hub
    if f"DIRECTIVE:{directive_id}" in load_overlay(name):
        return False
    from . import topic
    overlay = load_overlay(name) or (
        f"# Topic directives: {name} ({topic.current().slug})\n\n"
        "Improvement-step directives for THIS topic only (D-35): the\n"
        "shared spec in agents/ never carries topic learnings; the\n"
        "improvement step appends here, build_prompt() composes this\n"
        "into the prompt after the spec's ## Directives header.\n\n")
    line = f"- [round-{round_n:02d}] DIRECTIVE:{directive_id} — {text}\n"
    write(overlay_path(name), overlay.rstrip("\n") + "\n" + line)
    return True


def remove_directive(name, directive_id):
    overlay = load_overlay(name)
    new = re.sub(rf"^- \[round-\d+\] DIRECTIVE:{directive_id} — .*\n", "",
                 overlay, flags=re.M)
    if new != overlay:
        write(overlay_path(name), new)
        return True
    return False


def build_prompt(task, agent=None, lang=None, provider=None, round_n=None,
                 inputs="", payload_json=None, instructions=""):
    """Assemble the prompt: structured header + agent spec + task + inputs.

    Real models follow the spec and instructions; the mock backend parses the
    header and DIRECTIVE markers deterministically.
    """
    header = [f"TASK: {task}"]
    if agent:
        header.append(f"AGENT: {agent}")
    if lang:
        header.append(f"LANG: {lang}")
    if provider:
        header.append(f"PROVIDER: {provider}")
    if round_n:
        header.append(f"ROUND: {round_n}")
    parts = ["\n".join(header), ""]
    if agent:
        # topic directive lines are appended right after the spec's trailing
        # ## Directives header — the composed prompt is identical to the
        # pre-D-35 one, where directives were baked into the spec file
        spec = load_spec(agent)
        extra = overlay_lines(agent)
        if extra:
            spec = spec.rstrip("\n") + "\n" + "\n".join(extra) + "\n"
        parts += ["=== AGENT SPEC (follow strictly, including ## Directives) ===",
                  spec, ""]
        from .memory import load_memory
        mem = load_memory(agent)
        if mem:
            parts += ["=== EPISODIC MEMORY (yours, from previous rounds — "
                      "respond to unresolved items, do not repeat resolved "
                      "ones) ===", mem, ""]
    if instructions:
        parts += ["=== TASK INSTRUCTIONS ===", instructions, ""]
    if payload_json is not None:
        parts += ["=== INPUT JSON ===", payload_json, "=== END INPUT ==="]
    if inputs:
        parts += ["=== INPUTS ===", inputs]
    return "\n".join(parts)
