#!/usr/bin/env python3
"""Definition of done, encoded as assertions. Exits non-zero unless ALL
checks pass. Do not weaken these checks to pass them; fix the system.

Checks 1-14 mirror the specification; the held-out qualitative checks
(lab/holdout_checks.py — invisible to the improvement step) run at the end.
"""
import hashlib
import os
import re
import subprocess
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from lab import holdout_checks, translation
from lab.evaluation import DIMENSIONS, LLM_SCORED
from lab.loadround import load_artifacts
from lab.pipeline import BRIEF_HEADERS_EN, BRIEF_HEADERS_HU, CRITIC_HEADING_RE
from lab.util import FINAL_DIR, ITER_DIR, ROOT, load_config, read, read_json

FAILURES = []
REQUIRED_ROUND_FILES = [
    "scenarios.json", "scenarios.en.md", "scenarios.hu.md", "synthesis.md",
    "rejected_framings.md", "brief.en.md", "brief.hu.md", "meta_critique.md",
    "evaluation.json", "evaluation.md", "improvement_plan.md",
    "revised_agents.md", "revised_workflow.md",
]
SCENARIO_FIELDS = ["goal", "mechanism", "evidence_status", "assumptions",
                   "expected_benefits", "equity_impact", "cost_categories",
                   "implementation_steps", "political_risks", "uncertainties"]
POLICY_CRITICS = ["devil_advocate", "evidence_checker", "assumption_checker",
                  "equity_checker", "feasibility_checker", "cost_checker",
                  "political_risk_checker", "coherence_checker"]


def check(num, name, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] check {num:>4}: {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(f"{num}: {name} ({detail})")


def rounds():
    if not ITER_DIR.exists():
        return []
    return sorted(int(p.name.split("_")[1]) for p in ITER_DIR.glob("round_*"))


def state_hash(rd):
    h = hashlib.sha256()
    base = rd / "system_state"
    for p in sorted(base.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(base)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def main():
    rs = rounds()
    # 1 — at least 2 complete rounds
    complete = all((ITER_DIR / f"round_{n:02d}" / f).exists()
                   for n in rs[:2] for f in REQUIRED_ROUND_FILES) if len(rs) >= 2 else False
    check(1, "at least 2 complete rounds with all required files",
          len(rs) >= 2 and complete, f"rounds found: {rs}")
    if len(rs) < 2:
        return finish()

    evs = {n: read_json(ITER_DIR / f"round_{n:02d}" / "evaluation.json") for n in rs}

    # 2 — machine-readable evaluation with numeric scores, variance, total
    ok2, det2 = True, []
    for n, ev in evs.items():
        for dim in DIMENSIONS:
            d = ev["dimensions"].get(dim)
            if d is None or not isinstance(d.get("score"), (int, float)):
                ok2, _ = False, det2.append(f"r{n}:{dim} missing score")
            elif dim in LLM_SCORED and "llm" in d and not isinstance(
                    d["llm"].get("variance"), (int, float)):
                ok2, _ = False, det2.append(f"r{n}:{dim} missing variance")
        if not isinstance(ev.get("total"), (int, float)):
            ok2, _ = False, det2.append(f"r{n} missing total")
    check(2, "evaluation.json: numeric per-dimension scores (+variance) and total",
          ok2, "; ".join(det2[:3]))

    # 3 — strictly increasing r1->r2, non-decreasing overall
    totals = [evs[n]["total"] for n in rs]
    ok3 = totals[1] > totals[0] and all(
        b >= a - 1e-9 for a, b in zip(totals[1:], totals[2:]))
    check(3, "total(r2) > total(r1), non-decreasing after",
          ok3, f"totals: {totals}")

    # 4 — every round differs from the previous by a real system change
    hashes = [state_hash(ITER_DIR / f"round_{n:02d}") for n in rs]
    ok4 = all(a != b for a, b in zip(hashes, hashes[1:]))
    check(4, "system_state differs between consecutive rounds (anti-faking)", ok4)

    # 5 — >=3 scenarios with every required field
    last = rs[-1]
    scen = read_json(ITER_DIR / f"round_{last:02d}" / "scenarios.json")["scenarios"]
    def full(s):
        return all((s.get(k) and (s[k].strip() if isinstance(s[k], str)
                    else all(str(x).strip() for x in s[k]))) for k in SCENARIO_FIELDS)
    ok5 = len(scen) >= 3 and all(full(s) for s in scen)
    check(5, ">=3 scenarios, each with all 10 required fields",
          ok5, f"{len(scen)} scenarios")

    # 6 — critics: concrete targeted objections (scenario id AND field)
    ok6, det6 = True, []
    for n in rs:
        for c in POLICY_CRITICS:
            p = ITER_DIR / f"round_{n:02d}" / "critic_outputs" / f"{c}.md"
            if not p.exists():
                ok6, _ = False, det6.append(f"r{n}:{c} missing")
                continue
            t = read(p)
            if not (CRITIC_HEADING_RE.search(t) and "Objection:" in t):
                ok6, _ = False, det6.append(f"r{n}:{c} not targeted")
    check(6, "critic objections name scenario id AND field", ok6, "; ".join(det6[:3]))

    # 7 — meta-critic evaluates the SYSTEM
    ok7 = True
    for n in rs:
        t = read(ITER_DIR / f"round_{n:02d}" / "meta_critique.md")
        if not (re.search(r"Gaming judgment", t)
                and re.search(r"(GENUINE|RUBRIC-GAMING)", t)
                and re.search(r"[Ww]orkflow", t) and re.search(r"[Aa]gent", t)):
            ok7 = False
    check(7, "meta-critique evaluates the agent system (incl. gaming judgment)", ok7)

    # 8 — final brief separates the five layers
    fb = read(FINAL_DIR / "final_brief.en.md") if (FINAL_DIR / "final_brief.en.md").exists() else ""
    ok8 = all(h in fb for h in BRIEF_HEADERS_EN)
    check(8, "final brief separates evidence/interpretation/assumptions/"
             "recommendations/open questions", ok8)

    # 9 — human_questions.md non-empty
    hq = FINAL_DIR / "human_questions.md"
    ok9 = hq.exists() and len(hq.read_text(encoding="utf-8")) > 300
    check(9, "human_questions.md states where human judgment is required", ok9)

    # 10 — git: one commit per round, messages name the change
    log = subprocess.run(["git", "log", "--oneline"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    ok10, det10 = True, []
    for n in rs:
        m = re.search(rf"round-{n:02d}: (.+)", log)
        if not m or len(m.group(1).strip()) < 15:
            ok10, _ = False, det10.append(f"round-{n:02d} missing/unnamed")
    check(10, "git history has a commit per round naming the change",
          ok10, "; ".join(det10))

    # 11 — bilingual deliverables exist
    pairs = [("final_brief.en.md", "final_brief.hu.md"),
             ("executive_summary.en.md", "executive_summary.hu.md"),
             ("scenarios.en.md", "scenarios.hu.md")]
    ok11 = all((FINAL_DIR / a).exists() and (FINAL_DIR / b).exists()
               and len(read(FINAL_DIR / a)) > 300 and len(read(FINAL_DIR / b)) > 300
               for a, b in pairs)
    check(11, "scenario set, final_brief, executive_summary exist in HU and EN", ok11)

    # 12 — translation parity (ids, structure, glossary, non-identity)
    ok12, det12 = True, []
    if ok11:
        scen_en = read_json(ITER_DIR / f"round_{last:02d}" / "scenarios.json")
        scen_hu = read_json(ITER_DIR / f"round_{last:02d}" / "scenarios.hu.json")
        doc_pairs = [(read(FINAL_DIR / a), read(FINAL_DIR / b)) for a, b in pairs]
        rep = translation.check(scen_en, scen_hu, doc_pairs)
        if not rep["id_sets_equal"]:
            ok12, _ = False, det12.append("scenario-id sets differ")
        if not rep["structure_equal"]:
            ok12, _ = False, det12.append("section structure differs")
        if rep["byte_identical_docs"]:
            ok12, _ = False, det12.append("HU is a byte-identical copy of EN")
        if rep["untranslated_fields"]:
            ok12, _ = False, det12.append(f"untranslated: {rep['untranslated_fields'][:3]}")
        if rep["glossary_violations"]:
            ok12, _ = False, det12.append(f"glossary: {rep['glossary_violations'][:2]}")
        hu_brief = read(FINAL_DIR / "final_brief.hu.md")
        if not all(h in hu_brief for h in BRIEF_HEADERS_HU):
            ok12, _ = False, det12.append("HU brief structure mismatch")
        tc = ITER_DIR / f"round_{last:02d}" / "critic_outputs" / "translation_checker.md"
        if not tc.exists():
            ok12, _ = False, det12.append("no translation_checker output")
    else:
        ok12 = False
    check(12, "translation_checker parity: ids, structure, glossary, non-identity",
          ok12, "; ".join(det12))

    # 13 — generator and judge providers differ
    cfg = load_config()["providers"]
    gen = os.environ.get("GENERATOR_PROVIDER", cfg["generator_default"])
    judge = os.environ.get("JUDGE_PROVIDER", cfg["judge_default"])
    check(13, "GENERATOR_PROVIDER != JUDGE_PROVIDER", gen != judge,
          f"generator={gen}, judge={judge}")

    # 14 — no core safety/evidence/critic constraint removed (anti-gaming)
    ok14, det14 = True, []
    prev_critics = None
    for n in rs:
        st = ITER_DIR / f"round_{n:02d}" / "system_state"
        critics_now = len(list((st / "agents" / "critics").glob("*.md")))
        if prev_critics is not None and critics_now < prev_critics:
            ok14, _ = False, det14.append(f"r{n}: critic removed")
        prev_critics = critics_now
        rubric = read(st / "evaluation_rubric.md")
        missing = [d for d in DIMENSIONS if d not in rubric]
        if missing:
            ok14, _ = False, det14.append(f"r{n}: rubric lost {missing}")
        for c in POLICY_CRITICS:
            spec = read(st / "agents" / "critics" / f"{c}.md")
            if "scenario id AND field" not in spec:
                ok14, _ = False, det14.append(f"r{n}: {c} concreteness rule removed")
    check(14, "no critic/evidence/disagreement constraint was removed", ok14,
          "; ".join(det14[:3]))

    # held-out qualitative checks (not visible to the improvement step)
    artifacts = load_artifacts(last)
    for name, ok, msg in holdout_checks.run_all(artifacts):
        check("H", f"held-out: {name}", ok, msg)

    return finish()


def finish():
    print()
    if FAILURES:
        print(f"VERIFY FAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("VERIFY PASSED — definition of done met.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
