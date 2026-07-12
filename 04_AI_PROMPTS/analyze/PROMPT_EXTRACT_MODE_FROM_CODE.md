---
title: AI Prompt - Topic Extractor - Operating Modes
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD04_Mode
prerequisite: [MDSCHEMA_RAWDATA_04_MODE.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD04_Mode.xlsx, RD04_Mode_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd04_mode.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_MODE_FROM_CODE.md — Operating Modes Topic Extractor

> **Reads `_parsed.md` and extracts the operating modes into RD04 per the `MDSCHEMA_RAWDATA_04_MODE.md` spec.** Fourth of the 14 extractors. Retrofit only.

---

## 1. When to Use?

- In Pipeline Gate 2, with `_parsed.md` ready, after RD01-RD03 are done
- Fourth of the 14 extractors
- **Retrofit** only

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (Mode DBs + Mode FBs + HMI Mode tags)
[THIS PROMPT — Mode extractor]
     ↓
[RD04_Mode.xlsx]
     ↓ Gate 3 → Gate 5
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_04_MODE.md`.

| Spec | Application |
|---|---|
| ModeID `^M\d{2}$` | M00, M01, M02 |
| Priority 0-99 unique | 0 = Emergency, 99 = lowest |
| PackMLState (OMAC enum) | Stopped/Starting/Execute/Held/Suspended/Aborted, etc. |
| HMI_Color hex format | Mode color coding |
| M00=Emergency Priority=0 | Fixed rule |

---

## 4. System Prompt

```
You are an engineer with expertise in OMAC PackML v3.0, ISA-88 §4.7 and
industrial mode management. Your job: extract the operating modes of the
legacy code from _parsed.md and produce an Excel sheet that conforms to
the MDSCHEMA_RAWDATA_04_MODE.md spec.

SOURCE HINTS (how modes may appear in the legacy code):
  - Symbolic names like "Mode_Auto" / "Mode_Hand" / "Mode_Setup"
  - "CurrentMode" integer inside a DB (1=AUTO, 2=MANUAL, ...)
  - HMI tags named "Modus" / "Operation_Mode"
  - PackML in use: "MachineMode" and "MachineState" are separate
  - Legacy platforms (S5) typically use two modes "Automatik" / "Hand"

STRICT RULES:
1. Do not contradict the spec — 14 columns:
   ModeID, ModeName, Priority, PackMLState, Description, EntryCondition,
   ExitCondition, PermittedActions, RestrictedActions, HMI_Color, HMI_Text,
   DB_ModeWord, Notes, Status
2. ModeID format `^M\d{2}$`:
   - M00 = Emergency (always Priority=0)
   - M01 = AUTO
   - M02 = MANUAL
   - M03 = SETUP / SERVICE
   - M04 = MAINTENANCE
   - M05 = CLEANING
   - M06 = LOCKOUT / LOTO
3. Priority:
   - 0 = highest (M00 Emergency)
   - 1-10 = critical modes
   - 50+ = standard modes
   - UNIQUE per ModeID
4. PackMLState (OMAC v3.0 enum):
   Idle, Starting, Execute, Completing, Complete, Resetting,
   Held, Holding, Suspended, Suspending, Unsuspending, Unholding,
   Stopped, Stopping, Aborted, Aborting, Clearing
5. Description:
   Original mode description (German "Automatik" etc.) AS-IS + English meaning
6. EntryCondition: condition to enter this mode (e.g. "NOT M00 AND Operator_Auto = TRUE")
7. ExitCondition: condition to leave this mode (e.g. "Emergency_Stop = TRUE → M00")
8. PermittedActions: actions allowed in this mode
   - Format: "Start, Stop, Jog, Reset"
9. RestrictedActions: actions FORBIDDEN in this mode
   - Format: "Production_Cycle, Auto_Sequence"
10. HMI_Color: hex format `#RRGGBB`
    - M00 = #FF0000 (red)
    - M01 (AUTO) = #00C800 (green)
    - M02 (MANUAL) = #FFA500 (orange)
    - M03 (SETUP) = #FFFF00 (yellow)
    - M04 (MAINT) = #0080FF (blue)
11. HMI_Text: short text shown on the HMI screen (TR/EN — multi-lang via RD11)
12. DB_ModeWord: variable holding the mode value (RD02 reference)
13. Uncertain → #UNKNOWNS

OUTPUT FORMAT:

```markdown
# RD04_Mode_draft.md

## Summary
- Total modes: <N>
- M00 (Emergency): present ✓
- PackML compliant: <Y/N>

## Modes

| ModeID | ModeName | Priority | PackMLState | Description | EntryCondition | ExitCondition | PermittedActions | RestrictedActions | HMI_Color | HMI_Text | DB_ModeWord | Notes | Status |
|--------|----------|----------|-------------|-------------|----------------|---------------|------------------|-------------------|-----------|----------|-------------|-------|--------|
| M00 | Emergency | 0 | Aborted | Emergency stop (orig: NOT-AUS) | E_Stop = TRUE | Reset_Cmd AND E_Stop = FALSE | Reset | All_Production | #FF0000 | NOT-AUS | gMode.CurrentMode | | Active |
| M01 | Auto | 50 | Execute | Automatic (orig: Automatik) | NOT M00 AND Op_Auto = TRUE | Op_Manual = TRUE OR M00 | Start, Stop, Reset | Manual_Jog | #00C800 | AUTO | gMode.CurrentMode | | Active |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## #UNKNOWNS

| Legacy symbol | Reason |
|---------------|--------|
| ... | ... |
```
```

---

## 5. User Prompt Template

```
TASK: Extract RD04 Operating Modes from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE:
  - PackML in use: <Y/N>
  - Mode count (from operator): <n>
  - Multi-language HMI: <Y/N>

SPECIAL:
  - M00 Emergency Priority=0 is fixed
  - Apply HMI_Color standard
  - Map to OMAC-compliant PackMLState

OUTPUT:
  - RD04_Mode_draft.md
  - #UNKNOWNS
```

---

## 6. Output Validation

- [ ] 14 columns
- [ ] M00 present and Priority=0
- [ ] Priority values are unique
- [ ] PackMLState in OMAC enum
- [ ] HMI_Color hex format `#RRGGBB`
- [ ] ModeID format `^M\d{2}$`

---

## 7. Typical AI Errors

### 7.1 Syntax (Category A)
- ModeID `M1` (not two digits) → reject
- HMI_Color `red` or `#FFF` → must be 6-digit hex

### 7.2 Schema/Standard (Category B)
- M00 Priority ≠ 0 → reject
- Two modes share the same Priority → reject

### 7.3 Semantic (Category C) — manual review
- ⚠️ Legacy code has only AUTO/MANUAL but AI invents 5-6 PackML modes (false positive)
- ⚠️ PackMLState map wrong: "Manual" → should be "Suspended" not "Held" (OMAC v3 correct value)
- ⚠️ HMI_Color non-intuitive (red for M01 AUTO) — violates the convention
- ⚠️ DB_ModeWord variable not in RD02 — cross-reference broken
- ⚠️ Lockout/LOTO mode exists but PermittedActions still allows Reset — safety issue
- ⚠️ Multi-lang HMI_Text written only in English — TR/DE missing

### 7.4 Correction

> "RD04 draft <ModeID>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| ModeID regex | Rule 2 |
| Priority unique | Rule 3 |
| PackML enum | Rule 4 |
| M00 Emergency=0 | Rule 2 + 3 |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_04_MODE.md`
- **Previous:** `PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_SAFETY_FROM_CODE.md`
- **Dependent RDs:** RD02 (DB_ModeWord), RD03 (Step ModeReq), RD11 (HMI multi-lang)

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_MODE_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). v1.2.0 roadmap: recipe-mode linkage, IEC 62264 batch integration.*
