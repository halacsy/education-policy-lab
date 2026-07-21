# V2 két témás éles elfogadási futás

**Dátum:** 2026-07-20–21  
**Ág:** `codex/artifact-dag-v2`  
**Futás:** `v2/production/2026-07-20-live/`  
**Cél:** ugyanazzal a v2 Artifact DAG-gal, friss kutatással újra lefuttatni a
korai szelekció és a vidéki kisiskolák kérdését, majd összevetni az eredményt
a v1 utolsó elfogadott körével.

## Eredmény röviden

Mindkét téma teljesítette a technikai v2 elfogadási kaput. A 31 csomópontos
DAG minden lépése befejeződött; nem volt mock-hívás vagy hibás aktuális
csomópont. A 12 jóváhagyott szakmai nézőpont mind a hat javaslatot értékelte.
Mindkét témán megmaradt az öt ember által jóváhagyott változtatási irány,
kritikus tartalomvesztés nélkül.

| Téma | V1 utolsó pontszám | V2 új pontszám | Friss megállapítás | Javaslat | Nézőpontértékelés | Dilemma | Kutatási kérdés |
|---|---:|---:|---:|---:|---:|---:|---:|
| Korai szelekció | 9,450 | 8,333 | 114 | 6 | 72 | 6 | 10 |
| Vidéki kisiskolák | 9,252 | 7,833 | 116 | 6 | 72 | 6 | 10 |

A v1- és v2-pontszámok **nem közvetlenül összehasonlíthatók**: más a
szempontrendszer, az értékelési szerződés és az architektúra. A kisebb v2
szám nem visszaesést bizonyít. A használható összevetés minőségi: a v2-ben a
forráskapcsolatok láthatók a döntési csomagban, a jóváhagyott lehetőségtér
lefedettsége gépi kapu, az értékellentétek külön dilemmarekordok, és a
döntésérettség nem keveredik a tartalmi pontszámmal.

## Mit hozott ki a korai szelekció kérdésén?

A hat változtatási irány:

1. felkészítésnek ellenállóbb, társadalmi helyzetet figyelembe vevő felvételi
   reform a meglévő hat- és nyolcosztályos szerkezetben;
2. az állami férőhelyek kapacitáskorlátos, demográfiához kötött szűkítése;
3. az első tanulmányi szelekció törvényi kitolása 14 éves kor fölé;
4. nem strukturális, kompenzáló méltányossági csomag;
5. beavatkozás nélküli, demográfiai passzív zsugorodási alapforgatókönyv;
6. a szegregációt növelő képzési kínálat bővítésének célzott hatósági
   korlátozása minden fenntartótípusnál.

Az értékelő fő hiányai: egyenetlen megvalósítási részletesség, néhány gyenge
vagy csak mutatóként tárolt forráscím, számszerű költség- és kapacitásmodellek
hiánya, nem teljes érintetti/politikai térkép, valamint a kiszorítási hatások
érzékenységvizsgálatának hiánya. Ítélet: `accept_with_caveats`; döntésérettség:
`ready_with_conditions`.

## Mit hozott ki a kisiskolák kérdésén?

A hat változtatási irány:

1. törvénybe foglalt bezárásellenes vélelem és kötelező alternatívavizsgálat;
2. kölcsönös állam–önkormányzat vidéki iskolaszerződések;
3. helyben maradó alsó és központba szervezett felső évfolyamok;
4. településközi iskolahálózatok és többfunkciós közösségi központok;
5. összevonás mint alapértelmezés, kötelező közlekedési és méltányossági
   kompenzációval;
6. országos életképességi, költség- és döntési nyilvántartás, benne a
   beavatkozás nélküli alapforgatókönyvvel.

Az értékelő fő hiányai: kevés konkrét felelős, jogszabályszöveg, költség és
ütemezés; a nem magyar oksági eredmények mellé kevés hazai kvázikísérleti
bizonyíték; nincs számszerű költségvetési hatás; az érintetti ösztönzők és
vétópontok túl általánosak; néhány hivatkozás csak auditálható URN-mutató.
Ítélet: `accept_with_caveats`; döntésérettség: `ready_with_conditions`.

## Audit és költség

Az elfogadott két termelési tárban összesen 1 016 aktuális szemantikai
rekord van. A futásnaplók 138 elemzési modellhívást tartalmaznak, összesen
3 722 579 bemeneti és 556 618 kimeneti tokennel; a konfigurált árlista szerinti
becsült költség 18,0905 USD. Ez a két tár teljes felépítési történetét is
tartalmazza, beleértve a később felülírt, auditként megőrzött csomagverziókat.
A külön lokalizációs hívások nincsenek ebben a költségösszegben.

## Elfogadási döntés

A v2 technikai termelési alapvonala elfogadva **belső emberi áttekintésre**.
Külső szakpolitikai használatra egyik csomag sincs automatikusan jóváhagyva:
mindkettőnél `human_external_use_gate=pending`. A v1 nyilvános belépési pont
lecserélése külön tulajdonosi döntés; a specifikáció fennmaradó, nyilvános
cutoverhez kötött tételei továbbra is nyitva maradnak.

## Ellenőrzések

- `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests/v2 -v` —
  16/16 sikeres;
- `.venv/bin/python scripts/verify_v2.py` — sikeres, 15 séma, 10 teljesen
  magyar oldal, 1 016 termelési rekord, 138 auditált analitikai hívás;
- `.venv/bin/python scripts/verify.py --topic korai-szelekcio` — sikeres;
- `.venv/bin/python scripts/verify.py --topic rural-school-closures` —
  sikeres.
