# Javaslat: strukturált, kétnyelvű, eszközhasználó agensek (D-34 tervezet)

Státusz: **ELFOGADVA (owner, 2026-07-14).** A nyitott kérdésekre adott
válaszok:
1. API-költség elfogadható — a generator-út API-ra kerül (nem hibrid).
2. A rounds 1–7 éra véglegesen lezárva, archív; a round 8 új baseline.
3. A P4 (web search) a P2-vel egy körben mehet.

A megvalósítás a `refactor/structured-agents` branchen folyik; merge után
D-34-ként kerül a decision logba (angolul, a decisions.md konvenciója szerint).

Branch: `test/bilingual-expert-prompt` — a bizonyító tesztek itt vannak:
- `scripts/test_bilingual_prompt.py` — instrukcióval kért kétnyelvűség NEM működik
- `scripts/test_json_expert_output.py` — "Return ONLY JSON" instrukció NEM működik
- `scripts/test_structured_json_real.py` — `output_config.format` schema **MŰKÖDIK**: garantált {en, hu} egy hívásban
- `scripts/test_websearch_expert.py` — web search-csel az expert `[evidence: weak]` → `[evidence: strong — forrás]` szintre lép, konkrét friss számokkal

## Mi a probléma (a 2026-07-14-i session diagnózisa)

1. **A mock fallback hamis eredményeket ad.** A round 6 brief-je teljes
   egészében mock-generált volt (`final_brief_writer` fallback); a mock a
   deterministic scorer formátumára optimalizál (sparse szöveg, magas
   tag-density), így mesterségesen jó score-t kap. A round 6→7 "romlás"
   (9.64→9.508) nagyrészt ennek a korrekciója, nem regresszió.
2. **A fordítási lépések a fő hibaforrás.** Round 7-ben mind a 17 fallback
   fordítás volt (`translate_voice` ×10, `translate_reciprocity` ×7). Ok: a
   claude-code CLI 600s subprocess-timeoutja + nagy batch-ek (~180K token).
3. **Az egész validációs gépezet szabad szöveget parse-ol regex-szel.**
   A critic-ek (`Objection:`/`Severity:`), a brief (`## `-headerek,
   `[fact]`-tagek), a synthesis (`Why:`-számlálás) — mind törékeny, és a
   D-30-hoz hasonló tag-vocabulary-bugokat termel (lásd 18f3941, a02acf5).
4. **Az expertek nem kutatnak.** Egy expert = egy LLM-hívás a betanított
   tudásból; ezért kénytelen `[evidence: weak]`-et írni és bizonytalanságot
   vallani ott, ahol egy keresés erős forrást adna (issue #6).

## A refactor négy pillére

### P1 — Strukturált output minden generátor-lépésre

Minden agens-output JSON, az Anthropic `output_config.format` (JSON schema,
constrained decoding) garanciájával; Gemini-oldalon `response_schema` az
ekvivalens. A schema kikényszeríti a mezőket — nincs több regex-parse,
nincs formátum-hibából eredő fallback.

- Artifact-schemák: `expert_analysis`, `scenarios`, `synthesis`, `critic`,
  `voice`, `reciprocity`, `cluster`, `brief` (10 szekció), `meta_critique`.
- Az evidence-tag strukturált mezővé válik:
  `{claim, kind: fact|estimate|assumption|value, evidence: strong|moderate|weak|contested, source}`
  — a "van-e tag" kérdés triviálissá válik, a hangsúly a minőségre tolódik.
- A `.md` fájlok generált nézetek lesznek (renderer JSON→md); a JSON az
  egyetlen source of truth. A site-buildnek ez kedvez (explorer már JSON-t
  eszik).

### P2 — Kétnyelvű agensek, fordítási lépések törlése

Minden schema `{en: {...}, hu: {...}}` párt tartalmaz; a glossary a (cache-elt)
system promptba kerül. Bizonyítva: a schema-kényszer mindkét nyelvet kitölti,
és a magyar minőség natív, nem gépi-fordítás-ízű.

- Törlődik: `translate_scenarios`, `translator_brief`, `translate_ledger`,
  `translate_voice`, `translate_reciprocity`, `translate_cluster` (~46 hívás/kör).
- A `translation_fidelity` dimenzió helyére `bilingual_parity` lép:
  determinisztikus (id-halmazok, elemszámok, tag-értékek egyezése a két nyelv
  közt — a mostani translation_checker logikájának adaptálása), + LLM-judge a
  jelentés-hűségre (cross-family, változatlanul).
- Kockázat: az angol minőség romolhat, ha a modell "megosztja a figyelmét".
  A teszt ezt nem mutatta, de az acceptance-körben (lásd ütemezés) explicit
  ellenőrizzük: az EN-mezők minősége nem lehet rosszabb a round-7 baseline-nál.

### P3 — Mock fallback törlése

- `llm.py`: a retry-lánc kimerülése után `StepFailed` exception, SOHA mock.
  A `steps.jsonl` a hibát logolja; az iteration loop leáll; a relaunch a
  meglévő state-hash resume-mal folytatja (ez már működik).
- A mock backend egyetlen legitim módja: `LAB_FORCE_MOCK=1` (explicit dry-run,
  `run_mock_sprint.py` — plumbing-teszt, gitignored output). Fallbackként soha.
- A `final_report`-ban a "mit szolgált ki mock" szekció helyére "mely lépések
  failed-eltek és hányszor kellett relaunch" kerül.

### P4 — Web search az experteknek (issue #6 első fele)

- Config-toggle: `research.web_search: true|false` (mint `discourse.enabled`).
- Expert-hívás `tools=[{type: web_search_20260209, max_uses: 5}]`-tel +
  `pause_turn`-kezelő loop (a teszt-scriptben már megírva).
- **A D-24 gate érintetlen marad:** a webes találat az expert-outputban
  idézett forrás, NEM kerül automatikusan a knowledge/registry-be. Regisztrált
  ténnyé csak human-gated PR-ral válhat (a proposal-fájl útvonalon).
- Költségkontroll: csak generator-oldal, csak expertek (9-10 hívás/kör), és a
  D-19 cache (változatlan spec → előző kör outputjának újrafelhasználása)
  továbbra is él, tehát csak változott expertek keresnek újra.

## Backend-következmény (fontos!)

A strukturált output **API-hívást igényel** — a `claude -p` CLI nem tud
`output_config`-ot. Tehát a generator-út a subscription-CLI-ről API-ra kerül:

- Költség-mitigáció: (a) prompt caching — a glossary + agent-spec a cache-elt
  system-prefixbe; (b) a D-26 ladder marad (Haiku a mechanikus lépésekre);
  (c) **Message Batches API**: a kör fan-out lépései (10 expert, 10 voice,
  8 critic, 18 cluster) nem latency-érzékenyek → 50% áron futtathatók. Ez
  külön al-döntés, a P1 után érdemes bevezetni.
- A judge maradhat cross-family (Gemini `response_schema` a `{score, reason}`
  párra — a SCORE:-regex is kiváltható; codex-judge text-fallback marad).
- A 600s subprocess-timeout megszűnik; az SDK-timeout + streaming kezeli a
  hosszú hívásokat.

## Kell-e CrewAI vagy LangChain?

**Nem javasolt. Rövid válasz: a labor értéke nem az orchestration-plumbing,
hanem a domain-logika — a frameworkök pont a plumbinget adnák, rosszabbul.**

| Amit egy framework ad | Nálunk |
|---|---|
| Agent-absztrakció, role-prompt | Megvan (`agents/**/*.md` spec + build_prompt), verziózva, auditálva |
| Orchestration / DAG | A kör determinisztikus, fix DAG — sima Python, `steps.jsonl` resume-mal. A CrewAI dinamikus delegálása pont a reprodukálhatóság (one change per round, state-hash) ellen dolgozik |
| Tool-integráció | Az Anthropic SDK natívan adja (server-side web search, structured output) — a LangChain-wrapper tipikusan hetekkel-hónapokkal lemarad az új API-feature-ökről (`output_config`, `web_search_20260209`) |
| Memory | Saját, szándékosan explicit (episodic memory fájlok, D-19 cache) |
| Multi-provider | Saját, és muszáj is: cross-family generator≠judge (check 13), D-26 ladder, D-27 quota-breaker — ezt egyik framework sem adja készen |

A `lab/llm.py` ~400 sor, és pont azokat a dolgokat tartalmazza, amiket egy
framework alatt is meg kellene írni (ladder, breaker, throttle, cross-family
szabály). A framework-bevezetés ára: dependency-churn, absztrakciós réteg a
hibakeresés útjában, és a decision-log 33 döntésének újra-leképezése egy idegen
modellre. Ha később mégis framework-igény merül fel (pl. dinamikus
multi-agent-delegálás), a natív Anthropic tool-runner / Managed Agents a
kisebb ugrás, nem a LangChain.

## Ütemezés (javasolt fázisok, mindegyik önállóan mergelhető)

| Fázis | Tartalom | Méret | Acceptance |
|---|---|---|---|
| 0 | **API-kulcs rotáció** (a mostani session-ben exponálódtak!), billing-enabled kulcsok (issue #4) | S | új kulcsokkal smoke-hívás |
| 1 | `llm.py`: `call_structured()` + mock-fallback→`StepFailed`; `LAB_FORCE_MOCK` explicit-only | M | unit-szint + 1 élő structured hívás |
| 2 | Schemák + pipeline-átállás artifact-onként (expert→scenario→critic→synthesis→discourse→brief), translate-lépések törlése, JSON→md renderer | L | `run_mock_sprint` (explicit mock) zöld + **élő round 8** |
| 3 | `evaluation.py`/`verify.py` átállás JSON-mezőkre; `translation_fidelity`→`bilingual_parity`; scorecard két-éra jelölés (1–7 régi séma, 8+ új) | M | verify zöld a round 8-on; check-ek nem gyengülnek |
| 4 | Web search toggle az experteknek (`research.web_search`), pause_turn-loop | M | A/B kör: evidence_discipline javul, D-24 gate sértetlen |
| 5 | Batches API a fan-out lépésekre (opcionális költség-optimalizálás) | M | kör-költség mérés |

Éra-váltás: a rounds 1–7 archív marad a régi séma alatt (nem rescore-oljuk —
a D-30 utáni tanulság, hogy a két éra nem összehasonlítható); a round 8 új
baseline. A final_scorecard mindkét érát mutatja, jelölve a törést.

## Nyitott kérdések az ownernek — MEGVÁLASZOLVA (2026-07-14)

1. Generator-költség: a CLI-subscription→API váltás pénzbe kerül. →
   **Elfogadva, teljes API-út (nem hibrid).**
2. A round 1–7 érát lezárjuk-e véglegesen? → **Igen, archív.**
3. A P4 (web search) mehet-e a P2-vel egy körben? → **Igen, együtt.**

## Újraszerkesztés, nem újraírás (2026-07-14 döntés)

A Phase 2 **fokozatos migráció** (strangler-minta), NEM zöldmezős újraírás.
Indoklás:

1. **Az architektúra a megtartandó érték.** A determinisztikus DAG +
   steps.jsonl-resume + state-hash + D-19 cache + D-26 ladder + D-27 breaker
   pont az, amiért a frameworköket is elvetettük — újraírásnál ezt kellene
   újra-levezetni, a 33 decision-log-döntés csendes elvesztésének kockázatával
   (pontosan ez történt a D-30-nál az agent-specekkel: seed vs committed fájl).
2. **A változás széles, de sekély.** Minden lépés megtartja a helyét a
   DAG-ban, a prompt-tartalmát és a szerepét — csak az output-kontraktus
   változik (markdown → kétnyelvű JSON). Ez tankönyvi inkrementális eset.
3. **A dry-run végig zöld maradhat.** Taskonkénti migrációnál a
   run_mock_sprint minden commit után fut; újraírásnál hosszú "minden törött"
   völgy lenne.
4. A Phase 1 (`call_structured` + `StepFailed`) már eleve inkrementális
   beszúrási pontnak készült.

**A kulcstrükk, ami a migrációt lépés-lokálissá teszi:** a JSON→md renderer
nem csak embernek szól — a downstream promptok (pl. az expert_digest a
scenario_buildernek) a renderelt markdownt kapják, így egy task migrálása
NEM kényszeríti a fogyasztóinak egyidejű átírását.

**Javasolt migrációs sorrend** (kockázat szerint, mindegyik önálló commit,
utána zöld mock sprint): `expert_analysis` (a minta validálása) →
`build_scenarios` (már JSON, csak {en,hu}-sítás) → critics → synthesis +
rejected_framings → discourse (voice/decompose/map/reciprocity — a
legnagyobb) → brief (a legnagyobb token-budget) → meta_critic. A
translate_* lépések mindig az adott task migrálásakor törlődnek.

Modul-szinten VAN helye teljes újraírásnak, ahol a modul feladata alapjaiban
változik: `translation.py` → `bilingual_parity` ellenőrző; mock-composerek
taskonként; új `lab/schemas.py` és `lab/render.py` tiszta lapról.

## Megvalósítási jegyzetek a Phase 2-höz (a Phase 1 tanulságai)

A Phase 1 (kész, commit `8f81df8`) által lefektetett interfész:
`llm.call_structured(prompt, schema, role, max_tokens=..., ...)` → parsed
dict; hibára `llm.StepFailed` (SOHA mock). A Phase 2 végrehajtójának:

- **`Step.run` structured-változat kell**: `schema=` paraméter, ami
  `call_structured`-ot hív; `loader=read_json`, `writer=write_json`; a
  `validate` a parsed dictet kapja. A corrective-retry (2 kísérlet,
  D-26 escalation) marad.
- **A mock_backendnek schema-tudatos composerek kellenek** minden áttért
  taskhoz, különben a `run_mock_sprint.py` (LAB_FORCE_MOCK=1 dry-run,
  plumbing-teszt) eltörik — a mock most markdownt ad, a `call_structured`
  json.loads-a StepFailed-et dob rá. Taskonként együtt kell átállítani:
  pipeline-schema + mock-composer + validátor.
- **A D-19 expert-reuse cache** (`reusable_expert`) a régi markdown-artifactot
  validálná — az első új-sémás körben a validátor-váltás miatt automatikusan
  cache-miss lesz (helyes), de a `validate(cached)` hívásnak dict/str
  mindkettőt túl kell élnie kivétel nélkül.
- **Az `agents/**/*.md` specek Output template-jei markdownt írnak le** —
  a D-30 tanulsága szerint a committed specfájlokat KÖZVETLENÜL kell
  szerkeszteni (a scaffold(force=False) soha nem nyúl meglévő fájlhoz).
  A schema mellett a spec-template is frissítendő, különben a prompt
  ellentmond a schemának.
- **Anthropic structured-output korlátok**: minden objektumra
  `additionalProperties: false` kötelező; nincs minLength/maxLength/minimum;
  truncation (`stop_reason=max_tokens`) StepFailed — a token-budgeteket
  bőven kell méretezni (a kétnyelvű brief a legnagyobb: 16K+).
- **Gemini-oldal**: a `_gemini_schema()` sanitizer strippeli az
  additionalProperties-t; a judge `{score, reason}` schemára állítása a
  SCORE:-regex kiváltásához Phase 3.
- **Web search (P4)**: a `pause_turn`-resume loop mintája a
  `scripts/test_websearch_expert.py`-ban; `web_search_20260209` server-side
  tool NEM kombinálható structured output-tal egy hívásban tetszőlegesen —
  ellenőrizendő; ha ütközik, az expert-hívás két fázis legyen (search-es
  szabad hívás → structured összefoglaló hívás). A D-24 gate: webes találat
  csak idézett forrás, registry-be sosem kerül automatikusan.
- **Maradék mock-hívóhely**: `evaluation.py` ~199. sor (judge-score parse
  fallback) — Phase 3-ban törlendő.
- **Éra-váltás**: rounds 1–7 NEM rescore-olandó; verify/scorecard két érát
  jelöl; a round 8 az új baseline és az acceptance-teszt (élő kör).
