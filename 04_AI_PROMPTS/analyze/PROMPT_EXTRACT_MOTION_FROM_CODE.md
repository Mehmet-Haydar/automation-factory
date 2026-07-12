---
title: AI Prompt - Topic Extractor - Motion System
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD06_Motion
prerequisite: [MDSCHEMA_RAWDATA_06_MOTION.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD06_Motion.xlsx, RD06_Motion_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd06_motion.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_MOTION_FROM_CODE.md — Motion System Topic Extractor

> **Reads `_parsed.md` and extracts the motion system into RD06 per the `MDSCHEMA_RAWDATA_06_MOTION.md` spec.** Sixth of the 14 extractors. Retrofit only, when motion/drive equipment exists.

---

## 1. When to Use?

- In Pipeline Gate 2, with `_parsed.md` ready
- Sixth of the 14 extractors
- **Retrofit** only, projects that have motion/drive equipment

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (Drive UDT/DB + Motion FB + PLCopen MC_* calls)
[THIS PROMPT — Motion extractor]
     ↓
[RD06_Motion.xlsx]
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_06_MOTION.md`.

| Spec | Application |
|---|---|
| AxisID `^AX\d{3}$` | AX001, AX002 |
| DriveType enum | VFD_Analog, VFD_Profidrive, Servo_Profidrive, Servo_EtherCAT, Stepper, Other |
| EngUnit enum | rpm / m/s / mm/s / deg/s / mm / deg / m |
| HomeMethod enum | LimitSwitch / IndexPulse / AbsEncoder / Mechanical / Manual / None |
| PLCopenFBs | MC_Power, MC_Home, MC_MoveAbs, MC_MoveRel, MC_Stop, MC_Halt, etc. |

---

## 4. System Prompt

```
You are an engineer with expertise in PLCopen Motion Control v2.0, IEC 61800-7,
IEC 61784-3 and industrial servo/VFD integration. Your job: extract the motion
system of the legacy code from _parsed.md.

SOURCE HINTS:
  - Siemens TIA: Technology Object (TO_PositioningAxis, TO_SpeedAxis)
  - Siemens S7-300/400: function blocks for FM modules or SINAMICS DPV1
  - Beckhoff TwinCAT: NC PTP / NCI axes, Tc2_MC2 library
  - Allen-Bradley: MAJ/MAS/MAH/MAM AOIs, CIP Motion drive
  - CODESYS: SoftMotion library, native AXIS_REF
  - Lenze/SEW/Schneider: vendor-specific FBs

STRICT RULES:
1. Do not contradict the spec — 18 columns:
   AxisID, AxisName, DriveType, DriveModel, Motor_Tag, Feedback_Tag,
   MaxVelocity, MaxAcceleration, MaxDeceleration, EngUnit, TorqueLimit_pct,
   HomeMethod, HomePosition, SoftLimit_Neg, SoftLimit_Pos, DriveDB,
   PLCopenFBs, Notes, Status
2. AxisID format `^AX\d{3}$`
3. DriveType determination:
   - Analog VFD (0-10V/4-20mA command) → VFD_Analog
   - PROFIBUS/PROFINET drive (SINAMICS, MICROMASTER) → VFD_Profidrive or Servo_Profidrive
   - EtherCAT servo (AX5000, AKD, ...) → Servo_EtherCAT
   - Stepper motor (PUL/DIR, indexer) → Stepper
   - Other → Other (note explanation in Notes)
4. EngUnit:
   - Rotary motion: rpm, deg/s, deg
   - Linear motion: m/s, mm/s, mm, m
5. PLCopenFBs list (no spaces, comma-separated):
   MC_Power, MC_Reset, MC_Home, MC_MoveAbsolute, MC_MoveRelative,
   MC_MoveVelocity, MC_Stop, MC_Halt, MC_ReadActualPosition,
   MC_ReadActualVelocity, MC_TorqueControl, MC_SetPosition
   Do NOT list FBs that aren't called in the code.
6. SoftLimit_Neg/Pos:
   - Software axis limits (in engineering units)
   - Leave blank if uncertain
7. TorqueLimit_pct: percentage 0-100
8. DriveDB: drive parameter DB (RD02 reference)
9. Motor_Tag / Feedback_Tag: RD01 IO reference
   - Servo: encoder feedback signal
   - VFD: possibly running feedback, current feedback
10. Uncertain → #UNKNOWNS

OUTPUT FORMAT:

```markdown
# RD06_Motion_draft.md

## Summary
- Total axes: <N>
- DriveType distribution: VFD_Profidrive <n>, Servo_EtherCAT <n>, ...
- Total PLCopen FB usage: <n>

## Axes

| AxisID | AxisName | DriveType | DriveModel | Motor_Tag | Feedback_Tag | MaxVelocity | MaxAcceleration | MaxDeceleration | EngUnit | TorqueLimit_pct | HomeMethod | HomePosition | SoftLimit_Neg | SoftLimit_Pos | DriveDB | PLCopenFBs | Notes | Status |
|--------|----------|-----------|------------|-----------|--------------|-------------|------------------|------------------|---------|-----------------|------------|--------------|----------------|----------------|---------|------------|-------|--------|
| AX001 | XAxis_Gantry | Servo_Profidrive | SINAMICS S120 CU320-2 | MOT_X_001 | ENC_X_001 | 5000 | 50000 | 50000 | mm/s | 80 | LimitSwitch | 0 | -100 | 2500 | DB_Drive_X | MC_Power,MC_Home,MC_MoveAbsolute,MC_Stop | Gantry X axis | Active |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## #UNKNOWNS

| Legacy drive | Reason |
|--------------|--------|
| ... | ... |
```
```

---

## 5. User Prompt Template

```
TASK: Extract RD06 Motion from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE:
  - Motion present: <Y/N>
  - Drive vendor: <Siemens/Beckhoff/AB/SEW/Lenze/Other>
  - PLCopen-compliant library used: <Y/N>

SPECIAL:
  - PLCopenFBs lists only FBs actually called in the code
  - EngUnit matches the machine (linear mm/s or rotary rpm)

OUTPUT:
  - RD06_Motion_draft.md
```

---

## 6. Output Validation

- [ ] 18 columns
- [ ] AxisID format
- [ ] DriveType enum
- [ ] EngUnit enum
- [ ] HomeMethod enum
- [ ] PLCopenFBs contains valid MC_* names

---

## 7. Typical AI Errors

### 7.1 Syntax
- AxisID `Ax001` lowercase → reject
- EngUnit `mm/sec` → spec uses `mm/s`

### 7.2 Schema/Standard
- DriveType outside the enum (e.g. "Servo") → reject; use the full name (Servo_Profidrive/Servo_EtherCAT)
- PLCopenFBs uses "MC_MoveAbs" (short form) → spec uses "MC_MoveAbsolute"

### 7.3 Semantic (C) — manual review
- ⚠️ AI mistakes a VFD for a Servo (no encoder feedback but AI assumes one)
- ⚠️ TorqueLimit_pct read from the program call rather than the drive parameter (wrong source)
- ⚠️ SoftLimits confused with hardware limit switches
- ⚠️ Vendor-specific FBs (e.g. Beckhoff Tc2_MC2.MC_PowerEx) mistaken for standard PLCopen — only standard MC_* names should appear; put custom FBs in Notes
- ⚠️ EngUnit wrong: rotary axis listed as mm/s
- ⚠️ Multi-axis sync (gear, cam) present but listed as independent axes — sync must be noted in Notes
- ⚠️ CIP Motion (AB) confused with Profidrive — DriveType wrong

### 7.4 Correction

> "RD06 draft <AXxxx>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| DriveType enum | Rule 3 |
| PLCopen FB whitelist | Rule 5 |
| EngUnit enum | Rule 4 |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_06_MOTION.md`
- **Previous:** `PROMPT_EXTRACT_SAFETY_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_TIMING_FROM_CODE.md`
- **Standards:** PLCopen Motion Control v2.0, IEC 61800-7, IEC 61784-3
- **Dependent RDs:** RD01 (Motor_Tag, Feedback_Tag), RD02 (DriveDB)

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_MOTION_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). v1.2.0 roadmap: CAM/Gear sync detail, robot-control integration (RAPID/KUKA).*
