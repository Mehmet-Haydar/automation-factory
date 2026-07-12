---
title: Raw Data Schema #10 — Function Block Spec
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_02_DATADICT.md, GLOBAL_FB_TEMPLATE.scl]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_02_DATADICT.md, MDSCHEMA_RAWDATA_03_FLOWCHART.md, PROMPT_EXTRACT_FBSPEC_FROM_CODE.md]
schema: RAWDATA
rd_number: 10
deliverable: [RD10_FBSpec.xlsx, RD10_FBSpec.md, rd10_fbspec.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [IEC 61131-3 §2.5, PLCopen, Siemens LAD/FBD/SCL Style Guide]
---

# MDSCHEMA_RAWDATA_10_FBSPEC.md — Function Block Spec

> **This file defines how the project's "10 — Function Block Spec" raw data file should be structured.** Documents all FB (Function Block) and FC (Function) interfaces — IN/OUT/INOUT/STAT parameter lists. The per-project data pack of `GLOBAL_FB_TEMPLATE.scl`.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual FB/FC interface list (`RD10_FBSpec.xlsx` / `.md`) must conform to this spec.

- ✅ Each FB/FC's name, type and purpose
- ✅ All IN / OUT / INOUT / STAT / TEMP parameters
- ✅ Type, default value and description per parameter
- ✅ Which OB/FB calls it (call hierarchy)
- ✅ Related instance DB and cross-reference to RD02 DataDict

**This file is NOT:**
- ❌ SCL code inside the FB (produced in Gate 5)
- ❌ Instance DB variable detail (that's RD02 DataDict — STAT variables live there)
- ❌ OB structure (that's sequence/program organization — OB call list in RD03)

**Difference vs RD02:** RD02 = where the data lives (which DB, which offset). RD10 = what the data MEANS (which FB parameter, direction, type, default).

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Legacy PLC FB/FC definitions + interface blocks | AI (`PROMPT_EXTRACT_FBSPEC_FROM_CODE.md`) — uses _parsed.md Section 7 (FB) and 8 (FC) | `script_consistency_check.py` |
| **Greenfield** | FB design decisions + RD03 Flowchart + GLOBAL_FB_TEMPLATE.scl | Human (automation engineer — designs per template) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** → **Gate 3** → **Gate 4** (GREEN). RD10 is the primary feed for Gate 5 code generation — this spec maps directly to the SCL INTERFACE section.

---

## 3. Excel Column Definition (Required)

`RD10_FBSpec.xlsx` contains two separate sheets: **BlockList** (block header table) + **ParamList** (parameter detail).

### 3.1 Sheet 1: BlockList

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `BlockName` | string | ✅ | `^(FB\|FC)_[A-Z][A-Za-z0-9_]+$` | Block name (e.g., `FB_Motor`, `FC_ScaleAnalog`) |
| 2 | `BlockType` | enum | ✅ | `FB`, `FC` | IEC 61131-3 POU type |
| 3 | `Version` | string | ✅ | `^\d+\.\d+\.\d+$` | Semantic version (e.g., `1.0.0`) |
| 4 | `Description` | string | ✅ | min 10 characters | Purpose of the block, which equipment or function |
| 5 | `CalledFrom` | string | ✅ | (free — comma-separated) | Which OB/FB calls this block |
| 6 | `InstanceDB` | string | ⚪ | (free) | FB's instance DB name (only for FB; RD02 cross-reference) |
| 7 | `LinkedEquipment` | string | ⚪ | (free — RD01 Equipment) | Physical equipment it corresponds to |
| 8 | `TemplateBase` | string | ⚪ | (free) | Factory template it's based on (e.g., `PROMPT_MOTOR_DOL.md`) |
| 9 | `Notes` | string | ⚪ | (free) | Special-structure note, dependency |
| 10 | `Status` | enum | ✅ | `Active`, `Inactive`, `Draft` | Renamed to English (2026-06-10); legacy Turkish literals (`Aktif`/`Pasif`/`Taslak`/`Yedek`) in existing projects remain readable by the tooling |

### 3.2 Sheet 2: ParamList

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `BlockName` | string | ✅ | (must match BlockList) | Which block's parameter (foreign key → BlockList.BlockName) |
| 2 | `ParamName` | string | ✅ | `^(in\|out\|inout\|stat\|temp)_[a-z][A-Za-z0-9]+$` | Parameter name. GLOBAL_NAMING_STANDARD prefix rule: `in_`, `out_`, `inout_`, `stat_`, `temp_` |
| 3 | `Section` | enum | ✅ | `IN`, `OUT`, `INOUT`, `STAT`, `TEMP` | IEC 61131-3 variable section |
| 4 | `Type` | string | ✅ | (IEC types + UDT name) | Parameter data type |
| 5 | `DefaultValue` | string | ⚪ | (free) | Initial value (meaningful for IN/STAT) |
| 6 | `Description` | string | ✅ | min 5 characters | Purpose, expected value range, connection point |
| 7 | `LinkedTag` | string | ⚪ | (free — RD01 Tag) | Linked IO signal (cross-reference) |
| 8 | `Notes` | string | ⚪ | (free) | Edge case, safety note |

### 3.3 ParamName Convention (GLOBAL_NAMING_STANDARD)

```
in_bEnable       → IN  section, BOOL type
in_wSetpoint     → IN  section, WORD type
out_bRunning     → OUT section, BOOL type
out_wErrorCode   → OUT section, WORD type
inout_sStatus    → INOUT section, STRING type
stat_bInitDone   → STAT section, BOOL type (lives in instance DB)
temp_wCalc       → TEMP section, WORD type (cleared each call)
```

Type prefix: `b`=BOOL, `w`=WORD, `i`=INT, `di`=DINT, `r`=REAL, `s`=STRING, `t`=TIME, `u`=UDT.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd10_fbspec.schema.json` — two separate schemas:

**BlockList schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD10 — FBSpec BlockList",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["BlockName","BlockType","Version","Description","CalledFrom","Status"],
    "additionalProperties": false,
    "properties": {
      "BlockName":       { "type": "string", "pattern": "^(FB|FC)_[A-Z][A-Za-z0-9_]+$" },
      "BlockType":       { "enum": ["FB","FC"] },
      "Version":         { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
      "Description":     { "type": "string", "minLength": 10 },
      "CalledFrom":      { "type": "string", "minLength": 1 },
      "InstanceDB":      { "type": "string" },
      "LinkedEquipment": { "type": "string" },
      "TemplateBase":    { "type": "string" },
      "Notes":           { "type": "string" },
      "Status":          { "enum": ["Active","Inactive","Draft"] }
    },
    "allOf": [
      {
        "if":   { "properties": { "BlockType": { "const": "FB" } } },
        "then": { "required": ["InstanceDB"] }
      }
    ]
  }
}
```

**Conditional rule:** `FB` blocks require an `InstanceDB` (FC has no instance DB).

**ParamList schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD10 — FBSpec ParamList",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["BlockName","ParamName","Section","Type","Description"],
    "additionalProperties": false,
    "properties": {
      "BlockName":    { "type": "string" },
      "ParamName":    { "type": "string", "pattern": "^(in|out|inout|stat|temp)_[a-z][A-Za-z0-9]+$" },
      "Section":      { "enum": ["IN","OUT","INOUT","STAT","TEMP"] },
      "Type":         { "type": "string", "minLength": 1 },
      "DefaultValue": { "type": "string" },
      "Description":  { "type": "string", "minLength": 5 },
      "LinkedTag":    { "type": "string" },
      "Notes":        { "type": "string" }
    }
  }
}
```

---

## 5. MD Output Format

`RD10_FBSpec.md` produced at Gate 4 — one section per block in a format directly transferable to SCL INTERFACE:

````markdown
---
title: RD10 — FBSpec
project: <project_name>
generated: YYYY-MM-DD
source: RD10_FBSpec.xlsx
filter: Status=Active
total_blocks: <N>
fb_count: <Nfb>
fc_count: <Nfc>
schema: RD10
---

# RD10 — Function Block Spec

## Block List

| BlockName | BlockType | Version | CalledFrom | Description |
|-----------|-----------|---------|------------|-------------|
| FB_Motor | FB | 1.0.0 | OB1, FC_MotorManager | Generic motor-control block |
| ... | ... | ... | ... | ... |

## FB_Motor — Parameter Interface

```
(* SCL INTERFACE equivalent — paste-ready *)
VAR_INPUT
    in_bEnable      : BOOL := FALSE;   // Motor enable command
    in_bStartCmd    : BOOL := FALSE;   // Start command
    in_bStopCmd     : BOOL := FALSE;   // Stop command
END_VAR
VAR_OUTPUT
    out_bRunning    : BOOL;            // Motor running feedback
    out_bFault      : BOOL;            // Fault output
    out_wErrorCode  : WORD;            // Error code (16#xxxx)
END_VAR
VAR
    stat_bInitDone  : BOOL;            // Initialization-done flag
    stat_tonStartup : TON;             // Startup timeout timer
END_VAR
```
````

---

## 6. AI Filling Instructions (Retrofit)

```
INPUT: _parsed.md Section 7 (FB interfaces) + Section 8 (FCs)
TASK:
  1. Create a BlockList row per FB/FC
  2. Add all VAR_INPUT/OUTPUT/INOUT/STAT/TEMP parameters of each FB into ParamList
  3. ParamName: convert to GLOBAL_NAMING_STANDARD prefix (in_/out_/stat_/temp_)
  4. Put the legacy parameter name into Notes (preserve German/Turkish)
  5. CalledFrom: from the "Called From" column in _parsed.md Section 7
  6. InstanceDB: find the instance DB name and match with RD02
  7. TEMP variables: in the LOCAL section of legacy code — Section=TEMP
  8. Version: if no value found in legacy code, write 1.0.0 (new baseline)
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: RD03 Flowchart (which FBs are called) + GLOBAL_FB_TEMPLATE.scl
TASK:
  1. Base on GLOBAL_FB_TEMPLATE.scl (4-region: INTERFACE / INIT / MAIN / FAULT)
  2. Derive the FB list from machine equipment (motor, valve, sensor groups)
  3. Minimum interface per FB: in_bEnable, out_bRunning, out_bFault, out_wErrorCode
  4. Add equipment-type-specific parameters (motor: in_bStartCmd; valve: in_bOpenCmd)
  5. STAT: timer instances and state variables go here
  6. TEMP: only intra-FB intermediate calculations (don't over-use STAT)
  7. FC: no parameter persistence (same value each call), stateless operations
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **IEC 61131-3 §2.5.1** | POU (Program Organization Unit) structure — BlockType enum (FB/FC) |
| **IEC 61131-3 §2.5.2** | Variable sections — Section enum (IN/OUT/INOUT/STAT/TEMP) |
| **PLCopen** | FB interface conventions — in_bEnable, out_bRunning, out_bFault standard port names |
| **Siemens SCL Style Guide** | ParamName prefix rule (b, w, i, di, r, s, t) — GLOBAL_NAMING_STANDARD |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- BlockName `Motor_FB` (not FB_ prefix) → regex reject
- ParamName `Enable` (no section prefix: `in_`) → regex reject
- Version `1.0` (not three-part semver) → pattern reject

### 9.2 Schema/Standard (Category B) — Validator catches
- FB block with empty InstanceDB → conditional rule reject
- Section=TEMP but DefaultValue populated → logical violation (TEMP is cleared each call, default meaningless — script warning)

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ AI puts everything into STAT (easy path) — TEMP variables in STAT create unnecessary NVRAM usage; intra-FB calculation variables should be TEMP
- ⚠️ FC has a VAR (STAT) section — FC must be stateless; convert to FB if state retention is needed
- ⚠️ PLCopen convention broken — `out_bError` used instead of `out_bFault`, ErrorCode output named `out_nErr` (prefix rule: n=? undefined) → should be `out_wErrorCode`
- ⚠️ In retrofit, German parameter names copied as-is (`in_Eingang`, `out_Ausgang`) → must be translated to English per GLOBAL_NAMING_STANDARD; legacy name to Notes
- ⚠️ CalledFrom "OB1" on a single line — if multiple callers, comma-separate

### 9.4 Correction Request Template

> "Error in RD10 block `<BlockName>` parameter `<ParamName>`: <category> issue: <description>. Expected: <correct value>. Fix only that row."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD10_FBSpec.xlsx` blank template:
- **Sheet "BlockList":** 10 columns, header + 2 examples (FB_Motor + FC_ScaleAnalog)
- **Sheet "ParamList":** 8 columns, header + 8 example parameters (mixed across both blocks)
- Data Validation: BlockType, Section, Status dropdowns
- Conditional Formatting: rows with Section=STAT highlighted blue (lives in instance DB — critical)

---

## 11. Related Files

- **Dependency:** `MDSCHEMA_RAWDATA_02_DATADICT.md` (InstanceDB cross-reference)
- **Dependency:** `MDSCHEMA_RAWDATA_03_FLOWCHART.md` (CalledFrom cross-reference)
- **Base:** `GLOBAL_FB_TEMPLATE.scl` (4-region FB structure — all FBs follow this template)
- **Next spec:** `MDSCHEMA_RAWDATA_11_HMI.md`
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_FBSPEC_FROM_CODE.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD10_FBSpec.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd10_fbspec.schema.json`
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_10_FBSPEC.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Primary input for Gate 5 code generation. Status enum renamed to `Active/Inactive/Draft` (English, 2026-06-10 coordinated update; see RD02 spec §3.1). v1.2.0 roadmap: UDT interface type support, generic type (ANY_*) parameters, multi-version FB coexistence scenario.*
