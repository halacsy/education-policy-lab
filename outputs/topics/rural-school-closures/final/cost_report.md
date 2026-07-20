# Költség- és időjelentés

Téma: `rural-school-closures` — az átláthatósági elv része: ennyi időbe és ennyibe került ennek a problémának a feldolgozása (a(z) 2. körtől számított érában).

- **Falióra-idő (körök összesen):** 59p 12mp
- **Tokenek:** 3,106,637 (bemenet: 2,654,799, kimenet: 451,838)
- **Becsült költség:** $11.12 USD (konfigurálható ártáblából — config/system_config.json pricing)
- **Mért / nem mért hívások:** 133 / 0 (a CLI/előfizetéses backendek hívásonként nem mérnek tokent — az ő költségük itt nem szerepel)

## Modellenként

| modell | bemeneti token | kimeneti token | becsült USD |
|---|---|---|---|
| claude-haiku-4-5 | 372,501 | 136,162 | $1.05 |
| claude-opus-4-8 | 138,908 | 5,429 | $0.83 |
| claude-sonnet-5 | 1,798,179 | 255,962 | $9.23 |

## Körönként

| kör | idő | token | becsült USD |
|---|---|---|---|
| 2 | 46p 45mp | 2,720,123 | $10.14 |
| 3 | 12p 26mp | 386,514 | $0.98 |

A számok forrása a körök `round_log.json`-ja (audit-nyom a repóban); az USD-érték becslés, nem számla.
