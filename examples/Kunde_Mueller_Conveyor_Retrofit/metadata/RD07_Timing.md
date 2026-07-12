---
title: RD07_Timing — Kunde Müller (placeholder)
last_validated: 2026-05
status: ACTIVE
---

# RD07_Timing — Kunde Müller (placeholder)

```yaml
status: DRAFT (30%)
plc_cycle_time_ms: 50
```

## Özet
- AI tespit: 8 timer (T1..T8 eski sembol)
- Watchdog: 2 adet (comm + sequence)

## Timer'lar

| TimerID | TimerName | TimerType | PresetValue | Function | LinkedStep | LinkedAlarm | IsWatchdog | Status |
|---------|-----------|-----------|-------------|----------|------------|-------------|-----------|--------|
| TMR_STEP_001 | Step_010_Hold | TON | T#3s | StepDelay | S010 | | N | DRAFT |
| TMR_STEP_002 | Step_020_Convey | TON | T#10s | StepDelay | S020 | | N | DRAFT |
| TMR_DEBOUNCE_001 | EStop_Debounce | TON | T#50ms | Debounce | | | N | DRAFT |
| TMR_WD_COMM | PROFINET_Watchdog | TON | T#500ms | Watchdog | | ALM0042 | Y | DRAFT |
| TMR_WD_SEQ | Sequence_Watchdog | TON | T#60s | Watchdog | | ALM0050 | Y | DRAFT |
| TMR_CYCLE_HZ1 | System_1Hz | TON | T#500ms | CycleControl | | | N | DRAFT |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

*v1.0.0 — Eski S5TIME → IEC TIME dönüşümü yapıldı.*
