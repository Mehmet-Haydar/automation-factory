---
title: Raw Data Schema #02 — Data Dictionary
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md, MDSCHEMA_RAWDATA_01_IO.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_03_FLOWCHART.md, PROMPT_EXTRACT_DATADICT_FROM_CODE.md]
schema: RAWDATA
rd_number: 02
deliverable: [RD02_DataDict.xlsx, RD02_DataDict.md, rd02_datadict.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [IEC 61131-3 §6.4, IEC 61131-3 §6.5, PLCopen]
---

# MDSCHEMA_RAWDATA_02_DATADICT.md — Data Dictionary Specification

> **This file defines how the project's "02 — Data Dictionary" raw data file should be structured.** Second step after the IO list (RD01): covers everything other than physical signals — memory markers, DB variables, UDT members. The data layer that feeds the RD10 FBSpec.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual data dictionary in the project (`RD02_DataDict.xlsx` / `.md`) must conform to this spec.

- ✅ Which columns are required, which optional
- ✅ Each column's data type, enum values, regex
- ✅ DB / UDT / Memory Marker distinctions and scope rules
- ✅ Excel ↔ MD ↔ JSON conversion rules
- ✅ What AI should watch for when filling this file

**This file is NOT:**
- ❌ The data dictionary itself (that's per-project, `<project>/RD02_DataDict.xlsx`)
- ❌ FB/FC interface definition (that's RD10 FBSpec)
- ❌ IO signals (that's RD01 IO List — variables with physical addresses don't go here)

**Difference vs RD01:** RD01 = signals with physical addresses (`%I`, `%Q`). RD02 = variables in internal memory: memory markers (`%M`), DB fields, UDT members, instance DBs.

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Old PLC symbol table + UDT definitions + DB contents | AI (`PROMPT_EXTRACT_DATADICT_FROM_CODE.md`) then human correction | `script_consistency_check.py` |
| **Greenfield** | Design brief + state machine design + FB interface decisions | Human (guided by `GREENFIELD_DESIGN_DATADICT.md`) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** (extraction) → **Gate 3** (human correction) → **Gate 4** (validation → GREEN).

RD02 works together with RD10 (FBSpec): while FBSpec defines the FB/FC interface, DataDict covers that block's internal STAT/TEMP variables and the related instance DBs.

---

## 3. Excel Column Definition (Required)

`RD02_DataDict.xlsx` must contain the following columns **in this order**:

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `VarName` | string | ✅ | `^[A-Za-z_][A-Za-z0-9_]{0,127}$` | Variable name. IEC 61131-3 identifier rules |
| 2 | `Scope` | enum | ✅ | `GlobalDB`, `InstanceDB`, `UDT`, `MemoryMarker`, `TempVar` | Context in which the variable lives |
| 3 | `ParentBlock` | string | ✅ | (free) | Which DB / UDT / OB it lives in (e.g., `DB_Motor_Pump01`, `UDT_MotorData`, `OB1`) |
| 4 | `Type` | string | ✅ | IEC + UDT name | `BOOL`, `BYTE`, `WORD`, `DWORD`, `INT`, `DINT`, `LINT`, `REAL`, `LREAL`, `TIME`, `DATE`, `STRING[N]`, `ARRAY[...]`, or a UDT name |
| 5 | `Offset` | string | ⚪ | `^\d+(\.\d)?$` | Byte[.bit] offset inside the DB (e.g., `0.0`, `2`, `4.0`). Only for DB and UDT |
| 6 | `InitValue` | string | ⚪ | (free) | Initial/default value (`FALSE`, `0`, `16#0000`, `T#0s`) |
| 7 | `Retain` | enum | ✅ | `Y`, `N`, `N/A` | Is the value retained across power loss? (`N/A` = MemoryMarker or TempVar) |
| 8 | `Description` | string | ✅ | min 5 characters | Variable purpose, where it's used, when it's updated |
| 9 | `LinkedTag` | string | ⚪ | (free) | Linked IO signal (cross-reference to RD01 Tag column) |
| 10 | `OldVar` | string | ⚪ | (free) | **Retrofit only.** Variable name in the legacy code |
| 11 | `Notes` | string | ⚪ | (free) | Edge case, safety note, operator note |
| 12 | `Status` | enum | ✅ | `Active`, `Inactive`, `Spare` | Inactive ones are not handed to AI. Enum values renamed to English (2026-06-10); the JSON schema, templates and example data now use `Active/Inactive/Spare`. Legacy Turkish literals in existing projects remain readable by the tooling. |

### 3.1 Column Descriptions (Detail)

**VarName (1):** IEC 61131-3 §6.4 rule: starts with a letter or underscore, followed by letters/digits/underscores. Case-insensitive at the language level, but Factory practice: `camelCase` or `PascalCase` (see `GLOBAL_NAMING_STANDARD.md`). Different from the tag format (`MOT_CV01_001`) — VarName is a code variable.

**Scope (2):**
- `GlobalDB` → DB variable shared by multiple OB/FB/FC
- `InstanceDB` → instance DB variable for one FB (STAT members go here)
- `UDT` → User Data Type member (struct definition, not yet instantiated)
- `MemoryMarker` → `%M` address (bit, byte, word) — for backwards compatibility; not used in new code
- `TempVar` → TEMP variable inside an OB/FB/FC (cleared on each call, does not live in a DB)

**Type (4):** IEC 61131-3 §6.5 elementary types + `STRING[n]` (n = max length) + `ARRAY[0..n] OF <type>` + existing UDT names. Vendor-specific types (e.g., Siemens `VARIANT`, `ANY`) go into `Notes`.

**Offset (5):** Only valid for `GlobalDB`, `InstanceDB`, `UDT` scopes. Left blank for `TempVar` and `MemoryMarker`.

**Retain (7):** Critical for preventing data loss across power cycles. A wrong `Y` → unnecessary NVRAM usage. A wrong `N` → data loss on restart. If unsure, AI leaves it blank.

**LinkedTag (9):** Cross-reference to RD01. E.g., `MOT_CV01_001_DRIVE` — indicates the physical signal this variable is bound to. Use commas if multiple.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd02_datadict.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD02 — Data Dictionary",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["VarName", "Scope", "ParentBlock", "Type", "Retain", "Description", "Status"],
    "additionalProperties": false,
    "properties": {
      "VarName":     { "type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]{0,127}$" },
      "Scope":       { "enum": ["GlobalDB","InstanceDB","UDT","MemoryMarker","TempVar"] },
      "ParentBlock": { "type": "string", "minLength": 1 },
      "Type":        { "type": "string", "minLength": 1 },
      "Offset":      { "type": "string", "pattern": "^\\d+(\\.\\d)?$" },
      "InitValue":   { "type": "string" },
      "Retain":      { "enum": ["Y","N","N/A"] },
      "Description": { "type": "string", "minLength": 5 },
      "LinkedTag":   { "type": "string" },
      "OldVar":      { "type": "string" },
      "Notes":       { "type": "string" },
      "Status":      { "enum": ["Active","Inactive","Spare"] }
    },
    "allOf": [
      {
        "if":   { "properties": { "Scope": { "enum": ["MemoryMarker","TempVar"] } } },
        "then": { "properties": { "Retain": { "const": "N/A" } } }
      }
    ]
  }
}
```

**Conditional rule:** for `MemoryMarker` and `TempVar` scope, `Retain` = `N/A` is mandatory (retain semantics don't apply to these scopes).

---

## 5. MD Output Format

When Gate 4 runs `script_excel_to_metadata.py`, it produces `RD02_DataDict.md`:

````markdown
---
title: RD02 — Data Dictionary
project: <project_name>
generated: YYYY-MM-DD
source: RD02_DataDict.xlsx
filter: Status=Active
total_vars: <N>
schema: RD02
---

# RD02 — Data Dictionary (Active Variables)

> This file is auto-generated from `RD02_DataDict.xlsx`. Do not edit manually — edit the Excel and re-run the script.

## Summary

- Total active variables: <N>
- Distribution: GlobalDB:<n> / InstanceDB:<n> / UDT:<n> / MemoryMarker:<n> / TempVar:<n>
- Retain (Y): <Nr>

## Global DB Variables

| VarName | ParentBlock | Type | Offset | InitValue | Retain | Description |
|---------|-------------|------|--------|-----------|--------|-------------|
| ... | ... | ... | ... | ... | ... | ... |

## Instance DB Variables

| VarName | ParentBlock | Type | Offset | InitValue | Retain | Description |
|---------|-------------|------|--------|-----------|--------|-------------|
| ... | ... | ... | ... | ... | ... | ... |

## UDT Definitions

| VarName | ParentBlock | Type | Offset | Description |
|---------|-------------|------|--------|-------------|
| ... | ... | ... | ... | ... |

## Memory Markers (%M)

| VarName | ParentBlock | Type | Description | OldVar |
|---------|-------------|------|-------------|--------|
| ... | ... | ... | ... | ... |
````

---

## 6. AI Filling Instructions (Retrofit)

AI fills this file via `PROMPT_EXTRACT_DATADICT_FROM_CODE.md`. Instruction framework:

```
INPUT: Platform parser output (_input/_parsed.md — Section 4 UDT, Section 5 DB)
TASK:
  1. Examine each DB: is it global or instance? (Section 5 Type column)
  2. List every variable in each DB (in Offset order)
  3. Take UDT definitions as separate rows (Scope=UDT, ParentBlock=UDT_name)
  4. If %M addresses exist, add them as MemoryMarker
  5. Fill Retain if information is available (backup/restore attribute); otherwise leave blank
  6. Put the legacy variable name into OldVar AS-IS (preserve German/Turkish)
  7. Description: keep the legacy comment without translating it; add the original in "(orig: ...)" format
  8. LinkedTag: cross-reference with the IO list (RD01 Tag column)
  9. INCLUDE TempVars (write the correct type), pulled from the TEMP section of the FB
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: _input/brief.md + the designed FB/FC interfaces (RD10 draft)
TASK:
  1. Design an instance DB for each FB (STAT variables → InstanceDB rows)
  2. Propose a GlobalDB for shared data (with project name: DB_<PROJECT>_State)
  3. Extract UDT definitions (abstract repeating structures)
  4. Leave OldVar blank (no source)
  5. InitValue: assign a safe starting value to each variable (FALSE, 0, T#0s)
  6. Retain: Y for critical state variables, N for derived values
  7. TempVar: calculation intermediates, cleared on each call — Retain=N/A
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **IEC 61131-3 §6.4** | Identifier rules — VarName regex |
| **IEC 61131-3 §6.5** | Elementary data types — Type column |
| **IEC 61131-3 §6.6** | Generic data types (`ANY_*`) — go into Notes |
| **PLCopen** | Retain-variable discipline (only the truly necessary ones in NVRAM) |
| **IEC 61508 §7.9** | Safe initial values (InitValue) — for safety-linked variables |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- Turkish characters in VarName (`Değer`, `İstatüs`) → regex reject
- Spaces in Offset (`0. 0`) → regex reject
- Type in lowercase (`bool`, `int`) → enum mismatch

### 9.2 Schema/Standard (Category B) — Validator catches
- `Retain=Y` on a `MemoryMarker` scope → conditional rule reject
- Required column blank (VarName, Scope, ParentBlock, Type empty) → schema reject
- Offset value written on a `TempVar` → logical violation (temp does not live in a DB)

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ AI confuses instance DB with global DB — e.g., `DB_Motor_Pump01` is an instance DB but marked `GlobalDB` → wrong DB binding on the FB call
- ⚠️ TEMP variables treated as STAT → Retain=Y assigned (dangerous — TEMP is cleared each call, retain is meaningless)
- ⚠️ `%M` areas with no definition in legacy code (ghost markers) look active to AI but are actually unused → must be Status=Inactive
- ⚠️ STRING type without a length (`STRING` instead of `STRING[80]`) → size ambiguity during SCL generation
- ⚠️ Lists UDT members directly as GlobalDB variables (does not see the parent UDT structure) → ParentBlock hierarchy broken

### 9.4 Correction Request Template

> "Error in RD02 row `<VarName>`: <category> issue: <description>. Expected: <correct value>. Fix only that row."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD02_DataDict.xlsx` copied as a blank template. Contents:
- 12 columns, header row + 1 example row (to delete)
- Data Validation: dropdown in Scope, Retain, Status columns
- Conditional Formatting: rows with Scope=MemoryMarker get an orange background (reminder to reduce its use in new code)
- Separate sheets: "GlobalDB", "InstanceDB", "UDT", "MemoryMarker", "TempVar" (Scope-filtered views)

---

## 11. Related Files

- **Previous spec:** `MDSCHEMA_RAWDATA_01_IO.md` (physical signals)
- **Next spec:** `MDSCHEMA_RAWDATA_03_FLOWCHART.md` (behavior model)
- **Companion:** `MDSCHEMA_RAWDATA_10_FBSPEC.md` (FB/FC interface — uses the RD02 data layer)
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_DATADICT_FROM_CODE.md`
- **Design guide (greenfield):** `02_PROJECT_TYPES/GREENFIELD/GREENFIELD_DESIGN_DATADICT.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD02_DataDict.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd02_datadict.schema.json`
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_02_DATADICT.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Deliverable filenames updated to `RD02_DataDict.xlsx/.md` to match actual project filenames. Status enum renamed to `Active/Inactive/Spare` (2026-06-10) in a coordinated update across spec + JSON schema + templates + example data; tooling still reads legacy Turkish literals. v1.2.0 roadmap: Allen-Bradley tag-name adaptation, multi-instance DB scenarios.*
