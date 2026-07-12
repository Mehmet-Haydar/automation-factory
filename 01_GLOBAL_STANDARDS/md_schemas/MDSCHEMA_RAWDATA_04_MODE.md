---
title: Raw Data Schema #04 — Operating Modes
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_03_FLOWCHART.md, MDSCHEMA_RAWDATA_05_SAFETY.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_03_FLOWCHART.md, MDSCHEMA_RAWDATA_05_SAFETY.md, PROMPT_EXTRACT_MODE_FROM_CODE.md]
schema: RAWDATA
rd_number: 04
deliverable: [RD04_Mode.xlsx, RD04_Mode.md, rd04_mode.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [ISA-88 §4.7, OMAC PackML, IEC 61512-1]
---

# MDSCHEMA_RAWDATA_04_MODE.md — Operating Modes Specification

> **This file defines how the project's "04 — Operating Modes" raw data file should be structured.** Documents which mode (Auto, Manual, Maintenance, Emergency, etc.) the machine can be in, the transition conditions, and the actions permitted/restricted in each mode. The data-pack representation of the OMAC PackML and ISA-88 mode model.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual mode definition in the project (`RD04_Mode.xlsx` / `.md`) must conform to this spec.

- ✅ Each mode's identifier, name and priority
- ✅ Entry and exit conditions
- ✅ Permitted and restricted actions per mode
- ✅ HMI mode display (color, text, icon)
- ✅ OMAC PackML mode transition matrix (optional)

**This file is NOT:**
- ❌ Sequence steps (that's RD03 Flowchart — steps run inside a mode)
- ❌ Safety functions (that's RD05 Safety — safety has precedence over modes)
- ❌ Alarm trigger conditions (that's RD08 Alarm — alarms fire mode-independent)

**Mode ≠ Step:** Mode = the machine's overall state (Auto, Manual). Step = the sequence motion inside a mode (Homing → Loading → Processing). Multiple steps can run within one mode.

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Legacy mode-transition logic (CASE/IF blocks), HMI screens, operator manual | AI (`PROMPT_EXTRACT_MODE_FROM_CODE.md`) then human correction | `script_consistency_check.py` |
| **Greenfield** | Customer machine spec + operator requirements | Human (guided by `GREENFIELD_DESIGN_MODE.md`) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** → **Gate 3** → **Gate 4** (GREEN). Linkage to RD03 Flowchart: each step's `ModeReq` column references the `ModeID`s defined here.

---

## 3. Excel Column Definition (Required)

`RD04_Mode.xlsx` must contain the following columns **in this order**:

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `ModeID` | string | ✅ | `^M\d{2}$` | Mode identifier (e.g., `M00` Emergency, `M01` Auto, `M02` Manual, `M03` Maintenance) |
| 2 | `ModeName` | string | ✅ | min 3 characters, EN | Short English mode name (used as an enum value in code generation) |
| 3 | `Priority` | integer | ✅ | 0-99 | Priority on conflict. `0` = highest (Emergency). Each mode must have a unique priority |
| 4 | `PackMLState` | string | ⚪ | (OMAC PackML enum) | OMAC PackML equivalent: `Stopped`, `Starting`, `Execute`, `Held`, `Suspended`, `Aborting`, `Aborted`, `Clearing`, `Stopping`, `Resetting`, `Idle`, `Completing`, `Complete` |
| 5 | `Description` | string | ✅ | min 5 characters | Mode purpose, typical usage scenario |
| 6 | `EntryCondition` | string | ✅ | (free — boolean expression) | How to enter this mode (operator selection, automatic transition, alarm) |
| 7 | `ExitCondition` | string | ✅ | (free — boolean expression) | How to leave this mode |
| 8 | `PermittedActions` | string | ✅ | (free — comma-separated) | Actions permitted in this mode |
| 9 | `RestrictedActions` | string | ✅ | (free — comma-separated) | Actions forbidden in this mode (safety/process rule) |
| 10 | `HMI_Color` | string | ⚪ | `#RRGGBB` | HMI mode display color (ISA-101 color convention recommended) |
| 11 | `HMI_Text` | string | ⚪ | (free) | Mode text shown on the HMI (per output_language) |
| 12 | `DB_ModeWord` | string | ⚪ | (free) | DB variable holding the mode state (cross-reference to RD02 VarName) |
| 13 | `Notes` | string | ⚪ | (free) | Edge case, safety note, operator note |
| 14 | `Status` | enum | ✅ | `Active`, `Inactive`, `Draft` | Renamed to English (2026-06-10); legacy Turkish literals (`Aktif`/`Pasif`/`Taslak`/`Yedek`) in existing projects remain readable by the tooling |

### 3.1 Column Descriptions (Detail)

**ModeID (1):** `M00` = Emergency (always Priority=0). `M01` = Auto Production. `M02` = Manual. `M03` = Maintenance/Setup. Extras: `M04`... `M09`. Typical Siemens implementation: each bit of a WORD represents one mode.

**Priority (3):** When multiple mode requests come in simultaneously, the lowest value wins. `M00` Emergency → `0` (absolute priority). Two modes cannot share the same priority — validator rejects.

**PackMLState (4):** OMAC PackML §4 state machine. Filled when interoperability with international equipment vendors is required. May be left optional in small machines.

**PermittedActions / RestrictedActions (8-9):** Examples:
- PermittedActions: `StartSequence, JogMotors, SetParameters, AcknowledgeAlarms`
- RestrictedActions: `OpenSafetyGuard, InhibitEmergencyStop, ChangeRecipe`

**HMI_Color (10):** ISA-101 color recommendation: Green (`#00AA00`) = Normal/Auto, Yellow (`#FFAA00`) = Manual/Warning, Red (`#FF0000`) = Emergency/Fault. HMI-platform-independent hex code.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd04_mode.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD04 — Operating Modes",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["ModeID", "ModeName", "Priority", "Description", "EntryCondition", "ExitCondition", "PermittedActions", "RestrictedActions", "Status"],
    "additionalProperties": false,
    "properties": {
      "ModeID":             { "type": "string", "pattern": "^M\\d{2}$" },
      "ModeName":           { "type": "string", "minLength": 3 },
      "Priority":           { "type": "integer", "minimum": 0, "maximum": 99 },
      "PackMLState":        { "type": "string" },
      "Description":        { "type": "string", "minLength": 5 },
      "EntryCondition":     { "type": "string", "minLength": 1 },
      "ExitCondition":      { "type": "string", "minLength": 1 },
      "PermittedActions":   { "type": "string", "minLength": 1 },
      "RestrictedActions":  { "type": "string", "minLength": 1 },
      "HMI_Color":          { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" },
      "HMI_Text":           { "type": "string" },
      "DB_ModeWord":        { "type": "string" },
      "Notes":              { "type": "string" },
      "Status":             { "enum": ["Active","Inactive","Draft"] }
    }
  },
  "uniqueItems": true
}
```

**Extra validator rule (script_consistency_check.py):** every `Priority` value must be unique (this cannot be enforced inside the array via JSON Schema's uniqueItems on properties, so it's checked by the script).

---

## 5. MD Output Format

`RD04_Mode.md` produced at Gate 4:

````markdown
---
title: RD04 — Operating Modes
project: <project_name>
generated: YYYY-MM-DD
source: RD04_Mode.xlsx
filter: Status=Active
total_modes: <N>
schema: RD04
---

# RD04 — Operating Modes

## Mode Transition Matrix

| ModeID | ModeName | Priority | EntryCondition | ExitCondition |
|--------|----------|----------|----------------|---------------|
| M00 | Emergency | 0 | ESTOP_PRESSED OR SAFETY_FAULT | ESTOP_RESET AND FAULTS_CLEARED |
| M01 | Auto | 10 | AUTO_KEY_ON AND NO_FAULTS | AUTO_KEY_OFF OR ANY_FAULT |
| ... | ... | ... | ... | ... |

## Mode Details

### M01 — Auto

- **Description:** ...
- **Permitted:** ...
- **Restricted:** ...
- **HMI:** Green (#00AA00) — "AUTO"

### M02 — Manual

...
````

---

## 6. AI Filling Instructions (Retrofit)

```
INPUT: _parsed.md Section 5 (Mode DBs) + Section 6 (OBs, mode-switch logic)
TASK:
  1. Find the mode-transition logic (typically CASE wMode or bit manipulation)
  2. One row per mode (ModeID M00..M09)
  3. EntryCondition/ExitCondition: derive from the IF conditions in the legacy code
  4. PermittedActions: list which FBs are called in that mode block
  5. RestrictedActions: list which outputs are locked in that mode (AND NOT bMode pattern)
  6. Fix Emergency mode to M00 Priority=0
  7. You may leave PackMLState blank (rarely defined in legacy code)
  8. HMI_Color can be taken from the legacy SCADA/HMI screen; if absent, apply the ISA-101 recommendation
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: _input/brief.md + operator requirements + safety requirements
TASK:
  1. Minimum mode set: M00 Emergency, M01 Auto, M02 Manual
  2. Add extra modes per customer requirements (M03 Maintenance, M04 Setup)
  3. For each mode, list "what can be done" (permitted) first, then "what cannot" (restricted)
  4. Priority order: Emergency < Safety < Auto < Manual < Maintenance
  5. PackMLState: map to OMAC PackML if there's an international customer
  6. HMI_Text: in the customer language (PROJECT_STATE.json output_language)
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **ISA-88 §4.7** | Procedural control mode model — ModeID, Priority, PermittedActions |
| **OMAC PackML v3.0** | State machine for international packaging machinery — PackMLState column |
| **IEC 61512-1** | IEC counterpart of ISA-88, §8 mode management |
| **ISA-101** | HMI design standard — color convention for HMI_Color |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- Wrong ModeID format (`Mode1` instead of `M01`) → regex reject
- HMI_Color `#FFGG00` (invalid hex) → regex reject
- Priority written as string (`"High"`) → type reject

### 9.2 Schema/Standard (Category B) — Validator catches
- Two modes with the same Priority → script uniqueness reject
- PermittedActions empty string → minLength reject
- Priority > 99 → maximum reject

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ AI identifies an "Emergency mode" but assigns Priority=5 (confusing higher-value-is-higher-priority semantics) → Emergency must always be Priority=0
- ⚠️ RestrictedActions left blank — but every mode has at least one restriction → critical for operator safety, human verification mandatory
- ⚠️ PermittedActions and RestrictedActions conflict (same action listed in both) → logical inconsistency, contradiction in code generation
- ⚠️ Maintenance mode merged with Manual mode — they may require different operator authorization levels → must be separate modes
- ⚠️ PackMLState written as "Running" instead of "Execute" — the official OMAC value is Execute

### 9.4 Correction Request Template

> "Error in RD04 row `<ModeID>`: <category> issue: <description>. Expected: <correct value>. Fix only that row."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD04_Mode.xlsx` blank template:
- 14 columns, header + 4 example rows (M00 Emergency / M01 Auto / M02 Manual / M03 Maintenance)
- Data Validation: Status dropdown, OMAC enum dropdown for PackMLState
- Conditional Formatting: rows with Priority=0 get a red background (Emergency visual cue)

---

## 11. Related Files

- **Previous spec:** `MDSCHEMA_RAWDATA_03_FLOWCHART.md`
- **Next spec:** `MDSCHEMA_RAWDATA_05_SAFETY.md`
- **Dependent:** `MDSCHEMA_RAWDATA_03_FLOWCHART.md` (the step's `ModeReq` column references this file)
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_MODE_FROM_CODE.md`
- **Design guide (greenfield):** `02_PROJECT_TYPES/GREENFIELD/GREENFIELD_DESIGN_MODE.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD04_Mode.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd04_mode.schema.json`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_04_MODE.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Deliverable filenames updated to `RD04_Mode.xlsx/.md` to match actual project files (was `RD04_CalismaMoods`, a typo in the original). Status enum renamed to `Active/Inactive/Draft` (English, 2026-06-10 coordinated update; see RD02 spec §3.1). v1.2.0 roadmap: automatic Mermaid generation of the OMAC PackML transition diagram, multi-operator authorization levels (role-based mode access).*
