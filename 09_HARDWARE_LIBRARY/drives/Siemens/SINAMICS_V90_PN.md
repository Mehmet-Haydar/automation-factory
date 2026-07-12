# Siemens SINAMICS V90 PN — drives

## metadata
```yaml
schema_version: "1.0"
device_id: "SIE_V90_PN"
vendor: "Siemens"
model: "SINAMICS V90 PN (servo)"
category: "drives"
subcategory: "servo"
part_number: "6SL3210-5F__-____ (rating-dependent — NOT_VERIFIED)"
datasheet_ref: "SINAMICS V90 PROFINET Operating Instructions (NOT_VERIFIED)"
library_path: "drives/Siemens/SINAMICS_V90_PN.md"
last_verified: "NOT_VERIFIED"
verified: NOT_VERIFIED
```

> **DRAFT / NOT_VERIFIED.** Telegram/positioning structure is standard;
> order number and motor pairing (SIMOTICS S-1FL6) MUST come from the
> datasheet + sizing tool.

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | SINAMICS V90 PROFINET servo drive |
| Category | Servo Amplifier |
| Power Range | 0.05 kW – 7 kW (motor-dependent) |
| Supply | 1 × 200 V AC or 3 × 200/400 V AC (variant) |
| Motor | SIMOTICS S-1FL6 (absolute/incremental encoder) |
| Comms | PROFINET (RT), controlled by S7-1500 (T)/Motion Control |

## 2. Communication

| Interface | Protocol | Telegram | Notes |
|-----------|----------|----------|-------|
| PROFINET | PROFIdrive | Telegram 3 / 111 (positioning, EPOS) | Depends on control mode |

## 3. Control Modes

| Mode | Use | S7-1500 side |
|------|-----|--------------|
| Speed (S) | simple speed axis | FB_Motor_VFD-style speed telegram |
| Basic positioner (EPOS) | point-to-point | Telegram 111, PLCopen TO |

## 4. Address / Telegram

```
Telegram 111 (EPOS): control/status + target position + velocity override.
Managed via a TIA Technology Object (TO_PositioningAxis) — not raw %QW.
```

## 5. SCL Integration

Servo axes use the TIA Motion Control TOs (MC_Power, MC_MoveAbsolute), not
the FB_Motor library. The factory records the drive; the motion program is
an engineer task (flagged as such in RD06_Motion).

## 6. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Axis won't enable | STO active / no MC_Power | Check safety + enable sequence |
| Following error | Gains untuned / mech. bind | Run one-button auto-tune |
| Wrong position | Encoder not referenced | Homing (MC_Home) required |

## 7. Notes

- V90 PN integrates with S7-1500 Motion Control; sizing via the SIZER tool.
- **Motion logic is NOT auto-generated** — RD06 lists it as engineer work.
