# Költség- és időjelentés

Téma: `rural-school-closures` — az átláthatósági elv része: ennyi időbe és ennyibe került ennek a problémának a feldolgozása (a(z) 2. körtől számított érában).

- **Falióra-idő (körök összesen):** 46p 45mp
- **Tokenek:** 2,720,123 (bemenet: 2,338,627, kimenet: 381,496)
- **Becsült költség:** $10.14 USD (konfigurálható ártáblából — config/system_config.json pricing)
- **Mért / nem mért hívások:** 107 / 0 (a CLI/előfizetéses backendek hívásonként nem mérnek tokent — az ő költségük itt nem szerepel)

## Modellenként

| modell | bemeneti token | kimeneti token | becsült USD |
|---|---|---|---|
| claude-haiku-4-5 | 340,119 | 135,541 | $1.02 |
| claude-opus-4-8 | 138,908 | 5,429 | $0.83 |
| claude-sonnet-5 | 1,693,991 | 213,983 | $8.29 |

## Körönként

| kör | idő | token | becsült USD |
|---|---|---|---|
| 2 | 46p 45mp | 2,720,123 | $10.14 |

A számok forrása a körök `round_log.json`-ja (audit-nyom a repóban); az USD-érték becslés, nem számla.
