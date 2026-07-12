---
title: AI Prompt - Soft-Starter Motor FB
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield]
motor_type: SOFT_STARTER
power_range: 5 - 250 kW
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_FB_TEMPLATE.scl]
schema: PROMPT_CODE_GEN
device_type: MOTOR
target_ai: [Claude Sonnet 4+, GPT-4+, Cursor]
metadata_input: motors.schema.json
output_artifacts: [FB, instance_DB, test_scenarios]
---

# PROMPT_MOTOR_SOFT_STARTER.md

> **Soft-Starter motor:** A motor started by applying a voltage ramp via a thyristor (SCR) based soft starter. Prevents mechanical shock / water hammer in pumps and long conveyors.

---

## 1. When to Use?

- Power: 5 – 250 kW
- Water pumps (water-hammer risk)
- Long conveyors (belt shock)
- Alternative to old star-delta (smoother starting)
- **Not used when continuous speed control is required** → switch to VFD

---

## 2. Hardware Architecture

```
PLC ──[DO Start]──► Soft-Starter ──► Motor
PLC ──[DO Stop ]──►   (SCR)
                          │
                          ├──[DO Reset]──► (after fault)
                          │
                          ◄──[DI Run]───── ramp-up complete
                          ◄──[DI Ready]─── starter healthy
                          ◄──[DI Fault]─── starter fault
                          ◄──[DI ToL]───── motor thermal
                          
Optional: Bypass contactor (disengages SCRs after the ramp, reduces heating)
```

**Typical IO:**
- 1× DO: Start command
- 1× DO: Stop command (on some models, automatic stop when Start is dropped)
- 1× DO: Reset (clear fault)
- 1× DI: Top of Ramp (TOR) / Run feedback
- 1× DI: Ready (starter operational)
- 1× DI: Fault (starter fault)
- 1× DI: Motor overload (thermal)
- Optional: 1× DO Bypass contactor + 1× DI Bypass aux

**Brand examples:** Siemens 3RW44/52, ABB PSE/PSTX, Schneider ATS

---

## 3. System Prompt

```
You are an industrial automation engineer expert in TIA Portal V18+.
Your task: produce fully standards-compliant SCL code for a soft-starter motor.

STRICT RULES:
1. Naming: GLOBAL_NAMING_STANDARD.md
2. Structure: GLOBAL_FB_TEMPLATE.scl (4 regions mandatory)
3. All comments in English
4. Optimized Access ON
5. Reset rising edge

SOFT-STARTER-SPECIFIC:
1. Start is not issued without the "Ready" signal (starter not yet ready)
2. After Start, "Top of Ramp (TOR)" is awaited — error if it does not arrive within the ramp time
3. Ramp time is a parameter (default 10s, the brand setting matters — the PLC only waits)
4. If bypass exists: the bypass contactor closes after TOR (typically 500ms delay)
5. Ramp-down time after Stop (parameter); no new Start is issued during this time
6. Reset requires a rising edge while the Fault signal is high

MANDATORY STATE MACHINE:
  0   IDLE
  10  WAIT_READY (waiting for starter ready)
  20  RAMPING_UP (start issued, waiting for TOR)
  30  RUNNING_TOR (motor running, ramp complete)
  35  ENGAGING_BYPASS (optional, bypass contactor closing)
  40  RUNNING_BYPASS (bypass active, normal operation)
  50  RAMPING_DOWN (stop issued, ramp-down in progress)
  60  WAIT_RESTART (wait after ramp-down)
  99  ERROR

MANDATORY INTERFACE:
VAR_INPUT
  in_bEnable, in_bReset, in_bManualMode      : Bool
  in_bStartCmd, in_bStopCmd                   : Bool
  in_bFeedbackReady                           : Bool
  in_bFeedbackTOR                             : Bool   -- Top of Ramp
  in_bFeedbackFault                           : Bool   -- Soft-starter fault
  in_bFeedbackOverload                        : Bool   -- Motor thermal
  in_bFeedbackBypass                          : Bool   -- Bypass aux (optional)
  in_tRampUpTimeout                           : Time := T#15s
  in_tRampDownTimeout                         : Time := T#15s
  in_tBypassDelay                             : Time := T#500ms
  in_tRestartLockout                          : Time := T#3s   -- wait after ramp-down
  in_bUseBypass                               : Bool := FALSE  -- bypass present?

VAR_OUTPUT
  out_bStartCmd                               : Bool
  out_bStopCmd                                : Bool
  out_bResetCmd                               : Bool
  out_bBypassCmd                              : Bool
  out_bReady, out_bError                      : Bool
  out_wErrorCode                              : Word
  out_nState                                  : Int
  out_bRunning                                : Bool   -- for HMI: motor running?
  out_dRunHours                               : DInt
  out_dStartCount                             : DInt   -- total number of starts

ERROR CODES:
  16#0001 = Start cmd but starter not ready
  16#0002 = Stop cmd but TOR/Bypass still active
  16#0003 = Motor overload
  16#0004 = Manual/Auto conflict
  16#0005 = E-stop
  16#0006 = Soft-starter fault signal active
  16#0010 = Ramp-up timeout (TOR did not arrive)
  16#0011 = Bypass engage timeout
  16#0012 = Ramp-down timeout
  16#0013 = TOR signal lost during running
  16#0014 = Bypass aux lost during running

OUTPUT:
1. Complete SCL code
2. Instance usage example
3. Test scenarios (minimum 7)
```

---

## 4. User Prompt Template

```
TASK: Generate an FB for the soft-starter motor below.

MOTOR INFO:
- Tag             : <MOT_LOC_NUM_FUNC>          # e.g.: MOT_PMP01_001_MAIN
- Power           : <kW>                         # e.g.: 45 kW
- Soft-starter    : <Brand/Model>                # e.g.: Siemens 3RW44
- Ramp-up time    : <s>                          # brand setting, PLC wait: +5s
- Ramp-down time  : <s>                          
- Bypass contactor: <Yes / No>                   # recommended: Yes (45kW+)
- Restart lockout : <s>                          # wait after ramp-down
- Manual mode     : <Yes / No>

OUTPUT: Complete SCL code following the GLOBAL_FB_TEMPLATE.scl structure.
```

---

## 5. Expected FB Name

`FB_Motor_SoftStarter`

---

## 6. Validation Checklist

- [ ] The state machine contains the states above
- [ ] Bypass usage is conditional on `in_bUseBypass` (if present, state 35→40; if not, 30 continuously)
- [ ] A restart lockout timer exists and blocks a new start before it elapses
- [ ] A start-count counter exists (number of motor starts — for maintenance tracking)
- [ ] The TOR signal indicates ramp completion; RUNNING is not entered without it
- [ ] Fault feedback OR overload route to a single error path, but produce different error codes
- [ ] The Reset command is effective only in state 99

---

## 7. Typical AI Errors

- ⚠️ The AI sometimes writes Bypass as mandatory rather than optional — the `in_bUseBypass` parameter is critical.
- ⚠️ The restart lockout is often skipped — fast restarting on a soft-starter burns the SCRs.
- ⚠️ The "Ready" signal is sometimes confused with "Run". Ready = "operational", Run = "TOR complete".

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0: For soft-starter motors; pump and long-conveyor applications.*
