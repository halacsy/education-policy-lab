"""Per-agent episodic memory (issue #1).

Owner decisions (2026-07-05, docs/decisions.md D-21/D-25):
- CRITICS ARE MEMORYLESS — fresh eyes each round beat consistent escalation;
  objection follow-through is tracked in the generation-side memory instead.
- Retention is RELEVANCE-based, not age-based: unresolved objections are
  carried forward until the criticized field actually changes; resolved items
  appear once and drop; a hard line-cap bounds token cost.

Recipients:
- scenario_builder — unresolved objections carried forward + this round's
  received/resolved record (it owns every scenario field);
- translator      — deterministic parity results (last few rounds);
- editor          — disagreement/consensus-related objections (last few rounds);
- experts         — meta-critique lines naming them (last few rounds).

Memory files live under agents/memory/ so every round's system_state snapshot
versions them, build_prompt() feeds them back, and changed memory invalidates
expert-output reuse. Distillation is deterministic code, not a model call:
memory must be an auditable record, not a paraphrase.
"""
import re

from .util import AGENTS_DIR, read, read_json, round_dir, write

MEM_DIR = AGENTS_DIR / "memory"
MAX_SECTIONS_SMALL = 3     # translator / editor / experts: newest N sections
MAX_UNRESOLVED_LINES = 40  # scenario_builder carry-forward cap (token bound)

OBJ_RE = re.compile(r"^## (S\d+)\.([a-z_]+)\s*\n(?:Objection:\s*)(.*?)$", re.M)
CARRY_RE = re.compile(r"\[(\w+) on (S\d+)\.([a-z_]+)\]")


def memory_path(name):
    return MEM_DIR / f"{name}.md"


def load_memory(name):
    p = memory_path(name)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def parse_objections(critic_name, text):
    return [dict(critic=critic_name, scenario=m.group(1), field=m.group(2),
                 text=m.group(3).strip()[:220])
            for m in OBJ_RE.finditer(text)]


def _scenario_field_text(scenarios, sid, field):
    for s in scenarios["scenarios"]:
        if s["id"] == sid:
            v = s.get(field)
            return " ".join(v) if isinstance(v, list) else (v or "")
    return ""


def _field_changed(prev_scen, cur_scen, sid, field):
    before = _scenario_field_text(prev_scen, sid, field)
    after = _scenario_field_text(cur_scen, sid, field)
    return bool(before and after and before != after)


def _header(name):
    return (f"# Episodic memory: {name}\n\n"
            "Deterministic distillation from previous rounds (lab/memory.py); "
            "fed back into this agent's prompt. Unresolved items persist "
            "until the criticized field changes; resolved items drop.\n")


# -- small recipients: newest-N sections ------------------------------------

def _append_sectioned(name, round_n, lines):
    if not lines:
        return
    existing = load_memory(name) or _header(name)
    body = existing.rstrip() + f"\n\n## round {round_n:02d}\n" + "\n".join(lines) + "\n"
    parts = re.split(r"(?=^## round )", body, flags=re.M)
    write(memory_path(name), parts[0] + "".join(parts[1:][-MAX_SECTIONS_SMALL:]))


# -- scenario_builder: relevance-based carry-forward -------------------------

def _rewrite_builder_memory(round_n, objections, resolutions, prev_scen, cur_scen):
    # previously carried, still-unresolved items (recheck against this round)
    carried = []
    for line in load_memory("scenario_builder").splitlines():
        m = CARRY_RE.search(line)
        if not m or not line.strip().startswith("-"):
            continue
        critic, sid, field = m.groups()
        if prev_scen is not None and _field_changed(prev_scen, cur_scen, sid, field):
            continue  # resolved this round — drops out
        carried.append(line.strip())

    # this round's outcomes for last round's objections
    resolved_now, unresolved_new = [], []
    for o in resolutions:
        tag = f"[{o['critic']} on {o['scenario']}.{o['field']}]"
        if o["addressed"]:
            resolved_now.append(f"- RESOLVED {tag} (field changed)")
        else:
            unresolved_new.append(f"- UNRESOLVED {tag}: {o['text']}")

    seen, unresolved = set(), []
    for line in carried + unresolved_new:
        m = CARRY_RE.search(line)
        if m is None or m.groups() in seen:
            continue
        seen.add(m.groups())
        unresolved.append(line)
    dropped = max(0, len(unresolved) - MAX_UNRESOLVED_LINES)
    unresolved = unresolved[-MAX_UNRESOLVED_LINES:]

    received = [f"- received [{o['critic']} on {o['scenario']}.{o['field']}]: {o['text']}"
                for o in objections]

    parts = [_header("scenario_builder")]
    if unresolved:
        parts.append("\n## unresolved objections (carried until the field changes)\n"
                     + "\n".join(unresolved)
                     + (f"\n- (+{dropped} older unresolved items dropped by cap)" if dropped else ""))
    parts.append(f"\n## round {round_n:02d} — received\n"
                 + ("\n".join(received) if received else "- none"))
    if resolved_now:
        parts.append(f"\n## round {round_n:02d} — resolved from previous round\n"
                     + "\n".join(resolved_now))
    write(memory_path("scenario_builder"), "\n".join(parts) + "\n")


def update_memories(n, artifacts):
    """Called at the end of round n, after critique and meta-critique.
    Critics are deliberately NOT written to (owner decision, D-25)."""
    objections = []
    for cname, text in artifacts["critics"].items():
        objections.extend(parse_objections(cname, text))

    resolutions, prev_scen = [], None
    prev = round_dir(n - 1)
    if n > 1 and (prev / "scenarios.json").exists():
        prev_scen = read_json(prev / "scenarios.json")
        for p in sorted((prev / "critic_outputs").glob("*.md")):
            if p.stem == "translation_checker":
                continue
            for o in parse_objections(p.stem, read(p)):
                o["addressed"] = _field_changed(prev_scen, artifacts["scenarios_en"],
                                                o["scenario"], o["field"])
                resolutions.append(o)

    _rewrite_builder_memory(n, objections, resolutions, prev_scen,
                            artifacts["scenarios_en"])

    tr = artifacts["translation"]
    _append_sectioned("translator", n, [
        f"- parity ok={tr['ok']}; glossary violations: "
        f"{tr['glossary_violations'] or 'none'}; untranslated fields: "
        f"{tr['untranslated_fields'] or 'none'}"])

    dis = [o for o in objections
           if re.search(r"disagree|minorit|consensus|dissent", o["text"], re.I)]
    _append_sectioned("editor", n,
                      [f"- {o['critic']} on {o['scenario']}.{o['field']}: {o['text']}"
                       for o in dis])

    # discourse conditions feed the political-feasibility expert (D-29):
    # "what would win each voice over / lose it" is exactly the stakeholder
    # information that expert otherwise has to guess.
    conds = artifacts.get("ledger_conditions") or []
    _append_sectioned("political_feasibility", n,
                      [f"- condition from discourse: {c[:220]}"
                       for c in conds[:8]])

    meta = artifacts.get("meta", "")
    for line in meta.splitlines():
        for name in _expert_names():
            if name in line and line.strip().startswith("-"):
                _append_sectioned(name, n, [line.strip()[:300]])


def _expert_names():
    from . import agent_defs as D
    return list(D.EXPERTS)
