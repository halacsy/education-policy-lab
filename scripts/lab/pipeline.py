"""Round runner: experts → scenarios → synthesis → discourse → brief →
critics → meta-critic. Every artifact is bilingual, schema-constrained JSON
(D-34): model calls go through lab.llm.call_structured, validators check
the parsed object, and lab/render.py produces every .md view
deterministically — there are no translation steps and no mock fallback
(a step that cannot be served raises llm.StepFailed and the round stops).

Interrupted rounds RESUME: if the round folder's system_state snapshot still
matches the live system, existing valid artifacts are reused and their
backend provenance is recovered from steps.jsonl (quota conservation; the
snapshot gate guarantees they were produced by the identical system)."""
import hashlib
import json
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

from . import agent_defs as D
from . import improve
from . import ledger as LG
from . import llm, render, topic, translation
from . import schemas as S
from .agents import build_prompt
from .util import (AGENTS_DIR, CONFIG_PATH, TEMPLATES_DIR, load_config,
                   read, read_json, round_dir, write, write_json)

FIELD_KEYS = translation.FIELD_KEYS


class FramesPending(RuntimeError):
    """Round 1 proposed the topic's scenario frames from the expert record
    and stopped at the human gate (issue #21, D-36): a human must approve
    (or edit) the proposal before any scenario-dependent step runs. The
    relaunch resumes the round — the expert outputs are reused."""


MAX_FRAMES = 5
MIN_FRAMES = 2

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

RELEVANCE_LEVELS = ("high", "medium", "low")
ATTENTION_KEYS = ("high_attention", "new_information", "changes_evaluation",
                  "already_answered", "primarily_rhetorical")

# Argument-map generation stays split into two phases (D-30 lesson: the
# 8-field per-cluster decomposition made one giant one-shot call too
# failure-prone — a bad cluster must degrade alone, live clustering must
# never be thrown away). Phase 1 clusters cheaply; phase 2 decomposes EACH
# cluster in its own small, parallel, independently-resumable call.
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

def pair_ok(v):
    """A bilingual {en, hu} leaf with both sides non-empty."""
    return (isinstance(v, dict)
            and str(v.get("en", "")).strip() != ""
            and str(v.get("hu", "")).strip() != "")


def valid_expert(o):
    try:
        findings = o["findings"]
    except (TypeError, KeyError):
        return False
    if not isinstance(findings, list) or not findings:
        return False
    for f in findings:
        if not pair_ok(f.get("claim")) or not str(f.get("source", "")).strip():
            return False
    if not pair_ok(o.get("interpretation")) or not pair_ok(o.get("position")):
        return False
    assumptions = o.get("assumptions")
    if not assumptions or not all(pair_ok(a) for a in assumptions):
        return False
    uncertainties = o.get("uncertainties")
    if not uncertainties:
        return False
    return all(pair_ok(u.get("text")) and pair_ok(u.get("reduced_by"))
               for u in uncertainties)


def valid_frames(o):
    """Emergent-framing proposal (issue #21): 2-5 frames with sequential
    S<i> ids, bilingual title+scope, and at least one rejected framing
    (the audit trail of the option-space choice)."""
    try:
        frames = o["frames"]
    except (TypeError, KeyError):
        return False
    if not isinstance(frames, list) or \
            not MIN_FRAMES <= len(frames) <= MAX_FRAMES:
        return False
    if [f.get("id") for f in frames] != \
            [f"S{i + 1}" for i in range(len(frames))]:
        return False
    if not all(pair_ok(f.get("title")) and pair_ok(f.get("scope"))
               for f in frames):
        return False
    rejected = o.get("rejected_framings")
    if not rejected:
        return False
    return all(pair_ok(r.get("framing")) and pair_ok(r.get("reason"))
               for r in rejected)


def valid_voice(obj, id_set):
    try:
        rs = obj["reactions"]
    except (TypeError, KeyError):
        return False
    if not isinstance(rs, list) or \
            {r.get("scenario") for r in rs} != id_set or \
            len(rs) != len(id_set):
        return False  # exactly ONE reaction per scenario (duplicates corrupt
        # the ledger's per-scenario rendering)
    for r in rs:
        if r.get("stance") not in STANCES:
            return False
        if r.get("label") not in POSITION_LABELS:
            return False
        if (r["stance"] == "no_position") != (r["label"] == "no_position"):
            return False
        arg = r.get("argument")
        if not pair_ok(arg) or len(arg["en"].strip()) < 10:
            return False
        # a voice with no position has no framing to sell: interest and
        # public_good_frame are only meaningful with a stated stance
        if r["stance"] != "no_position" and (
                not pair_ok(r.get("interest"))
                or not pair_ok(r.get("public_good_frame"))):
            return False
        if r["label"] == "documented" and not str(r.get("source", "")).strip():
            return False
        if r["label"] == "value_modeled" and not str(r.get("basis", "")).strip():
            return False
        if r["stance"] != "no_position" and \
                not pair_ok(r.get("condition_to_change")):
            return False
    return True


def valid_argmap_basic(obj, voice_names, id_set):
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
        if c.get("scenario") not in id_set:
            return False
        if c.get("kind") not in ("fact", "value", "mixed"):
            return False
        if c.get("side") not in ("pro", "con", "conditional"):
            return False
        rb = c.get("raised_by")
        if not rb or not set(rb) <= set(voice_names):
            return False
        if not pair_ok(c.get("claim")):
            return False
    return True


def valid_cluster_decomposition(d):
    """Phase 2 (per-cluster decomposition — one cluster's extra fields)."""
    if not isinstance(d, dict):
        return False
    for field in ("interest", "value", "fear", "assumption",
                  "empirical_uncertainty"):
        if not pair_ok(d.get(field)):
            return False
    affected = d.get("affected")
    if not affected or not all(pair_ok(a) for a in affected):
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
               and pair_ok(r.get("response"))
               and len(r["response"]["en"].strip()) >= 10
               and r.get("outcome") in ("maintain", "revise") for r in rs)


def valid_grades(o, factual_ids):
    """Evidence-layer grading: 90% coverage of the fact/mixed clusters
    (a judge that skips one cluster of thirty must not fail the step)."""
    try:
        gs = o["grades"]
    except (TypeError, KeyError):
        return False
    if not isinstance(gs, list):
        return False
    ids = {g.get("cluster_id") for g in gs}
    covered = sum(1 for cid in factual_ids if cid in ids)
    return covered >= max(1, int(0.9 * len(factual_ids)))


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


def valid_meta(o):
    try:
        g = o["gaming_judgment"]
    except (TypeError, KeyError):
        return False
    if g.get("verdict") not in ("GENUINE", "RUBRIC-GAMING", "NO_BASELINE"):
        return False
    if not g.get("reasons") or not all(str(x).strip() for x in g["reasons"]):
        return False
    for key in ("agent_performance", "workflow", "critique_quality",
                "translation_consistency"):
        items = o.get(key)
        if not items or not all(str(x).strip() for x in items):
            return False
    return True  # removal_candidates may legitimately be empty


def valid_brief(o, id_set, cluster_ids=None):
    """Bilingual 10-section brief (D-30/D-34). With a live argument map the
    response obligation is checked on the JSON fields directly (same
    coverage threshold as the old text check: a ledger whose id set differs
    slightly must not deadlock the round)."""
    try:
        if not pair_ok(o["intro"]):
            return False
    except (TypeError, KeyError):
        return False
    if {k.get("id") for k in o.get("scenario_key", [])} != id_set:
        return False
    for key in ("what_we_know", "what_we_consider_likely",
                "what_we_dont_know", "what_each_option_costs"):
        items = o.get(key)
        if not items or not all(pair_ok(i.get("text")) for i in items):
            return False
    dis = o.get("where_experts_disagree")
    if not dis:
        return False
    for d in dis:
        if not pair_ok(d.get("topic")):
            return False
        ps = d.get("positions")
        if not ps or not all(p.get("holders") and pair_ok(p.get("position"))
                             and pair_ok(p.get("why")) for p in ps):
            return False
    could = o.get("what_could_be_done")
    if not could or {c.get("scenario_id") for c in could} != id_set:
        return False
    if not all(pair_ok(c.get("title")) and pair_ok(c.get("summary"))
               for c in could):
        return False
    for key in ("what_research_could_resolve", "what_people_must_decide"):
        items = o.get(key)
        if not items or not all(pair_ok(i) for i in items):
            return False
    minority = o.get("minority_positions")
    if not minority or not all(m.get("holders") and pair_ok(m.get("position"))
                               and pair_ok(m.get("rationale"))
                               for m in minority):
        return False
    if not all(pair_ok(a.get("text")) for a in o.get("attention_sinks", [])):
        return False
    responses = o.get("stakeholder_responses", [])
    if not all(pair_ok(r.get("restatement")) and pair_ok(r.get("reason"))
               for r in responses):
        return False
    if cluster_ids:
        answered = {r.get("cluster_id") for r in responses}
        hits = sum(1 for cid in cluster_ids if cid in answered)
        if hits < max(6, int(0.8 * len(cluster_ids))):
            return False
    return True


def valid_synthesis(o):
    try:
        dis = o["disagreements"]
    except (TypeError, KeyError):
        return False
    if not pair_ok(o.get("overview")):
        return False
    if not isinstance(dis, list) or len(dis) < 2:
        return False
    minority_seen = False
    for d in dis:
        if not pair_ok(d.get("topic")):
            return False
        sides = d.get("sides")
        if not sides or len(sides) < 2:
            return False
        for side in sides:
            if not side.get("holders") or not pair_ok(side.get("position")) \
                    or not pair_ok(side.get("rationale")):
                return False
            minority_seen = minority_seen or bool(side.get("minority"))
    agreements = o.get("agreements")
    if not agreements or not all(pair_ok(a.get("text")) for a in agreements):
        return False
    return minority_seen  # a map with no minority side is consensus laundering


def valid_rejected(o, id_set):
    try:
        sc = o["scenarios"]
    except (TypeError, KeyError):
        return False
    if not isinstance(sc, list) or {s.get("id") for s in sc} != id_set:
        return False
    return all(str(s.get("chosen", "")).strip() and s.get("rejected")
               and all(str(r.get("framing", "")).strip()
                       and str(r.get("reason", "")).strip()
                       for r in s["rejected"])
               for s in sc)


def valid_critic(o):
    try:
        obs = o["objections"]
    except (TypeError, KeyError):
        return False
    if not isinstance(obs, list) or len(obs) < 2:
        return False
    return all(len(str(ob.get("objection", "")).strip()) >= 10
               and str(ob.get("suggested_revision", "")).strip()
               for ob in obs)


def valid_scenarios_bi(o, id_set):
    """Bilingual scenarios (D-34): exactly the topic's frozen frame ids,
    every prose leaf a non-empty {en, hu} pair, every structured sub-field
    present."""
    try:
        sc = o["scenarios"]
    except (TypeError, KeyError):
        return False
    if not isinstance(sc, list) or len(sc) != len(id_set) or \
            {s.get("id") for s in sc} != id_set:
        return False
    for s in sc:
        if not all(pair_ok(s.get(k)) for k in ("title", "goal", "equity_impact")):
            return False
        es = s.get("evidence_status")
        if not isinstance(es, dict) or not pair_ok(es.get("note")):
            return False
        for key in ("mechanism", "expected_benefits"):
            items = s.get(key)
            if not items or not all(pair_ok(i.get("text")) for i in items):
                return False
        for key in ("assumptions", "cost_categories", "political_risks"):
            items = s.get(key)
            if not items or not all(pair_ok(i) for i in items):
                return False
        steps = s.get("implementation_steps")
        if not steps or not all(pair_ok(st.get("actor")) and pair_ok(st.get("action"))
                                and pair_ok(st.get("timeline")) for st in steps):
            return False
        us = s.get("uncertainties")
        if not us or not all(pair_ok(u.get("text")) and pair_ok(u.get("reduced_by"))
                             for u in us):
            return False
    return True


def _hash_md_tree(h, base, root):
    for p in sorted(root.rglob("*.md")) if root.exists() else []:
        h.update(str(p.relative_to(base)).encode())
        h.update(p.read_bytes())


def _current_state_hash():
    """Effective system state: shared agent specs + THIS topic's overlay
    (memory + directives) + config + rubric + the topic's problem brief.
    The topic fingerprint deliberately excludes the frames — see
    Topic.state_fingerprint (frame approval must not invalidate the expert
    outputs it was derived from)."""
    T = topic.current()
    h = hashlib.sha256()
    _hash_md_tree(h, AGENTS_DIR, AGENTS_DIR)
    _hash_md_tree(h, T.memory_dir, T.memory_dir)
    _hash_md_tree(h, T.directives_dir, T.directives_dir)
    h.update(CONFIG_PATH.read_bytes())
    h.update((TEMPLATES_DIR / "evaluation_rubric.md").read_bytes())
    h.update(T.state_fingerprint())
    return h.hexdigest()


def _snapshot_state_hash(rd):
    base = rd / "system_state"
    if not ((base / "agents").exists() and (base / "system_config.json").exists()
            and (base / "evaluation_rubric.md").exists()
            and (base / "topic.json").exists()):
        return None
    h = hashlib.sha256()
    agents_base = base / "agents"
    # shared specs (the overlay dirs are hashed separately, exactly like
    # the live side hashes AGENTS_DIR without them)
    for p in sorted(agents_base.rglob("*.md")):
        rel = p.relative_to(agents_base)
        if rel.parts[0] in ("memory", "directives"):
            continue
        h.update(str(rel).encode())
        h.update(p.read_bytes())
    _hash_md_tree(h, agents_base / "memory", agents_base / "memory")
    _hash_md_tree(h, agents_base / "directives", agents_base / "directives")
    h.update((base / "system_config.json").read_bytes())
    h.update((base / "evaluation_rubric.md").read_bytes())
    snap_cfg = json.loads((base / "topic.json").read_text(encoding="utf-8"))
    # MUST mirror Topic.state_fingerprint's exclusions (frames, evaluation)
    # — this inline copy diverging from it caused a full re-run (2026-07-17)
    snap_cfg = {k: v for k, v in snap_cfg.items()
                if k not in ("frames", "evaluation")}
    h.update(json.dumps(snap_cfg, ensure_ascii=False,
                        sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def _print_state_diff(snap, T):
    """List files that differ between the stored snapshot and the live
    state-hash inputs (#27 diagnosability)."""
    pairs = [(snap / "agents", AGENTS_DIR, ("memory", "directives")),
             (snap / "agents" / "memory", T.memory_dir, ()),
             (snap / "agents" / "directives", T.directives_dir, ())]
    diffs = []
    for a, b, skip in pairs:
        names = set()
        for base in (a, b):
            if base.exists():
                names |= {p.relative_to(base) for p in base.rglob("*.md")
                          if not skip or p.relative_to(base).parts[0] not in skip}
        for rel in sorted(names):
            fa, fb = a / rel, b / rel
            if not fa.exists():
                diffs.append(f"NEW: {fb}")
            elif not fb.exists():
                diffs.append(f"REMOVED: {fb}")
            elif fa.read_bytes() != fb.read_bytes():
                diffs.append(f"CHANGED: {fb}")
    for label, fa, fb in (("config", snap / "system_config.json", CONFIG_PATH),
                          ("rubric", snap / "evaluation_rubric.md",
                           TEMPLATES_DIR / "evaluation_rubric.md"),
                          ("topic.json", snap / "topic.json", T.path)):
        if fa.exists() and fb.exists() and fa.read_bytes() != fb.read_bytes():
            diffs.append(f"CHANGED: {label}")
    print("[resume invalidated] diverging state inputs:", flush=True)
    for d in diffs or ["(no md/config diff found — check topic fingerprint)"]:
        print(f"  {d}", flush=True)


def snapshot_system_state(rd):
    """Snapshot everything the round's behaviour depends on. Layout matches
    the pre-D-35 one (memory under system_state/agents/memory — verify
    check M globs it there), with the per-topic overlay and topic.json
    added."""
    T = topic.current()
    dest = rd / "system_state"
    if dest.exists():
        # Preserve the superseded snapshot (issue #27): when a relaunch
        # does NOT resume, the previous snapshot is the only evidence of
        # WHAT changed — overwriting it made every invalidation
        # undiagnosable after the fact.
        prev = rd / "system_state_prev"
        if prev.exists():
            shutil.rmtree(prev)
        dest.rename(prev)
    dest.mkdir(parents=True)
    shutil.copytree(AGENTS_DIR, dest / "agents")
    if T.memory_dir.exists():
        shutil.copytree(T.memory_dir, dest / "agents" / "memory")
    if T.directives_dir.exists():
        shutil.copytree(T.directives_dir, dest / "agents" / "directives")
    shutil.copy(T.path, dest / "topic.json")
    shutil.copy(CONFIG_PATH, dest / "system_config.json")
    shutil.copy(TEMPLATES_DIR / "evaluation_rubric.md", dest / "evaluation_rubric.md")


class Step:
    """One generation step with validation, one corrective retry,
    resume-from-disk, and a step journal. No mock fallback (D-34):
    a step that cannot be served or validated raises llm.StepFailed —
    the journal records it and a relaunch resumes from this step."""

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

    def _reject(self, name, attempt, backend, output, reason):
        """rejections.jsonl: the full rejected output + why (audit trail;
        input for agent improvement — see issue on rejection-driven
        directives). Kept out of steps.jsonl so the step journal stays a
        cheap resume index."""
        entry = {
            "step": name, "attempt": attempt, "backend": backend,
            "reason": reason,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "output": output if isinstance(output, str)
            else json.dumps(output, ensure_ascii=False),
        }
        with open(self.rd / "rejections.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

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
            loader=None, writer=None, schema=None, web_search=False):
        """With schema= (D-34): the call goes through llm.call_structured,
        the result is the parsed (schema-valid) dict, and JSON IO is the
        default. Everything else — validation, corrective retry with D-26
        escalation, resume, journal — is identical to the text path."""
        if schema is not None:
            loader = loader or read_json
            writer = writer or write_json
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
        backend = "?"
        for attempt in (0, 1):
            kw = dict(prompt_kwargs)
            if corrective:
                kw["instructions"] = kw.get("instructions", "") + "\n" + corrective
            prompt = build_prompt(**kw)
            # a validation-failure retry escalates one rung on the model
            # ladder (D-26): cheap model produced unusable output
            try:
                if schema is not None:
                    result = llm.call_structured(prompt, schema, role,
                                                 max_tokens=max_tokens,
                                                 escalation=attempt)
                else:
                    text = llm.call_model(prompt, role, max_tokens=max_tokens,
                                          escalation=attempt,
                                          web_search=web_search)
            except llm.StepFailed:
                self._note(name, "FAILED")
                raise
            backend = llm.CALL_LOG[-1]["backend"]
            if schema is None:
                result = text
            reason = None
            try:
                if schema is None:
                    result = postprocess(text)
                if validate(result):
                    if out_path is not None:
                        writer(out_path, result)
                    self._note(name, backend)
                    return result, backend
                reason = "validator returned False"
            except Exception as e:  # noqa: BLE001 — the reason IS the log
                reason = f"{type(e).__name__}: {e}"
            # Audit trail (owner direction 2026-07-16): every rejected
            # output is persisted WITH its reason — agent improvement needs
            # to see what was refused and why, not just that a retry ran.
            self._reject(name, attempt, backend, result, reason)
            corrective = (
                "PREVIOUS ATTEMPT FAILED CONTENT VALIDATION. Fill EVERY "
                "field of the required schema with substantive content (no "
                "empty or placeholder values), cover every required item, "
                "and follow the task rules exactly."
                if schema is not None else
                "PREVIOUS ATTEMPT FAILED FORMAT VALIDATION. Follow "
                "the output format EXACTLY as specified, with no "
                "surrounding commentary.")
        # No mock fallback (D-34): journal the failure and stop the round;
        # a relaunch resumes from this step via the state-hash gate.
        self._note(name, "FAILED")
        raise llm.StepFailed(
            f"step {name!r} failed format validation after 2 attempts "
            f"(backend {backend})")


def run_discourse(step, rd, n, scen_en_md, glossary, disc_cfg, T, facts):
    """Societal-discourse layer (D-29, structured+bilingual since D-34):
    voices react to the scenarios, the mediator builds the argument map,
    the evidence layer grades factual claims, an optional reciprocity pass
    makes the voices answer their strongest counter-argument. Every
    artifact is bilingual JSON; BOTH ledgers are rendered deterministically
    from the same data (render.project) — no translation steps at all."""
    voice_names = T.voices
    ids = tuple(T.scenario_ids)
    id_set = set(ids)
    ids_line = "SCENARIO IDS: " + ", ".join(ids)
    ddir = rd / "discourse"
    bilingual_note = (
        "Write every {en, hu} pair as the SAME statement authored natively "
        "in both languages (use the glossary terms strictly; never "
        "machine-translation flavour).\n\nGLOSSARY:\n" + glossary)

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
                     "the required JSON object. Rules: one reaction per "
                     f"scenario ({ids_line}); a stance without "
                     "justification is invalid; no_position is the honest "
                     "choice when your interest implies nothing; NEVER "
                     "attribute an unsourced position to a real "
                     "organisation — use value_modeled with its basis. "
                     "Keep every free-text field to at most 2 "
                     "sentences per language — density beats volume, "
                     "length is not rewarded. "
                     + bilingual_note),
                 inputs=scen_en_md),
            validate=lambda o: valid_voice(o, id_set),
            out_path=ddir / "voices" / f"{name}.json",
            # sourced scenarios lengthen voice reactions (round-2 truncation,
            # #29: rural-school-closures round_03 digitalisgazdasagi hit the
            # 40000 cap under the 5-frame scenario set — raised, infra fix,
            # not part of the panel-expansion experiment's documented change)
            schema=S.VOICE(ids), max_tokens=56000)
        return name, obj

    voices = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, obj in ex.map(run_voice, voice_names):
            voices[name] = obj

    voices_digest = json.dumps(
        {k: render.project(v["reactions"], "en") for k, v in voices.items()},
        ensure_ascii=False)

    # Phase 1: cluster only (small schema — the same shape as pre-D-30).
    arg_map_basic, _ = step.run(
        "argument_map",
        dict(task="argument_map", agent="discourse_mediator", round_n=n,
             instructions=(
                 "Cluster the voices' arguments into an argument map as the "
                 "required JSON object. Rules: stable sequential ids "
                 "A1..An; aim for 8-16 clusters — MERGE near-duplicate "
                 "arguments across voices and scenarios into one canonical "
                 "claim instead of enumerating variants; every claim in "
                 "canonical one-sentence form; classify fact vs value vs "
                 "mixed; raised_by lists ONLY voice names that actually "
                 "raise it; NEVER drop a minority argument; do not count "
                 "heads. " + ids_line + ". " + bilingual_note),
             inputs=voices_digest),
        validate=lambda o: valid_argmap_basic(o, voice_names, id_set),
        out_path=ddir / "argument_map_basic.json",
        schema=S.CLUSTER_BASIC(ids), max_tokens=24000)
    clusters_basic = arg_map_basic["clusters"]

    # Phase 2: decompose EACH cluster in its own small, parallel,
    # independently-resumable call (a bad cluster degrades alone; the live
    # clustering is never thrown away).
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
                    f"{r['argument']['en']} Condition: "
                    f"{r['condition_to_change']['en']}")
        obj, _ = step.run(
            f"decompose:{cid}",
            dict(task="argument_decompose", agent="discourse_mediator",
                 round_n=n,
                 instructions=(
                     f"For argument cluster {cid} (scenario "
                     f"{c['scenario']}, {c['kind']}/{c['side']}): "
                     f"\"{c['claim']['en']}\"\ndecompose it for the "
                     "stakeholder stress test digest, and screen it for "
                     "'gumicsont' status (a debate that draws a lot of "
                     "attention but would not change the decision if "
                     "resolved: high attention + low decision_relevance is "
                     "exactly what real participants need flagged, not "
                     "hidden).\n" + CLUSTER_DECOMPOSE_FIELD_GUIDE +
                     "\nReturn the required JSON object. " + bilingual_note),
                 inputs=("ORIGINAL VOICE ARGUMENTS RAISING THIS CLUSTER:\n"
                        + "\n".join(context_lines))),
            validate=valid_cluster_decomposition,
            out_path=ddir / "clusters" / f"{cid}.json",
            schema=S.CLUSTER_DECOMPOSE, max_tokens=8000)
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
        for fid, f in facts.items()) or \
        "(no registry-backed facts admitted for this topic yet)"
    grades_obj, _ = step.run(
        "grade_arguments",
        dict(task="grade_arguments", agent="evidence_checker", round_n=n,
             instructions=(
                 "Grade the FACTUAL claim of every fact/mixed argument "
                 "cluster below against the curated registry, as the "
                 "required JSON object (one entry per fact/mixed cluster). "
                 f"You MUST return one grade for EACH of these cluster ids "
                 f"— ALL of them, no sampling: {', '.join(factual)}. "
                 f"That is {len(factual)} entries. "
                 "status = the registry-backed evidence grade with its "
                 "registry source, or not_registry_backed (treat as model "
                 "knowledge) when no registry fact supports it. Value "
                 "claims are NOT graded — omit them.\n\nREGISTRY:\n"
                 + registry_digest),
             inputs=json.dumps(render.project(clusters, "en"),
                               ensure_ascii=False)),
        validate=lambda o: valid_grades(o, factual),
        out_path=ddir / "argument_grades.json",
        schema=S.GRADES, role="judge", max_tokens=16000)
    grades = render.grades_dict(grades_obj)

    responses = {name: None for name in voice_names}
    if disc_cfg.get("reciprocity", True):
        clusters_digest = json.dumps(render.project(clusters, "en"),
                                     ensure_ascii=False)

        def run_response(name):
            obj, _ = step.run(
                f"response:{name}",
                dict(task="discourse_reciprocity", agent=name, round_n=n,
                     instructions=(
                         "Reciprocity pass (DQI): from the argument map "
                         "below, pick the strongest argument AGAINST your "
                         "stated positions — AT MOST THREE clusters, the "
                         "ones that hit your position hardest — and answer "
                         "them as the required JSON object. Answering means "
                         "engaging the argument on its merits, not "
                         "repeating yourself; depth on the strongest "
                         "counter-argument beats coverage. Keep "
                         "every free-text field to at most 3 "
                         "sentences per language — density beats "
                         "volume. "
                         + bilingual_note),
                     inputs=("YOUR REACTIONS:\n"
                             + json.dumps(render.project(
                                   voices[name]["reactions"], "en"),
                                   ensure_ascii=False)
                             + "\n\nARGUMENT MAP:\n" + clusters_digest)),
                validate=lambda o: valid_reciprocity(o, set(cluster_ids)),
                out_path=ddir / "responses" / f"{name}.json",
                schema=S.RECIPROCITY, max_tokens=32000)
            return name, obj

        with ThreadPoolExecutor(max_workers=4) as ex:
            for name, obj in ex.map(run_response, voice_names):
                responses[name] = obj

    # BOTH ledgers render deterministically from the same bilingual data —
    # the D-34 replacement for the deleted translate_voice /
    # translate_cluster / translate_reciprocity steps (17 fallbacks in
    # round 7 were ALL translation steps).
    ledger_en = LG.render_ledger(
        n, render.project(voices, "en"), render.project(clusters, "en"),
        grades, render.project(responses, "en"), "en")
    write(rd / "argument_ledger.en.md", ledger_en)
    ledger_hu = LG.render_ledger(
        n, render.project(voices, "hu"), render.project(clusters, "hu"),
        grades, render.project(responses, "hu"), "hu")
    write(rd / "argument_ledger.hu.md", ledger_hu)

    stances = [r["stance"] for v in voices.values() for r in v["reactions"]]
    labels = [r["label"] for v in voices.values() for r in v["reactions"]]
    conditions = [f"{name} ({r['scenario']}): {r['condition_to_change']['en']}"
                  for name, v in voices.items() for r in v["reactions"]
                  if r["stance"] != "no_position"
                  and pair_ok(r.get("condition_to_change"))]
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


def propose_frames(step, rd, n, T, question, expert_digest, glossary):
    """Emergent framing (issue #21, D-36): derive the option space (2-5
    solution frames) from THIS round's expert record as a human-gated
    proposal (D-24 pattern). The proposal is a round artifact (resumable)
    AND a file pair under topics/<slug>/proposals/ for the human to review,
    edit and approve.

    Gate feedback (new_topic.py reframe): if the owner rejected an earlier
    proposal with feedback, the entries are appended to the instructions
    and the derivation re-runs on the SAME expert record — frames stay
    emergent, never hand-written."""
    feedback_path = T.proposals_dir / "frames-feedback.md"
    feedback = ""
    if feedback_path.exists():
        feedback = (
            "\n\nHUMAN GATE FEEDBACK — the topic owner reviewed an earlier "
            "frames proposal and sent it back. Each entry below points at "
            "where the derived option space fell short. Address the "
            "feedback, but every frame must still be grounded in the "
            "expert record given as input — if the record does not support "
            "a requested frame, record it under rejected framings with "
            "that reason instead of inventing it:\n\n"
            + read(feedback_path))
    obj, _ = step.run(
        "frame_scenarios",
        dict(task="frame_scenarios", agent="scenario_builder", round_n=n,
             instructions=(
                 f"{question}\n"
                 "FRAMING STEP: from the expert record below, derive the "
                 "OPTION SPACE of this problem: 2-5 solution frames "
                 "(families of interventions worth developing into full "
                 "scenarios). Return the required JSON object. Rules: "
                 "sequential ids S1, S2, ...; each frame carries a short "
                 "bilingual title and a one-sentence bilingual scope; the "
                 "frames together must span the REAL option space the "
                 "expert record describes (including a low-intervention or "
                 "compensatory frame when the record supports one) — never "
                 "converge on a single answer; record every considered-but-"
                 "rejected framing with its reason (this is the audit "
                 "trail of the option-space choice). Write every {en, hu} "
                 "pair as the SAME statement authored natively in both "
                 "languages.\n\nGLOSSARY:\n" + glossary + feedback),
             inputs=expert_digest),
        validate=valid_frames, out_path=rd / "frames_proposal.json",
        schema=S.FRAMES, max_tokens=8000)
    write_json(T.proposals_dir / "frames.json",
               {"topic": T.slug, "derived_from_round": n,
                "status": "proposed", **obj})
    write(T.proposals_dir / "frames.md", render.frames_md(obj, T, n))
    return obj


def run_round(n):
    """Generate all round-n artifacts (steps 1-6 of the workflow). Evaluation,
    meta-critique and improvement planning are orchestrated by the loop."""
    cfg = load_config()
    T = topic.current()
    rd = round_dir(n, create=True)
    state_hash = _current_state_hash()
    resume = _snapshot_state_hash(rd) == state_hash
    if not resume and (rd / "system_state").exists():
        # name the diverging files BEFORE the snapshot is replaced (#27) —
        # an invalidated resume re-runs the whole round, so the cause must
        # be visible, not inferred
        _print_state_diff(rd / "system_state", topic.current())
    if not resume and (rd / "steps.jsonl").exists():
        (rd / "steps.jsonl").unlink()  # stale partial attempt
    snapshot_system_state(rd)
    # round_meta.json (owner direction 2026-07-16: log when and under what
    # conditions every round leg started, per topic). Each (re)launch
    # APPENDS a start record, so interrupted/resumed rounds keep their full
    # launch history. The WHY of the round (the applied improvement plan)
    # is recorded by the loop in the round commit and prev round's
    # plan.json; providers recorded here are what verify check 13 should
    # eventually validate against (issue #24).
    meta_path = rd / "round_meta.json"
    meta = read_json(meta_path) if meta_path.exists() else {
        "topic": T.slug, "round": n, "starts": []}
    meta["starts"].append({
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "resume": resume,
        "generator_provider": llm.provider_for_role("generator"),
        "judge_provider": llm.provider_for_role("judge"),
        "fresh_experts": bool(os.environ.get("LAB_FRESH_EXPERTS")),
        "state_hash": state_hash,
    })
    write_json(meta_path, meta)
    step = Step(rd, resume, round_n=n)
    print(f"[round {n:02d}] starting... (topic: {T.slug})", flush=True)
    question = T.question_block()
    facts = T.registry_facts()

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
        out_prev = prev_rd / "expert_outputs" / f"{name}.json"
        spec_now = AGENTS_DIR / "experts" / f"{name}.md"
        if not (spec_prev.exists() and out_prev.exists()):
            return None
        if spec_prev.read_text(encoding="utf-8") != spec_now.read_text(encoding="utf-8"):
            return None
        # episodic memory is part of the effective prompt: changed memory
        # means the expert must actually re-run (issue #1)
        mem_prev = prev_rd / "system_state" / "agents" / "memory" / f"{name}.md"
        mem_now = T.memory_dir / f"{name}.md"
        prev_mem = mem_prev.read_text(encoding="utf-8") if mem_prev.exists() else ""
        now_mem = mem_now.read_text(encoding="utf-8") if mem_now.exists() else ""
        if prev_mem != now_mem:
            return None
        try:
            return read_json(out_prev)  # pre-D-34 rounds stored .md: no reuse
        except Exception:
            return None

    def curated_sources(name):
        fids = [f for f in T.expert_facts(name) if f in facts]
        if not fids:
            return ""
        rows = [f"- [{facts[f]['evidence']}] {facts[f]['en']} "
                f"(source: {facts[f]['source']})" for f in fids]
        return ("\nCURATED SOURCES (registry-backed; cite these with their "
                "evidence grade; anything beyond them must be flagged as "
                "model knowledge):\n" + "\n".join(rows))

    glossary = T.glossary()
    # P4 (D-34, issue #6 first half): optional live-retrieval phase before
    # the structured expert call. Web findings are CITED SOURCES in the
    # expert output only — they NEVER enter the curated registry (knowledge
    # admission stays human-gated, D-24).
    web_search_on = bool(cfg.get("research", {}).get("web_search")) \
        and llm.web_search_supported("generator")

    def run_expert(name):
        out_path = rd / "expert_outputs" / f"{name}.json"
        validate = directive_validator(
            valid_expert, dict(task="expert_analysis", agent=name))
        obj = None
        # LAB_FRESH_EXPERTS=1 disables the cross-round expert cache so every
        # seat re-runs its research (live web search) + analysis. Use it when
        # the cached outputs are valid by spec but stale by sourcing — e.g.
        # the previous round's search phase was down (issue #23) and the
        # point of the new round is fresh evidence. Intra-round resume
        # (step.resume) is unaffected: an interrupted round still reuses its
        # own artifacts.
        fresh = bool(os.environ.get("LAB_FRESH_EXPERTS"))
        if not (step.resume and out_path.exists()) and not fresh:
            cached = reusable_expert(name)
            try:
                cached_ok = cached is not None and validate(cached)
            except Exception:
                cached_ok = False
            if cached_ok:
                write_json(out_path, cached)
                reused_prev.append(f"expert:{name}")
                print(f"[round {n:02d}] {'':>3} {'expert:' + name:<32} "
                     f"{'cached (unchanged spec)':<20}", flush=True)
                obj = cached
        research_notes = ""
        if obj is None and web_search_on:
            # two-phase call: the server-side web-search tool and structured
            # output are not combined in one request — a free research call
            # produces cited notes, the structured call consumes them
            research_text, _ = step.run(
                f"research:{name}",
                dict(task="expert_research", agent=name, round_n=n,
                     instructions=(
                         f"Policy question: {question}\n"
                         "RESEARCH PHASE (web search enabled): search the "
                         "web for the most current, load-bearing evidence "
                         "in YOUR domain (fresh statistics, new studies, "
                         "recent policy changes). For every finding note "
                         "the claim, the number/year, and the exact source "
                         "(title + URL) — the FULL URL after each finding. "
                         "5-10 findings as prose notes — a "
                         "later call turns them into your structured "
                         "analysis. Your spec's ~450-words-per-language cap "
                         "applies to that LATER analysis, NOT to these "
                         "notes: complete URLs and full findings take "
                         "precedence over brevity here. "
                         "Return the FULL notes as the text of "
                         "your reply: you have NO persistent filesystem, "
                         "and anything written to files by result-filtering "
                         "code is DISCARDED — a finding (and its URL) that "
                         "is not in your reply text is lost. Never reply "
                         "with a summary of notes kept elsewhere. Web "
                         "findings are cited sources only; they never "
                         "enter the curated registry (knowledge admission "
                         "is human-gated).")),
                # notes must carry their sources: a reply that merely
                # narrates notes "saved" in the (discarded) sandbox has no
                # URLs and fails here, triggering the corrective retry
                validate=lambda t: len(t.strip()) > 200 and "http" in t,
                out_path=rd / "research" / f"{name}.md",
                # thinking + search orchestration count toward the cap: at
                # 4000 the search-heavy seats hit max_tokens BEFORE writing
                # the sourced notes (live probe: stop=max_tokens, 0 URLs).
                # 16000 matches the expert-analysis budget — these seats
                # think a lot before they cite (owner call, 2026-07-16)
                max_tokens=16000, web_search=True)
            research_notes = (
                "\n\nLIVE RESEARCH NOTES (from web search this round; cite "
                "them with their URL as the source and an honest evidence "
                "grade; registry-backed facts keep their registry source):\n"
                + research_text)
        if obj is None:
            obj, _ = step.run(
                f"expert:{name}",
                dict(task="expert_analysis", agent=name, round_n=n,
                     instructions=(
                         f"Policy question: {question}\n"
                         "Produce your analysis as the required JSON object, "
                         "in BOTH English and Hungarian: every {en, hu} pair "
                         "carries the SAME statement written natively in "
                         "each language (parallel authoring, never "
                         "machine-translation flavour; use the glossary "
                         "terms strictly). findings = factual claims, each "
                         "with an honest evidence grade and a named source; "
                         "position = exactly one falsifiable sentence; "
                         "uncertainties = known unknowns with confidence "
                         "and what evidence would reduce them."
                         + curated_sources(name) + research_notes
                         + "\n\nGLOSSARY:\n" + glossary)),
                # bilingual output ≈ 2x the monolingual token count, and the
                # live research notes add material — 8000 truncated in the
                # round-8 acceptance run (structured truncation is terminal)
                validate=valid_expert, out_path=out_path,
                schema=S.EXPERT_ANALYSIS, max_tokens=24000)
        md = render.expert_md(name, obj, "en")
        write(rd / "expert_outputs" / f"{name}.md", md)
        return name, md

    experts = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, md in ex.map(run_expert, T.experts):
            experts[name] = md

    expert_digest = "\n\n".join(
        f"----- {name} -----\n{text}" for name, text in experts.items())

    # 1.5 emergent scenario framing (issue #21, D-36): on a topic with no
    #     approved frames yet, round 1 derives the option space (2-5 frames)
    #     from the expert record, writes a human-gated proposal, and STOPS.
    #     Approval (scripts/new_topic.py approve-frames) freezes the frames
    #     into topic.json; the relaunch resumes this round and the expert
    #     outputs are reused (the state hash excludes the frames block).
    if not T.frames_approved:
        propose_frames(step, rd, n, T, question, expert_digest, glossary)
        raise FramesPending(
            f"topic {T.slug!r}: scenario frames were derived from the "
            f"round-{n} expert record and await HUMAN APPROVAL.\n"
            f"  review/edit: {T.proposals_dir / 'frames.json'}\n"
            f"  (readable view: {T.proposals_dir / 'frames.md'})\n"
            f"  approve:     .venv/bin/python scripts/new_topic.py "
            f"approve-frames --topic {T.slug}\n"
            "  then relaunch the same run command — the round resumes and "
            "the expert outputs are reused.")

    ids = tuple(T.scenario_ids)
    id_set = set(ids)
    ids_line = "SCENARIO IDS: " + ", ".join(ids)

    # 2. scenario builder (bilingual, schema-constrained — D-34; anchored
    #    on the topic's frozen, human-approved frames — issue #21/D-36)
    scen_bi, _ = step.run(
        "scenario_builder",
        dict(task="build_scenarios", agent="scenario_builder", round_n=n,
             instructions=(
                 f"{question}\n{T.frame_anchors()}\n{ids_line}\n"
                 "Return the scenarios in the required JSON schema, in BOTH "
                 "English and Hungarian: every {en, hu} pair carries the "
                 "SAME statement written natively in each language "
                 "(parallel authoring, never machine-translation flavour; "
                 "use the glossary terms strictly). Grade every mechanism "
                 "claim's and expected benefit's evidence honestly; give "
                 "every implementation step an actor, action and timeline; "
                 "give every uncertainty a confidence level and what "
                 "evidence would reduce it.\n\nGLOSSARY:\n" + glossary),
             inputs=expert_digest),
        validate=lambda o: valid_scenarios_bi(o, id_set),
        out_path=rd / "scenarios.json",
        # 30000 truncated with direct-search experts: richer sourced inputs
        # produce longer scenario sets (5 frames, bilingual, 10 fields each).
        # 48000 itself compresses under a 13-expert digest (PR #29 Cell C/D:
        # uncertainties per scenario dropped 3->2.2 only when the digest grew,
        # not from expert-content rerun noise) — raised for panel headroom.
        schema=S.SCENARIOS(ids), max_tokens=64000)
    scen_en = render.scenario_view(scen_bi, "en")
    scen_hu = render.scenario_view(scen_bi, "hu")
    scen_en_md = render.scenarios_md(scen_en, "en")
    scen_hu_md = render.scenarios_md(scen_hu, "hu")
    write(rd / "scenarios.en.md", scen_en_md)
    write(rd / "scenarios.hu.md", scen_hu_md)

    # 3. editor synthesis + rejected framings
    synthesis_obj, _ = step.run(
        "editor",
        dict(task="synthesis", agent="editor", round_n=n,
             instructions=(
                 "Synthesize the expert record as the required JSON object, "
                 "in BOTH English and Hungarian: every {en, hu} pair carries "
                 "the SAME statement written natively in each language (use "
                 "the glossary strictly). overview = the coherent picture "
                 "WITHOUT forcing consensus; disagreements = the "
                 "disagreement map (per side: holders, position, rationale, "
                 "minority flag — mark the minority side, never resolve it "
                 "away); agreements = what the experts agree on, each with "
                 "an honest evidence grade.\n\nGLOSSARY:\n" + glossary),
             inputs=expert_digest),
        validate=valid_synthesis, out_path=rd / "synthesis.json",
        schema=S.SYNTHESIS, max_tokens=32000)
    synthesis_text = render.synthesis_md(synthesis_obj, "en")
    write(rd / "synthesis.md", synthesis_text)
    write(rd / "synthesis.hu.md", render.synthesis_md(synthesis_obj, "hu"))

    rejected_obj, _ = step.run(
        "rejected_framings",
        dict(task="rejected_framings", agent="scenario_builder", round_n=n,
             instructions=(
                 f"For each scenario ({ids_line}), record the candidate "
                 "framings you considered as the required JSON object: the "
                 "chosen framing plus at least one rejected framing with "
                 "the reason for its rejection."),
             inputs=scen_en_md),
        validate=lambda o: valid_rejected(o, id_set),
        out_path=rd / "rejected_framings.json",
        schema=S.REJECTED_FRAMINGS(ids), max_tokens=4000)
    rejected = render.rejected_md(rejected_obj)
    write(rd / "rejected_framings.md", rejected)

    # 3.5 societal-discourse layer (D-29): argument ledger
    disc_cfg = cfg.get("discourse", {})
    disc = None
    if disc_cfg.get("enabled"):
        disc = run_discourse(step, rd, n, scen_en_md, glossary, disc_cfg,
                             T, facts)

    # 5. brief — the bilingual 10-section deliberation deliverable
    #    (D-30/D-34; the old translator_brief step is gone). With the
    #    discourse layer on, stakeholder_responses carries the response
    #    obligation (D-29, CNDP model): every argument cluster gets a
    #    typed answer.
    brief_instr = (
        "Write the deliberation brief as the required JSON object, in BOTH "
        "English and Hungarian: every {en, hu} pair carries the SAME "
        "statement authored natively in each language (glossary strictly; "
        "never machine-translation flavour). The renderer produces the 10 "
        "public sections from your fields — fill each with substance: "
        "what_we_know = the strongest evidence-backed findings, honest "
        "evidence grades; what_we_consider_likely = weaker or "
        "indirect-evidence conclusions (kind: estimate); "
        "where_experts_disagree = the disagreement map's substance with "
        "reasons (why), minority sides marked; what_we_dont_know = the "
        "critical gaps, distinguishing known-unknowns from mere "
        "assumptions; what_could_be_done = the real alternatives (never "
        "crown a single scenario as the answer); what_each_option_costs = "
        "trade-offs, harms, risks and who wins/loses per alternative — "
        "never hide a trade-off behind neutral language; "
        "what_research_could_resolve = what new data or study would most "
        "change the decision; what_people_must_decide = the value choices "
        "and political decisions this needs — these are the honest answer, "
        "not failures; minority_positions = every minority view with "
        "holders and rationale, never resolved away; scenario_key = one "
        "line per scenario so the brief is self-contained. Set every "
        "item's kind honestly ([fact]/[estimate]/[assumption]/[value] in "
        "the rendered view) — never let a value judgment pass as a fact.")
    brief_inputs = scen_en_md + "\n\n" + synthesis_text
    if disc:
        brief_instr += (
            " stakeholder_responses: answer EVERY argument cluster from "
            "the ledger by its A<i> id. response_type MUST be one of the 7 "
            "tokens: evidence_answerable (evidence settles or meaningfully "
            "refines it), policy_design_fixable (a design change, "
            "guarantee, compensation or phase-in reduces it), "
            "communication_fixable (already addressed but not visibly or "
            "legibly), value_conflict (legitimate values collide, there is "
            "no technical fix), irreducible_tradeoff (improving one goal "
            "necessarily costs another), needs_more_info (not yet "
            "decidable from the evidence), not_decision_relevant "
            "(attention-worthy but would not change the decision). Do NOT "
            "force every cluster into artificial consensus — "
            "value_conflict and irreducible_tradeoff are legitimate final "
            "answers, not failures. An argument answered by no one is a "
            "defect (response obligation). attention_sinks: the ledger's "
            "gumicsont clusters (high attention, would not change the "
            "decision) with why — so readers can tell which arguments "
            "move the decision from which mostly consume attention.")
        brief_inputs += ("\n\n=== ARGUMENT LEDGER (public arguments that "
                         "MUST each be answered) ===\n" + disc["ledger_en"])
    brief_obj, _ = step.run(
        "final_brief_writer",
        dict(task="brief", agent="final_brief_writer", round_n=n,
             instructions=brief_instr + "\n" + ids_line
             + "\n\nGLOSSARY:\n" + glossary,
             inputs=brief_inputs),
        validate=lambda o: valid_brief(
            o, id_set, disc["cluster_ids"] if disc else None),
        # bilingual 10 sections + a typed response per argument cluster in
        # one shot — the largest deliverable in the round
        out_path=rd / "brief.json", schema=S.BRIEF(ids), max_tokens=64000)
    brief_en = render.brief_md(brief_obj, "en")
    brief_hu = render.brief_md(brief_obj, "hu")
    write(rd / "brief.en.md", brief_en)
    write(rd / "brief.hu.md", brief_hu)

    # 6. critics (parallel) + translation checker
    registry_digest = "\n".join(
        f"- {fid} [{f['evidence']}]: {f['en'][:120]}... (source: {f['source']})"
        for fid, f in facts.items()) or \
        "(no registry-backed facts admitted for this topic yet)"

    def run_critic(name):
        extra = ""
        if name == "evidence_checker":
            extra = ("\nCURATED SOURCE REGISTRY (the only registry-backed "
                     "facts; a claim tagged stronger than its registry grade, "
                     "or citing a source not listed here without flagging it "
                     "as model knowledge, is a defect):\n" + registry_digest)
        obj, _ = step.run(
            f"critic:{name}",
            dict(task="critic", agent=name, round_n=n,
                 instructions=(
                     "Critique the scenarios below as the required JSON "
                     "object. 2-4 objections — pick the most consequential, "
                     "not the easiest. Each objection names the specific "
                     "scenario and field it attacks, states the concrete "
                     "flaw (generic feedback is a failure), a severity, and "
                     "a concrete suggested revision. Attack content, not "
                     "style." + extra),
                 inputs=scen_en_md + "\n\n" + synthesis_text),
            validate=valid_critic,
            out_path=rd / "critic_outputs" / f"{name}.json",
            schema=S.CRITIC(ids), role="judge", max_tokens=8000)
        md = render.critic_md(name, obj)
        write(rd / "critic_outputs" / f"{name}.md", md)
        return name, md

    critics = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, md in ex.map(run_critic, D.CRITICS):
            critics[name] = md

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
    obj, _ = step.run(
        "meta_critic",
        dict(task="meta_critique", agent="meta_critic", round_n=n,
             payload_json=json.dumps(payload, ensure_ascii=False, indent=2),
             instructions=(
                 "Write the round's meta-critique of the agent SYSTEM as "
                 "the required JSON object. gaming_judgment.verdict: "
                 "GENUINE or RUBRIC-GAMING with reasons grounded in the "
                 "input scores (NO_BASELINE only when there is no previous "
                 "total to compare against). Name at least one concrete "
                 "agent or workflow weakness; if any agent raised no "
                 "dimension for two rounds, list it in removal_candidates."),
             inputs=("Critic outputs digest:\n"
                     + "\n".join(f"- {k}: {len(CRITIC_HEADING_RE.findall(v))} targeted objections"
                                 for k, v in artifacts["critics"].items()))),
        validate=valid_meta,
        out_path=artifacts["round_dir"] / "meta_critique.json",
        schema=S.META_CRITIQUE, role="judge", max_tokens=8000)
    text = render.meta_md(obj, n)
    write(artifacts["round_dir"] / "meta_critique.md", text)
    artifacts["fallbacks"][:] = step.fallbacks
    artifacts["meta"] = text
    return text
