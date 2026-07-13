---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD08
generated_at: 2026-07-12T18:25:47+00:00
model: deepseek-chat
step: RD08 Alarms Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

# RD08_Alarm_draft.md

## Alarm Table

| AlarmID | AlarmName | Class | Priority | TriggerTag | TriggerCondition | LimitValue | LimitUnit | AlarmText_EN | AlarmText_TR | AlarmText_DE | AcknRequired | SuppressCondition | LinkedTimer | LinkedSF | RecommendedAction | Notes | Status |
|---------|-----------|-------|----------|------------|------------------|------------|-----------|--------------|--------------|--------------|--------------|-------------------|-------------|----------|-------------------|-------|--------|
| ALM0001 | NOT_AUS_ausgeloest | Critical | 10 | E1.0, E1.1 | NOT_AUS_Nord = FALSE OR NOT_AUS_Sued = FALSE | | | Emergency stop triggered | | NOT-AUS ausgeloest | Y | M50.0 (Maintenance bypass) | | | Check the cause of the emergency stop, reset the pushbutton | | DRAFT_UNVERIFIED |
| ALM0002 | Motorschutz_Ruehrer_ausgeloest | Critical | 20 | E0.4 | Motorschutz_Ruehrer = TRUE | | | Motor protection stirrer triggered | | Motorschutz Ruehrer ausgeloest | Y | | | | Check the stirrer motor for overload, reset the motor protection switch | | DRAFT_UNVERIFIED |
| ALM0003 | Motorschutz_Band_ausgeloest | Critical | 30 | E0.3 | Motorschutz_Band = TRUE | | | Motor protection conveyor belt triggered | | Motorschutz Band ausgeloest | Y | | | | Check the conveyor belt motor for overload, reset the motor protection switch | | DRAFT_UNVERIFIED |
| ALM0004 | Lichtvorhang_Beladung_ausgeloest | Warning | 100 | E1.2 | Lichtvorhang_Beladung = FALSE | | | Light curtain loading area triggered | | Lichtvorhang Beladung ausgeloest | Y | M50.0 (Maintenance bypass) | | | Check the loading area for obstructions | | DRAFT_UNVERIFIED |
| ALM0005 | Temperatur_zu_hoch | Warning | 150 | MW100 | MW100 > 16500 | 16500 | Raw value | Temperature too high | | Temperatur zu hoch | N | | | | Check the heater control, wait for temperature to drop | | DRAFT_UNVERIFIED |
| ALM0006 | Temperatur_zu_niedrig | Warning | 200 | MW100 | MW100 < 15500 | 15500 | Raw value | Temperature too low | | Temperatur zu niedrig | N | | | | Check the heater control | | DRAFT_UNVERIFIED |
