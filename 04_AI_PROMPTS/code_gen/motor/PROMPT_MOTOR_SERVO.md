---
title: AI Prompt - Servo Motor FB
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield]
motor_type: SERVO
power_range: < 30 kW
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_FB_TEMPLATE.scl, DOMAIN_DRIVES_CONFIG.md]
schema: PROMPT_CODE_GEN
device_type: MOTOR
target_ai: [Claude Sonnet 4+, GPT-4+, Cursor]
metadata_input: motors.schema.json
output_artifacts: [FB, instance_DB, test_scenarios]
---

# PROMPT_MOTOR_SERVO.md

> **Servo motor:** A high-dynamic, closed-loop position/speed/torque control motor. This prompt is written for servo axes using the **TIA Portal Technology Object (TO_PositioningAxis)**.

---

## 1. When to Use?

- Position control is required (axis, indexing, robotic motion)
- High dynamics (fast acceleration/deceleration)
- Synchronous motion (electronic gearing/camming)
- Common brands: Siemens S210/SINAMICS V90, Beckhoff AX5xxx, Bosch IndraDrive

**Out of scope for this prompt:**
- Multi-axis kinematics (CNC, robotics) — a separate system (SIMATIC Robot, NC control)
- Path planning — higher-level TOs such as TO_KinematicsAccess

---

## 2. Architecture (TIA Portal TO)

```
PLC (S7-1500T)
  │
  └── Technology Object: "AX_<LOC>_<NUM>"  (TO_PositioningAxis)
         │
         └── Profinet IRT ──► SINAMICS Drive ──► Servo Motor + Encoder

Standard Motion Control blocks (TIA Portal):
- MC_Power      : Axis power enable
- MC_Reset      : Fault reset
- MC_Home       : Referencing (homing)
- MC_MoveAbsolute : Absolute position move
- MC_MoveRelative : Relative position
- MC_MoveJog    : Jog (manual move)
- MC_Halt       : Smooth stop
- MC_Stop       : Emergency stop (ramp)
```

**This FB wraps these blocks (wrapper).**

---

## 3. System Prompt

```
You are an industrial automation engineer expert in TIA Portal V18+.
Your task: produce a high-level control FB based on TO_PositioningAxis for a servo axis.

STRICT RULES:
1. Naming: GLOBAL_NAMING_STANDARD.md
2. Structure: GLOBAL_FB_TEMPLATE.scl (4 regions mandatory)
3. All comments in English
4. Optimized Access ON
5. Reset rising edge

SERVO-SPECIFIC — CRITICAL:
1. The TO reference is passed as VAR_IN_OUT via `inout_axis : TO_PositioningAxis`
2. MC_* blocks are instantiated inside (static, not in VAR_TEMP)
3. Axis power: in_bEnable rising edge → MC_Power active
4. Homing mandatory first → absolute moves forbidden until homing completes
5. Move commands are triggered on a rising edge (Execute parameter)
6. A new command during an active move → the BufferMode parameter decides
7. On fault, Reset via MC_Reset, then re-activate MC_Power

MANDATORY STATE MACHINE:
  0   IDLE_DISABLED (axis disabled)
  10  ENABLING (MC_Power command issued)
  20  IDLE_ENABLED_NOT_HOMED (power on, not yet homed)
  25  HOMING (homing sequence)
  30  IDLE_HOMED (homing complete, waiting for a move)
  40  MOVING_ABS
  41  MOVING_REL
  42  JOGGING
  50  HALTING (smooth stop)
  90  STOPPING (emergency stop, ramp)
  99  ERROR

MANDATORY INTERFACE:
VAR_INPUT
  in_bEnable, in_bReset, in_bManualMode      : Bool
  in_bHomeReq                                 : Bool
  in_bMoveAbsReq                              : Bool
  in_bMoveRelReq                              : Bool
  in_bJogPosReq, in_bJogNegReq                : Bool
  in_bHaltReq                                 : Bool
  in_bStopReq                                 : Bool
  in_rTargetPosition                          : Real    -- mm or degrees
  in_rRelativeDistance                        : Real
  in_rVelocity                                : Real
  in_rAcceleration                            : Real
  in_rDeceleration                            : Real
  in_rJerk                                    : Real := 0.0
  in_nHomingMode                              : Int := 0  -- TIA standard homing modes

VAR_IN_OUT
  inout_axis                                  : TO_PositioningAxis

VAR_OUTPUT
  out_bReady                                  : Bool   -- power + homed
  out_bEnabled                                : Bool   -- power on
  out_bHomed                                  : Bool
  out_bMoving                                 : Bool
  out_bDone                                   : Bool   -- last command complete
  out_bError                                  : Bool
  out_wErrorCode                              : Word
  out_nState                                  : Int
  out_rActualPosition                         : Real
  out_rActualVelocity                         : Real

ERROR CODES:
  16#0001 = MC_Power error
  16#0002 = MC_Home error
  16#0003 = MC_MoveAbsolute error
  16#0004 = Manual/Auto conflict
  16#0005 = E-stop
  16#0010 = Move requested before homing
  16#0011 = Multiple moves requested simultaneously
  16#0012 = Target position out of software limits
  16#0013 = Velocity exceeds axis limits
  16#0014 = Axis follow error too high

OUTPUT:
1. Complete SCL code (instantiating the MC_* blocks)
2. Instance usage example
3. Test scenarios (minimum 8)
4. NOTE: TO configuration must be done in the TIA Portal Technology view
```

---

## 4. User Prompt Template

```
TASK: Generate a control FB for the servo axis below.

AXIS INFO:
- Axis tag        : <AX_LOC_NUM>                # e.g.: AX_ST01_001 → MOT_AX01_001_SERVO
- Drive brand     : <SINAMICS V90 / S210 / etc.>
- Position unit   : <mm / degrees / pulses>
- Motion range    : <min> – <max>               # software limits
- Max speed       : <unit/s>
- Max acceleration: <unit/s²>
- Homing mode     : <External cam / Endless / Direct etc.>
- Buffer mode     : <Aborting / Buffered>       # usually Aborting

FEATURES:
- Jog mode        : <Yes / No>
- Multi-target    : <Yes / No>                  # multiple positions
- Manual mode     : <Yes / No>

OUTPUT: Complete SCL code following the GLOBAL_FB_TEMPLATE.scl structure.
```

---

## 5. Expected FB Name

`FB_MOTOR_SERVO_AXIS`

---

## 6. Validation Checklist

- [ ] The `inout_axis : TO_PositioningAxis` parameter exists
- [ ] MC_Power, MC_Home, MC_MoveAbsolute, MC_Halt, MC_Reset instances are under VAR
- [ ] Each move command is triggered on a rising edge (`s_b<Cmd>EdgeMem`)
- [ ] Absolute move blocked until homing completes (transition to 40 before state 30 is forbidden)
- [ ] Software limit check is in the FB, before the move starts
- [ ] Multiple move commands at the same time → error 16#0011
- [ ] out_bEnabled is computed from the MC_Power.Status feedback
- [ ] out_bHomed from axis.StatusBits.HomingDone
- [ ] The specific error code is set from MC_*.Error

---

## 7. Typical AI Errors

- ⚠️ The AI sometimes leaves MC_Power permanently TRUE — acceptable, but it must be documented (Continuous Mode).
- ⚠️ The Execute parameter is given as a level → the block runs once, and without noticing the AI gets CommandAborted. A rising edge is mandatory.
- ⚠️ The Buffer mode parameter is skipped — default Aborting. If queued motion is not wanted, write Aborting explicitly.
- ⚠️ It tries to check software limits in the FB instead of the TO. **They must be in the TO**, the FB only verifies.
- ⚠️ The "Done" signal is a level → TRUE for one scan. Expecting it to stay TRUE is wrong.

---

## 8. Important Note

This FB requires an **S7-1500T** or **S7-1500 with Motion Control** CPU. The standard S7-1500 / S7-1200 has no TO_PositioningAxis — alternative: SINAMICS DriveLib FBs (Telegram-based, close to the VFD prompt).

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0: TO_PositioningAxis-based control for servo motors. Single-axis scope.*
