---
title: Raw Data Schema #08 — Alarm List
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_07_TIMING.md, GLOBAL_LANG_POLICY.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_07_TIMING.md, MDSCHEMA_RAWDATA_11_HMI.md, PROMPT_EXTRACT_ALARM_FROM_CODE.md]
schema: RAWDATA
rd_number: 08
deliverable: [RD08_Alarm.xlsx, RD08_Alarm.md, rd08_alarm.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [ISA-18.2, IEC 62682, EEMUA 191]
---

# MDSCHEMA_RAWDATA_08_ALARM.md — Alarm List Specification

> **This file defines how the project's "08 — Alarm List" raw data file should be structured.** Documents all alarms, warnings and notifications; their trigger conditions, priorities, multi-language text and acknowledgement requirements. Based on the ISA-18.2 alarm-management standard.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual alarm list (`RD08_Alarm.xlsx` / `.md`) must conform to this spec.

- ✅ Each alarm's unique identifier, class and priority
- ✅ Trigger condition (tag + threshold or boolean expression)
- ✅ Multi-language alarm text (TR / EN / DE — GLOBAL_LANG_POLICY)
- ✅ Acknowledgement requirement
- ✅ Suppression condition (can it be silenced in certain modes?)
- ✅ Linked timer (RD07 filter delay)

**This file is NOT:**
- ❌ HMI alarm display design (that's RD11 HMI — screen layout and color)
- ❌ Alarm OB code structure (that's SCL code, generated from this file)
- ❌ Safety-function-to-alarm conversion (that's RD05 Safety — SF alarms are also added here via LinkedSF)

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Legacy alarm OBs + HMI alarm definitions + operator manual | AI (`PROMPT_EXTRACT_ALARM_FROM_CODE.md`) then human correction | `script_consistency_check.py` |
| **Greenfield** | Process design + risk assessment + ISA-18.2 alarm philosophy | Human (process engineer + guided by EEMUA 191) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** → **Gate 3** → **Gate 4** (GREEN). Bidirectional link with RD07: the `LinkedAlarm` of timeout timers comes from this file.

---

## 3. Excel Column Definition (Required)

`RD08_Alarm.xlsx` must contain the following columns **in this order**:

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `AlarmID` | string | ✅ | `^ALM\d{4}$` | Unique alarm identifier (e.g., `ALM0001`) |
| 2 | `AlarmName` | string | ✅ | min 3 characters, EN | Short alarm name (used as a code variable) |
| 3 | `Class` | enum | ✅ | `Critical`, `Warning`, `Info` | ISA-18.2 alarm class |
| 4 | `Priority` | integer | ✅ | 1-999 | 1=highest. Unique per AlarmID is recommended |
| 5 | `TriggerTag` | string | ✅ | (free — RD01 Tag or RD02 VarName) | Signal or variable that triggers the alarm |
| 6 | `TriggerCondition` | string | ✅ | (free — boolean or threshold) | Trigger logic (e.g., `> 80.0`, `= FALSE`, `= TRUE`) |
| 7 | `LimitValue` | string | ⚪ | (free) | Threshold value (analog alarm: `80.0`, `T#30s`). Blank for boolean |
| 8 | `LimitUnit` | string | ⚪ | (free) | Threshold unit (`°C`, `bar`, `mm`, `s`) |
| 9 | `AlarmText_EN` | string | ✅ | min 5 characters | English alarm text (base language) |
| 10 | `AlarmText_TR` | string | ⚪ | min 5 characters | Turkish alarm text |
| 11 | `AlarmText_DE` | string | ⚪ | min 5 characters | German alarm text |
| 12 | `AcknRequired` | enum | ✅ | `Y`, `N` | Does the operator need to acknowledge? |
| 13 | `SuppressCondition` | string | ⚪ | (free — ModeID or boolean) | Condition under which suppression applies (e.g., `M03 Maintenance`) |
| 14 | `LinkedTimer` | string | ⚪ | `^TMR_[A-Z0-9]+_\d{3}$` | Filter/delay timer (cross-reference to RD07 TimerID) |
| 15 | `LinkedSF` | string | ⚪ | `^SF\d{3}$` | Related safety function (cross-reference to RD05 FunctionID) |
| 16 | `RecommendedAction` | string | ⚪ | (free) | Recommended corrective action for the operator |
| 17 | `Notes` | string | ⚪ | (free) | Edge case, field experience note |
| 18 | `Status` | enum | ✅ | `Active`, `Inactive`, `Draft` | Renamed to English (2026-06-10); legacy Turkish literals (`Aktif`/`Pasif`/`Taslak`/`Yedek`) in existing projects remain readable by the tooling |

### 3.1 Column Descriptions (Detail)

**AlarmID (1):** `ALM0001`-`ALM9999`. Recommended ordering: `ALM0001-0099` = Safety alarms (linked to RD05), `ALM0100-0999` = Critical, `ALM1000-4999` = Warning, `ALM5000-9999` = Info. This grouping is a project choice, not mandatory.

**Class (3):** ISA-18.2 §3.5:
- `Critical` → immediate response required; delay is dangerous
- `Warning` → requires attention; response soon
- `Info` → informational, no response required

**Priority (4):** ISA-18.2 §7.3 — EEMUA 191 advice: P1 only for true emergencies, P2 for important resources, P3 for support. Assigning the same priority to all alarms creates an alarm flood.

**AlarmText_EN/TR/DE (9-11):** Recommended text format: `"[Equipment]: [What happened] — [Possible cause]"`. Example: `"Motor CV01: Overcurrent detected — Check mechanical load or drive fault"`. `AlarmText_EN` is always mandatory. The others are used per the `output_language` configuration (GLOBAL_LANG_POLICY §3). **NOTE:** the `_TR`/`_DE` suffix is intentional multi-language design — field names stay, values are populated per project language.

**AcknRequired (12):** typically `Y` for `Critical` and `Warning`. `N` for `Info`. ISA-18.2: a critical alarm without acknowledgement is bad practice.

**SuppressCondition (13):** e.g., `M03` = suppress motor-guard-open alarm while in Maintenance mode. Suppression logic is applied as an alarm mask at code-generation time. Note: safety alarms (rows with `LinkedSF` populated) cannot be suppressed.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd08_alarm.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD08 — Alarm List",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["AlarmID","AlarmName","Class","Priority","TriggerTag","TriggerCondition","AlarmText_EN","AcknRequired","Status"],
    "additionalProperties": false,
    "properties": {
      "AlarmID":            { "type": "string", "pattern": "^ALM\\d{4}$" },
      "AlarmName":          { "type": "string", "minLength": 3 },
      "Class":              { "enum": ["Critical","Warning","Info"] },
      "Priority":           { "type": "integer", "minimum": 1, "maximum": 999 },
      "TriggerTag":         { "type": "string", "minLength": 1 },
      "TriggerCondition":   { "type": "string", "minLength": 1 },
      "LimitValue":         { "type": "string" },
      "LimitUnit":          { "type": "string" },
      "AlarmText_EN":       { "type": "string", "minLength": 5 },
      "AlarmText_TR":       { "type": "string", "minLength": 5 },
      "AlarmText_DE":       { "type": "string", "minLength": 5 },
      "AcknRequired":       { "enum": ["Y","N"] },
      "SuppressCondition":  { "type": "string" },
      "LinkedTimer":        { "type": "string", "pattern": "^TMR_[A-Z0-9]+_\\d{3}$" },
      "LinkedSF":           { "type": "string", "pattern": "^SF\\d{3}$" },
      "RecommendedAction":  { "type": "string" },
      "Notes":              { "type": "string" },
      "Status":             { "enum": ["Active","Inactive","Draft"] }
    },
    "allOf": [
      {
        "if":   { "properties": { "Class": { "const": "Critical" } } },
        "then": { "properties": { "AcknRequired": { "const": "Y" } } }
      }
    ]
  }
}
```

**Conditional rule:** for `Class=Critical` alarms, `AcknRequired=Y` is mandatory (ISA-18.2 §9.3).

---

## 5. MD Output Format

`RD08_Alarm.md` produced at Gate 4. Text is selected per `output_language`:

````markdown
---
title: RD08 — Alarm List
project: <project_name>
generated: YYYY-MM-DD
source: RD08_Alarm.xlsx
filter: Status=Active
output_language: tr
total_alarms: <N>
critical_count: <Nc>
warning_count: <Nw>
info_count: <Ni>
schema: RD08
---

# RD08 — Alarm List

## Alarm Summary

| AlarmID | AlarmName | Class | Priority | TriggerTag | AcknRequired |
|---------|-----------|-------|----------|------------|--------------|
| ALM0001 | MotorOvercurrent | Critical | 1 | MOT_CV01_001_CURR | Y |
| ... | ... | ... | ... | ... | ... |

## Critical Alarms

### ALM0001 — MotorOvercurrent (Critical, P1)

- **Trigger:** `MOT_CV01_001_CURR > 15.0 A`
- **Text:** "Motor CV01: Overcurrent detected — check mechanical load or drive fault"
- **Acknowledge:** Required
- **Action:** Stop motor, check the load
````

---

## 6. AI Filling Instructions (Retrofit)

```
INPUT: _parsed.md Section 6 (alarm OBs — OB82, OB121, OB122 + HMI alarm DBs)
TASK:
  1. Scan alarm OBs and alarm DBs (typically prefixed "ALM", "FAULT", "ERROR")
  2. Assign a unique AlarmID to each alarm (starting at ALM0001)
  3. Class: derive from legacy text ("FAULT"→Critical, "WARNING"→Warning, "MSG"→Info)
  4. Priority: from the legacy alarm priority number; if absent, assign per Class
  5. TriggerCondition: pull the boolean or threshold expression as-is
  6. AlarmText_EN: translate the legacy alarm text into English, keep the original in Notes
  7. AlarmText_TR/DE: per output_language and fallback_language — may be left blank; human adds in Gate 3
  8. SuppressCondition: if the legacy code has an alarm-enable bit, extract it here
  9. RecommendedAction: from the legacy manual (if any), or leave blank
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: _input/brief.md + process risk analysis + ISA-18.2 alarm philosophy doc
TASK:
  1. Design an alarm for each critical process parameter (temperature, pressure, level, speed)
  2. Per ISA-18.2 §5, only truly necessary alarms → avoid alarm flood
  3. Critical alarms: P1-P10 (small number); Warning: P11-P100; Info: P101+
  4. Fill LimitValue + LimitUnit for every analog alarm
  5. AlarmText_EN mandatory. Format: "[Equipment]: [Problem] — [Possible cause]"
  6. For each timeout (RD07 IsWatchdog=Y) you MUST create a matching alarm
  7. Safety alarms (linked to RD05): populate LinkedSF, leave SuppressCondition blank (not suppressible)
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **ISA-18.2** | Alarm management standard — Class, Priority, AcknRequired, SuppressCondition |
| **IEC 62682** | IEC equivalent of ISA-18.2, international interoperability |
| **EEMUA 191** | Alarm system design guide — priority ordering and alarm-flood avoidance |
| **ISA-101** | HMI standard — alarm visual presentation (applied in RD11) |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- AlarmID `ALARM001` (ALM prefix, not 4 digits) → regex reject
- Priority = 0 → minimum reject (starts at 1)
- AlarmText_EN 3 characters → minLength reject

### 9.2 Schema/Standard (Category B) — Validator catches
- Class=Critical but AcknRequired=N → conditional rule reject
- LinkedTimer wrong format → pattern reject
- String value in Priority column (`"High"`) → type reject

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ AI duplicates all alarm text in English — AlarmText_TR/DE left untranslated; alarms can't be displayed in the output language
- ⚠️ Same Priority (e.g., 1) assigned to every alarm → ISA-18.2 violation; alarm flood overwhelms the operator
- ⚠️ Safety alarm (LinkedSF populated) has SuppressCondition filled in → dangerous; safety alarms cannot be suppressed
- ⚠️ Info-class alarm has AcknRequired=Y → unnecessary operator load; against ISA-18.2 advice
- ⚠️ Alarm text extracted from legacy code is still German (`"Motor überlastet"`) — must be moved to AlarmText_DE; AlarmText_EN holds the English translation

### 9.4 Correction Request Template

> "Error in RD08 row `<AlarmID>`: <category> issue: <description>. Expected: <correct value>. Fix only that row."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD08_Alarm.xlsx` blank template:
- 18 columns, header + 3 example rows (Critical/Warning/Info examples)
- Data Validation: Class, AcknRequired, Status dropdowns
- Conditional Formatting: Class=Critical → red, Warning → yellow, Info → blue background
- Separate sheet: "AlarmStatistics" — summary table of Class/Priority distribution (for ISA-18.2 rationalization)

---

## 11. Related Files

- **Dependency:** `MDSCHEMA_RAWDATA_07_TIMING.md` (timeout alarms, LinkedTimer/LinkedAlarm cross-reference)
- **Dependency:** `MDSCHEMA_RAWDATA_05_SAFETY.md` (safety alarms, LinkedSF)
- **Next spec:** `MDSCHEMA_RAWDATA_09_COMMS.md`
- **Companion:** `MDSCHEMA_RAWDATA_11_HMI.md` (alarm HMI display)
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_ALARM_FROM_CODE.md`
- **Design guide (greenfield):** `02_PROJECT_TYPES/GREENFIELD/GREENFIELD_DESIGN_ALARM.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD08_Alarm.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd08_alarm.schema.json`
- **Language policy:** `01_GLOBAL_STANDARDS/rules/GLOBAL_LANG_POLICY.md` (multi-language AlarmText)

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_08_ALARM.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Deliverable filenames updated to `RD08_Alarm.xlsx/.md` to match actual project files. Multi-language `AlarmText_TR/DE` field names preserved (multi-lang design intent). Status enum renamed to `Active/Inactive/Draft` (English, 2026-06-10 coordinated update; see RD02 spec §3.1). v1.2.0 roadmap: alarm rationalization process (EEMUA 191 §3), alarm shelving mechanism.*
