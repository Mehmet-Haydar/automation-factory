---
title: RD11_HMI — Kunde Müller (placeholder)
last_validated: 2026-05
status: ACTIVE
---

# RD11_HMI — Kunde Müller (placeholder)

```yaml
status: DRAFT (30%)
output_language: DE
```

## Özet
- Eski HMI: WinCC Classic V7.4 — 8 ekran (lokal panel)
- Yeni HMI: TIA WinCC Unified — Hierarchical (4 seviye) + multi-lang

## Sayfa 1: ScreenList (taslak yeni proje)

| ScreenID | ScreenName | ScreenType | AccessLevel | Title_DE | Title_EN | Title_TR | Status |
|----------|------------|------------|-------------|----------|----------|----------|--------|
| SCR001 | Main_Overview | Overview | Operator | Übersicht | Main Overview | Ana Görünüm | DRAFT |
| SCR002 | Conveyor1_Faceplate | Detail | Operator | Förderer 1 | Conveyor 1 | Konveyör 1 | DRAFT |
| SCR003 | Conveyor2_Faceplate | Detail | Operator | Förderer 2 | Conveyor 2 | Konveyör 2 | DRAFT |
| SCR010 | Alarm_List | Alarm | Operator | Alarme | Alarms | Alarmlar | DRAFT |
| SCR020 | Recipe_Mgmt | Recipe | Supervisor | Rezeptverwaltung | Recipe Management | Reçete Yönetimi | DRAFT |
| SCR030 | Trends | Trend | Operator | Trends | Trends | Eğilimler | DRAFT |
| SCR090 | Diagnostics | Diagnostic | Engineer | Diagnose | Diagnostics | Tanı | DRAFT |

## Sayfa 2: TagList (örnek 4 satır — gerçek 60+)

| HMI_TagID | PLC_Tag | ScreenRef | ElementType | Label_DE | Label_EN | ReadWrite | EngUnit | Status |
|-----------|---------|-----------|-------------|----------|----------|-----------|---------|--------|
| HMI_CONV_01_RUN | MOT_CV01_001_OUT | SCR001 | Indicator | Förderer 1 läuft | Conveyor 1 Running | Read | | DRAFT |
| HMI_CONV_01_START | DB_HMI.bBtn_Conv01_Start | SCR002 | Button | Start | Start | Write | | DRAFT |
| HMI_TT_001_VAL | ANALOG_TT_TK_001 | SCR002 | NumericDisplay | Temperatur | Temperature | Read | °C | DRAFT |
| HMI_SETPOINT_T01 | DB_Recipe.rTankTempSetpoint | SCR020 | NumericInput | Temperatur-Sollwert | Temperature Setpoint | Write | °C | DRAFT |

*v1.0.0 — Multi-lang text glossary'den türetildi.*
