# Design brief — Oktatáspolitikai Atlasz (nyilvános weboldal)

*Felülvizsgálva 2026-07-18-án a `docs/positioning.md` alapján — a pozicionálási
dokumentum az elsődleges forrás, ez a brief annak design-következményeit
rögzíti. A korábbi brief (rendszer-központú bemutatás, git-napló mint
hero-bizonyíték) érvénytelen.*

**Megvalósítási státusz (D-55):** a v2 az alapértelmezett nyilvános Atlasz.
A főoldal a kérdésekkel nyit, a témaoldalak fokozatosan mélyülnek, az
eredettérkép pedig csak az elfogadott, forrásolt production futásokat mutatja.
A v1 és a nyilvános v1/v2 összehasonlítás már csak a Git-történetben él.

## Mi ez a termék (egy bekezdésben)

Az **Oktatáspolitikai Atlasz** (munkacím) Magyarország nagy oktatáspolitikai
kérdéseit térképezi fel: kérdésenként megmutatja a lehetséges válaszokat,
mindegyik válasz előnyeit és hátrányait, az érvek mögötti bizonyítékok
erősségét — és azt is, miben nem értenek egyet a szakértők. A vezérmetafora:
**a termék a térkép, nem a térképrajzoló gép.** Az atlasz nem mondja meg,
hová menj — megmutatja, milyen utak vannak.

Az AI-asszisztált előállítási folyamat a módszertan-aloldalon jelenik meg,
teljes átláthatósággal — de a főoldalon és a témaoldalakon a tartalom a
főszereplő, nem a rendszer. Kifelé kerülendő szókincs: „önjavító",
„többágenses", „AI-rendszer" mint vezető üzenet.

## Célcsoportok (fontossági sorrendben)

1. **Az érdeklődő, aki most tanul bele az oktatási rendszerbe** — nincs
   szakpolitikai előképzettsége, de egy konkrét kérdést fél óra alatt szeretne
   megérteni: mi a probléma, mit lehetne tenni, kinek lenne jobb vagy rosszabb,
   és hol marad valódi vita. Köznyelvi belépőt és fokozatos mélyülést kér, nem
   szakértői zsargont vagy technológiai bemutatót.
2. **Döntéshozók, intézményvezetők, oktatási szakértők** — mélyebb rétegek: források,
   bizonyíték-fokozatok, nyitott kérdések.
3. **EU-s / nemzetközi szakpolitikai kollégák** — a teljes EN tükör nekik szól.
4. **Kutatók, AI-módszertan iránt érdeklődők** — őket a módszertan-aloldal és
   a nyílt repo szolgálja ki.

**A honlap az olvasóé, nem a projekté.** A projekt története, a módszertan és
a közreműködő-toborzás aloldal; a főoldal a kérdésekkel nyit.

## Hangvétel

Intézményi megbízhatóság + kutatási transzparencia. Inkább „közpolitikai
folyóirat és atlasz", mint startup-landing vagy laborjegyzőkönyv. Kerülendő:
AI-hype esztétika, gradiens-hero, sci-fi motívumok, robotos illusztrációk.
Az atlasz/térkép metafora vizuálisan is használható (tájékozódás, útvonalak,
jelmagyarázat), de ne váljon szó szerinti térképgrafikává.

## Információs architektúra (többoldalas)

1. **Főoldal = témakatalógus.** Hero: maguk a nagy kérdések, kérdés
   formájában megfogalmazva („Maradjon-e a 6/8 osztályos gimnázium?" —
   „Mi legyen az elnéptelenedő falvak kisiskoláival?"), belépési pontként.
   Rövid „mi ez az oldal" sáv (az atlasz-bekezdés), lábjegyzet-szintű
   módszertan-link.
   - Amíg a témakatalógus még rövid, a főoldal külön, adatvezérelt
     **állományjegyzékben** mutatja meg az Atlasz tényleges mélységét:
     kérdések, válaszutak, érvklaszterek, emberi döntést kérő dilemmák,
     nézeteltérések, szakértői kutatási dossziék, kimondott bizonytalanságok
     és kurált evidencia-tételek. A számlálók a publikált rekordokból
     generálódnak, nem marketingmetrikák.
   - A kérdésbeküldés és a frissülés külön főoldali útvonalat kap: tegye
     láthatóvá, hogy az Atlasz növekvő gyűjtemény, és hogy új kérdésből vagy
     új evidenciából ugyanazzal az auditálható folyamattal gyorsan új vagy
     frissített döntési dosszié készülhet.
2. **Témaoldal = a mélyülés íve:** kérdés (problem brief) → lehetséges
   válaszok (forgatókönyvek, köztük a „nem csinálunk semmit" ellenpont) →
   érvek és ellenérvek (érv-főkönyv, bizonyítékcímkékkel) → miben vitáznak a
   szakértők (nézeteltérés-térkép) → nyitott kérdések. Kattintásos mélyülés,
   nincs chat.
   - **Forgatókönyv-oldal = egy válaszút teljes dossziéja.** A témaoldal
     minden válaszútja külön, stabilan linkelhető oldalra vezet. Az oldal a
     legfrissebb strukturált rekord minden mezőjét megmutatja: cél,
     mechanizmus és elemenkénti bizonyítékfokozat, előnyök,
     méltányossági hatás, költségkategóriák, megvalósítási lépések,
     feltételezések, politikai kockázatok és a bizonytalanságot csökkentő
     kutatási igény. Innen nyílik a forgatókönyvhöz tartozó teljes kritikai
     és érvrekord.
   - **Vita- és dilemmaoldal = kanonikus, megosztható rekord.** Minden
     megőrzött szakértői nézeteltérés és minden emberi döntést kérő dilemma
     saját szemantikus URL-t kap a szülő kérdés alatt
     (`/vita/<id>-<slug>.html`, `/dilemma/<id>-<slug>.html`). A feltáró
     fragmentumai megmaradnak teljes auditnézetnek; egy későbbi popup csak
     előnézet lehet, a külön oldalt nem helyettesíti. A rekordoldal mindig
     mutassa a teljes hierarchiát morzsamenüben, és adjon előző/következő
     navigációt az azonos típusú rekordok között. A dilemma azonosítója és
     típusa az oldal címe; a gyakran mondathosszúságú klaszterállítás
     olvasási méretű bekezdés, nem display címsor. A rövid vitakérdés
     továbbra is valódi címsor.
   - **Szakértői profil = témán belüli provenance-dosszié.** Minden, az adott
     kérdésen dolgozó szakértő-ágens saját stabil oldalt kap. A profil
     egyértelműen jelzi, hogy nem ember vagy intézmény, bemutatja a futáskor
     használt szerepspecifikációt, a hozzárendelt emberileg kurált tételeket,
     az élő kutatás URL-jeit, minden strukturált megállapítást és
     bizonytalanságot, valamint azokat a vitákat, amelyekben a brief név
     szerint pozíciót rendelt hozzá. Csak explicit attribúció jelenhet meg;
     a profil nem találhat ki utólag állításszintű provenance-et.
3. **Aloldalak:**
   - **Módszertan** — ide költözik minden, ami eddig a főoldal gerince volt:
     hogyan készül az Atlasz, a 6 lépéses kör diagramja, scorecard és
     pontszám-görbe, git-napló, emberi kapuk (kérdés-keretezés jóváhagyása,
     tudás-admisszió). Itt teljes őszinteség az AI szerepéről.
   - **Az Atlaszról** — mi ez, kinek szól, mit nem csinál (nem ír
     szakpolitikát, nem ajánl győztest, nem szimulálja a társadalmat).
   - **Közreműködőknek** — „Dolgozz velünk az Atlaszon": szakértők (források,
     ellenérvek a proposal-kapun át), fejlesztők, később témagazdák. A
     közreműködés egysége a javaslat, nem a szerkesztés.
   - **Kérdés beküldése** — űrlap + a folyamat elmesélése (kérdés → feldolgozás
     → kétnyelvű témaoldal + nyitott emberi kérdések vissza).

## A tartalomból adódó megkülönböztető vizuális anyagok

Olvasó felé (fő- és témaoldalak):

- **Bizonyítékcímkék**: `[bizonyíték: erős / mérsékelt / gyenge / vitatott]` —
  chip/badge komponensként végigvihetők.
- **Kétszínű jelentésrendszer** (javaslat, felülbírálható): egy szín a
  bizonyítéknak, egy kontrasztos a különvéleménynek / nyitott kérdésnek.
  A tartalom lényege a kettő feszültsége.
- **Nézeteltérés-térkép**: többségi/kisebbségi álláspont-párok — kétoszlopos
  vizuális motívum.
- **A vita-típus jelölése**: bizonyítékkal eldönthető / értékválasztás /
  feloldhatatlan trade-off — ez az Atlasz egyik legritkább műfaji értéke,
  érdemes saját vizuális nyelvet adni neki.

Módszertan-oldalra (NEM a főoldalra):

- **Kör-diagram**: a 6 lépéses iterációs kör.
- **Git-napló és pontszám-görbe**: a mérhető javulás.

## Funkcionális követelmények

- **Kétnyelvűség**: HU-elsődleges, teljes EN tükörre tervezz (a rendszer
  minden anyagot mindkét nyelven előállít).
- **„Vidd magaddal promptként" gomb** (ötlet-fázis, tervezz rá helyet):
  minden témaoldalon másolható/letölthető szövegcsomag, amit az olvasó a
  saját AI-asszisztensébe illesztve tovább beszélgethet a témáról.
- **Mondatszintű olvasói jelzés** (későbbi fázis, ne blokkolja a designt):
  „ez itt nem stimmel" visszajelzés, ami javaslatként fut be, nem
  szerkesztésként.
- **Kérdésbeküldés**: az űrlap most mock; a mechanika nyitott döntés
  (e-mail / GitHub issue / backend).
- Statikus oldal, önállóan hosztolható; akadálymentesség (WCAG AA,
  fókusz-állapotok, `prefers-reduced-motion`).
- A táblázatok/kódblokkok saját konténerben görgethetők, az oldal maga soha
  nem görget vízszintesen.
- A témaoldalak generáltak (`build_v2_production_site.py`) — a design komponensei
  ezekben a sablonokban élnek majd, tervezz ismétlődő, adatvezérelt
  komponensekben.

## Nyitott kérdések a designernek

- A főoldali témakatalógus formája: kártyák, lista, vagy „térkép-szerű"
  belépés?
- A bizonyítékcímke- és vitatípus-rendszer együtt mennyire terhelhető
  vizuálisan (két párhuzamos jelölésnyelv)?
- Illusztrációs nyelv: tisztán tipografikus + diagram, vagy van illusztráció?
- A HU/EN váltó interakciója.
