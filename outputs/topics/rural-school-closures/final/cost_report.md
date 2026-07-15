# Költség- és időjelentés

Téma: `rural-school-closures` — az átláthatósági elv része: ennyi időbe és ennyibe került ennek a problémának a feldolgozása (a(z) 1. körtől számított érában).

- **Falióra-idő (körök összesen):** 40p 23mp
- **Tokenek:** 493,044 (bemenet: 408,009, kimenet: 85,035)
- **Becsült költség:** $1.02 USD (konfigurálható ártáblából — config/system_config.json pricing)
- **Mért / nem mért hívások:** 36 / 0 (a CLI/előfizetéses backendek hívásonként nem mérnek tokent — az ő költségük itt nem szerepel)

## Modellenként

| modell | bemeneti token | kimeneti token | becsült USD |
|---|---|---|---|
| claude-haiku-4-5 | 179,983 | 32,202 | $0.34 |
| claude-sonnet-5 | 90,211 | 27,243 | $0.68 |

## Körönként

| kör | idő | token | becsült USD |
|---|---|---|---|
| 1 | 40p 23mp | 493,044 | $1.02 |

A számok forrása a körök `round_log.json`-ja (audit-nyom a repóban); az USD-érték becslés, nem számla.
