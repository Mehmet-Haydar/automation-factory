---
title: Drives Configuration
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [MDSCHEMA_RAWDATA_06_MOTION.md]
status: ACTIVE
---

# DOMAIN_DRIVES_CONFIG.md — Drive/Servo Configuration Domain Standard

> The Factory's selection, configuration, and parameter reference for VFD and servo drive projects.

---

## 1. Drive Selection Matrix

| Application | Recommended Drive | DriveType (RD06) |
|-------------|-------------------|------------------|
| Low-power pump/fan | Lenze i510, SEW MoviTrac LTP-B | VFD_Analog |
| Standard production-line motor | SINAMICS G120, AB PowerFlex 525 | VFD_Profidrive |
| High-dynamic servo | SINAMICS S120, AB Kinetix 5700 | Servo_Profidrive |
| EtherCAT servo | Beckhoff AX5xxx, AKD | Servo_EtherCAT |
| Low-power stepper | Trinamic, Leadshine | Stepper |
| Multi-axis sync (CNC) | SINAMICS S210 + TIA Motion | Servo_Profidrive |

---

## 2. SINAMICS S120 Standard Parameter Set

```yaml
# General
p0010: 1          # Commissioning mode active
p2000: 3000       # Rated speed reference (rpm)
p2001: 17.5       # Rated torque (Nm)

# Encoder
p404: 2048        # Encoder pulses per revolution
p400: 1           # Encoder type (incremental)

# Control mode
p1300: 21         # Vector control with encoder (servo)
p1301: 0          # Speed control

# Limits
p1080: 0          # Minimum speed (rpm)
p1082: 3000       # Maximum speed (rpm)
p1520: 100        # Positive torque limit (%)
p1521: -100       # Negative torque limit (%)

# Ramps
p1120: 0.5        # Acceleration ramp (s)
p1121: 0.5        # Deceleration ramp (s)
p1135: 0.0        # Jerk (s) — smooth ramp

# Safety (if F-Drive)
p9501: 1          # STO enable
p9502: 1          # SS1 enable
p9550: 1.0        # SS1 stop time (s)
```

---

## 3. Allen-Bradley Kinetix 5700 Standard Set

```
General:
  Catalog: 2198-D050-ERS3
  Encoder: 2090-CSBM1DG-18AAxx (single-turn)
  Cable: 2090-CFBM7DD-CDAFxx

Motion Group:
  Update Period: 1 ms
  Coarse Update: 2 ms

Axis Configuration:
  Axis Type: Servo
  Control Mode: Position Loop
  Feedback Configuration: Motor Feedback

Drive Parameters:
  Velocity Loop Bandwidth: 200 Hz
  Position Loop Bandwidth: 30 Hz
  Torque/Force Loop Bandwidth: 1500 Hz
  Position Error Tolerance: 0.1 deg
```

---

## 4. Beckhoff TwinCAT NC PTP / AX5000

```
TwinCAT NC Configuration:
  Axis Type: Continuous (servo)
  Encoder:
    Type: Incremental EnDat
    Resolution: 2^16 = 65536 inc/rev
  
  Drive:
    Type: AX5103-0000
    Bus: EtherCAT
    Cycle: 1 ms (DC enabled)
  
  Limits:
    Soft Min: -100 mm
    Soft Max: 2500 mm
    Max Velocity: 5000 mm/s
    Max Acceleration: 50000 mm/s²
    Max Deceleration: 50000 mm/s²

PLC FB (Tc2_MC2):
  MC_Power, MC_Home, MC_MoveAbsolute, MC_Stop
```

---

## 5. PLCopen Motion FB Standard Usage

```scl
// 1. Power ON
"MC_Power_X"(
    Axis := "AX_X",
    Enable := "DB_Drive".bEnableX,
    Status := "DB_Drive".bPoweredX,
    Error := "DB_Drive".bErrorX
);

// 2. Homing
"MC_Home_X"(
    Axis := "AX_X",
    Execute := "DB_Drive".bHomeReqX AND NOT "DB_Drive".bHomedX,
    Position := 0.0,
    HomingMode := mcDirectAbsoluteMode,
    Done := "DB_Drive".bHomedX
);

// 3. Move Absolute
"MC_MoveAbsolute_X"(
    Axis := "AX_X",
    Execute := "DB_Drive".bMoveReqX,
    Position := "DB_Recipe".rTargetPositionX,
    Velocity := 1000.0,
    Acceleration := 5000.0,
    Deceleration := 5000.0,
    Done := "DB_Drive".bMoveDoneX,
    Error := "DB_Drive".bMoveErrorX
);

// 4. Stop
"MC_Stop_X"(
    Axis := "AX_X",
    Execute := "DB_Drive".bStopReqX OR "DB_Safety".bEStopActive,
    Deceleration := 10000.0,
    Done := "DB_Drive".bStoppedX
);
```

---

## 6. Drive Fault-Code Mapping

### 6.1 SINAMICS Fault Code Examples

| Fault | Meaning | Action |
|-------|---------|--------|
| F07900 | Motor stuck | Check mechanical |
| F07901 | Motor overspeed | Check setpoint |
| F07452 | Velocity error | Loop tuning |
| F08501 | DC link overvoltage | Check braking resistor |
| F30001 | Power module overcurrent | Check load |

Mapping into the RD08 alarm table:
```
ALM0100 (Critical, Priority 10):
  TriggerTag: DB_Drive.iFaultCode
  TriggerCondition: DB_Drive.iFaultCode IN [F07900, F30001]
  RecommendedAction: Check mechanical load + braking resistor
```

---

## 7. Multi-Axis Synchronisation

### 7.1 Gear (Electronic Gearbox)

```scl
"MC_GearIn_Slave"(
    Master := "AX_Master",
    Slave := "AX_Slave",
    RatioNumerator := 1,
    RatioDenominator := 1,
    Acceleration := 5000.0,
    Execute := "DB_Sync".bGearEngage,
    InGear := "DB_Sync".bGearActive
);
```

### 7.2 CAM (Electronic Cam)

```scl
"MC_CamIn_Slave"(
    Master := "AX_Master",
    Slave := "AX_Slave",
    CamTableID := 1,    // Loaded with MC_CamTableSelect
    StartMode := mcAbsolute,
    Execute := "DB_Sync".bCamEngage,
    InSync := "DB_Sync".bCamActive
);
```

EtherCAT Distributed Clocks (DC) mandatory — multi-axis jitter ≤ 1 µs.

---

## 8. Safety Integration

Drive STO (Safe Torque Off) integrated with the F-PLC:

```yaml
SINAMICS_S120_STO:
  hardware: F-DI signal direct to the drive (terminal X121.1)
  parameter: p9501=1 (STO enabled)
  response_time: < 50 ms
  
SINAMICS_S120_SS1 (Safe Stop 1):
  parameter: p9502=1, p9550 = 1.0 s (stop time)
  process: ramp down, then STO

SINAMICS_S120_SLS (Safely Limited Speed):
  parameter: p9531=1
  speed_limit: 100 rpm (example)
```

---

## 9. AUTOMATION_FACTORY Application

- **AI prompt (extraction):** `PROMPT_EXTRACT_MOTION_FROM_CODE.md`
- **RD spec:** `MDSCHEMA_RAWDATA_06_MOTION.md`
- **Retrofit guide:** `RETROFIT_EXTRACT_MOTION.md`
- **Greenfield guide:** `GREENFIELD_DESIGN_MOTION.md`
- **Vendor quirks:** `KB_VENDOR_QUIRKS.md` (Lenze/SEW/Schneider notes)

---

## 10. Standards

- **PLCopen Motion Control v2.0** Standard FB definitions
- **IEC 61800-7-1..304** Adjustable speed electrical power drive systems
- **IEC 61784-3** Functional safety fieldbuses
- **NEMA MG-1** Motors and Generators

---

*v1.1.0 — Full English body (2026-05-23). Drive domain standard. Vendor parameter references will be updated over the years.*
