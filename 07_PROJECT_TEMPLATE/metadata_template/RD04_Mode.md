# RD04_Mode — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_04_MODE.md`. Schema: `rd04_mode.schema.json`.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <Engineer Name>
filled_at: <YYYY-MM-DD>
status: <DRAFT | REVIEWED | APPROVED>
```

---

## Summary

- Total modes: __
- M00 (Emergency) Priority=0: ✓
- PackML compliant: <Y/N>

---

## Modes

| ModeID | ModeName | Priority | PackMLState | Description | EntryCondition | ExitCondition | PermittedActions | RestrictedActions | HMI_Color | HMI_Text | DB_ModeWord | Notes | Status |
|--------|----------|----------|-------------|-------------|----------------|---------------|------------------|-------------------|-----------|----------|-------------|-------|--------|
| M00 | Emergency | 0 | Aborted | Emergency stop (orig: NOT-AUS) | E_Stop = TRUE | Reset_Cmd AND E_Stop = FALSE | Reset | All_Production | #FF0000 | NOT-AUS | DB_System.ModeState.iCurrentMode | | Active |
| M01 | Auto | 50 | Execute | Automatic (orig: Automatik) | NOT M00 AND Op_Auto = TRUE | Op_Manual = TRUE OR M00 | Start, Stop, Reset | Manual_Jog | #00C800 | AUTO | DB_System.ModeState.iCurrentMode | | Active |
| M02 | Manual | 40 | Suspended | Manual (orig: Hand) | NOT M00 AND Op_Manual = TRUE | Op_Auto = TRUE OR M00 | Jog, Reset | Auto_Cycle | #FFA500 | MANUAL | DB_System.ModeState.iCurrentMode | | Active |
| M03 | Setup | 30 | Suspended | Commissioning (orig: Einrichten) | Auth >= Eng AND Setup_Btn | Auth Loss OR M00 | Single_Step, Jog | Production | #FFFF00 | SETUP | DB_System.ModeState.iCurrentMode | | Active |
| M06 | Lockout | 5 | Stopped | LOTO mode | Lockout_Key_Inserted | Lockout_Key_Removed AND Reset | (none, LOTO) | All | #000000 | LOTO | DB_System.ModeState.iCurrentMode | | Active |

---

## #UNKNOWNS

| Old symbol | Reason |
|------------|--------|
| | |

---

## Fill-in Notes

- **ModeID format:** `^M\d{2}$` (M00..M99)
- **M00 Priority=0** (fixed rule)
- **Priority must be unique**
- **PackMLState:** OMAC v3.0 enum (Idle/Execute/Held/Suspended/Stopped/Aborted/...)
- **HMI_Color hex:** `^#[0-9A-F]{6}$`
- **HMI_Text:** Per project language (multi-lang support — detail in RD11)
- **DB_ModeWord:** Must be defined in RD02 (cross-ref)

---

*Template v1.0.0 — RD04 Operating Modes.*
