---
title: Raw Data Schema #01 — IO List
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-15
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md, GLOBAL_METADATA_SCHEMA.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_02_DATADICT.md, PROMPT_EXTRACT_IO_FROM_CODE.md]
schema: RAWDATA
rd_number: 01
deliverable: [RD01_IO_List.xlsx, RD01_IO_List.md, rd01_io.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [IEC 81346-2, ISA-5.1, IEC 61131-3 §6.3]
---

# MDSCHEMA_RAWDATA_01_IO.md — IO List Specification

> **This file defines how the project's "01 — IO List" raw data file should be structured.** First of the 14-point raw data pack. Mandatory for both retrofit (extraction from old code) and greenfield (design from scratch).

---

## 1. What Does This File Define?

This is **a "schema"** — meaning the actual IO list in the project (`RD01_IO_List.xlsx` / `.md`) must conform to this spec.

- ✅ Which columns are required, which optional
- ✅ Each column's data type, enum values, regex
- ✅ References to industry standards (IEC 81346, ISA-5.1)
- ✅ Excel ↔ MD ↔ JSON conversion rules
- ✅ What AI should watch for when filling this file

**This file is NOT:**
- ❌ The IO list itself (that's per-project, `<project>/RD01_IO_List.xlsx`)
- ❌ Extraction procedure (that's in `RETROFIT_EXTRACT_*.md` or `PROMPT_EXTRACT_IO_FROM_CODE.md`)
- ❌ Tag naming rule (that's in `GLOBAL_NAMING_STANDARD.md`)

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|------|--------|----------|-----------|
| **Retrofit** | Old PLC tag table + EPLAN + field walkdown | AI (`PROMPT_EXTRACT_IO_FROM_CODE.md`) then human correction | `script_consistency_check.py` |
| **Greenfield** | Customer brief + P&ID + machine layout | Human (guided by `GREENFIELD_DESIGN_*.md`) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** (extraction) → **Gate 3** (human correction) → **Gate 4** (validation → GREEN).

---

## 3. Excel Column Definition (Required)

`RD01_IO_List.xlsx` must contain the following columns **in this order**:

| # | Column | Type | Required | Enum / Regex | Description |
|---|--------|------|----------|---|---|
| 1 | `Tag` | string | ✅ | `^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$` | Global unique name of signal. Required by `GLOBAL_NAMING_STANDARD.md` |
| 2 | `Address` | string | ✅ | `^%[IQM][WBDX]?\d+(\.\d+)?$` | Physical address (e.g., `%I1.2`, `%QW20`) |
| 3 | `Type` | enum | ✅ | `BOOL`, `BYTE`, `WORD`, `DWORD`, `INT`, `DINT`, `REAL`, `TIME` | IEC 61131-3 §6.3 elementary types |
| 4 | `Direction` | enum | ✅ | `DI`, `DO`, `AI`, `AO` | Discrete/Analog × Input/Output |
| 5 | `Equipment` | string | ✅ | (free) | Associated physical equipment (e.g., `Conveyor1_Motor`, `Fluid_Tank_Level`) |
| 6 | `Description` | string | ✅ | min 5 characters | Signal purpose, NC/NO info, when active |
| 7 | `NormalState` | enum | ⚪ | `NC`, `NO`, `N/A` | Discrete inputs only. Normally Closed / Normally Open |
| 8 | `EngUnit` | string | ⚪ | (free) | For analog: `°C`, `bar`, `mm`, `m/s` |
| 9 | `RangeMin` | real | ⚪ | float | For analog: scaled minimum |
| 10 | `RangeMax` | real | ⚪ | float | For analog: scaled maximum |
| 11 | `SafetyRelated` | enum | ✅ | `Y`, `N` | Is this signal connected to F-PLC safety circuit? |
| 12 | `SourceModule` | string | ✅ | (free) | Which I/O module / rack (e.g., `PLC1_DI_001`, `ET200SP_Slot4`) |
| 13 | `OldTag` | string | ⚪ | (free) | **Retrofit only.** Old tag name in legacy code (for cross-reference) |
| 14 | `Notes` | string | ⚪ | (free) | Operator/engineer note, edge case |
| 15 | `Status` | enum | ✅ | `Active`, `Inactive`, `Spare` | Excel→MD conversion: only `Active` is transferred |

### 3.1 Column Descriptions (Detail)

**Tag (1):** Format `<DOMAIN>_<LOC>_<NUM>[_<SUFFIX>]`. Full table from `GLOBAL_NAMING_STANDARD.md` applies. Examples:
- `MOT_CV01_001_DRIVE` (motor, conveyor 1, sequence 001, drive output)
- `SEN_TANK_005_LEVEL` (sensor, tank, sequence 005, level)
- `VLV_INLET_002` (valve, inlet, sequence 002, no suffix)

**Address (2):** Siemens format default. Allen-Bradley adaptation planned (future v1.1.0).

**Type (3):** IEC 61131-3 §6.3 strict list. Vendor-specific types (TIME_OF_DAY, etc.) planned for v1.1.0.

**Direction (4):** Discrete/Analog × Input/Output classification. Universal across all vendors.

**Equipment (5):** Physical owner of signal. AI should **preserve original** German/Turkish names when extracting from old code, NOT translate (comment preservation rule).

**Description (6):** Minimum 5 characters. Do NOT allow AI to write `?` or `TODO` — rejected at Gate 4 if empty.

**NormalState (7):** NC signals must be logically inverted — critical for code generation. If left blank, AI defaults to NO (dangerous).

**SafetyRelated (11):** If `Y`, signal must be in F-PLC address range (`%I600.x` Siemens default). Check performed at Gate 4.

**Status (15):** Human marks at Gate 3. Inactive ones not provided to AI but preserved in Excel (for recovery).

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd01_io.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD01 — IO List",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["Tag", "Address", "Type", "Direction", "Equipment", "Description", "SafetyRelated", "SourceModule", "Status"],
    "additionalProperties": false,
    "properties": {
      "Tag":            { "type": "string", "pattern": "^[A-Z]+_[A-Z0-9]+_\\d{3}(_[A-Z]+)?$" },
      "Address":        { "type": "string", "pattern": "^%[IQM][WBDX]?\\d+(\\.\\d+)?$" },
      "Type":           { "enum": ["BOOL","BYTE","WORD","DWORD","INT","DINT","REAL","TIME"] },
      "Direction":      { "enum": ["DI","DO","AI","AO"] },
      "Equipment":      { "type": "string", "minLength": 1 },
      "Description":    { "type": "string", "minLength": 5 },
      "NormalState":    { "enum": ["NC","NO","N/A"] },
      "EngUnit":        { "type": "string" },
      "RangeMin":       { "type": "number" },
      "RangeMax":       { "type": "number" },
      "SafetyRelated":  { "enum": ["Y","N"] },
      "SourceModule":   { "type": "string", "minLength": 1 },
      "OldTag":         { "type": "string" },
      "Notes":          { "type": "string" },
      "Status":         { "enum": ["Active","Inactive","Spare"] }
    },
    "allOf": [
      {
        "if":   { "properties": { "Direction": { "enum": ["AI","AO"] } } },
        "then": { "required": ["EngUnit","RangeMin","RangeMax"] }
      },
      {
        "if":   { "properties": { "Direction": { "const": "DI" } } },
        "then": { "required": ["NormalState"] }
      }
    ]
  }
}
```

**Conditional rules:**
- Analog signal (AI/AO): `EngUnit`, `RangeMin`, `RangeMax` required
- Discrete input (DI): `NormalState` required

---

## 5. MD Output Format

When Gate 4 runs `script_excel_to_metadata.py`, it produces `RD01_IO_List.md`:

````markdown
---
title: RD01 — IO List
project: <project_name>
generated: YYYY-MM-DD
source: RD01_IO_List.xlsx
filter: Status=Active
total_signals: <N>
schema: RD01
---

# RD01 — IO List (Active Signals)

> This file is auto-generated from `RD01_IO_List.xlsx`. Do not edit manually — edit the Excel and re-run the script.

## Summary

- Total active signals: <N>
- Distribution: <DI>/<DO>/<AI>/<AO>
- Safety-related: <Ns>
- Number of modules: <Nm>

## Table

| Tag | Address | Type | Direction | Equipment | Description | NormalState | EngUnit | Range | Safety | Module |
|-----|---------|------|-----------|-----------|-------------|-------------|---------|-------|--------|--------|
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## AI Usage Note

When feeding this list to `04_AI_PROMPTS/code_gen/` prompts:
- Motor FB generation: `PROMPT_MOTOR_DOL.md` (etc.) reads tag list with `equipment` filter
- Valve FB generation: `PROMPT_CODE_GEN_FB_VALVE.md` same way
- Symbol table import: `script_openness_export.py` uses Address column
````

---

## 6. AI Filling Instructions (Retrofit)

AI fills this file via `PROMPT_EXTRACT_IO_FROM_CODE.md`. Instruction framework:

```
INPUT: Platform parser output (_input/_parsed.md), old tag table
TASK:
  1. Generate new tags from old ones conforming to GLOBAL_NAMING_STANDARD
  2. Store old tag in OldTag column (for cross-reference)
  3. Extract Description from comments — preserve original German/Turkish comments, do NOT translate
  4. Extract NormalState from signal name/comments (e.g., "Endschalter NC" → NC)
  5. For analog signals, extract RangeMin/Max and EngUnit from scaling blocks
  6. Mark signals in F-PLC address range (Siemens: %I600+) as SafetyRelated=Y
  7. Write "Active" to Status column (human corrects at Gate 3)
  8. DO NOT fill uncertain cells — leave blank (human will fill at Gate 3)
```

---

## 7. AI Filling Instructions (Greenfield)

On greenfield, AI cannot fill alone — human brief required. AI role:

```
INPUT: _input/brief.md (project definition, machine layout, P&ID)
TASK:
  1. Extract equipment from brief (motor, valve, sensor, etc.)
  2. Propose tags per GLOBAL_NAMING_STANDARD
  3. Propose typical IO counts (e.g., each DOL motor = 1 DO + 2 DI)
  4. Leave Address column BLANK (filled after hardware selection)
  5. Write "TBD" in SourceModule (determined in Phase 3 hardware selection)
  6. Status="Active" (human approves)
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **IEC 81346-2** | Equipment reference designation (KKS-like). Notation in `Equipment` column |
| **ISA-5.1** | Instrumentation symbols & identification. Tag suffix conventions for analog signals (`_LT` level transmitter, `_PT` pressure, etc.) |
| **IEC 61131-3 §6.3** | Elementary data types. `Type` column strictly limited to this list |
| **IEC 62443-3-3** | (future) Segregation requirements for SafetyRelated signals |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- AI writes Address as `%I 1.2` (with space) → regex rejects
- Tag with lowercase (`mot_pump_01`) → regex rejects
- Type as `bool` (lowercase) → enum rejects

### 9.2 Schema/Standard (Category B) — Validator catches
- Analog signal with empty EngUnit → conditional rule rejects
- NormalState left blank on DI → conditional rule rejects
- Two rows with same Address → uniqueness rule rejects (script_consistency_check)

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ `Endschalter_Oben` interpreted by AI as "Limit Switch Up" in Description — correct, but original German symbol may be lost → OldTag protected
- ⚠️ Emergency stop button marked SafetyRelated=N (AI treated as normal DI) — cannot be caught without F-PLC address; human must fix at Gate 3
- ⚠️ NC/NO info missing in old comments → AI defaults to NO; dangerous, operator verification required

### 9.4 Correction Request Template

> "Error in RD01 row X: <category> issue: <description>. Expected: <correct value>. Fix, re-generate that row only."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD01_IO_List.xlsx` copied as blank template. Contents:
- 15 columns, header row + 1 example row (to delete)
- Data Validation (Excel): dropdown in Type, Direction, Status, SafetyRelated columns
- Conditional Formatting: Status=Inactive rows gray background

---

## 11. Related Files

- **Spec family:** `MDSCHEMA_RAWDATA_02..12_*.md`
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_IO_FROM_CODE.md`
- **Extraction guide:** `02_PROJECT_TYPES/RETROFIT/RETROFIT_IO_EXTRACT.md` (existing, compatible with this spec)
- **Design guide:** `02_PROJECT_TYPES/GREENFIELD/GREENFIELD_IO_NEWDESIGN.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD01_IO_List.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd01_io.schema.json`
- **Dependent prompts:** All `04_AI_PROMPTS/code_gen/**/*.md` (read IO list as input)
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_01_IO.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.0.0 — First spec of the 14-Point Raw Data Pack idea. Remaining 11 specs follow this pattern. v1.1.0 roadmap: Allen-Bradley address format, vendor-specific type list expansion.*
