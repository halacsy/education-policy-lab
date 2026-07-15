"""Shared loaders for the public-site generators (build_site_explorer,
build_site_topics).

The D-34 structured JSON artifacts are the single source of truth; both the
topic page and the explorer must read the same clusters / verdicts /
disagreement axes so that a deep link minted on one page (e.g.
explorer.html#cluster-A16) always lands on the same item on the other.
Standard library only — the Pages workflow runs these on bare python3.
"""
import json

from .render import grades_dict, project

VERDICT_HU = {
    "evidence_answerable": "evidenciával megválaszolható",
    "policy_design_fixable": "tervezéssel kezelhető",
    "communication_fixable": "kommunikációval kezelhető",
    "value_conflict": "értékkonfliktus",
    "irreducible_tradeoff": "feloldhatatlan trade-off",
    "needs_more_info": "több információ kell",
    "not_decision_relevant": "nem döntésreleváns",
}
# 7 verdict types -> 3 semantic groups: fixable (evidence green),
# human decision needed (rust), open/parked (muted)
VERDICT_GROUP = {
    "evidence_answerable": "fix", "policy_design_fixable": "fix",
    "communication_fixable": "fix",
    "value_conflict": "human", "irreducible_tradeoff": "human",
    "needs_more_info": "open", "not_decision_relevant": "open",
}
KIND_HU = {"fact": "tény", "value": "érték", "mixed": "vegyes"}
SIDE_HU = {"pro": "mellette", "con": "ellene", "conditional": "feltételes"}
REL_HU = {"high": "magas", "medium": "közepes", "low": "alacsony"}
DECOMP_FIELDS = [("interest", "Kinek az érdeke"), ("value", "Milyen érték ütközik"),
                 ("fear", "Milyen félelem hajtja"), ("assumption", "Milyen feltevésre épül"),
                 ("empirical_uncertainty", "Empirikus bizonytalanság")]


def last_round(iter_dir):
    """Highest round number under outputs/topics/<slug>/iterations, or None."""
    rounds = sorted(int(p.name.split("_")[1]) for p in iter_dir.glob("round_*"))
    return rounds[-1] if rounds else None


def is_gumicsont(cluster):
    """Attention sink: heavily debated but would not change the decision."""
    attn = cluster.get("attention", {})
    return bool(attn.get("high_attention")) and \
        cluster.get("decision_relevance") == "low"


def load_structured_discourse(rd):
    """Cluster data straight from the D-34 JSON artifacts (no md parsing).
    Returns None for pre-D-34 rounds."""
    amap = rd / "discourse" / "argument_map.json"
    brief = rd / "brief.json"
    if not (amap.exists() and brief.exists()):
        return None
    clusters = project(json.loads(amap.read_text(encoding="utf-8"))["clusters"], "hu")
    grades_p = rd / "discourse" / "argument_grades.json"
    grades = grades_dict(json.loads(grades_p.read_text(encoding="utf-8"))) \
        if grades_p.exists() else {}
    recipro = {}
    for rp in sorted((rd / "discourse" / "responses").glob("*.json")):
        obj = project(json.loads(rp.read_text(encoding="utf-8")), "hu")
        for r in obj.get("responses", []):
            recipro.setdefault(r["cluster"], []).append(
                dict(voice=obj.get("voice", rp.stem), response=r["response"],
                     outcome=r["outcome"]))
    b = project(json.loads(brief.read_text(encoding="utf-8")), "hu")
    verdicts = {r["cluster_id"]: r for r in b.get("stakeholder_responses", [])}
    sinks = {s["cluster_id"]: s["text"] for s in b.get("attention_sinks", [])}
    return dict(clusters=clusters, grades=grades, recipro=recipro,
                verdicts=verdicts, sinks=sinks)


def load_structured_disagreements(rd, lang="hu"):
    """where_experts_disagree axes from brief.json: list of
    {topic, positions:[{holders, minority, position, why}]}.
    None for pre-D-34 rounds (callers fall back to md parsing)."""
    p = rd / "brief.json"
    if not p.exists():
        return None
    b = project(json.loads(p.read_text(encoding="utf-8")), lang)
    return b.get("where_experts_disagree") or []


def list_experts(rd):
    """Expert-agent names that produced output in this round."""
    return sorted(p.stem for p in (rd / "expert_outputs").glob("*.md"))
