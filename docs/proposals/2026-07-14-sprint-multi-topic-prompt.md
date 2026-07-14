# Sprint-prompt: multi-topic — több probléma, egy expert hub

> Ezt a promptot add oda a sprintet végrehajtó agensnek. Owner: Halácsy
> Péter; a sprint terméke publikus (GitHub + Pages). A repo CLAUDE.md-je a
> kanonikus kontextus — olvasd el először, ez a dokumentum arra épül.

## A sprint célja (owner, 2026-07-14)

Több szakpolitikai problémát lehessen ugyanezzel a rendszerrel és
ugyanezzel az expert hubbal kidolgoztatni, és **meg tudjuk mutatni, mit tud
ez az egész**: mennyi időbe és mennyi tokenbe (forintba) kerül egy új
probléma feldolgozása, és a weboldalon minden téma böngészhető legyen.
Semmi probléma-specifikus nem maradhat bedrótozva a kódban.

## A rendszer bemenete: a probléma-lap (owner-döntés)

A bemenet NEM egy kérdés, hanem egy **leírt probléma vagy lehetőség**.
Rossz bemenet: „Mit kezdjen Magyarország a korai szelekcióval és a
hat-/nyolcosztályos gimnáziummal?" Jó bemenet:

> „Magyarország iskolarendszerének egyik legvitatottabb szerkezeti eleme a
> 10–12 éves kori szelekció. Arra szeretnénk választ találni, hogy milyen
> problémákat old meg, milyen új problémákat hoz létre, és milyen
> alternatívák képzelhetők el."

Formálisan (per-topic config, kétnyelvű — a schemákhoz a `lab/schemas.py`
konvenciói):

```
problem_brief:
  slug:               "korai-szelekcio"        # könyvtár, URL, git-hivatkozás
  title: {hu, en}                              # rövid cím a weboldalra
  problem_statement: {hu, en}                  # 1-3 bekezdés: helyzet + feszültség
  learning_goals: [{hu, en}, ...]              # 2-4 explicit tanulási cél
  scope: {hu, en}                              # mi van benne / kifejezetten kívül
  seed_sources: [...]                          # opcionális; registry-be CSAK a D-24 kapun át
```

**Intake-lépés emberi kapuval**: ha a beadott szöveg alul-specifikált
(csupasz kérdés), a rendszer maga fogalmazza meg belőle a teljes
probléma-lap-tervezetet (strukturált hívás), és az ember hagyja jóvá /
szerkeszti, mielőtt bármelyik kör elindul. A jóváhagyott lap a topic
configjába fagy.

A megoldási javaslatokat (2–5 forgatókönyv) NEM a bemenet adja: a #21-es
issue mechanizmusa szerint az 1. kör derivája a szakértői elemzésből,
emberi jóváhagyással, és onnantól stabil id-kkel működik minden, mint most.

## Szállítandók

### 1. Probléma-lap intake (bemenet)

- Per-topic config (`topics/<slug>/topic.json` vagy hasonló) a fenti
  schemával; a `config/system_config.json`-ból a `policy_question` ide
  költözik.
- `scripts/new_topic.py` (vagy `--init-topic`): beadott szabad szövegből
  strukturált probléma-lap-tervezet + emberi jóváhagyási pont (a D-24
  proposal-mintájára: fájl + PR vagy explicit confirm).
- Acceptance: a meglévő gimnázium-kérdés probléma-lapja visszamenőleg
  elkészül (a fenti owner-példa szövegével).

### 2. Emergens keretezés (#21 — előfeltétel, ott a részletes terv)

- 1. köri keretező lépés: a szakértői digestből 2–5 megoldási keret
  (strukturált, kétnyelvű: id, cím, scope, elvetett keretek indoklással),
  emberi jóváhagyás, majd a topic configjába fagy.
- A `pipeline.SCENARIO_ANCHORS` hardkód törlődik; a validátorok a topic
  configból kapják az id-halmazt (2–5, nem fixen 4!).
- Acceptance: az új tesztkérdés keretei a szakértői válaszokból születnek,
  nem kézzel írottak.

### 3. Multi-topic plumbing (#18 — ott a felmérés; a másik agens
`refactor/deliberation-phase-b` branchével koordinálj, NE duplikálj)

- `outputs/topics/<slug>/{iterations,final}/`; `--topic` kapcsoló a
  scriptekben (`run_iteration_loop`, `verify`, site-builderek).
- **Per-topic állapot** — ez a felmérésből még hiányzik, kötelező:
  - `agents/memory/` topiconként (a memória kérdés-specifikus!),
  - az improvement-direktívák topiconként (a közös agent-spec fájlokhoz
    per-topic overlay/direktíva-réteg kell — egy topic tanulsága nem
    szivároghat át csendben egy másikba),
  - `evaluation.era_start_round` és az attempts_log topiconként.
- **Git egyidejű topicokkal**: a kör-commit ma `git add -A` (CLAUDE.md
  gotcha!) — ez több párhuzamos topicnál keresztbe commitolna. Megoldás:
  a kör-commit csak a saját topic-útvonalait + a topic-overlay állapotát
  addolja; VAGY topiconként git worktree. Döntsd el, dokumentáld
  decision-log-bejegyzésként.
- Probléma-specifikus hardkódok kigyomlálása (lista a #21-ben):
  `render.py` BRIEF_TITLE → topic configból; `translation.py` CHECKABLE +
  `docs/glossary.md` → per-topic glossary; expert-roster per-topic szűrés
  (#18 „vegyes" kategória); diskurzus-archetípusok felülvizsgálata.

### 4. Mérés: idő + token + költség kérdésenként

- A `llm.token_stats()` már körönként gyűjt; kell: topic-szintű aggregátum
  (összes kör), wall-clock idő, és USD-becslés (modellenkénti árakból,
  konfigurálható ártáblával).
- Kerüljön a final reportba ÉS a weboldalra (átláthatósági szekció:
  „ennyi időbe és ennyibe került ennek a problémának a feldolgozása") —
  ez a projekt átláthatósági elvének része, nem belső metrika.

### 5. Weboldal: téma-böngésző

- `site/index.html` → belépő oldal, ami a témákat listázza (cím,
  probléma-lap kivonat, állapot, költség/idő), témánként saját
  explorer/brief oldal (`site/topics/<slug>/…` vagy query-alapú — döntsd
  el a Pages-korlátok szerint).
- A mostani egy-kérdéses tartalom az első téma lapjává válik; a „hogyan
  működik" általános leírás marad a belépő oldalon.

### 6. Acceptance: MÁSODIK probléma end-to-end

- Futtasd végig az új tesztkérdést (owner-példa): **„A kistelepülések
  elnéptelenedése mellett mit kezdjünk a kisiskolákkal?"** — probléma-lap
  intake → emergens keretek (human gate) → teljes kör(ök) → publikált
  téma-oldal.
- Jelentsd: wall-clock, token, becsült USD; a keretek tényleg a szakértői
  válaszokból jöttek-e; a gimnázium-téma futása közben semmi nem tört el
  (regressziómentesség: verify zöld mindkét topicra).

## Kemény szabályok (nem alku tárgya)

- CLAUDE.md ground rules: cross-family generator≠judge; one documented
  change per round; verify nem gyengülhet (scope-olás ≠ gyengítés, de
  minden checknek maradnia kell ekvivalens vagy szigorúbb formában);
  D-24 human gate a tudásbevitelre; D-04: ezt a sprintet NEM szabad egy
  kör-változtatásba passzírozni.
- A kétnyelvű strukturált hívások token-budgetje ~2–3× az egynyelvűének;
  truncation terminális; nagy schemák `$defs`/`$ref`-fel (Anthropic-only —
  a Gemini-sanitizer nem oldja fel a refeket). Részletek: D-34 bejegyzés.
- Minden user-facing szöveg magyarul, kód/commit angolul. A repo publikus:
  soha semmi kulcs vagy személyes adat.
- Taskonként haladj, minden lépés után zöld `run_mock_sprint.py`; élő
  futás előtt egyeztess költségkeretet az ownerrel.

## Nem célja a sprintnek

- Phase 3 (#20: evaluation/verify a JSON-mezőkön, bilingual_parity) — csak
  ha egy szállítandó kikényszeríti.
- Új agens-típusok, új diskurzus-mechanika, D-31 Phase B elemek.
- A meglévő gimnázium-téma újrafuttatása (az archív éra zárva; a round 8
  az érvényes állapot).

## Kontextus-mutatók

- Döntésnapló: D-34 (strukturált kétnyelvű ágensek), D-24 (human gate),
  D-04 (one change per round), D-29/D-32 (diskurzus).
- Issues: #21 (emergens keretezés — előfeltétel), #18 (multi-topic
  felmérés + a másik agens munkája), #14 (új kérdés-jelöltek), #20
  (Phase 3, nem e sprint része).
- Branch: `refactor/deliberation-phase-b` (másik gépen készült — nézd meg,
  mi van rajta, mielőtt átfedő munkába kezdesz).
