---
title: AI Prompt - Recipe Manager FB
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_FB_TEMPLATE.scl, GLOBAL_DB_TEMPLATE.scl]
status: STUB
---

# PROMPT_PROCESS_RECIPE_MANAGER

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

Recipe management:
  - Recipe list (DB array)
  - Active recipe (instance)
  - Loading: command from HMI → copy from DB array to active
  - Validation: parameter limit checks
  - Versioning: audit log of recipe changes

---

## Dependencies

These files must be complete before filling this in:
- `GLOBAL_FB_TEMPLATE.scl`
- `GLOBAL_DB_TEMPLATE.scl`

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
