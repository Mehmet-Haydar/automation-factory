---
title: _SCHEMA_DEVICE.md — Device MD Template (v1.0)
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
---

# _SCHEMA_DEVICE.md — Device MD Template (v1.0)

This template defines the standard structure to be used for every device added to the
AUTOMATION_FACTORY hardware library.

**Important:** The AI reads these MD files to generate SCL code.
Do not leave fields empty, do not use placeholders — write real values.

---

```markdown
# [VENDOR] [MODEL] — [CATEGORY]

## metadata
```yaml
schema_version: "1.0"
device_id: "[VENDOR_ABBREV]_[MODEL_ABBREV]"        # e.g.: SEW_MOVIDRIVE_B
vendor: "[Manufacturer name]"                       # e.g.: SEW-Eurodrive
model: "[Model name]"                               # e.g.: MDF...-503-4-1T
category: "[drives|io_modules|sensors|valves|hmi]"
subcategory: "[ac_drive|servo|di_module|do_module|ai_module|...]"
part_number: "[Order number]"                       # e.g.: 8270285.01
datasheet_ref: "[Document name or URL]"
library_path: "drives/SEW/MoviDrive_B.md"
last_verified: "2026-01"
```

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | [Product's full commercial name] |
| Category | [AC Drive / Servo Amplifier / DI Module / ...] |
| Power Range | [e.g.: 0.37 kW – 315 kW] |
| Supply | [e.g.: 3 × 400 V AC, 50/60 Hz] |
| Output | [e.g.: 3 × 0..400 V AC, 0..550 Hz] |
| Protection Class | [e.g.: IP20 (control), IP55 (optional)] |
| Certifications | [CE, UL, cUL, ...] |

## 2. Communication Interfaces

| Interface | Protocol | Telegram / Data Length | Notes |
|-----------|----------|------------------------|-------|
| [PROFINET IRT / PROFIBUS DP / EtherNet/IP / ...] | [e.g.: PROFIdrive] | [PZD-2/PPO1/...] | [GSDML: ...] |

## 3. PROFINET Configuration (for S7-1500)

```
GSDML File:    [file name, e.g.: GSDML-V2.35-SEW-MOVIDRIVE_B-20210901.xml]
Device Family: [e.g.: SEW-MOVIDRIVE_B]
DAP Module:    [DAP module name]
Default IP:    [e.g.: 192.168.1.50 — set per project]
```

### PROFINET IO Address Example (TIA Portal)
```
Input  (PLC ← Drive):  %I[x].0 — [byte count] byte PZD/Status Word
Output (PLC → Drive):  %Q[x].0 — [byte count] byte PZD/Control Word
```

## 4. Control Words (PROFIdrive Telegram 1 example)

### STW1 — Control Word (PLC → Drive) — Bit definitions
| Bit | Name | 0 = | 1 = |
|-----|------|-----|-----|
| 0 | ON/OFF1 | OFF1 stop via ramp | Ready to run |
| 1 | OFF2 | Coast to stop (coasting) | None |
| 2 | OFF3 | Quick stop (OFF3 ramp) | None |
| 3 | ENABLE_OPERATION | Inhibit operation | Enable operation |
| 4 | RAMP_GEN_ENABLE | Stop ramp generator | Enable |
| 5 | RAMP_GEN_FREEZE | Freeze ramp output | Release |
| 6 | SETPOINT_ENABLE | Setpoint = 0 | Setpoint enabled |
| 7 | FAULT_RESET | — | Reset fault (0→1 edge) |
| 10 | REMOTE_CONTROL | Local control | PROFINET control |

### ZSW1 — Status Word (Drive → PLC) — Bit definitions
| Bit | Name | Description |
|-----|------|-------------|
| 0 | READY_TO_SWITCH_ON | Voltage applied, relay closed |
| 1 | READY | ON/OFF1=1 command received |
| 2 | OPERATION_ENABLED | Motor running |
| 3 | FAULT | Fault present (show on HMI) |
| 6 | SWITCH_ON_INHIBIT | OFF2/OFF3 required after fault |
| 7 | ALARM | Warning (no stop) |
| 11 | REMOTE_CONTROL | PROFINET control active |

## 5. Parameters (Critical)

| Parameter | No | Factory Value | Typical Setting | Description |
|-----------|-----|---------------|-----------------|-------------|
| [P-no] | [e.g.: P100] | [value] | [recommended] | [what it does] |

## 6. TIA Portal — SCL Integration Template

```scl
// [VENDOR] [MODEL] — PROFIdrive Telegram 1 control
// This block is called inside FB_Motor (use an F-FB for drives configured with F61)

// --- OUTPUT (PLC → Drive) ---
// Control Word STW1 (WORD)
#drv_stw1.0 := #cmd_on;           // ON/OFF1
#drv_stw1.1 := TRUE;              // OFF2 none (active)
#drv_stw1.2 := TRUE;              // OFF3 none (active)
#drv_stw1.3 := #cmd_enable;       // Enable Operation
#drv_stw1.4 := TRUE;              // Ramp generator enabled
#drv_stw1.5 := TRUE;              // Ramp released
#drv_stw1.6 := #cmd_setpoint_ok;  // Setpoint valid
#drv_stw1.10 := TRUE;             // Remote (PROFINET)

// Speed setpoint (HSW) — PROFINET normalized: 16384 = max Hz
#drv_hsw := INT_TO_WORD(REAL_TO_INT(#speed_rpm / #max_rpm * 16384.0));

// Write to the target %Q address (set per the configuration table)
// %QW[x] := #drv_stw1;           // Control Word
// %QW[x+2] := #drv_hsw;          // Speed Setpoint

// --- INPUT (Drive → PLC) ---
// Status Word ZSW1 (WORD) — source %IW[x]
// #drv_zsw1 := %IW[x];
#drv_ready    := #drv_zsw1.1;    // Ready
#drv_running  := #drv_zsw1.2;    // Running
#drv_fault    := #drv_zsw1.3;    // Fault
#drv_alarm    := #drv_zsw1.7;    // Warning
```

## 7. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| [issue description] | [cause] | [solution steps] |

## 8. Notes

- [Important notes, limitations, version differences]
- [An F-drive version is required for Safety (STO/SLS) integration]
```

---

## Schema Validation Rules

The GUI "Add Device" screen checks these rules automatically:

1. `device_id` — no spaces, alphanumeric + `_`
2. `vendor` — cannot be empty
3. `model` — cannot be empty
4. `category` — allowed values: `drives`, `io_modules`, `sensors`, `valves`, `hmi`, `controllers`, `cables`, `accessories`
5. There must be at least **1** `##` heading
6. The `metadata` YAML block is mandatory
