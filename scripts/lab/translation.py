"""Deterministic HU↔EN parity checks (the translation_checker's core).

Never LLM-only (judge reliability degrades across languages): scenario-id set
parity, section-structure parity, glossary conformance, non-identity, and a
back-translation key-term check. Residual nuance is flagged for a human.
"""
import re

from . import topic

FIELD_KEYS = ["goal", "mechanism", "evidence_status", "assumptions",
              "expected_benefits", "equity_impact", "cost_categories",
              "implementation_steps", "political_risks", "uncertainties"]


def checkable_pairs():
    """Glossary terms mechanically checkable by substring (lowercased),
    parsed from the topic glossary's '## Machine-checked key pairs' section
    (per-topic since D-35 — the pairs are question-specific). Line format:
    '- <en> = <hu>'; alternative EN phrasings separated by ' / ' (any one
    counts as present — live generation legitimately varies phrasing, e.g.
    'school choice' as 'choice and catchment redesign', without that being
    a translation defect); a trailing hyphen acts as a prefix ('phase-').
    Pairs whose EN side is too generic for substring matching stay out of
    the section and are left to the human-review flag."""
    text = topic.current().glossary()
    m = re.search(r"^## Machine-checked key pairs\s*$(.*?)(?=^## |\Z)",
                  text, re.M | re.S)
    pairs = []
    for line in (m.group(1) if m else "").splitlines():
        pm = re.match(r"^- (.+?) = (.+?)\s*$", line)
        if pm:
            en_alts = tuple(a.strip() for a in pm.group(1).split(" / "))
            pairs.append((en_alts, pm.group(2).strip()))
    return pairs


def load_glossary_pairs():
    """Parse the EN↔HU table from the topic glossary (topics/<slug>/glossary.md)."""
    pairs = []
    for line in topic.current().glossary().splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if m and m.group(1) not in ("English", "---------", "English "):
            en, hu = m.group(1).strip(), m.group(2).strip()
            if en and hu and not set(en) <= set("-: "):
                pairs.append((en, hu))
    return pairs


def structure_of(scenarios):
    """(id, per-field item counts) signature of a scenarios JSON dict."""
    sig = {}
    for s in scenarios["scenarios"]:
        sig[s["id"]] = tuple(
            len(s[k]) if isinstance(s[k], list) else 1 for k in FIELD_KEYS)
    return sig


def check(en_json, hu_json, doc_pairs):
    """doc_pairs: list of (en_text, hu_text) whole-document pairs to check
    for non-identity and glossary conformance (scenarios md, brief, ...)."""
    report = {}
    en_ids = {s["id"] for s in en_json["scenarios"]}
    hu_ids = {s["id"] for s in hu_json["scenarios"]}
    report["id_sets_equal"] = en_ids == hu_ids
    report["en_ids"], report["hu_ids"] = sorted(en_ids), sorted(hu_ids)
    report["structure_equal"] = structure_of(en_json) == structure_of(hu_json)

    report["byte_identical_docs"] = [
        i for i, (en, hu) in enumerate(doc_pairs) if en.strip() == hu.strip()]

    # per-scenario identity check (untranslated copy of any field)
    hu_by_id = {s["id"]: s for s in hu_json["scenarios"]}
    identical_fields = []
    for s in en_json["scenarios"]:
        h = hu_by_id.get(s["id"])
        if not h:
            continue
        for k in FIELD_KEYS:
            if s[k] == h[k]:
                identical_fields.append(f"{s['id']}.{k}")
    report["untranslated_fields"] = identical_fields

    # glossary conformance + back-translation key-term check
    en_all = "\n".join(en for en, _ in doc_pairs).lower()
    hu_all = "\n".join(hu for _, hu in doc_pairs).lower()
    violations = []
    for en_terms, hu_term in checkable_pairs():
        en_present = any(t in en_all for t in en_terms)
        if en_present and hu_term not in hu_all:
            violations.append(f"EN '{en_terms[0]}' present but HU '{hu_term}' missing")
        if hu_term in hu_all and not en_present:
            violations.append(f"HU '{hu_term}' present but EN '{en_terms[0]}' missing (back-translation)")
    report["glossary_violations"] = violations

    report["ok"] = (report["id_sets_equal"] and report["structure_equal"]
                    and not report["byte_identical_docs"]
                    and not identical_fields and not violations)
    return report


def render_report(report, round_n):
    lines = [f"# Critique: translation_checker — round {round_n}", "",
             "Deterministic HU↔EN parity checks (glossary: the topic glossary (topics/<slug>/glossary.md)).", ""]
    lines.append(f"- Scenario-id sets equal: {report['id_sets_equal']} "
                 f"(EN {report['en_ids']}, HU {report['hu_ids']})")
    lines.append(f"- Section structure equal: {report['structure_equal']}")
    lines.append(f"- Byte-identical document pairs: "
                 f"{report['byte_identical_docs'] or 'none'}")
    lines.append(f"- Untranslated (identical) fields: "
                 f"{report['untranslated_fields'] or 'none'}")
    if report["glossary_violations"]:
        lines.append("- Glossary/back-translation violations:")
        lines += [f"  - {v}" for v in report["glossary_violations"]]
    else:
        lines.append("- Glossary + back-translation key-term checks: no violations")
    lines += ["",
              "Residual uncertainty (register, connotation — e.g. the "
              "historical load of 'egységes alapiskola') cannot be verified "
              "mechanically and is flagged for native-speaker review in "
              "human_questions.md."]
    return "\n".join(lines) + "\n"
