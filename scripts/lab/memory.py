"""Per-agent episodic memory (issue #1).

At the end of every round each agent that received signal gets an appended
entry in agents/memory/<name>.md:

- scenario_builder      — every critic objection (it owns all scenario fields),
                          plus whether last round's objections were addressed
                          (field text changed) or not;
- each critic           — its own objections and their resolution status;
- translator            — the deterministic translation report;
- editor                — objections touching disagreement/consensus language;
- experts               — meta-critique lines naming them.

Memory files live under agents/ so every round's system_state snapshot
versions them (verify check 4), and build_prompt() feeds them back to the
agent. Distillation is deterministic code, not another model call: the memory
must be an auditable record, not a paraphrase. Retention: the newest
MAX_ROUNDS_KEPT round-sections per agent (docs/decisions.md D-21).
"""
import re

from .util import AGENTS_DIR, read, read_json, round_dir, write

MEM_DIR = AGENTS_DIR / "memory"
MAX_ROUNDS_KEPT = 5

OBJ_RE = re.compile(
    r"^## (S\d+)\.([a-z_]+)\s*\n(?:Objection:\s*)(.*?)$", re.M)
SEV_RE = re.compile(r"^Severity:\s*(high|medium|low)", re.M)


def memory_path(name):
    return MEM_DIR / f"{name}.md"


def load_memory(name):
    p = memory_path(name)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def parse_objections(critic_name, text):
    objs = []
    for m in OBJ_RE.finditer(text):
        objs.append(dict(critic=critic_name, scenario=m.group(1),
                         field=m.group(2), text=m.group(3).strip()[:220]))
    return objs


def _scenario_field_text(scenarios, sid, field):
    for s in scenarios["scenarios"]:
        if s["id"] == sid:
            v = s.get(field)
            return " ".join(v) if isinstance(v, list) else (v or "")
    return ""


def _append(name, round_n, lines):
    if not lines:
        return
    p = memory_path(name)
    existing = load_memory(name)
    if not existing:
        existing = (f"# Episodic memory: {name}\n\n"
                    "Deterministic distillation of what this agent should "
                    "remember from previous rounds (see lab/memory.py). Fed "
                    "back into the agent's prompt each round.\n")
    body = existing.rstrip() + f"\n\n## round {round_n:02d}\n" + "\n".join(lines) + "\n"
    body = _prune(body)
    write(p, body)


def _prune(body):
    parts = re.split(r"(?=^## round )", body, flags=re.M)
    head, sections = parts[0], parts[1:]
    return head + "".join(sections[-MAX_ROUNDS_KEPT:])


def update_memories(n, artifacts):
    """Called at the end of round n, after critique and meta-critique."""
    objections = []
    for cname, text in artifacts["critics"].items():
        objections.extend(parse_objections(cname, text))

    # resolution status of last round's objections
    resolutions = []
    prev = round_dir(n - 1)
    if n > 1 and (prev / "scenarios.json").exists():
        prev_scen = read_json(prev / "scenarios.json")
        for p in sorted((prev / "critic_outputs").glob("*.md")):
            if p.stem == "translation_checker":
                continue
            for o in parse_objections(p.stem, read(p)):
                before = _scenario_field_text(prev_scen, o["scenario"], o["field"])
                after = _scenario_field_text(artifacts["scenarios_en"],
                                             o["scenario"], o["field"])
                o["addressed"] = bool(before and after and before != after)
                resolutions.append(o)

    # scenario_builder: owns all fields
    lines = [f"- received {o['critic']} on {o['scenario']}.{o['field']}: {o['text']}"
             for o in objections]
    lines += [f"- resolution of round {n-1:02d} objection "
              f"({o['critic']} on {o['scenario']}.{o['field']}): "
              f"{'ADDRESSED (field changed)' if o['addressed'] else 'NOT ADDRESSED (field unchanged)'}"
              for o in resolutions]
    _append("scenario_builder", n, lines)

    # critics: own objections + own resolution feedback
    for cname in artifacts["critics"]:
        own = [o for o in objections if o["critic"] == cname]
        own_res = [o for o in resolutions if o["critic"] == cname]
        lines = [f"- you objected to {o['scenario']}.{o['field']}: {o['text']}"
                 for o in own]
        lines += [f"- your round {n-1:02d} objection on {o['scenario']}.{o['field']} was "
                  f"{'addressed — verify the fix, do not re-litigate' if o['addressed'] else 'NOT addressed — escalate or explain why it stands'}"
                  for o in own_res]
        _append(cname, n, lines)

    # translator: deterministic parity results
    tr = artifacts["translation"]
    _append("translator", n, [
        f"- parity ok={tr['ok']}; glossary violations: "
        f"{tr['glossary_violations'] or 'none'}; untranslated fields: "
        f"{tr['untranslated_fields'] or 'none'}"])

    # editor: disagreement/consensus-related objections
    dis = [o for o in objections
           if re.search(r"disagree|minorit|consensus|dissent", o["text"], re.I)]
    _append("editor", n, [f"- {o['critic']} on {o['scenario']}.{o['field']}: {o['text']}"
                          for o in dis])

    # experts: meta-critique lines that name them
    meta = artifacts.get("meta", "")
    for line in meta.splitlines():
        for name in _expert_names():
            if name in line and line.strip().startswith("-"):
                _append(name, n, [line.strip()[:300]])


def _expert_names():
    from . import agent_defs as D
    return list(D.EXPERTS)
