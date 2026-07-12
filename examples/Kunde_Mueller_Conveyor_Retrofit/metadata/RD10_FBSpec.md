---
title: RD10_FBSpec — Kunde Müller (modernize edilmiş FB envanteri)
last_validated: 2026-05
status: ACTIVE
---

# RD10_FBSpec — Kunde Müller (modernize edilmiş FB envanteri)

```yaml
project_id: KMG-2026-001
status: DRAFT (70%)
```

## Özet
- Toplam blok: 12 (FB: 6, FC: 6)
- Eski blok sayısı: 11 — yeni envanterde 12 (FB_ModeMgr ve FB_AlarmMgr eklendi)
- Multi-instance FB: 2 (FB_Motor_Conveyor ×2 instance, FB_Valve ×5 instance)

## Sayfa 1: BlockList

| BlockName | BlockType | Version | Description | CalledFrom | InstanceDB | LinkedEquipment | TemplateBase | Notes | Status |
|-----------|-----------|---------|-------------|------------|------------|------------------|--------------|-------|--------|
| FB_Motor_Conveyor | FB | 1.0.0 | DOL/VFD motor kontrolü (Almanca yorum) | OB1 | DB_Mot_Conv01, DB_Mot_Conv02 | Conveyor01, Conveyor02 | GLOBAL_FB_TEMPLATE | Original: FB10 | Active |
| FB_Valve | FB | 1.0.0 | Solenoid valf kontrolü | OB1 | DB_Val_V01, DB_Val_V02, DB_Val_V03, DB_Val_V04, DB_Val_V05 | V01..V05 | GLOBAL_FB_TEMPLATE | Original: FB20 | Active |
| FB_PID_Temperature | FB | 1.0.0 | Tank sıcaklık PID | OB35 (100ms) | DB_PID_T01 | Tank01 Heater | GLOBAL_FB_TEMPLATE | Original: FB30 | Active |
| FB_ModeMgr | FB | 1.0.0 | Mod yönetimi (RD04 + AuthLevel) | OB1 | DB_ModeMgr (singleton) | (sistem geneli) | GLOBAL_FB_TEMPLATE | YENİ — eski kodda FC20 idi | Active |
| FB_AlarmMgr | FB | 1.0.0 | Alarm yönetimi (ISA-18.2) | OB1 | DB_AlarmMgr | (sistem geneli) | GLOBAL_FB_TEMPLATE | YENİ — eski kodda FC40 + FC50 | Active |
| F_FB_EStop_Operator | FB | 1.0.0 | E-Stop güvenlik FB | (SafetyTask) | F_DB_EStop | Safety system | TIA Safety lib | YENİ — F-PLC migration | Active |
| FC_IO_Read | FC | 1.0.0 | Tüm fiziksel girişleri oku | OB1 | (global) | (tüm IO) | Custom | Original: FC1 | Active |
| FC_IO_Write | FC | 1.0.0 | Tüm fiziksel çıkışları yaz | OB1 | (global) | (tüm IO) | Custom | Original: FC2 | Active |
| FC_Sequence | FC | 1.0.0 | Sequence/State machine (RD03) | OB1 | (global) | (tüm) | Custom | Original: FC30 (CASE-based) | Active |
| FC_Recipe_Load | FC | 1.0.0 | Recipe yükleme | OB1 | - | (sistem) | Custom | YENİ — eski kodda yok | Active |
| FC_HMI_DataPack | FC | 1.0.0 | HMI veri paketleme | OB1 | - | (HMI) | Custom | Original: FC50 | Active |
| FC_Diagnostic | FC | 1.0.0 | Diagnostic logger | OB82 | - | (sistem) | Custom | Original: FC99 | Active |

## Sayfa 2: ParamList (FB_Motor_Conveyor — örnek)

| BlockName | ParamName | Section | Type | DefaultValue | Description | LinkedTag | Notes |
|-----------|-----------|---------|------|--------------|-------------|-----------|-------|
| FB_Motor_Conveyor | in_bStartCmd | IN | BOOL | FALSE | Start-Befehl | MOT_CV01_001_START | |
| FB_Motor_Conveyor | in_bStopCmd | IN | BOOL | FALSE | Stopp-Befehl | | |
| FB_Motor_Conveyor | in_bResetCmd | IN | BOOL | FALSE | Reset-Befehl | | |
| FB_Motor_Conveyor | in_bSafetyOK | IN | BOOL | FALSE | Safety-System OK | F_DB_EStop.bQ | F-PLC cross-ref |
| FB_Motor_Conveyor | in_iMode | IN | INT | 0 | Betriebsart | DB_ModeMgr.iCurrentMode | |
| FB_Motor_Conveyor | in_rSetSpeed | IN | REAL | 0.0 | Drehzahl-Sollwert (%) | | |
| FB_Motor_Conveyor | out_bRunning | OUT | BOOL | FALSE | Motor läuft | MOT_CV01_001_OUT | |
| FB_Motor_Conveyor | out_bFault | OUT | BOOL | FALSE | Störung | | |
| FB_Motor_Conveyor | out_iFaultCode | OUT | INT | 0 | Störungscode | | |
| FB_Motor_Conveyor | out_rActSpeed | OUT | REAL | 0.0 | Drehzahl-Istwert | ANALOG_SP_OUT_001 | |
| FB_Motor_Conveyor | inout_udMotorData | INOUT | UDT_Motor | - | HMI veri | DB_Mot_Conv01.sMotor | |
| FB_Motor_Conveyor | stat_bInternalRunReq | STAT | BOOL | FALSE | İç çalışma talebi | | |
| FB_Motor_Conveyor | stat_TON_StartDelay | STAT | TON | - | Start gecikme timer | | Multi-instance |
| ... | ... | ... | ... | ... | ... | ... | (kısaltıldı) |

## Notlar
- 6 FB hepsi GLOBAL_FB_TEMPLATE'den türetildi
- F_FB_EStop_Operator ayrı F-CPU üzerinde (SafetyTask)
- 2 yeni FB eklendi: FB_ModeMgr (modernizasyon) ve FB_AlarmMgr (ISA-18.2)
- Eski FC20+FC40+FC50 birleşip modüler FB'lere dönüştü

---
*v1.0.0 — Gate 5 kod üretimi için hazır. FB_Motor_Conveyor.scl `_output/` altında üretildi.*
