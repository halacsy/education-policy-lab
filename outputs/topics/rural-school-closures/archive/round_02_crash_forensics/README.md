# Round 2 crash-leg forensics (2026-07-16)

Ez a könyvtár a round 2 ELSŐ, több szakaszban megszakadt futásának teljes
nyers rekordja — karanténban, mert módszertanilag érvénytelen: a szakaszok
között a regression-revert + relaunch-reapply kölcsönhatása 5 direktívát
halmozott fel egyszerre (one-change-per-round sérült), és a közbülső
delta-mérések (evidence_tag_all -0.123, scenario_crossref -0.296) vegyes
direktíva-állapotú artifactokon születtek (attempts_log.round2_crashlegs.jsonl).
A teljes elemzés: issue #27 + docs/experiments/2026-07-16-research-token-
budget-and-search-outage.md. A kanonikus round 2 ez UTÁN futott, tiszta
állapotból. A rejections.jsonl és round_meta.json itt őrzi a nap tanulságait.
