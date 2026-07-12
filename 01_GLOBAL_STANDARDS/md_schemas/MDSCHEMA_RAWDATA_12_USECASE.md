---
title: Raw Data Schema #12 — Use Cases
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_03_FLOWCHART.md, MDSCHEMA_RAWDATA_04_MODE.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_03_FLOWCHART.md, MDSCHEMA_RAWDATA_04_MODE.md, PROMPT_EXTRACT_USECASE_FROM_CODE.md]
schema: RAWDATA
rd_number: 12
deliverable: [RD12_UseCase.xlsx, RD12_UseCase.md, rd12_usecase.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [ISA-88 §4 procedure model, UML Use Case, IEC 62264-3]
---

# MDSCHEMA_RAWDATA_12_USECASE.md — Use Cases Specification

> **This file defines how the project's "12 — Use Cases" raw data file should be structured.** Documents how the operator interacts with the machine, typical workflows, exception cases and maintenance procedures. The raw-data source of FAT/SAT test scenarios.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual use-case list (`RD12_UseCase.xlsx` / `.md`) must conform to this spec.

- ✅ Steps of each use case (operator perspective)
- ✅ Preconditions and postconditions
- ✅ Exception cases and how to handle them
- ✅ Cross-references to related FB / Flowchart steps
- ✅ Potential conversion into FAT/SAT test steps

**This file is NOT:**
- ❌ Technical sequence steps (that's RD03 Flowchart — machine perspective)
- ❌ Alarm list (that's RD08 — exception conditions are referenced here, not defined)
- ❌ FAT protocol (a separate document — but derived from this spec)

**RD03 vs RD12 difference:** RD03 = what the machine does (step, condition, action). RD12 = what the operator does (UI interaction, decision points, maintenance).

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Legacy operator manual + field walkdown + HMI screen captures + existing work instructions | AI (`PROMPT_EXTRACT_USECASE_FROM_CODE.md`) — _parsed.md Section 6 (OB), 10 (call tree), 11 (comments) | `script_consistency_check.py` |
| **Greenfield** | Customer operation requirements + machine spec + FAT criteria | Human (project engineer + customer together) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** → **Gate 3** → **Gate 4** (GREEN). RD12 maps directly to Gate 7 FAT/SAT test scenarios.

---

## 3. Excel Column Definition (Required)

`RD12_UseCase.xlsx` must contain the following columns **in this order**:

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `UseCaseID` | string | ✅ | `^UC\d{3}$` | Scenario identifier (e.g., `UC001` Normal Production, `UC002` Emergency Stop) |
| 2 | `UseCaseName` | string | ✅ | min 3 characters, EN | Short scenario name |
| 3 | `Actor` | enum | ✅ | `Operator`, `Supervisor`, `Technician`, `System` | Party that starts the scenario |
| 4 | `Category` | enum | ✅ | `NormalOperation`, `Emergency`, `Maintenance`, `Startup`, `Shutdown`, `Calibration` | Scenario category |
| 5 | `Precondition` | string | ✅ | min 5 characters | Conditions that must hold before the scenario starts |
| 6 | `Trigger` | string | ✅ | min 3 characters | Event that starts the scenario (operator action or system state) |
| 7 | `Steps` | string | ✅ | min 10 characters | Step-by-step procedure (1. ... 2. ... format) |
| 8 | `Postcondition` | string | ✅ | min 5 characters | Expected system state after successful completion |
| 9 | `Exceptions` | string | ⚪ | (free) | Exception cases that can arise and their response |
| 10 | `LinkedFlowStep` | string | ⚪ | (free — comma-separated S+IDs) | Cross-reference to RD03 StepID |
| 11 | `LinkedMode` | string | ⚪ | (free — ModeID) | Cross-reference to RD04 ModeID |
| 12 | `LinkedFB` | string | ⚪ | (free — comma-separated BlockNames) | Cross-reference to RD10 BlockName |
| 13 | `FATTestable` | enum | ✅ | `Y`, `N` | Can this scenario be tested in FAT? |
| 14 | `Notes` | string | ⚪ | (free) | Customer-specific condition, safety note |
| 15 | `Status` | enum | ✅ | `Active`, `Inactive`, `Draft` | Renamed to English (2026-06-10); legacy Turkish literals (`Aktif`/`Pasif`/`Taslak`/`Yedek`) in existing projects remain readable by the tooling |

### 3.1 Column Descriptions (Detail)

**Actor (3):**
- `Operator` → daily production operator (lowest authority)
- `Supervisor` → shift lead (parameter-change right)
- `Technician` → maintenance technician (maintenance mode, hardware test)
- `System` → fully automatic (no human trigger)

**Category (4):**
- `NormalOperation` → daily production cycle
- `Emergency` → emergency stop, evacuation
- `Maintenance` → maintenance, lubrication, filter change
- `Startup` → first start, shift start
- `Shutdown` → planned shutdown, shift end
- `Calibration` → sensor calibration, homing

**Steps (7):** sequential step format:
```
1. Operator presses "Start" on the HMI
2. System runs the homing sequence (UC001 → S010)
3. When homing finishes, the HMI green indicator lights
4. Operator places the part at the loading position
5. Operator presses "Part Loaded"
...
```

**FATTestable (13):** `Y` → this scenario is auto-transferred into the FAT protocol. `N` → can only be tested in SAT or simulation.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd12_usecase.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD12 — Use Cases",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["UseCaseID","UseCaseName","Actor","Category","Precondition","Trigger","Steps","Postcondition","FATTestable","Status"],
    "additionalProperties": false,
    "properties": {
      "UseCaseID":       { "type": "string", "pattern": "^UC\\d{3}$" },
      "UseCaseName":     { "type": "string", "minLength": 3 },
      "Actor":           { "enum": ["Operator","Supervisor","Technician","System"] },
      "Category":        { "enum": ["NormalOperation","Emergency","Maintenance","Startup","Shutdown","Calibration"] },
      "Precondition":    { "type": "string", "minLength": 5 },
      "Trigger":         { "type": "string", "minLength": 3 },
      "Steps":           { "type": "string", "minLength": 10 },
      "Postcondition":   { "type": "string", "minLength": 5 },
      "Exceptions":      { "type": "string" },
      "LinkedFlowStep":  { "type": "string" },
      "LinkedMode":      { "type": "string" },
      "LinkedFB":        { "type": "string" },
      "FATTestable":     { "enum": ["Y","N"] },
      "Notes":           { "type": "string" },
      "Status":          { "enum": ["Active","Inactive","Draft"] }
    }
  }
}
```

---

## 5. MD Output Format

`RD12_UseCase.md` produced at Gate 4:

````markdown
---
title: RD12 — Use Cases
project: <project_name>
generated: YYYY-MM-DD
source: RD12_UseCase.xlsx
filter: Status=Active
total_usecases: <N>
fat_testable: <Nfat>
schema: RD12
---

# RD12 — Use Cases

## Scenario Summary

| UseCaseID | UseCaseName | Actor | Category | FATTestable |
|-----------|-------------|-------|----------|-------------|
| UC001 | NormalProduction | Operator | NormalOperation | Y |
| UC002 | EmergencyStop | Operator | Emergency | Y |
| ... | ... | ... | ... | ... |

## UC001 — NormalProduction

**Actor:** Operator | **Category:** NormalOperation | **FAT:** ✅

**Precondition:** Machine powered on, E-Stop reset, safety doors closed

**Trigger:** Operator presses "Start Production" on the HMI

**Steps:**
1. ...
2. ...

**Postcondition:** Product on the outfeed conveyor, machine in ready state

**Exceptions:** ...

**Cross-reference:** S010-S040, M01_Auto, FB_Motor, FB_Conveyor
````

---

## 6. AI Filling Instructions (Retrofit)

```
INPUT: _parsed.md Section 6 (OBs), 10 (call tree), 11 (comments — operator notes)
TASK:
  1. From OBs derive the main production loops → NormalOperation scenarios
  2. From alarm OBs (OB82, OB86) → Emergency scenarios
  3. From legacy comments mentioning "Anfahren", "Einrichten", "Stopp" blocks → Startup/Shutdown/Maintenance
  4. LinkedFlowStep: match with RD03 step IDs
  5. LinkedMode: match with RD04 mode IDs
  6. Steps: translate the sequentially-written code logic into the operator perspective
  7. Exceptions: derive from the IF-ERROR branches in the legacy code
  8. FATTestable: Y if the scenario can be simulated with the machine accessible
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: _input/brief.md + customer operation requirements + FAT criteria
TASK:
  1. Minimum scenario set: Normal Production, Emergency Stop, Startup, Shutdown
  2. Customer-specific scenarios: recipe change, material change, CIP/SIP cleaning
  3. Write Steps step by step (numbered list — converts directly into a FAT checklist)
  4. Exceptions: every possible alarm + its response procedure
  5. FATTestable=Y scenarios → derive a simulation test plan
  6. By Actor level: Technician scenarios → PLC maintenance mode (M03)
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **ISA-88 §4** | Procedural model — Category enum (Startup, Normal, Shutdown, Emergency) |
| **UML Use Case** | Actor/Scenario/Precondition/Postcondition structure — the spec's base format |
| **IEC 62264-3** | MES/ERP-PLC integration — System Actor scenarios |
| **GAMP 5** | Use-case requirement for validation & testing (GxP industries) |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- UseCaseID `UC01` (not 3 digits) → regex reject
- Actor `operator` (lowercase, enum) → enum reject
- Steps shorter than 5 characters → minLength reject

### 9.2 Schema/Standard (Category B) — Validator catches
- Required column (Precondition, Postcondition) blank → required reject

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ AI writes what the machine does (system perspective) instead of what the operator does → RD12 = operator perspective; steps must be "Operator does X, system does Y"
- ⚠️ Exceptions column blank — but each scenario should have at least one exception thought through (e.g., what if motor doesn't start?)
- ⚠️ All scenarios FATTestable=Y — some can only be tested on the real machine on site (calibration, under load)
- ⚠️ LinkedFlowStep/LinkedMode left blank — a UC003 Maintenance scenario should trigger M03 mode; missing this link creates inconsistency

### 9.4 Correction Request Template

> "Error in RD12 scenario `<UseCaseID>`: <category> issue: <description>. Expected: <correct value>. Fix only that row."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD12_UseCase.xlsx` blank template:
- 15 columns, header + 4 example rows (NormalOperation / EmergencyStop / Startup / Maintenance)
- Data Validation: Actor, Category, FATTestable, Status dropdowns
- Conditional Formatting: rows with FATTestable=Y get a green background (in FAT scope)
- Separate sheet: "FATProtocol" — auto-filter for FATTestable=Y rows, test-checklist format

---

## 11. Related Files

- **Dependency:** `MDSCHEMA_RAWDATA_03_FLOWCHART.md` (LinkedFlowStep cross-reference)
- **Dependency:** `MDSCHEMA_RAWDATA_04_MODE.md` (LinkedMode cross-reference)
- **Dependency:** `MDSCHEMA_RAWDATA_10_FBSPEC.md` (LinkedFB cross-reference)
- **Next spec:** `MDSCHEMA_RAWDATA_13_ANNOTATION.md`
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_USECASE_FROM_CODE.md`
- **Design guide (greenfield):** `02_PROJECT_TYPES/GREENFIELD/GREENFIELD_DESIGN_USECASE.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD12_UseCase.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd12_usecase.schema.json`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_12_USECASE.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Deliverable filenames updated to `RD12_UseCase.xlsx/.md` to match actual project files. Source document for FAT/SAT test scenarios. Status enum renamed to `Active/Inactive/Draft` (English, 2026-06-10 coordinated update; see RD02 spec §3.1). v1.2.0 roadmap: BDD (Behavior Driven Development) Given/When/Then format option, GAMP 5 IQ/OQ/PQ validation alignment.*
