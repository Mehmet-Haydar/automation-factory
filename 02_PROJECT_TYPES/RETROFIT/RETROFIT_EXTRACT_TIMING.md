---
title: Retrofit Timing/Watchdog Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD07_Timing
prerequisite: [MDSCHEMA_RAWDATA_07_TIMING.md, RETROFIT_EXTRACT_DATADICT.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_TIMING_FROM_CODE.md
---

# RETROFIT_EXTRACT_TIMING.md — Timing Extraction Procedure

> **Goal:** systematically extract every timer usage in legacy PLC code (TON/TOF/TP/TONR), every watchdog and every cycle controller.

---

## 1. Prerequisites

- [ ] RD03 Flowchart (for StepDelay timer cross-references)
- [ ] RD08 Alarm List draft (LinkedAlarm for watchdogs)
- [ ] Platform timer types known (S5 SE/SI/SF, S7 IEC TON/TOF, AB RTO)
- [ ] Are legacy timer presets hard-coded in the DB or parametric? (parametric vs. fixed)

---

## 2. Workflow

### 2.1 Timer Type Mapping

Legacy platform → IEC 61131-3 equivalent:

| Platform | Legacy Instruction | IEC Equivalent | Notes |
|----------|--------------------|----------------|-------|
| S5 | `SE` (Time-as-pulse Extended) | TP | Extended pulse |
| S5 | `SI` (Time-as-Impulse) | TP | Pulse |
| S5 | `SS` (Time-as-Stored-on-delay) | TONR | Retentive on-delay |
| S5 | `SF` (Time-as-off-delay) | TOF | Off-delay |
| S7 Classic | `S_PULSE` | TP | |
| S7 Classic | `S_PEXT` | TP | (extended) |
| S7 Classic | `S_ODT` | TON | On-delay |
| S7 Classic | `S_ODTS` | TONR | Retentive |
| S7 Classic | `S_OFFDT` | TOF | Off-delay |
| TIA Portal | IEC_TIMER (TON/TOF/TP) | Same | Direct |
| AB Logix | `TON` | TON | |
| AB Logix | `TOF` | TOF | |
| AB Logix | `RTO` | TONR | Retentive |
| CODESYS | `Standard.TON/TOF/TP` | Same | Direct |

### 2.2 Hybrid Workflow

```
[1] _parsed.md + RD03 + RD08 ready
       ↓
[2] AI prompt: PROMPT_EXTRACT_TIMING_FROM_CODE.md
       ↓
[3] RD07_Timing_draft.md
       ↓
[4] Convert legacy timer instructions to IEC (table §2.1)
       ↓
[5] Cycle-time analysis (oscilloscope/PLC trace in the field)
       ↓
[6] Detect watchdogs + add LinkedAlarm
       ↓
[7] RD07_Timing.xlsx (approved)
```

### 2.3 Determining the Function Category

| Function | Typical Marker |
|----------|----------------|
| **StepDelay** | Delay between sequence steps (linked to RD03 StepID) |
| **Debounce** | Signal-chatter filter (usually 50-100 ms, after a DI signal) |
| **Watchdog** | Comm heartbeat, cycle monitoring; alarm if lost |
| **Timeout** | Maximum operation duration (e.g. tank-fill timeout) |
| **CycleControl** | Periodic trigger (e.g. measurement every 1 s) |
| **AlarmFilter** | Alarm-chatter filter (suppress transient conditions) |
| **Other** | None of the above |

### 2.4 Human Review Checklist

#### A. TimerID Format
- [ ] `TMR_<CATEGORY>_<NUM>`, e.g. `TMR_HOLD_001`, `TMR_WD_002`, `TMR_DEBOUNCE_005`
- [ ] Sequential numbering

#### B. PresetValue Format
- [ ] T# format: `T#3s`, `T#500ms`, `T#1m30s`, `T#15h`
- [ ] **Parametric preset:** if the preset is read from the DB, leave PresetValue empty and add "Configurable via DB_xx" to Notes

#### C. Watchdog-Specific Checks
- [ ] LinkedAlarm is MANDATORY on rows where IsWatchdog=Y
- [ ] Watchdog duration reasonable (comm watchdog 100-1000 ms, sequence watchdog 5-60 s)
- [ ] Is there a safe-state transition when the watchdog trips?

#### D. Cycle-Time Optimisation
- [ ] PLC scan cycle is known (e.g. 50 ms)
- [ ] Timer preset cannot be smaller than the cycle (e.g. T#10ms can't be resolved at a 50 ms scan)
- [ ] Cycle-bound critical timers flagged in Notes

#### E. Multi-Instance Separation
- [ ] If a timer FB has multiple instances, each gets a SEPARATE TimerID
- [ ] DB_Instance populated on every row and unique

---

## 3. Field-Discovery Methods

### 3.1 Fast Timer Search in Legacy Code

**Siemens S5/S7 Classic:**
```bash
grep -E "(SE|SI|SS|SF|S_ODT|S_OFFDT|S_PULSE)" *.AWL
grep -E "L S5T#|L T#" *.AWL
```

**TIA Portal SCL:**
```bash
grep -E "IEC_TIMER|TON|TOF|TP|TONR" *.scl
```

**Allen-Bradley:**
```bash
# Inside .L5X
grep -E "TIMER|TON|TOF|RTO" Project.L5X
```

**CODESYS XML:**
```bash
grep -E "Standard\.(TON|TOF|TP)" Project.xml
```

### 3.2 Collecting Preset Values

| Source | Method |
|--------|--------|
| Hard-coded (in code) | Read the code directly |
| Read from DB (parametric) | Online HMI parameter table |
| Changed from HMI | HMI tag-database export |
| Coming from recipe | Recipe parameter list |

### 3.3 Watchdog Detection

Watchdogs are usually written in patterns like these:

```scl
// PROFINET watchdog example
TMR_WD_001(IN := PN_Heartbeat_Lost, PT := T#500ms);
IF TMR_WD_001.Q THEN
    ALARM_TRIGGER(ALM0042);  // Comm lost alarm
END_IF;
```

or alternatively:

```scl
// Sequence watchdog
IF Step_Active AND NOT Step_Timeout THEN
    TMR_WD_002(IN := TRUE, PT := T#60s);
END_IF;
IF TMR_WD_002.Q THEN
    Sequence_Fault := TRUE;
END_IF;
```

---

## 4. Validation

### 4.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD07 \
  --check-watchdog-alarm-link \
  --check-timer-cycle-resolution
```

### 4.2 Manual

| Check | Target |
|-------|--------|
| TimerID regex | `^TMR_[A-Z0-9]+_\d{3}$` |
| PresetValue format | `T#...` |
| Watchdog → LinkedAlarm | Conditional |
| TimerType IEC enum | TON/TOF/TP/TONR |
| Cycle resolution | PT > 2 × cycle time |

---

## 5. Common Pitfalls

- ❌ **Confusing S5 SE with TON:** SE is pulse-extended, TON is on-delay — semantically different. SE → TP (pulse), not TON.
- ❌ **Retentive vs non-retentive:** mixing TONR and TON loses the count on power loss.
- ❌ **One row for a multi-instance timer:** if the same timer FB has 5 instances, you need 5 separate TimerID records.
- ❌ **Variable preset written as constant:** if it is read from the DB, leave PresetValue empty + add "Configurable" to Notes.
- ❌ **Watchdog without LinkedAlarm:** what happens when the watchdog trips becomes unclear → silent failure without AcknRequired.
- ❌ **Mistaking AB RTO for TON:** RTO is retentive, TON is not. Tag type `TIMER` may be the same, but behaviour differs.
- ❌ **Timer too short:** PT=T#5ms cannot be resolved in a 50 ms scan cycle → always appears as either 0 or 50 ms.
- ❌ **Watchdog duration too short:** trips even under normal comm jitter → nuisance alarms.

---

## 6. AI Prompt Suggestion

`04_AI_PROMPTS/analyze/PROMPT_EXTRACT_TIMING_FROM_CODE.md`

AI is particularly weak at watchdog detection — manual verification is critical.

---

## 7. Gate 3 Checklist

- [ ] All timers converted to their IEC equivalents
- [ ] PresetValue in T# format
- [ ] Watchdog timers linked via LinkedAlarm
- [ ] Each multi-instance timer has its own TimerID
- [ ] Cycle-time resolution analysis done
- [ ] Parametric preset values explained in Notes
- [ ] StepDelay timers linked to RD03 StepID (LinkedStep)
- [ ] AlarmFilter timers linked to RD08 AlarmID

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_07_TIMING.md`
- **AI prompt:** `PROMPT_EXTRACT_TIMING_FROM_CODE.md`
- **Previous:** `RETROFIT_EXTRACT_MODE.md`
- **Next:** `RETROFIT_EXTRACT_ALARM.md`
- **Dependent RDs:** RD03 (LinkedStep), RD08 (LinkedAlarm)
- **Standards:** IEC 61131-3 §2.5.2 (timer FB), §6.5.3 (semantics)

---

*v1.1.0 — Full English body (2026-05-23). Missing a watchdog = silent-failure risk. In this procedure manual verification is always added on top of AI output.*
