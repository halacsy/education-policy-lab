"""Deterministic HU↔EN parity checks (the translation_checker's core).

Never LLM-only (judge reliability degrades across languages): scenario-id set
parity, section-structure parity, glossary conformance, non-identity, and a
back-translation key-term check. Residual nuance is flagged for a human.
"""
import re

from .util import DOCS_DIR, read

FIELD_KEYS = ["goal", "mechanism", "evidence_status", "assumptions",
              "expected_benefits", "equity_impact", "cost_categories",
              "implementation_steps", "political_risks", "uncertainties"]

# Glossary terms mechanically checkable by substring (lowercased). Pairs whose
# EN side is too generic for substring matching are excluded from the
# automated sweep and left to the human-review flag.
CHECKABLE = [
    ("early selection", "korai szelekció"),
    ("comprehensive school", "egységes alapiskola"),
    ("equity", "méltányosság"),
    ("social mobility", "társadalmi mobilitás"),
    ("school choice", "iskolaválasztás"),
    ("phase-", "fokozatos"),          # phase-out/phase-down family
    ("teacher shortage", "pedagógushiány"),
]


def load_glossary_pairs():
    """Parse the EN↔HU table from docs/glossary.md."""
    pairs = []
    for line in read(DOCS_DIR / "glossary.md").splitlines():
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
    for en_term, hu_term in CHECKABLE:
        if en_term in en_all and hu_term not in hu_all:
            violations.append(f"EN '{en_term}' present but HU '{hu_term}' missing")
        if hu_term in hu_all and en_term not in en_all:
            violations.append(f"HU '{hu_term}' present but EN '{en_term}' missing (back-translation)")
    report["glossary_violations"] = violations

    report["ok"] = (report["id_sets_equal"] and report["structure_equal"]
                    and not report["byte_identical_docs"]
                    and not identical_fields and not violations)
    return report


def render_report(report, round_n):
    lines = [f"# Critique: translation_checker — round {round_n}", "",
             "Deterministic HU↔EN parity checks (glossary: docs/glossary.md).", ""]
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
