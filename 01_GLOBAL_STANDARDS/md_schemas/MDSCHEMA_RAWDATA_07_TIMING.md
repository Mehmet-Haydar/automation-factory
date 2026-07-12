---
title: Raw Data Schema #07 — Timing
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_03_FLOWCHART.md, MDSCHEMA_RAWDATA_06_MOTION.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_03_FLOWCHART.md, MDSCHEMA_RAWDATA_08_ALARM.md, PROMPT_EXTRACT_TIMING_FROM_CODE.md]
schema: RAWDATA
rd_number: 07
deliverable: [RD07_Timing.xlsx, RD07_Timing.md, rd07_timing.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [IEC 61131-3 §2.5.2, IEC 61131-3 §6.5.3]
---

# MDSCHEMA_RAWDATA_07_TIMING.md — Timing Specification

> **This file defines how the project's "07 — Timing" raw data file should be structured.** Documents every timer usage, wait durations, cycle intervals and watchdog times. Correct timing values are critical for machine safety and production quality.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual timing-parameter list (`RD07_Timing.xlsx` / `.md`) must conform to this spec.

- ✅ Each timer's identifier, type and preset value
- ✅ Timer trigger and reset conditions
- ✅ Which RD03 step or RD08 alarm it relates to
- ✅ Special tagging of watchdog timers
- ✅ IEC 61131-3 timer type (TON, TOF, TP, TONR)

**This file is NOT:**
- ❌ Actual timer instance DBs (that's RD02 DataDict — instance DB data)
- ❌ OB cycle time (that's system configuration — TIA Portal OB setting)
- ❌ Alarm delays (that's RD08 Alarm — alarm filter time, referenced here)

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Legacy PLC code timer instance DBs + TON/TOF/TP calls | AI (`PROMPT_EXTRACT_TIMING_FROM_CODE.md`) then human correction | `script_consistency_check.py` |
| **Greenfield** | Process requirements + machine kinematics analysis + safety requirements | Human (process engineer + automation engineer) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** → **Gate 3** → **Gate 4** (GREEN). RD07 feeds the RD03 Flowchart `TimerRef` column.

---

## 3. Excel Column Definition (Required)

`RD07_Timing.xlsx` must contain the following columns **in this order**:

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `TimerID` | string | ✅ | `^TMR_[A-Z0-9]+_\d{3}$` | Timer identifier (e.g., `TMR_STEP010_001`, `TMR_WDOG_001`) |
| 2 | `TimerName` | string | ✅ | min 3 characters, EN | Short timer name (used in code generation) |
| 3 | `TimerType` | enum | ✅ | `TON`, `TOF`, `TP`, `TONR` | IEC 61131-3 §2.5.2 timer types |
| 4 | `PresetValue` | string | ✅ | `^T#\d+(\.\d+)?(ms\|s\|m\|h)$` | Preset duration, IEC TIME format (e.g., `T#5s`, `T#500ms`, `T#2m`) |
| 5 | `Function` | enum | ✅ | `StepDelay`, `Debounce`, `Watchdog`, `Timeout`, `CycleControl`, `AlarmFilter`, `Other` | Timer's purpose |
| 6 | `TriggerCondition` | string | ✅ | (free — boolean expression) | Condition that starts the timer |
| 7 | `ResetCondition` | string | ✅ | (free — boolean expression) | Condition that resets the timer. `IN_FALLING_EDGE` or a specific condition |
| 8 | `OutputAction` | string | ✅ | (free) | What the Q/ET output does (step transition, raise alarm, etc.) |
| 9 | `LinkedStep` | string | ⚪ | `^S\d{3}[A-Z]?$` | Cross-reference to RD03 Flowchart StepID |
| 10 | `LinkedAlarm` | string | ⚪ | `^ALM\d{4}$` | Cross-reference to RD08 Alarm AlarmID (timeout alarm) |
| 11 | `DB_Instance` | string | ⚪ | (free) | Timer instance DB variable (cross-reference to RD02 VarName) |
| 12 | `IsWatchdog` | enum | ✅ | `Y`, `N` | Watchdog timer? (critical safety tag) |
| 13 | `Notes` | string | ⚪ | (free) | Tuning note, field experience, fine-tuning range |
| 14 | `Status` | enum | ✅ | `Active`, `Inactive`, `Spare` | Renamed to English (2026-06-10); legacy Turkish literals (`Aktif`/`Pasif`/`Taslak`/`Yedek`) in existing projects remain readable by the tooling |

### 3.1 Column Descriptions (Detail)

**TimerID (1):** Format `TMR_<SCOPE>_<NUM>`. Scope = the related step, system or equipment. Examples:
- `TMR_STEP010_001` → first timer of step S010
- `TMR_WDOG_001` → watchdog timer
- `TMR_DEBOUNCE_001` → debounce timer

**TimerType (3):**
- `TON` → Turn-On Delay: T# after IN goes TRUE, Q=TRUE
- `TOF` → Turn-Off Delay: T# after IN goes FALSE, Q=FALSE
- `TP` → Pulse: rising edge of IN → Q=TRUE for T#, then reset
- `TONR` → Retentive (cumulative): retains value across power cycles (Siemens: S_ODTS)

**PresetValue (4):** Strictly IEC TIME format: `T#100ms`, `T#5s`, `T#2m30s`. A plain number (`500`) is rejected — unit ambiguous.

**Function (5):**
- `StepDelay` → wait time inside a sequence step
- `Debounce` → signal-noise filtering (physical contact bounce)
- `Watchdog` → detects that the expected event did not occur (timeout)
- `Timeout` → alarm trigger on overrun
- `CycleControl` → periodic trigger outside the OB cycle
- `AlarmFilter` → filtering transient alarms (linked to RD08)

**IsWatchdog (12):** When `Y`, the timeout of this timer typically triggers an alarm (linked via RD08 LinkedAlarm). Watchdog timers receive special review — too short → false alarms; too long → dangerous wait.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd07_timing.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD07 — Timing",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["TimerID","TimerName","TimerType","PresetValue","Function","TriggerCondition","ResetCondition","OutputAction","IsWatchdog","Status"],
    "additionalProperties": false,
    "properties": {
      "TimerID":          { "type": "string", "pattern": "^TMR_[A-Z0-9]+_\\d{3}$" },
      "TimerName":        { "type": "string", "minLength": 3 },
      "TimerType":        { "enum": ["TON","TOF","TP","TONR"] },
      "PresetValue":      { "type": "string", "pattern": "^T#\\d+(\\.\\d+)?(ms|s|m|h)$" },
      "Function":         { "enum": ["StepDelay","Debounce","Watchdog","Timeout","CycleControl","AlarmFilter","Other"] },
      "TriggerCondition": { "type": "string", "minLength": 1 },
      "ResetCondition":   { "type": "string", "minLength": 1 },
      "OutputAction":     { "type": "string", "minLength": 1 },
      "LinkedStep":       { "type": "string", "pattern": "^S\\d{3}[A-Z]?$" },
      "LinkedAlarm":      { "type": "string", "pattern": "^ALM\\d{4}$" },
      "DB_Instance":      { "type": "string" },
      "IsWatchdog":       { "enum": ["Y","N"] },
      "Notes":            { "type": "string" },
      "Status":           { "enum": ["Active","Inactive","Spare"] }
    },
    "allOf": [
      {
        "if":   { "properties": { "IsWatchdog": { "const": "Y" } } },
        "then": { "required": ["LinkedAlarm"] }
      }
    ]
  }
}
```

**Conditional rule:** for timers with `IsWatchdog=Y`, `LinkedAlarm` is mandatory (the alarm raised by the watchdog must be documented).

---

## 5. MD Output Format

`RD07_Timing.md` produced at Gate 4:

````markdown
---
title: RD07 — Timing
project: <project_name>
generated: YYYY-MM-DD
source: RD07_Timing.xlsx
filter: Status=Active
total_timers: <N>
watchdog_count: <Nw>
schema: RD07
---

# RD07 — Timing

## Timing Summary

| TimerID | TimerType | PresetValue | Function | IsWatchdog | LinkedStep |
|---------|-----------|-------------|----------|------------|------------|
| TMR_STEP010_001 | TON | T#5s | StepDelay | N | S010 |
| TMR_WDOG_001 | TON | T#30s | Watchdog | Y | S020 |
| ... | ... | ... | ... | ... | ... |

## Watchdog Timers

| TimerID | PresetValue | LinkedAlarm | OutputAction |
|---------|-------------|-------------|--------------|
| TMR_WDOG_001 | T#30s | ALM0010 | StepTimeout → Safe stop |
````

---

## 6. AI Filling Instructions (Retrofit)

```
INPUT: _parsed.md Section 5 (timer instance DBs) + Section 7 (FB calls, TON/TOF/TP)
TASK:
  1. Find all TON/TOF/TP/TONR calls → one row each
  2. PresetValue: derive from the PT parameter, convert to IEC TIME format (ms → T#Xms)
  3. TriggerCondition: the boolean expression on the IN parameter
  4. DB_Instance: the related timer instance variable (cross-reference to RD02)
  5. LinkedStep: the sequence step the timer sits inside (RD03 cross-reference)
  6. IsWatchdog: Y if comments mention "timeout", "watchdog", "überwach"
  7. OutputAction: what the Q output does (step transition or alarm)
  8. If legacy code uses a DB variable instead of a literal preset, note it in Notes
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: _input/brief.md + process requirements + RD03 Flowchart draft
TASK:
  1. Add a TON timer for any RD03 step that has a wait time
  2. Add a watchdog timer for every critical step (max wait time)
  3. Debounce timers: physical contact = propose T#20-50ms; sensor = T#5-10ms
  4. PresetValue: fill from process-engineer-supplied durations; if none, use "T#0s" AND note "to be tuned on site" in Notes
  5. For every watchdog timer create a matching RD08 alarm (LinkedAlarm)
  6. TONR: for processes that must continue across power loss (e.g., heating, cooling accumulator)
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **IEC 61131-3 §2.5.2** | Standard function block timers — TimerType enum (TON, TOF, TP, TONR) |
| **IEC 61131-3 §6.5.3** | TIME data type — PresetValue format (T# prefix) |
| **IEC 62061 §6.7.5** | Watchdog timer requirements — IsWatchdog column + mandatory LinkedAlarm |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- TimerID `TIMER_001` (not TMR prefix) → regex reject
- PresetValue `5000` (no T# prefix) → regex reject
- PresetValue `T#5sec` (must be `s` not `sec`) → regex reject

### 9.2 Schema/Standard (Category B) — Validator catches
- IsWatchdog=Y but LinkedAlarm blank → conditional rule reject
- TimerType `TONI` (not in the enum list) → enum reject

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ Legacy code used an `IEC_TIMER` instance DB — AI may not infer the `TON` type; the DB struct definition must be inspected
- ⚠️ PresetValue given as a milliseconds integer (`5000`) in legacy code — must be converted to `T#5s`; a math error creates a 1000× mistake
- ⚠️ Watchdog timer marked `IsWatchdog=N` (AI didn't read the comment) → timeout alarm not associated; safety gap
- ⚠️ TOF used but AI guessed TON — TriggerCondition logic is inverted, OutputAction mistimed
- ⚠️ TON used where TONR (retentive) was required — accumulated time resets on power loss; critical in heating/cooling cycles

### 9.4 Correction Request Template

> "Error in RD07 row `<TimerID>`: <category> issue: <description>. Expected: <correct value>. Fix only that row."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD07_Timing.xlsx` blank template:
- 14 columns, header + 3 example rows (TON step, TOF deactivate, Watchdog)
- Data Validation: TimerType, Function, IsWatchdog, Status dropdowns
- Conditional Formatting: rows with IsWatchdog=Y get an orange background (special attention)

---

## 11. Related Files

- **Dependency:** `MDSCHEMA_RAWDATA_03_FLOWCHART.md` (TimerRef cross-reference)
- **Dependency:** `MDSCHEMA_RAWDATA_08_ALARM.md` (timeout alarms, LinkedAlarm)
- **Next spec:** `MDSCHEMA_RAWDATA_08_ALARM.md`
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_TIMING_FROM_CODE.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD07_Timing.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd07_timing.schema.json`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_07_TIMING.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Deliverable filenames updated to `RD07_Timing.xlsx/.md` to match actual project files. Status enum renamed to `Active/Inactive/Spare` (English, 2026-06-10 coordinated update; see RD02 spec §3.1). v1.2.0 roadmap: OB cycle time analysis, jitter tolerance documentation, power-loss scenario documentation with TONR.*
