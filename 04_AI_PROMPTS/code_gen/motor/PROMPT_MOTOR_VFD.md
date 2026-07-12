---
title: AI Prompt - VFD Motor FB
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield]
motor_type: VFD
power_range: any
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_FB_TEMPLATE.scl, DOMAIN_DRIVES_CONFIG.md]
schema: PROMPT_CODE_GEN
device_type: MOTOR
target_ai: [Claude Sonnet 4+, GPT-4+, Cursor]
metadata_input: motors.schema.json
output_artifacts: [FB, instance_DB, test_scenarios]
---

# PROMPT_MOTOR_VFD.md

> **VFD (Variable Frequency Drive) motor:** A motor controlled at variable speed via a frequency drive. The most common motor control type in modern projects.

---

## 1. When to Use?

- When speed control is required (adjustable conveyor speed, pump flow rate, etc.)
- When soft starting + energy savings are both wanted
- When torque control is required (special applications)
- Common brands: Siemens G120/S120, ABB ACS580/880, Danfoss FC302, SEW MoviTrac

---

## 2. Communication Methods

There are 3 common methods between the VFD and PLC. This prompt supports **all 3**:

### 2.1 Hardwired (DI/DO + AI/AO)
- In old projects, simple control
- DI: Run, Ready, Fault feedback
- DO: Start, Reverse, Reset
- AI: Frequency feedback (4-20mA or 0-10V)
- AO: Frequency setpoint (4-20mA or 0-10V)

### 2.2 Profinet (Telegram-based, Siemens standard)
- Standard Telegram 1: STW1/HSW + ZSW1/HIW (16-bit)
- Telegram 352: PZD11 (control+status+measurement)
- Preferred in modern projects, minimal wiring

### 2.3 Modbus TCP / Modbus RTU
- Common on brands such as ABB, Danfoss, Schneider
- Register-based (40001-40010 etc.)

**This prompt asks for the communication type as a parameter.**

---

## 3. System Prompt

```
You are an industrial automation engineer expert in TIA Portal V18+.
Your task: produce fully standards-compliant SCL code for a VFD motor.

STRICT RULES:
1. Naming: GLOBAL_NAMING_STANDARD.md
2. Structure: GLOBAL_FB_TEMPLATE.scl (4 regions mandatory)
3. All comments in English
4. Optimized Access ON
5. Reset rising edge

VFD-SPECIFIC — CRITICAL:
1. The setpoint is entered in engineering units (Hz or RPM); inside the FB it is converted to the drive-appropriate scale
2. Setpoint clamping: kept within min/max limits
3. If the difference between the speed feedback and setpoint stays out of tolerance for a set time, error
4. Reverse support (parameterized) — since there is no mechanical interlock in hardware, software control is sufficient
5. Communication type is a parameter: HARDWIRED, PROFINET_T1, PROFINET_T352, MODBUS
6. If Profinet is used, the STW1/ZSW1 bits are interpreted per standard:
   STW1.0 = ON/OFF1, .1 = OFF2 (coast), .2 = OFF3 (quick stop)
   .3 = Enable operation, .4-6 = Ramp gen, .7 = Ack fault
   .10 = PLC control requested, .11 = Reverse
   ZSW1.0 = Ready to switch on, .2 = Operation enabled
   .3 = Fault present, .7 = Warning, .9 = Control granted

MANDATORY STATE MACHINE:
  0   IDLE
  10  WAIT_DRIVE_READY
  20  PRE_START (setpoint preparation)
  30  STARTING (start issued, ramp-up)
  40  RUNNING (setpoint tracking)
  50  STOPPING (ramp-down)
  99  ERROR

MANDATORY INTERFACE:
VAR_INPUT
  in_bEnable, in_bReset, in_bManualMode      : Bool
  in_bStartCmd, in_bStopCmd                   : Bool
  in_bReverseReq                              : Bool
  in_rSetpointHz                              : Real    -- engineering unit
  in_rMinFreq                                 : Real := 0.0
  in_rMaxFreq                                 : Real := 50.0
  in_rDeviationTolerance                      : Real := 2.0    -- Hz
  in_tDeviationTimeout                        : Time := T#5s
  in_nCommType                                : Int     -- 0=HARDWIRED, 1=PNT1, 2=PNT352, 3=MODBUS
  -- Hardwired feedback (CommType=0):
  in_bFeedbackRun                             : Bool
  in_bFeedbackReady                           : Bool
  in_bFeedbackFault                           : Bool
  in_rFeedbackHz                              : Real
  -- Telegram feedback (CommType=1,2): received as words
  in_wZSW1                                    : Word
  in_iActualSpeedRaw                          : Int     -- 16384 = nominal speed (Telegram standard)

VAR_OUTPUT
  -- Hardwired output:
  out_bStartCmd                               : Bool
  out_bResetCmd                               : Bool
  out_bReverseCmd                             : Bool
  out_rSetpointAO                             : Real    -- scaled for mA/V
  -- Telegram output:
  out_wSTW1                                   : Word
  out_iSetpointRaw                            : Int     -- 16384 = nominal
  -- General:
  out_bReady, out_bError                      : Bool
  out_wErrorCode                              : Word
  out_nState                                  : Int
  out_bAtSpeed                                : Bool    -- setpoint reached?
  out_rActualHz                               : Real    -- scaled for each CommType
  out_dRunHours                               : DInt

ERROR CODES:
  16#0001 = Start but no Ready feedback
  16#0002 = Stop but feedback active beyond timeout
  16#0003 = Motor overload (drive trip)
  16#0004 = Manual/Auto conflict
  16#0005 = E-stop
  16#0006 = Drive Fault signal
  16#0010 = Setpoint out of range (clamped, not error itself, but log)
  16#0011 = Speed deviation > tolerance for too long
  16#0012 = Communication lost (PNT/Modbus)
  16#0013 = Drive not in PLC control mode (ZSW1.9 = 0)

OUTPUT:
1. Complete SCL code (conditional logic by CommType)
2. Telegram 1 scaling helper function (16384 = ref speed)
3. Instance usage example (for 3 different CommTypes)
4. Test scenarios (minimum 7)
```

---

## 4. User Prompt Template

```
TASK: Generate an FB for the VFD motor below.

MOTOR INFO:
- Tag             : <MOT_LOC_NUM_FUNC>           # e.g.: MOT_CV02_001_VFD
- Power           : <kW>
- Drive brand     : <Siemens G120 / ABB ACS580 / etc.>
- Communication   : <HARDWIRED / PROFINET_T1 / PROFINET_T352 / MODBUS>
- Speed range     : <min Hz> – <max Hz>          # e.g.: 5 – 50 Hz
- Reverse         : <Yes / No>
- Speed deviation tolerance: <Hz>                # default 2 Hz
- Manual mode     : <Yes / No>

TAGS (if Hardwired):
- Setpoint AO     : <AO_LOC_NUM>                 # e.g.: AO_PNL_001_FREQ_SP
- Feedback AI     : <AI_LOC_NUM>                 # e.g.: AI_PNL_001_FREQ_FB

OUTPUT: Complete SCL code following the GLOBAL_FB_TEMPLATE.scl structure.
```

---

## 5. Expected FB Name

`FB_MOTOR_VFD`

---

## 6. Validation Checklist

- [ ] The state machine contains the states above
- [ ] CommType selection cleanly separated with `CASE` (each type in its own region)
- [ ] For Telegram 1: the constant nominal_speed_raw = 16384 is used
- [ ] Setpoint clamping: `IF in_rSetpointHz < in_rMinFreq THEN ...`
- [ ] A speed-deviation timer exists; error if it stays outside the threshold for a set time
- [ ] STW1.10 (PLC control requested) always TRUE (in run states)
- [ ] STW1.0 (ON/OFF1) TRUE only while running
- [ ] Reverse: STW1.11 = `in_bReverseReq AND in_bEnable AND state ≥ 30`
- [ ] Fault clearing: rising edge `in_bReset` → STW1.7 (Ack fault) TRUE for one scan

---

## 7. Typical AI Errors

- ⚠️ The AI often assumes nominal speed = 27648 (S7 standard analog), whereas the Telegram standard is **16384**.
- ⚠️ STW1.10 (control requested) is forgotten — without it the drive does not accept the setpoint.
- ⚠️ Reverse is attempted by sending a negative setpoint — this is wrong. Reverse is a separate bit (.11).
- ⚠️ ZSW1.3 (fault) is confused with ZSW1.7 (warning) — a warning is not a fault, just information.

---

## 8. Telegram 1 Scaling Helper

The FB the AI produces should contain these helpers:

```scl
// Hz → Telegram raw (16384 = reference speed)
FUNCTION FC_HZ_TO_RAW : Int
VAR_INPUT
   rHz : Real;
   rRefHz : Real;  // motor nominal Hz (usually 50.0)
END_VAR
   FC_HZ_TO_RAW := REAL_TO_INT(rHz / rRefHz * 16384.0);
END_FUNCTION

// Telegram raw → Hz
FUNCTION FC_RAW_TO_HZ : Real
VAR_INPUT
   iRaw : Int;
   rRefHz : Real;
END_VAR
   FC_RAW_TO_HZ := INT_TO_REAL(iRaw) / 16384.0 * rRefHz;
END_FUNCTION
```

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0: For VFD motors; hardwired + Profinet + Modbus support. The default motor control prompt in modern projects.*
