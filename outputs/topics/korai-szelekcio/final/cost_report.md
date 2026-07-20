# Költség- és időjelentés

Téma: `korai-szelekcio` — az átláthatósági elv része: ennyi időbe és ennyibe került ennek a problémának a feldolgozása (a(z) 9. körtől számított érában).

- **Falióra-idő (körök összesen):** 25p 27mp
- **Tokenek:** 906,453 (bemenet: 753,798, kimenet: 152,655)
- **Becsült költség:** $2.00 USD (konfigurálható ártáblából — config/system_config.json pricing)
- **Mért / nem mért hívások:** 62 / 0 (a CLI/előfizetéses backendek hívásonként nem mérnek tokent — az ő költségük itt nem szerepel)

## Modellenként

| modell | bemeneti token | kimeneti token | becsült USD |
|---|---|---|---|
| claude-haiku-4-5 | 200,619 | 18,670 | $0.29 |
| claude-sonnet-5 | 177,870 | 78,052 | $1.70 |

## Körönként

| kör | idő | token | becsült USD |
|---|---|---|---|
| 9 | 12p 54mp | 516,941 | $1.00 |
| 10 | 12p 32mp | 389,512 | $0.99 |

A számok forrása a körök `round_log.json`-ja (audit-nyom a repóban); az USD-érték becslés, nem számla.
