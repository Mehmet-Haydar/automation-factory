---
title: Retrofit Use Cases Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD12_UseCase
prerequisite: [MDSCHEMA_RAWDATA_12_USECASE.md, RETROFIT_EXTRACT_ALARM.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_USECASE_FROM_CODE.md
---

# RETROFIT_EXTRACT_USECASE.md — Use Cases Extraction Procedure

> **Goal:** document the operator/system interaction scenarios of the legacy machine. This is the direct source for the Gate 7 FAT/SAT test protocol.

---

## 1. Prerequisites

- [ ] RD03 Flowchart (for LinkedFlowStep), RD04 Mode (LinkedMode), RD10 FBSpec (LinkedFB)
- [ ] **Operator interview:** the most critical input — operator + maintainer + supervisor
- [ ] Existing operations manual (if any)
- [ ] HMI screen map (RD11 draft)

---

## 2. Workflow

### 2.1 Use Case = Behaviour Document

A UseCase is DIFFERENT from RD03 Flowchart and RD04 Mode:

| RD | Question |
|----|----------|
| RD03 Flowchart | "What happens inside the sequence?" |
| RD04 Mode | "Which modes exist?" |
| **RD12 UseCase** | **"Who does what, and when?"** (interaction) |

UseCase = actor + trigger + steps + outcome + exceptions.

### 2.2 Operator Interview (Critical!)

**Question guide:**

1. "What do you do when you switch the machine on in the morning?" → **Startup UseCase**
2. "What do you do during production?" → **NormalOperation**
3. "What happens in an emergency?" → **Emergency**
4. "How is maintenance performed?" → **Maintenance**
5. "Is calibration yearly or more frequent?" → **Calibration**
6. "How do you shut the machine down at end of shift?" → **Shutdown**
7. "What changes when the product changes?" → **Recipe change**
8. "Which scenarios happen most often?" → **High-frequency UseCase**

### 2.3 Hybrid Workflow

```
[1] _parsed.md + RD03 + RD04 + RD10 ready
       ↓
[2] AI prompt: PROMPT_EXTRACT_USECASE_FROM_CODE.md (draft)
       ↓
[3] Operator interview (face-to-face, video recording ideal)
       ↓
[4] Revise the AI draft with operator input
       ↓
[5] Add concrete success criteria for FATTestable=Y items
       ↓
[6] RD12_UseCase.xlsx + detailed descriptions (.md)
       ↓
[7] Derive Gate 7 FAT scenarios from this list
```

### 2.4 Scenario Structure

Every scenario MUST follow this structure:

```yaml
UseCaseID: UC001
UseCaseName: Operator_Starts_Auto_Cycle
Actor: Operator
Category: NormalOperation
Precondition: |
  - PLC in RUN mode
  - Not in M00 (Emergency)
  - All safety FBs fault-free
  - HMI screen SCR001 active
Trigger: Operator presses HMI_BTN_START_AUTO
Steps:
  1. Operator: presses the AUTO_START button (HMI_BTN_AUTO_START := TRUE)
  2. System: Mode_Auto_Cmd is set TRUE (DB_System.ModeCmd.Auto)
  3. System: FB_ModeMgr → transition to M01 (AUTO) (RD04)
  4. System: Flowchart S000 → S010 transition (RD03)
  5. System: HMI status indicator GREEN (RD11 HMI_LED_MODE)
Postcondition: |
  - gMode.CurrentMode = 1 (AUTO)
  - RD03 active step = S010
  - Production cycle started
Exceptions:
  - E-Stop pressed → M00 (Emergency), scenario aborted, ALM0001 triggered
  - Safety_OK = FALSE → scenario does not start, ALM0010 triggered
  - Operator not authorised → HMI error message "Insufficient Authorization"
LinkedFlowStep: S000, S010
LinkedMode: M01
LinkedFB: FB_ModeMgr
FATTestable: Y
Status: Active
```

### 2.5 Comprehensive Scenario List (for Most Machines)

These are the scenarios you probably need:

| ID | Category | Scenario |
|----|----------|----------|
| UC001 | NormalOperation | Operator starts auto cycle |
| UC002 | NormalOperation | Operator stops auto cycle gracefully |
| UC003 | NormalOperation | Recipe selection and load |
| UC010 | Emergency | E-Stop pressed during production |
| UC011 | Emergency | Light curtain interrupted |
| UC012 | Emergency | Safety door opened |
| UC020 | Startup | Power-on initialization |
| UC021 | Startup | Cold start (full reset) |
| UC022 | Startup | Warm start (state preserved) |
| UC030 | Shutdown | End-of-shift planned shutdown |
| UC031 | Shutdown | Emergency unplanned shutdown |
| UC040 | Maintenance | Filter change procedure |
| UC041 | Maintenance | Manual jog for setup |
| UC042 | Maintenance | LOTO (Lockout Tag-Out) |
| UC050 | Calibration | Annual sensor calibration |
| UC051 | Calibration | Reference part teach |
| UC060 | Recipe | New recipe creation |
| UC061 | Recipe | Recipe swap during production |

---

## 3. FATTestable Criteria

For FATTestable=Y the scenario must be OBJECTIVELY testable:

### 3.1 Objective Completion Criterion
- ❌ Bad: "the system worked correctly" (subjective)
- ✅ Good: "gMode.CurrentMode = 1 AND Flowchart_ActiveStep = S010 (3 seconds after test start)"

### 3.2 Repeatability
- Scenario must produce the same result over 5 repeats under the same conditions
- Random failures → FATTestable=N or expand the scenario

### 3.3 Isolatability
- Scenario must run independently of other active scenarios
- If there are dependencies, list them explicitly in the Precondition

---

## 4. Practical Tips for the Operator Interview

### 4.1 Site-Visit Plan (Half a Day)

| Time | Activity |
|------|----------|
| 09:00 | Shift start, operator runs startup → observe + take notes |
| 09:30 | Operator interview (Section 2.2 questions) |
| 10:30 | Maintenance-staff interview |
| 11:30 | Supervisor interview (authorisation, recipes) |
| 12:30 | E-Stop test (controlled), observe operator response |
| 13:30 | Mode-change demo |

### 4.2 Video Recording (with Customer Permission)

- Record the operator's HMI interaction (about 1 hour)
- Then transcribe into UseCase format step by step
- The AI can read this video transcript too (mind CONFIDENTIAL)

### 4.3 Maintenance Log / Log Books

The maintainer's paper logbook often documents typical procedures → UseCase source.

---

## 5. Validation

### 5.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD12 \
  --check-links \
  --check-fat-criteria
```

### 5.2 Manual Checklist

- [ ] At least one NormalOperation scenario per mode
- [ ] One Emergency scenario per safety function
- [ ] Startup + Shutdown scenarios
- [ ] Maintenance scenarios (filter, jog, LOTO)
- [ ] Objective criterion present on every FATTestable=Y scenario
- [ ] Steps ≥ 3
- [ ] Exceptions section present on every scenario
- [ ] LinkedFlowStep/Mode/FB references consistent

---

## 6. Common Pitfalls

- ❌ **Happy path only:** Exceptions empty → fails in the real world
- ❌ **Steps too generic:** "System starts, runs, stops" — missing concrete tags/actions
- ❌ **Vague Precondition:** "System ready" is not enough — give a concrete flag/state
- ❌ **Actor mixing:** one scenario has both operator and supervisor → split into two UCs
- ❌ **FATTestable=Y but no objective criterion:** can't be written as a test
- ❌ **Mixing Emergency with Maintenance:** Emergency = unexpected loss; Maintenance = planned
- ❌ **System actor forgotten:** automatically triggered scenarios (cron, comm trigger) → Actor=System
- ❌ **Calibration skipped:** the maintainer's annual work item ends up undocumented

---

## 7. AI Prompt Suggestion

`04_AI_PROMPTS/analyze/PROMPT_EXTRACT_USECASE_FROM_CODE.md`

The AI only produces a code-based draft. **Without the operator interview it stays incomplete.**

---

## 8. Gate 3 + Gate 7 Preparation Checklist

- [ ] Operator interview complete, notes filed
- [ ] At least one scenario per category (NormalOp / Emergency / Maintenance / Startup / Shutdown / Calibration)
- [ ] FATTestable=Y scenarios have an objective criterion
- [ ] Steps ≥ 3, each tagged with concrete references
- [ ] Exceptions section present on every scenario
- [ ] LinkedFlowStep/Mode/FB cross-ref clean
- [ ] Scenarios transferable into the Gate 7 FAT test plan template
- [ ] Maintenance-staff and supervisor scenarios (Actor) separated

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_12_USECASE.md`
- **AI prompt:** `PROMPT_EXTRACT_USECASE_FROM_CODE.md`
- **Previous:** `RETROFIT_EXTRACT_ALARM.md`
- **Next:** `RETROFIT_MODERNIZATION_GUIDE.md`
- **Dependent RDs:** RD03 (LinkedFlowStep), RD04 (LinkedMode), RD10 (LinkedFB), RD08 (Exception alarms)
- **Pipeline:** the direct source for Gate 7 FAT/SAT
- **Standards:** ISA-88 §4, UML 2.5 Use Case, IEC 62264-3

---

*v1.1.0 — Full English body (2026-05-23). UseCase = "the machine's daily life". Without the operator interview it stays incomplete. Gate 7 FAT tests are derived from here, so gaps here = test gaps = field problems.*
