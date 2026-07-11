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
from . import ledger as LG
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
RESPONSES_HEADER = {"en": "## Responses to public arguments",
                    "hu": "## Válaszok a társadalmi érvekre"}

# -- societal discourse layer (D-29) -----------------------------------------

STANCES = ("support", "oppose", "conditional", "no_position")
POSITION_LABELS = ("documented", "value_modeled", "no_position")

VOICE_SCHEMA_HINT = json.dumps({
    "voice": "<your agent name>",
    "reactions": [{
        "scenario": "S1", "stance": "support|oppose|conditional|no_position",
        "label": "documented|value_modeled|no_position",
        "source": "<document/URL — REQUIRED when label=documented, else empty>",
        "basis": "<the documented values it derives from — REQUIRED when "
                 "label=value_modeled, else empty>",
        "interest": "<whose interest you defend>",
        "public_good_frame": "<your public-good framing>",
        "argument": "<justification; a bare stance is invalid. For "
                    "no_position: one line on why the interest implies "
                    "nothing here>",
        "condition_to_change": "<what would change your stance; empty only "
                               "for no_position>",
    }]
}, indent=2)

RELEVANCE_LEVELS = ("high", "medium", "low")

ARGMAP_SCHEMA_HINT = json.dumps({
    "clusters": [{
        "id": "A1", "scenario": "S1", "kind": "fact|value|mixed",
        "side": "pro|con|conditional",
        "claim": "<one-sentence canonical form of the argument>",
        "raised_by": ["<voice name>"],
        "interest": "<whose interest is behind this argument>",
        "value": "<which value is in tension, e.g. equity vs. excellence>",
        "fear": "<the anticipated loss or harm driving it — emotional "
                "framing here is not a defect, name the real need behind it>",
        "affected": ["<actor group affected by this argument>"],
        "assumption": "<the unstated assumption the claim rests on>",
        "empirical_uncertainty": "<is the factual part of this settled, "
                                 "contested, or unknown — and why>",
        "decision_relevance": "high|medium|low — how much would resolving "
                              "this change the actual decision",
        "attention": {
            "high_attention": "true|false — does this argument draw a lot "
                              "of public/media attention",
            "new_information": "true|false — does it carry information "
                               "not already covered by another cluster",
            "changes_evaluation": "true|false — would resolving it change "
                                  "how a scenario is evaluated",
            "already_answered": "true|false — is this substantively "
                                "answered elsewhere in the record already",
            "primarily_rhetorical": "true|false — is its main role "
                                    "rhetorical/identity-signalling rather "
                                    "than substantive",
        },
    }]
}, indent=2)

ATTENTION_KEYS = ("high_attention", "new_information", "changes_evaluation",
                  "already_answered", "primarily_rhetorical")


def valid_voice(obj):
    try:
        rs = obj["reactions"]
    except (TypeError, KeyError):
        return False
    if not isinstance(rs, list) or \
            {r.get("scenario") for r in rs} != {"S1", "S2", "S3", "S4"}:
        return False
    for r in rs:
        if r.get("stance") not in STANCES:
            return False
        if r.get("label") not in POSITION_LABELS:
            return False
        if (r["stance"] == "no_position") != (r["label"] == "no_position"):
            return False
        if len(str(r.get("argument", "")).strip()) < 10:
            return False
        if r["label"] == "documented" and not str(r.get("source", "")).strip():
            return False
        if r["label"] == "value_modeled" and not str(r.get("basis", "")).strip():
            return False
        if r["stance"] != "no_position" and \
                not str(r.get("condition_to_change", "")).strip():
            return False
    return True


def valid_argmap(obj, voice_names):
    try:
        cl = obj["clusters"]
    except (TypeError, KeyError):
        return False
    if not isinstance(cl, list) or len(cl) < 6:
        return False
    ids = [c.get("id", "") for c in cl]
    if len(set(ids)) != len(ids):
        return False
    for c in cl:
        if not re.fullmatch(r"A\d+", c.get("id", "")):
            return False
        if c.get("scenario") not in ("S1", "S2", "S3", "S4"):
            return False
        if c.get("kind") not in ("fact", "value", "mixed"):
            return False
        if c.get("side") not in ("pro", "con", "conditional"):
            return False
        rb = c.get("raised_by")
        if not rb or not set(rb) <= set(voice_names):
            return False
        if not str(c.get("claim", "")).strip():
            return False
        for field in ("interest", "value", "fear", "assumption",
                      "empirical_uncertainty"):
            if not str(c.get(field, "")).strip():
                return False
        affected = c.get("affected")
        if not affected or not all(str(a).strip() for a in affected):
            return False
        if c.get("decision_relevance") not in RELEVANCE_LEVELS:
            return False
        attn = c.get("attention")
        if not isinstance(attn, dict) or \
                not all(isinstance(attn.get(k), bool) for k in ATTENTION_KEYS):
            return False
    return True


def valid_reciprocity(obj, cluster_ids):
    try:
        rs = obj["responses"]
    except (TypeError, KeyError):
        return False
    if not isinstance(rs, list) or not rs:
        return False
    return all(r.get("cluster") in cluster_ids
               and len(str(r.get("response", "")).strip()) >= 10
               and r.get("outcome") in ("maintain", "revise") for r in rs)


def responds_to_clusters(text, lang, cluster_ids):
    """Response obligation (CNDP): the brief answers the argument clusters.
    Word-boundary match (A1 must not count via A10); coverage threshold (not
    all-ids) so a mock fallback whose id set differs slightly from a live
    argument map cannot deadlock the round."""
    if RESPONSES_HEADER[lang] not in text:
        return False
    hits = sum(1 for cid in cluster_ids
               if re.search(rf"\b{cid}\b", text))
    return hits >= max(6, int(0.8 * len(cluster_ids)))

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


def run_discourse(step, rd, n, scen_en_md, glossary, disc_cfg):
    """Societal-discourse layer (D-29): voices react to the scenarios, the
    mediator builds the argument map, the evidence layer grades factual
    claims, an optional reciprocity pass makes the voices answer their
    strongest counter-argument, and the argument ledger is rendered
    deterministically (EN) + translated (HU)."""
    voice_names = list(D.DISCOURSE)
    ddir = rd / "discourse"

    def run_voice(name):
        obj, _ = step.run(
            f"voice:{name}",
            dict(task="discourse_voice", agent=name, round_n=n,
                 instructions=(
                     "This is a STAKEHOLDER STRESS TEST, not a simulation: "
                     "you model a plausible objection/interest-conflict for "
                     "real stakeholders to verify later — you are NOT "
                     "predicting what real people or organisations will "
                     "actually think. React to each scenario below AS THE "
                     "INTEREST/VALUE VOICE your spec defines — you "
                     "represent, you do not give expert judgment. Return "
                     f"ONLY a JSON object with this exact schema:\n"
                     f"{VOICE_SCHEMA_HINT}\n"
                     "Rules: one reaction per scenario (S1..S4); a stance "
                     "without justification is invalid; no_position is the "
                     "honest choice when your interest implies nothing; "
                     "NEVER attribute an unsourced position to a real "
                     "organisation — use value_modeled with its basis."),
                 inputs=scen_en_md),
            validate=valid_voice, out_path=ddir / "voices" / f"{name}.json",
            postprocess=parse_json_block, loader=read_json,
            writer=lambda p, o: write_json(p, o), max_tokens=4000)
        return name, obj

    voices = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, obj in ex.map(run_voice, voice_names):
            voices[name] = obj

    voices_digest = json.dumps(
        {k: v["reactions"] for k, v in voices.items()}, ensure_ascii=False)

    arg_map, _ = step.run(
        "argument_map",
        dict(task="argument_map", agent="discourse_mediator", round_n=n,
             instructions=(
                 "Cluster the voices' arguments into an argument map, and "
                 "decompose EACH cluster (structured counter-argument "
                 "processing): the interest behind it, the value in "
                 "tension, the fear/anticipated loss driving it (name the "
                 "real need behind emotional framing, do not dismiss it as "
                 "a defect), which actor group(s) are affected, the "
                 "unstated assumption it rests on, whether its factual part "
                 "is settled/contested/unknown, and how much resolving it "
                 "would actually change the decision (decision_relevance). "
                 "Also screen each cluster for 'gumicsont' status (a debate "
                 "that draws a lot of attention but would not change the "
                 "decision if resolved): does it draw high attention, does "
                 "it carry new information, would resolving it change a "
                 "scenario's evaluation, is it already answered elsewhere, "
                 "is its main role rhetorical/identity-signalling. High "
                 "attention + low decision_relevance is exactly what real "
                 "participants need flagged, not hidden. "
                 "Return ONLY a JSON object with this exact schema:\n"
                 + ARGMAP_SCHEMA_HINT +
                 "\nRules: stable sequential ids A1..An; aim for 8-24 "
                 "clusters — MERGE near-duplicate arguments across voices "
                 "and scenarios into one canonical claim instead of "
                 "enumerating variants; every claim in canonical "
                 "one-sentence form; classify fact vs value vs mixed; "
                 "raised_by lists ONLY voice names that actually raise it; "
                 "NEVER drop a minority argument; do not count heads."),
             inputs=voices_digest),
        validate=lambda o: valid_argmap(o, voice_names),
        out_path=ddir / "argument_map.json", postprocess=parse_json_block,
        loader=read_json, writer=lambda p, o: write_json(p, o),
        max_tokens=6000)
    clusters = arg_map["clusters"]
    cluster_ids = [c["id"] for c in clusters]
    factual = [c["id"] for c in clusters if c["kind"] in ("fact", "mixed")]

    registry_digest = "\n".join(
        f"- {fid} [{f['evidence']}]: {f['en'][:120]} (source: {f['source']})"
        for fid, f in K.FACTS.items())
    grades_text, _ = step.run(
        "grade_arguments",
        dict(task="grade_arguments", agent="evidence_checker", round_n=n,
             instructions=(
                 "Grade the FACTUAL claim of every fact/mixed argument "
                 "cluster below against the curated registry. Output one "
                 "line per cluster, nothing else:\n"
                 "A<i>: [evidence: strong|moderate|weak|contested — "
                 "<registry source>] <one-line note>\n"
                 "or, when no registry fact supports it:\n"
                 "A<i>: [not registry-backed — treat as model knowledge] "
                 "<one-line note>\n"
                 "Value claims are NOT graded.\n\nREGISTRY:\n"
                 + registry_digest),
             inputs=json.dumps(clusters, ensure_ascii=False)),
        # lenient prefixes ('- ', '**') and 90% coverage: a judge that skips
        # one cluster of thirty must not force a full mock fallback
        validate=lambda t: sum(
            1 for cid in factual if re.search(
                rf"^[\s\-\*]*{cid}\**\s*:.*(\[evidence:|not registry-backed)",
                t, re.M)) >= max(1, int(0.9 * len(factual))),
        out_path=ddir / "argument_grades.md", role="judge", max_tokens=4000)
    grades = LG.grade_lines(grades_text)

    responses = {name: None for name in voice_names}
    if disc_cfg.get("reciprocity", True):
        clusters_digest = json.dumps(clusters, ensure_ascii=False)

        def run_response(name):
            obj, _ = step.run(
                f"response:{name}",
                dict(task="discourse_reciprocity", agent=name, round_n=n,
                     instructions=(
                         "Reciprocity pass (DQI): from the argument map "
                         "below, pick the strongest argument AGAINST your "
                         "stated positions and answer it. Return ONLY JSON: "
                         '{"voice": "<name>", "responses": [{"cluster": '
                         '"A<i>", "response": "<engage the argument on its '
                         'merits>", "outcome": "maintain|revise", '
                         '"new_condition": "<if revised>"}]} — answering '
                         "means engaging, not repeating yourself."),
                     inputs=("YOUR REACTIONS:\n"
                             + json.dumps(voices[name]["reactions"],
                                          ensure_ascii=False)
                             + "\n\nARGUMENT MAP:\n" + clusters_digest)),
                validate=lambda o: valid_reciprocity(o, set(cluster_ids)),
                out_path=ddir / "responses" / f"{name}.json",
                postprocess=parse_json_block, loader=read_json,
                writer=lambda p, o: write_json(p, o), max_tokens=2000)
            return name, obj

        with ThreadPoolExecutor(max_workers=4) as ex:
            for name, obj in ex.map(run_response, voice_names):
                responses[name] = obj

    ledger_en = LG.render_ledger(n, voices, clusters, grades, responses, "en")
    write(rd / "argument_ledger.en.md", ledger_en)

    ledger_hu, _ = step.run(
        "translate_ledger",
        dict(task="translate_ledger", agent="translator", lang="hu",
             round_n=n,
             instructions=(
                 "Translate this argument ledger into Hungarian. Use EXACTLY "
                 f"these headings: '# Érv-főkönyv — {n}. kör', "
                 "'## Álláspont-mátrix', '## Érvklaszterek', "
                 "'## Reciprocitás-kör' (only if present in the source), "
                 "'## Feltétel-regiszter'. Keep every A<i> id and every "
                 "voice name unchanged. Use the glossary strictly.\n\n"
                 "GLOSSARY:\n" + glossary),
             inputs=ledger_en),
        validate=lambda t: ("## Álláspont-mátrix" in t
                            and "## Érvklaszterek" in t
                            and "## Feltétel-regiszter" in t
                            and len(re.findall(r"\*\*A\d+\*\*", t)) >= 6
                            and t.strip() != ledger_en.strip()),
        out_path=rd / "argument_ledger.hu.md", max_tokens=8000)

    stances = [r["stance"] for v in voices.values() for r in v["reactions"]]
    labels = [r["label"] for v in voices.values() for r in v["reactions"]]
    conditions = [f"{name} ({r['scenario']}): {r['condition_to_change']}"
                  for name, v in voices.items() for r in v["reactions"]
                  if r["stance"] != "no_position"
                  and str(r.get("condition_to_change", "")).strip()]
    metrics = {
        "voices": len(voices),
        "stance_counts": {s: stances.count(s) for s in STANCES},
        "label_counts": {lb: labels.count(lb) for lb in POSITION_LABELS},
        "clusters": len(clusters),
        "factual_clusters_graded": len([c for c in factual if c in grades]),
        "reciprocity": {"ran": bool(disc_cfg.get("reciprocity", True)),
                        "revised": sum(1 for rp in responses.values() if rp
                                       for it in rp["responses"]
                                       if it["outcome"] == "revise")},
    }
    return dict(voices=voices, argument_map=arg_map, grades=grades,
                responses=responses, ledger_en=ledger_en,
                ledger_hu=ledger_hu, cluster_ids=cluster_ids,
                conditions=conditions, metrics=metrics)


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

    glossary = (ROOT / "docs" / "glossary.md").read_text(encoding="utf-8")

    # 3.5 societal-discourse layer (D-29): argument ledger
    disc_cfg = cfg.get("discourse", {})
    disc = None
    if disc_cfg.get("enabled"):
        disc = run_discourse(step, rd, n, scen_en_md, glossary, disc_cfg)

    # 4. translator (HU scenarios)
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

    # 5. briefs (EN by final_brief_writer, HU by translator). With the
    #    discourse layer on, the brief carries the response obligation
    #    (D-29, CNDP model): every argument cluster gets an answer.
    brief_instr = (
        "Write the policy brief. It MUST contain exactly these "
        "sections in order: " + ", ".join(f"'{h}'" for h in BRIEF_HEADERS_EN)
        + ". Every bullet in Evidence carries an [evidence: ...] tag; "
        "Interpretation bullets carry [interpretation]; Assumptions "
        "carry [assumption]. Recommendations must NOT pick a single "
        "scenario as the answer. Open questions lists what needs "
        "human judgment. Add any section your ## Directives require.")
    brief_inputs = scen_en_md + "\n\n" + synthesis_text
    if disc:
        brief_instr += (
            " After Recommendations, add a section "
            f"'{RESPONSES_HEADER['en']}' answering EVERY argument cluster "
            "from the ledger by id (one bullet per cluster: '- A<i> "
            "(<short restatement>): accepted / rejected / left open — "
            "<one-line reason>'). An argument answered by no one is a "
            "defect (response obligation).")
        brief_inputs += ("\n\n=== ARGUMENT LEDGER (public arguments that "
                         "MUST each be answered) ===\n" + disc["ledger_en"])
    brief_en, _ = step.run(
        "final_brief_writer",
        dict(task="brief", agent="final_brief_writer", lang="en", round_n=n,
             instructions=brief_instr, inputs=brief_inputs),
        validate=lambda t: (all(h in t for h in BRIEF_HEADERS_EN)
                            and (not disc or responds_to_clusters(
                                t, "en", disc["cluster_ids"]))),
        out_path=rd / "brief.en.md", max_tokens=6000)

    brief_hu_instr = (
        "Translate this policy brief into Hungarian. Use EXACTLY "
        "these section headers in place of the English ones: "
        + ", ".join(f"'{h}'" for h in BRIEF_HEADERS_HU)
        + ". Keep bullet counts identical. Use the glossary strictly.")
    if disc:
        brief_hu_instr += (f" Translate '{RESPONSES_HEADER['en']}' as "
                           f"'{RESPONSES_HEADER['hu']}' and keep every "
                           "A<i> id unchanged.")
    brief_hu, _ = step.run(
        "translator_brief",
        dict(task="brief", agent="translator", lang="hu", round_n=n,
             instructions=brief_hu_instr + "\n\nGLOSSARY:\n" + glossary,
             inputs=brief_en),
        validate=lambda t: (all(h in t for h in BRIEF_HEADERS_HU)
                            and t.strip() != brief_en.strip()
                            and (not disc or responds_to_clusters(
                                t, "hu", disc["cluster_ids"]))),
        out_path=rd / "brief.hu.md", max_tokens=6000)

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
        "discourse": disc["metrics"] if disc else None,
        "backends": llm.backend_stats(),
    })

    return {
        "round_dir": rd, "experts": experts,
        "scenarios_en": scen_en, "scenarios_hu": scen_hu,
        "scenarios_en_md": scen_en_md, "scenarios_hu_md": scen_hu_md,
        "synthesis": synthesis_text, "rejected": rejected,
        "brief_en": brief_en, "brief_hu": brief_hu,
        "critics": critics, "translation": tr_report,
        "discourse": disc["metrics"] if disc else None,
        "ledger_conditions": disc["conditions"] if disc else [],
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
