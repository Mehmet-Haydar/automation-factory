# RD08_Alarm — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_08_ALARM.md`. Schema: `rd08_alarm.schema.json`.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <Engineer Name>
filled_at: <YYYY-MM-DD>
output_language: <TR | EN | DE>
status: <DRAFT | REVIEWED | APPROVED>
```

---

## Summary

- Total alarms: __
- Class: Critical __ | Warning __ | Info __
- AcknRequired: __
- Multi-lang coverage: EN __% | TR __% | DE __%

---

## Alarms

| AlarmID | AlarmName | Class | Priority | TriggerTag | TriggerCondition | LimitValue | LimitUnit | AlarmText_EN | AlarmText_TR | AlarmText_DE | AcknRequired | SuppressCondition | LinkedTimer | LinkedSF | RecommendedAction | Notes | Status |
|---------|-----------|-------|----------|------------|------------------|------------|-----------|--------------|--------------|--------------|--------------|-------------------|-------------|----------|-------------------|-------|--------|
| ALM0001 | EStop_North_Pressed | Critical | 1 | F_I_EStop_N | F_I_EStop_N = FALSE | | | Emergency stop pressed (North) | Acil durdurma basıldı (Kuzey) | NOT-AUS Nord gedrückt | Y | | | SF001 | Reset E-Stop; verify clear; reset PLC | | Active |
| ALM0020 | TankLevel_HighHigh | Critical | 5 | LT_TK_001 | LT_TK_001 > 95.0 | 95.0 | % | Tank level extremely high | Tank seviyesi çok yüksek | Tankfüllstand sehr hoch | Y | M05 | TMR_DEBOUNCE_005 | | Open drain valve V12; reduce inflow | | Active |
| ALM0042 | Comm_PN_Lost | Critical | 15 | gComm.S1_Error | gComm.S1_Error = TRUE | | | PROFINET communication lost | PROFINET haberleşmesi koptu | PROFINET-Kommunikation verloren | Y | | TMR_WD_001 | | Check network cable; verify switch | | Active |
| ALM0500 | Mode_AutoStarted | Info | 500 | gMode.CurrentMode | gMode.CurrentMode = 1 | | | AUTO mode started | AUTO modu başladı | AUTO-Modus gestartet | N | | | | | | Active |

---

## #UNKNOWNS

| Old alarm | Reason |
|-----------|--------|
| | |

---

## Fill-in Notes

- **AlarmID format:** `^ALM\d{4}$` (4 digits, ALM0001..ALM9999)
- **Class enum:** Critical/Warning/Info
- **Priority 1-999 UNIQUE:** 1-50 Critical, 51-300 Warning, 301-999 Info
- **Class=Critical → AcknRequired=Y** (conditional, enforced by the validator)
- **AlarmText_EN MANDATORY** (min 5 char)
- **AlarmText_DE:** Mandatory for a German customer — the original text is kept AS-IS
- **AlarmText_TR:** Mandatory for a TR project
- **LinkedTimer:** Nuisance filter (RD07 LinkedTimer)
- **LinkedSF:** Safety function (RD05)
- **SuppressCondition:** Mode-based suppression (e.g. `M05` cleaning)
- **RecommendedAction:** A CONCRETE recommendation to the operator (avoid generic statements)
- **Standards:** ISA-18.2, IEC 62682, EEMUA 191

---

*Template v1.0.0 — RD08 Alarm List.*
