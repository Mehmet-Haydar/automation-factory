---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD11
generated_at: 2026-07-12T18:26:16+00:00
model: deepseek-chat
step: RD11 HMI Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

# RD11_HMI_draft.md

## Sheet 1: ScreenList

| ScreenID | ScreenName | ScreenType | AccessLevel | Title_EN | Title_TR | Title_DE | NavigateTo | LinkedAlarm | Notes | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| SCR001 | Main_Overview | Overview | Operator | Main Overview | | | SCR002, SCR003 | | | DRAFT_UNVERIFIED |
| SCR002 | Conveyor_Control | Detail | Operator | Conveyor Control | | | SCR001 | | | DRAFT_UNVERIFIED |
| SCR003 | Mixer_Control | Detail | Operator | Mixer Control | | | SCR001, SCR004 | | | DRAFT_UNVERIFIED |
| SCR004 | Mixer_Detail | Detail | Engineer | Mixer Detail | | | SCR003 | | | DRAFT_UNVERIFIED |
| SCR005 | Alarm_List | Alarm | Operator | Alarm List | | | SCR001 | ALM_NotAus, ALM_MotorschutzRuehrer | | DRAFT_UNVERIFIED |
| SCR006 | Trend_Temperature | Trend | Operator | Temperature Trend | | | SCR001 | | | DRAFT_UNVERIFIED |
| SCR007 | Diagnostic | Diagnostic | Engineer | Diagnostic | | | SCR001 | | | DRAFT_UNVERIFIED |
| SCR008 | Navigation | Navigation | Operator | Navigation | | | SCR001, SCR002, SCR003, SCR005, SCR006, SCR007 | | | DRAFT_UNVERIFIED |

## Sheet 2: TagList

| HMI_TagID | PLC_Tag | ScreenRef | ElementType | Label_EN | Label_TR | Label_DE | ReadWrite | MinValue | MaxValue | EngUnit | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| HMI_START_BTN | DB_HMI.Cmd.bStart | SCR001 | Button | Start | | | Write | | | | legacy E 0.0 |
| HMI_STOP_BTN | DB_HMI.Cmd.bStop | SCR001 | Button | Stop | | | Write | | | | legacy E 0.1 |
| HMI_AUTO_MODE | DB_HMI.Sts.bAutoMode | SCR001 | Indicator | Auto Mode | | | Read | | | | legacy E 0.2 |
| HMI_MOTOR_PROT_CONV | DB_HMI.Sts.bMotorProtConveyor | SCR002 | Indicator | Motor Protection Conveyor | | | Read | | | | legacy E 0.3 |
| HMI_MOTOR_PROT_MIX | DB_HMI.Sts.bMotorProtMixer | SCR003 | Indicator | Motor Protection Mixer | | | Read | | | | legacy E 0.4 |
| HMI_ES_NORTH | DB_HMI.Sts.bESNorth | SCR001 | Indicator | E-Stop North | | | Read | | | | legacy E 1.0 |
| HMI_ES_SOUTH | DB_HMI.Sts.bESSouth | SCR001 | Indicator | E-Stop South | | | Read | | | | legacy E 1.1 |
| HMI_LIGHT_CURTAIN | DB_HMI.Sts.bLightCurtain | SCR002 | Indicator | Light Curtain | | | Read | | | | legacy E 1.2 |
| HMI_LEVEL_MIN | DB_HMI.Sts.bLevelMin | SCR003 | Indicator | Level Min | | | Read | | | | legacy E 2.0 |
| HMI_LEVEL_MAX | DB_HMI.Sts.bLevelMax | SCR003 | Indicator | Level Max | | | Read | | | | legacy E 2.1 |
| HMI_TEMP_RAW | DB_HMI.Sts.iTempRaw | SCR006 | NumericDisplay | Temperature Raw | | | Read | | | | legacy EW 64 |
| HMI_CONVEYOR_RUN | DB_HMI.Sts.bConveyorRun | SCR002 | Indicator | Conveyor Running | | | Read | | | | legacy A 0.0 |
| HMI_MIXER_STAR | DB_HMI.Sts.bMixerStar | SCR003 | Indicator | Mixer Star | | | Read | | | | legacy A 0.1 |
| HMI_MIXER_DELTA | DB_HMI.Sts.bMixerDelta | SCR003 | Indicator | Mixer Delta | | | Read | | | | legacy A 0.2 |
| HMI_MIXER_MAIN | DB_HMI.Sts.bMixerMain | SCR003 | Indicator | Mixer Main Contactor | | | Read | | | | legacy A 0.3 |
| HMI_INLET_VALVE | DB_HMI.Sts.bInletValve | SCR003 | Indicator | Inlet Valve | | | Read | | | | legacy A 0.4 |
| HMI_HEATER | DB_HMI.Sts.bHeater | SCR003 | Indicator | Heater | | | Read | | | | legacy A 0.5 |
| HMI_FAULT_LAMP | DB_HMI.Sts.bFaultLamp | SCR001 | Indicator | Fault Lamp | | | Read | | | | legacy A 0.6 |
| HMI_MAIN_CONTACTOR | DB_HMI.Sts.bMainContactor | SCR001 | Indicator | Main Contactor | | | Read | | | | legacy A 3.7 |
| HMI_ALM_NOTAUS | DB_HMI.Sts.bAlmNotAus | SCR005 | AlarmWidget | Alarm E-Stop | | | Read | | | | legacy DB30.DBX 0.0 |
| HMI_ALM_MOTOR_PROT_MIX | DB_HMI.Sts.bAlmMotorProtMixer | SCR005 | AlarmWidget | Alarm Motor Protection Mixer | | | Read | | | | legacy DB30.DBX 0.1 |
| HMI_STEP_10 | DB_HMI.Sts.bStep10 | SCR004 | Indicator | Step 10: Filling | | | Read | | | | legacy M 20.0 |
| HMI_STEP_20 | DB_HMI.Sts.bStep20 | SCR004 | Indicator | Step 20: Mixing | | | Read | | | | legacy M 20.1 |
| HMI_STEP_30 | DB_HMI.Sts.bStep30 | SCR004 | Indicator | Step 30: Emptying | | | Read | | | | legacy M 20.2 |
| HMI_MIXER_REQ | DB_HMI.Sts.bMixerReq | SCR004 | Indicator | Mixer Request | | | Read | | | | legacy M 30.0 |
| HMI_LOAD_ENABLE | DB_HMI.Sts.bLoadEnable | SCR002 | Indicator | Load Enable | | | Read | | | | legacy M 60.0 |
| HMI_TEMP_SETPOINT | DB_HMI.Set.iTempSetpoint | SCR006 | NumericInput | Temperature Setpoint | | | ReadWrite | 0 | 27648 | | no legacy operand |
