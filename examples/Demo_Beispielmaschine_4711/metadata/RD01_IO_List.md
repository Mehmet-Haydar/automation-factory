---
status: done
source: engineer_reviewed_demo
rd: RD01
note: Synthetic demo data - reviewed and approved for the assembler demo.
---

# RD01 — IO List (Demo_Beispielmaschine_4711)

Reviewed demo IO list, derived from `_raw/legacy_code/4711Z0.SEQ` +
`4711_OB1.awl`. Tags follow GLOBAL_NAMING_STANDARD; old S5 addresses are
kept in the Description for traceability.

## Digital / Analog signals

| Tag | Description | IO_Type | Address | SafetyRelated | Status |
|-----|-------------|---------|---------|---------------|--------|
| MOT_HYD_001_FBM | Hydraulic pump star-delta main contactor feedback (old E 1.0) | DI | %I1.0 | N | done |
| MOT_HYD_001_FBS | Hydraulic pump star contactor feedback (old E 1.1) | DI | %I1.1 | N | done |
| MOT_HYD_001_FBD | Hydraulic pump delta contactor feedback (old E 1.2) | DI | %I1.2 | N | done |
| MOT_HYD_001_OL | Hydraulic pump star-delta overload protection (old E 1.3) | DI | %I1.3 | N | done |
| MOT_HYD_001_MAIN | Hydraulic pump star-delta main contactor (old A 4.0) | DQ | %Q4.0 | N | done |
| MOT_HYD_001_STAR | Hydraulic pump star contactor (old A 4.1) | DQ | %Q4.1 | N | done |
| MOT_HYD_001_DELTA | Hydraulic pump delta contactor (old A 4.2) | DQ | %Q4.2 | N | done |
| MOT_CONV_002_FB | Conveyor belt motor run feedback (old E 1.4) | DI | %I1.4 | N | done |
| MOT_CONV_002_OL | Conveyor belt motor overload (old E 1.5) | DI | %I1.5 | N | done |
| MOT_CONV_002_RUN | Conveyor belt motor contactor (old A 4.3) | DQ | %Q4.3 | N | done |
| VLV_COOL_001_ZSO | Coolant valve open limit switch feedback (old E 2.0) | DI | %I2.0 | N | done |
| VLV_COOL_001_OPEN | Coolant valve solenoid open (old A 4.4) | DQ | %Q4.4 | N | done |
| SEN_OILTEMP_001_VAL | Oil temperature sensor 4-20mA (old EW 10) | AI | %IW10 | N | done |
| ENC_SHAFT_001_A | Drive-shaft incremental encoder track A (old E 2.1) | DI | %I2.1 | N | done |

## Notes

- `MOT_HYD_001` is a **star-delta** hydraulic pump → expected library
  match: `FB_Motor_StarDelta` (welded-star/delta protection included).
- `ENC_SHAFT_001` (encoder) has **no library block on purpose** — it
  demonstrates the explicit `#UNKNOWN` path of the assembler.
