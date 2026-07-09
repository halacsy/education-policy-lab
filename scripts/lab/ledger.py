"""Argument-ledger rendering (D-29 societal-discourse layer).

The ledger is rendered DETERMINISTICALLY from the validated JSON artifacts
(voice reactions, argument map, evidence grades, reciprocity responses) —
the model calls produce data, code produces the document. Used by
lab.pipeline (EN, from live/mock artifacts) and by lab.mock_backend
(HU twin built from the curated pack).
"""

HEAD = {
    "en": dict(title="# Argument ledger — round {n}",
               intro=("Societal-discourse layer output: voices REPRESENT "
                      "interests and values (they are not experts). Every "
                      "position carries an epistemic label; factual claims "
                      "inside arguments are graded by the evidence layer; "
                      "the policy brief must answer every argument cluster "
                      "(response obligation)."),
               matrix="## Stance matrix", clusters="## Argument clusters",
               recipro="## Reciprocity round",
               conditions="## Conditions register",
               stance_w={"support": "supports", "oppose": "opposes",
                         "conditional": "conditionally supports",
                         "no_position": "no position"},
               label_w={"documented": "documented", "value_modeled":
                        "value-modeled", "no_position": "no position"},
               cond="Condition", raised="raised by", outcome="outcome"),
    "hu": dict(title="# Érv-főkönyv — {n}. kör",
               intro=("A társadalmi diskurzus-réteg kimenete: a hangok "
                      "érdekeket és értékeket KÉPVISELNEK (nem szakértők). "
                      "Minden álláspont episztemikus címkét visel; az érvek "
                      "ténybeli állításait az evidencia-réteg fokozatolja; a "
                      "szakpolitikai összefoglaló minden érvklaszterre "
                      "köteles válaszolni (válaszkötelezettség)."),
               matrix="## Álláspont-mátrix", clusters="## Érvklaszterek",
               recipro="## Reciprocitás-kör",
               conditions="## Feltétel-regiszter",
               stance_w={"support": "támogatja", "oppose": "ellenzi",
                         "conditional": "feltételesen támogatja",
                         "no_position": "nincs álláspontja"},
               label_w={"documented": "dokumentált álláspont",
                        "value_modeled": "értékekből modellezett",
                        "no_position": "nincs álláspont"},
               cond="Feltétel", raised="felvetette", outcome="kimenetel"),
}


def render_ledger(n, voices, clusters, grades, responses, lang):
    """voices: {name: voice-json}; clusters: [cluster dict]; grades:
    {cluster_id: grade line}; responses: {name: response-json or None}.
    All text inside the data is already in the target language."""
    H = HEAD[lang]
    L = [H["title"].format(n=n), "", H["intro"], "", H["matrix"], ""]
    sids = sorted({r["scenario"] for v in voices.values()
                   for r in v["reactions"]})
    for sid in sids:
        L.append(f"### {sid}")
        for name, v in voices.items():
            r = next((x for x in v["reactions"] if x["scenario"] == sid), None)
            if r is None:
                continue
            tag = H["label_w"][r["label"]]
            src = r.get("source") or r.get("basis") or ""
            if src:
                tag += f": {src}"
            line = (f"- **{name}** — {H['stance_w'][r['stance']]} [{tag}] — "
                    f"{r['argument']}")
            if r.get("condition_to_change"):
                line += f" {H['cond']}: {r['condition_to_change']}"
            L.append(line)
        L.append("")
    L += [H["clusters"], ""]
    for c in clusters:
        grade = grades.get(c["id"])
        gtxt = f" {grade}" if grade else ""
        L.append(f"- **{c['id']}** ({c['scenario']}, {c['kind']}, "
                 f"{c['side']}): {c['claim']}{gtxt} — {H['raised']}: "
                 f"{', '.join(c['raised_by'])}")
    L.append("")
    if any(responses.values()):
        L += [H["recipro"], ""]
        for name, resp in responses.items():
            if not resp:
                continue
            for item in resp["responses"]:
                L.append(f"- **{name}** → {item['cluster']}: "
                         f"{item['response']} ({H['outcome']}: "
                         f"{item['outcome']})")
        L.append("")
    L += [H["conditions"], ""]
    for name, v in voices.items():
        for r in v["reactions"]:
            if r.get("condition_to_change") and r["stance"] != "no_position":
                L.append(f"- {name} ({r['scenario']}): "
                         f"{r['condition_to_change']}")
    return "\n".join(L) + "\n"


def grade_lines(text):
    """Parse the evidence layer's grading output into {cluster_id: line}.
    Lenient about list/bold prefixes ('- A3:', '**A3**:', 'A3 :')."""
    import re
    out = {}
    for line in text.splitlines():
        m = re.match(r"^[\s\-\*]*(A\d+)\**\s*:\s*(.*)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out
