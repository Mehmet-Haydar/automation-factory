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

## Özet
- Toplam alarm: 32 (eski FC40'tan tespit)
- Class: Critical 5 | Warning 18 | Info 9
- Multi-lang: EN 100% | DE 100% | TR 0% (gerekmiyor — DE proje)

## Alarmlar (örnek 6 satır — gerçek 32)

| AlarmID | AlarmName | Class | Priority | TriggerTag | TriggerCondition | AlarmText_EN | AlarmText_DE | AcknRequired | LinkedSF | RecommendedAction | Status |
|---------|-----------|-------|----------|------------|------------------|--------------|--------------|--------------|----------|-------------------|--------|
| ALM0001 | EStop_North_Pressed | Critical | 1 | F_I_EStop_North | F_I_EStop_North = FALSE | Emergency stop pressed (North) | NOT-AUS Nord gedrückt | Y | SF001 | NOT-AUS lösen, prüfen, RESET drücken | Active |
| ALM0002 | EStop_South_Pressed | Critical | 2 | F_I_EStop_South | F_I_EStop_South = FALSE | Emergency stop pressed (South) | NOT-AUS Süd gedrückt | Y | SF002 | NOT-AUS lösen, prüfen, RESET drücken | Active |
| ALM0003 | LightCurtain_Loading_Broken | Critical | 5 | F_I_LC_Loading | F_I_LC_Loading = TRUE | Light curtain (loading) interrupted | Lichtvorhang (Beladung) unterbrochen | Y | SF003 | Schutzbereich räumen, RESET drücken | Active |
| ALM0042 | PROFINET_Comm_Lost | Critical | 15 | gComm.bPN_S1_Error | TMR_WD_COMM.Q | PROFINET communication lost | PROFINET-Kommunikation verloren | Y | | Netzwerkkabel + Switch prüfen | Active |
| ALM0100 | Conveyor1_Drive_Fault | Warning | 100 | MOT_CV01_001_FAULT | MOT_CV01_001_FAULT = FALSE | Conveyor 1 drive fault | Förderer 1 Antriebsstörung | Y | | Drive Fehlercode anzeigen, Wartung | Active |
| ALM0500 | Mode_Auto_Started | Info | 500 | DB_System.iCurrentMode | iCurrentMode = 1 | AUTO mode started | AUTO-Modus gestartet | N | | - | Active |

## Notlar
- 32 alarmın tümü ISA-18.2 sınıflandırmasına uyduruldu
- Almanca metin orijinal eski WinCC'den korundu
- 5 Critical alarm 3'ü F-PLC migrasyon sonrası SAFETY function ile cross-ref (SF001-SF003)

*v1.0.0 — Glossary ile EN ↔ DE çeviri tutarlılığı sağlandı.*
