---
title: AI Prompt - OB1 (Cyclic Main)
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_OB_TEMPLATE.scl, GLOBAL_AI_INTERFACE.md]
status: STUB
---

# PROMPT_OB_MAIN_OB1

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

Prompt for generating OB1:
  - Call all FB instances in order
  - Call order: (1) Mode manager (2) Watchdog (3) IO mapping (4) Motor FBs (5) Valve FBs (6) Sequence (7) HMI interface (8) Diagnostics
  - Each group in a separate REGION
  - Cycle time monitoring (RUNTIME instruction)
  - Stop condition: if emergency stop is high, disable all motor FBs
Input: generated FB list from PROJECT_STATE.json
Output: OB1.scl

---

## Dependencies

These files must be complete before filling this in:
- `GLOBAL_OB_TEMPLATE.scl`
- `GLOBAL_AI_INTERFACE.md`

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
