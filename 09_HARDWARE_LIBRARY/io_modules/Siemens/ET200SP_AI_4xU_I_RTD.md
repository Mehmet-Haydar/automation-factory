---
title: Siemens ET 200SP AI 4×U/I/RTD — Analog Input Module
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
---

# Siemens ET 200SP AI 4×U/I/RTD — Analog Input Module

## metadata
```yaml
schema_version: "1.0"
device_id: "SIEMENS_ET200SP_AI4_U_I_RTD"
vendor: "Siemens AG"
model: "ET 200SP AI 4×U/I/RTD/TC ST"
category: "io_modules"
subcategory: "ai_module"
part_number: "6ES7134-6JD00-0CA1"
datasheet_ref: "Siemens ET 200SP AI 4×U/I/RTD/TC ST Manual (A5E03718734)"
library_path: "io_modules/Siemens/ET200SP_AI_4xU_I_RTD.md"
last_verified: "2026-01"
```

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | ET 200SP AI 4×U/I/RTD/TC ST Analog Input Module |
| Category | Analog Input (AI) Module |
| Channel Count | 4 × AI (each channel configured independently) |
| Input Types | Voltage: ±10V, 0–10V, 0–5V, 1–5V |
| | Current: 0–20 mA, 4–20 mA, ±20 mA |
| | RTD: PT100, PT200, PT500, PT1000, Ni100, Cu10 |
| | TC: Type J, K, N, B, E, R, S, T |
| Resolution | 16 bit (internal), 15 bit + sign |
| Conversion time | 52 ms / 4 channels (normal), 26 ms (fast) |
| Common-mode rejection | ≥ 100 dB |
| Error limit | ±0.1% FS (25°C) |
| Protection Class | IP20 |
| Operating Temperature | -30°C … +60°C |
| Certifications | CE, UL, cUL |

## 2. Communication Interfaces

| Interface | Protocol | Format | Notes |
|-----------|----------|--------|-------|
| ET 200SP backplane bus | PROFINET (via head station) | 8 byte input (4 × INT, 2 byte/channel) | Via the ET200SP station |

## 3. PROFINET Configuration (ET 200SP + S7-1500)

```
Module Type:   AI 4×U/I/RTD/TC ST (6ES7134-6JD00-0CA1)
Head Station:  ET 200SP IM 155-6 PN
Backplane Bus: BaseUnit BU15-P16+A10+2D (6ES7193-6BP20-0DA0) — 2-wire for AI
               BaseUnit BU15-P16+A10+4D (6ES7193-6BP40-0DA0) — 4-wire (RTD)
TIA Portal:    Input type configured per channel
```

### IO Address
```
Input: 8 byte (4 channels × 2 byte INT)
       Channel 0 → %IW[n]    (INT, ±27648 normalization)
       Channel 1 → %IW[n+2]  (INT)
       Channel 2 → %IW[n+4]  (INT)
       Channel 3 → %IW[n+6]  (INT)
Output: None (AI module)
```

## 4. Value Normalization

### Voltage/Current Channels (PLC value ↔ physical value)
```
For the 4–20 mA measuring range:
  PLC INT value: 0 = 4 mA, 27648 = 20 mA
  Formula: physical_mA = (plc_int / 27648.0) * (20.0 - 4.0) + 4.0

For the 0–10 V measuring range:
  PLC INT value: 0 = 0 V, 27648 = 10 V
  Formula: physical_V = (plc_int / 27648.0) * 10.0

For the ±10 V measuring range:
  PLC INT value: -27648 = -10 V, 0 = 0 V, 27648 = 10 V
```

### RTD Channels (PT100 example)
```
PT100: PLC INT value = temperature × 10
  Example: 250 = 25.0°C, 1000 = 100.0°C, -100 = -10.0°C
  Formula: temperature_C = plc_int / 10.0
```

### Error Values
```
7FFF hex (32767) = Overrange
8000 hex (-32768) = Underrange or wire break
```

## 5. Parameters (TIA Portal HW Config, per channel)

| Parameter | Value Range | Default | Description |
|-----------|-------------|---------|-------------|
| Input type | U / I / RTD / TC | Disabled | Each channel independent |
| Measuring range | Per type | — | 4–20 mA / ±10 V / PT100 etc. |
| Hysteresis | 0–100% | 10 | Fault hysteresis |
| Integration time | 16.7 / 20 / 50 / 60 ms | 20 ms | Noise filtering |
| Diagnostic address | — | Automatic | Wire-break diagnostics |
| 2-wire / 4-wire | — | 2-wire | Connection type for RTD |

## 6. TIA Portal SCL Integration Template

```scl
// ET 200SP AI 4xU/I/RTD/TC ST — Analog input read and scaling
// NOTE: %IW addresses come from TIA Portal HW Config
// Normalization: 27648 = full-scale upper value

// ------------------------------------------------------------------
// CHANNEL 0 — Current input (4-20 mA → 0-100% pressure)
// ------------------------------------------------------------------
#raw_ch0 := %IW[n];    // Raw INT value

// Error check
IF #raw_ch0 = 32767 THEN
    #ch0_overrange := TRUE;
    #ch0_value := 0.0;
ELSIF #raw_ch0 = -32768 THEN
    #ch0_wire_break := TRUE;
    #ch0_value := 0.0;
ELSE
    #ch0_overrange := FALSE;
    #ch0_wire_break := FALSE;
    // 4-20 mA → 0.0-100.0% scaling
    #ch0_value := (INT_TO_REAL(#raw_ch0) / 27648.0) * 100.0;
END_IF;

// ------------------------------------------------------------------
// CHANNEL 1 — Voltage input (0-10 V → 0-100% fill level)
// ------------------------------------------------------------------
#raw_ch1 := %IW[n+2];

IF #raw_ch1 >= 0 AND #raw_ch1 <= 27648 THEN
    #ch1_level_pct := (INT_TO_REAL(#raw_ch1) / 27648.0) * 100.0;
ELSE
    #ch1_level_pct := 0.0;
END_IF;

// ------------------------------------------------------------------
// CHANNEL 2 — RTD (PT100 → °C temperature)
// ------------------------------------------------------------------
#raw_ch2 := %IW[n+4];

IF #raw_ch2 = 32767 THEN
    #ch2_overrange := TRUE;
    #ch2_temp_c := 0.0;
ELSIF #raw_ch2 = -32768 THEN
    #ch2_sensor_break := TRUE;
    #ch2_temp_c := 0.0;
ELSE
    // PT100: PLC value = temperature × 10
    #ch2_temp_c := INT_TO_REAL(#raw_ch2) / 10.0;
END_IF;

// ------------------------------------------------------------------
// Generic scaling function (reusable)
// ------------------------------------------------------------------
// SCALE block (TIA Portal standard library):
// Use FC105 SCALE or the NORM_X + SCALE_X instruction blocks
//
// Example NORM_X + SCALE_X:
// #normalized := NORM_X(MIN := 0, VALUE := INT_TO_REAL(#raw), MAX := 27648.0);
// #scaled := SCALE_X(MIN := 4.0, VALUE := #normalized, MAX := 20.0);
```

## 7. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| 32767 (overrange) | Signal out of range | Check the transmitter output |
| -32768 (wire break) | Wire break or no transmitter | Check the cable and transmitter supply |
| Value fluctuates | Noise (ground loop) | Use shielded cable, ground the shield at a single point |
| 4-20 mA reading wrong | Wrong BaseUnit selected | Use a P BaseUnit for the AI module |
| RTD reading wrong | Wrong 2-wire/4-wire setting | Channel configuration in TIA Portal: 2-wire |

## 8. Notes

- **BaseUnit selection:** The AI module needs a special BaseUnit — use BU15-P16+A10+2D for a 2-wire sensor, BU15-P16+A10+4D for a 4-wire RTD.
- **Grounding:** Shielded cable and proper grounding are critical for analog channels — noise causes measurement errors.
- **Galvanic isolation:** The module's input channels are NOT galvanically isolated from each other — use an isolation barrier for transmitters with different reference potentials.
- **Conversion time:** 52 ms / 4 channels → for applications requiring high speed, consider a FAST I/O module (AI 4xU/I ST).
- **NORM_X/SCALE_X:** With TIA Portal V14+, using the NORM_X + SCALE_X instruction blocks instead of SCALE (FC105) is the recommended approach.
- **Diagnostics:** Wire-break diagnostics appear in the TIA Portal diagnostic view; in the program they can be read via `RDSYSST` or `DeviceStates`.
