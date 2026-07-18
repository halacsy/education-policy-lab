# Pozicionálás — Oktatáspolitikai Atlasz

*Állapot: tulajdonosi döntések alapján rögzítve, 2026-07-18. Ez a dokumentum a
kifelé szóló kommunikáció (weboldal, sajtó, bemutatkozás) egyetlen forrása.
Ahol a `site/DESIGN_BRIEF.md` ellentmond neki, ez a dokumentum érvényes.*

## A termék egy mondatban

> Az **Oktatáspolitikai Atlasz** Magyarország nagy oktatáspolitikai kérdéseit
> térképezi fel: kérdésenként megmutatja a lehetséges válaszokat, mindegyik
> válasz előnyeit és hátrányait, az érvek mögötti bizonyítékok erősségét — és
> azt is, miben nem értenek egyet a szakértők.

A név munkacím, de a metafora kötelező: **a termék a térkép, nem a
térképrajzoló gép.** Az atlasz nem mondja meg, hová menj — megmutatja, milyen
utak vannak, és melyik milyen terepen vezet.

## Kinek szól

**Elsődleges olvasó: a friss döntéshozó.** Egy most pozícióba került politikus,
képviselő, önkormányzati vezető vagy stábtag, akinek hetei lennének beolvasni
magát egy kérdésbe — itt fél óra alatt átlátja az opcióteret, és tudja, hol
vannak a valódi viták. Nem kész álláspontot kap, hanem tájékozódási képességet.

Másodlagos közönségek (a korábbi brief sorrendje él): intézményvezetők és
szakértők; nemzetközi szakpolitikai kollégák (EN tükör); kutatók és
AI-módszertan iránt érdeklődők (őket a módszertan-oldal szolgálja ki).

**A honlap az olvasóé, nem a projekté.** A projekt története, a módszertan és
a közreműködő-toborzás aloldalakra kerül; a főoldal a kérdésekkel nyit.

## Mit ígérünk (és ebből mi látszik már ma)

| Ígéret | Miből áll ma |
|---|---|
| A nagy kérdések listája | témák (korai szelekció, kisiskolák) — a problem brief maga a kérdés kifejtése |
| Adható válaszok | 5 forgatókönyv kérdésenként, köztük a „nem csinálunk semmit" ellenpont |
| Előnyök és hátrányok | érv-főkönyv, klaszterenként bizonyíték-fokozattal (erős/gyenge) |
| A viták természete | tipizált válaszkötelezettség: mi dönthető el bizonyítékkal, mi értékválasztás, mi feloldhatatlan trade-off |
| Ahol a szakértők nem értenek egyet | disagreement map — ritka műfaj, kiemelt helyet érdemel |
| Nyitott kérdések | human_questions — mit kell még kideríteni a döntés előtt |

## Mit NEM csinálunk (kifelé is kimondva)

- **Nem írunk szakpolitikát és nem ajánlunk győztest.** Az Atlasz opcióteret
  mutat, nem álláspontot képvisel.
- **Nem helyettesítjük a szakértőket** — a létező szakértői tudást és érveket
  rendszerezzük, forrásokkal.
- **Nem szimuláljuk a társadalmat.** A diskurzus-réteg pozíció-archetípusokat
  stresszteszt-céllal ütköztet; valós szervezetnek csak dokumentált,
  episztemikus címkével ellátott álláspontot tulajdonítunk.
- **Nem rejtjük el a bizonytalanságot**: a gyenge bizonyíték gyengének van
  jelölve, a nézeteltérés nem tűnik el a szintézisben.

## Az AI helye a történetben

Az AI a **módszertan**, nem az identitás. A sorrend a pozicionálás: az
AI-eredet az első bekezdés *után* derüljön ki, ne az első mondat előtt —
de derüljön ki, teljes őszinteséggel, mert az átláthatóság a hitelesség
forrása.

A módszertan-oldal üzenete: az Atlaszt AI-asszisztált kutatási folyamat
állítja elő; minden forrás, minden lépés és minden hiba nyilvános (git);
az érvek besorolása auditálható; a tartalmi kapuk (kérdés-keretezés
jóváhagyása, tudásbázis-bővítés) emberi döntések. Az AI itt nem *véleményt*
alkot, hanem *rendszerez*.

**Tanulság a Telex-levélből** (2026-07-16): a rendszer-központú bemutatkozás
(„önjavító, többágenses AI-rendszer") azt a kérdést hívja elő, hogy „mit
csinál itt az AI?", és erre kívülről a legrosszabb választ adják meg („AI ír
policyket"). A tagadó keretezés — „nem szakpolitikát gyárt" — is az AI-t
tartja a fókuszban. Újságírónak ezért így mutatkozunk be:

> „Összegyűjtöttük egy helyre, hogy a magyar oktatás nagy kérdéseire milyen
> válaszlehetőségek léteznek, azoknak mi szól mellette és ellene, és miben
> vitatkoznak a szakértők. Olyan, mint egy atlasz: nem mondja meg, hová menj,
> de nélküle eltévedsz. A gyűjtést és rendszerezést AI-eszközökkel gyorsítjuk,
> minden lépése nyilvános és ellenőrizhető, a tartalmi döntések embernél
> vannak."

## Interakció: most és később

- **Most: böngészhető érvtérkép.** Kattintásos mélyülés: kérdés → válaszok →
  érvek → bizonyítékok/források. Nincs chat, nincs generálás az olvasó előtt.
- **Olcsó következő lépés (ötlet, nem vállalás): „Vidd magaddal promptként"
  gomb.** Minden oldalon letölthető/másolható szövegcsomag, amit az olvasó a
  saját AI-asszisztensébe (ChatGPT, Claude, Gemini) illesztve tovább
  beszélgethet a témáról. Elegáns, mert a párbeszédet a látogató saját,
  megbízottnak tekintett eszközébe visszük — nem nekünk kell chatszolgáltatást
  üzemeltetni és annak felelősségét viselni.
- **Később: párbeszéd az Atlasszal** (retrieval a tudásbázis felett, #6) —
  csak akkor, ha az érvtérkép már bizonyított.
- **Később: mondatszintű olvasói jelzés** („ez itt nem stimmel") — a köz nem
  írja az Atlaszt, de jelezhet; a jelzés a meglévő emberi kapun (proposal →
  admisszió) folyik be, nem közvetlen szerkesztés. Illeszkedik a D-24
  tudás-admissziós elvhez.

## Közreműködők

Külön aloldal („Dolgozz velünk az Atlaszon"), nem a főoldal része. Keresünk:
szakértőket (források, ellenérvek, tényellenőrzés — a D-24 kapun át),
fejlesztőket (nyílt repo), és később témagazdákat új kérdésekhez. A
közreműködés egysége a *javaslat* (proposal), nem a szerkesztés — ez a
minőségvédelem, és ez különböztet meg a wiki-modelltől.

## Elvetett irányok (hogy ne térjünk vissza rájuk érvek nélkül)

- **„Oktatáspolitikai Wikipédia"** mint külső hívószó: azonnal érthető, de
  hamis ígéret — a Wikipédiát a köz írja, az Atlaszt kapuőrzött folyamat.
  Belső magyarázatnak sem használjuk sajtó felé.
- **AI-rendszer mint vezető üzenet**: a fenti Telex-tanulság miatt.

## Következmények a weboldalra (a design brief felülvizsgálandó pontjai)

1. Főoldal-hero: a kérdések, nem a projekt. („Maradjon-e a 6/8 osztályos
   gimnázium?" — belépés a témába.)
2. Oldaltérkép: főoldal = témakatalógus; témaoldal = kérdés → válaszok →
   érvek; aloldalak = módszertan (ide a mostani „hogyan működik" + scorecard
   + git-napló), az Atlaszról, közreműködőknek.
3. A „önjavító, többágenses" szókincs kifelé eltűnik; a bizonyítékcímkék és a
   nézeteltérés-térkép vizuális rendszere marad (az a tartalom erőssége).
4. Az EN tükör a nemzetközi közönségnek szól, változatlan elv.
