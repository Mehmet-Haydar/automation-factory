---
title: Greenfield Use Cases Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD12_UseCase
prerequisite: [MDSCHEMA_RAWDATA_12_USECASE.md, GREENFIELD_DESIGN_ALARM.md, GREENFIELD_FLOWCHART.md]
---

# GREENFIELD_DESIGN_USECASE.md — Use Cases Design Guide

> **Goal:** design use cases in greenfield projects from the start in a way that fits the FAT/SAT tests. Test-first thinking.

---

## 1. Prerequisites

- [ ] RD03 Flowchart, RD04 Mode, RD10 FBSpec designs
- [ ] **Customer/operator workshop** held
- [ ] HMI mockup ready (RD11)
- [ ] Gate 7 FAT/SAT test environment planned

---

## 2. Test-First Design Approach

Greenfield advantage: you design UseCases **BEFORE the code is written**. This is test-first / behaviour-driven design:

```
[1] Design UseCases (RD12)
   ↓
[2] Reflect UseCase requirements into FB/FC design (RD10)
   ↓
[3] Sequence (RD03) and Mode (RD04) support the UseCases
   ↓
[4] Code is written
   ↓
[5] FAT tests = execution of UseCases
```

---

## 3. Standard Scenario Template

Scenarios that MUST exist in every greenfield project:

### 3.1 Lifecycle Scenarios

| ID | Scenario | Category | Actor |
|----|----------|----------|-------|
| UC020 | Power-on cold start | Startup | System |
| UC021 | Power-on warm start (retain valid) | Startup | System |
| UC022 | Operator first login of shift | Startup | Operator |
| UC030 | End-of-shift planned shutdown | Shutdown | Operator |
| UC031 | Emergency unplanned shutdown | Shutdown | Operator |
| UC032 | Long-term shutdown (weekend) | Shutdown | Supervisor |

### 3.2 Normal Operation

| ID | Scenario | Category | Actor |
|----|----------|----------|-------|
| UC001 | Operator starts auto cycle | NormalOperation | Operator |
| UC002 | Operator pauses cycle (graceful) | NormalOperation | Operator |
| UC003 | Operator stops cycle | NormalOperation | Operator |
| UC004 | Operator changes recipe | NormalOperation | Supervisor |
| UC005 | Operator views production stats | NormalOperation | Operator |

### 3.3 Emergency

| ID | Scenario | Category | Actor |
|----|----------|----------|-------|
| UC010 | E-Stop pressed during production | Emergency | Operator |
| UC011 | Light curtain interrupted | Emergency | Operator |
| UC012 | Safety door opened during cycle | Emergency | Operator |
| UC013 | Communication lost (PROFINET) | Emergency | System |
| UC014 | Tank level HighHigh | Emergency | System |

### 3.4 Maintenance

| ID | Scenario | Category | Actor |
|----|----------|----------|-------|
| UC040 | Filter change procedure | Maintenance | Technician |
| UC041 | Manual jog for setup | Maintenance | Technician |
| UC042 | LOTO (Lockout Tag-Out) | Maintenance | Technician |
| UC043 | Lubrication routine | Maintenance | Technician |
| UC044 | Belt tension adjustment | Maintenance | Technician |

### 3.5 Calibration

| ID | Scenario | Category | Actor |
|----|----------|----------|-------|
| UC050 | Annual sensor calibration | Calibration | Engineer |
| UC051 | Reference part teach | Calibration | Engineer |
| UC052 | Drive parameter tuning | Calibration | Engineer |
| UC053 | PID loop autotune | Calibration | Engineer |

---

## 4. Scenario Design Template

```yaml
UseCaseID: UC001
UseCaseName: Operator_Starts_Auto_Cycle
Actor: Operator
Category: NormalOperation
Priority: HIGH  # important sequencing for FAT

Precondition: |
  - PLC in RUN mode
  - Mode != M00 (Emergency)
  - Safety_OK = TRUE
  - HMI screen SCR001 (Main Overview) active
  - DB_System.iActiveRecipe > 0 (recipe selected)
  - Operator authentication level >= 1

Trigger: Operator presses HMI_BTN_START_AUTO

Steps:
  1. Operator: presses HMI_BTN_START_AUTO
     Tag: DB_HMI.bBtn_StartAuto := TRUE
  2. System: FB_ModeMgr evaluates (RD04 rules)
     Mode transition approved
  3. System: DB_System.ModeState.iCurrentMode := 1 (AUTO)
  4. System: HMI status indicator GREEN (#00C800)
  5. System: Flowchart S000 → S010 transition
     Tag: DB_Sequence.iActiveStep := 10
  6. System: TMR_STEP_001 starts (S010 hold time)
  7. System: Production cycle begins (RD03 normal flow)

Postcondition: |
  - DB_System.ModeState.iCurrentMode = 1
  - DB_System.ModeState.sCurrentModeName = "AUTO"
  - DB_System.ModeState.iPackMLState = 3 (Execute)
  - DB_Sequence.iActiveStep > 0 (sequence active)
  - HMI indicator GREEN

Exceptions:
  - E1: E-Stop pressed → M00 (Emergency), scenario aborted
    Expected: ALM0001 triggered, mode = 0
  - E2: Safety_OK = FALSE → scenario does not start
    Expected: ALM0010 triggered, HMI message "Safety Not OK"
  - E3: Operator not authorised → HMI error message
    Expected: "Insufficient Authorization" pop-up
  - E4: No recipe selected → HMI error message
    Expected: "No recipe loaded" pop-up

LinkedFlowStep: S000, S010
LinkedMode: M01
LinkedFB: FB_ModeMgr, FB_Sequence
LinkedAlarm: ALM0001, ALM0010

FATTestable: Y
FAT_TestProcedure: |
  Steps:
    1. Satisfy the preconditions
    2. Press HMI_BTN_START_AUTO
    3. Wait 3 seconds
  Expected result:
    - DB_System.ModeState.iCurrentMode = 1
    - DB_Sequence.iActiveStep > 0
  Pass/Fail: automatic (via PLC trace)

Status: Active
```

---

## 5. Workshop Method (With the Customer)

In greenfield, run a 1-day customer workshop before writing any code:

### 5.1 Workshop Plan

| Time | Activity | Output |
|------|----------|--------|
| 09:00 | Brief review | Shared understanding |
| 10:00 | Scenario brainstorming (whiteboard) | Scenario list |
| 11:00 | Steps writing for each scenario | Step details |
| 12:00 | Lunch | |
| 13:00 | Exception scenarios | Edge cases |
| 14:00 | FAT-criterion definition | Objective limits |
| 15:00 | HMI mockup review | UI validation |
| 16:00 | Conclusion + sign-off | RD12 draft |

### 5.2 Workshop Output

What you should have at the end:
- 15-30 scenario list (with category distribution)
- Main steps per scenario
- Objective criteria for FAT
- Customer signature (scope sign-off)

---

## 6. Converting to FAT/SAT Test Plan

UseCase → FAT test procedure:

```
UC001 (Operator_Starts_Auto_Cycle, FATTestable=Y)
   ↓ Gate 7 FAT planning
TEST-FAT-001:
  Precondition setup → automated script
  Trigger execution → manual/automated
  Postcondition check → automated PLC trace
  Pass/Fail logic → automated reporting
```

```
UC010 (E-Stop_During_Production, FATTestable=Y)
   ↓
TEST-FAT-010:
  Setup: Production running
  Trigger: Physical E-Stop press
  Check: Within 100 ms all outputs cleared
  Document: Reaction time measured
```

FATTestable=N items (e.g. annual calibration) move into the SAT procedure.

---

## 7. Validation

### 7.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD12 \
  --check-links \
  --check-fat-criteria \
  --check-coverage
```

### 7.2 Coverage Check

- [ ] At least one NormalOperation scenario per ModeID
- [ ] Emergency scenario for every safety function (RD05)
- [ ] All Startup/Shutdown lifecycles
- [ ] Maintenance scenarios (filter, jog, LOTO, lubrication)
- [ ] Calibration scenarios (annual + on-demand)

### 7.3 Manual Checklist

- [ ] Scenario workshop held, customer signed off
- [ ] Objective criterion present on FATTestable=Y items
- [ ] Steps ≥ 3, tagged with concrete references
- [ ] Exceptions on every scenario
- [ ] LinkedFlowStep/Mode/FB cross-ref clean
- [ ] Gate 7 FAT plan skeleton ready

---

## 8. Common Design Pitfalls

- ❌ **Happy path only:** field surprises because exceptions weren't considered
- ❌ **Subjective FAT criterion:** "Should work fine" — not testable
- ❌ **Calibration forgotten:** annual work items end up undocumented
- ❌ **LOTO scenario missing:** OSHA / EN ISO 14118 violation
- ❌ **Multi-actor scenario:** single scenario has both operator and supervisor — split in two
- ❌ **Steps too generic:** missing concrete tag/action
- ❌ **Weak Precondition:** "System ready" is not enough
- ❌ **Skipping the workshop:** designing without bringing the customer in → scope issues

---

## 9. Design-Approval Checklist

- [ ] Customer workshop held, scope signed
- [ ] Scenarios cover all 5 categories (NormalOp / Emergency / Maintenance / Startup / Shutdown / Calibration)
- [ ] FATTestable=Y scenarios have objective criteria
- [ ] Steps ≥ 3 on every scenario
- [ ] Exceptions section on every scenario
- [ ] LinkedFlowStep/Mode/FB references consistent
- [ ] FAT test plan skeleton derived
- [ ] SAT (field) procedures in a separate document

---

## 10. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_12_USECASE.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_USECASE.md`
- **Previous:** `GREENFIELD_DESIGN_ALARM.md`
- **Next:** (last document of Phase 4)
- **Dependent RDs:** RD03 (LinkedFlowStep), RD04 (LinkedMode), RD10 (LinkedFB), RD08 (Exception alarms)
- **Pipeline:** direct source for Gate 7 FAT/SAT
- **Standards:** ISA-88 §4, UML 2.5 Use Case, IEC 62264-3

---

*v1.1.0 — Full English body (2026-05-23). In greenfield, UseCase = FAT test plan. It makes sense to think this through BEFORE writing code: the code is then written to support the scenarios.*
