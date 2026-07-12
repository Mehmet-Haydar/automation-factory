---
title: Raw Data Schema #06 — Motion System
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_02_DATADICT.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_07_TIMING.md, PROMPT_EXTRACT_MOTION_FROM_CODE.md]
schema: RAWDATA
rd_number: 06
deliverable: [RD06_Motion.xlsx, RD06_Motion.md, rd06_motion.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [PLCopen Motion Control v2.0, IEC 61800-7, Siemens S120 Startdrive]
---

# MDSCHEMA_RAWDATA_06_MOTION.md — Motion System Specification

> **This file defines how the project's "06 — Motion System" raw data file should be structured.** Documents electric drives (VFD/Servo), axes, positioning and homing parameters. Based on the PLCopen Motion Control standard.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual motion-system parameter list (`RD06_Motion.xlsx` / `.md`) must conform to this spec.

- ✅ Each drive/axis identifier and type
- ✅ Motor parameters (max velocity, acceleration, torque limit)
- ✅ Encoder/feedback structure
- ✅ Homing method and reference position
- ✅ PLCopen Motion FB references (MC_MoveAbsolute, MC_Home, etc.)
- ✅ Drive DB and IO cross-references

**This file is NOT:**
- ❌ Drive parameter file (exported from the inverter/servo GUI — e.g., Siemens STARTER .dpv)
- ❌ Drive selection (that's mechanical/electrical design — hardware-selection stage)
- ❌ Standard motor ON/OFF control (that's RD01 IO List — DOL/Y-D start)
- ❌ Timer values (that's RD07 Timing)

**Scope:** RD06 covers applications where the drive receives a speed/position/torque reference (VFD analog output, PROFIdrive, servo control over Profinet fieldbus). A simple DOL motor goes only into RD01.

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Legacy drive parameter lists + PLC code (drive DBs) + drive communication addresses | AI (`PROMPT_EXTRACT_MOTION_FROM_CODE.md`) then human correction | `script_consistency_check.py` |
| **Greenfield** | Machine spec + mechanical design + motor data sheet | Human (mechanical engineer + automation engineer together) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** → **Gate 3** → **Gate 4** (GREEN).

---

## 3. Excel Column Definition (Required)

`RD06_Motion.xlsx` must contain the following columns **in this order**:

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `AxisID` | string | ✅ | `^AX\d{3}$` | Axis identifier (e.g., `AX001` X axis, `AX002` Y axis) |
| 2 | `AxisName` | string | ✅ | min 3 characters, EN | Short axis name (used in code generation) |
| 3 | `DriveType` | enum | ✅ | `VFD_Analog`, `VFD_Profidrive`, `Servo_Profidrive`, `Servo_EtherCAT`, `Stepper`, `Other` | Drive/communication type |
| 4 | `DriveModel` | string | ⚪ | (free) | Drive make and model (e.g., `Siemens G120`, `SEW Movidrive`) |
| 5 | `Motor_Tag` | string | ✅ | (RD01 Tag format) | Motor drive-output tag from RD01 (cross-reference) |
| 6 | `Feedback_Tag` | string | ⚪ | (RD01 Tag format) | Encoder/resolver feedback signal (RD01 AI/DI tag) |
| 7 | `MaxVelocity` | real | ✅ | >0 | Max velocity (unit depends on EngUnit) |
| 8 | `MaxAcceleration` | real | ✅ | >0 | Max acceleration |
| 9 | `MaxDeceleration` | real | ⚪ | >0 | Max deceleration (if blank, MaxAcceleration is used) |
| 10 | `EngUnit` | enum | ✅ | `rpm`, `m/s`, `mm/s`, `deg/s`, `mm`, `deg`, `m` | Velocity/position unit |
| 11 | `TorqueLimit_pct` | real | ⚪ | 0-200 | Torque limit (%) |
| 12 | `HomeMethod` | enum | ✅ | `LimitSwitch`, `IndexPulse`, `AbsEncoder`, `Mechanical`, `Manual`, `None` | Homing method |
| 13 | `HomePosition` | real | ⚪ | (free) | Reference position value (per EngUnit, usually 0.0) |
| 14 | `SoftLimit_Neg` | real | ⚪ | (free) | Negative software endpoint (EngUnit) |
| 15 | `SoftLimit_Pos` | real | ⚪ | (free) | Positive software endpoint (EngUnit) |
| 16 | `DriveDB` | string | ⚪ | (free) | Related drive instance DB (cross-reference to RD02 ParentBlock) |
| 17 | `PLCopenFBs` | string | ⚪ | (free — comma-separated) | PLCopen Motion Control FBs used |
| 18 | `Notes` | string | ⚪ | (free) | Special parameter, field note, safety note |
| 19 | `Status` | enum | ✅ | `Active`, `Inactive`, `Spare` | Renamed to English (2026-06-10); legacy Turkish literals (`Aktif`/`Pasif`/`Taslak`/`Yedek`) in existing projects remain readable by the tooling |

### 3.1 Column Descriptions (Detail)

**DriveType (3):**
- `VFD_Analog` → 0-10V or 4-20mA speed reference (legacy connection)
- `VFD_Profidrive` → PROFIdrive profile over Profibus/Profinet
- `Servo_Profidrive` → servo drive over PROFIdrive
- `Servo_EtherCAT` → EtherCAT real-time bus (Beckhoff, Yaskawa, etc.)
- `Stepper` → stepper motor (step/dir signal)

**MaxVelocity / MaxAcceleration (7-8):** Must be consistent with EngUnit. `rpm` for VFD, `mm/s` for a linear axis. AI writes the drive parameter value (e.g., P1082) directly.

**HomeMethod (12):**
- `LimitSwitch` → travel until limit switch is touched, then retract
- `IndexPulse` → travel until encoder index pulse
- `AbsEncoder` → absolute encoder — no homing required
- `Mechanical` → physical stop (small axes)
- `Manual` → operator positions manually; that position is set to 0
- `None` → no homing (continuously rotating axis, fan-like)

**PLCopenFBs (17):** IEC 61131-10 / PLCopen Motion Control v2.0 FBs. Examples: `MC_Power, MC_Home, MC_MoveAbsolute, MC_MoveVelocity, MC_Stop, MC_Reset`.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd06_motion.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD06 — Motion System",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["AxisID","AxisName","DriveType","Motor_Tag","MaxVelocity","MaxAcceleration","EngUnit","HomeMethod","Status"],
    "additionalProperties": false,
    "properties": {
      "AxisID":           { "type": "string", "pattern": "^AX\\d{3}$" },
      "AxisName":         { "type": "string", "minLength": 3 },
      "DriveType":        { "enum": ["VFD_Analog","VFD_Profidrive","Servo_Profidrive","Servo_EtherCAT","Stepper","Other"] },
      "DriveModel":       { "type": "string" },
      "Motor_Tag":        { "type": "string", "minLength": 1 },
      "Feedback_Tag":     { "type": "string" },
      "MaxVelocity":      { "type": "number", "exclusiveMinimum": 0 },
      "MaxAcceleration":  { "type": "number", "exclusiveMinimum": 0 },
      "MaxDeceleration":  { "type": "number", "exclusiveMinimum": 0 },
      "EngUnit":          { "enum": ["rpm","m/s","mm/s","deg/s","mm","deg","m"] },
      "TorqueLimit_pct":  { "type": "number", "minimum": 0, "maximum": 200 },
      "HomeMethod":       { "enum": ["LimitSwitch","IndexPulse","AbsEncoder","Mechanical","Manual","None"] },
      "HomePosition":     { "type": "number" },
      "SoftLimit_Neg":    { "type": "number" },
      "SoftLimit_Pos":    { "type": "number" },
      "DriveDB":          { "type": "string" },
      "PLCopenFBs":       { "type": "string" },
      "Notes":            { "type": "string" },
      "Status":           { "enum": ["Active","Inactive","Spare"] }
    }
  }
}
```

---

## 5. MD Output Format

`RD06_Motion.md` produced at Gate 4:

````markdown
---
title: RD06 — Motion System
project: <project_name>
generated: YYYY-MM-DD
source: RD06_Motion.xlsx
filter: Status=Active
total_axes: <N>
schema: RD06
---

# RD06 — Motion System

## Axis Summary

| AxisID | AxisName | DriveType | MaxVelocity | EngUnit | HomeMethod |
|--------|----------|-----------|-------------|---------|------------|
| AX001 | X_Axis | Servo_Profidrive | 500.0 | mm/s | LimitSwitch |
| ... | ... | ... | ... | ... | ... |

## Detail

### AX001 — X_Axis

- **Drive:** Siemens S120 — Servo_Profidrive
- **Motor Tag:** `MOT_XAXIS_001_DRIVE`
- **Feedback:** `SEN_XAXIS_001_ENC`
- **Homing:** LimitSwitch @ 0.0 mm
- **PLCopen FBs:** MC_Power, MC_Home, MC_MoveAbsolute, MC_Stop
````

---

## 6. AI Filling Instructions (Retrofit)

```
INPUT: _parsed.md Section 4 (drives UDT), Section 5 (drive instance DBs), Section 7 (motion FBs)
TASK:
  1. Locate the drive instance DBs (typically prefixed "DRIVE", "AXIS", "VFD", "SERVO")
  2. Assign AX001+ AxisID per drive
  3. Motor_Tag: find the related DO tag from RD01 (DRIVE_OUTPUT or Profidrive ENO)
  4. MaxVelocity/MaxAcceleration: derive from the drive DB limit parameters (P1082, P1120, etc.)
  5. EngUnit: derive from scaling blocks or comments
  6. HomeMethod: derive from the homing routine code (LimitSwitch if a limit switch is used)
  7. PLCopenFBs: list the PLCopen FBs that are called
  8. DriveModel: from HW config or comments
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: _input/brief.md + machine kinematics + motor data sheet
TASK:
  1. Define each motion axis (X/Y/Z/Rotation + conveyor/roller, etc.)
  2. DriveType: propose per application (position = Servo, speed = VFD)
  3. MaxVelocity/MaxAcceleration: from the mechanical design (safe limits)
  4. SoftLimit: derive from physical machine dimensions
  5. HomeMethod: absolute encoder is recommended (no risk of reference loss); LimitSwitch otherwise
  6. PLCopenFBs: propose the standard PLCopen set (Power/Home/MoveAbsolute/Stop/Reset)
  7. DriveDB: propose the instance DB name per PLCopen convention (DB_<AxisName>_Drive)
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **PLCopen Motion Control v2.0** | FB function blocks (MC_Power, MC_Home, etc.) — PLCopenFBs column |
| **IEC 61131-10** | IEC number of the PLCopen Motion Control standard |
| **IEC 61800-7** | Drive communication profile (incl. PROFIdrive) — DriveType enum |
| **Siemens S120 Startdrive** | Drive parameter numbers (P1082, P1120) — referenced in Notes |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- AxisID `AXIS001` (not AX prefix) → regex reject
- EngUnit `RPM` (uppercase; enum lists `rpm`) → enum reject
- MaxVelocity=0 → exclusiveMinimum reject

### 9.2 Schema/Standard (Category B) — Validator catches
- Motor_Tag blank → required-field reject
- TorqueLimit_pct = 250 → maximum reject (>200%)

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ AI confuses VFD_Analog with VFD_Profidrive — if the legacy drive uses a 4-20mA speed reference it's Analog; if it uses fieldbus PROFIdrive it's Profidrive; they require a different FB set
- ⚠️ MaxVelocity and MaxAcceleration in a unit inconsistent with EngUnit — wrote mm/s instead of rpm; scaling error in code generation
- ⚠️ HomeMethod=None but SoftLimit_Neg/Pos blank → without homing, software limits must protect the axis; safety risk
- ⚠️ PLCopenFBs list missing MC_Stop — MC_Stop mandatory on every axis (safety)
- ⚠️ AbsEncoder selected but Feedback_Tag blank → feedback signal not defined; missing piece in code generation

### 9.4 Correction Request Template

> "Error in RD06 row `<AxisID>`: <category> issue: <description>. Expected: <correct value>. Fix only that row."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD06_Motion.xlsx` blank template:
- 19 columns, header + 2 example rows (VFD axis / Servo axis)
- Data Validation: DriveType, EngUnit, HomeMethod, Status dropdowns
- Separate sheet: "PLCopenReference" — PLCopen v2.0 FB reference table

---

## 11. Related Files

- **Dependency:** `MDSCHEMA_RAWDATA_01_IO.md` (Motor_Tag, Feedback_Tag cross-reference)
- **Dependency:** `MDSCHEMA_RAWDATA_02_DATADICT.md` (DriveDB cross-reference)
- **Next spec:** `MDSCHEMA_RAWDATA_07_TIMING.md`
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_MOTION_FROM_CODE.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD06_Motion.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd06_motion.schema.json`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_06_MOTION.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Deliverable filenames updated to `RD06_Motion.xlsx/.md` to match actual project files. Status enum renamed to `Active/Inactive/Spare` (English, 2026-06-10 coordinated update; see RD02 spec §3.1). v1.2.0 roadmap: EtherCAT slave mapping, coordinated multi-axis motion (gantry) scenarios, CNC-like G-code interpretation.*
