# Javaslat: strukturált, kétnyelvű, eszközhasználó agensek (D-34 tervezet)

Státusz: **TERVEZET — owner-döntésre vár.** Elfogadás után D-34-ként kerül a
decision logba (angolul, a decisions.md konvenciója szerint).

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

## Nyitott kérdések az ownernek

1. Generator-költség: a CLI-subscription→API váltás pénzbe kerül. Elfogadható-e,
   vagy hibrid kell (structured-igényes lépések API-n, többi CLI-n)?
2. A round 1–7 érát lezárjuk-e véglegesen (javaslat: igen, archív)?
3. A P4 (web search) mehet-e a P2-vel egy körben, vagy külön kör legyen a
   "one documented change per round" szellemében? (Javaslat: külön.)
