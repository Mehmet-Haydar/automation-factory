---
title: RD06_Motion — Kunde Müller (placeholder)
last_validated: 2026-05
status: ACTIVE
---

# RD06_Motion — Kunde Müller (placeholder)

```yaml
status: DRAFT (30%)
```

## Özet
- 1 axis tespit edildi (Conveyor1 — SINAMICS G120 VFD)
- Servo eksen yok (sadece VFD)

## Eksenler (taslak)

| AxisID | AxisName | DriveType | DriveModel | Motor_Tag | Feedback_Tag | EngUnit | HomeMethod | PLCopenFBs | Status |
|--------|----------|-----------|------------|-----------|--------------|---------|------------|------------|--------|
| AX001 | Conveyor1_VFD | VFD_Profidrive | SINAMICS G120C | MOT_CV01_001_OUT | (encoder yok, sadece run feedback) | rpm | None | MC_Power, MC_MoveVelocity, MC_Stop | DRAFT |

## Notlar
- Eski VFD PROFIBUS-DP slave 5 — yeni proje PROFINET'e geçecek (FND004 modernizasyon)
- Servo gerekmiyor (basit konveyör hareketi)

*v1.0.0 — Drive datasheet'ten parametreler eklenecek (Gate 3).*
