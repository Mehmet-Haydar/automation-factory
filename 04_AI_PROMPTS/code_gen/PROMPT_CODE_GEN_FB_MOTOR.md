---
title: AI Prompt Router - Motor Code Generation
version: 2.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield]
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_FB_TEMPLATE.scl]
target_ai: [Claude Sonnet 4+, GPT-4+, Cursor]
role: router
---

# PROMPT_CODE_GEN_FB_MOTOR.md — Router

> **This is a router file.** It is not given to the AI on its own. It routes you to the correct sub-prompt based on the motor type.

---

## 1. Motor Type Decision Tree

```
What is your motor starting method?
│
├─ Does it start directly with a 400V contactor?
│  └─ → motor/PROMPT_MOTOR_DOL.md
│
├─ Star-delta transition (high power, current limiting)?
│  └─ → motor/PROMPT_MOTOR_STAR_DELTA.md
│
├─ With a soft-starter (ramp, water-hammer protection)?
│  └─ → motor/PROMPT_MOTOR_SOFT_STARTER.md
│
├─ With a frequency drive (VFD, variable speed)?
│  └─ → motor/PROMPT_MOTOR_VFD.md
│
└─ Servo motor (position control)?
   └─ → motor/PROMPT_MOTOR_SERVO.md
```

---

## 2. Which Type for Which Situation?

| Type | Typical Power | Typical Application |
|------|---------------|---------------------|
| **DOL** | < 7.5 kW | Conveyor, fan, small pump |
| **Star-Delta** | 7.5 – 75 kW | Large fan, compressor, crusher |
| **Soft-Starter** | 5 – 250 kW | Pump (water hammer), long conveyor |
| **VFD** | Any power | Variable speed: conveyor, pump, fan |
| **Servo** | < 30 kW | Position: axis, indexing |

---

## 3. Common Structure in All Motor FBs

`GLOBAL_FB_TEMPLATE.scl` is mandatory — 4 regions, error code Word/hex, rising edge reset, operating-hours counter, feedback watchdog.

**Common error codes (across all motor types):**

| Code | Meaning |
|------|---------|
| `16#0001` | Start command but no run feedback within timeout |
| `16#0002` | Stop command but feedback still active |
| `16#0003` | Overload / motor protection triggered |
| `16#0004` | Manual/Auto mode conflict |
| `16#0005` | Emergency stop active |
| `16#0006` | Feedback signal anomaly (chatter) |

Type-specific error codes `16#0010+` are defined in the sub-prompts.

---

## 4. Usage

1. Determine the motor type from the decision tree
2. Open the relevant `motor/PROMPT_MOTOR_<TYPE>.md` file
3. Copy the System Prompt + User Template there and give it to the AI

---

## 5. Adding a New Motor Type

If you encounter a new motor type in the field (e.g., Dahlander 2-speed):

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/code_gen/motor/" \
  --reason "No prompt for pole-changing motor" \
  --suggestion "PROMPT_MOTOR_DAHLANDER.md should be added"
```

---

*v2.1.0 — Full English body (2026-05-23). v2.0.0: Restructured as a router; motor types separated out.*
