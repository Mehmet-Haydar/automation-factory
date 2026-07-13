---
title: RD04_Mode — Kunde Müller (after operator interview)
last_validated: 2026-05
status: ACTIVE
---

# RD04_Mode — Kunde Müller (after operator interview)

```yaml
project_id: KMG-2026-001
status: DRAFT (80%)
```

## Summary
- Total modes: 4 (M00 + AUTO + HAND + SETUP)
- M00 Priority=0: ✓
- PackML compliant: Y (new design)

## Modes

| ModeID | ModeName | Priority | PackMLState | Description | EntryCondition | ExitCondition | PermittedActions | RestrictedActions | HMI_Color | HMI_Text | DB_ModeWord | Notes | Status |
|--------|----------|----------|-------------|-------------|----------------|---------------|------------------|-------------------|-----------|----------|-------------|-------|--------|
| M00 | Emergency | 0 | Aborted | Emergency stop (orig: NOT-AUS) | F_I_EStop_North=FALSE OR F_I_EStop_South=FALSE | Reset_Cmd AND all E-Stops=TRUE | Reset | Production, Manual_Jog | #FF0000 | NOT-AUS | DB_System.ModeState.iCurrentMode | Active with the new F-PLC | Active |
| M01 | Auto | 50 | Execute | Automatic production (orig: Automatik) | not M00 AND Op_Auto_Btn AND Safety_OK | Op_Manual_Btn OR M00 | Start, Stop, Reset | Manual_Jog | #00C800 | AUTO | DB_System.ModeState.iCurrentMode | Production mode | Active |
| M02 | Manual | 40 | Suspended | Manual control (orig: Hand) | not M00 AND Op_Manual_Btn | Op_Auto_Btn OR M00 | Jog, Reset, Single_Step | Auto_Cycle | #FFA500 | HAND | DB_System.ModeState.iCurrentMode | For maintenance staff | Active |
| M03 | Setup | 30 | Suspended | Commissioning (orig: Einrichten) | Auth >= Engineer AND Setup_Key | Auth Loss OR M00 | Single_Step, Jog, Cal | Production | #FFFF00 | SETUP | DB_System.ModeState.iCurrentMode | Authorization mandatory | Active |

## Notes
- The legacy code only had 3 modes (Auto/Hand/Setup); M00 Emergency was not separate — a modernization addition
- LOTO mode (M06) does not exist on the old machine — can be added in v1.1.0 if the customer requests it
- HMI_Color scheme matches colors the operators already recognize (validated)

---
*v1.0.0 — Approved after the 2026-05-12 interview with operator Klaus Müller.*
