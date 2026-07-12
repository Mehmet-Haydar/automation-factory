# RD07_Timing — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_07_TIMING.md`. Schema: `rd07_timing.schema.json`.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <Engineer Name>
filled_at: <YYYY-MM-DD>
status: <DRAFT | REVIEWED | APPROVED>
plc_cycle_time_ms: <50>          # PLC scan time (for the PT < 2×cycle warning)
```

---

## Summary

- Total timers: __
- TimerType: TON __ | TOF __ | TP __ | TONR __
- Function: StepDelay __ | Debounce __ | Watchdog __ | Timeout __ | CycleControl __ | AlarmFilter __
- Watchdog timer: __

---

## Timers

| TimerID | TimerName | TimerType | PresetValue | Function | TriggerCondition | ResetCondition | OutputAction | LinkedStep | LinkedAlarm | DB_Instance | IsWatchdog | Notes | Status |
|---------|-----------|-----------|-------------|----------|------------------|----------------|--------------|------------|-------------|-------------|-----------|-------|--------|
| TMR_HOLD_001 | Step10_Hold | TON | T#3s | StepDelay | Step S010 active | Step S010 inactive | Allow transition to S020 | S010 | | DB_TMR_001 | N | Tank fill hold time | Active |
| TMR_DEBOUNCE_001 | EStop_Debounce | TON | T#50ms | Debounce | E_Stop raw signal | E_Stop FALSE | Filter chatter | | | DB_TMR_002 | N | Mechanical button debounce | Active |
| TMR_WD_001 | Comm_Watchdog | TON | T#1s | Watchdog | Comm_HeartbeatLost | Comm_HeartbeatOK | Trigger ALM0042 | | ALM0042 | DB_TMR_003 | Y | PROFINET WD | Active |
| TMR_CYCLE_HZ1 | System_1Hz_Pulse | TON | T#500ms | CycleControl | NOT bPulse1Hz | (self-reset) | Toggle bPulse1Hz | | | DB_TMR_004 | N | Global 1Hz pulse | Active |

---

## #UNKNOWNS

| Old timer | Reason |
|-----------|--------|
| | |

---

## Fill-in Notes

- **TimerID format:** `^TMR_[A-Z0-9]+_\d{3}$`
- **TimerType IEC enum:** TON / TOF / TP / TONR (for the vendor-specific equivalent see RETROFIT_EXTRACT_TIMING.md)
- **PresetValue:** `T#3s`, `T#500ms`, `T#1m30s`
- **IsWatchdog=Y → LinkedAlarm MANDATORY** (RD08 reference)
- **PT > 2 × plc_cycle_time_ms** (resolution check)
- **Parametric preset (read from a DB):** PresetValue empty + put "Configurable via <DB>" in Notes
- **Multi-instance:** Each instance a separate TimerID + separate DB_Instance
- **Standards:** IEC 61131-3 §2.5.2, §6.5.3

---

*Template v1.0.0 — RD07 Timing.*
