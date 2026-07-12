---
title: Raw Data Schema #05 — Safety Functions
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_01_IO.md, GLOBAL_DATA_CLASSIFICATION.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_04_MODE.md, PROMPT_EXTRACT_SAFETY_FROM_CODE.md]
schema: RAWDATA
rd_number: 05
deliverable: [RD05_Safety_DRAFT_UNVERIFIED.xlsx, RD05_Safety_DRAFT_UNVERIFIED.md, rd05_safety.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [IEC 62061, ISO 13849-1, IEC 61508, IEC 61511]
---

# MDSCHEMA_RAWDATA_05_SAFETY.md — Safety Functions Specification

> **This file defines how the project's "05 — Safety Functions" raw data file should be structured.** Documents all safety functions running on the F-PLC (Siemens Safety Integrated) or an external safety relay, the SIL/PLr levels, trigger conditions and safe-state actions.

> ⚠️ **CRITICAL:** Errors in this file can lead to injury or death. AI output **must always** be verified by an authorized safety engineer. No safety function may go to production with AI approval alone.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual safety functions in the project (`RD05_Safety_DRAFT_UNVERIFIED.xlsx` / `.md`) must conform to this spec.

- ✅ Each safety function's identifier and SIL/PLr level
- ✅ Trigger conditions (F-Input signals — cross-referenced with RD01)
- ✅ Safe-state actions (F-Output signals)
- ✅ Reset type (auto / manual / tooled)
- ✅ F-PLC block references (F-DB, F-FB names)
- ✅ Test interval (proof test interval)

**This file is NOT:**
- ❌ Safety engineering calculations (SIL verification report, FMEA — those are separate documents)
- ❌ F-PLC code (that's SCL/FBD code, generated from this file)
- ❌ Standard IO signals (that's RD01 — F-prefixed signals are marked `SafetyRelated=Y` in both files)

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Legacy F-PLC code + safety-circuit schematics + CE documentation | AI (`PROMPT_EXTRACT_SAFETY_FROM_CODE.md`) — **extraction ONLY**; verification by human + safety engineer | `script_consistency_check.py` + safety-engineer sign-off |
| **Greenfield** | Machine risk assessment + Safety Requirement Spec (SRS) | Safety engineer (AI may assist, NOT primary owner) | Safety engineer + CE sign-off |

Pipeline placement: **Gate 2** → **Gate 3** (signed by safety engineer) → **Gate 4** (validation → GREEN). RD05 requires a **mandatory sign-off at Gate 3** — different from the other RDs.

---

## 3. Excel Column Definition (Required)

`RD05_Safety_DRAFT_UNVERIFIED.xlsx` must contain the following columns **in this order**:

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `FunctionID` | string | ✅ | `^SF\d{3}$` | Safety function identifier (e.g., `SF001` E-Stop, `SF002` Light Curtain) |
| 2 | `FunctionName` | string | ✅ | min 3 characters, EN | Short name of the function |
| 3 | `SIL_Level` | enum | ✅ | `SIL1`, `SIL2`, `SIL3`, `PLr_a`, `PLr_b`, `PLr_c`, `PLr_d`, `PLr_e`, `N/A` | IEC 62061 SIL or ISO 13849 PLr |
| 4 | `Category` | enum | ✅ | `B`, `1`, `2`, `3`, `4`, `N/A` | ISO 13849 category (control-system category) |
| 5 | `TriggerCondition` | string | ✅ | (free — boolean expression) | Condition that triggers the safety function (F-Input tags) |
| 6 | `SafeAction` | string | ✅ | (free — comma-separated) | Safe-state actions after trigger |
| 7 | `ResponseTime_ms` | integer | ✅ | >0 | Time from trigger to safe state (ms) |
| 8 | `ResetType` | enum | ✅ | `Auto`, `Manual`, `Tooled` | Auto = automatic reset; Manual = operator button; Tooled = tool/key required |
| 9 | `F_InputTag` | string | ✅ | (free — comma-separated) | F-prefixed signals from RD01 (cross-reference) |
| 10 | `F_OutputTag` | string | ✅ | (free — comma-separated) | F-Output signals driven to the safe state |
| 11 | `F_DB` | string | ⚪ | (free) | Related F-DB name in Siemens Safety Integrated |
| 12 | `F_FB` | string | ⚪ | (free) | Related F-FB name (e.g., `F_ESTOP`, `F_LightCurtain`) |
| 13 | `ProofTestInterval_h` | integer | ⚪ | >0 | Test interval (hours). Required by IEC 62061 §6.7 |
| 14 | `Verified_By` | string | ⚪ | (free) | Verifying safety engineer's name/signature |
| 15 | `Notes` | string | ⚪ | (free) | Standard reference, calculation note, special condition |
| 16 | `Status` | enum | ✅ | `Active`, `Inactive`, `DRAFT_UNVERIFIED` | `DRAFT_UNVERIFIED` = awaiting safety-engineer sign-off. Renamed to English (2026-06-10); legacy Turkish literals (`Aktif`/`Pasif`/`Taslak`/`Yedek`) in existing projects remain readable by the tooling |

### 3.1 Column Descriptions (Detail)

**SIL_Level (3):** `SIL1`-`SIL3` for IEC 62061 (electrical/electronic/programmable). `PLr_a`-`PLr_e` for ISO 13849 (mechanically-oriented systems). `N/A` = configuration/category not yet assessed (temporary).

**Category (4):** ISO 13849-1 §6.2 control-system categories. Categories 1-4 increase reliability. Category B = basic requirement (lowest), Category 4 = highest reliability.

**ResponseTime_ms (7):** The actual system response time. Must be less than the permitted response time in the risk assessment. AI must not guess — left to engineer calculation (blank = validator warning).

**ResetType (8):**
- `Auto` → machine continues automatically after the hazard clears (low-risk categories only)
- `Manual` → operator must press a reset button
- `Tooled` → only an authorized person can reset using a special tool or key (high risk)

**Status (16):** The special value `DRAFT_UNVERIFIED` — this row has not yet been signed by a safety engineer. `script_consistency_check.py` treats this differently from `Active` and surfaces a dedicated warning in the report.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd05_safety.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD05 — Safety Functions",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["FunctionID","FunctionName","SIL_Level","Category","TriggerCondition","SafeAction","ResponseTime_ms","ResetType","F_InputTag","F_OutputTag","Status"],
    "additionalProperties": false,
    "properties": {
      "FunctionID":            { "type": "string", "pattern": "^SF\\d{3}$" },
      "FunctionName":          { "type": "string", "minLength": 3 },
      "SIL_Level":             { "enum": ["SIL1","SIL2","SIL3","PLr_a","PLr_b","PLr_c","PLr_d","PLr_e","N/A"] },
      "Category":              { "enum": ["B","1","2","3","4","N/A"] },
      "TriggerCondition":      { "type": "string", "minLength": 1 },
      "SafeAction":            { "type": "string", "minLength": 1 },
      "ResponseTime_ms":       { "type": "integer", "minimum": 1 },
      "ResetType":             { "enum": ["Auto","Manual","Tooled"] },
      "F_InputTag":            { "type": "string", "minLength": 1 },
      "F_OutputTag":           { "type": "string", "minLength": 1 },
      "F_DB":                  { "type": "string" },
      "F_FB":                  { "type": "string" },
      "ProofTestInterval_h":   { "type": "integer", "minimum": 1 },
      "Verified_By":           { "type": "string" },
      "Notes":                 { "type": "string" },
      "Status":                { "enum": ["Active","Inactive","DRAFT_UNVERIFIED"] }
    }
  }
}
```

---

## 5. MD Output Format

`RD05_Safety_DRAFT_UNVERIFIED.md` produced at Gate 4:

````markdown
---
title: RD05 — Safety Functions
project: <project_name>
generated: YYYY-MM-DD
source: RD05_Safety_DRAFT_UNVERIFIED.xlsx
filter: Status=Active
total_functions: <N>
unverified_count: <N>
schema: RD05
---

# RD05 — Safety Functions

> ⚠️ This document requires safety-engineer sign-off. DRAFT_UNVERIFIED rows cannot be transferred to code.

## Safety Function Summary

| FunctionID | FunctionName | SIL_Level | Category | ResponseTime_ms | ResetType | Verified_By |
|------------|--------------|-----------|----------|-----------------|-----------|-------------|
| SF001 | EmergencyStop | SIL2 | 3 | 50 | Manual | M.Yılmaz |
| ... | ... | ... | ... | ... | ... | ... |

## Detail

### SF001 — EmergencyStop

- **Trigger:** `F_ESTOP_PB001 OR F_ESTOP_PB002`
- **Safe Action:** `RESET F_MOT_ALL, RESET F_VLV_INLET`
- **F-DB:** `F_DB_EmergencyStop`
- **F-FB:** `F_EmergencyStop`
````

---

## 6. AI Filling Instructions (Retrofit)

```
INPUT: _parsed.md Section 9 (Safety Blocks — all F-prefixed blocks)
TASK:
  1. List all F-prefixed FB/FC/DBs → one SF row each
  2. F-InputTag: SafetyRelated=Y signals from RD01 (cross-reference)
  3. F-OutputTag: F-prefixed output signals
  4. ResponseTime_ms: derive from legacy code — typically in the F-CPU watchdog parameter
  5. SIL_Level: if stated in the legacy CE document, write it; otherwise N/A (AI DOES NOT GUESS)
  6. Category: same — derive from existing documentation or N/A
  7. ResetType: derive from comments in the legacy code or the HMI reset logic
  8. Status: start every row at DRAFT_UNVERIFIED (safety engineer approves)
  9. Verified_By: LEAVE BLANK (safety engineer will fill)
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: risk-assessment report + SRS (Safety Requirement Spec)
TASK:
  1. Create an SF row for each hazard in the risk assessment
  2. SIL/PLr: take from the SRS (AI does NOT calculate)
  3. ResponseTime_ms: take from the SRS or LEAVE BLANK
  4. TriggerCondition: use the planned F-Input signals from RD01
  5. SafeAction: safe park position per hazard (from the machine design)
  6. ResetType: per risk level — SIL3/PLr_e → minimum Tooled
  7. Status: DRAFT_UNVERIFIED (not final without a safety engineer's signature)
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **IEC 62061** | Machine safety — SIL determination, SIL_Level column |
| **ISO 13849-1** | Design of safety-related control systems — PLr and Category columns |
| **IEC 61508** | Functional safety general framework — proof test interval |
| **IEC 61511** | SIS in process industries — chemistry/petrochemistry |
| **EN ISO 13850** | Emergency stop function — ResetType requirements |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- FunctionID `SF01` (not 3 digits) → regex reject
- SIL_Level `sil2` (lowercase) → enum reject
- ResponseTime_ms 0 or negative → minimum reject

### 9.2 Schema/Standard (Category B) — Validator catches
- Required column (TriggerCondition, SafeAction, F_InputTag) blank → schema reject
- Status `Active` but Verified_By blank → script_consistency_check warning

### 9.3 Semantic (Category C) — Manual review required (CRITICAL)
- ⚠️ AI guesses SIL_Level ("looks like SIL2") — strictly forbidden, must write N/A
- ⚠️ Mistakes a standard IO signal for an F-signal (signal with SafetyRelated=N ends up in an SF row) → F-prefix check is mandatory
- ⚠️ ResetType=Auto on a safety function — Auto reset is not acceptable for SIL2+ (EN ISO 13850)
- ⚠️ ResponseTime_ms guessed from legacy code comments — actual measurement required; wrong value → SIL calculation invalid
- ⚠️ Category B paired with SIL2 — ISO 13849/IEC 62061 incompatibility; engineer verification mandatory

### 9.4 Correction Request Template

> "Error in RD05 row `<FunctionID>`: <category> issue: <description>. Expected: <correct value>. ONLY a safety engineer may sign off."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD05_Safety_DRAFT_UNVERIFIED.xlsx` blank template:
- 16 columns, header + 2 example rows (E-Stop / Light Curtain)
- Data Validation: dropdowns on SIL_Level, Category, ResetType, Status
- Conditional Formatting: rows with Status=DRAFT_UNVERIFIED get a red background
- Separate sheet: "VerificationLog" — safety-engineer signature date and comments

---

## 11. Related Files

- **Dependency:** `MDSCHEMA_RAWDATA_01_IO.md` (F-Input/Output signals, SafetyRelated=Y)
- **Next spec:** `MDSCHEMA_RAWDATA_06_MOTION.md`
- **Companion:** `MDSCHEMA_RAWDATA_04_MODE.md` (Emergency mode — M00)
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_SAFETY_FROM_CODE.md`
- **Knowledge base:** `06_KNOWLEDGE_BASE/KB_PITFALLS_SAFETY.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD05_Safety_DRAFT_UNVERIFIED.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd05_safety.schema.json`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_05_SAFETY.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Deliverable filenames updated to `RD05_Safety_DRAFT_UNVERIFIED.xlsx/.md` to match actual project files (the suffix is intentional — surfaces the "needs sign-off" status). Status enum renamed to `Active/Inactive/DRAFT_UNVERIFIED` (English, 2026-06-10 coordinated update; see RD02 spec §3.1). Only spec requiring a safety-engineer signature. v1.2.0 roadmap: automatic linkage to SISTEMA calculation file (.SSS), SIL verification checklist integration.*
