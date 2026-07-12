---
title: Project Maestro Template
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [FACTORY_MAESTRO.md]
status: ACTIVE
---

# PROJECT_MAESTRO_TEMPLATE — Project Orchestrator Template

> **Purpose:** The main orchestrator document copied for each new project. `script_project_init.py` fills in the placeholders. This file is the project's "internal compass" — all RDs, gates, and decisions are visible in one place.

---

## 0. Project Meta

```yaml
project_id: <PROJECT_CODE>          # e.g. AUTO-2026-001
project_name: <Project Name>        # e.g. Customer XYZ Conveyor Line
customer: <Customer Name>           # e.g. Customer XYZ GmbH
project_type: <retrofit | greenfield>
output_language: <TR | EN | DE>     # code comments + HMI language
data_classification: <PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED>
project_start: <YYYY-MM-DD>
project_target: <YYYY-MM-DD>        # target SAT date
project_lead: <Engineer Name>
safety_engineer: <assigned certified engineer>
factory_version: v3.0.0-alpha
```

---

## 1. Factory References

This project depends on the following factory files:

| Type | File | Version |
|------|------|---------|
| Pipeline | `PIPELINE_CODE_REWRITE.md` | <factory_version> |
| Naming | `01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md` | <v> |
| Data class | `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md` | <v> |
| Language policy | `01_GLOBAL_STANDARDS/rules/GLOBAL_LANG_POLICY.md` | <v> |
| Metadata schema | `01_GLOBAL_STANDARDS/rules/GLOBAL_METADATA_SCHEMA.md` | <v> |
| Maestro (by project type) | `02_PROJECT_TYPES/<RETROFIT|GREENFIELD>/<TYPE>_MAESTRO.md` | <v> |
| FB template | `01_GLOBAL_STANDARDS/code_templates/GLOBAL_FB_TEMPLATE.scl` | <v> |

---

## 2. Pipeline Gate Progress

```
Gate 1: DISCOVERY         [STATUS]   completed: <YYYY-MM-DD>
Gate 2: EXTRACTION        [STATUS]   completed: <YYYY-MM-DD>
Gate 3: HUMAN REVIEW      [STATUS]   completed: <YYYY-MM-DD>
Gate 4: VALIDATION        [STATUS]   completed: <YYYY-MM-DD>
Gate 5: CODE GENERATION   [STATUS]   completed: <YYYY-MM-DD>
Gate 6: SIMULATION        [STATUS]   completed: <YYYY-MM-DD>
Gate 7: FAT/SAT           [STATUS]   completed: <YYYY-MM-DD>
```

**Status values:** `pending` / `in_progress` / `blocked` / `completed`

---

## 3. 14-Point Raw Data Pack Status

| RD | File | Status | Source | Fill-in |
|----|------|--------|--------|---------|
| RD01 | RD01_IO_List.md | <DRAFT/REVIEWED/APPROVED> | <AI/Customer Excel/Manual> | <percent> |
| RD02 | RD02_DataDict.md | <...> | <...> | <...> |
| RD03 | RD03_Flowchart.md | <...> | <...> | <...> |
| RD04 | RD04_Mode.md | <...> | <...> | <...> |
| RD05 | RD05_Safety_DRAFT_UNVERIFIED.md | DRAFT_UNVERIFIED | AI + Safety Eng. | <...> |
| RD06 | RD06_Motion.md | <...> | <...> | <...> |
| RD07 | RD07_Timing.md | <...> | <...> | <...> |
| RD08 | RD08_Alarm.md | <...> | <...> | <...> |
| RD09 | RD09_Comms.md | <...> | <...> | <...> |
| RD10 | RD10_FBSpec.md | <...> | <...> | <...> |
| RD11 | RD11_HMI.md | <...> | <...> | <...> |
| RD12 | RD12_UseCase.md | <...> | <...> | <...> |
| RD13 | RD13_Annotation.md | <retrofit-specific> | AI + Manual | <...> |
| RD14 | RD14_Modernization.md | <retrofit-specific> | AI + Customer decision | <...> |

---

## 4. Project-Specific Decisions

Decisions specific to this project (if there is any deviation from the factory standard):

| Date | Decision | Reason | Decision Owner |
|------|----------|--------|----------------|
| | | | |

Typical deviation examples:
- The customer wants to keep using PROFIBUS_DP (not migrating to PROFINET)
- The old HMI panel will be kept (no new screen)
- The recipe system will stay in the existing SCADA (not in the PLC)

---

## 5. Data Classification + AI Policy

```
data_classification: <class>
```

AI usage discipline based on this class:

| Class | AI Usage |
|-------|----------|
| 🟢 PUBLIC | Public AI services (ChatGPT.com, claude.ai) can be used |
| 🟡 INTERNAL | Cursor (enterprise tier) or self-hosted AI |
| 🟠 CONFIDENTIAL | **ONLY** self-hosted or Enterprise AI |
| 🔴 RESTRICTED | Air-gapped system, AI usage restricted |

---

## 6. Safety (RD05) Tracking

> ⚠️ Mandatory section for projects that include a safety function.

```yaml
safety_engineer:
  name: <name>
  certification: <TÜV / VDE / IEC 61508>
  cert_number: <number>
  contact: <email/phone>

risk_assessment:
  document_id: <document ID>
  date: <YYYY-MM-DD>
  iso_12100: <done/none>

sil_requirements:
  - function: SF001 EStop_North
    required: SIL2 (set by operator)
    achieved: <SIL_Level (measured by engineer)>
    status: <DRAFT_UNVERIFIED | APPROVED>
```

---

## 7. Team + Responsibility Matrix

| Role | Name | Responsibility |
|------|------|----------------|
| Project Lead | | Overall responsibility |
| Lead Engineer | | Code generation |
| Safety Engineer | | RD05 + risk assessment |
| HMI Designer | | RD11 |
| Customer Contact | | Workshop + approval |
| Test Lead | | Gate 7 FAT/SAT |

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| | | | |

---

## 9. Linked Files

### 9.1 Project Files
- `<project>/README.md` — Project overview
- `<project>/PROJECT_STATE.json` — Machine-readable state
- `<project>/metadata/RD<NN>.md` — Filled-in 14-point pack
- `<project>/_input/` — Customer source files (CONFIDENTIAL!)
- `<project>/_output/` — Generated SCL code (Gate 5+)

### 9.2 Factory Files
- `PIPELINE_CODE_REWRITE.md` — Gate orchestrator
- `FACTORY_MAESTRO.md` — Factory-wide orchestrator
- `01_GLOBAL_STANDARDS/` — All rules
- `02_PROJECT_TYPES/<TYPE>/<TYPE>_MAESTRO.md` — Project-type maestro

---

## 10. Sprint Log

| Sprint | Goal | Completed | Next |
|--------|------|-----------|------|
| 2026-W19 | RD01-RD05 | | |
| 2026-W20 | RD06-RD10 | | |
| 2026-W21 | RD11-RD14 | | |
| 2026-W22 | Gate 4 + Gate 5 | | |

---

## 11. Notes

(Free-form notes taken during the project)

---

*This file is the project's living document. It is updated at every gate progression. Its final form at project end becomes part of the "as-built" document delivered to the customer.*
