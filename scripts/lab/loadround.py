"""Load a completed round folder back into the artifacts dict used by
evaluation, holdout checks and verification.

New-era rounds (D-34, round 8+) store ONE bilingual scenarios.json; the
legacy EN/HU views are projected deterministically (render.scenario_view),
exactly the way the pipeline itself derives them."""
from . import render, translation
from .util import read, read_json, round_dir


def load_scenario_views(rd):
    """(scen_en, scen_hu) legacy-shape views from either era's artifacts."""
    scen = read_json(rd / "scenarios.json")
    if scen.get("scenarios") and \
            isinstance(scen["scenarios"][0].get("title"), dict):
        return (render.scenario_view(scen, "en"),
                render.scenario_view(scen, "hu"))
    return scen, read_json(rd / "scenarios.hu.json")


def load_artifacts(n):
    rd = round_dir(n)
    scen_en, scen_hu = load_scenario_views(rd)
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
