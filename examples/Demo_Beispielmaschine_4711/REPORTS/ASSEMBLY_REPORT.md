# ASSEMBLY REPORT — library-first program assembly

Generated: 2026-06-10T02:10:59+00:00
Result: OK — Assembled 4 device instance(s), 1 unknown item(s) need engineering.

Label: `AUTO_VERIFIED_structural | PENDING_TIA_VERIFY` — TIA compile
and PLCSIM run are still required before field use.

## Device → Library mapping

| Device | Library FB | Instance DB | Bound inputs | Bound outputs |
|--------|-----------|-------------|--------------|---------------|
| MOT_HYD_001 | FB_Motor_StarDelta | iDB_MOT_HYD_001 | in_bFeedbackMain←MOT_HYD_001_FBM, in_bFeedbackDelta←MOT_HYD_001_FBD | out_bMain→MOT_HYD_001_MAIN, out_bStar→MOT_HYD_001_STAR, out_bDelta→MOT_HYD_001_DELTA |
| MOT_CONV_002 | FB_MOTOR_DOL | iDB_MOT_CONV_002 | in_bFeedbackRun←MOT_CONV_002_FB, in_bFeedbackOverload←MOT_CONV_002_OL | out_bMotorRun→MOT_CONV_002_RUN |
| VLV_COOL_001 | FB_VALVE_ONOFF | iDB_VLV_COOL_001 | in_bFeedbackOpen←VLV_COOL_001_ZSO | out_bOpenOutput→VLV_COOL_001_OPEN |
| SEN_OILTEMP_001 | FB_AnalogScale | iDB_SEN_OILTEMP_001 | — | — |

### Engineering TODOs (unwired ports)
- **MOT_HYD_001**: in_bFeedbackOverload ambiguous — candidates: MOT_HYD_001_FBS, MOT_HYD_001_OL (wire manually)
- **VLV_COOL_001**: in_bFeedbackClosed not wired — no matching VLV_COOL_001 signal in RD01
- **VLV_COOL_001**: out_bReadyOpen not wired — no matching VLV_COOL_001 signal in RD01
- **VLV_COOL_001**: out_bReadyClosed not wired — no matching VLV_COOL_001 signal in RD01

## #UNKNOWN — needs an engineer (never silently dropped)
- **ENC_SHAFT_001** — no library block for prefix 'ENC' / description 'Drive-shaft incremental encoder track A (old E 2.1)' (signals: ENC_SHAFT_001_A)

## Copied library blocks (verbatim proof)

| File | SHA-256 (first 16) | Verbatim | Contract |
|------|--------------------|----------|----------|
| FB_AlarmHandler.scl | `713e0c8895ec61aa` | ✓ | FB_AlarmHandler.contract.json |
| FB_AnalogScale.scl | `818357018e26847b` | ✓ | FB_AnalogScale.contract.json |
| FB_ModeManager.scl | `f5087f052a3bda30` | ✓ | FB_ModeManager.contract.json |
| FB_Motor_DOL.scl | `990121c72435bbd2` | ✓ | FB_Motor_DOL.contract.json |
| FB_Motor_StarDelta.scl | `65d132cb9d2f6ffe` | ✓ | FB_Motor_StarDelta.contract.json |
| FB_Valve_OnOff.scl | `dbc3127ae37fbf6e` | ✓ | FB_Valve_OnOff.contract.json |
| FB_Watchdog.scl | `e198712a5e0d37e6` | ✓ | FB_Watchdog.contract.json |
| OB_Diagnostic_OB82.scl | `7cd6c5a1ea27dca1` | ✓ | OB_Diagnostic_OB82.contract.json |
| OB_RackFailure_OB86.scl | `1b61c1d6ec1f680a` | ✓ | OB_RackFailure_OB86.contract.json |
| OB_Startup_OB100.scl | `93e45ebe954ae69d` | ✓ | OB_Startup_OB100.contract.json |

## Generated sources

- iDB_MOT_HYD_001.db
- iDB_MOT_CONV_002.db
- iDB_VLV_COOL_001.db
- iDB_SEN_OILTEMP_001.db
- iDB_ModeManager.db
- iDB_Watchdog.db
- iDB_AlarmHandler.db
- OB_Main.scl

## Validation

| File | Errors | Warnings |
|------|--------|----------|
| FB_AlarmHandler.scl | 0 | 0 |
| FB_AnalogScale.scl | 0 | 0 |
| FB_ModeManager.scl | 0 | 0 |
| FB_Motor_DOL.scl | 0 | 0 |
| FB_Motor_StarDelta.scl | 0 | 0 |
| FB_Valve_OnOff.scl | 0 | 0 |
| FB_Watchdog.scl | 0 | 0 |
| OB_Diagnostic_OB82.scl | 0 | 0 |
| OB_Main.scl | 0 | 1 |
| OB_RackFailure_OB86.scl | 0 | 0 |
| OB_Startup_OB100.scl | 0 | 0 |

## Contract gate (copied blocks)

| File | Overall | Label |
|------|---------|-------|
| FB_AlarmHandler.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |
| FB_AnalogScale.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |
| FB_ModeManager.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |
| FB_Motor_DOL.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |
| FB_Motor_StarDelta.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |
| FB_Valve_OnOff.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |
| FB_Watchdog.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |
| OB_Diagnostic_OB82.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |
| OB_RackFailure_OB86.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |
| OB_Startup_OB100.scl | PASS | AUTO_VERIFIED_structural | PENDING_TIA_VERIFY |