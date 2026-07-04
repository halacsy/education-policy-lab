# Scenario template

Every policy scenario MUST contain every field below (verify check 5).
Machine-readable form: one object in `scenarios.json`; human-readable form:
one section per scenario in `scenarios.en.md` / `scenarios.hu.md`.

```
## <ID> — <title>

**Goal** (Cél)
  What state of the world the scenario tries to reach.

**Mechanism** (Mechanizmus)
  The causal chain from intervention to goal. Each causal claim carries an
  evidence-status tag.

**Evidence status** (Bizonyítékstátusz)
  Overall: strong / moderate / weak / contested — with the key sources.

**Assumptions** (Feltevések)
  What must be true, and is not itself evidenced, for the mechanism to work.

**Expected benefits** (Várható előnyök)
  Who gains what; tagged with evidence status.

**Equity impact** (Méltányossági hatás)
  Distributional consequences, including possible harms.

**Cost categories** (Költségkategóriák)
  One-off / recurring; fiscal / human / political-capital. Orders of
  magnitude only unless evidenced.

**Implementation steps** (Megvalósítási lépések)
  Ordered steps, each with actor and rough timeline.

**Political risks** (Politikai kockázatok)
  Who opposes, why, with what power; reversal risk.

**Uncertainties** (Bizonytalanságok)
  What we do not know; confidence level per item; what evidence would
  reduce it.
```

Scenario IDs are stable across languages and rounds (`S1`, `S2`, ...). The
HU and EN files must contain identical ID sets and section structure
(translation_checker enforces).
