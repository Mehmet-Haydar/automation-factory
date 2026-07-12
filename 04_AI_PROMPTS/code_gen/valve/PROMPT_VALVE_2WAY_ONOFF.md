---
title: AI Prompt - 2-Way On/Off Valve FB
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [PROMPT_CODE_GEN_FB_VALVE.md, GLOBAL_FB_TEMPLATE.scl]
status: STUB
---

# PROMPT_VALVE_2WAY_ONOFF

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

2-way on/off valve:
  - Solenoid coil (DO)
  - Open limit switch (DI, optional)
  - Closed limit switch (DI, optional)
  - Command: open/close
  - Feedback timeout (if no limit switch: time-based assume)
  - Error: limit switch conflict (both active)
  - State machine: IDLE/OPENING/OPEN/CLOSING/CLOSED/ERROR

---

## Dependencies

These files must be complete before filling this in:
- `PROMPT_CODE_GEN_FB_VALVE.md`
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
