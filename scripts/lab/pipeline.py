"""Round runner: experts → scenarios → synthesis → translation → critics →
meta-critic. Every model call goes through lab.llm.call_model; every step
validates its output, retries once with a corrective instruction, and falls
back to the deterministic mock composition if the real backend cannot satisfy
the format (fallbacks are recorded per step)."""
import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor

from . import agent_defs as D
from . import knowledge as K
from . import llm, mock_backend, translation
from .agents import build_prompt
from .util import (AGENTS_DIR, CONFIG_PATH, ROOT, TEMPLATES_DIR, load_config,
                   round_dir, write, write_json)

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


class Step:
    """One generation step with validation, one corrective retry, and a
    deterministic mock fallback."""

    def __init__(self, fallbacks):
        self.fallbacks = fallbacks  # shared list of step names that degraded

    def run(self, name, prompt_kwargs, validate, role="generator",
            max_tokens=8000, postprocess=lambda t: t):
        corrective = ""
        for attempt in (0, 1):
            kw = dict(prompt_kwargs)
            if corrective:
                kw["instructions"] = kw.get("instructions", "") + "\n" + corrective
            prompt = build_prompt(**kw)
            text = llm.call_model(prompt, role, max_tokens=max_tokens)
            backend = llm.CALL_LOG[-1]["backend"]
            try:
                result = postprocess(text)
                if validate(result):
                    return result, backend
            except Exception:
                pass
            corrective = ("PREVIOUS ATTEMPT FAILED FORMAT VALIDATION. Follow "
                          "the output format EXACTLY as specified, with no "
                          "surrounding commentary.")
        # deterministic fallback
        self.fallbacks.append(name)
        prompt = build_prompt(**prompt_kwargs)
        result = postprocess(mock_backend.compose(prompt, role))
        if not validate(result):
            raise RuntimeError(f"mock fallback failed validation for step {name}")
        return result, "mock-fallback"


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


def snapshot_system_state(rd):
    dest = rd / "system_state"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(AGENTS_DIR, dest / "agents")
    shutil.copy(CONFIG_PATH, dest / "system_config.json")
    shutil.copy(TEMPLATES_DIR / "evaluation_rubric.md", dest / "evaluation_rubric.md")


def run_round(n):
    """Generate all round-n artifacts (steps 1-6 of the workflow). Evaluation,
    meta-critique and improvement planning are orchestrated by the loop."""
    cfg = load_config()
    rd = round_dir(n, create=True)
    snapshot_system_state(rd)
    fallbacks = []
    step = Step(fallbacks)
    question = cfg["policy_question"]

    # 1. experts (parallel; unchanged specs reuse the previous round's live
    #    output — same deterministic input, saves daily API quota, D-19)
    prev_rd = round_dir(n - 1) if n > 1 else None
    prev_log = {}
    if prev_rd and (prev_rd / "round_log.json").exists():
        import json as _json
        prev_log = _json.loads((prev_rd / "round_log.json").read_text())
    reused = []

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
        return out_prev.read_text(encoding="utf-8")

    def run_expert(name):
        cached = reusable_expert(name)
        if cached is not None:
            reused.append(f"expert:{name}")
            return name, cached, "reused"
        return name, *step.run(
            f"expert:{name}",
            dict(task="expert_analysis", agent=name, round_n=n,
                 instructions=(
                     f"Policy question: {question}\n"
                     "Write your analysis following your Output template. "
                     "Sections required: '## Findings (evidence)' (each "
                     "finding with an inline [evidence: ...] tag and source), "
                     "'## Interpretation', '## Assumptions', '## Position', "
                     "'## Uncertainties'.")),
            validate=lambda t: "[evidence:" in t and "## Position" in t
                               and "## Uncertainties" in t,
            max_tokens=3000)

    experts = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, text, backend in ex.map(run_expert, D.EXPERTS):
            experts[name] = text
            write(rd / "expert_outputs" / f"{name}.md", text)

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
        postprocess=parse_json_block, max_tokens=16000)
    write_json(rd / "scenarios.json", scen_en)
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
        max_tokens=4000)
    write(rd / "synthesis.md", synthesis_text)

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
        max_tokens=2500)
    write(rd / "rejected_framings.md", rejected)

    # 4. translator (HU scenarios + HU brief later)
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
        postprocess=parse_json_block, max_tokens=16000)
    write_json(rd / "scenarios.hu.json", scen_hu)
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
        max_tokens=4000)
    write(rd / "brief.en.md", brief_en)

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
        max_tokens=4000)
    write(rd / "brief.hu.md", brief_hu)

    # 6. critics (parallel) + translation checker
    def run_critic(name):
        return name, *step.run(
            f"critic:{name}",
            dict(task="critic", agent=name, round_n=n,
                 instructions=(
                     "Critique the scenarios below. Output format per "
                     "objection:\n## S<n>.<field>\nObjection: <concrete flaw>\n"
                     "plus any lines your ## Directives require. <field> must "
                     "be one of: " + ", ".join(FIELD_KEYS) + "."),
                 inputs=scen_en_md + "\n\n" + synthesis_text),
            validate=lambda t: len(CRITIC_HEADING_RE.findall(t)) >= 2
                               and "Objection:" in t,
            role="judge", max_tokens=2500)

    critics = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, text, backend in ex.map(run_critic, D.CRITICS):
            critics[name] = text
            write(rd / "critic_outputs" / f"{name}.md", text)

    doc_pairs = [(scen_en_md, scen_hu_md), (brief_en, brief_hu)]
    tr_report = translation.check(scen_en, scen_hu, doc_pairs)
    tr_md = translation.render_report(tr_report, n)
    write(rd / "critic_outputs" / "translation_checker.md", tr_md)

    write_json(rd / "round_log.json", {
        "round": n, "fallbacks": fallbacks, "reused": reused,
        "backends": llm.backend_stats(),
    })

    return {
        "round_dir": rd, "experts": experts,
        "scenarios_en": scen_en, "scenarios_hu": scen_hu,
        "scenarios_en_md": scen_en_md, "scenarios_hu_md": scen_hu_md,
        "synthesis": synthesis_text, "rejected": rejected,
        "brief_en": brief_en, "brief_hu": brief_hu,
        "critics": critics, "translation": tr_report,
        "fallbacks": fallbacks,
    }


def run_meta_critic(n, artifacts, payload):
    """Step 7: meta-critique (judge side), fed with the scores-so-far."""
    step = Step(artifacts["fallbacks"])
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
        role="judge", max_tokens=2500)
    write(artifacts["round_dir"] / "meta_critique.md", text)
    artifacts["meta"] = text
    return text
