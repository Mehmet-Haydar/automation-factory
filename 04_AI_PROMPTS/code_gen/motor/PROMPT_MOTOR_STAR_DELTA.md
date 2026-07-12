---
title: AI Prompt - Star-Delta Motor FB
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield]
motor_type: STAR_DELTA
power_range: 7.5 - 75 kW
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_FB_TEMPLATE.scl]
schema: PROMPT_CODE_GEN
device_type: MOTOR
target_ai: [Claude Sonnet 4+, GPT-4+, Cursor]
metadata_input: motors.schema.json
output_artifacts: [FB, instance_DB, test_scenarios]
---

# PROMPT_MOTOR_STAR_DELTA.md

> **Star-Delta motor:** A motor started with three contactors (Main, Star, Delta). For large motors that require current limiting.

---

## 1. When to Use?

- Power: 7.5 – 75 kW
- When the mains starting current must be limited
- Typical application: Large fan, compressor, crusher, motors that start unloaded
- **Not suitable for loaded starting** — torque drops to 33% in the star position

---

## 2. Hardware Architecture

```
                ┌─► K_MAIN (main contactor) ──┐
PLC ────────────┤                             ├──► Motor
                ├─► K_STAR (star) ────────────┤
                └─► K_DELTA (delta) ──────────┘

Logic: K_MAIN + K_STAR active → motor runs in star (low current)
        Transition: K_STAR opens, short wait, K_DELTA closes
        Continuous: K_MAIN + K_DELTA active → motor in delta, full power
```

**Critical rules:**
- K_STAR and K_DELTA can **never** be TRUE at the same time (short circuit)
- A **dead-time** is mandatory during the K_STAR-to-K_DELTA transition (default 50-100ms)
- Star duration: the time the motor takes to accelerate (typically 3-10s, depending on motor characteristics)

**Typical IO:**
- 3× DO: Main, Star, Delta contactors
- 2× DI: Run feedback (usually Main and Delta aux)
- 1× DI: Thermal / overload

---

## 3. System Prompt

```
You are an industrial automation engineer expert in TIA Portal V18+.
Your task: produce fully standards-compliant SCL code for a star-delta motor.

STRICT RULES:
1. Naming: GLOBAL_NAMING_STANDARD.md
2. Structure: GLOBAL_FB_TEMPLATE.scl (4 regions mandatory)
3. All comments in English
4. Optimized Access ON
5. Reset rising edge

STAR-DELTA-SPECIFIC — CRITICAL:
1. K_STAR and K_DELTA can NEVER be TRUE at the same time (software interlock)
2. Transition order: K_STAR OFF → wait t_DeadTime → K_DELTA ON
3. Dead-time minimum 50ms (default 100ms, depending on contactor pickup time)
4. Transition to delta is forbidden before the star duration completes
5. Returning to star after switching to delta is forbidden (requires manual reset)
6. K_MAIN stays active throughout the entire run

MANDATORY STATE MACHINE (must match the curated library block FB_Motor_StarDelta.scl):
  0   IDLE
  10  STAR phase (K_MAIN + K_STAR ON, accelerating)
  15  STAR_OPENING (K_STAR commanded OFF, wait for star aux to confirm physical open)
  20  DEAD TIME (star off, delta not yet on)
  30  DELTA_RUNNING (K_MAIN + K_DELTA ON, normal operation)
  35  DELTA_STOPPING (verify delta contactor opens before returning to IDLE)
  99  FAULT

MANDATORY INTERFACE:
VAR_INPUT
  in_bEnable, in_bReset, in_bManualMode      : Bool
  in_bStartCmd, in_bStopCmd                   : Bool
  in_bManualStart, in_bManualStop             : Bool
  in_bFeedbackMain                            : Bool   -- Main contactor NC aux
  in_bFeedbackDelta                           : Bool   -- Delta contactor NC aux (TRUE = delta CLOSED)
  in_bFeedbackStar                            : Bool   -- Star contactor NC aux (TRUE = star OPEN = safe)
                                                       --   REQUIRED for welded-star detection (step 15 / 16#0020)
  in_bFeedbackOverload                        : Bool
  in_tStarDuration                            : Time := T#5s    -- star duration
  in_tDeadTime                                : Time := T#100ms -- transition dead-time
  in_tStartTimeout                            : Time := T#3s
  in_tStopTimeout                             : Time := T#5s

VAR_OUTPUT
  out_bMain, out_bStar, out_bDelta            : Bool
  out_bReady, out_bError                      : Bool
  out_wErrorCode                              : Word
  out_nState                                  : Int    -- current state for HMI (0/10/15/20/30/35/99)
  out_dRunHours                               : DInt

ERROR CODES (must match FB_Motor_StarDelta.scl):
  16#0001 = Main contactor — no feedback within start timeout
  16#0003 = Overload tripped
  16#0010 = STAR and DELTA feedback both ON (catastrophic — stop immediately)
  16#0011 = Transition timeout (DELTA feedback not arriving)
  16#0012 = Delta contactor welded (delta aux still closed after stop command)
  16#0020 = Star contactor stuck closed (star aux did not confirm open — welded-star)

OUTPUT:
1. Complete SCL code
2. Instance usage example
3. Test scenarios (at least 7 — including the critical star-delta transitions)
```

---

## 4. User Prompt Template

```
TASK: Generate an FB for the star-delta motor below.

MOTOR INFO:
- Tag             : <MOT_LOC_NUM_FUNC>
- Power           : <kW>                       # e.g.: 22 kW
- Star duration   : <s>                        # per motor characteristics, default 5s
- Dead-time       : <ms>                       # default 100ms
- Manual mode     : <Yes / No>

FEEDBACK:
- Main contactor aux  : <Yes / No>             # recommended: Yes
- Delta contactor aux : <Yes / No>             # required for welded-delta detection (16#0012)
- Star aux            : <Yes / No>             # REQUIRED — welded-star detection (step 15 / 16#0020)
                                               #   Without it the safety check cannot detect a
                                               #   star contactor that fails to open before delta.

OUTPUT: Complete SCL code following the GLOBAL_FB_TEMPLATE.scl structure.
```

---

## 5. Expected FB Name

`FB_Motor_StarDelta`

---

## 6. Validation Checklist

- [ ] The state machine has the 7 states above (0/10/15/20/30/35/99)
- [ ] The `out_bStar` and `out_bDelta` outputs can **never** be TRUE together **by code path**
- [ ] Stop/disable guard in steps 10 and 20 uses **ELSE** — the energising
      assignment must NOT run unconditionally after the guard `END_IF`
      (otherwise the contactors are re-energised in the same scan)
- [ ] The dead-time TON instance is under VAR, not in VAR_TEMP
- [ ] Catastrophic check: `IF #in_bFeedbackStar = FALSE AND #in_bFeedbackDelta THEN error 16#0010`
      (star still closed while delta closed)
- [ ] Welded-star check (step 15): star aux must confirm OPEN before dead time;
      timeout → error 16#0020
- [ ] Overload checked in every state (10–30), error → force to 99
- [ ] In the stopping state, **all 3 contactors** OFF at the same time (not sequentially)

---

## 7. Typical AI Errors

- ⚠️ The AI sometimes opens K_DELTA without closing K_STAR (short-circuit code). A state machine is mandatory.
- ⚠️ It may implement the dead-time with a counter/scan-cycle instead of a timer. **Always TON.**
- ⚠️ Transition to delta before the star duration elapses is sometimes done off a "Done" signal — wrong. Duration + feedback are two combined conditions.

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0: For star-delta motors; medium-to-large motors requiring current limiting.*
