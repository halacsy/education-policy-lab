"""Round runner: experts → scenarios → synthesis → translation → critics →
meta-critic. Every model call goes through lab.llm.call_model; every step
validates its output, retries once with a corrective instruction, and falls
back to the deterministic mock composition if the real backend cannot satisfy
the format (fallbacks are recorded per step).

Interrupted rounds RESUME: if the round folder's system_state snapshot still
matches the live system, existing valid artifacts are reused and their
backend provenance is recovered from steps.jsonl (quota conservation; the
snapshot gate guarantees they were produced by the identical system)."""
import hashlib
import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor

from . import agent_defs as D
from . import improve
from . import knowledge as K
from . import llm, mock_backend, translation
from .agents import build_prompt
from .util import (AGENTS_DIR, CONFIG_PATH, ROOT, TEMPLATES_DIR, load_config,
                   read, read_json, round_dir, write, write_json)

FIELD_KEYS = translation.FIELD_KEYS

SCENARIO_SCHEMA_HINT = json.dumps({
    "scenarios": [{
        "id": "S1", "title": "...", "goal": "...",
        "mechanism": ["causal claim with inline [evidence: strong|moderate|weak|contested] tag where required"],
        "evidence_status": "overall label — one-sentence justification",
        "assumptions": ["..."], "expected_benefits": ["... [evidence: ...]"],
        "equity_impact": "...", "cost_categories": ["..."],
        "implementation_steps": ["Actor — action"],
        "political_risks": ["..."], "uncertainties": ["..."],
    }]
}, indent=2)

SCENARIO_ANCHORS = (
    "Produce EXACTLY four scenarios with stable ids:\n"
    "S1 admission reform within the current structure; S2 gradual phase-down "
    "of 6/8-year entry places; S3 comprehensive school to age 14 (structural "
    "reform); S4 keep the structure, compensate general schools "
    "(Portuguese-style package).")

BRIEF_HEADERS_EN = ["## Evidence", "## Interpretation", "## Assumptions",
                    "## Recommendations", "## Open questions"]
BRIEF_HEADERS_HU = ["## Bizonyítékok", "## Értelmezés", "## Feltevések",
                    "## Ajánlások", "## Nyitott kérdések"]

CRITIC_HEADING_RE = re.compile(
    r"^## S\d+\.(goal|mechanism|evidence_status|assumptions|expected_benefits|"
    r"equity_impact|cost_categories|implementation_steps|political_risks|"
    r"uncertainties)", re.M)


def directive_validator(validate, prompt_kwargs):
    """Compose the base validator with the output markers mandated by the
    agent's active directives (issue #11, D-28). A directive is a contract:
    if the model silently drops a promised section, the step FAILS validation
    and escalates the model ladder (D-26) instead of passing unnoticed."""
    markers = improve.required_markers(prompt_kwargs.get("agent"),
                                       prompt_kwargs.get("task"),
                                       prompt_kwargs.get("lang"))
    if not markers:
        return validate

    def _validate(result):
        if not validate(result):
            return False
        text = result if isinstance(result, str) else \
            json.dumps(result, ensure_ascii=False)
        return all(m in text for m in markers)
    return _validate


def parse_json_block(text):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    return json.loads(text[start:end + 1])


def _nonempty(v):
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return bool(v) and all(isinstance(x, str) and x.strip() for x in v)
    return False


def valid_scenarios(obj, require_ids=None):
    try:
        sc = obj["scenarios"]
    except (TypeError, KeyError):
        return False
    if len(sc) < 3:
        return False
    ids = [s.get("id", "") for s in sc]
    if len(set(ids)) != len(ids) or not all(re.fullmatch(r"S\d+", i) for i in ids):
        return False
    if require_ids and set(ids) != set(require_ids):
        return False
    return all(_nonempty(s.get(k)) for s in sc for k in FIELD_KEYS)


def render_scenarios_md(obj, lang):
    title = ("# Policy scenarios" if lang == "en"
             else "# Szakpolitikai forgatókönyvek")
    lines = [title, ""]
    for s in obj["scenarios"]:
        lines.append(f"## {s['id']} — {s['title']}")
        for key in FIELD_KEYS:
            label = K.FIELD_LABELS[key][0 if lang == "en" else 1]
            lines.append(f"**{label}**")
            v = s[key]
            if isinstance(v, list):
                lines += [f"- {item}" for item in v]
            else:
                lines.append(v)
            lines.append("")
    return "\n".join(lines)


def _current_state_hash():
    h = hashlib.sha256()
    for p in sorted(AGENTS_DIR.rglob("*.md")):
        h.update(str(p.relative_to(AGENTS_DIR)).encode())
        h.update(p.read_bytes())
    h.update(CONFIG_PATH.read_bytes())
    h.update((TEMPLATES_DIR / "evaluation_rubric.md").read_bytes())
    return h.hexdigest()


def _snapshot_state_hash(rd):
    base = rd / "system_state"
    if not ((base / "agents").exists() and (base / "system_config.json").exists()
            and (base / "evaluation_rubric.md").exists()):
        return None
    h = hashlib.sha256()
    for p in sorted((base / "agents").rglob("*.md")):
        h.update(str(p.relative_to(base / "agents")).encode())
        h.update(p.read_bytes())
    h.update((base / "system_config.json").read_bytes())
    h.update((base / "evaluation_rubric.md").read_bytes())
    return h.hexdigest()


def snapshot_system_state(rd):
    dest = rd / "system_state"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(AGENTS_DIR, dest / "agents")
    shutil.copy(CONFIG_PATH, dest / "system_config.json")
    shutil.copy(TEMPLATES_DIR / "evaluation_rubric.md", dest / "evaluation_rubric.md")


class Step:
    """One generation step with validation, one corrective retry, a
    deterministic mock fallback, resume-from-disk, and a step journal."""

    def __init__(self, rd, resume):
        self.rd = rd
        self.resume = resume
        self.fallbacks = []
        self.resumed = []
        self.journal_path = rd / "steps.jsonl"
        self._prior = {}
        if resume and self.journal_path.exists():
            for line in self.journal_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    e = json.loads(line)
                    self._prior[e["step"]] = e["backend"]

    def _note(self, name, backend):
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"step": name, "backend": backend}) + "\n")
        if backend == "mock-fallback":
            self.fallbacks.append(name)

    def run(self, name, prompt_kwargs, validate, out_path=None,
            role="generator", max_tokens=8000, postprocess=lambda t: t,
            loader=None, writer=None):
        loader = loader or read
        writer = writer or write
        validate = directive_validator(validate, prompt_kwargs)
        # resume: identical system state + existing valid artifact => reuse
        if self.resume and out_path is not None and out_path.exists():
            try:
                result = loader(out_path)
                if validate(result):
                    backend = self._prior.get(name, "unknown")
                    if backend == "mock-fallback":
                        self.fallbacks.append(name)
                    self.resumed.append(name)
                    return result, backend
            except Exception:
                pass
        corrective = ""
        for attempt in (0, 1):
            kw = dict(prompt_kwargs)
            if corrective:
                kw["instructions"] = kw.get("instructions", "") + "\n" + corrective
            prompt = build_prompt(**kw)
            # a validation-failure retry escalates one rung on the model
            # ladder (D-26): cheap model produced unusable output
            text = llm.call_model(prompt, role, max_tokens=max_tokens,
                                  escalation=attempt)
            backend = llm.CALL_LOG[-1]["backend"]
            try:
                result = postprocess(text)
                if validate(result):
                    if out_path is not None:
                        writer(out_path, result)
                    self._note(name, backend)
                    return result, backend
            except Exception:
                pass
            corrective = ("PREVIOUS ATTEMPT FAILED FORMAT VALIDATION. Follow "
                          "the output format EXACTLY as specified, with no "
                          "surrounding commentary.")
        # deterministic fallback
        prompt = build_prompt(**prompt_kwargs)
        result = postprocess(mock_backend.compose(prompt, role))
        if not validate(result):
            raise RuntimeError(f"mock fallback failed validation for step {name}")
        if out_path is not None:
            writer(out_path, result)
        self._note(name, "mock-fallback")
        return result, "mock-fallback"


def run_round(n):
    """Generate all round-n artifacts (steps 1-6 of the workflow). Evaluation,
    meta-critique and improvement planning are orchestrated by the loop."""
    cfg = load_config()
    rd = round_dir(n, create=True)
    resume = _snapshot_state_hash(rd) == _current_state_hash()
    if not resume and (rd / "steps.jsonl").exists():
        (rd / "steps.jsonl").unlink()  # stale partial attempt
    snapshot_system_state(rd)
    step = Step(rd, resume)
    question = cfg["policy_question"]
    write_scen = lambda p, obj: write_json(p, obj)

    # 1. experts (parallel; unchanged specs may reuse the previous round's
    #    live output — same deterministic input, saves daily quota, D-19)
    prev_rd = round_dir(n - 1) if n > 1 else None
    prev_log = {}
    if prev_rd and (prev_rd / "round_log.json").exists():
        prev_log = read_json(prev_rd / "round_log.json")
    reused_prev = []

    def reusable_expert(name):
        if prev_rd is None or f"expert:{name}" in set(prev_log.get("fallbacks", [])):
            return None
        spec_prev = prev_rd / "system_state" / "agents" / "experts" / f"{name}.md"
        out_prev = prev_rd / "expert_outputs" / f"{name}.md"
        spec_now = AGENTS_DIR / "experts" / f"{name}.md"
        if not (spec_prev.exists() and out_prev.exists()):
            return None
        if spec_prev.read_text(encoding="utf-8") != spec_now.read_text(encoding="utf-8"):
            return None
        # episodic memory is part of the effective prompt: changed memory
        # means the expert must actually re-run (issue #1)
        mem_prev = prev_rd / "system_state" / "agents" / "memory" / f"{name}.md"
        mem_now = AGENTS_DIR / "memory" / f"{name}.md"
        prev_mem = mem_prev.read_text(encoding="utf-8") if mem_prev.exists() else ""
        now_mem = mem_now.read_text(encoding="utf-8") if mem_now.exists() else ""
        if prev_mem != now_mem:
            return None
        return out_prev.read_text(encoding="utf-8")

    def curated_sources(name):
        fids = K.EXPERT_BRIEFS.get(name, {}).get("findings", [])
        if not fids:
            return ""
        rows = [f"- [{K.FACTS[f]['evidence']}] {K.FACTS[f]['en']} "
                f"(source: {K.FACTS[f]['source']})" for f in fids]
        return ("\nCURATED SOURCES (registry-backed; cite these with their "
                "evidence grade; anything beyond them must be flagged as "
                "model knowledge):\n" + "\n".join(rows))

    def run_expert(name):
        out_path = rd / "expert_outputs" / f"{name}.md"
        validate = directive_validator(
            lambda t: "[evidence:" in t and "## Position" in t
                      and "## Uncertainties" in t,
            dict(task="expert_analysis", agent=name))
        if not (step.resume and out_path.exists()):
            cached = reusable_expert(name)
            if cached is not None and validate(cached):
                write(out_path, cached)
                reused_prev.append(f"expert:{name}")
                return name, cached
        text, _ = step.run(
            f"expert:{name}",
            dict(task="expert_analysis", agent=name, round_n=n,
                 instructions=(
                     f"Policy question: {question}\n"
                     "Write your analysis following your Output template. "
                     "Sections required: '## Findings (evidence)' (each "
                     "finding with an inline [evidence: ...] tag and source), "
                     "'## Interpretation', '## Assumptions', '## Position', "
                     "'## Uncertainties'." + curated_sources(name))),
            validate=validate, out_path=out_path, max_tokens=3000)
        return name, text

    experts = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, text in ex.map(run_expert, D.EXPERTS):
            experts[name] = text

    expert_digest = "\n\n".join(
        f"----- {name} -----\n{text}" for name, text in experts.items())

    # 2. scenario builder (EN, machine-readable)
    scen_en, _ = step.run(
        "scenario_builder",
        dict(task="build_scenarios", agent="scenario_builder", lang="en",
             round_n=n,
             instructions=(
                 f"Policy question: {question}\n{SCENARIO_ANCHORS}\n"
                 "Return ONLY a JSON object with this exact schema (all ten "
                 f"fields, every field non-empty):\n{SCENARIO_SCHEMA_HINT}"),
             inputs=expert_digest),
        validate=lambda o: valid_scenarios(o),
        out_path=rd / "scenarios.json", postprocess=parse_json_block,
        loader=read_json, writer=write_scen, max_tokens=16000)
    scen_en_md = render_scenarios_md(scen_en, "en")
    write(rd / "scenarios.en.md", scen_en_md)

    # 3. editor synthesis + rejected framings
    synthesis_text, _ = step.run(
        "editor",
        dict(task="synthesis", agent="editor", round_n=n,
             instructions=(
                 "Synthesize the expert record. Required sections: "
                 "'## Overview', '## Disagreement map' (each entry: "
                 "'- **<holders>**: <position> Why: <rationale>'; mark the "
                 "minority side '(minority)'), '## What the experts agree on'. "
                 "Add any section your ## Directives require. Do NOT resolve "
                 "disagreements."),
             inputs=expert_digest),
        validate=lambda t: "## Disagreement map" in t and t.count("Why:") >= 3,
        out_path=rd / "synthesis.md", max_tokens=4000)

    rejected, _ = step.run(
        "rejected_framings",
        dict(task="rejected_framings", agent="scenario_builder", round_n=n,
             instructions=(
                 "For each scenario S1-S4, list the candidate framings you "
                 "considered: exactly one line starting '- CHOSEN: ' and at "
                 "least one starting '- REJECTED: ... — reason: ...' under a "
                 "'## S<n> — <title>' heading."),
             inputs=scen_en_md),
        validate=lambda t: "REJECTED" in t and "CHOSEN" in t,
        out_path=rd / "rejected_framings.md", max_tokens=2500)

    # 4. translator (HU scenarios)
    glossary = (ROOT / "docs" / "glossary.md").read_text(encoding="utf-8")
    scen_hu, _ = step.run(
        "translator_scenarios",
        dict(task="translate_scenarios", agent="translator", lang="hu",
             round_n=n,
             instructions=(
                 "Translate the scenarios JSON below into Hungarian. Keep the "
                 "EXACT same JSON schema, ids and item counts. Use the "
                 "glossary equivalents strictly. Translate inline tags as "
                 "[bizonyíték: erős|mérsékelt|gyenge|vitatott]. Return ONLY "
                 "the JSON object.\n\nGLOSSARY:\n" + glossary),
             inputs=json.dumps(scen_en, ensure_ascii=False)),
        validate=lambda o: (valid_scenarios(
            o, require_ids=[s["id"] for s in scen_en["scenarios"]])
            and not any(s == h for s, h in zip(scen_en["scenarios"],
                                               o["scenarios"]))),
        out_path=rd / "scenarios.hu.json", postprocess=parse_json_block,
        loader=read_json, writer=write_scen, max_tokens=16000)
    scen_hu_md = render_scenarios_md(scen_hu, "hu")
    write(rd / "scenarios.hu.md", scen_hu_md)

    # 5. briefs (EN by final_brief_writer, HU by translator)
    brief_en, _ = step.run(
        "final_brief_writer",
        dict(task="brief", agent="final_brief_writer", lang="en", round_n=n,
             instructions=(
                 "Write the policy brief. It MUST contain exactly these "
                 "sections in order: " + ", ".join(f"'{h}'" for h in BRIEF_HEADERS_EN)
                 + ". Every bullet in Evidence carries an [evidence: ...] tag; "
                 "Interpretation bullets carry [interpretation]; Assumptions "
                 "carry [assumption]. Recommendations must NOT pick a single "
                 "scenario as the answer. Open questions lists what needs "
                 "human judgment. Add any section your ## Directives require."),
             inputs=scen_en_md + "\n\n" + synthesis_text),
        validate=lambda t: all(h in t for h in BRIEF_HEADERS_EN),
        out_path=rd / "brief.en.md", max_tokens=4000)

    brief_hu, _ = step.run(
        "translator_brief",
        dict(task="brief", agent="translator", lang="hu", round_n=n,
             instructions=(
                 "Translate this policy brief into Hungarian. Use EXACTLY "
                 "these section headers in place of the English ones: "
                 + ", ".join(f"'{h}'" for h in BRIEF_HEADERS_HU)
                 + ". Keep bullet counts identical. Use the glossary strictly."
                 "\n\nGLOSSARY:\n" + glossary),
             inputs=brief_en),
        validate=lambda t: (all(h in t for h in BRIEF_HEADERS_HU)
                            and t.strip() != brief_en.strip()),
        out_path=rd / "brief.hu.md", max_tokens=4000)

    # 6. critics (parallel) + translation checker
    registry_digest = "\n".join(
        f"- {fid} [{f['evidence']}]: {f['en'][:120]}... (source: {f['source']})"
        for fid, f in K.FACTS.items())

    def run_critic(name):
        extra = ""
        if name == "evidence_checker":
            extra = ("\nCURATED SOURCE REGISTRY (the only registry-backed "
                     "facts; a claim tagged stronger than its registry grade, "
                     "or citing a source not listed here without flagging it "
                     "as model knowledge, is a defect):\n" + registry_digest)
        text, _ = step.run(
            f"critic:{name}",
            dict(task="critic", agent=name, round_n=n,
                 instructions=(
                     "Critique the scenarios below. Output format per "
                     "objection:\n## S<n>.<field>\nObjection: <concrete flaw>\n"
                     "plus any lines your ## Directives require. <field> must "
                     "be one of: " + ", ".join(FIELD_KEYS) + "." + extra),
                 inputs=scen_en_md + "\n\n" + synthesis_text),
            validate=lambda t: len(CRITIC_HEADING_RE.findall(t)) >= 2
                               and "Objection:" in t,
            out_path=rd / "critic_outputs" / f"{name}.md",
            role="judge", max_tokens=2500)
        return name, text

    critics = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, text in ex.map(run_critic, D.CRITICS):
            critics[name] = text

    doc_pairs = [(scen_en_md, scen_hu_md), (brief_en, brief_hu)]
    tr_report = translation.check(scen_en, scen_hu, doc_pairs)
    tr_md = translation.render_report(tr_report, n)
    write(rd / "critic_outputs" / "translation_checker.md", tr_md)

    write_json(rd / "round_log.json", {
        "round": n, "fallbacks": step.fallbacks,
        "reused": reused_prev, "resumed": step.resumed,
        "backends": llm.backend_stats(),
    })

    return {
        "round_dir": rd, "experts": experts,
        "scenarios_en": scen_en, "scenarios_hu": scen_hu,
        "scenarios_en_md": scen_en_md, "scenarios_hu_md": scen_hu_md,
        "synthesis": synthesis_text, "rejected": rejected,
        "brief_en": brief_en, "brief_hu": brief_hu,
        "critics": critics, "translation": tr_report,
        "fallbacks": step.fallbacks, "_step": step,
    }


def run_meta_critic(n, artifacts, payload):
    """Step 7: meta-critique (judge side), fed with the scores-so-far."""
    step = artifacts["_step"]
    text, _ = step.run(
        "meta_critic",
        dict(task="meta_critique", agent="meta_critic", round_n=n,
             payload_json=json.dumps(payload, ensure_ascii=False, indent=2),
             instructions=(
                 "Write the round's meta-critique of the agent SYSTEM. "
                 "Required sections: '## Agent performance', '## Workflow', "
                 "'## Critique quality', '## Gaming judgment (explicit)' "
                 "(state GENUINE or RUBRIC-GAMING with reasons grounded in "
                 "the input scores), '## Translation consistency'. Name at "
                 "least one concrete agent or workflow weakness and, if any "
                 "agent raised no dimension for two rounds, flag it as a "
                 "removal candidate."),
             inputs=("Critic outputs digest:\n"
                     + "\n".join(f"- {k}: {len(CRITIC_HEADING_RE.findall(v))} targeted objections"
                                 for k, v in artifacts["critics"].items()))),
        validate=lambda t: "Gaming judgment" in t
                           and ("GENUINE" in t or "RUBRIC-GAMING" in t),
        out_path=artifacts["round_dir"] / "meta_critique.md",
        role="judge", max_tokens=2500)
    artifacts["fallbacks"][:] = step.fallbacks
    artifacts["meta"] = text
    return text
