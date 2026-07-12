---
title: SEW-Eurodrive MoviDrive B — AC Drive
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
---

# SEW-Eurodrive MoviDrive B — AC Drive

## metadata
```yaml
schema_version: "1.0"
device_id: "SEW_MOVIDRIVE_B"
vendor: "SEW-Eurodrive"
model: "MoviDrive B (MDF.../MDX...)"
category: "drives"
subcategory: "ac_drive"
part_number: "MDF...-503-4-1T / MDX...-503-4-1T"
datasheet_ref: "SEW-Eurodrive System Manual MoviDrive B (Document No: 11271313)"
library_path: "drives/SEW/MoviDrive_B.md"
last_verified: "2026-01"
```

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | SEW-Eurodrive MoviDrive B Frequency Inverter |
| Category | AC Drive (Frequency Inverter) |
| Power Range | 0.37 kW – 160 kW (3-phase) |
| Supply Voltage | 3 × 380–500 V AC, 50/60 Hz |
| Output Voltage | 3 × 0–Vinput, 0–300 Hz |
| Control Voltage | 24 V DC (external supply) |
| Protection Class | IP20 (control unit), IP54/IP55 (optional enclosure) |
| Certifications | CE, UL, cUL, CCC |
| Operating Temperature | -10°C … +40°C (derating above 40°C) |
| Storage Temperature | -25°C … +70°C |

## 2. Communication Interfaces

| Interface | Protocol | Telegram / Format | Notes |
|-----------|----------|-------------------|-------|
| PROFINET IRT (DFE33B option) | PROFIdrive profile | Telegram 1 (PZD-2/2), Telegram 20 (extended) | GSDML required |
| PROFIBUS DP (DFP21B option) | PROFIdrive | PPO1 (PKW+PZD-2) | DP address via DIP switch |
| USB (local programming) | MoviTools protocol | — | PC tool: MOVITOOLS MotionStudio |
| RS-485 (SBus) | SEW SBus | — | Optional multi-axis |

## 3. PROFINET Configuration (for S7-1500)

```
GSDML File:    GSDML-V2.35-SEW-MOVIDRIVE_B-20210901.xml
               (download from the SEW website: sew-eurodrive.de → Downloads → GSDML)
Device Family: SEW-MOVIDRIVE_B
DAP Module:    DFE33B (Dual-Port Ethernet)
Default IP:    Assigned per project (DHCP or static)
```

### IO Address (Telegram 1 — PZD-2/2)
```
Input  (PLC ← Drive): 4 byte — ZSW1 (Status Word) + HIW (Actual Speed)
Output (PLC → Drive): 4 byte — STW1 (Control Word) + HSW (Speed Setpoint)
```

### IO Address (Telegram 20 — extended)
```
Input  (PLC ← Drive): 12 byte
Output (PLC → Drive): 8 byte
```

## 4. Control Words (PROFIdrive Telegram 1)

### STW1 — Control Word (PLC → Drive)
| Bit | Name | 0 = | 1 = |
|-----|------|-----|-----|
| 0 | ON/OFF1 | OFF1 (stop via ramp) | Ready to run |
| 1 | OFF2 | Coast to stop (coasting) | None |
| 2 | OFF3 | Quick stop (OFF3 ramp) | None |
| 3 | ENABLE_OPERATION | Inhibit operation | Enable operation |
| 4 | RAMP_GEN_ENABLE | Stop ramp generator | Enable |
| 5 | RAMP_GEN_FREEZE | Freeze ramp output | Release |
| 6 | SETPOINT_ENABLE | Setpoint = 0 | Setpoint active |
| 7 | FAULT_RESET | — | Reset fault (0→1 rising edge) |
| 8 | JOG_1 | No Jog 1 | Jog speed 1 |
| 9 | JOG_2 | No Jog 2 | Jog speed 2 |
| 10 | REMOTE_CONTROL | Local control | PROFINET remote control |
| 11 | SETPOINT_INV | Normal direction | Reverse direction |
| 15 | RESERVED | — | — |

### ZSW1 — Status Word (Drive → PLC)
| Bit | Name | Description |
|-----|------|-------------|
| 0 | READY_TO_SWITCH_ON | Main voltage OK, logic ready |
| 1 | READY | ON/OFF1=1 command received |
| 2 | OPERATION_ENABLED | Motor actively running |
| 3 | FAULT | Fault present — show alarm on HMI |
| 4 | OFF2_ACTIVE | Coast-stop active |
| 5 | OFF3_ACTIVE | Quick-stop active |
| 6 | SWITCH_ON_INHIBIT | OFF2/OFF3 awaited after fault |
| 7 | ALARM | Warning (drive does not stop) |
| 8 | SETPOINT_REACHED | Target speed reached |
| 9 | REMOTE_CONTROL | PROFINET control active |
| 11 | REVERSE | Running in reverse |

### HIW — Actual Speed (Drive → PLC, INT)
```
16384 = Max frequency (the maximum frequency in P302)
Formula: rpm = HIW * max_rpm / 16384
```

### HSW — Speed Setpoint (PLC → Drive, INT)
```
16384 = Max frequency (P302)
Formula: HSW = INT(speed_rpm * 16384 / max_rpm)
Negative value = reverse direction
```

## 5. Parameters (Critical Settings)

| Parameter | No | Factory Value | Typical Setting | Description |
|-----------|-----|---------------|-----------------|-------------|
| Control mode | P700 | 0 | 3 | 3 = PROFINET/PROFIBUS remote control |
| Max frequency | P302 | 50 Hz | 50–60 Hz | Reference for HIW/HSW normalization |
| Acceleration ramp | P130 | 5 s | Per project | 0…650 s (0–max frequency) |
| Deceleration ramp | P131 | 5 s | Per project | 0…650 s |
| Motor rated current | P160 | From motor nameplate | Motor nameplate value | A |
| Motor rated voltage | P161 | 230/400 V | Motor nameplate value | V |
| Motor rated frequency | P162 | 50 Hz | Motor nameplate value | Hz |
| Motor rated speed | P163 | 1395 rpm | Motor nameplate value | rpm |
| Motor power | P164 | From motor nameplate | Motor nameplate value | kW |
| Fault response | P834 | 1 | 1 | 1 = Auto reset when fault clears |

## 6. TIA Portal SCL Integration Template

```scl
// SEW MoviDrive B — PROFIdrive Telegram 1 control
// %IW[input_addr] = ZSW1, %IW[input_addr+2] = HIW
// %QW[output_addr] = STW1, %QW[output_addr+2] = HSW
// Addresses come from the TIA Portal PROFINET IO configuration

// ------------------------------------------------------------------
// STATUS READ (Drive → PLC)
// ------------------------------------------------------------------
#drv_zsw1       := #io_zsw1;           // Status Word (WORD)
#drv_speed_act  := #io_hiw;            // Actual speed (INT, normalized)

// Bit extraction
#drv_ready          := #drv_zsw1.1;   // Ready
#drv_running        := #drv_zsw1.2;   // Running
#drv_fault          := #drv_zsw1.3;   // Fault
#drv_alarm          := #drv_zsw1.7;   // Warning
#drv_setpoint_ok    := #drv_zsw1.8;   // Target speed reached
#drv_remote         := #drv_zsw1.9;   // Remote control active

// Actual speed calculation (rpm)
// max_rpm: from P163 (motor rated speed), HIW normalized: 16384 = max
#drv_speed_rpm := REAL_TO_INT(
    INT_TO_REAL(#drv_speed_act) / 16384.0 * INT_TO_REAL(#cfg_max_rpm)
);

// ------------------------------------------------------------------
// CONTROL WRITE (PLC → Drive)
// ------------------------------------------------------------------
#drv_stw1 := WORD#0;

// Basic bit settings
#drv_stw1.0 := #cmd_on;              // ON/OFF1
#drv_stw1.1 := TRUE;                 // OFF2 none (keep active)
#drv_stw1.2 := TRUE;                 // OFF3 none (keep active)
#drv_stw1.3 := #cmd_enable;          // Enable Operation
#drv_stw1.4 := TRUE;                 // Ramp generator enabled
#drv_stw1.5 := TRUE;                 // Ramp output released
#drv_stw1.6 := #cmd_setpoint_valid;  // Setpoint valid
#drv_stw1.7 := #cmd_fault_reset;     // Fault reset (rising edge)
#drv_stw1.10 := TRUE;                // Remote (PROFINET)
#drv_stw1.11 := #cmd_reverse;        // Reverse direction

// Speed setpoint calculation
#drv_hsw := REAL_TO_INT(
    INT_TO_REAL(#cmd_speed_rpm) / INT_TO_REAL(#cfg_max_rpm) * 16384.0
);
IF #cmd_reverse THEN
    #drv_hsw := -#drv_hsw;
END_IF;

// Write to IO
#io_stw1 := #drv_stw1;
#io_hsw  := #drv_hsw;
```

## 7. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| F-07 (PROFINET connection loss) | IP address conflict or cable | Check the IO device in TIA Portal, ping it |
| F-10 (Load too high) | Motor overloaded | Check the motor and load sizing |
| Bit 6 SWITCH_ON_INHIBIT = 1 | Correct reset sequence not done after fault | STW1.7 → 0, then 1 (rising edge) → STW1.0..3 active |
| PROFINET IO fault | GSDML mismatch | Download the current GSDML from the SEW site |
| P700 ≠ 3 | Left at factory default | Set P700 = 3 with MoviTools |

## 8. Notes

- **Safety (STO/SS1):** The MoviDrive B Safety version (MDX...F) requires an F-module add-on; STO is activated via PROFIsafe or hardwired 24V. The standard model has a hardware STO input (terminal X17).
- **Jog:** Done with STW1 bit 8/9; no rising edge expected, continuous level.
- **Multimotor:** Multiple drives can be connected to the same PROFINET ring (MRP supported).
- **TIA V18+ recommended:** Use GSDML V2.35+ for the DFE33B card.
- **MoviLink protocol:** Use MOVITOOLS MotionStudio to read/write parameters over USB/RS-485.
