---
title: AI Prompt - OB82 (Diagnostic Interrupt)
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_OB_TEMPLATE.scl]
status: STUB
---

# PROMPT_OB_DIAGNOSTIC_OB82

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

Prompt for generating OB82 (module fault):
  - Which module faulted? (detect from LADDR)
  - Write to DIAG_BUFFER
  - Notify the HMI (alarm)
  - If it is a critical module → stop all motor FBs

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
