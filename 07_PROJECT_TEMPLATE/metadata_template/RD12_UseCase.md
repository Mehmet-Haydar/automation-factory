# RD12_UseCase — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_12_USECASE.md`. Schema: `rd12_usecase.schema.json`.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <Engineer Name>
filled_at: <YYYY-MM-DD>
workshop_date: <YYYY-MM-DD>      # customer workshop date
status: <DRAFT | REVIEWED | APPROVED>
```

---

## Summary

- Total scenarios: __
- Category: NormalOp __ | Emergency __ | Maintenance __ | Startup __ | Shutdown __ | Calibration __
- FATTestable=Y: __
- Operator __ | Supervisor __ | Technician __ | System __

---

## Scenarios

### UC001 — Operator_Starts_Auto_Cycle (NormalOperation)

- **Actor:** Operator
- **Precondition:** PLC RUN; NOT M00; Safety_OK; SCR001 active; recipe selected
- **Trigger:** Operator presses HMI_BTN_START_AUTO
- **Steps:**
  1. Operator: presses the AUTO_START button
  2. System: Mode_Auto_Cmd = TRUE is set
  3. System: FB_ModeMgr → transitions to M01 (AUTO)
  4. System: Flowchart S000 → S010 transition
  5. System: HMI status indicator GREEN
- **Postcondition:** gMode.CurrentMode = 1; RD03 active step = S010
- **Exceptions:**
  - If E-Stop is pressed → M00, scenario aborted, ALM0001
  - If Safety_OK is false → ALM0010
- **LinkedFlowStep:** S000, S010
- **LinkedMode:** M01
- **LinkedFB:** FB_ModeMgr, FB_Sequence
- **FATTestable:** Y
- **Status:** Active

### UC010 — Emergency_Stop_During_Production (Emergency)

- **Actor:** Operator
- **Precondition:** M01 (AUTO) active, production cycle running
- **Trigger:** Operator presses the physical E-Stop button
- **Steps:**
  1. Operator: presses the physical E-Stop button
  2. System: F_I_EStop signal goes FALSE
  3. System: F_FB_EStop1 → All_Outputs := FALSE (within 100ms)
  4. System: Mode → M00 (Emergency)
  5. System: ALM0001 is triggered, the HMI shows the alarm widget
- **Postcondition:** gMode.CurrentMode = 0; all motor outputs FALSE; ALM0001 active
- **Exceptions:**
  - F-PLC failure → backup electromechanical disconnection
- **LinkedFlowStep:** S099
- **LinkedMode:** M00
- **LinkedSF:** SF001
- **LinkedAlarm:** ALM0001
- **FATTestable:** Y
- **Status:** Active

---

## Summary Table

| UseCaseID | UseCaseName | Actor | Category | FATTestable | Status |
|-----------|-------------|-------|----------|-------------|--------|
| UC001 | Operator_Starts_Auto_Cycle | Operator | NormalOperation | Y | Active |
| UC010 | Emergency_Stop_During_Production | Operator | Emergency | Y | Active |
| UC020 | Power_On_Cold_Start | System | Startup | Y | Active |
| UC030 | End_Of_Shift_Shutdown | Operator | Shutdown | Y | Active |
| UC040 | Filter_Change_Procedure | Technician | Maintenance | N | Active |
| UC050 | Annual_Sensor_Calibration | Engineer | Calibration | N | Active |

---

## #UNKNOWNS

| Scenario | Reason |
|----------|--------|
| | |

---

## Fill-in Notes

- **UseCaseID format:** `^UC\d{3}$`
- **Actor enum:** Operator/Supervisor/Technician/System
- **Category enum:** NormalOperation/Emergency/Maintenance/Startup/Shutdown/Calibration
- **Steps min 3** (concrete tag/action)
- **Exceptions present in every scenario**
- **FATTestable=Y → objective criterion mandatory** (concrete PostCondition)
- **Customer approval via a workshop is recommended**
- **Standards:** ISA-88 §4, UML 2.5 Use Case, IEC 62264-3

---

*Template v1.0.0 — RD12 Use Cases. The source for Gate 7 FAT/SAT.*
