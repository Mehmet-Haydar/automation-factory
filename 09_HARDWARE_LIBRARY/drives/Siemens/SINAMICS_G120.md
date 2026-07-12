---
title: Siemens SINAMICS G120 — AC Drive
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
---

# Siemens SINAMICS G120 — AC Drive

## metadata
```yaml
schema_version: "1.0"
device_id: "SIEMENS_SINAMICS_G120"
vendor: "Siemens AG"
model: "SINAMICS G120 (PM240-2 + CU250S-2 / CU240E-2)"
category: "drives"
subcategory: "ac_drive"
part_number: "6SL3210-1PE2x-xxx1 (PM240-2) / 6SL3246-0BA22-1PA0 (CU250S-2 PN)"
datasheet_ref: "Siemens SINAMICS G120 Operating Instructions (A5E44751205A)"
library_path: "drives/Siemens/SINAMICS_G120.md"
last_verified: "2026-01"
```

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | Siemens SINAMICS G120 Modular Frequency Converter |
| Category | AC Drive (Frequency Inverter) |
| Power Module | PM240-2: 0.37 kW – 250 kW (3 × 380–480 V AC) |
| Supply Voltage | 3 × 380–480 V AC, 47–63 Hz |
| Output Voltage | 3 × 0–Vinput, 0–650 Hz (vector mode) |
| Control Unit | CU250S-2 PN (PROFINET + Safety) / CU240E-2 PN (standard PN) |
| Protection Class | IP20 (standard), IP55 (external enclosure optional) |
| Certifications | CE, UL, cUL, C-Tick |
| Operating Temperature | -10°C … +50°C |

## 2. Communication Interfaces

| Interface | Protocol | Telegram / Format | Notes |
|-----------|----------|-------------------|-------|
| PROFINET IRT (CU250S-2 PN / CU240E-2 PN) | PROFIdrive | Telegram 1, 20, 350, 352 | Built-in (no external card needed) |
| PROFIBUS DP (CU240E-2 DP) | PROFIdrive | PPO1–PPO5 | Optional card |
| EtherNet/IP (CU240E-2 F PN) | Drive Profile | CIP Motion | Optional |
| USB (Service) | STARTER/SINAMICS Startdrive | — | PC tool |

## 3. PROFINET Configuration (for S7-1500)

```
GSDML File:    GSDML-V2.35-Siemens-Sinamics_G120-20220601.xml
               (Siemens Industry Mall or support.industry.siemens.com)
Device Family: SINAMICS G120
DAP Module:    Control Unit CU250S-2 PN (6SL3246-0BA22-1PA0)
TIA Portal:    Drive configurator: SINAMICS Startdrive (TIA V14+)
```

### IO Address (Telegram 1 — PZD-2/2)
```
Input  (PLC ← Drive): 4 byte — ZSW1 (2B) + HIW (2B)
Output (PLC → Drive): 4 byte — STW1 (2B) + HSW (2B)
```

### IO Address (Telegram 350 — Safety Integrated)
```
Input  (PLC ← Drive): 12 byte — ZSW1 + HIW + ZSW2 + MIST_A + MIST_B
Output (PLC → Drive): 8 byte  — STW1 + HSW + STW2
```

## 4. Control Words (PROFIdrive Telegram 1)

### STW1 — Control Word (PLC → Drive)
| Bit | Name | 0 = | 1 = |
|-----|------|-----|-----|
| 0 | ON/OFF1 | OFF1 (stop via ramp) | Ready to run |
| 1 | OFF2 | Coast to stop (coasting) | — |
| 2 | OFF3 | Quick stop | — |
| 3 | ENABLE_OPERATION | Inhibit | Enable |
| 4 | RAMP_GEN_ENABLE | Stop | Enable |
| 5 | RAMP_GEN_FREEZE | Freeze | Release |
| 6 | SETPOINT_ENABLE | SP = 0 | SP enabled |
| 7 | FAULT_RESET | — | Reset fault (rising edge) |
| 8 | JOG_1 | — | Jog speed 1 |
| 9 | JOG_2 | — | Jog speed 2 |
| 10 | REMOTE_CONTROL | Local | Remote (PROFINET) |
| 11 | SETPOINT_INV | Normal | Reverse direction |

### ZSW1 — Status Word (Drive → PLC)
| Bit | Name | Description |
|-----|------|-------------|
| 0 | READY_TO_SWITCH_ON | Ready to switch on |
| 1 | READY | Ready for operation |
| 2 | OPERATION_ENABLED | Running |
| 3 | FAULT | Fault (see code r0947) |
| 4 | OFF2_ACTIVE | Coast-stop active |
| 5 | OFF3_ACTIVE | Quick-stop active |
| 6 | SWITCH_ON_INHIBIT | Inhibited |
| 7 | ALARM | Warning (see code r2110) |
| 8 | SPEED_DEVIATION_OK | Speed within tolerance |
| 9 | REMOTE_CONTROL | Remote control active |
| 10 | ABOVE_FREQ | Frequency > threshold (p2141) |
| 11 | ALARM_2 | Additional alarm |
| 12 | CURRENT_LIMIT | At current limit |

### STW2 / ZSW2 (Telegram 350 — Safety)
| Bit | Name | Description |
|-----|------|-------------|
| 0–7 | S_STW1 | PROFIsafe safety control words |
| 8–15 | S_ZSW1 | PROFIsafe safety status words |

## 5. Parameters (Critical Settings)

| Parameter | No | Factory Value | Typical Setting | Description |
|-----------|-----|---------------|-----------------|-------------|
| Command source | p0700 | 2 | 6 | 6 = PROFINET |
| Setpoint source | p1000 | 2 | 6 | 6 = PROFINET |
| Max speed | p1082 | 1500 rpm | Per motor | rpm |
| Min speed | p1080 | 0 rpm | Per project | rpm |
| Acceleration ramp | p1120 | 10 s | Per project | s |
| Deceleration ramp | p1121 | 10 s | Per project | s |
| Motor rated current | p0305 | — | Motor nameplate | A |
| Motor rated voltage | p0304 | 400 V | Motor nameplate | V |
| Motor rated frequency | p0310 | 50 Hz | Motor nameplate | Hz |
| Motor rated speed | p0311 | 1395 rpm | Motor nameplate | rpm |
| Motor rated power | p0307 | — | Motor nameplate | kW |
| Fault response | p2100 | — | Per project | Fault-code response table |
| Telegram selection | p0922 | 1 | 1 (or 350) | 350 = Safety Integrated |

## 6. TIA Portal SCL Integration Template

```scl
// Siemens SINAMICS G120 — PROFIdrive Telegram 1 control
// The Siemens drive can also be used with DriveLib (LDrv_RunDrive)
// The code below shows manual (raw PZD) control

// ------------------------------------------------------------------
// STATUS READ (Drive → PLC)
// ------------------------------------------------------------------
#drv_zsw1      := #io_zsw1;
#drv_hiw       := #io_hiw;

#drv_ready          := #drv_zsw1.1;
#drv_running        := #drv_zsw1.2;
#drv_fault          := #drv_zsw1.3;
#drv_inhibit        := #drv_zsw1.6;
#drv_alarm          := #drv_zsw1.7;
#drv_speed_ok       := #drv_zsw1.8;
#drv_remote         := #drv_zsw1.9;

// Actual speed (rpm): HIW normalized — 0x4000 (16384) = p1082 (max speed)
#drv_speed_rpm := REAL_TO_INT(
    INT_TO_REAL(#drv_hiw) / 16384.0 * INT_TO_REAL(#cfg_max_rpm)
);

// ------------------------------------------------------------------
// CONTROL WRITE (PLC → Drive)
// ------------------------------------------------------------------
#drv_stw1 := WORD#16#047E;    // Initial: OFF1=0, others safe
                               // Bit 1,2,3,4,5,6 = 1 (standard mask)

IF #cmd_on THEN
    #drv_stw1 := WORD#16#047F;  // ON/OFF1 = 1
END_IF;

IF #cmd_fault_reset THEN
    #drv_stw1.7 := TRUE;
END_IF;

IF #cmd_reverse THEN
    #drv_stw1.11 := TRUE;
END_IF;

// Speed setpoint: 16384 = p1082 (max speed)
IF #cmd_speed_rpm > 0 AND #cfg_max_rpm > 0 THEN
    #drv_hsw := REAL_TO_INT(
        INT_TO_REAL(ABS(#cmd_speed_rpm)) / INT_TO_REAL(#cfg_max_rpm) * 16384.0
    );
ELSE
    #drv_hsw := INT#0;
END_IF;

// Write
#io_stw1 := #drv_stw1;
#io_hsw  := #drv_hsw;
```

### TIA Portal DriveLib Alternative
```scl
// If you use Siemens DriveLib:
// Library: "Drives" → LDrv_RunDrive (FB)
// This FB handles all PROFIdrive Telegram 1 control automatically
// Parameters: Enable, SpeedSetpoint, FaultReset, Direction
```

## 7. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| A7015 (PROFINET connection loss) | Cable or IP | STEP 7 online → IE diagnostics |
| F07801 (Speed limit exceeded) | p1082 wrong | Set p1082 per the motor nameplate |
| Bit 6 SWITCH_ON_INHIBIT | Wrong reset sequence after fault | STW1 = 16#047E → 16#047F |
| No SINAMICS Startdrive connection | IP address | TIA Portal → Online → Extended Download |
| p0700 factory = 2 | Responds to analog command | Change p0700 = 6 (PROFINET) |

## 8. Notes

- **Safety Integrated (STO/SS1/SLS):** The CU250S-2 PN version has Safety integrated; PROFIsafe Telegram 350 is used with an F-PLC. There is also a hardware STO input (terminal DI4/DI5).
- **Startdrive:** The Startdrive add-in within TIA Portal is used for parameters — STARTER does not require a separate tool.
- **Encoder:** The CU250S-2 has an HTL/TTL encoder input; used for closed-loop speed control.
- **TIA DriveLib:** The LDrv_RunDrive FB from Siemens' own "Drives" library works directly with this drive — library download: support.industry.siemens.com (Entry 109477430).
- **BOP-2 panel:** Optional for manual jog and parameter setting.
