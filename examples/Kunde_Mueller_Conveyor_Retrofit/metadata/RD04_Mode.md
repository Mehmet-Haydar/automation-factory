---
title: RD04_Mode — Kunde Müller (operatör görüşmesi sonrası)
last_validated: 2026-05
status: ACTIVE
---

# RD04_Mode — Kunde Müller (operatör görüşmesi sonrası)

```yaml
project_id: KMG-2026-001
status: DRAFT (80%)
```

## Özet
- Toplam mod: 4 (M00 + AUTO + HAND + SETUP)
- M00 Priority=0: ✓
- PackML uyumlu: Y (yeni tasarım)

## Modlar

| ModeID | ModeName | Priority | PackMLState | Description | EntryCondition | ExitCondition | PermittedActions | RestrictedActions | HMI_Color | HMI_Text | DB_ModeWord | Notes | Status |
|--------|----------|----------|-------------|-------------|----------------|---------------|------------------|-------------------|-----------|----------|-------------|-------|--------|
| M00 | Emergency | 0 | Aborted | Acil durdurma (orig: NOT-AUS) | F_I_EStop_North=FALSE OR F_I_EStop_South=FALSE | Reset_Cmd AND tüm E-Stop=TRUE | Reset | Production, Manual_Jog | #FF0000 | NOT-AUS | DB_System.ModeState.iCurrentMode | Yeni F-PLC ile Active | Active |
| M01 | Auto | 50 | Execute | Otomatik üretim (orig: Automatik) | M00 değil AND Op_Auto_Btn AND Safety_OK | Op_Manual_Btn OR M00 | Start, Stop, Reset | Manual_Jog | #00C800 | AUTO | DB_System.ModeState.iCurrentMode | Üretim modu | Active |
| M02 | Manual | 40 | Suspended | Manuel kontrol (orig: Hand) | M00 değil AND Op_Manual_Btn | Op_Auto_Btn OR M00 | Jog, Reset, Single_Step | Auto_Cycle | #FFA500 | HAND | DB_System.ModeState.iCurrentMode | Bakım personeli için | Active |
| M03 | Setup | 30 | Suspended | Komisyonlama (orig: Einrichten) | Auth >= Engineer AND Setup_Key | Auth Loss OR M00 | Single_Step, Jog, Cal | Production | #FFFF00 | SETUP | DB_System.ModeState.iCurrentMode | Yetkilendirme zorunlu | Active |

## Notlar
- Eski kodda sadece 3 mod (Auto/Hand/Setup) vardı, M00 Emergency ayrı değildi — modernizasyon eklemesi
- LOTO modu (M06) eski makinede yok — müşteri talep ederse v1.1.0'a eklenebilir
- HMI_Color renk standardı operatör tanıdığı renklerle uyumlu (test edildi)

---
*v1.0.0 — Operatör Klaus Müller ile 2026-05-12 görüşme sonrası onaylandı.*
