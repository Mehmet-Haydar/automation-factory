---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD07
generated_at: 2026-07-12T18:25:42+00:00
model: deepseek-chat
step: RD07 Timing Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

# RD07_Timing_draft.md

## Timer Inventory

| TimerID | TimerName | TimerType | PresetValue | Function | TriggerCondition | ResetCondition | OutputAction | LinkedStep | LinkedAlarm | DB_Instance | IsWatchdog | Notes | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TMR_MIX_001 | T5 | TON | T#30s | StepDelay | M20.1 (Schritt 20 aktiv) | T5.Q (Timer abgelaufen) | R M20.1, S M20.2 | RD03: Schritt 20 | | | N | S5 SE (Einschaltverzögerung) verwendet; entspricht IEC TON | DRAFT_UNVERIFIED |
| TMR_STAR_001 | T1 | TON | T#6s | StepDelay | M30.0 (Rührer-Anforderung) | T1.Q (Timer abgelaufen) | Sternschütz AUS, Dreieckschütz EIN | RD03: Schritt 20 | | | N | S5 SE (Einschaltverzögerung) verwendet; entspricht IEC TON | DRAFT_UNVERIFIED |
