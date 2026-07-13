---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD02
generated_at: 2026-07-12T18:24:31+00:00
model: deepseek-chat
step: RD02 Data Dictionary Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

Based on the legacy code analysis, here is the RD02 Data Dictionary for the internal data elements (data blocks, markers/flags, timers, counters, and computed values).

## RD02 Data Dictionary – Internal Data

| Name | LegacyAddress | DataType | Scope | Description | Status |
|------|---------------|----------|-------|-------------|--------|
| Wartungs_Bypass | M 50.0 | BOOL | MARKER | Maintenance bypass for E-Stop and light curtain (DANGEROUS) | DRAFT_UNVERIFIED |
| Freigabe_Beladung | M 60.0 | BOOL | MARKER | Loading release from light curtain logic | DRAFT_UNVERIFIED |
| AUTO_Mode | M 10.7 | BOOL | MARKER | 1 = AUTO mode, 0 = HAND mode | DRAFT_UNVERIFIED |
| Step_10_Active | M 20.0 | BOOL | MARKER | Step 10 active – Fill vessel | DRAFT_UNVERIFIED |
| Step_20_Active | M 20.1 | BOOL | MARKER | Step 20 active – Stirring phase | DRAFT_UNVERIFIED |
| Step_30_Active | M 20.2 | BOOL | MARKER | Step 30 active – Empty vessel | DRAFT_UNVERIFIED |
| Stirrer_Request | M 30.0 | BOOL | MARKER | Stirrer motor start request (from step 20) | DRAFT_UNVERIFIED |
| Temp_RawValue | MW 100 | INT | MARKER | Raw analog value from temperature sensor (0-27648) | DRAFT_UNVERIFIED |
| Timer_Stirring | T 5 | S5TIME | TIMER | Stirring duration timer (30s) | DRAFT_UNVERIFIED |
| Timer_StarDelta | T 1 | S5TIME | TIMER | Star-delta transition delay (6s) | DRAFT_UNVERIFIED |
| ALM_NotAus | DB30.DBX 0.0 | BOOL | DB | Alarm bit – Emergency stop triggered | DRAFT_UNVERIFIED |
| ALM_MotorschutzRuehrer | DB30.DBX 0.1 | BOOL | DB | Alarm bit – Stirrer motor protection triggered | DRAFT_UNVERIFIED |

## UDT Candidates

The following groups of related data should be consolidated into UDTs (User-Defined Types) in the new TIA Portal program:

### UDT_StepChain
- Step_10_Active (M 20.0)
- Step_20_Active (M 20.1)
- Step_30_Active (M 20.2)

### UDT_AlarmData
- ALM_NotAus (DB30.DBX 0.0)
- ALM_MotorschutzRuehrer (DB30.DBX 0.1)

### UDT_TemperatureControl
- Temp_RawValue (MW 100)
- (Future: scaled temperature value, setpoint, hysteresis parameters)

### UDT_SafetyStatus
- Wartungs_Bypass (M 50.0)
- Freigabe_Beladung (M 60.0)
- (Future: safety PLC status, diagnostic bits)