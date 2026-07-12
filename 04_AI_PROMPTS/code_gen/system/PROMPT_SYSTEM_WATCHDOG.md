---
title: AI Prompt - Watchdog/Heartbeat FB
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_FB_TEMPLATE.scl]
status: STUB
---

# PROMPT_SYSTEM_WATCHDOG

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

Watchdog FB:
  - Heartbeat counter (increments every N seconds)
  - Awaiting a heartbeat from HMI/SCADA
  - Comms timeout detection
  - PLC↔PLC heartbeat
  - Master/slave discovery
  - Transition to safe state on timeout

---

## Dependencies

These files must be complete before filling this in:
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
