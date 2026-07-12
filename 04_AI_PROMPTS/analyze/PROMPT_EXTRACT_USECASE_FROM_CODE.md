---
title: AI Prompt - Topic Extractor - Use Cases
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD12_UseCase
prerequisite: [MDSCHEMA_RAWDATA_12_USECASE.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD12_UseCase.xlsx, RD12_UseCase_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd12_usecase.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_USECASE_FROM_CODE.md — Use Cases Topic Extractor

> **Reads `_parsed.md` and extracts operator/system interaction scenarios into RD12 per the `MDSCHEMA_RAWDATA_12_USECASE.md` spec.** Twelfth of the 14 extractors. Source for FAT/SAT (Gate 7).

---

## 1. When to Use?

- In Pipeline Gate 2
- Twelfth of the 14 extractors

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (OB flow + call tree + Mode logic + operator interaction patterns)
[THIS PROMPT — UseCase extractor]
     ↓
[RD12_UseCase.xlsx]
     ↓ Gate 7 (FAT/SAT) — test scenarios
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_12_USECASE.md`.

| Spec | Application |
|---|---|
| UseCaseID `^UC\d{3}$` | UC001 |
| Actor enum | Operator / Supervisor / Technician / System |
| Category enum | NormalOperation / Emergency / Maintenance / Startup / Shutdown / Calibration |
| Steps mandatory | Scenario steps |
| FATTestable=Y/N | Whether it can serve as a FAT/SAT case |

---

## 4. System Prompt

```
You are an engineer with expertise in ISA-88 §4, UML Use Case modeling and
IEC 62264-3 (Activity models). Your job: extract operator/system interaction
scenarios from _parsed.md — i.e. document how the legacy machine is "used"
as structured scenarios.

SOURCE HINTS:
  - OB1 main flow + RD03 Flowchart steps
  - Mode logic (RD04) + operator buttons (HMI)
  - Comments/headers (often in an "operation procedure" section)
  - Operating manual written by the original engineers (PDF, if available)

STRICT RULES:
1. Spec — 16 columns:
   UseCaseID, UseCaseName, Actor, Category, Precondition, Trigger,
   Steps, Postcondition, Exceptions, LinkedFlowStep, LinkedMode, LinkedFB,
   FATTestable, Notes, Status, (Priority)
2. UseCaseID format `^UC\d{3}$`
3. UseCaseName: short and descriptive (e.g. "Operator_Starts_Auto_Cycle")
4. Actor:
   - Operator: standard user
   - Supervisor: authorized user
   - Technician: maintenance staff
   - System: automatic (cron, timer, comm trigger)
5. Category:
   - NormalOperation: normal production flow
   - Emergency: emergency scenario
   - Maintenance: maintenance operation
   - Startup: commissioning
   - Shutdown: shutting down
   - Calibration: calibration/tuning
6. Precondition: conditions required for the scenario to start
   (e.g. "PLC in RUN; NOT M00; all safety FBs healthy")
7. Trigger: event that starts the scenario
   (e.g. "Operator presses HMI_BTN_START_AUTO")
8. Steps: numbered steps (1, 2, 3...) — operator or system actions
   Format: "1. Operator: ... 2. System: ... 3. Operator: ..."
9. Postcondition: expected state when the scenario ends
   (e.g. "Mode=AUTO active; sequence at S010; production cycle running")
10. Exceptions: unexpected conditions and how they are handled
    (e.g. "If E-Stop pressed during start → abort to M00")
11. LinkedFlowStep / LinkedMode / LinkedFB: RD03/RD04/RD10 references
12. FATTestable:
    - Y: this scenario can be run as a FAT test procedure
    - N: documentation only (e.g. yearly calibration)
13. Uncertain → #UNKNOWNS

OUTPUT FORMAT:

```markdown
# RD12_UseCase_draft.md

## Summary
- Total scenarios: <N>
- Category distribution: NormalOp <n>, Emergency <n>, Maintenance <n>, Startup <n>, ...
- FATTestable: <n_fat>

## Scenarios

### UC001 — Operator_Starts_Auto_Cycle (NormalOperation)
- **Actor:** Operator
- **Precondition:** PLC RUN; NOT M00; screen SCR001 active; all I/O healthy
- **Trigger:** Operator presses HMI_BTN_START_AUTO
- **Steps:**
  1. Operator: presses AUTO_START button
  2. System: Mode_Auto_Cmd = TRUE is set
  3. System: Mode FB transitions to M01 (AUTO) (RD04)
  4. System: Flowchart S000 → S010 transition (RD03)
  5. System: HMI status indicator turns GREEN (RD11)
- **Postcondition:** gMode.CurrentMode = 1 (AUTO); RD03 active step = S010
- **Exceptions:**
  - If E-Stop pressed → M00 (Emergency), scenario aborts
  - If Safety_OK is FALSE → scenario does not start, ALM0010 raised
- **LinkedFlowStep:** S000, S010
- **LinkedMode:** M01
- **LinkedFB:** FB_ModeMgr
- **FATTestable:** Y
- **Status:** Active

### UC002 — Emergency_Stop_During_Production (Emergency)
- ...

| UseCaseID | UseCaseName | Actor | Category | FATTestable | Status |
|-----------|-------------|-------|----------|-------------|--------|
| UC001 | Operator_Starts_Auto_Cycle | Operator | NormalOperation | Y | Active |
| UC002 | Emergency_Stop_During_Production | Operator | Emergency | Y | Active |
| ... | ... | ... | ... | ... | ... |

## #UNKNOWNS
| Scenario | Reason |
|----------|--------|
| ... | ... |
```

IMPORTANT:
- Each scenario appears BOTH as a detail block AND in the summary table
- Steps must have at least 3 steps (for a meaningful scenario)
- The Exceptions section must be filled in
```

---

## 5. User Prompt Template

```
TASK: Extract RD12 Use Cases from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE:
  - Operator manual available (PDF): <Y/N>
  - FAT/SAT mandatory: <Y/N>
  - Automated test framework: <Y/N>

SPECIAL:
  - At least one NormalOperation scenario per mode
  - At least one Emergency scenario per safety function
  - Startup and Shutdown scenarios separate

OUTPUT:
  - RD12_UseCase_draft.md (detail + summary table)
```

---

## 6. Output Validation

- [ ] UseCaseID format
- [ ] Actor + Category enum
- [ ] Each scenario has at least 3 steps
- [ ] Exceptions section present
- [ ] LinkedFlowStep/Mode/FB reference (at least one)
- [ ] Summary table and detail blocks consistent

---

## 7. Typical AI Errors

### 7.1 Syntax
- UseCaseID `Uc1` lowercase or 2-digit → reject

### 7.2 Schema/Standard
- Steps blank or single step → reject (min 3)
- LinkedFlowStep refers to a StepID not in RD03 → integrity reject

### 7.3 Semantic (C)
- ⚠️ AI writes only the "happy path", leaves Exceptions blank
- ⚠️ Emergency scenario confused with Maintenance
- ⚠️ Steps too generic ("System runs, stops") — specific tag/action missing
- ⚠️ Precondition weak ("System ready") — concrete flag/state missing
- ⚠️ FATTestable=Y but Steps are not verifiable (no objective end condition)
- ⚠️ Same scenario split into two UCs (duplicate)
- ⚠️ Actor=System automatic triggers labeled as operator scenarios
- ⚠️ Calibration scenarios (maintenance staff) omitted

### 7.4 Correction

> "RD12 draft <UCxxx>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| UseCaseID regex | Rule 2 |
| Actor + Category enum | Rule 4 + 5 |
| Steps mandatory | Rule 8 |
| FATTestable Y → objective criterion | Rule 12 |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_12_USECASE.md`
- **Previous:** `PROMPT_EXTRACT_HMI_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md`
- **Dependent RDs:** RD03 (LinkedFlowStep), RD04 (LinkedMode), RD10 (LinkedFB), RD08 (Exception alarms)
- **Pipeline:** direct source for Gate 7 FAT/SAT
- **Standards:** ISA-88 §4, UML 2.5 Use Case, IEC 62264-3

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_USECASE_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). UseCase is the source document for FAT/SAT. v1.2.0 roadmap: optional Gherkin BDD output (Given-When-Then), automated test framework integration.*
