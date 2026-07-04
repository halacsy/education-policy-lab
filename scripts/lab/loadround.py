"""Load a completed round folder back into the artifacts dict used by
evaluation, holdout checks and verification."""
from . import translation
from .util import read, read_json, round_dir


def load_artifacts(n):
    rd = round_dir(n)
    scen_en = read_json(rd / "scenarios.json")
    scen_hu = read_json(rd / "scenarios.hu.json")
    scen_en_md = read(rd / "scenarios.en.md")
    scen_hu_md = read(rd / "scenarios.hu.md")
    brief_en = read(rd / "brief.en.md")
    brief_hu = read(rd / "brief.hu.md")
    critics = {p.stem: read(p) for p in sorted((rd / "critic_outputs").glob("*.md"))
               if p.stem != "translation_checker"}
    experts = {p.stem: read(p) for p in sorted((rd / "expert_outputs").glob("*.md"))}
    log = read_json(rd / "round_log.json") if (rd / "round_log.json").exists() else {}
    tr = translation.check(scen_en, scen_hu,
                           [(scen_en_md, scen_hu_md), (brief_en, brief_hu)])
    meta_path = rd / "meta_critique.md"
    return {
        "round_dir": rd, "experts": experts,
        "scenarios_en": scen_en, "scenarios_hu": scen_hu,
        "scenarios_en_md": scen_en_md, "scenarios_hu_md": scen_hu_md,
        "synthesis": read(rd / "synthesis.md"),
        "rejected": read(rd / "rejected_framings.md"),
        "brief_en": brief_en, "brief_hu": brief_hu,
        "critics": critics, "translation": tr,
        "meta": read(meta_path) if meta_path.exists() else "",
        "fallbacks": log.get("fallbacks", []),
    }
