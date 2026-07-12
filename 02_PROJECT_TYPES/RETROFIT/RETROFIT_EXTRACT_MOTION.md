---
title: Retrofit Motion System Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD06_Motion
prerequisite: [MDSCHEMA_RAWDATA_06_MOTION.md, RETROFIT_EXTRACT_DATADICT.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_MOTION_FROM_CODE.md
---

# RETROFIT_EXTRACT_MOTION.md — Motion System Extraction Procedure

> **Goal:** extract the drive/axis/servo system from the legacy PLC code into RD06 aligned with PLCopen Motion Control v2.0.

---

## 1. Prerequisites

- [ ] RD01 IO complete (Motor/Feedback tags)
- [ ] RD02 DataDict complete (DriveDB)
- [ ] Drive vendor + model known (SINAMICS, Allen-Bradley Kinetix, etc.)
- [ ] Drive parameter files if available (`.dlc`, `.acd`, etc.)
- [ ] Mechanical info: motor power, gear ratio, max velocity/acceleration

---

## 2. Determine the Drive Type

| Legacy drive | DriveType (RD06) |
|--------------|------------------|
| MICROMASTER 4 + analog command | VFD_Analog |
| SINAMICS G120 (PROFIBUS/PROFINET) | VFD_Profidrive |
| SINAMICS S120 (servo) | Servo_Profidrive |
| Beckhoff AX5xxx (EtherCAT) | Servo_EtherCAT |
| Allen-Bradley Kinetix 5500/5700 | Servo_EtherCAT |
| Lenze 9300 / 8400 / i550 | VFD_Profidrive (newer) / VFD_Analog |
| SEW MoviAxis / MoviDrive | Servo_Profidrive |
| Stepper indexer (PUL/DIR) | Stepper |

---

## 3. Workflow

```
[1] _parsed.md + RD01 + RD02 ready
       ↓
[2] AI prompt: PROMPT_EXTRACT_MOTION_FROM_CODE.md
       ↓
[3] RD06_Motion_draft.md
       ↓
[4] Compare against the drive vendor's documentation
   ├─ Verify parameters (rated speed, torque, etc.)
   ├─ Check soft limits and home position
   └─ Identify PLCopen FB usage
       ↓
[5] Match with the mechanical engineer
   ├─ Verify engineering unit (rpm/mm/s/deg/s)
   └─ Gear ratio + travel distance + max velocity
       ↓
[6] RD06_Motion.xlsx (approved)
```

---

## 4. Human Review Checklist

#### A. DriveType Accuracy
- [ ] Drive catalog number matches the AI output
- [ ] FBs used in the legacy code (e.g., MAJ, MAM, MC_MoveAbsolute) match the drive type

#### B. PLCopen FB Verification
- [ ] Only STANDARD MC_* names listed (vendor-specific in Notes)
- [ ] Unused FBs excluded (e.g., if the legacy code doesn't use MC_Halt, don't list it)

#### C. Engineering Unit
- [ ] Rotary axis: rpm or deg/s
- [ ] Linear axis: m/s or mm/s
- [ ] Position: mm/deg/m

#### D. Soft Limit and Home
- [ ] SoftLimit_Neg/Pos taken from the drive parameters (if available)
- [ ] HomeMethod taken from the actual code: LimitSwitch / IndexPulse / AbsEncoder
- [ ] HomePosition reflects the mechanical origin (may differ from 0)

#### E. Cross-Reference
- [ ] Motor_Tag exists in RD01 (output)
- [ ] Feedback_Tag exists in RD01 (input — encoder, current, etc.)
- [ ] DriveDB defined in RD02

---

## 5. Common Pitfalls

- ❌ **Treating a VFD as a Servo:** marking Servo when there's no encoder feedback
- ❌ **Calling vendor-specific FBs standard:** Tc2_MC2.MC_PowerEx is NOT MC_Power (note in Notes)
- ❌ **Reading TorqueLimit_pct from a program call:** should come from a drive parameter; program-runtime values vary
- ❌ **Confusing SoftLimit with hardware limit switches:** SoftLimit is software; hardware limit is separate
- ❌ **Skipping multi-axis sync:** gear/cam synchronization between axes must be noted
- ❌ **Wrong EngUnit:** writing mm/s for a rotary axis

---

## 6. Drive-Specific Notes

### 6.1 SINAMICS G120/S120
- Parameter p2000 (rated speed reference)
- Telegrams 1, 3, 105 carry different data
- Profidrive state-machine states must match RD05 Safety

### 6.2 Beckhoff TwinCAT NC PTP / NCI
- All info lives in the AXIS_REF struct
- nDeviceName + sAxisName
- Tc2_MC2 library FBs

### 6.3 Allen-Bradley Kinetix CIP Motion
- AXIS_CIP_DRIVE tag type
- MAJ/MAM/MSF AOIs (motion)
- ServoUpdate task (periodic motion task)

---

## 7. Gate 3 Checklist

- [ ] All axes listed (every motor + every axis)
- [ ] DriveType in the right category
- [ ] PLCopen FBs limited to the ones the code actually uses
- [ ] EngUnit appropriate for the machine
- [ ] HomeMethod correct
- [ ] Soft limits taken from the drive parameters
- [ ] Cross-reference (RD01/RD02) clean

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_06_MOTION.md`
- **AI prompt:** `PROMPT_EXTRACT_MOTION_FROM_CODE.md`
- **Standards:** PLCopen Motion Control v2.0, IEC 61800-7, IEC 61784-3

---

*v1.1.0 — Full English body (2026-05-23). Motion is the "muscle" of modern industry. Bad extraction = field downtime = customer loss.*
