"""Per-topic time / token / cost metering (D-35, sprint deliverable 4).

Transparency principle (owner): what a problem's processing cost — wall
clock, tokens, estimated USD — is part of the PUBLIC record (final report
+ website), not an internal metric.

Sources of truth:
- each round's round_log.json gets `wall_clock_s`, per-round `tokens`
  (llm.token_stats(since=round-start)) and a `usd_estimate` written by the
  iteration loop right after evaluation;
- the topic-level report aggregates the era rounds' logs into
  final/cost_report.{json,md}.

Honesty rules: prices come from config `pricing.usd_per_mtok` (a
configurable estimate table); a model missing from it is listed as
UNPRICED, never silently costed at zero; CLI/subscription backends report
no per-call usage, so their calls are counted as unmetered.
"""
import re

from . import llm, topic
from .util import final_dir, load_config, read_json, round_dir, write, write_json

_LABEL_RE = re.compile(r"\[([^\]]+)\]$")


def _price_table():
    return load_config().get("pricing", {}).get("usd_per_mtok", {})


def _model_of(label):
    """'task [backend:model]' -> model; None for mock/unlabelled entries."""
    m = _LABEL_RE.search(label)
    if not m or ":" not in m.group(1):
        return None
    return m.group(1).split(":", 1)[1]


def usd_estimate(tokens):
    """Cost estimate for one llm.token_stats() dict: per-model token sums
    priced from the config table. Returns {total_usd, by_model, unpriced}."""
    prices = _price_table()
    by_model = {}
    for label, v in tokens.get("by_task_backend", {}).items():
        model = _model_of(label)
        if not model:
            continue
        cur = by_model.setdefault(model, {"input_tokens": 0, "output_tokens": 0})
        cur["input_tokens"] += v.get("input_tokens") or 0
        cur["output_tokens"] += v.get("output_tokens") or 0
    total = 0.0
    unpriced = []
    for model, v in by_model.items():
        p = prices.get(model)
        if p is None:
            unpriced.append(model)
            v["usd"] = None
            continue
        v["usd"] = round((v["input_tokens"] * p[0]
                          + v["output_tokens"] * p[1]) / 1e6, 4)
        total += v["usd"]
    return {"total_usd": round(total, 2), "by_model": by_model,
            "unpriced_models": sorted(unpriced)}


def update_round_log(rd, since_mark, wall_clock_s):
    """Stamp one round's log with its own wall clock, its own token usage
    (generation + judging + meta, attributed via the CALL_LOG marker) and
    the USD estimate. Overwrites the tokens run_round wrote mid-round
    (those were cumulative-from-process-start)."""
    path = rd / "round_log.json"
    log = read_json(path) if path.exists() else {}
    tokens = llm.token_stats(since=since_mark)
    log["wall_clock_s"] = round(wall_clock_s, 1)
    log["tokens"] = tokens
    log["usd_estimate"] = usd_estimate(tokens)
    write_json(path, log)
    return log


def collect_topic_stats():
    """Aggregate the current topic's era rounds into one stats dict."""
    T = topic.current()
    era = T.era_start_round
    rounds = []
    if T.iter_dir.exists():
        rounds = sorted(int(p.name.split("_")[1])
                        for p in T.iter_dir.glob("round_*")
                        if int(p.name.split("_")[1]) >= era)
    total_in = total_out = metered = unmetered = 0
    wall = 0.0
    wall_known = True
    by_model = {}
    per_round = []
    for n in rounds:
        p = round_dir(n) / "round_log.json"
        if not p.exists():
            continue
        log = read_json(p)
        tokens = log.get("tokens") or {}
        total_in += tokens.get("total_input_tokens") or 0
        total_out += tokens.get("total_output_tokens") or 0
        metered += tokens.get("metered_calls") or 0
        unmetered += tokens.get("unmetered_calls") or 0
        w = log.get("wall_clock_s")
        if w is None:
            wall_known = False
        else:
            wall += w
        est = log.get("usd_estimate") or usd_estimate(tokens)
        for model, v in est.get("by_model", {}).items():
            cur = by_model.setdefault(
                model, {"input_tokens": 0, "output_tokens": 0, "usd": 0.0})
            cur["input_tokens"] += v.get("input_tokens") or 0
            cur["output_tokens"] += v.get("output_tokens") or 0
            if v.get("usd") is not None and cur["usd"] is not None:
                cur["usd"] = round(cur["usd"] + v["usd"], 4)
            else:
                cur["usd"] = None
        per_round.append({
            "round": n,
            "wall_clock_s": w,
            "total_tokens": tokens.get("total_tokens"),
            "usd": est.get("total_usd"),
        })
    prices = _price_table()
    total_usd = round(sum(v["usd"] for v in by_model.values()
                          if v.get("usd") is not None), 2)
    unpriced = sorted(m for m in by_model if m not in prices)
    return {
        "topic": T.slug,
        # False when no round in the era carries metered usage (e.g. the
        # rounds ran as interrupted/resumed processes before per-round
        # metering landed) — the report must say "unknown", not "$0"
        "has_data": (total_in + total_out) > 0 or metered > 0,
        "era_start_round": era,
        "rounds": per_round,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "metered_calls": metered,
        "unmetered_calls": unmetered,
        "wall_clock_s": round(wall, 1),
        "wall_clock_known_for_all_rounds": wall_known,
        "by_model": by_model,
        "unpriced_models": unpriced,
        "total_usd": total_usd,
    }


def _fmt_dur(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}ó {m}p {s}mp" if h else f"{m}p {s}mp"


def render_report_md(stats):
    """Hungarian, public-facing cost report (transparency section source)."""
    lines = [
        "# Költség- és időjelentés",
        "",
        f"Téma: `{stats['topic']}` — az átláthatósági elv része: ennyi időbe "
        "és ennyibe került ennek a problémának a feldolgozása "
        f"(a(z) {stats['era_start_round']}. körtől számított érában).",
        "",
    ]
    if not stats["has_data"]:
        lines += [
            "**Ennek az érának a köreihez nem áll rendelkezésre mért "
            "token-adat** (a futások a körönkénti mérés bevezetése előtt, "
            "megszakításokkal/folytatásokkal készültek). A költség itt nem "
            "ismert — NEM nulla. A következő teljes kör már mért adatot "
            "rögzít.",
            "",
        ]
        return "\n".join(lines)
    lines += [
        f"- **Falióra-idő (körök összesen):** {_fmt_dur(stats['wall_clock_s'])}"
        + ("" if stats["wall_clock_known_for_all_rounds"] else
           " (nem minden körnél ismert — alsó becslés)"),
        f"- **Tokenek:** {stats['total_tokens']:,} "
        f"(bemenet: {stats['total_input_tokens']:,}, "
        f"kimenet: {stats['total_output_tokens']:,})",
        f"- **Becsült költség:** ${stats['total_usd']:.2f} USD "
        "(konfigurálható ártáblából — config/system_config.json pricing)",
        f"- **Mért / nem mért hívások:** {stats['metered_calls']} / "
        f"{stats['unmetered_calls']} (a CLI/előfizetéses backendek hívásonként "
        "nem mérnek tokent — az ő költségük itt nem szerepel)",
        "",
        "## Modellenként",
        "",
        "| modell | bemeneti token | kimeneti token | becsült USD |",
        "|---|---|---|---|",
    ]
    for model, v in sorted(stats["by_model"].items()):
        usd = f"${v['usd']:.2f}" if v.get("usd") is not None else "nincs ár"
        lines.append(f"| {model} | {v['input_tokens']:,} | "
                     f"{v['output_tokens']:,} | {usd} |")
    if stats["unpriced_models"]:
        lines += ["", "Ártábla nélküli modellek (a fenti összegben NEM "
                  "szerepelnek): " + ", ".join(stats["unpriced_models"])]
    lines += ["", "## Körönként", "",
              "| kör | idő | token | becsült USD |", "|---|---|---|---|"]
    for r in stats["rounds"]:
        w = _fmt_dur(r["wall_clock_s"]) if r["wall_clock_s"] is not None else "?"
        t = f"{r['total_tokens']:,}" if r["total_tokens"] is not None else "?"
        u = f"${r['usd']:.2f}" if r["usd"] is not None else "?"
        lines.append(f"| {r['round']} | {w} | {t} | {u} |")
    lines += ["",
              "A számok forrása a körök `round_log.json`-ja (audit-nyom a "
              "repóban); az USD-érték becslés, nem számla."]
    return "\n".join(lines) + "\n"


def write_cost_report():
    """Write the topic's final/cost_report.{json,md}; returns the stats."""
    stats = collect_topic_stats()
    fdir = final_dir()
    fdir.mkdir(parents=True, exist_ok=True)
    write_json(fdir / "cost_report.json", stats)
    write(fdir / "cost_report.md", render_report_md(stats))
    return stats
