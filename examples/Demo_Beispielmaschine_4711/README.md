# Demo_Beispielmaschine_4711 — assembler demo (no API key needed)

> **100% synthetic.** Every name, number, signal and code line in this
> folder is fictional and exists only to demonstrate the pipeline.

A second, minimal demo next to `Kunde_Mueller_Conveyor_Retrofit`: it
shows the **deterministic half** of the retrofit pipeline — the part a
reviewer can run **without any AI key**.

## What's inside

| Path | What it demonstrates |
|------|----------------------|
| `_raw/legacy_code/4711Z0.SEQ` | STEP5 symbol table (Zuordnungsliste) — dropped in as-is |
| `_raw/legacy_code/4711_OB1.awl` | Old AWL listing (star-delta hydraulic pump, conveyor, valve) |
| `metadata/RD01_IO_List.md` | The reviewed/approved IO list (status: done) — normally produced by AI pre-analysis + engineer review |
| `_output/scl/` + `REPORTS/ASSEMBLY_REPORT.md` | **Committed assembler output** so you can inspect the result without running anything |

## Try it yourself (2 minutes, no keys)

1. `start.bat` → **Open Project** → this folder.
2. Click **Assemble Program** (Gate 3/4 action).
3. Compare your `REPORTS/ASSEMBLY_REPORT.md` with the committed one:
   - `MOT_HYD_001` → **FB_Motor_StarDelta** (matched via "star-delta" in
     the description — includes welded-contactor protection)
   - `MOT_CONV_002` → **FB_Motor_DOL**
   - `VLV_COOL_001` → **FB_Valve_OnOff**
   - `SEN_OILTEMP_001` → **FB_AnalogScale**
   - `ENC_SHAFT_001` → **#UNKNOWN** — on purpose: encoders have no
     library block yet, and the assembler refuses to guess. This is the
     honesty mechanism, not a bug.
4. `_output/scl/` now holds TIA external sources: library FBs (verbatim,
   SHA-256-proven), `iDB_*.db` instance DBs and `OB_Main.scl` with real
   field-signal bindings — importable via **Send to TIA** or
   **Export TIA**.

## What this demo does NOT show

The AI half (PDF extraction review, 6-step pre-analysis writing RD
drafts, sequence-FB generation) needs API keys — see
[docs/USER_GUIDE_RETROFIT.md](../../docs/USER_GUIDE_RETROFIT.md) for the
full click path.
