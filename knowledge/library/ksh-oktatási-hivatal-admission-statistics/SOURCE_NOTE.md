# SOURCE NOTE — ksh-oktatási-hivatal-admission-statistics

Download date: 2026-07-05

Official statistics on the Hungarian secondary-school admission process (középfokú felvételi eljárás, KIFIR) from the Oktatási Hivatal (Educational Authority), plus the KSH education table covering gimnázium enrolment including 6/8-year (early-selective) gimnázium pupils.

## Files in this directory

### 1. oh-kozepfoku-irasbeli-felveteli-eredmenyek-2007-2026.pdf (~1.9 MB, 68 pages)
- **What it is:** Oktatási Hivatal: "A középfokú írásbeli felvételi vizsgadolgozatok eredményei 2007–2026" — official score-distribution statistics of the central written entrance examinations (Hungarian and mathematics) for 4-, 6- and 8-year secondary programmes, every year from 2007 to 2026.
- **URL used:** https://www.oktatas.hu/pub_bin/dload/kozoktatas/beiskolazas/2026/OH_honlap_felveteli_eredmenyek_2007_2026.pdf (linked from https://www.oktatas.hu/kozneveles/kozepfoku_felveteli_eljaras/prezentaciok_tanulmanyok)

### 2. oh-felveteli-a-kozepfoku-iskolakban-2025-2026-tanev.pptx (~890 KB)
- **What it is:** Oktatási Hivatal official presentation "Felvételi a középfokú iskolákban a 2025/2026. tanévben" — headline admission-round statistics (advertised places, applications, admission rates by institution type, including 6- and 8-year gimnázium tracks) for the latest completed KIFIR round.
- **URL used:** https://www.oktatas.hu/pub_bin/dload/kozoktatas/beiskolazas/2026/Felveteli_a_kozepfoku_iskolakban_a_2025_2026._tanevben.pptx (same OH statistics page as above; the page hosts equivalent presentations for every year back to 2005/2006)

### 3. ksh-okt0014-gimnaziumi-neveles-oktatas.xlsx / .csv
- **What it is:** KSH STADAT table **23.1.1.14. "Gimnáziumi nevelés és oktatás"** — annual gimnázium statistics from school year 1990/1991 to 2025/2026: schools, classrooms, teachers, pupils, and crucially the column "Nappali oktatásban tanulókból 5–8. évfolyamos" (full-time gimnázium pupils in grades 5–8, i.e. the lower grades of 6- and 8-year gimnázium), which allows computing the early-selective gimnázium enrolment share over time (e.g. 1991/92: 3,761; 2025/26: 26,142 pupils).
- **URLs used:** https://www.ksh.hu/stadat_files/okt/hu/okt0014.xlsx and https://www.ksh.hu/stadat_files/okt/hu/okt0014.csv (table page: https://www.ksh.hu/stadat_files/okt/hu/okt0014.html)

## License basis
- **Oktatási Hivatal files:** Official publications of a Hungarian public authority, published on oktatas.hu explicitly for public information about the admission procedure (közérdekű adatok / public-interest data); freely accessible without registration.
- **KSH file:** Public sector information; KSH permits free reuse and republication of STADAT tables with source attribution ("Forrás: KSH"). Attribution: **Source: Hungarian Central Statistical Office (KSH), STADAT table 23.1.1.14.**

## File encoding note
The KSH CSV is Windows-1250 encoded with semicolon separators (`iconv -f WINDOWS-1250 -t UTF-8` before parsing).
