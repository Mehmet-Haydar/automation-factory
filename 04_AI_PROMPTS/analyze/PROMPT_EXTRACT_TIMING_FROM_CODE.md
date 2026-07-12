---
title: AI Prompt - Topic Extractor - Timing
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD07_Timing
prerequisite: [MDSCHEMA_RAWDATA_07_TIMING.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD07_Timing.xlsx, RD07_Timing_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd07_timing.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_TIMING_FROM_CODE.md — Timing Topic Extractor

> **Reads `_parsed.md` and extracts timer usage into RD07 per the `MDSCHEMA_RAWDATA_07_TIMING.md` spec.** Seventh of the 14 extractors.

---

## 1. When to Use?

- In Pipeline Gate 2
- Seventh of the 14 extractors

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (T-symbol + Timer instance DB + Timer FB calls)
[THIS PROMPT — Timing extractor]
     ↓
[RD07_Timing.xlsx]
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_07_TIMING.md`.

| Spec | Application |
|---|---|
| TimerID `^TMR_[A-Z0-9]+_\d{3}$` | TMR_HOLD_001 etc. |
| TimerType IEC 61131-3 | TON/TOF/TP/TONR |
| PresetValue T# format | T#3s, T#500ms |
| Function enum | StepDelay / Debounce / Watchdog / Timeout / CycleControl / AlarmFilter / Other |
| IsWatchdog=Y → LinkedAlarm mandatory | Conditional |

---

## 4. System Prompt

```
You are an engineer with expertise in IEC 61131-3 §2.5.2 (timer FBs) and
§6.5.3 (timing semantics). Your job: extract timer usage from _parsed.md.

SOURCE HINTS:
  - Siemens S5: T-symbols (T 1, T 2...) + L S5T#3s + SE/SI/SS/SF
  - Siemens S7 Classic: T-symbols + IEC timer SFB (TON/TOF/TP)
  - Siemens TIA: IEC_TIMER instance DB
  - CODESYS: Standard.TON/TOF/TP, instance call
  - AB Logix: TIMER tag, TON/TOF/RTO instructions

STRICT RULES:
1. Spec — 14 columns:
   TimerID, TimerName, TimerType, PresetValue, Function, TriggerCondition,
   ResetCondition, OutputAction, LinkedStep, LinkedAlarm, DB_Instance,
   IsWatchdog, Notes, Status
2. TimerID format `^TMR_[A-Z0-9]+_\d{3}$`
   - TMR_<category>_<seq>: TMR_HOLD_001, TMR_DEBOUNCE_001, TMR_WD_001
3. TimerType IEC enum:
   - TON: on-delay
   - TOF: off-delay
   - TP: pulse
   - TONR: retentive on-delay
   - Vendor-specific (SE/SF/SS) → closest IEC equivalent + Notes
4. PresetValue: T# format: T#3s, T#500ms, T#1m30s
5. Function:
   - StepDelay: delay between sequence steps (RD03 reference in LinkedStep)
   - Debounce: signal-bounce filter
   - Watchdog: system monitor (IsWatchdog=Y)
   - Timeout: operation time limit (RD08 alarm link)
   - CycleControl: periodic trigger
   - AlarmFilter: alarm-bounce filter
   - Other
6. If IsWatchdog=Y, LinkedAlarm is MANDATORY (AlarmID from RD08)
7. DB_Instance: Timer instance DB name
8. TriggerCondition: condition that drives IN=TRUE
9. ResetCondition: condition that resets the timer (IN=FALSE for TON; manual reset for TONR)
10. OutputAction: what happens when Timer Q=TRUE
11. Uncertain → #UNKNOWNS

OUTPUT FORMAT:

```markdown
# RD07_Timing_draft.md

## Summary
- Total timers: <N>
- TimerType: TON <n>, TOF <n>, TP <n>, TONR <n>
- Function: StepDelay <n>, Debounce <n>, Watchdog <n>, ...
- Watchdog timers: <n_wd>

## Timers

| TimerID | TimerName | TimerType | PresetValue | Function | TriggerCondition | ResetCondition | OutputAction | LinkedStep | LinkedAlarm | DB_Instance | IsWatchdog | Notes | Status |
|---------|-----------|-----------|-------------|----------|------------------|----------------|--------------|------------|-------------|-------------|-----------|-------|--------|
| TMR_HOLD_001 | Step10_Hold | TON | T#3s | StepDelay | Step S010 active | Step S010 inactive | Allow transition to S020 | S010 | | DB_TMR_001 | N | Tank fill hold time | Active |
| TMR_WD_001 | Comm_Watchdog | TON | T#1s | Watchdog | Comm_HeartbeatLost | Comm_HeartbeatOK | Trigger ALM0042 | | ALM0042 | DB_TMR_002 | Y | PROFINET WD | Active |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## #UNKNOWNS
| Legacy timer | Reason |
|--------------|--------|
| ... | ... |
```
```

---

## 5. User Prompt Template

```
TASK: Extract RD07 Timing from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md

SPECIAL:
  - If legacy S5/S7 Classic timers (SE/SI/SF) present, map to nearest IEC equivalent and keep the original in Notes
  - Watchdog timers must include a LinkedAlarm reference

OUTPUT:
  - RD07_Timing_draft.md
```

---

## 6. Output Validation

- [ ] TimerID format
- [ ] TimerType IEC enum
- [ ] PresetValue T# format
- [ ] IsWatchdog=Y → LinkedAlarm populated

---

## 7. Typical AI Errors

### 7.1 Syntax
- PresetValue `3 sec` → spec requires `T#3s`
- TimerID `tmr_001` lowercase → reject

### 7.2 Schema/Standard
- IsWatchdog=Y but LinkedAlarm empty → conditional reject

### 7.3 Semantic (C)
- ⚠️ S5 SE (Time-as-pulse Extended) confused with TON (different semantics)
- ⚠️ TONR (retentive) confused with TON — reset behavior differs
- ⚠️ Debounce timer mistaken for StepDelay (cycle dependency wrong)
- ⚠️ Watchdog timer detection is weak — comm/process watchdogs get missed
- ⚠️ Same-name (multi-instance) timers collapse into one row (each instance must be a separate record)
- ⚠️ Timer preset read from a DB variable → AI writes a static value; should be left blank with the source noted in Notes

### 7.4 Correction

> "RD07 draft <TMRxxx>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| TimerID regex | Rule 2 |
| TimerType IEC | Rule 3 |
| IsWatchdog → LinkedAlarm | Rule 6 |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_07_TIMING.md`
- **Previous:** `PROMPT_EXTRACT_MOTION_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_ALARM_FROM_CODE.md`
- **Dependent RDs:** RD03 (LinkedStep), RD08 (LinkedAlarm)
- **Standards:** IEC 61131-3 §2.5.2, §6.5.3

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_TIMING_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). v1.2.0 roadmap: S5 SE/SI/SS/SF semantic mapping table, AB RTO retentive behavior.*
