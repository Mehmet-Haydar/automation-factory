---
title: Greenfield Motion System Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD06_Motion
prerequisite: [MDSCHEMA_RAWDATA_06_MOTION.md]
---

# GREENFIELD_DESIGN_MOTION.md — Motion System Design Guide

> **Goal:** design the motion system of a greenfield project with PLCopen Motion Control v2.0 discipline. Drive selection + parameters + PLC integration.

---

## 1. Prerequisites

- [ ] Mechanical design ready (motor count + kinematics)
- [ ] Performance requirements (max velocity, acceleration, accuracy)
- [ ] Environmental conditions (temperature, IP rating, EMC)
- [ ] Customer drive-brand preference (if any)

---

## 2. Drive-Type Selection Matrix

| Application | Recommended DriveType | Example Drive |
|-------------|------------------------|---------------|
| Low-performance pump/fan | VFD_Analog | Lenze i510, SEW MoviTrac LTP-B |
| Standard production-line motor | VFD_Profidrive | SINAMICS G120, AB PowerFlex 525 |
| High-dynamic servo (CNC, robotics) | Servo_EtherCAT | Beckhoff AX5xxx, AB Kinetix 5700 |
| High-dynamic (PROFINET) | Servo_Profidrive | SINAMICS S120, S210 |
| Low-power step | Stepper | Trinamic, Leadshine |
| High-precision sync (printing, paper) | Servo_EtherCAT + Tc2_MC2 | Beckhoff (Tc2_MC2 CAM/Gear) |

---

## 3. Design Steps

### 3.1 Step 1 — Axis Inventory

For every axis:
- AxisID (AX001..)
- Linear/Rotary
- Motor torque/power
- Max velocity (engineering units)
- Acceleration profile
- Positioning accuracy (±mm/±°)

### 3.2 Step 2 — Drive Selection

**Decision matrix:**

| Factor | Considerations |
|--------|----------------|
| Performance | Velocity-loop bandwidth, position-loop bandwidth |
| Precision | Encoder resolution, linear/rotary |
| Safety | STO, SS1, SS2, SLS required → Safety-rated drive |
| Network | PROFINET/EtherCAT/CIP Motion |
| Customer | Brand preference, spare-parts availability |

### 3.3 Step 3 — PLCopen FB Inventory

Which of the standard MC_* FBs will be used:

**Basic (per axis):**
- `MC_Power` — enable/disable
- `MC_Reset` — reset
- `MC_Home` — homing
- `MC_Stop` — controlled stop

**Positioning:**
- `MC_MoveAbsolute` — absolute position
- `MC_MoveRelative` — relative position
- `MC_MoveAdditive` — additive position

**Velocity:**
- `MC_MoveVelocity` — continuous motion
- `MC_Halt` — slow stop

**Torque:**
- `MC_TorqueControl` — torque mode

**Diagnostic:**
- `MC_ReadActualPosition`
- `MC_ReadActualVelocity`
- `MC_ReadStatus`

### 3.4 Step 4 — Drive Parameters

Typical parameters from the drive vendor's documentation:

```yaml
SINAMICS S120 example:
  rated_power_kW: 5.5
  rated_speed_rpm: 3000
  max_speed_rpm: 4500
  rated_torque_Nm: 17.5
  
  encoder:
    type: incremental
    resolution_ppr: 2048
  
  control:
    type: vector_with_encoder
    ramp_up_time_s: 0.5
    ramp_down_time_s: 0.5
  
  limits:
    torque_limit_pct: 100
    soft_limit_neg_mm: -10
    soft_limit_pos_mm: 2500
  
  safety:
    sto_enabled: true
    ss1_time_s: 1.0
```

### 3.5 Step 5 — Naming and Tag Design

```
Motor:
  MOT_X_001         (X-axis motor)
  MOT_Y_001         (Y-axis motor)
  MOT_SP_001        (Spindle motor)

Feedback:
  ENC_X_001         (X-axis encoder)
  ENC_Y_001         (Y-axis encoder)

DB:
  DB_Drive_X        (X drive instance DB)
  DB_Drive_Y        (Y drive instance DB)

FB Instance:
  FB_Axis_X (gAxisX instance)
  FB_Axis_Y (gAxisY instance)
```

---

## 4. Multi-Axis Synchronisation

If CAM/Gear is required:
- `MC_GearIn` — gear (proportional coupling)
- `MC_CamIn` — CAM (curve coupling)
- `MC_GearOut` / `MC_CamOut` — decouple

For sync precision, EtherCAT Distributed Clocks (DC) may be mandatory.

---

## 5. Validation (FAT/SAT)

- [ ] Homing successful for every axis
- [ ] Soft limits correctly placed
- [ ] Max-velocity test (free motion)
- [ ] Acceleration-profile test
- [ ] STO test (if any) — response-time measurement
- [ ] Multi-axis sync precision test (if any)

---

## 6. Common Design Pitfalls

- ❌ **Over-spec drive selection:** picking a servo for a pump multiplies cost by ~5x
- ❌ **Insufficient encoder selection:** 1024 ppr is not enough for 0.01° precision
- ❌ **Skipping STO:** modern machines require Safety-rated drives
- ❌ **Skipping EtherCAT DC sync:** if multi-axis sync is required, jitter problems appear without DC
- ❌ **Locking into a vendor-specific FB:** if the drive changes, the code is rewritten
- ❌ **Soft limit equals hardware limit:** the soft limit must engage before the hardware limit

---

## 7. Checklist

- [ ] Axis inventory complete
- [ ] Drive catalogue numbers selected
- [ ] PLCopen FB inventory chosen
- [ ] Drive parameters extracted (from the datasheet)
- [ ] Naming convention applied
- [ ] Multi-axis sync (if any) designed
- [ ] FAT test plan prepared

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_06_MOTION.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_MOTION.md`
- **Standards:** PLCopen Motion Control v2.0, IEC 61800-7

---

*v1.1.0 — Full English body (2026-05-23). Motion = the machine's dance. PLCopen discipline = the code stays the same even when the drive changes.*
