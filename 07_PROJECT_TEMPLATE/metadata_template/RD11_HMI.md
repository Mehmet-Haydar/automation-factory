# RD11_HMI — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_11_HMI.md`. Schema: `rd11_hmi.schema.json`.
> **Two sheets:** ScreenList + TagList.

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

- Total screens: __
- Total HMI tags: __
- Access: Operator __ | Supervisor __ | Engineer __
- Multi-lang: EN __% | TR __% | DE __%

---

## Sheet 1: ScreenList

| ScreenID | ScreenName | ScreenType | AccessLevel | Title_EN | Title_TR | Title_DE | NavigateTo | LinkedAlarm | Notes | Status |
|----------|------------|------------|-------------|----------|----------|----------|------------|-------------|-------|--------|
| SCR001 | Main_Overview | Overview | Operator | Main Overview | Ana Görünüm | Übersicht | SCR002,SCR010 | | Plant overview | Active |
| SCR002 | Motor_Faceplate | Detail | Operator | Motor Detail | Motor Detayı | Motor Detail | SCR001 | ALM0001,ALM0002 | Pump01 faceplate | Active |
| SCR010 | Alarm_List | Alarm | Operator | Alarms | Alarmlar | Alarme | SCR001 | (all) | ISA-18.2 summary | Active |
| SCR020 | Recipe_Mgmt | Recipe | Supervisor | Recipe Management | Reçete Yönetimi | Rezeptverwaltung | SCR001 | | | Active |
| SCR030 | Trends | Trend | Operator | Trends | Eğilimler | Trends | SCR001 | | | Active |
| SCR090 | Diagnostics | Diagnostic | Engineer | Diagnostics | Tanı | Diagnose | SCR001 | | | Active |

---

## Sheet 2: TagList

| HMI_TagID | PLC_Tag | ScreenRef | ElementType | Label_EN | Label_TR | Label_DE | ReadWrite | MinValue | MaxValue | EngUnit | Notes |
|-----------|---------|-----------|-------------|----------|----------|----------|-----------|----------|----------|---------|-------|
| HMI_PUMP_01_RUN | DB_HMI.Sts.bPump01Run | SCR001 | Indicator | Pump 1 Running | Pompa 1 Çalışıyor | Pumpe 1 läuft | Read | | | | legacy A 5.0 · MOT_PUMP_01_OUT |
| HMI_PUMP_01_START | DB_HMI.Cmd.bPump01Start | SCR002 | Button | Start | Başlat | Start | Write | | | | legacy E 0.0 |
| HMI_TT_001_VAL | DB_HMI.Sts.iTT001Val | SCR002 | NumericDisplay | Temperature | Sıcaklık | Temperatur | Read | -20 | 200 | °C | legacy EW 10 · ANALOG_TT_001 |
| HMI_SETPOINT_001 | DB_Recipe.rSetpoint | SCR020 | NumericInput | Setpoint | Set Değeri | Sollwert | Write | 0 | 100 | % | |
| HMI_LED_MODE | DB_System.ModeState.iCurrentMode | SCR001 | Indicator | Mode | Mod | Modus | Read | | | | |

---

## #UNKNOWNS

| HMI element | Reason |
|-------------|--------|
| | |

---

## Fill-in Notes

- **ScreenID format:** `^SCR\d{3}$`
- **HMI_TagID format:** `^HMI_[A-Z0-9_]+$`
- **ScreenType enum:** Overview/Detail/Alarm/Trend/Recipe/Diagnostic/Navigation
- **AccessLevel enum (ISA-101):** Operator/Supervisor/Engineer
- **ElementType enum:** Button/Indicator/NumericDisplay/NumericInput/Trend/AlarmWidget/Text/Image
- **ReadWrite enum:** Read/Write/ReadWrite
- **Label_EN MANDATORY** (multi-lang minimum)
- **NumericInput → MinValue/MaxValue mandatory** (input validation)
- **Standards:** ISA-101, IEC 62714-1, NAMUR NE107

---

*Template v1.0.0 — RD11 HMI.*
