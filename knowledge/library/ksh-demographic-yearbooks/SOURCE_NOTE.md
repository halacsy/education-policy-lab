# SOURCE NOTE — ksh-demographic-yearbooks

Download date: 2026-07-05

KSH = Központi Statisztikai Hivatal (Hungarian Central Statistical Office). Instead of the print/priced "Demográfiai évkönyv", this directory stores the equivalent official STADAT summary tables (the live, freely downloadable dissemination channel of the same vital statistics).

## Files in this directory

### 1. nep0006-live-births-total-fertility-rate.xlsx / .csv
- **What it is:** STADAT table **22.1.1.6. "Élveszületések és teljes termékenységi arányszám"** — live births (count and per 1,000 population) and total fertility rate. Decennial anchor years 1900–1941, then annual from 1949 through 2025 (e.g. 1990: annual series fully covered; 2024: 77,511 live births, TFR 1.39; 2025: 72,000, TFR 1.31).
- **URLs used:** https://www.ksh.hu/stadat_files/nep/hu/nep0006.xlsx and https://www.ksh.hu/stadat_files/nep/hu/nep0006.csv (table page: https://www.ksh.hu/stadat_files/nep/hu/nep0006.html)

### 2. nep0001-live-births-population-indicators.xlsx / .csv
- **What it is:** STADAT table **22.1.1.1. "A népesség, népmozgalom főbb mutatói"** — headline population and vital-statistics indicators (population number, mean age, live births, deaths, natural change, marriages, life expectancy, etc.) for benchmark years 1941–1990 and annually 2001–2026.
- **URLs used:** https://www.ksh.hu/stadat_files/nep/hu/nep0001.xlsx and https://www.ksh.hu/stadat_files/nep/hu/nep0001.csv (table page: https://www.ksh.hu/stadat_files/nep/hu/nep0001.html)

## License basis
KSH dissemination data are public sector information. Per KSH's terms of use, STADAT tables and other published data may be freely used and re-published **with attribution to the source** (required citation: "Forrás: KSH" / "Source: HCSO"). The CSV/XLSX files themselves carry the embedded provenance note "Ezt az állományt a Központi Statisztikai Hivatal Összefoglaló táblák (STADAT) rendszeréből töltötte le." Attribution: **Source: Hungarian Central Statistical Office (KSH), STADAT tables 22.1.1.1 and 22.1.1.6.**

## Note on the Demográfiai évkönyv
The "Demográfiai évkönyv" (Demographic Yearbook of Hungary) is a KSH publication sold in print/CD form and not fully downloadable as a free PDF; its underlying vital-statistics series are exactly what the STADAT tables above provide free of charge, so the tables were stored instead of a pointer-only entry.

## File encoding note
The CSV files are in Windows-1250 (Central European) encoding with semicolon separators — convert with `iconv -f WINDOWS-1250 -t UTF-8` before parsing. The XLSX files are UTF-8-safe.
