---
title: RD08_Alarm — Kunde Müller (multi-lang DE/EN/TR)
last_validated: 2026-05
status: ACTIVE
---

# RD08_Alarm — Kunde Müller (multi-lang DE/EN/TR)

```yaml
status: DRAFT (75%)
output_language: DE
```

## Summary
- Total alarms: 32 (detected from the legacy FC40)
- Class: Critical 5 | Warning 18 | Info 9
- Multi-lang: EN 100% | DE 100% | TR 0% (not needed — DE project)

## Alarms (6 example rows shown — 32 total)

| AlarmID | AlarmName | Class | Priority | TriggerTag | TriggerCondition | AlarmText_EN | AlarmText_DE | AcknRequired | LinkedSF | RecommendedAction | Status |
|---------|-----------|-------|----------|------------|------------------|--------------|--------------|--------------|----------|-------------------|--------|
| ALM0001 | EStop_North_Pressed | Critical | 1 | F_I_EStop_North | F_I_EStop_North = FALSE | Emergency stop pressed (North) | NOT-AUS Nord gedrückt | Y | SF001 | Release E-Stop, inspect, press RESET | Active |
| ALM0002 | EStop_South_Pressed | Critical | 2 | F_I_EStop_South | F_I_EStop_South = FALSE | Emergency stop pressed (South) | NOT-AUS Süd gedrückt | Y | SF002 | Release E-Stop, inspect, press RESET | Active |
| ALM0003 | LightCurtain_Loading_Broken | Critical | 5 | F_I_LC_Loading | F_I_LC_Loading = TRUE | Light curtain (loading) interrupted | Lichtvorhang (Beladung) unterbrochen | Y | SF003 | Clear the protected zone, press RESET | Active |
| ALM0042 | PROFINET_Comm_Lost | Critical | 15 | gComm.bPN_S1_Error | TMR_WD_COMM.Q | PROFINET communication lost | PROFINET-Kommunikation verloren | Y | | Check network cable + switch | Active |
| ALM0100 | Conveyor1_Drive_Fault | Warning | 100 | MOT_CV01_001_FAULT | MOT_CV01_001_FAULT = FALSE | Conveyor 1 drive fault | Förderer 1 Antriebsstörung | Y | | Show drive fault code, maintenance | Active |
| ALM0500 | Mode_Auto_Started | Info | 500 | DB_System.iCurrentMode | iCurrentMode = 1 | AUTO mode started | AUTO-Modus gestartet | N | | - | Active |

## Notes
- All 32 alarms mapped to the ISA-18.2 classification
- German text preserved from the original legacy WinCC
- 3 of the 5 Critical alarms are cross-referenced with a SAFETY function after F-PLC migration (SF001-SF003)

*v1.0.0 — EN ↔ DE translation consistency verified against the glossary.*
