# Költség- és időjelentés

Téma: `korai-szelekcio` — az átláthatósági elv része: ennyi időbe és ennyibe került ennek a problémának a feldolgozása (a(z) 9. körtől számított érában).

- **Falióra-idő (körök összesen):** 55p 23mp
- **Tokenek:** 3,525,338 (bemenet: 3,047,488, kimenet: 477,850)
- **Becsült költség:** $12.17 USD (konfigurálható ártáblából — config/system_config.json pricing)
- **Mért / nem mért hívások:** 144 / 0 (a CLI/előfizetéses backendek hívásonként nem mérnek tokent — az ő költségük itt nem szerepel)

## Modellenként

| modell | bemeneti token | kimeneti token | becsült USD |
|---|---|---|---|
| claude-haiku-4-5 | 569,463 | 142,497 | $1.28 |
| claude-opus-4-8 | 177,812 | 12,602 | $1.20 |
| claude-sonnet-5 | 1,920,732 | 261,723 | $9.69 |

## Körönként

| kör | idő | token | becsült USD |
|---|---|---|---|
| 9 | 12p 54mp | 516,941 | $1.00 |
| 10 | 42p 28mp | 3,008,397 | $11.17 |

A számok forrása a körök `round_log.json`-ja (audit-nyom a repóban); az USD-érték becslés, nem számla.
