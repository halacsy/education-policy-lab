"""Held-out qualitative checks (anti-Goodhart).

NOT visible to the improvement step: lab/improve.py never imports this
module, so no change can be selected to satisfy these checks. They run only
at verification time (scripts/verify.py) and gate the definition of done.
Each check returns (ok, message).
"""
import re


def check_no_single_answer(brief_en):
    """The brief must not crown one scenario as THE answer."""
    m = re.search(r"## Recommendations(.*?)(\n## |\Z)", brief_en, re.S)
    body = m.group(1).lower() if m else brief_en.lower()
    bad = re.search(r"(the government should (adopt|choose|implement) s\d\b|"
                    r"scenario s\d is the (best|right|correct) (choice|answer)|"
                    r"we recommend (adopting |choosing )?s\d\b(?! and))", body)
    return (not bad,
            "recommendations crown a single scenario as the answer" if bad
            else "recommendations preserve the option space")


def check_dissent_has_reasons(synthesis):
    """Dissent must carry rationale, not just labels."""
    m = re.search(r"## Disagreement map(.*?)(\n## |\Z)", synthesis, re.S)
    body = m.group(1) if m else ""
    entries = len(re.findall(r"^- \*\*", body, re.M))
    reasons = len(re.findall(r"(Why:|Rationale:|because)", body))
    ok = entries >= 3 and reasons >= entries * 0.7
    return (ok, f"disagreement map: {entries} entries, {reasons} rationales")


def check_hu_not_transliteration(scen_hu_md):
    """HU text must read as Hungarian, not word-order-preserving English."""
    hu_markers = len(re.findall(
        r"\b(és|hogy|nem|az|egy|amely|kell|közötti|szerint|évfolyam)\b",
        scen_hu_md.lower()))
    en_leak = len(re.findall(
        r"\b(the|and|should|would|school system|therefore)\b", scen_hu_md))
    ok = hu_markers > 30 and en_leak < hu_markers / 4
    return (ok, f"HU quality markers={hu_markers}, EN leakage={en_leak}")


def check_uncertainty_not_boilerplate(scen_en_json):
    """Uncertainty items must be scenario-specific, not one recycled phrase."""
    items = [u for s in scen_en_json["scenarios"] for u in s["uncertainties"]]
    unique = len({u[:60] for u in items})
    ok = len(items) >= 6 and unique >= len(items) * 0.8
    return (ok, f"{unique}/{len(items)} distinct uncertainty items")


def check_critics_disagree_with_output(critics_texts):
    """Critics must actually push back (contain negative/corrective language)."""
    pushback = sum(1 for t in critics_texts.values() if re.search(
        r"(unsupported|missing|contradict|understate|overstate|lack|fails?|"
        r"do(es)? not|no evidence|without|rather than|misalign|foreclos|"
        r"not (shown|verified|evidence|mitigated|decision-ready)|"
        r"asserted, not)", t, re.I))
    ok = pushback >= max(1, int(len(critics_texts) * 0.75))
    return (ok, f"{pushback}/{len(critics_texts)} critics contain real pushback")


def run_all(artifacts):
    """artifacts: dict with brief_en, synthesis, scenarios_hu_md,
    scenarios_en(json), critics(dict). Returns list of (name, ok, msg)."""
    return [
        ("no_single_answer", *check_no_single_answer(artifacts["brief_en"])),
        ("dissent_has_reasons", *check_dissent_has_reasons(artifacts["synthesis"])),
        ("hu_not_transliteration", *check_hu_not_transliteration(artifacts["scenarios_hu_md"])),
        ("uncertainty_not_boilerplate", *check_uncertainty_not_boilerplate(artifacts["scenarios_en"])),
        ("critics_disagree", *check_critics_disagree_with_output(artifacts["critics"])),
    ]
