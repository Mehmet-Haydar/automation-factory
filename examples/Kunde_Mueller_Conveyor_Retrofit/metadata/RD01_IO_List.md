---
title: RD01_IO_List — Kunde Müller Conveyor Retrofit
last_validated: 2026-05
status: ACTIVE
---

# RD01_IO_List — Kunde Müller Conveyor Retrofit

> AI extraction + human review (Gate 2 + Gate 3 in_progress). 47 signals detected.

---

## Frontmatter

```yaml
project_id: KMG-2026-001
project_name: Kunde_Mueller_Conveyor_Retrofit
customer: Kunde Müller GmbH
filled_by: AI Engine + Mehmet Haydar (review)
filled_at: 2026-05-15
output_language: DE
status: DRAFT
```

---

## Summary

- Total signals: 47
- DI: 24 | DO: 18 | AI: 3 | AO: 2
- Safety-related: 4 (E-Stop ×2, Light Curtain ×2) — ⚠️ on a standard PLC
- Module count: 5

---

## Signals

| Tag | Address | Type | Direction | Equipment | Description | NormalState | EngUnit | RangeMin | RangeMax | SafetyRelated | SourceModule | OldTag | Notes | Status |
|-----|---------|------|-----------|-----------|-------------|-------------|---------|----------|----------|---------------|--------------|--------|-------|--------|
| MOT_CV01_001_START | %I0.0 | BOOL | DI | Conveyor1 | Start button push (orig: Taste Start) | NO | | | | N | DI_001 | E_Start | Operator panel — FC30 NW1 (Schritt 10 trigger, AUTO mode + S M10.0) | Active |
| MOT_CV01_001_STOP | %I0.1 | BOOL | DI | Conveyor1 | Stop button push (orig: Taste Stop) | NC | | | | N | DI_001 | E_Stop_Btn | Operator panel | Active |
| MOT_CV01_001_RUN | %I0.2 | BOOL | DI | Conveyor1 | Motor running feedback (orig: Motor läuft) | NO | | | | N | DI_001 | E_Motor_Lauf | | Active |
| MOT_CV01_002_RUN | %I0.3 | BOOL | DI | Conveyor2 | Motor running feedback | NO | | | | N | DI_001 | E_Motor_Lauf_2 | | Active |
| MOT_CV01_001_FAULT | %I0.4 | BOOL | DI | Conveyor1 | Drive fault (orig: Antriebsstörung) | NC | | | | N | DI_001 | E_Stoerung | | Active |
| PC_LOAD_001 | %I0.5 | BOOL | DI | Loading | Photocell beam (orig: Lichtschranke Beladung) | NO | | | | N | DI_001 | E_LS_Beladen | Dual role: load detection + FC30 NW3 Schritt 20→30 step transition | Active |
| LS_LIM_001_TOP | %I0.6 | BOOL | DI | Conveyor1 | Limit switch top position | NC | | | | N | DI_001 | E_ES_Oben | | Active |
| LS_LIM_001_BOT | %I0.7 | BOOL | DI | Conveyor1 | Limit switch bottom position | NC | | | | N | DI_001 | E_ES_Unten | | Active |
| F_I_EStop_North | %I100.0 | BOOL | DI | Operator | Emergency stop NORTH panel (orig: NOT-AUS Nord) | NC | | | | **Y** | DI_safety | E_NotAus_N | ⚠️ Standard PLC — F-PLC migration required (FC10 NW5/NW6/NW12) | Active |
| F_I_EStop_South | %I100.1 | BOOL | DI | Operator | Emergency stop SOUTH panel | NC | | | | **Y** | DI_safety | E_NotAus_S | ⚠️ Standard PLC (FC10 NW5/NW6/NW12 — parallel to North) | Active |
| F_I_LC_Loading | %I100.2 | BOOL | DI | Loading | Light curtain loading zone (orig: Lichtvorhang Beladung) | NC | | | | **Y** | DI_safety | E_LV_Beladung | ⚠️ Bypass exists (FC10 NW8 — via `AN DB10.DBX0.2` maintenance mode) | Active |
| F_I_LC_Unloading | %I100.3 | BOOL | DI | Unloading | Light curtain unloading zone | NC | | | | **Y** | DI_safety | E_LV_Entladung | ⚠️ Standard PLC (FC10 NW9 — no bypass) | Active |
| MOT_CV01_001_OUT | %Q0.0 | BOOL | DO | Conveyor1 | Motor contactor command (orig: Schütz Motor) | | | | | N | DO_001 | A_Schuetz | FC10 NW8 — LC can be overridden while maintenance mode is active | Active |
| MOT_CV01_002_OUT | %Q0.1 | BOOL | DO | Conveyor2 | Motor contactor command | | | | | N | DO_001 | A_Schuetz_2 | FC10 NW9 — no LC bypass | Active |
| VAL_V01_OUT | %Q0.2 | BOOL | DO | Pneumatic | Valve V01 open (orig: Ventil 1 öffnen) | | | | | N | DO_001 | A_Ventil_1 | | Active |
| VAL_V02_OUT | %Q0.3 | BOOL | DO | Pneumatic | Valve V02 open | | | | | N | DO_001 | A_Ventil_2 | | Active |
| LIGHT_GREEN | %Q0.4 | BOOL | DO | Panel | Status lamp GREEN (orig: Lampe grün) | | | | | N | DO_001 | A_Lampe_Gruen | | Active |
| LIGHT_RED | %Q0.5 | BOOL | DO | Panel | Status lamp RED (orig: Lampe rot) | | | | | N | DO_001 | A_Lampe_Rot | | Active |
| SIREN_001 | %Q3.6 | BOOL | DO | Panel | Audio alarm (orig: Hupe) | | | | | N | DO_001 | A_Hupe | | Active |
| MASTER_CONTACTOR | %Q3.7 | BOOL | DO | Cabinet | Master contactor (orig: Hauptschütz) | | | | | **Y** | DO_001 | A_Hauptschuetz | ⚠️ E-Stop is cut from this output (FC10 NW5: `A I100.0 & A I100.1 & AN M50.0`) — M50.0 bypass risk! | Active |
| ANALOG_TT_TK_001 | %IW64 | INT | AI | Tank1 | Temperature sensor (orig: Temperatur Tank) | | °C | -20 | 200 | N | AI_001 | EW_Temp_Tank | Pt100 sensor | Active |
| ANALOG_PT_PI_001 | %IW66 | INT | AI | Pipe | Pressure sensor (orig: Druck Leitung) | | bar | 0 | 10 | N | AI_001 | EW_Druck | 4-20mA | Active |
| ANALOG_LT_TK_001 | %IW68 | INT | AI | Tank1 | Tank level (orig: Tank-Füllstand) | | % | 0 | 100 | N | AI_001 | EW_Niveau | Ultrasonic | Active |
| ANALOG_SP_OUT_001 | %QW64 | INT | AO | Conveyor1 | Drive speed setpoint (orig: Drehzahl Sollwert) | | % | 0 | 100 | N | AO_001 | AW_Drehzahl | 0-10V | Active |
| ANALOG_HEAT_OUT_001 | %QW66 | INT | AO | Heater | Heater PWM output | | % | 0 | 100 | N | AO_001 | AW_Heizung | 4-20mA | Active |
| ...22 more signals... | | | | | | | | | | | | | (truncated, real list has 47 rows) | |

---

## #UNKNOWNS (Gate 3 — a human will fill these in)

| Old Tag | Reason |
|----------|-------|
| MW100..MW150 (no symbol) | Not in the symbol table but used in OB1 — operator interview needed |
| EW_Druck (PT) | Range 0-10 bar or 0-16 bar unclear — drive datasheet needed |
| A_Reserve_1..A_Reserve_4 | Marked as reserve but the legacy code shows a wired connection |

---

## ⚠️ CRITICAL FINDINGS (carried to RD14)

1. **F_I_EStop_* + MASTER_CONTACTOR on a standard PLC:** FND001 SAFETY CRITICAL (RD14)
2. **Light curtain bypass logic (FC10 NW8):** `F_I_LC_Loading` is overridden while maintenance mode (`DB10.DBX0.2`) is active — risk assessment required
3. **47 signals mixing absolute addresses with German symbols:** FND002 NAMING MAJOR (RD14)
4. **🆕 E-Stop M50.0 maintenance bypass (FC10 NW5):** the `AN M50.0` logic can disable both NOT-AUS input chains in software → `MASTER_CONTACTOR` (Q3.7) stays energized. **FND008** SAFETY CRITICAL (RD14) — surfaced by the snippet analysis
5. **🆕 Broken E-Stop redundancy (FC10 NW5 vs NW6):** NW5 drives the master contactor via `AN M50.0` (with bypass); NW6 only sets an internal flag `M50.7` — not a physical redundancy, just a flag mirror. **FND009** SAFETY CRITICAL (RD14)

---

## Fill-in Notes (for this example)

- **100% of the 47 signals kept their OldTag** (German names in `(orig: ...)` format)
- **F-prefix only for safety-PLC signals** — migration proposal in RD14
- **Multi-lang description:** English + (orig: German) — German is also ready for `output_language=DE`
- **Memory markers (M*) are NOT in this list** — they go to RD02
- **#UNKNOWNS has 3 items awaiting human review**

### Snippet merge (2026-05-22)

- Source: `_input/old_code_snippet.awl` (FC10 E-Stop + FC30 Sequence)
- The **Notes** column of the 9 affected rows was enriched with FC/NW cross-references (`%I0.0`, `%I0.5`, `%I100.0..3`, `%Q0.0`, `%Q0.1`, `%Q3.7`)
- The snippet analysis surfaced 2 new CRITICAL FINDINGS (added to RD14 as **FND008/FND009**):
  - **FND008** — M50.0 software E-Stop bypass (NW5)
  - **FND009** — broken E-Stop redundancy (NW5 master contactor, NW6 just a flag)
- Raw snippet CSV: `_output/io_table_snippet.csv` (kept for the audit trail)
- **Note (2026-05-23):** during the initial merge these findings were temporarily named FND003/FND004; an ID clash was fixed (RD14 already used FND003=STRUCTURE, FND004=OBSOLETE_PLATFORM).

---

*v1.0.0 — This example RD01 output matches exactly the structure the real factory produces from AI extraction.*
