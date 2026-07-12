# Siemens SINAMICS G120C — drives

## metadata
```yaml
schema_version: "1.0"
device_id: "SIE_G120C"
vendor: "Siemens"
model: "SINAMICS G120C (compact)"
category: "drives"
subcategory: "ac_drive"
part_number: "6SL3210-1KE__-__ (rating-dependent — NOT_VERIFIED)"
datasheet_ref: "SINAMICS G120C Operating Instructions (NOT_VERIFIED)"
library_path: "drives/Siemens/SINAMICS_G120C.md"
last_verified: "NOT_VERIFIED"
verified: NOT_VERIFIED
```

> **DRAFT / NOT_VERIFIED.** PROFIdrive telegram structure below is standard
> and stable; the exact order number depends on power rating and MUST be
> selected from the datasheet per project.

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | SINAMICS G120C compact converter |
| Category | AC Drive (V/f, vector) |
| Power Range | 0.55 kW – 132 kW (frame-dependent) |
| Supply | 3 × 380..480 V AC |
| Integrated Safety | STO (basic, terminal) — confirm variant |
| Comms | PROFINET / PROFIBUS (variant-dependent) |

## 2. Communication

| Interface | Protocol | Telegram | Notes |
|-----------|----------|----------|-------|
| PROFINET | PROFIdrive | Standard Telegram 1 (PZD-2/2) | GSDML per firmware |

## 3. PROFINET IO Address Example

```
Input  (PLC ← Drive): %IW[x]   ZSW1 (status),  %IW[x+2] actual speed
Output (PLC → Drive): %QW[x]   STW1 (control), %QW[x+2] speed setpoint (HSW)
Setpoint norm: 16384 (0x4000) = reference frequency (p2000).
```

## 4. Control / Status Words

Standard Telegram 1 — same STW1/ZSW1 bit layout as the `_SCHEMA_DEVICE`
PROFIdrive reference (ON/OFF1 bit0, Enable bit3, Fault-Reset bit7; Ready
ZSW1.1, Running ZSW1.2, Fault ZSW1.3).

## 5. SCL Integration

Use the FB_Motor_VFD library block: bind `in_rSetpointHz` to the speed
setpoint, `in_bFeedbackRun` to ZSW1.2, overload/fault to ZSW1.3. The
telegram mapping (STW/ZSW ↔ %QW/%IW) is set in HW config, not user code.

## 6. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| F07801 overcurrent | Ramp too steep / mech. jam | Extend p1120 ramp, check load |
| No PROFINET comms | Device name / IP mismatch | Assign device name in TIA |
| STO won't clear | Safety terminals open | Check F-DQ / safety relay to STO |

## 7. Notes

- For SLS/SS1 beyond basic STO a Failsafe variant + F-CPU is required.
- Commissioning wizard (p0010) must be completed before RUN.
