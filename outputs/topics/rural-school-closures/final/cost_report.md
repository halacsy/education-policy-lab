# Költség- és időjelentés

Téma: `rural-school-closures` — az átláthatósági elv része: ennyi időbe és ennyibe került ennek a problémának a feldolgozása (a(z) 2. körtől számított érában).

- **Falióra-idő (körök összesen):** 1ó 5p 14mp
- **Tokenek:** 3,424,068 (bemenet: 2,910,582, kimenet: 513,486)
- **Becsült költség:** $12.23 USD (konfigurálható ártáblából — config/system_config.json pricing)
- **Mért / nem mért hívások:** 168 / 0 (a CLI/előfizetéses backendek hívásonként nem mérnek tokent — az ő költségük itt nem szerepel)

## Modellenként

| modell | bemeneti token | kimeneti token | becsült USD |
|---|---|---|---|
| claude-haiku-4-5 | 524,065 | 159,149 | $1.32 |
| claude-opus-4-8 | 138,908 | 5,429 | $0.83 |
| claude-sonnet-5 | 1,889,324 | 294,070 | $10.08 |

## Körönként

| kör | idő | token | becsült USD |
|---|---|---|---|
| 2 | 46p 45mp | 2,720,123 | $10.14 |
| 3 | 18p 28mp | 703,945 | $2.09 |

A számok forrása a körök `round_log.json`-ja (audit-nyom a repóban); az USD-érték becslés, nem számla.
