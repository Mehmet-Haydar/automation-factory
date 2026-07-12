---
title: AI Prompt - DOL Motor FB
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield]
motor_type: DOL
power_range: < 7.5 kW
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_FB_TEMPLATE.scl]
schema: PROMPT_CODE_GEN
device_type: MOTOR
target_ai: [Claude Sonnet 4+, GPT-4+, Cursor]
metadata_input: motors.schema.json
output_artifacts: [FB, instance_DB, test_scenarios]
---

# PROMPT_MOTOR_DOL.md

> **Direct-On-Line (DOL) motor:** A motor connected directly to the mains with a single contactor. The simplest form of control.

---

## 1. When to Use?

- Power: < 7.5 kW (typically)
- Application: Conveyor, fan, small pump, simple machine motors
- Reverse: FWD/REV possible with two contactors (interlock mandatory)

## 2. Hardware Architecture

```
PLC ──[Q]──► K1 (contactor) ──► Motor
              │
              └─[K1 aux]──► PLC (run feedback)

Motor protection: Thermal relay or MPCB → to PLC as DI
```

**Typical IO:**
- 1× DO: Contactor output (`MOT_<LOC>_<NUM>_DRIVE`)
- 1× DI: Run feedback / contactor aux (`MOT_<LOC>_<NUM>_FB_RUN`)
- 1× DI: Thermal / overload (`MOT_<LOC>_<NUM>_FB_OL`)

If reversing:
- 2× DO: FWD and REV contactors (mechanical interlock mandatory in hardware)
- 2× DI: FWD and REV feedback

---

## 3. System Prompt (to give to the AI)

```
You are an industrial automation engineer expert in TIA Portal V18+.
Your task: produce fully standards-compliant SCL code for a DOL (Direct-On-Line) motor.

STRICT RULES:
1. Naming: GLOBAL_NAMING_STANDARD.md
2. Structure: GLOBAL_FB_TEMPLATE.scl (4 regions mandatory)
3. All comments in English
4. Optimized Access ON
5. Reset on rising edge (level-triggered forbidden)
6. Feedback timeout mandatory (error if no feedback after start)
7. If reversing, a software interlock in the PLC is mandatory in addition to the hardware interlock

DOL-SPECIFIC:
- Run feedback must arrive within the timeout (default 2s)
- Feedback must drop after stop (default 2s) — welded-contactor detection
- Start must be blocked while the overload signal is high
- In reverse mode: wait time between FWD↔REV transitions (anti-rock, default 500ms)

MANDATORY INTERFACE:
VAR_INPUT
  in_bEnable, in_bReset, in_bManualMode      : Bool
  in_bStartCmd, in_bStopCmd                   : Bool
  in_bManualStart, in_bManualStop             : Bool
  in_bFeedbackRun                             : Bool
  in_bFeedbackOverload                        : Bool
  in_tStartTimeout                            : Time := T#2s
  in_tStopTimeout                             : Time := T#2s
  -- If reversing:
  in_bStartCmdRev, in_bManualStartRev         : Bool   -- optional
  in_bFeedbackRunRev                          : Bool   -- optional
  in_tDirectionChangeDelay                    : Time := T#500ms

VAR_OUTPUT
  out_bMotorRun                               : Bool
  out_bMotorRunRev                            : Bool   -- if reversing
  out_bReady, out_bError                      : Bool
  out_wErrorCode                              : Word
  out_nState                                  : Int
  out_dRunHours                               : DInt   -- total operating hours

ERROR CODES (DOL-specific + common):
  16#0001 = Start cmd but no feedback in timeout
  16#0002 = Stop cmd but feedback still active
  16#0003 = Overload triggered
  16#0004 = Manual/Auto mode conflict
  16#0005 = E-stop active
  16#0006 = Feedback chattering
  16#0010 = FWD and REV requested simultaneously    (reversing)
  16#0011 = Direction change without delay         (reversing)

OUTPUT:
1. Complete SCL code (copy-paste ready for TIA)
2. Instance usage example
3. Test scenarios (minimum 5)
```

---

## 4. User Prompt Template

```
TASK: Generate an FB for the DOL motor below.

MOTOR INFO:
- Tag           : <MOT_LOC_NUM_FUNC>           # e.g.: MOT_CV01_001_DRIVE
- Power         : <kW>                          # e.g.: 5.5 kW
- Reverse       : <No / Yes>                    # e.g.: No
- Manual mode   : <Yes / No>                    # e.g.: Yes
- Start timeout : <ms>                          # e.g.: 2000ms (default)
- Stop timeout  : <ms>                          # e.g.: 2000ms
- Operating hrs : <Yes / No>                    # e.g.: Yes

EXTRA FEATURES:
- <e.g.: status word for HMI>
- <e.g.: periodic maintenance reminder counter>

OUTPUT: Complete SCL code following the GLOBAL_FB_TEMPLATE.scl structure.
```

---

## 5. Expected FB Names

| Scenario | FB Name |
|----------|---------|
| Single-direction DOL | `FB_MOTOR_DOL` |
| FWD/REV DOL | `FB_MOTOR_DOL_REV` |

---

## 6. Validation Checklist

The AI output must contain:

- [ ] FB name `FB_MOTOR_DOL` or `FB_MOTOR_DOL_REV`
- [ ] 4 regions present
- [ ] `s_tonStartTO : TON` (under VAR, not in VAR_TEMP)
- [ ] `s_tonStopTO : TON`
- [ ] Reset rising edge (`s_bResetTrig := in_bReset AND NOT s_bResetEdgeMem`)
- [ ] Overload signal continuously checked across state transitions
- [ ] If reversing: FWD and REV outputs can **never** be TRUE at the same time (software interlock)
- [ ] If reversing: the direction-change-delay is waited before changing direction
- [ ] `s_dRunHours` counts in seconds, using OB1 cycle time (e.g. `OB1.PIP_INPUT_TIME` or the `RUNTIME` instruction)

---

## 7. Typical AI Errors

> Misconceptions encountered in the field.

- ⚠️ The AI often forgets the welded-contactor error (stop cmd but feedback still on). **Ask for it explicitly.**
- ⚠️ In reverse mode it may skip the software interlock, relying on the hardware interlock. **Both are mandatory.**
- ⚠️ It may write the run-hours counter without protection against DInt overflow (~68 years, but still). Instead of DInt, prefer LReal seconds or a `DTL` difference.

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0: Base prompt for DOL motor. Reverse scenario optionally supported.*
