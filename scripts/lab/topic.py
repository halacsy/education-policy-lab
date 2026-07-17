"""Per-topic configuration and state (multi-topic architecture, D-35).

A topic is one policy problem processed by the shared agent hub. Everything
question-specific lives under topics/<slug>/ (committed) and
outputs/topics/<slug>/ (committed audit trail) — the code carries NO
question-specific literals (owner direction 2026-07-14, issues #18/#21).

topics/<slug>/
  topic.json          problem brief (the system INPUT), frozen frames,
                      rosters, per-topic evaluation settings
  glossary.md         bilingual terminology + machine-checked key pairs
  agents/memory/      per-topic episodic memory (lab/memory.py)
  agents/directives/  per-topic improvement-directive overlay (lab/improve.py
                      writes here, never into the shared specs — one topic's
                      learnings must not leak into another)
  proposals/          intake / framing proposals awaiting human approval

outputs/topics/<slug>/{iterations,final,archive}/

Entry scripts select the topic once (set_current); everything else reads
current(). Concurrent topics run as separate processes; their round commits
are path-scoped (lab/gitutil.py) so they never cross-commit.
"""
import json

from .util import OUTPUTS_DIR, ROOT, load_config, read_json, write_json

TOPICS_DIR = ROOT / "topics"

_current = None


class Topic:
    def __init__(self, slug):
        self.slug = slug
        self.dir = TOPICS_DIR / slug
        self.path = self.dir / "topic.json"
        if not self.path.exists():
            known = sorted(p.parent.name for p in TOPICS_DIR.glob("*/topic.json"))
            raise SystemExit(
                f"unknown topic {slug!r} — known topics: {known} "
                "(create one with scripts/new_topic.py)")
        self.config = read_json(self.path)
        # overridable output root (run_mock_sprint points it at the
        # gitignored scratch dir)
        self.out_root = OUTPUTS_DIR / "topics" / slug

    def save(self):
        write_json(self.path, self.config)

    # -- paths ----------------------------------------------------------------

    @property
    def iter_dir(self):
        return self.out_root / "iterations"

    @property
    def final_dir(self):
        return self.out_root / "final"

    @property
    def archive_dir(self):
        return self.out_root / "archive"

    @property
    def memory_dir(self):
        return self.dir / "agents" / "memory"

    @property
    def directives_dir(self):
        return self.dir / "agents" / "directives"

    @property
    def proposals_dir(self):
        return self.dir / "proposals"

    @property
    def glossary_path(self):
        return self.dir / "glossary.md"

    def glossary(self):
        return self.glossary_path.read_text(encoding="utf-8")

    # -- problem brief (the system input) --------------------------------------

    @property
    def problem_brief(self):
        return self.config["problem_brief"]

    def title(self, lang):
        return self.problem_brief["title"][lang]

    def question_block(self):
        """The problem brief as the prompt block that replaced the old
        single policy_question literal (EN projection; the bilingual pairs
        live in topic.json)."""
        b = self.problem_brief
        goals = "\n".join(f"- {g['en']}" for g in b["learning_goals"])
        return (f"PROBLEM BRIEF: {b['title']['en']}\n"
                f"Problem statement: {b['problem_statement']['en']}\n"
                f"Learning goals:\n{goals}\n"
                f"Scope: {b['scope']['en']}")

    def brief_title(self, lang):
        if lang == "en":
            return f"# Policy brief — {self.title('en')}"
        return f"# Szakpolitikai összefoglaló — {self.title('hu')}"

    # -- frames (emergent scenario framing, issue #21) --------------------------

    @property
    def frames(self):
        return self.config.get("frames") or {}

    @property
    def frames_approved(self):
        return self.frames.get("status") == "approved"

    @property
    def scenario_ids(self):
        return [f["id"] for f in self.frames.get("scenarios", [])]

    def frame_anchors(self):
        """The scenario-builder anchor instruction, built from the frozen
        frames (replaces the deleted pipeline.SCENARIO_ANCHORS hardcode)."""
        scs = self.frames["scenarios"]
        lines = [f"{f['id']} {f['title']['en']}: {f['scope']['en']}"
                 for f in scs]
        return (f"Produce EXACTLY {len(scs)} scenarios with these stable, "
                "human-approved frames (keep each scenario inside its "
                "frame's scope):\n" + "\n".join(lines))

    # -- rosters (shared hub, per-topic selection) -------------------------------

    @property
    def experts(self):
        from . import agent_defs as D
        return list(self.config.get("experts") or D.EXPERTS)

    @property
    def voices(self):
        from . import agent_defs as D
        return list(self.config.get("voices") or D.DISCOURSE)

    # -- knowledge --------------------------------------------------------------

    def registry_facts(self):
        """The curated registry facts relevant to this topic (D-24 gated).
        registry_facts: null means all; a list scopes to those fact ids."""
        from . import knowledge as K
        wanted = self.config.get("registry_facts")
        if wanted is None:
            return dict(K.FACTS)
        return {fid: K.FACTS[fid] for fid in wanted if fid in K.FACTS}

    def expert_facts(self, name):
        """Registry fact ids curated for one expert (topic.json expert_facts)."""
        return self.config.get("expert_facts", {}).get(name, [])

    @property
    def human_questions(self):
        return self.config.get("human_questions", [])

    @property
    def era_start_round(self):
        return self.config.get("evaluation", {}).get("era_start_round", 1)

    # -- state fingerprint --------------------------------------------------------

    def state_fingerprint(self):
        """Canonical topic.json bytes for the round state hash, EXCLUDING
        frames: frame approval mid-round-1 must not invalidate the expert
        outputs the frames were derived from (frames are consumed only by
        scenario-dependent steps, whose validators re-check the id set; the
        sanctioned frame-change path, new_topic.py approve-frames, purges
        scenario-dependent artifacts explicitly)."""
        # "evaluation" (era_start_round) is likewise excluded: the era
        # label is consumed only by the loop's delta/revert logic, never by
        # a generation step — moving an era boundary must not invalidate
        # the artifacts it merely re-labels (same rationale as frames).
        cfg = {k: v for k, v in self.config.items()
               if k not in ("frames", "evaluation")}
        return json.dumps(cfg, ensure_ascii=False, sort_keys=True).encode("utf-8")


def default_slug():
    slug = load_config().get("default_topic")
    if not slug:
        raise SystemExit("config/system_config.json has no default_topic")
    return slug


def all_slugs():
    return sorted(p.parent.name for p in TOPICS_DIR.glob("*/topic.json"))


def set_current(slug=None):
    global _current
    _current = Topic(slug or default_slug())
    return _current


def current():
    global _current
    if _current is None:
        _current = Topic(default_slug())
    return _current
