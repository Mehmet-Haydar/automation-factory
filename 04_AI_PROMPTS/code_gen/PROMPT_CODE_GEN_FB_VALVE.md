---
title: AI Prompt Router - Valve Code Generation
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_FB_TEMPLATE.scl]
status: STUB
---

# PROMPT_CODE_GEN_FB_VALVE

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

Valve router (like the motor router):
Decision tree:
  - 2-way on/off solenoid → valve/PROMPT_VALVE_2WAY_ONOFF.md
  - 3-way direction selector → valve/PROMPT_VALVE_3WAY.md
  - Modulating (4-20mA position control) → valve/PROMPT_VALVE_MODULATING.md
  - Servo valve (high dynamic) → valve/PROMPT_VALVE_PROPORTIONAL.md
Common error codes, common interface.

---

## Dependencies

These files must be complete before filling this in:
- `GLOBAL_NAMING_STANDARD.md`
- `GLOBAL_FB_TEMPLATE.scl`

---

## Fill-In Guidance

Open a new chat and paste in:
1. `PROJECT_VISION.md`
2. `SKELETON_BLUEPRINT.md`
3. `PROGRESS_TRACKER.md`
4. This file

Then give the command:
> "Fill in this file. Follow the content definition and dependencies in SKELETON_BLUEPRINT.md. Use existing FILLED files (e.g. PROMPT_MOTOR_DOL.md) as quality and structure references."

---

*v0.1.1 → bump to v1.0.0 when content is filled in.*
