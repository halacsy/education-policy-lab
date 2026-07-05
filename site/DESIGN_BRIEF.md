# Design brief — Education Policy Lab nyilvános weboldal

A mellékelt `index.html` **tartalom-kész vázlat**: a szöveg, a szerkezet és az
információs hierarchia végleges szándékú, a vizuális identitás a tiéd. Azt a
minimál stílust, ami most rajta van, nyugodtan dobd el.

## Mi ez a projekt (egy bekezdésben)

Önjavító, kétnyelvű (HU/EN), többágenses AI-műhely oktatáspolitikai kérdések
kidolgozására. Az AI szakértő- és kritikus-ágensei információt dolgoznak fel;
az ember dönt. Minden állításon bizonyítékcímke van, a szakértői nézeteltérés
nem tűnik el, és minden önjavító lépés git-commitban auditálható.

## Célcsoportok (fontossági sorrendben)

1. **Magyar oktatáspolitikai szereplők** — döntéshozók, intézményvezetők,
   szakértők. Bizalmat és komolyságot kell látniuk, nem tech-demót.
2. **EU-s / nemzetközi szakpolitikai kollégák** — az angol kivonat nekik szól.
3. **Kutatók, AI-módszertan iránt érdeklődők** — őket a transzparencia-szakasz
   és a repo érdekli.

## Hangvétel

Intézményi megbízhatóság + kutatási transzparencia. Inkább „közpolitikai
folyóirat és laborjegyzőkönyv", mint startup-landing. Kerülendő: AI-hype
esztétika, gradiens-hero, sci-fi motívumok, robotos illusztrációk.

## A tartalomból adódó megkülönböztető vizuális anyagok

Ezek a rendszer *valódi* munkadarabjai — ezekből lehet karakteres design:

- **Bizonyítékcímkék**: `[bizonyíték: erős / mérsékelt / gyenge / vitatott]` —
  chip/badge komponensként végigvihetők az oldalon.
- **Kétszínű jelentésrendszer** (javaslat, felülbírálható): egy szín a
  bizonyítéknak/rendszernek, egy kontrasztos a különvéleménynek / nyitott
  emberi kérdésnek. A projekt lényege a kettő feszültsége.
- **Nézeteltérés-térkép**: többségi/kisebbségi álláspont-párok — kétoszlopos
  vizuális motívum.
- **Git-napló és pontszám-görbe**: a javulás ténylegesen mérhető
  (7.072 → 9.230 öt körben) — ez lehet az oldal „hero-bizonyítéka".
- **Kör-diagram**: a 6 lépéses iterációs kör (szakértők → forgatókönyvek →
  szintézis+fordítás → kritika → meta-kritika → értékelés → önjavítás).

## Oldaltérkép (jelenlegi egyoldalas vázlat szakaszai)

1. Mi ez? — 4 elv-kártya
2. Hogyan működik? — 6 lépés + scorecard + git-napló
3. Az első kérdés — S1–S4 forgatókönyv-kártyák + többségi/kisebbségi álláspont
4. Kérdés beküldése — űrlap (mechanika még nyitott, ld. lent)
5. Átláthatóság
6. English abstract
7. Lábléc — jogi/etikai disclaimer

Later: külön eredmény-aloldal kérdésenként (scenariók, brief, disagreement map
böngészhetően).

## Funkcionális követelmények

- **Kétnyelvűség**: most HU-elsődleges + EN kivonat; tervezz teljes HU/EN
  váltóra (a rendszer minden anyagot mindkét nyelven előállít).
- **Kérdésbeküldés**: az űrlap most mock. Nyitott döntés: űrlap → e-mail,
  vagy GitHub issue, vagy saját backend. A designtól azt kérjük, hogy a
  beküldés *folyamatát* is mesélje el (kérdés → futás → kétnyelvű csomag +
  emberi kérdések vissza).
- Statikus oldal, önállóan hosztolható; akadálymentesség (WCAG AA, fókusz-
  állapotok, `prefers-reduced-motion`).
- A táblázatok/kódblokkok saját konténerben görgethetők, az oldal maga soha
  nem görget vízszintesen.

## Nyitott kérdések a designernek

- Egyoldalas marad vagy többoldalas IA?
- A pontszám-görbe/scorecard mennyire hangsúlyos elem (hero vs. támogató)?
- Illusztrációs nyelv: tisztán tipografikus + diagram, vagy van illusztráció?
- A HU/EN váltó interakciója.
