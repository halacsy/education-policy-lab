# Költség- és időjelentés

Téma: `korai-szelekcio` — az átláthatósági elv része: ennyi időbe és ennyibe került ennek a problémának a feldolgozása (a(z) 9. körtől számított érában).

- **Falióra-idő (körök összesen):** 12p 54mp
- **Tokenek:** 516,941 (bemenet: 432,690, kimenet: 84,251)
- **Becsült költség:** $1.00 USD (konfigurálható ártáblából — config/system_config.json pricing)
- **Mért / nem mért hívások:** 36 / 0 (a CLI/előfizetéses backendek hívásonként nem mérnek tokent — az ő költségük itt nem szerepel)

## Modellenként

| modell | bemeneti token | kimeneti token | becsült USD |
|---|---|---|---|
| claude-haiku-4-5 | 167,883 | 18,089 | $0.26 |
| claude-sonnet-5 | 67,520 | 36,255 | $0.75 |

## Körönként

| kör | idő | token | becsült USD |
|---|---|---|---|
| 9 | 12p 54mp | 516,941 | $1.00 |

A számok forrása a körök `round_log.json`-ja (audit-nyom a repóban); az USD-érték becslés, nem számla.
