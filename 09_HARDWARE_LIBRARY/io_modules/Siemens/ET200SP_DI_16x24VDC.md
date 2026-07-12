---
title: Siemens ET 200SP DI 16×24VDC — Digital Input Module
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
---

# Siemens ET 200SP DI 16×24VDC — Digital Input Module

## metadata
```yaml
schema_version: "1.0"
device_id: "SIEMENS_ET200SP_DI16_24VDC"
vendor: "Siemens AG"
model: "ET 200SP DI 16×24VDC HF"
category: "io_modules"
subcategory: "di_module"
part_number: "6ES7131-6BH01-0BA0"
datasheet_ref: "Siemens ET 200SP DI 16×24VDC HF Manual (A5E03700734)"
library_path: "io_modules/Siemens/ET200SP_DI_16x24VDC.md"
last_verified: "2026-01"
```

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | ET 200SP DI 16×24VDC HF Digital Input Module |
| Category | Digital Input (DI) Module |
| Channel Count | 16 × DI (24 V DC) |
| Input Voltage | 24 V DC (15–30 V DC tolerance) |
| "1" input current | ≥ 5 mA (@24 V) |
| "0" input voltage | ≤ 5 V DC |
| Input delay | HF: 0.05 ms (adjustable 0.05–20 ms) |
| Isolation | Channel group → backplane bus (optocoupler) |
| Protection Class | IP20 |
| Operating Temperature | -30°C … +60°C |
| Certifications | CE, UL, cUL, FM |

## 2. Communication Interfaces

| Interface | Protocol | Format | Notes |
|-----------|----------|--------|-------|
| ET 200SP backplane bus | PROFINET (via head station) | 2 byte input (I address) | Not direct IO — via the ET200SP station |

## 3. PROFINET Configuration (ET 200SP + S7-1500)

```
Module Type:   DI 16×24VDC HF (6ES7131-6BH01-0BA0)
Head Station:  ET 200SP IM 155-6 PN (PROFINET head station)
Backplane Bus: BaseUnit BU15-P16+A10+2D (6ES7193-6BP20-0DA0) — for input
TIA Portal:    Auto-detect or add manually
```

### IO Address (TIA Portal auto-assignment)
```
Input: 2 byte (16 bit) — %IB[x] and %IB[x+1]
       Each bit represents one channel
       Channel 0 = Bit 0 (%I[x].0)
       Channel 15 = Bit 15 (%I[x+1].7)
Output: None (DI module)
```

## 4. Channel Addressing (TIA Portal)

```
Module start address = %IB[n] (assigned by TIA Portal)
Channel 0  → %I[n].0    (DI CH0)
Channel 1  → %I[n].1    (DI CH1)
...
Channel 7  → %I[n].7    (DI CH7)
Channel 8  → %I[n+1].0  (DI CH8)
...
Channel 15 → %I[n+1].7  (DI CH15)
```

### Tagging Suggestion (SCL Tag DB)
```scl
// Tag DB example — %I addresses come from the HW configuration
// Specify the physical address in hardware_config.xlsx
di_emergency_stop    AT %I[n].0 : BOOL;  // DI CH0  — emergency stop button
di_door_switch_1     AT %I[n].1 : BOOL;  // DI CH1  — door switch 1
di_door_switch_2     AT %I[n].2 : BOOL;  // DI CH2  — door switch 2
di_motor_feedback    AT %I[n].3 : BOOL;  // DI CH3  — motor relay feedback
di_sensor_prox_1     AT %I[n].4 : BOOL;  // DI CH4  — inductive sensor 1
di_sensor_prox_2     AT %I[n].5 : BOOL;  // DI CH5  — inductive sensor 2
```

## 5. Parameters (TIA Portal HW Config)

| Parameter | Value Range | Default | Description |
|-----------|-------------|---------|-------------|
| Input delay | 0.05 / 0.1 / 0.4 / 1.6 / 3.2 / 12.8 / 20 ms | 3.2 ms | HF → 0.05 ms |
| Short-circuit diagnostics | On/Off | On | Per channel |
| Fault diagnostics | On/Off | On | diagnostic address in TIA Portal |

## 6. TIA Portal SCL Integration Template

```scl
// ET 200SP DI 16x24VDC HF — Input read example
// NOTE: %I addresses come from TIA Portal HW Config
//       map the physical Rack/Slot/Channel in hardware_config.xlsx

// Example: reading the input bytes
#raw_di_byte0 := %IB[n];     // Channels 0–7
#raw_di_byte1 := %IB[n+1];   // Channels 8–15

// Bit extraction (using symbolic tags is recommended)
#sig_estop        := %I[n].0;    // CH0 — Emergency Stop
#sig_door_sw1     := %I[n].1;    // CH1 — Door switch 1
#sig_door_sw2     := %I[n].2;    // CH2 — Door switch 2
#sig_motor_fb     := %I[n].3;    // CH3 — Motor feedback
#sig_prox1        := %I[n].4;    // CH4 — Inductive sensor 1
#sig_prox2        := %I[n].5;    // CH5 — Inductive sensor 2
#sig_prox3        := %I[n].6;    // CH6 — Inductive sensor 3
#sig_prox4        := %I[n].7;    // CH7 — Inductive sensor 4
#sig_limit_fwd    := %I[n+1].0;  // CH8  — Forward limit switch
#sig_limit_rev    := %I[n+1].1;  // CH9  — Reverse limit switch
#sig_home_sensor  := %I[n+1].2;  // CH10 — Home sensor
// ... CH11–CH15 unused channels
```

## 7. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| All channels 0 | Wrong BaseUnit | Check that the P and M terminals are connected |
| Channel chatter | Input delay too short | TIA Portal → module properties → increase the delay |
| Short-circuit diagnostic fault | Damaged cable | Measure the cable resistance in the field |
| ET200SP PROFINET offline | IP conflict | Check the head station IP |

## 8. Notes

- **BaseUnit:** For the DI module use **BU15-P16+A10+2D** (6ES7193-6BP20-0DA0) — a BaseUnit with input channels.
- **Channel group:** 16 channels organized in 2 groups (8 channels each) — channels in the same group share the same reference potential.
- **HF vs SF:** The HF (High Feature) version offers faster input delay and diagnostics. SF (Standard) ≥ 3.2 ms delay.
- **Color code:** The channel numbers on the BaseUnit are printed on the terminal.
- **Address assignment:** When the module is selected in TIA Portal Hardware Configuration the address is assigned automatically; these addresses must be documented in hardware_config.xlsx.
