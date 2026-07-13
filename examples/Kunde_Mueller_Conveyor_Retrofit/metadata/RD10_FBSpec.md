---
title: RD10_FBSpec — Kunde Müller (modernized FB inventory)
last_validated: 2026-05
status: ACTIVE
---

# RD10_FBSpec — Kunde Müller (modernized FB inventory)

```yaml
project_id: KMG-2026-001
status: DRAFT (70%)
```

## Summary
- Total blocks: 12 (FB: 6, FC: 6)
- Legacy block count: 11 — new inventory has 12 (FB_ModeMgr and FB_AlarmMgr added)
- Multi-instance FB: 2 (FB_Motor_Conveyor ×2 instances, FB_Valve ×5 instances)

## Page 1: BlockList

| BlockName | BlockType | Version | Description | CalledFrom | InstanceDB | LinkedEquipment | TemplateBase | Notes | Status |
|-----------|-----------|---------|-------------|------------|------------|------------------|--------------|-------|--------|
| FB_Motor_Conveyor | FB | 1.0.0 | DOL/VFD motor control (German comments) | OB1 | DB_Mot_Conv01, DB_Mot_Conv02 | Conveyor01, Conveyor02 | GLOBAL_FB_TEMPLATE | Original: FB10 | Active |
| FB_Valve | FB | 1.0.0 | Solenoid valve control | OB1 | DB_Val_V01, DB_Val_V02, DB_Val_V03, DB_Val_V04, DB_Val_V05 | V01..V05 | GLOBAL_FB_TEMPLATE | Original: FB20 | Active |
| FB_PID_Temperature | FB | 1.0.0 | Tank temperature PID | OB35 (100ms) | DB_PID_T01 | Tank01 Heater | GLOBAL_FB_TEMPLATE | Original: FB30 | Active |
| FB_ModeMgr | FB | 1.0.0 | Mode management (RD04 + AuthLevel) | OB1 | DB_ModeMgr (singleton) | (system-wide) | GLOBAL_FB_TEMPLATE | NEW — was FC20 in the legacy code | Active |
| FB_AlarmMgr | FB | 1.0.0 | Alarm management (ISA-18.2) | OB1 | DB_AlarmMgr | (system-wide) | GLOBAL_FB_TEMPLATE | NEW — was FC40 + FC50 in the legacy code | Active |
| F_FB_EStop_Operator | FB | 1.0.0 | E-Stop safety FB | (SafetyTask) | F_DB_EStop | Safety system | TIA Safety lib | NEW — F-PLC migration | Active |
| FC_IO_Read | FC | 1.0.0 | Read all physical inputs | OB1 | (global) | (all IO) | Custom | Original: FC1 | Active |
| FC_IO_Write | FC | 1.0.0 | Write all physical outputs | OB1 | (global) | (all IO) | Custom | Original: FC2 | Active |
| FC_Sequence | FC | 1.0.0 | Sequence/state machine (RD03) | OB1 | (global) | (all) | Custom | Original: FC30 (CASE-based) | Active |
| FC_Recipe_Load | FC | 1.0.0 | Recipe loading | OB1 | - | (system) | Custom | NEW — not in the legacy code | Active |
| FC_HMI_DataPack | FC | 1.0.0 | HMI data packing | OB1 | - | (HMI) | Custom | Original: FC50 | Active |
| FC_Diagnostic | FC | 1.0.0 | Diagnostic logger | OB82 | - | (system) | Custom | Original: FC99 | Active |

## Page 2: ParamList (FB_Motor_Conveyor — example)

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
| FB_Motor_Conveyor | inout_udMotorData | INOUT | UDT_Motor | - | HMI data | DB_Mot_Conv01.sMotor | |
| FB_Motor_Conveyor | stat_bInternalRunReq | STAT | BOOL | FALSE | Internal run request | | |
| FB_Motor_Conveyor | stat_TON_StartDelay | STAT | TON | - | Start delay timer | | Multi-instance |
| ... | ... | ... | ... | ... | ... | ... | (truncated) |

## Notes
- All 6 FBs are derived from GLOBAL_FB_TEMPLATE
- F_FB_EStop_Operator runs on a separate F-CPU (SafetyTask)
- 2 new FBs added: FB_ModeMgr (modernization) and FB_AlarmMgr (ISA-18.2)
- The old FC20+FC40+FC50 merged and turned into modular FBs

---
*v1.0.0 — Ready for Gate 5 code generation. FB_Motor_Conveyor.scl produced under `_output/`.*
