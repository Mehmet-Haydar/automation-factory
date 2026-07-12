# RD06_Motion — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_06_MOTION.md`. Schema: `rd06_motion.schema.json`.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <Engineer Name>
filled_at: <YYYY-MM-DD>
status: <DRAFT | REVIEWED | APPROVED>
```

---

## Summary

- Total axes: __
- DriveType: VFD_Profidrive __ | Servo_EtherCAT __ | Stepper __
- PLCopen FB usage: __

---

## Axes

| AxisID | AxisName | DriveType | DriveModel | Motor_Tag | Feedback_Tag | MaxVelocity | MaxAcceleration | MaxDeceleration | EngUnit | TorqueLimit_pct | HomeMethod | HomePosition | SoftLimit_Neg | SoftLimit_Pos | DriveDB | PLCopenFBs | Notes | Status |
|--------|----------|-----------|------------|-----------|--------------|-------------|------------------|------------------|---------|-----------------|------------|--------------|----------------|----------------|---------|------------|-------|--------|
| AX001 | XAxis_Gantry | Servo_Profidrive | SINAMICS S120 | MOT_X_001 | ENC_X_001 | 5000 | 50000 | 50000 | mm/s | 80 | LimitSwitch | 0 | -100 | 2500 | DB_Drive_X | MC_Power,MC_Home,MC_MoveAbsolute,MC_Stop | Gantry X axis | Active |
| AX002 | YAxis_Gantry | Servo_Profidrive | SINAMICS S120 | MOT_Y_001 | ENC_Y_001 | 5000 | 50000 | 50000 | mm/s | 80 | LimitSwitch | 0 | -50 | 1500 | DB_Drive_Y | MC_Power,MC_Home,MC_MoveAbsolute,MC_Stop | Gantry Y axis | Active |
| AX003 | Spindle | VFD_Profidrive | SINAMICS G120 | MOT_SP_001 | | 8000 | 1000 | 1000 | rpm | 100 | None | | | | DB_Drive_SP | MC_Power,MC_MoveVelocity,MC_Stop | Spindle motor | Active |

---

## #UNKNOWNS

| Old drive | Reason |
|-----------|--------|
| | |

---

## Fill-in Notes

- **AxisID format:** `^AX\d{3}$`
- **DriveType enum:** VFD_Analog/VFD_Profidrive/Servo_Profidrive/Servo_EtherCAT/Stepper/Other
- **EngUnit enum:** rpm/m/s/mm/s/deg/s/mm/deg/m
- **HomeMethod enum:** LimitSwitch/IndexPulse/AbsEncoder/Mechanical/Manual/None
- **PLCopenFBs:** Only STANDARD MC_* names (put vendor-specific FBs in Notes)
- **Motor_Tag/Feedback_Tag:** RD01 IO reference (cross-ref)
- **Standards:** PLCopen Motion Control v2.0, IEC 61800-7

---

*Template v1.0.0 — RD06 Motion.*
