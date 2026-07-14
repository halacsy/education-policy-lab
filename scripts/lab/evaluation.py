"""Rubric evaluation (spec: templates/evaluation_rubric.md).

Deterministic, capped, density-based checks are primary (weight ≥ 0.7).
Five dimensions add an LLM-judged component under the Evaluator protocol:
N=3 order-randomized trials, mean+variance recorded, cross-family scoring
without self-judging (D-14), verbosity capped, divergence → deterministic
score + human flag (never averaged away).
"""
import json
import random
import re
import statistics

from . import llm
from .agents import build_prompt
from .util import load_config, write, write_json

DIMENSIONS = [
    "scenario_completeness", "evidence_discipline", "critic_concreteness",
    "layer_separation", "meta_system_eval", "disagreement_preservation",
    "uncertainty_explicitness", "translation_fidelity",
]

# role whose provider scores the dimension's artifact (never the producer)
LLM_SCORED = {
    "evidence_discipline": "judge",          # generator-side artifacts
    "disagreement_preservation": "judge",
    "translation_fidelity": "judge",
    "critic_concreteness": "generator",      # judge-side artifacts
    "meta_system_eval": "generator",
}
DET_WEIGHT = 0.7

JUDGE_RUBRICS = {
    "evidence_discipline": "Are important claims tagged with an evidence status? Are evidence, interpretation and assumption kept apart? Is any confidence invented?",
    "disagreement_preservation": "Is disagreement mapped (who, what, why)? Do minority positions survive with rationale, or is there forced consensus?",
    "translation_fidelity": "Compare the Hungarian and English versions: same meaning, same structure, terminology consistent? (Structure/ids are checked mechanically; judge meaning fidelity only.)",
    "critic_concreteness": "Are objections concrete and targeted (specific scenario+field, specific flaw), actionable, and non-generic?",
    "meta_system_eval": "Does this evaluate the agent SYSTEM (agent/workflow failures, critique quality, gaming judgment) rather than the policy content?",
}


def _frac(count, total):
    return 0.0 if total <= 0 else min(1.0, count / total)


def _count(pattern, text):
    return len(re.findall(pattern, text, re.M))


# --------------------------------------------------------------------------
# deterministic components
# --------------------------------------------------------------------------

def det_scenario_completeness(a):
    scs = a["scenarios_en"]["scenarios"]
    fields_ok = _frac(sum(1 for s in scs if all(
        (s[k] if isinstance(s[k], str) else " ".join(s[k])).strip()
        for k in FIELDS)), len(scs))
    steps = [st for s in scs for st in s["implementation_steps"]]
    timeline = _frac(sum(1 for st in steps if re.search(
        r"timeline|ütemezés|\bé[vv]\b|year|\b20\d\d\b|\d+\.\s*év", st)), len(steps))
    actors = _frac(sum(1 for st in steps if "—" in st or " - " in st), len(steps))
    return 10 * (0.5 * fields_ok + 0.3 * timeline + 0.2 * actors)


def det_evidence_discipline(a):
    def tag_frac(scen):
        claims = tags = 0
        for s in scen["scenarios"]:
            items = s["mechanism"] + s["expected_benefits"]
            claims += len(items)
            tags += sum(1 for i in items if "[evidence:" in i or "[bizonyíték:" in i)
        return _frac(tags, claims)

    expert_text = "\n".join(a["experts"].values())
    expert_frac = _frac(_count(r"\[evidence:", expert_text),
                        _count(r"^- ", expert_text) or 1)
    brief_frac = _frac(_count(r"\[(?:fact|estimate|assumption|value)\b", a["brief_en"]),
                       _count(r"^- ", a["brief_en"]) or 1)
    return 10 * (0.5 * tag_frac(a["scenarios_en"]) + 0.25 * min(1.0, expert_frac)
                 + 0.25 * min(1.0, brief_frac))


def det_critic_concreteness(a):
    from .pipeline import CRITIC_HEADING_RE
    ids = sev = fix = obj = 0
    for text in a["critics"].values():
        h = len(CRITIC_HEADING_RE.findall(text))
        ids += h
        obj += max(h, _count(r"Objection:", text))
        sev += _count(r"Severity:\s*(high|medium|low)", text)
        fix += _count(r"Suggested revision:", text)
    return 10 * (0.5 * _frac(ids, obj) + 0.25 * _frac(sev, obj) + 0.25 * _frac(fix, obj))


def det_layer_separation(a):
    """Scores the 10-section deliberation brief (D-30): section coverage
    plus per-claim [fact]/[estimate]/[assumption]/[value] tag density,
    applied wherever a claim lands rather than confined to one section."""
    from .pipeline import BRIEF_HEADERS_EN
    text = a["brief_en"]
    headers = _frac(sum(1 for h in BRIEF_HEADERS_EN if h in text),
                    len(BRIEF_HEADERS_EN))
    tag_frac = _frac(_count(r"\[(?:fact|estimate|assumption|value)\b[^\]]*\]", text),
                     _count(r"^- ", text) or 1)
    return 10 * (0.6 * headers + 0.4 * min(1.0, tag_frac))


def det_meta_system_eval(meta_text):
    markers = [r"## Agent performance", r"## Workflow", r"## Critique quality",
               r"Gaming judgment", r"(GENUINE|RUBRIC-GAMING)",
               r"removal candidate", r"Translation consistency"]
    return 10 * _frac(sum(1 for p in markers if re.search(p, meta_text)),
                      len(markers))


def det_disagreement_preservation(a):
    syn = a["synthesis"]
    m = re.search(r"## Disagreement map(.*?)(\n## |\Z)", syn, re.S)
    body = m.group(1) if m else ""
    entries = _count(r"^- \*\*", body)
    whys = _count(r"Why:", body)
    minority_marked = 1.0 if re.search(r"\(minority\)", body) else 0.0
    minority_in_brief = 1.0 if re.search(
        r"## (Minority positions|Különvélemények)", a["brief_en"] + a["brief_hu"]) else 0.0
    return 10 * (0.3 * _frac(entries, 4) + 0.2 * _frac(whys, max(entries, 1))
                 + 0.1 * minority_marked + 0.4 * minority_in_brief)


def det_uncertainty_explicitness(a):
    items = [u for s in a["scenarios_en"]["scenarios"] for u in s["uncertainties"]]
    items_hu = [u for s in a["scenarios_hu"]["scenarios"] for u in s["uncertainties"]]
    has = _frac(len(items), 3 * len(a["scenarios_en"]["scenarios"]))
    conf = _frac(sum(1 for u in items if re.search(r"confidence:", u)), len(items))
    conf_hu = _frac(sum(1 for u in items_hu if re.search(r"megbízhatóság", u)),
                    len(items_hu))
    reducer = _frac(sum(1 for u in items if re.search(r"reduc", u)), len(items))
    return 10 * (0.3 * has + 0.25 * conf + 0.17 * conf_hu + 0.28 * reducer)


def det_translation_fidelity(a):
    r = a["translation"]
    viol = 1.0 - _frac(len(r["glossary_violations"]), 3)
    clean = 1.0 if not (r["byte_identical_docs"] or r["untranslated_fields"]) else 0.0
    return 10 * (0.3 * float(r["id_sets_equal"]) + 0.25 * float(r["structure_equal"])
                 + 0.25 * viol + 0.2 * clean)


FIELDS = ["goal", "mechanism", "evidence_status", "assumptions",
          "expected_benefits", "equity_impact", "cost_categories",
          "implementation_steps", "political_risks", "uncertainties"]


def artifact_text_for(dim, a):
    if dim == "evidence_discipline":
        return a["scenarios_en_md"] + "\n" + a["brief_en"]
    if dim == "disagreement_preservation":
        return a["synthesis"] + "\n" + a["brief_en"]
    if dim == "translation_fidelity":
        en = a["scenarios_en"]["scenarios"][0]
        hu = a["scenarios_hu"]["scenarios"][0]
        return ("EN:\n" + json.dumps(en, ensure_ascii=False, indent=1)
                + "\nHU:\n" + json.dumps(hu, ensure_ascii=False, indent=1))
    if dim == "critic_concreteness":
        return "\n\n".join(a["critics"].values())
    if dim == "meta_system_eval":
        return a["meta"]
    raise KeyError(dim)


def llm_component(dim, a, round_n):
    """N=3 order-randomized trials; returns (mean, variance, trials, provider)."""
    cfg = load_config()["evaluation"]
    role = LLM_SCORED[dim]
    provider = llm.provider_for_role(role)
    text = artifact_text_for(dim, a)
    sections = re.split(r"\n(?=## )", text)
    trials = []
    for t in range(cfg["llm_judge_trials"]):
        rng = random.Random(f"round{round_n}:{dim}:trial{t}")
        shuffled = sections[:]
        rng.shuffle(shuffled)
        prompt = build_prompt(
            task="judge_score", provider=provider, round_n=round_n,
            payload_json=json.dumps({"dimension": dim}),
            instructions=(
                f"You are scoring the rubric dimension '{dim}'.\n"
                f"Criteria: {JUDGE_RUBRICS[dim]}\n"
                "Score 0-10. Text length alone must NOT raise the score; "
                "judge density and discipline, not volume. Sections are "
                "presented in randomized order. Respond with exactly two "
                "lines:\nSCORE: <number>\nREASON: <one sentence>"),
            inputs="=== ARTIFACT ===\n" + "\n".join(shuffled))
        out = llm.call_model(prompt, role, max_tokens=800, dimension=dim)
        m = re.search(r"SCORE:\s*([0-9]+(?:\.[0-9]+)?)", out)
        score = float(m.group(1)) if m else None
        if score is None:
            from . import mock_backend
            out = mock_backend.compose(prompt, role)
            score = float(re.search(r"SCORE:\s*([0-9.]+)", out).group(1))
        trials.append(round(min(10.0, max(0.0, score)), 3))
    mean = round(statistics.fmean(trials), 3)
    var = round(statistics.pvariance(trials), 4)
    return mean, var, trials, provider


def score_seven(a, round_n):
    """All dimensions except meta_system_eval (which needs the meta-critique)."""
    det = {
        "scenario_completeness": det_scenario_completeness(a),
        "evidence_discipline": det_evidence_discipline(a),
        "critic_concreteness": det_critic_concreteness(a),
        "layer_separation": det_layer_separation(a),
        "disagreement_preservation": det_disagreement_preservation(a),
        "uncertainty_explicitness": det_uncertainty_explicitness(a),
        "translation_fidelity": det_translation_fidelity(a),
    }
    dims = {}
    for name, d in det.items():
        dims[name] = _compose(name, d, a, round_n)
    return dims


def meta_dimension(meta_text, a, round_n):
    return _compose("meta_system_eval", det_meta_system_eval(meta_text), a,
                    round_n)


def _compose(name, det_value, a, round_n):
    threshold = load_config()["evaluation"]["judge_divergence_threshold"]
    entry = {"deterministic": round(det_value, 3)}
    if name in LLM_SCORED:
        mean, var, trials, provider = llm_component(name, a, round_n)
        flagged = abs(mean - det_value) > threshold
        entry["llm"] = {"provider": provider, "trials": trials, "mean": mean,
                        "variance": var, "divergence_flagged": flagged}
        if flagged:
            # never averaged: deterministic score stands, human review flagged
            entry["score"] = round(det_value, 3)
            entry["method"] = "deterministic (LLM diverged; flagged for human)"
        else:
            entry["score"] = round(DET_WEIGHT * det_value + (1 - DET_WEIGHT) * mean, 3)
            entry["method"] = f"mixed ({DET_WEIGHT} det + {1-DET_WEIGHT:.1f} llm)"
    else:
        entry["score"] = round(det_value, 3)
        entry["method"] = "deterministic"
    return entry


def finalize(round_n, dims, a, prev_total):
    total = round(statistics.fmean(d["score"] for d in dims.values()), 3)
    flagged = [n for n, d in dims.items()
               if d.get("llm", {}).get("divergence_flagged")]
    ev = {
        "round": round_n,
        "dimensions": {n: dims[n] for n in DIMENSIONS},
        "total": total,
        "prev_total": prev_total,
        "delta": None if prev_total is None else round(total - prev_total, 3),
        "generator_provider": llm.provider_for_role("generator"),
        "judge_provider": llm.provider_for_role("judge"),
        "divergence_flagged": flagged,
        "step_fallbacks": a["fallbacks"],
    }
    rd = a["round_dir"]
    write_json(rd / "evaluation.json", ev)
    lines = [f"# Evaluation — round {round_n}", "",
             f"Total: **{total}**" + (f" (delta {ev['delta']:+.3f})" if ev["delta"] is not None else " (baseline)"),
             "",
             "| dimension | score | method | det | llm mean | llm var |",
             "|---|---|---|---|---|---|"]
    for n in DIMENSIONS:
        d = dims[n]
        L = d.get("llm", {})
        lines.append(f"| {n} | {d['score']} | {d['method']} | "
                     f"{d['deterministic']} | {L.get('mean', '—')} | "
                     f"{L.get('variance', '—')} |")
    lines += ["",
              f"Generator: {ev['generator_provider']}; judge: {ev['judge_provider']} "
              "(cross-family; judge-side artifacts scored by the generator "
              "provider — see docs/decisions.md D-14).",
              f"Divergence-flagged dimensions (sent to human review): {flagged or 'none'}.",
              f"Steps that failed and needed a relaunch (D-34, no mock "
              f"fallback): {a['fallbacks'] or 'none'}.",
              "",
              "Note: the meta-critique was written before the final total "
              "existed; it saw the seven content dimensions and the previous "
              "round's total."]
    write(rd / "evaluation.md", "\n".join(lines) + "\n")
    return ev
