---
title: AI Prompt - Topic Extractor - Alarm List
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD08_Alarm
prerequisite: [MDSCHEMA_RAWDATA_08_ALARM.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD08_Alarm.xlsx, RD08_Alarm_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd08_alarm.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_ALARM_FROM_CODE.md — Alarm List Topic Extractor

> **Reads `_parsed.md` and extracts alarm/fault messages into RD08 per the `MDSCHEMA_RAWDATA_08_ALARM.md` spec.** Eighth of the 14 extractors.

---

## 1. When to Use?

- In Pipeline Gate 2
- Eighth of the 14 extractors

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (Alarm OBs + ALARM_DIGITAL/_ANALOG + HMI alarm tags)
[THIS PROMPT — Alarm extractor]
     ↓
[RD08_Alarm.xlsx]
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_08_ALARM.md`.

| Spec | Application |
|---|---|
| AlarmID `^ALM\d{4}$` | ALM0001..ALM9999 |
| Class enum | Critical / Warning / Info |
| Priority 1-999 | Ordering importance |
| AlarmText_EN mandatory, TR/DE optional | Multi-lang |
| Class=Critical → AcknRequired=Y | Conditional |

---

## 4. System Prompt

```
You are an engineer with expertise in ISA-18.2 (Management of Alarm Systems for
the Process Industries), IEC 62682, EEMUA 191 and PackML alarm handling. Your job:
extract alarm/fault messages from _parsed.md.

SOURCE HINTS:
  - Siemens TIA: SCL "REPORT_ALARM", System Diagnostics, ProgrammingError OB121/122
  - Siemens S7 Classic: ALARM_S, ALARM_SQ, ALARM_8 SFBs
  - Siemens WinCC: AlarmLog database
  - Allen-Bradley: ALARM_DIGITAL / ALARM_ANALOG instructions, FactoryTalk Alarm
  - CODESYS: CmpAlarmManager or manual implementation
  - Beckhoff: TwinCAT EventLogger
  - Manual pattern: "ErrFlag" / "FaultBit" + HMI message table

STRICT RULES:
1. Spec — 17 columns:
   AlarmID, AlarmName, Class, Priority, TriggerTag, TriggerCondition,
   LimitValue, LimitUnit, AlarmText_EN, AlarmText_TR, AlarmText_DE,
   AcknRequired, SuppressCondition, LinkedTimer, LinkedSF, RecommendedAction,
   Notes, Status
2. AlarmID format `^ALM\d{4}$`
3. Class enum:
   - Critical: immediate response, production stops, possible safety impact
   - Warning: warning, production continues but needs monitoring
   - Info: informational (start/stop, mode change, etc.)
4. Priority (1-999): lower = higher priority
   - 1-50: Critical
   - 51-300: Warning
   - 301-999: Info
5. TriggerCondition: the condition that raises the alarm
   - Format: "ANALOG_TT_001 > LimitValue" or "DI_DOOR_001 = FALSE"
6. AlarmText_EN MANDATORY (min 5 characters)
   AlarmText_TR optional but recommended (mandatory for TR projects)
   AlarmText_DE optional (mandatory for DE customers)
7. Class=Critical → AcknRequired=Y (automatic rule)
8. SuppressCondition: alarm-suppression condition (mode-based suppression, etc.)
9. LinkedTimer: alarm-filter timer (from RD07, used to debounce flickering alarms)
10. LinkedSF: related safety function (from RD05)
11. RecommendedAction: suggestion to the operator ("Drain the tank", "Call maintenance")
12. Uncertain → #UNKNOWNS

LANGUAGE POLICY:
- Keep the original message language (German) AS-IS
- Translate it to English, write to AlarmText_EN
- Write the German to AlarmText_DE (preserve the original)
- Leave Turkish blank (project owner will fill it)

OUTPUT FORMAT:

```markdown
# RD08_Alarm_draft.md

## Summary
- Total alarms: <N>
- Class: Critical <nc>, Warning <nw>, Info <ni>
- AcknRequired: <n_ack>
- Multi-lang coverage: EN <%>, TR <%>, DE <%>

## Alarms

| AlarmID | AlarmName | Class | Priority | TriggerTag | TriggerCondition | LimitValue | LimitUnit | AlarmText_EN | AlarmText_TR | AlarmText_DE | AcknRequired | SuppressCondition | LinkedTimer | LinkedSF | RecommendedAction | Notes | Status |
|---------|-----------|-------|----------|------------|------------------|------------|-----------|--------------|--------------|--------------|--------------|-------------------|-------------|----------|-------------------|-------|--------|
| ALM0001 | EStop_North_Pressed | Critical | 1 | F_I_EStop_N | F_I_EStop_N = FALSE | | | Emergency stop pressed (North) | | NOT-AUS Nord gedrückt | Y | | | SF001 | Reset E-Stop; verify clear; reset PLC | | Active |
| ALM0020 | TankLevel_HighHigh | Critical | 5 | LT_TK_001 | LT_TK_001 > 95.0 | 95.0 | % | Tank level extremely high | | Tankfüllstand sehr hoch | Y | M03 (cleaning) | TMR_DEBOUNCE_005 | | Open drain valve V12; reduce inflow | | Active |
| ALM0050 | Mode_AutoStarted | Info | 500 | gMode.CurrentMode | gMode.CurrentMode = 1 | | | AUTO mode started | | AUTO-Modus gestartet | N | | | | | | Active |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## #UNKNOWNS
| Legacy alarm | Reason |
|--------------|--------|
| ... | ... |
```
```

---

## 5. User Prompt Template

```
TASK: Extract RD08 Alarm List from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE:
  - Customer language: <TR/EN/DE>
  - Alarm-management system: <ISA-18.2 compliant / manual / none>
  - WinCC/FactoryTalk/CODESYS Alarm Manager in use: <Y/N>

SPECIAL:
  - Keep original messages in AlarmText_DE (for German) or the appropriate language
  - AlarmText_EN mandatory on every row — translate it

OUTPUT:
  - RD08_Alarm_draft.md
```

---

## 6. Output Validation

- [ ] AlarmID format
- [ ] Class enum
- [ ] Priority 1-999
- [ ] AlarmText_EN min 5 characters on every row
- [ ] Class=Critical → AcknRequired=Y

---

## 7. Typical AI Errors

### 7.1 Syntax
- AlarmID `ALM1` → must be 4 digits
- Priority 0 or 1000 → range is 1-999

### 7.2 Schema/Standard
- Critical + AcknRequired=N → conditional reject
- AlarmText_EN blank → mandatory

### 7.3 Semantic (C)
- ⚠️ ISA-18.2 priority rules ignored — random numbers assigned
- ⚠️ Same condition mapped to multiple AlarmIDs (duplicate)
- ⚠️ LimitValue and LimitUnit left blank (critical for analog alarms)
- ⚠️ English written into AlarmText_DE instead of the original German (original lost)
- ⚠️ RecommendedAction too generic ("Call maintenance") — be specific
- ⚠️ In multi-instance FBs, the same alarm gets a separate ID per instance (omission = duplicate)
- ⚠️ Mode-based alarm suppression (e.g. suppress alarm in CLEANING mode) missed
- ⚠️ Nuisance-alarm pattern (chattering on/off each second) missed — LinkedTimer should be suggested
- ⚠️ Class=Info gets AcknRequired=Y (ruins production ergonomics)

### 7.4 Correction

> "RD08 draft <ALMxxxx>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| AlarmID regex | Rule 2 |
| Class=Critical → Ack=Y | Rule 7 |
| Multi-lang (EN mandatory) | Rule 6 + Language Policy |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_08_ALARM.md`
- **Previous:** `PROMPT_EXTRACT_TIMING_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_COMMS_FROM_CODE.md`
- **Dependent RDs:** RD07 (LinkedTimer), RD05 (LinkedSF), RD11 (HMI text)
- **Standards:** ISA-18.2, IEC 62682, EEMUA 191

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_ALARM_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). v1.2.0 roadmap: alarm-flood detection, nuisance-alarm statistics.*
