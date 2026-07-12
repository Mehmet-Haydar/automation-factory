---
title: AI Prompt - OB86 (Rack/Station Failure)
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_OB_TEMPLATE.scl]
status: STUB
---

# PROMPT_OB_RACK_FAILURE_OB86

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

Prompt for generating OB86 (rack/IO station failure):
  - Which distributed IO is offline?
  - Move the motor/valve FBs tied to this IO into the 'comm lost' state
  - Alarm to the HMI
  - If in automatic mode → force to safe state

---

## Dependencies

These files must be complete before filling this in:
- `GLOBAL_OB_TEMPLATE.scl`

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
