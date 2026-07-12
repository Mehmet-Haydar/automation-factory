---
title: Raw Data Schema #11 — HMI
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_08_ALARM.md, GLOBAL_LANG_POLICY.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_08_ALARM.md, PROMPT_EXTRACT_HMI_FROM_CODE.md]
schema: RAWDATA
rd_number: 11
deliverable: [RD11_HMI.xlsx, RD11_HMI.md, rd11_hmi.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [ISA-101, IEC 62714-1, NAMUR NE107]
---

# MDSCHEMA_RAWDATA_11_HMI.md — HMI Specification

> **This file defines how the project's "11 — HMI" raw data file should be structured.** Documents HMI screens, PLC-HMI tag mapping, display elements and multi-language text. Based on the ISA-101 operator-interface standard.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual HMI configuration (`RD11_HMI.xlsx` / `.md`) must conform to this spec.

- ✅ Each HMI screen's type and content
- ✅ PLC tag → HMI tag mapping
- ✅ Display elements (button, indicator, trend, alarm list)
- ✅ Multi-language screen text (output_language)
- ✅ Access level (operator/supervisor/engineer)

**This file is NOT:**
- ❌ HMI screen design/graphics file (that's the WinCC Unified project — this spec is its data pack)
- ❌ Alarm display rules (that's RD08 — alarm class/priority there, HMI visualization here)
- ❌ SCADA communications (that's RD09 Comms — OPC UA/S7 link structure)

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Legacy HMI project (WinCC Classic/Unified export) + screenshots + operator manual | AI (`PROMPT_EXTRACT_HMI_FROM_CODE.md`) — _parsed.md Section 3 (HMI tags) and 5 (DB) | `script_consistency_check.py` |
| **Greenfield** | ISA-101 screen design guide + machine operator requirements | Human (HMI designer + automation engineer) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** → **Gate 3** → **Gate 4** (GREEN).

---

## 3. Excel Column Definition (Required)

`RD11_HMI.xlsx` contains two sheets: **ScreenList** (screen headers) + **TagList** (HMI-PLC tag mappings).

### 3.1 Sheet 1: ScreenList

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `ScreenID` | string | ✅ | `^SCR\d{3}$` | Screen identifier (e.g., `SCR001` Overview, `SCR002` Motor Detail) |
| 2 | `ScreenName` | string | ✅ | min 3 characters, EN | Short screen name |
| 3 | `ScreenType` | enum | ✅ | `Overview`, `Detail`, `Alarm`, `Trend`, `Recipe`, `Diagnostic`, `Navigation` | ISA-101 screen types |
| 4 | `AccessLevel` | enum | ✅ | `Operator`, `Supervisor`, `Engineer` | Minimum access right |
| 5 | `Title_EN` | string | ✅ | min 2 characters | English screen title |
| 6 | `Title_TR` | string | ⚪ | min 2 characters | Turkish screen title |
| 7 | `Title_DE` | string | ⚪ | min 2 characters | German screen title |
| 8 | `NavigateTo` | string | ⚪ | (free — comma-separated SCR IDs) | Which screens you can navigate to |
| 9 | `LinkedAlarm` | string | ⚪ | (free — comma-separated ALM IDs) | Alarms related to this screen (cross-reference to RD08 AlarmID) |
| 10 | `Notes` | string | ⚪ | (free) | Design note, user story |
| 11 | `Status` | enum | ✅ | `Active`, `Inactive`, `Draft` | Renamed to English (2026-06-10); legacy Turkish literals (`Aktif`/`Pasif`/`Taslak`/`Yedek`) in existing projects remain readable by the tooling |

### 3.2 Sheet 2: TagList

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `HMI_TagID` | string | ✅ | `^HMI_[A-Z0-9_]+$` | HMI internal tag name |
| 2 | `PLC_Tag` | string | ✅ | (free — RD01 Tag or RD02 VarName) | Matching PLC tag or DB variable |
| 3 | `ScreenRef` | string | ✅ | `^SCR\d{3}$` | Which screen it appears on (ScreenID) |
| 4 | `ElementType` | enum | ✅ | `Button`, `Indicator`, `NumericDisplay`, `NumericInput`, `Trend`, `AlarmWidget`, `Text`, `Image` | HMI visual element type |
| 5 | `Label_EN` | string | ✅ | min 2 characters | English element label |
| 6 | `Label_TR` | string | ⚪ | min 2 characters | Turkish element label |
| 7 | `Label_DE` | string | ⚪ | min 2 characters | German element label |
| 8 | `ReadWrite` | enum | ✅ | `Read`, `Write`, `ReadWrite` | Can the operator write? |
| 9 | `MinValue` | real | ⚪ | (free) | Analog display min value |
| 10 | `MaxValue` | real | ⚪ | (free) | Analog display max value |
| 11 | `EngUnit` | string | ⚪ | (free) | Display unit (`°C`, `bar`, `rpm`) |
| 12 | `Notes` | string | ⚪ | (free) | Special visual rule, color note |

**Note:** the `_TR`/`_DE` suffix on Title and Label columns is intentional multi-language design — field names stay, values are populated per project language.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd11_hmi.schema.json`:

**ScreenList:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD11 — HMI ScreenList",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["ScreenID","ScreenName","ScreenType","AccessLevel","Title_EN","Status"],
    "additionalProperties": false,
    "properties": {
      "ScreenID":    { "type": "string", "pattern": "^SCR\\d{3}$" },
      "ScreenName":  { "type": "string", "minLength": 3 },
      "ScreenType":  { "enum": ["Overview","Detail","Alarm","Trend","Recipe","Diagnostic","Navigation"] },
      "AccessLevel": { "enum": ["Operator","Supervisor","Engineer"] },
      "Title_EN":    { "type": "string", "minLength": 2 },
      "Title_TR":    { "type": "string", "minLength": 2 },
      "Title_DE":    { "type": "string", "minLength": 2 },
      "NavigateTo":  { "type": "string" },
      "LinkedAlarm": { "type": "string" },
      "Notes":       { "type": "string" },
      "Status":      { "enum": ["Active","Inactive","Draft"] }
    }
  }
}
```

**TagList:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD11 — HMI TagList",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["HMI_TagID","PLC_Tag","ScreenRef","ElementType","Label_EN","ReadWrite"],
    "additionalProperties": false,
    "properties": {
      "HMI_TagID":   { "type": "string", "pattern": "^HMI_[A-Z0-9_]+$" },
      "PLC_Tag":     { "type": "string", "minLength": 1 },
      "ScreenRef":   { "type": "string", "pattern": "^SCR\\d{3}$" },
      "ElementType": { "enum": ["Button","Indicator","NumericDisplay","NumericInput","Trend","AlarmWidget","Text","Image"] },
      "Label_EN":    { "type": "string", "minLength": 2 },
      "Label_TR":    { "type": "string", "minLength": 2 },
      "Label_DE":    { "type": "string", "minLength": 2 },
      "ReadWrite":   { "enum": ["Read","Write","ReadWrite"] },
      "MinValue":    { "type": "number" },
      "MaxValue":    { "type": "number" },
      "EngUnit":     { "type": "string" },
      "Notes":       { "type": "string" }
    }
  }
}
```

---

## 5. MD Output Format

`RD11_HMI.md` produced at Gate 4:

````markdown
---
title: RD11 — HMI
project: <project_name>
generated: YYYY-MM-DD
output_language: tr
total_screens: <N>
total_tags: <N>
schema: RD11
---

# RD11 — HMI

## Screen List

| ScreenID | ScreenName | ScreenType | AccessLevel | Title |
|----------|------------|------------|-------------|-------|
| SCR001 | Overview | Overview | Operator | Machine Overview |
| SCR002 | MotorDetail | Detail | Operator | Motor CV01 Detail |
| ... | ... | ... | ... | ... |

## SCR001 — Machine Overview

| HMI_TagID | PLC_Tag | ElementType | Label | ReadWrite |
|-----------|---------|-------------|-------|-----------|
| HMI_MOT_CV01_RUN | MOT_CV01_001_FDBK | Indicator | Motor Running | Read |
| HMI_MOT_CV01_CMD | MOT_CV01_001_DRIVE | Button | Motor Start/Stop | Write |
| ... | ... | ... | ... | ... |
````

---

## 6. AI Filling Instructions (Retrofit)

```
INPUT: _parsed.md Section 3 (HMI tags) + Section 5 (HMI DBs)
TASK:
  1. Group HMI tags by which screen they belong to (by function/equipment name)
  2. Each screen group → one SCR row
  3. Each HMI tag → one TagList row; map PLC_Tag via cross-reference to RD01
  4. ElementType: BOOL tag → Indicator/Button, analog tag → NumericDisplay/NumericInput
  5. ReadWrite: Write/ReadWrite for HMI-writable tags
  6. Label_EN: translate the legacy HMI text to English; keep the original in Notes
  7. Label_TR/DE: per output_language — may leave blank, human fills at Gate 3
  8. AccessLevel: per legacy HMI password level (Level 0→Operator, 1→Supervisor, 2+→Engineer)
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: _input/brief.md + ISA-101 screen design principles + RD01 IO List
TASK:
  1. Minimum screen set: SCR001 Overview, SCR002+ Detail (per equipment), SCR_ALARM Alarm
  2. Overview: bird's-eye view of all equipment (status indicator per motor/valve)
  3. Detail: all parameters for one piece of equipment (speed, current, temp, alarm state)
  4. Alarm screen: all Critical + Warning alarms from RD08
  5. Trend screen: historical traces for analog signals
  6. HMI_TagID: format `HMI_<PLC_Tag_root>` (e.g., HMI_MOT_CV01_RUN)
  7. Label translation: use GLOBAL_LANG_POLICY §6 Glossary
  8. ReadWrite: Write only for operator commands — Read is enough for display
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **ISA-101** | HMI design standard — ScreenType enum, AccessLevel, color conventions |
| **IEC 62714-1** | AutomationML — HMI configuration data-exchange format (future export) |
| **NAMUR NE107** | Field-device status icons (green check=OK, yellow ! =maintenance, orange ! =out of function, red X=fault) — Indicator element color rule |
| **ISA-18.2** | Alarm display — AlarmWidget elements |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- ScreenID `SCREEN001` (SCR prefix, not 3 digits) → regex reject
- HMI_TagID `hmi_mot_001` (lowercase) → pattern reject
- AccessLevel `admin` (outside enum) → enum reject

### 9.2 Schema/Standard (Category B) — Validator catches
- ScreenRef points to a non-existent SCR ID in ScreenList → referential integrity (script)
- ElementType=Button but ReadWrite=Read → logical violation (a button is for writing; script warning)

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ AI puts all tags into a single Overview screen — per ISA-101 the Overview should hold at most 8-12 objects; more distracts the operator
- ⚠️ Write-access tags left at Operator level — critical setpoint changes should be Engineer level
- ⚠️ Alarm widgets without an AlarmID reference — unclear which alarms appear on this screen
- ⚠️ Label text is identical in every language (English copied as-is) → multi-language support not actually delivered

### 9.4 Correction Request Template

> "Error in RD11 screen `<ScreenID>` tag `<HMI_TagID>`: <category> issue: <description>. Fix only that row."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD11_HMI.xlsx` blank template:
- **Sheet "ScreenList":** 11 columns, header + 3 example screens (Overview/Detail/Alarm)
- **Sheet "TagList":** 12 columns, header + 5 example tags
- Data Validation: ScreenType, AccessLevel, ElementType, ReadWrite, Status dropdowns

---

## 11. Related Files

- **Dependency:** `MDSCHEMA_RAWDATA_01_IO.md` (PLC_Tag cross-reference)
- **Dependency:** `MDSCHEMA_RAWDATA_08_ALARM.md` (LinkedAlarm cross-reference)
- **Next spec:** `MDSCHEMA_RAWDATA_12_USECASE.md`
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_HMI_FROM_CODE.md`
- **Language policy:** `01_GLOBAL_STANDARDS/rules/GLOBAL_LANG_POLICY.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD11_HMI.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd11_hmi.schema.json`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_11_HMI.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Multi-language `Title_TR/DE` and `Label_TR/DE` field names preserved (multi-lang design intent). Status enum renamed to `Active/Inactive/Draft` (English, 2026-06-10 coordinated update; see RD02 spec §3.1). v1.2.0 roadmap: WinCC Unified tag export format, ISA-101 color palette schema, multi-monitor workstation configuration.*
