---
title: AI Prompt - Flowchart vs Code Match
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [MDSCHEMA_RAWDATA_03_FLOWCHART.md, GLOBAL_NAMING_STANDARD.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+]
input_source: RD03_Flowchart.md, generated SCL code (FB_Sequence.scl)
output_artifacts: [flowchart_match_report.md]
role: review
schema: PROMPT_REVIEW
---

# PROMPT_REVIEW_FLOWCHART_MATCH.md — RD03 Flowchart ↔ Code Match Review

> **This prompt compares the RD03 Flowchart spec to the SCL sequence code generated at Gate 5.** It checks design ↔ implementation alignment.

---

## 1. When to Use?

- After Gate 5: an FB_Sequence (or similar state machine) has been generated
- A consistency check between RD03 and the code is required
- Before delivery to the customer (alignment with the FAT plan)

---

## 2. What the AI Checks

✅ Does every StepID correspond to a CASE/IF branch in the code
✅ Is EntryCondition the transition guard in the code
✅ Is ExitCondition the termination guard in the code
✅ Are Actions the output assignments in the code
✅ Are NextStep + ErrorStep the transitions in the code
✅ Is TimerRef the timer instance in the code
✅ Is ModeReq the mode check in the code

---

## 3. System Prompt

```
You are a Flowchart-Code consistency checker. You compare the RD03 spec to the
generated SCL state-machine code.

METHOD:
1. Read the step list from RD03 (S000..S099)
2. Find the CASE OF or SFC step pattern in the SCL code
3. For each step, compare the 7 fields:
   - StepID ↔ code case value
   - EntryCondition ↔ transition guard
   - ExitCondition ↔ next-step guard
   - Actions ↔ output assignments
   - NextStep ↔ state transition
   - ErrorStep ↔ error path
   - TimerRef ↔ TON/TOF instance

OUTPUT:

# flowchart_match_report.md

## Summary
- RD03 step count: <N>
- States in code: <M>
- Matching: <count>
- Mismatching: <count>
- In RD03, missing in code: <count>
- In code, missing in RD03: <count>

## Comparison Table

| StepID | Spec EntryCond | Code Guard | Spec Actions | Code Outputs | Match |
| S010 | Tank_Full | iLevel > 80 | OPEN_VALVE_FILL | VAL_V01_OUT := TRUE | ✓ |
| S020 | (missing) | mModeAuto AND ... | — | — | ✗ code differs |
| S030 | Cycle_Done | (none) | Stop_Pump | — | ✗ code missing |
| ... | ... | ... | ... | ... | ... |

## Gaps

### Present in RD03 but missing in code
- S015 (Wait_Operator) — add to the code or remove from RD03

### Present in code but missing in RD03
- S025 (Buffer_Idle) — add to RD03 or remove from the code

### Action gaps
- S010: RD03 says "Start Pump", code does "Start Pump + Open Valve" — update RD03

## Mermaid Diagram (in-sync view)
\```mermaid
stateDiagram-v2
    ...
\```
```

---

## 4. User Prompt

```
TASK: check the alignment between RD03_Flowchart.md and <project>/03_PLC/SCL/FB_Sequence.scl.

PROJECT: <project_name>
SCL file: <path>

CONSTRAINT: the spec ↔ code mapping must be objective — do not assume.

OUTPUT: flowchart_match_report.md
```

---

## 5. Common Pitfalls

- A step is added to the code but RD03 is not updated
- A step exists in RD03 but is not implemented in code
- Actions differ (1 output in RD03, 3 outputs in code)
- ErrorStep defined in RD03 but no error handler in code
- TimerRef defined in RD03 but a different timer instance in code

---

## 6. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_03_FLOWCHART.md`
- **Pipeline:** after Gate 5, before Gate 6
- **Code gen:** `PROMPT_CODE_GEN_SEQUENCE.md`

---

*v1.1.0 — Full English body (2026-05-23). Flowchart ↔ code match = document ↔ reality. The accuracy check for customer presentations.*
