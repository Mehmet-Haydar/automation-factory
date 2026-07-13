---
title: RD12_UseCase — Kunde Müller (placeholder, awaiting customer workshop)
last_validated: 2026-05
status: ACTIVE
---

# RD12_UseCase — Kunde Müller (placeholder, awaiting customer workshop)

```yaml
status: DRAFT (25%)
workshop_pending: 2026-05-25
```

## Summary (to expand after the workshop)
- AI draft: 8 use cases
- Expected to grow to 15-20 after operator interview + customer workshop

## Scenarios (draft)

| UseCaseID | UseCaseName | Actor | Category | FATTestable | Status |
|-----------|-------------|-------|----------|-------------|--------|
| UC001 | Operator_Starts_Auto_Cycle | Operator | NormalOperation | Y | DRAFT |
| UC002 | Operator_Stops_Cycle_Gracefully | Operator | NormalOperation | Y | DRAFT |
| UC010 | EStop_North_Pressed | Operator | Emergency | Y | DRAFT |
| UC011 | EStop_South_Pressed | Operator | Emergency | Y | DRAFT |
| UC012 | LightCurtain_Loading_Interrupted | Operator | Emergency | Y | DRAFT |
| UC020 | PowerOn_ColdStart | System | Startup | Y | DRAFT |
| UC030 | EndOfShift_Shutdown | Operator | Shutdown | Y | DRAFT |
| UC040 | FilterChange_Procedure | Technician | Maintenance | N | DRAFT |

## UC001 Detail (example)

```yaml
UseCaseID: UC001
UseCaseName: Operator_Starts_Auto_Cycle
Actor: Operator
Category: NormalOperation

Precondition: |
  - PLC RUN
  - Mode != M00 (Emergency)
  - F_DB_EStop.bQ = TRUE (Safety OK)
  - HMI SCR001 active
  - A recipe is selected (DB_Recipe.iActive > 0)

Trigger: Operator presses HMI_BTN_AUTO_START

Steps:
  1. Operator: HMI_BTN_AUTO_START.click()
  2. System: DB_HMI.bBtn_AutoStart = TRUE
  3. System: FB_ModeMgr → M01 (AUTO) transition
  4. System: FC_Sequence S000 → S010
  5. System: HMI_LED_MODE → GREEN (#00C800)

Postcondition: |
  - DB_System.ModeState.iCurrentMode = 1
  - DB_System.ModeState.iPackMLState = 3 (Execute)
  - DB_Sequence.iActiveStep > 0

Exceptions:
  - If E-Stop is pressed → M00, ALM0001
  - Safety_OK=FALSE → the scenario does not start, ALM_SAFETY_NOT_OK

FATTestable: Y
Test: TEST-FAT-001-001 (automated test script)
```

*v1.0.0 — To be detailed through the customer workshop.*
