---
title: AI Prompt - Analog Scaling FB
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_NAMING_STANDARD.md]
status: STUB
---

# PROMPT_PROCESS_ANALOG_SCALING

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

Analog scaling:
  - 4-20mA raw (5530-27648) → engineering unit
  - 0-10V raw → unit
  - RTD/TC raw → °C
  - Wire-break detection (NAMUR NE43)
  - Out-of-range detection
  - Filtering (low-pass, default disabled)

---

## Dependencies

These files must be complete before filling this in:
- `GLOBAL_NAMING_STANDARD.md`

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
