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
import time
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

# The 10-section deliberation deliverable (D-30), replacing the old 5-layer
# Evidence/Interpretation/Assumptions/Recommendations/Open-questions split.
# The per-claim tagging discipline that split used to enforce is NOT
# dropped — it moves from a page-level split to a per-bullet [fact] /
# [estimate] / [assumption] / [value] tag, applied wherever the claim lands.
BRIEF_HEADERS_EN = [
    "## What we know", "## What we consider likely",
    "## Where experts disagree", "## What we don't know",
    "## What could be done", "## What each option costs",
    "## What research could resolve", "## What people must decide",
    "## What to verify with real stakeholders",
    "## Where the red herrings are",
]
BRIEF_HEADERS_HU = [
    "## Amit már tudunk", "## Amit valószínűnek tartunk",
    "## Amiben nincs szakértői egyetértés", "## Amit nem tudunk",
    "## Mit lehetne tenni", "## Mi az egyes alternatívák ára",
    "## Mit lehet még kutatással eldönteni",
    "## Mit kell embereknek eldönteniük",
    "## Mit kell valódi stakeholderekkel ellenőrizni",
    "## Hol vannak a gumicsontok",
]
RESPONSES_HEADER = {"en": BRIEF_HEADERS_EN[8], "hu": BRIEF_HEADERS_HU[8]}
CLAIM_TAGS = ("fact", "estimate", "assumption", "value")

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
ATTENTION_KEYS = ("high_attention", "new_information", "changes_evaluation",
                  "already_answered", "primarily_rhetorical")

# Argument-map generation is split into two phases (issue: the D-30 8-field
# per-cluster decomposition made one giant one-shot call too failure-prone —
# a single dropped field anywhere in 8-16 clusters failed the whole map, and
# the mock fallback then discarded ALL the live clustering work). Phase 1
# clusters cheaply (small schema, same shape as pre-D-30); phase 2 decomposes
# EACH cluster in its own small, parallel, independently-retryable/resumable
# call — a bad cluster degrades alone, live clustering is never thrown away.
CLUSTER_BASIC_SCHEMA_HINT = json.dumps({
    "clusters": [{
        "id": "A1", "scenario": "S1", "kind": "fact|value|mixed",
        "side": "pro|con|conditional",
        "claim": "<one-sentence canonical form of the argument>",
        "raised_by": ["<voice name>"],
    }]
}, indent=2)

CLUSTER_DECOMPOSE_FIELD_GUIDE = (
    "Field meanings: interest = whose interest is behind this argument; "
    "value = which value is in tension (e.g. equity vs. excellence); "
    "fear = the anticipated loss or harm driving it (emotional framing "
    "here is not a defect, name the real need behind it); affected = "
    "actor group(s) affected; assumption = the unstated assumption the "
    "claim rests on; empirical_uncertainty = is the factual part of this "
    "settled, contested, or unknown, and why; decision_relevance = how "
    "much would resolving this change the actual decision; "
    "attention.high_attention = does this argument draw a lot of "
    "public/media attention; attention.new_information = does it carry "
    "information not already covered by another cluster; "
    "attention.changes_evaluation = would resolving it change how a "
    "scenario is evaluated; attention.already_answered = is this "
    "substantively answered elsewhere in the record already; "
    "attention.primarily_rhetorical = is its main role rhetorical/"
    "identity-signalling rather than substantive.")

# Literal example values, not "true|false — <explanation>" placeholders: a
# placeholder that mixes an enum/boolean with an inline explanation reliably
# gets echoed back literally (e.g. "true — teacher shortages are a salient
# public topic" as the STRING value of a boolean field) instead of producing
# a bare boolean/enum — every field's semantics live in
# CLUSTER_DECOMPOSE_FIELD_GUIDE (prose) instead, and the schema stays a
# clean structural example.
CLUSTER_DECOMPOSE_SCHEMA_HINT = json.dumps({
    "interest": "<one sentence>", "value": "<one sentence>",
    "fear": "<one sentence>", "affected": ["<actor group>", "..."],
    "assumption": "<one sentence>", "empirical_uncertainty": "<one sentence>",
    "decision_relevance": "high",
    "attention": {
        "high_attention": True, "new_information": False,
        "changes_evaluation": False, "already_answered": False,
        "primarily_rhetorical": False,
    },
}, indent=2)

# The ledger's HU version used to come from ONE call translating the fully
# rendered document — at 17 clusters that's 200KB+ of source text, which
# needs more output than the Anthropic SDK allows without switching to
# streaming (a >10-minute non-streamed call is rejected outright). Instead
# translate the underlying DATA in small per-voice/per-cluster pieces (same
# principle as the argument-map split), then call ledger.render_ledger()
# again — the EXACT same deterministic renderer already used for EN — to
# produce the HU document. Scales to any cluster count; no separate
# "translate the whole document" step needed at all.
TRANSLATE_CLUSTER_SCHEMA_HINT = json.dumps({
    "claim": "<translated>", "interest": "<translated>",
    "value": "<translated>", "fear": "<translated>",
    "affected": ["<translated>", "..."], "assumption": "<translated>",
    "empirical_uncertainty": "<translated>",
}, indent=2)


def valid_cluster_translation(d):
    if not isinstance(d, dict):
        return False
    for field in ("claim", "interest", "value", "fear", "assumption",
                  "empirical_uncertainty"):
        if not str(d.get(field, "")).strip():
            return False
    affected = d.get("affected")
    if not affected or not all(str(a).strip() for a in affected):
        return False
    return True


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


def valid_argmap_basic(obj, voice_names):
    """Phase 1 (clustering only — id/scenario/kind/side/claim/raised_by)."""
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
    return True


def valid_cluster_decomposition(d):
    """Phase 2 (per-cluster decomposition — one cluster's extra fields)."""
    if not isinstance(d, dict):
        return False
    for field in ("interest", "value", "fear", "assumption",
                  "empirical_uncertainty"):
        if not str(d.get(field, "")).strip():
            return False
    affected = d.get("affected")
    if not affected or not all(str(a).strip() for a in affected):
        return False
    if d.get("decision_relevance") not in RELEVANCE_LEVELS:
        return False
    attn = d.get("attention")
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


RESPONSE_TYPES = ("evidence_answerable", "policy_design_fixable",
                  "communication_fixable", "value_conflict",
                  "irreducible_tradeoff", "needs_more_info",
                  "not_decision_relevant")


def response_types_valid(text, cluster_ids, valid_types=RESPONSE_TYPES):
    """Typed response obligation (D-30): a bare accepted/rejected/left-open
    verdict is replaced by one of 7 tokens naming HOW the argument can be
    resolved (or honestly can't). The token is a stable identifier, like the
    A<i> ids — unchanged across languages, translated prose around it.
    Additive to responds_to_clusters(): same coverage threshold, does not
    change its behaviour."""
    type_alt = "|".join(valid_types)
    hits = sum(1 for cid in cluster_ids
               if re.search(rf"\b{cid}\b[^\n]*\b(?:{type_alt})\b", text))
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

    def __init__(self, rd, resume, round_n=None):
        self.rd = rd
        self.resume = resume
        self.round_n = round_n
        self.fallbacks = []
        self.resumed = []
        self.journal_path = rd / "steps.jsonl"
        self._prior = {}
        self._t0 = time.time()
        self._count = 0
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
        self._count += 1
        elapsed = time.time() - self._t0
        rlabel = f"round {self.round_n:02d}" if self.round_n else "round"
        print(f"[{rlabel}] {self._count:>3}. {name:<32} {backend:<20} "
             f"(+{elapsed:6.0f}s)", flush=True)

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
                    self._count += 1
                    elapsed = time.time() - self._t0
                    rlabel = f"round {self.round_n:02d}" if self.round_n else "round"
                    print(f"[{rlabel}] {self._count:>3}. {name:<32} "
                         f"{'resumed (' + backend + ')':<20} "
                         f"(+{elapsed:6.0f}s)", flush=True)
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
            writer=lambda p, o: write_json(p, o), max_tokens=6000)
        return name, obj

    voices = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, obj in ex.map(run_voice, voice_names):
            voices[name] = obj

    voices_digest = json.dumps(
        {k: v["reactions"] for k, v in voices.items()}, ensure_ascii=False)

    # Phase 1: cluster only (small schema — the same shape as pre-D-30).
    arg_map_basic, _ = step.run(
        "argument_map",
        dict(task="argument_map", agent="discourse_mediator", round_n=n,
             instructions=(
                 "Cluster the voices' arguments into an argument map. "
                 "Return ONLY a JSON object with this exact schema:\n"
                 + CLUSTER_BASIC_SCHEMA_HINT +
                 "\nRules: stable sequential ids A1..An; aim for 8-16 "
                 "clusters — MERGE near-duplicate arguments across voices "
                 "and scenarios into one canonical claim instead of "
                 "enumerating variants; every claim in canonical "
                 "one-sentence form; classify fact vs value vs mixed; "
                 "raised_by lists ONLY voice names that actually raise it; "
                 "NEVER drop a minority argument; do not count heads."),
             inputs=voices_digest),
        validate=lambda o: valid_argmap_basic(o, voice_names),
        out_path=ddir / "argument_map_basic.json", postprocess=parse_json_block,
        loader=read_json, writer=lambda p, o: write_json(p, o),
        max_tokens=6000)
    clusters_basic = arg_map_basic["clusters"]

    # Phase 2: decompose EACH cluster in its own small, parallel,
    # independently-resumable call (issue: one dropped field anywhere in
    # 8-16 clusters used to fail the WHOLE map and discard all the live
    # clustering work — see the comment above CLUSTER_BASIC_SCHEMA_HINT).
    def decompose_cluster(c):
        cid = c["id"]
        context_lines = []
        for name in c["raised_by"]:
            v = voices.get(name)
            r = next((x for x in v["reactions"]
                     if x["scenario"] == c["scenario"]), None) if v else None
            if r:
                context_lines.append(
                    f"- {name} ({r['stance']}, {r['label']}): "
                    f"{r['argument']} Condition: "
                    f"{r.get('condition_to_change', '')}")
        obj, _ = step.run(
            f"decompose:{cid}",
            dict(task="argument_decompose", agent="discourse_mediator",
                 round_n=n,
                 instructions=(
                     f"For argument cluster {cid} (scenario "
                     f"{c['scenario']}, {c['kind']}/{c['side']}): "
                     f"\"{c['claim']}\"\ndecompose it for the stakeholder "
                     "stress test digest, and screen it for 'gumicsont' "
                     "status (a debate that draws a lot of attention but "
                     "would not change the decision if resolved: high "
                     "attention + low decision_relevance is exactly what "
                     "real participants need flagged, not hidden).\n"
                     + CLUSTER_DECOMPOSE_FIELD_GUIDE +
                     "\nReturn ONLY a JSON object with this exact "
                     "schema:\n" + CLUSTER_DECOMPOSE_SCHEMA_HINT +
                     "\nRules: decision_relevance MUST be the bare word "
                     "high, medium, or low — no explanation in that field. "
                     "Every attention.* value MUST be a literal JSON "
                     "boolean (true or false) — no explanation in that "
                     "field either; put any reasoning in the prose fields "
                     "(interest/value/fear/assumption/"
                     "empirical_uncertainty) instead."),
                 inputs=("ORIGINAL VOICE ARGUMENTS RAISING THIS CLUSTER:\n"
                        + "\n".join(context_lines))),
            validate=valid_cluster_decomposition,
            out_path=ddir / "clusters" / f"{cid}.json",
            postprocess=parse_json_block, loader=read_json,
            writer=lambda p, o: write_json(p, o), max_tokens=1500)
        return cid, obj

    decompositions = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for cid, obj in ex.map(decompose_cluster, clusters_basic):
            decompositions[cid] = obj

    clusters = []
    for c in clusters_basic:
        merged = dict(c)
        merged.update(decompositions[c["id"]])
        clusters.append(merged)
    write_json(ddir / "argument_map.json", {"clusters": clusters})
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
        out_path=ddir / "argument_grades.md", role="judge", max_tokens=6000)
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
                writer=lambda p, o: write_json(p, o), max_tokens=3000)
            return name, obj

        with ThreadPoolExecutor(max_workers=4) as ex:
            for name, obj in ex.map(run_response, voice_names):
                responses[name] = obj

    ledger_en = LG.render_ledger(n, voices, clusters, grades, responses, "en")
    write(rd / "argument_ledger.en.md", ledger_en)

    # HU: translate the data in small parallel pieces, then render with the
    # same deterministic renderer used for EN (see the comment above
    # TRANSLATE_CLUSTER_SCHEMA_HINT).
    def translate_voice(name):
        v = voices[name]
        obj, _ = step.run(
            f"translate_voice:{name}",
            dict(task="translate_voice", agent="translator", lang="hu",
                 round_n=n,
                 instructions=(
                     "Translate this discourse voice's reactions into "
                     "Hungarian. Keep the exact same JSON schema and every "
                     "scenario id, stance, and label value unchanged — "
                     "translate only the prose fields (interest, "
                     "public_good_frame, argument, condition_to_change, "
                     "basis). Return ONLY the JSON object.\n\nGLOSSARY:\n"
                     + glossary),
                 inputs=json.dumps(v, ensure_ascii=False)),
            validate=valid_voice, out_path=ddir / "voices_hu" / f"{name}.json",
            postprocess=parse_json_block, loader=read_json,
            writer=lambda p, o: write_json(p, o), max_tokens=6000)
        return name, obj

    voices_hu = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, obj in ex.map(translate_voice, voice_names):
            voices_hu[name] = obj

    def translate_cluster(c):
        cid = c["id"]
        obj, _ = step.run(
            f"translate_cluster:{cid}",
            dict(task="translate_cluster", agent="translator", lang="hu",
                 round_n=n,
                 instructions=(
                     f"Translate argument cluster {cid}'s text fields into "
                     "Hungarian. Return ONLY a JSON object with this exact "
                     "schema:\n" + TRANSLATE_CLUSTER_SCHEMA_HINT
                     + "\n\nGLOSSARY:\n" + glossary),
                 inputs=json.dumps(
                     {k: c[k] for k in ("claim", "interest", "value", "fear",
                                        "affected", "assumption",
                                        "empirical_uncertainty")},
                     ensure_ascii=False)),
            validate=valid_cluster_translation,
            out_path=ddir / "clusters_hu" / f"{cid}.json",
            postprocess=parse_json_block, loader=read_json,
            writer=lambda p, o: write_json(p, o), max_tokens=1500)
        merged = dict(c)
        merged.update(obj)
        return cid, merged

    clusters_hu_by_id = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for cid, merged in ex.map(translate_cluster, clusters):
            clusters_hu_by_id[cid] = merged
    clusters_hu = [clusters_hu_by_id[c["id"]] for c in clusters]

    responses_hu = {name: None for name in voice_names}
    if any(responses.values()):
        def translate_response(name):
            r = responses[name]
            if not r:
                return name, None
            obj, _ = step.run(
                f"translate_reciprocity:{name}",
                dict(task="translate_reciprocity", agent="translator",
                     lang="hu", round_n=n,
                     instructions=(
                         "Translate this reciprocity response into "
                         "Hungarian. Keep the cluster id and outcome "
                         "unchanged — translate only the response prose "
                         "(and new_condition, if present). Return ONLY the "
                         "JSON object.\n\nGLOSSARY:\n" + glossary),
                     inputs=json.dumps(r, ensure_ascii=False)),
                validate=lambda o: valid_reciprocity(o, set(cluster_ids)),
                out_path=ddir / "responses_hu" / f"{name}.json",
                postprocess=parse_json_block, loader=read_json,
                writer=lambda p, o: write_json(p, o), max_tokens=2000)
            return name, obj

        with ThreadPoolExecutor(max_workers=4) as ex:
            for name, obj in ex.map(translate_response, voice_names):
                responses_hu[name] = obj

    ledger_hu = LG.render_ledger(n, voices_hu, clusters_hu, grades,
                                 responses_hu, "hu")
    write(rd / "argument_ledger.hu.md", ledger_hu)

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
    return dict(voices=voices, argument_map={"clusters": clusters},
                grades=grades, responses=responses, ledger_en=ledger_en,
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
    step = Step(rd, resume, round_n=n)
    print(f"[round {n:02d}] starting...", flush=True)
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
                f"(source: {K.FACTS[f]['source']})"
                + (f" TRANSFERABILITY: {K.FACTS[f]['transferability_en']}"
                   if "transferability_en" in K.FACTS[f] else "")
                for f in fids]
        return ("\nCURATED SOURCES (registry-backed; cite these with their "
                "evidence grade; anything beyond them must be flagged as "
                "model knowledge; where a TRANSFERABILITY note is given, "
                "state the precondition in your own claim rather than "
                "citing the foreign result as directly applicable):\n"
                + "\n".join(rows))

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
                print(f"[round {n:02d}] {'':>3} {'expert:' + name:<32} "
                     f"{'cached (unchanged spec)':<20}", flush=True)
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

    # 5. briefs (EN by final_brief_writer, HU by translator) — the 10-section
    #    deliberation deliverable (D-30). With the discourse layer on, the
    #    "What to verify with real stakeholders" section carries the
    #    response obligation (D-29, CNDP model): every argument cluster
    #    gets a typed answer.
    brief_instr = (
        "Write the policy brief. It MUST contain exactly these "
        "sections in order: " + ", ".join(f"'{h}'" for h in BRIEF_HEADERS_EN)
        + ". Tag every substantive claim by kind, wherever it appears: "
        "[fact] (evidence-backed — cite the evidence status), [estimate] "
        "(a reasoned but uncertain figure or probability), [assumption] "
        "(an unverified premise the argument needs), or [value] (a value "
        "judgment, not a factual claim — never let one pass as a fact). "
        "'What we know' = the strongest evidence-backed findings. 'What we "
        "consider likely' = weaker or indirect-evidence conclusions. "
        "'Where experts disagree' = the disagreement map's substance, with "
        "reasons, not just labels. 'What we don't know' = the critical "
        "gaps and uncertainties, distinguishing known-unknowns from mere "
        "assumptions. 'What could be done' lists the real alternatives "
        "(including a do-nothing baseline where relevant) and must NOT "
        "crown a single scenario as the answer. 'What each option costs' "
        "states trade-offs, harms, risks and who wins/loses per "
        "alternative — never hide a trade-off behind neutral language. "
        "'What research could resolve' names what new data or study would "
        "most change the decision. 'What people must decide' names the "
        "value choices and political decisions this needs — these are not "
        "failures to resolve, they are the honest answer. Add any section "
        "your ## Directives require.")
    brief_inputs = scen_en_md + "\n\n" + synthesis_text
    if disc:
        brief_instr += (
            f" In '{RESPONSES_HEADER['en']}', answer EVERY argument cluster "
            "from the ledger by id (one bullet per cluster: '- A<i> "
            "(<short restatement>): <type> — <one-line reason>'). <type> "
            "MUST be exactly one of these 7 tokens, unchanged in every "
            "language version (like the A<i> ids): evidence_answerable "
            "(evidence settles or meaningfully refines it), "
            "policy_design_fixable (a design change, guarantee, "
            "compensation or phase-in reduces it), communication_fixable "
            "(already addressed but not visibly or legibly), value_conflict "
            "(legitimate values collide, there is no technical fix), "
            "irreducible_tradeoff (improving one goal necessarily costs "
            "another), needs_more_info (not yet decidable from the "
            "evidence), not_decision_relevant (attention-worthy but would "
            "not change the decision). Do NOT force every cluster into "
            "artificial consensus — value_conflict and irreducible_tradeoff "
            "are legitimate final answers, not failures. An argument "
            "answered by no one is a defect (response obligation). In "
            f"'{BRIEF_HEADERS_EN[9]}', summarise the ledger's Attention "
            "sinks (gumicsontok) section: which debates draw attention "
            "without being decision-relevant, and why — so readers can "
            "tell which arguments move the decision from which mostly "
            "consume attention.")
        brief_inputs += ("\n\n=== ARGUMENT LEDGER (public arguments that "
                         "MUST each be answered) ===\n" + disc["ledger_en"])
    brief_en, _ = step.run(
        "final_brief_writer",
        dict(task="brief", agent="final_brief_writer", lang="en", round_n=n,
             instructions=brief_instr, inputs=brief_inputs),
        validate=lambda t: (all(h in t for h in BRIEF_HEADERS_EN)
                            and (not disc or (responds_to_clusters(
                                t, "en", disc["cluster_ids"])
                                and response_types_valid(
                                    t, disc["cluster_ids"])))),
        # D-30 asks for 10 sections + a typed response per argument cluster
        # in one shot — a materially bigger deliverable than the pre-D-30
        # 5-section brief, hence the higher budget than the old 6000.
        out_path=rd / "brief.en.md", max_tokens=12000)

    brief_hu_instr = (
        "Translate this policy brief into Hungarian. Use EXACTLY "
        "these section headers in place of the English ones: "
        + ", ".join(f"'{h}'" for h in BRIEF_HEADERS_HU)
        + ". Keep bullet counts identical. Use the glossary strictly. Keep "
        f"every claim-kind tag ({', '.join(CLAIM_TAGS)}) unchanged, in "
        "English, exactly like the A<i> ids — translate only the "
        "surrounding prose.")
    if disc:
        brief_hu_instr += (f" Translate '{RESPONSES_HEADER['en']}' as "
                           f"'{RESPONSES_HEADER['hu']}'; keep every A<i> id "
                           "AND every response-type token (evidence_"
                           "answerable / policy_design_fixable / "
                           "communication_fixable / value_conflict / "
                           "irreducible_tradeoff / needs_more_info / "
                           "not_decision_relevant) unchanged — translate "
                           "only the restatement and reason around them.")
    brief_hu, _ = step.run(
        "translator_brief",
        dict(task="brief", agent="translator", lang="hu", round_n=n,
             instructions=brief_hu_instr + "\n\nGLOSSARY:\n" + glossary,
             inputs=brief_en),
        validate=lambda t: (all(h in t for h in BRIEF_HEADERS_HU)
                            and t.strip() != brief_en.strip()
                            and (not disc or (responds_to_clusters(
                                t, "hu", disc["cluster_ids"])
                                and response_types_valid(
                                    t, disc["cluster_ids"])))),
        out_path=rd / "brief.hu.md", max_tokens=12000)

    # 6. critics (parallel) + translation checker
    registry_digest = "\n".join(
        f"- {fid} [{f['evidence']}]: {f['en'][:120]}... (source: {f['source']})"
        + (f" | transferability: {f['transferability_en']}"
           if "transferability_en" in f else "")
        for fid, f in K.FACTS.items())

    def run_critic(name):
        extra = ""
        if name == "evidence_checker":
            extra = ("\nCURATED SOURCE REGISTRY (the only registry-backed "
                     "facts; a claim tagged stronger than its registry grade, "
                     "or citing a source not listed here without flagging it "
                     "as model knowledge, is a defect):\n" + registry_digest)
        elif name == "context_transferability_checker":
            extra = ("\nCURATED SOURCE REGISTRY (facts with a "
                     "'transferability' note are drawn from outside Hungary; "
                     "a scenario citing one of these without engaging its "
                     "named precondition is a defect):\n" + registry_digest)
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
        "tokens": llm.token_stats(),
        "errors": llm.error_stats(),
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
