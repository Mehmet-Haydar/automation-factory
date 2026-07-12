---
title: AI Prompt - Alarm Handler FB
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_FB_TEMPLATE.scl, DOMAIN_HMI_STANDARD.md]
status: STUB
---

# PROMPT_PROCESS_ALARM_HANDLER

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

Alarm management FB:
  - Alarm classes: info, warning, critical
  - Alarm filter (debounce)
  - Acknowledge (ack) logic
  - Alarm history (DTL timestamp + ring buffer)
  - Link to the HMI alarm view
  - Multiple alarms: first-in wins (first-out)

---

## Dependencies

These files must be complete before filling this in:
- `GLOBAL_FB_TEMPLATE.scl`
- `DOMAIN_HMI_STANDARD.md`

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
