---
title: Siemens ET 200SP DQ 16×24VDC — Digital Output Module
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
---

# Siemens ET 200SP DQ 16×24VDC — Digital Output Module

## metadata
```yaml
schema_version: "1.0"
device_id: "SIEMENS_ET200SP_DQ16_24VDC"
vendor: "Siemens AG"
model: "ET 200SP DQ 16×24VDC/0.5A HF"
category: "io_modules"
subcategory: "do_module"
part_number: "6ES7132-6BH01-0BA0"
datasheet_ref: "Siemens ET 200SP DQ 16×24VDC/0.5A HF Manual (A5E03700750)"
library_path: "io_modules/Siemens/ET200SP_DQ_16x24VDC.md"
last_verified: "2026-01"
```

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | ET 200SP DQ 16×24VDC/0.5A HF Digital Output Module |
| Category | Digital Output (DQ) Module |
| Channel Count | 16 × DQ (24 V DC, 0.5 A/channel) |
| Output Voltage | 24 V DC (±20%) |
| Output Current | 0.5 A / channel (max 4 A / group) |
| Output Type | PNP sourcing |
| Turn-on time | 0.5 ms (typical) |
| Turn-off time | 2 ms (typical) |
| Short-circuit protection | Electronic (per channel) |
| Protection Class | IP20 |
| Operating Temperature | -30°C … +60°C |
| Certifications | CE, UL, cUL |

## 2. Communication Interfaces

| Interface | Protocol | Format | Notes |
|-----------|----------|--------|-------|
| ET 200SP backplane bus | PROFINET (via head station) | 2 byte output (Q address) | Via the ET200SP station |

## 3. PROFINET Configuration (ET 200SP + S7-1500)

```
Module Type:   DQ 16×24VDC/0.5A HF (6ES7132-6BH01-0BA0)
Head Station:  ET 200SP IM 155-6 PN (PROFINET head station)
Backplane Bus: BaseUnit BU15-P16+A10+2D (6ES7193-6BP20-0DA0) — for output
TIA Portal:    Auto-detect or add manually
```

### IO Address (TIA Portal auto-assignment)
```
Output: 2 byte (16 bit) — %QB[x] and %QB[x+1]
        Each bit represents one channel
        Channel 0 = Bit 0 (%Q[x].0)
        Channel 15 = Bit 15 (%Q[x+1].7)
Input: None (DQ module) — diagnostic address only
```

## 4. Channel Addressing (TIA Portal)

```
Module start address = %QB[n] (assigned by TIA Portal)
Channel 0  → %Q[n].0    (DQ CH0)
Channel 1  → %Q[n].1    (DQ CH1)
...
Channel 7  → %Q[n].7    (DQ CH7)
Channel 8  → %Q[n+1].0  (DQ CH8)
...
Channel 15 → %Q[n+1].7  (DQ CH15)
```

### Tagging Suggestion (SCL Tag DB)
```scl
// Tag DB example — %Q addresses come from the HW configuration
dq_motor_contactor   AT %Q[n].0 : BOOL;  // DQ CH0  — Motor contactor
dq_brake_output      AT %Q[n].1 : BOOL;  // DQ CH1  — Brake release output
dq_alarm_lamp        AT %Q[n].2 : BOOL;  // DQ CH2  — Alarm lamp
dq_horn              AT %Q[n].3 : BOOL;  // DQ CH3  — Audible alarm (horn)
dq_valve_1           AT %Q[n].4 : BOOL;  // DQ CH4  — Solenoid valve 1
dq_valve_2           AT %Q[n].5 : BOOL;  // DQ CH5  — Solenoid valve 2
```

## 5. Parameters (TIA Portal HW Config)

| Parameter | Value Range | Default | Description |
|-----------|-------------|---------|-------------|
| Substitute value | 0 / 1 / Hold | 0 | Output value when the PROFINET connection drops |
| Short-circuit response | Turn off / Re-enable | Turn off | Behavior after a short circuit |
| Fault diagnostics | On/Off | On | Writes to the diagnostic address |

## 6. TIA Portal SCL Integration Template

```scl
// ET 200SP DQ 16x24VDC/0.5A HF — Output write example
// NOTE: %Q addresses come from TIA Portal HW Config
//       map the physical Rack/Slot/Channel in hardware_config.xlsx

// Motor control outputs
%Q[n].0 := #fb_motor_contactor;    // CH0 — Motor contactor
%Q[n].1 := #fb_brake_release;      // CH1 — Brake release
%Q[n].2 := #alarm_active;          // CH2 — Alarm lamp
%Q[n].3 := #alarm_audio;           // CH3 — Horn
%Q[n].4 := #valve_1_cmd;           // CH4 — Valve 1
%Q[n].5 := #valve_2_cmd;           // CH5 — Valve 2
%Q[n].6 := #conveyor_fwd;          // CH6 — Conveyor forward
%Q[n].7 := #conveyor_rev;          // CH7 — Conveyor reverse

// Byte write (update all channels at once)
// %QB[n]   := BOOL_TO_BYTE(#ch0) OR ...; -- requires bit manipulation
// Preferred: use symbolic bit addressing (as above)
```

## 7. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Channel stuck at "0" | Substitute value = 0 | Check the PROFINET connection status |
| Short-circuit diagnostic | Damaged cable or overload | Measure the channel current (max 0.5A) |
| High temperature | Overcurrent, no ventilation | Check the group current (max 4A/group) |
| LED not lit | No BaseUnit supply | Check the L+ and M terminals |

## 8. Notes

- **BaseUnit:** For the DQ module use **BU15-P16+A10+2D** (6ES7193-6BP20-0DA0).
- **Group current:** 16 channels split into 2 groups (8 channels each), max 4 A per group. Inductive loads may require derating.
- **Isolation:** The output channels are not galvanically isolated from the backplane bus — they use the same 24 V supply.
- **Substitute:** What value the outputs hold when the PROFINET connection drops is configured in TIA Portal.
- **Relay load:** 0.5A max — for large contactors use a relay adapter or a separate output module.
- **Diagnostics:** Short-circuit or open-circuit diagnostics are written to the diagnostic address and appear in the TIA Portal CPU diagnostic view.
