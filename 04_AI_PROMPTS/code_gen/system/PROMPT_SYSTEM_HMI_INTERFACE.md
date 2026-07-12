---
title: AI Prompt - HMI Interface DB
version: 0.1.1
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_DB_TEMPLATE.scl, DOMAIN_HMI_STANDARD.md]
status: STUB
---

# PROMPT_SYSTEM_HMI_INTERFACE

> **Status:** 🚧 STUB — this file will be filled in per the sprint plan.

---

## Will Contain

PLC↔HMI interface DB:
  - A single global DB: DB_HMI_INTERFACE
  - Regions: status (PLC→HMI), commands (HMI→PLC), parameters (bidirectional)
  - Tag conventions (the name shown on the HMI)
  - Data types: in a form the HMI can read (Word, Real, String)

---

## Dependencies

These files must be complete before filling this in:
- `GLOBAL_DB_TEMPLATE.scl`
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
