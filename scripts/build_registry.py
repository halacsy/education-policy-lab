#!/usr/bin/env python3
"""Compile knowledge/sources/*.md into knowledge/registry.json.

The per-source markdown files are the human-reviewable source of truth
(owner decision, issue #2): one file per source, facts as `### <fact_id>`
blocks. This script regenerates the machine-readable index the code loads;
run it after editing any source file (CI checks freshness).

    python scripts/build_registry.py          # rebuild registry.json
    python scripts/build_registry.py --check  # exit 1 if registry is stale

Standard library only.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "knowledge" / "sources"
REGISTRY = ROOT / "knowledge" / "registry.json"

VALID_EVIDENCE = {"strong", "moderate", "weak", "contested"}

META = {
    "description": ("Curated source registry — GENERATED from "
                    "knowledge/sources/*.md by scripts/build_registry.py. "
                    "Edit the per-source files, not this index."),
    "governance": ("New facts and sources enter as agent proposals "
                   "(knowledge/proposals/) and require human approval via PR "
                   "review before entering knowledge/sources/. Evidence "
                   "grades follow templates/evaluation_rubric.md."),
    "library": ("knowledge/library/ holds full reference documents (papers, "
                "reports, data tables); a source file's library_doc field "
                "points at its document once ingested."),
}


def parse_source_file(path):
    text = path.read_text(encoding="utf-8")
    src = re.search(r"^# Source:\s*(.+)$", text, re.M)
    lib = re.search(r"^library_doc:\s*(\S+)", text, re.M)
    if not src:
        raise ValueError(f"{path.name}: missing '# Source:' header")
    source_name = src.group(1).strip()
    library_doc = lib.group(1) if lib and lib.group(1) != "none" else None
    facts = {}
    for m in re.finditer(
            r"^### (\w+)\n((?:- .+\n?)+)", text, re.M):
        fid, body = m.group(1), m.group(2)
        fields = dict(re.findall(r"^- (\w+):\s*(.+)$", body, re.M))
        missing = {"evidence", "used_by", "en", "hu"} - set(fields)
        if missing:
            raise ValueError(f"{path.name}:{fid}: missing fields {missing}")
        if fields["evidence"] not in VALID_EVIDENCE:
            raise ValueError(f"{path.name}:{fid}: bad evidence grade "
                             f"{fields['evidence']!r}")
        facts[fid] = {
            "en": fields["en"], "hu": fields["hu"],
            "evidence": fields["evidence"], "source": source_name,
            "used_by": [u.strip() for u in fields["used_by"].split(",") if u.strip()],
        }
        if library_doc:
            facts[fid]["library_doc"] = library_doc
        # optional: context/transferability note (D-31 B1) — for facts drawn
        # from a different country/system, what condition Hungary may lack
        if "transferability_en" in fields or "transferability_hu" in fields:
            missing_t = {"transferability_en", "transferability_hu"} - set(fields)
            if missing_t:
                raise ValueError(f"{path.name}:{fid}: has one of "
                                 f"transferability_en/hu but not both "
                                 f"(missing {missing_t})")
            facts[fid]["transferability_en"] = fields["transferability_en"]
            facts[fid]["transferability_hu"] = fields["transferability_hu"]
    return facts


def build():
    facts = {}
    for path in sorted(SRC_DIR.glob("*.md")):
        for fid, f in parse_source_file(path).items():
            if fid in facts:
                raise ValueError(f"duplicate fact id {fid!r} in {path.name}")
            facts[fid] = f
    return {"_meta": META, "facts": facts}


def main():
    reg = build()
    rendered = json.dumps(reg, ensure_ascii=False, indent=2) + "\n"
    if "--check" in sys.argv:
        current = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else ""
        if current != rendered:
            print("STALE: knowledge/registry.json does not match "
                  "knowledge/sources/ — run scripts/build_registry.py")
            return 1
        print(f"registry fresh ({len(reg['facts'])} facts)")
        return 0
    REGISTRY.write_text(rendered, encoding="utf-8")
    print(f"wrote {REGISTRY} ({len(reg['facts'])} facts from "
          f"{len(list(SRC_DIR.glob('*.md')))} source files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
