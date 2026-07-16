# Kísérlet: research token-keret és a web-keresés kiesésének megfejtése

Dátum: 2026-07-16 · Kontextus: a rural-school-closures round 2 friss-szakértős
futása közben a research-lépések ismétlődően URL nélküli jegyzeteket adtak,
több szék pedig "server tool use limit exceeded"-et jelentett. Két kérdést
mértünk: (1) számít-e a research-hívás token-kerete a jegyzetek minőségére,
(2) mi okozza a keresés-kieséseket.

## 1. kísérlet — token-keret (8K / 16K / 32K), 3 szék

Székek: international_comparison, finnish_reform (a két ismétlődően bukó),
demography (kontroll). Azonos prompt, csak a max_tokens változott.
Modell: claude-sonnet-5, web_search_20260209 (dynamic filtering), max_uses=5.

| szék | keret | csonkolt? | keresés ok | URL | idő |
|---|---|---|---|---|---|
| international | 8K | nem | 5/5 | **12** | 99s |
| international | 16K | nem | 5/5 | 0 | 210s |
| international | 32K | — SDK ValueError (streaming kellene) | | | |
| finnish | 8K | nem | 5/5 | 0 | 135s |
| finnish | 16K | nem | 5/5 | 0 | 256s |
| demography | 8K | nem | 5/5 | 0 | 118s |
| demography | 16K | nem | 5/5 | 0 | 88s |

## 2. kísérlet — minőség-összevetés (8K / 16K / 128K), teljes szövegek mentve

A 128K-s kar streaminggel futott ("nincs limit" — a modell kimeneti plafonja).

| szék | 8K | 16K | 128K |
|---|---|---|---|
| international | 5,0K kar., 22 szám | 5,1K kar., 24 szám | 4,0K kar., 19 szám |
| finnish | 9,7K kar., 96 szám, 14 URL ✅ | 7,0K kar., 19 szám | 6,9K kar., 36 szám |
| demography | 5,7K kar., 32 szám | 5,0K kar., 31 szám | 5,3K kar., 24 szám |

**Eredmény:** a keret NEM befolyásolja a tartalmi mélységet — a limit
nélküli karok két széknél a legrövidebb szöveget adták (az adaptív
gondolkodás önszabályoz), csak lassabbak (186–214s vs 82–124s). A 4K-s
eredeti keret viszont valóban csonkolt (külön próbában stop=max_tokens,
0 URL). A minőséget egyetlen tényező dominálta: működött-e a keresés —
az egyetlen élő-forrásos futás (finnish-8K) messze a legjobb. A 2.
kísérlet ablakában 9-ből 8 futás keresése halt el ("Server tool use limit
exceeded") — ez vezetett a 3. kísérlethez.

## 3. kísérlet — a keresés-kiesés megfejtése (blokk-szintű dump + A/B)

A valódi pipeline-promptot futtattuk nyers blokk-rögzítéssel, felváltva
dynamic filtering és direct (`allowed_callers: ["direct"]`) módban,
request-id-k mentésével.

**A mechanizmus (blokk-szekvenciából bizonyítva):** a dynamic filtering
útvonalon a modell szűrőkódja elindítja a kereséseket — azok LEFUTNAK, a
válaszban ott a 42 releváns találat (OECD, CEU, ERRC…) —, de maga a
szűrőkód futása kap "Server tool use limit exceeded" hibát (kérésen belüli
server-tool-keret), így **a modell soha nem látja a saját, már lekért
találatait**. Hatszor újrapróbálja (várakozással, egyesével), mind bukik,
majd jóhiszeműen azt jelenti: "a keresés nem működik", és háttértudásból
ír forrás nélküli jegyzetet. A műszerezésünk közben 5 "sikeres"
kereső-blokkot lát — ezért nem fogta meg a require_search kapu.

Ugyanabban az idősávban: dynamic kar 2/2 bukás (egyik 28 percig őrölt),
direct kar 2/2 működő keresés (68–87s, az egyik 11 URL-lel).

## Mellék-lelet: instrukció-konfliktus mint "URL-szeszély"

A research-hívás a teljes szakértői spec-et kapja ("follow strictly"),
benne a ~450 szó/nyelv szabállyal — ami ellentmond az "5–10 finding teljes
URL-lel" tasknak. Melyik nyer, futásonként változott (azonos prompt: hol
12 URL, hol 0). Feloldva: a jegyzetek explicit felmentést kaptak a
szó-limit alól.

## Döntések (mind commitolva 2026-07-16)

1. **Direct keresés** a research-hívásokban (`allowed_callers: ["direct"]`,
   llm._call_search) — több input-token, de a források tényleg megérkeznek;
   `research.dynamic_filtering=true` visszakapcsolja a szűrt utat, ha az
   upstream limit javul.
2. **Keret: 16K** (a 4K csonkolt; 8K felett nincs mérhető különbség; a
   32K+ streaming nélkül nem is küldhető el).
3. **URL-validátor + corrective retry** a research-lépésen (jegyzet URL
   nélkül nem megy tovább); a spec szó-limitje alól a jegyzet felmentve.
4. **Audit-réteg**: rejections.jsonl (elutasított kimenet + ok),
   round_meta.json (indítások), hívásonkénti keresés-statisztika a
   round_logban; műhely-napló nézet a site-on.

## Nyitva maradt

- Az upstream "Server tool use limit exceeded" pontos természete (kérésen
  belüli keret? időszakos kapacitás?) — request-id-k mentve egy esetleges
  Anthropic support-jegyhez (scratchpad/search-diag). Nem blokkol: direct
  móddal kikerültük.
- A require_search kapu a dynamic útvonalon elvi vakfolt marad (a
  válasz-blokkok "sikeresnek" látszanak) — direct módban a számláló
  megbízható.
- Mintaszám: karonként 1–2 futás; a variancia-állítások irányát a
  blokk-szintű mechanizmus-bizonyíték hordozza, nem a statisztika.
