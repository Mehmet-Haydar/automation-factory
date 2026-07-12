---
title: Retrofit Alarm List Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD08_Alarm
prerequisite: [MDSCHEMA_RAWDATA_08_ALARM.md, RETROFIT_EXTRACT_TIMING.md, GLOBAL_LANG_POLICY.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_ALARM_FROM_CODE.md
---

# RETROFIT_EXTRACT_ALARM.md — Alarm List Extraction Procedure

> **Goal:** extract alarm/fault messages from legacy PLC code and standardise them into an alarm system that complies with ISA-18.2 / IEC 62682 / EEMUA 191.

---

## 1. Prerequisites

- [ ] RD01 IO (for TriggerTag), RD05 Safety (for LinkedSF), RD07 Timing (for LinkedTimer)
- [ ] HMI alarm configuration files (WinCC AlarmLogging.xls, FactoryTalk Alarm.AML, etc.)
- [ ] Customer project language confirmed: TR / EN / DE / multi-lang
- [ ] If available, alarm statistics from the legacy machine (most frequently triggered alarms)

---

## 2. Workflow

### 2.1 Alarm Sources

In legacy projects, alarms can live in three different places:

| Source | Content | Typical file |
|--------|---------|--------------|
| **PLC code** | Alarm trigger logic, ALARM_S/_SQ/_DIGITAL calls | `.awl`, `.scl`, `.L5X` |
| **HMI database** | Alarm texts, classes, colours | `*.AML`, `*.xls`, `*.alarm` |
| **PDF documentation** | Alarm tables inside the operations manual | Customer documents |

### 2.2 Hybrid Workflow

```
[1] _parsed.md + HMI alarm DB + (PDF if any) ready
       ↓
[2] AI prompt: PROMPT_EXTRACT_ALARM_FROM_CODE.md
       ↓
[3] Join HMI alarm texts (alarm trigger ↔ message mapping)
       ↓
[4] RD08_Alarm_draft.md
       ↓
[5] ISA-18.2 priority classification (manual)
       ↓
[6] Multi-lang text translation (project language EN/TR/DE)
       ↓
[7] RD08_Alarm.xlsx (approved)
```

### 2.3 Human Review Checklist

#### A. AlarmID + Format
- [ ] `^ALM\d{4}$` (4 digits)
- [ ] Sequential, no gaps
- [ ] One AlarmID per condition (duplicate check)

#### B. Class Classification (ISA-18.2)
- [ ] **Critical:** immediate response required, production must stop, safety may be involved
- [ ] **Warning:** advisory, production can continue but monitoring required
- [ ] **Info:** status information (mode started, production complete, etc.)

#### C. Priority (1-999)
Suggested ISA-18.2 distribution:

| Priority | Class | Meaning |
|----------|-------|---------|
| 1-10 | Critical | Urgent — the operator should be focused on nothing else |
| 11-50 | Critical/Major | Fast response (within minutes) |
| 51-150 | Warning | Close monitoring (action within hours) |
| 151-300 | Warning/Minor | Standard monitoring |
| 301-999 | Info | Information/log |

#### D. AcknRequired Conditional
- [ ] Class=Critical → AcknRequired=Y (automatic rule, the validator enforces it)
- [ ] Class=Warning → usually Y (do not let it pass unseen)
- [ ] Class=Info → N (do not break flow)

#### E. Multi-Language Text (GLOBAL_LANG_POLICY)
- [ ] AlarmText_EN mandatory on every row (min 5 characters)
- [ ] If the customer is German, AlarmText_DE must be filled
- [ ] For TR projects, AlarmText_TR must be filled
- [ ] If machine-translated, a human must review (terminology)

#### F. TriggerCondition Concreteness
- [ ] Use the symbolic tag name, not an absolute address
- [ ] Comparison operator explicit (`>`, `<`, `>=`, `=`, `<>`)
- [ ] For analog: LimitValue + LimitUnit populated

#### G. SuppressCondition (Mode-Based Suppression)
- [ ] Suppress alarms in Cleaning mode: `gMode.CurrentMode = M05`
- [ ] Suppress some alarms in Setup mode
- [ ] Suppress almost all alarms in LOTO mode (only safety remains)

#### H. LinkedTimer (Debounce / Filter)
- [ ] Add a filter timer for chattering signal alarms (e.g. 500 ms TON)
- [ ] Pick LinkedTimer from RD07 (TMR_DEBOUNCE_xxx)

#### I. LinkedSF (Safety Function)
- [ ] For alarms that trigger a safety function, reference the RD05 SF

#### J. RecommendedAction (Suggestion to the Operator)
- [ ] Specific action ("Drain the tank", "Call maintenance", "Reset pump MOT_PUMP_01")
- [ ] Avoid generic phrases ("Stop the job" is not enough)

---

## 3. Field Discovery and Customer Data

### 3.1 Alarm Statistics (Most Important)

If you can get the alarm log from the legacy machine, it is high-value:

```bash
# WinCC AlarmLog SQL export
# FactoryTalk Alarm History database query
# CODESYS Alarm Manager log file
```

What to look at:
- **Top 10 alarms:** most frequently triggered — nuisance-alarm candidates
- **Acknowledge time:** how long it took the operator to acknowledge (long times = possibly not critical)
- **Alarm-flood events:** alarms that fire together (root-cause analysis)

### 3.2 ISA-18.2 Performance Indicators

Target values (use these to score the existing system):

| Indicator | Target | Legacy system typically |
|-----------|--------|------------------------|
| Alarms per hour | < 6 / hour | Usually 50+ |
| Critical ratio | < 5% | Usually high |
| Same-alarm repeat ratio | < 5% | 30%+ without filtering |
| Suppressed-alarm ratio | < 1% | Usually 0 (no suppression) |

### 3.3 Mode-Based Suppression Design

| Mode | Alarms to suppress |
|------|---------------------|
| M03 Setup | Cycle timeout, position out-of-range |
| M04 Maintenance | All production alarms |
| M05 Cleaning | Tank low, flow alarms |
| M06 Lockout | Only safety remains active |

---

## 4. Multi-Language Text Conversion

### 4.1 Strategy

```
[Original German text]
   ↓
[AlarmText_DE: preserved verbatim]
   ↓
[English translation produced]
   ↓
[AlarmText_EN: translated]
   ↓
[Turkish translation (if project is TR)]
   ↓
[AlarmText_TR: translated]
```

### 4.2 Terminology Glossary (`lang_glossary/`)

Use the glossary:
- "NOT-AUS" → EN: "Emergency Stop" / TR: "Acil Durdurma"
- "Schutzfeld" → EN: "Safety Zone" / TR: "Güvenlik Bölgesi"
- "Tankfüllstand" → EN: "Tank Level" / TR: "Tank Seviyesi"

Details: `01_GLOBAL_STANDARDS/lang_glossary/GLOSSARY_BASE.md` (Phase 5)

---

## 5. Validation

### 5.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD08 \
  --check-critical-ack \
  --check-multilang-coverage \
  --check-trigger-tags
```

### 5.2 Manual

| Check | Target |
|-------|--------|
| AlarmID format | `^ALM\d{4}$` |
| Class + AcknRequired conditional | Critical → Y |
| Priority unique | 1-999 |
| AlarmText_EN populated | Min 5 chars |
| TriggerTag in RD01 | Cross-ref |
| LinkedTimer in RD07 | Cross-ref |
| LinkedSF in RD05 | Cross-ref |

---

## 6. Common Pitfalls

- ❌ **Critical class + AcknRequired=N:** conditional reject. Critical always requires ACK.
- ❌ **Two AlarmIDs for the same condition:** duplicate (same tag, same limit, different ID) → merge into one ID.
- ❌ **LimitValue empty on an analog alarm:** "Tank high" with no limit value → unusable.
- ❌ **Writing English into AlarmText_DE:** if the original German is lost, the customer can no longer read the source text.
- ❌ **No nuisance-alarm filter:** a chattering sensor produces 10 alarms per second → operator overload. Add a LinkedTimer.
- ❌ **No mode-based suppression:** "Tank low" alarms during Cleaning continuously → configure suppression.
- ❌ **Random Priority:** the AI assigns arbitrary values like "Priority=100" → classify per the ISA-18.2 distribution.
- ❌ **RecommendedAction too generic:** "Call maintenance" is not enough — say which equipment/location/method.

---

## 7. AI Prompt Suggestion

`04_AI_PROMPTS/analyze/PROMPT_EXTRACT_ALARM_FROM_CODE.md`

The AI must be careful with multi-lang text — pull terminology from the glossary, don't translate on its own.

---

## 8. Gate 3 Checklist

- [ ] AlarmID format correct and sequential
- [ ] Class distribution close to the ISA-18.2 targets
- [ ] Priority unique and class-appropriate
- [ ] AcknRequired=Y on every Critical alarm
- [ ] AlarmText_EN on every row
- [ ] Project-language text (TR/DE) populated where needed
- [ ] Original text preserved in AlarmText_DE
- [ ] TriggerTag exists in RD01 (cross-ref clean)
- [ ] Nuisance candidates filtered via LinkedTimer
- [ ] Mode-based suppression configured
- [ ] RecommendedAction concrete on every row

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_08_ALARM.md`
- **AI prompt:** `PROMPT_EXTRACT_ALARM_FROM_CODE.md`
- **Previous:** `RETROFIT_EXTRACT_TIMING.md`
- **Next:** `RETROFIT_EXTRACT_USECASE.md`
- **Dependent RDs:** RD01 (TriggerTag), RD05 (LinkedSF), RD07 (LinkedTimer)
- **Language:** `GLOBAL_LANG_POLICY.md` + `lang_glossary/`
- **Standards:** ISA-18.2, IEC 62682, EEMUA 191

---

*v1.1.0 — Full English body (2026-05-23). The alarm system is the machine's communication channel with the operator. A badly designed alarm = operator overload = real alarms get missed. ISA-18.2 discipline is mandatory.*
