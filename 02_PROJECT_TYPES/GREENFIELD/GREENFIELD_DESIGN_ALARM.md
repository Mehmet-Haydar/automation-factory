---
title: Greenfield Alarm System Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD08_Alarm
prerequisite: [MDSCHEMA_RAWDATA_08_ALARM.md, GREENFIELD_DESIGN_TIMING.md, GLOBAL_LANG_POLICY.md]
---

# GREENFIELD_DESIGN_ALARM.md — Alarm System Design Guide

> **Goal:** design the alarm system of a greenfield project in full compliance with ISA-18.2 / IEC 62682 / EEMUA 191.

---

## 1. Prerequisites

- [ ] RD01 IO (TriggerTag), RD05 Safety (LinkedSF), RD07 Timing (LinkedTimer)
- [ ] RD04 Mode (for mode-based suppression)
- [ ] Customer language defined (TR / EN / DE / multi-lang)
- [ ] HMI platform selected (FactoryTalk View, WinCC, CODESYS Visu)

---

## 2. ISA-18.2 Design Principles

### 2.1 An Alarm Requires Operator Action

The question "**should this trigger be an alarm?**":

| Trigger | Operator action? | Alarm? |
|---------|------------------|--------|
| Tank level 90% (warning level) | Yes (manual intervention) | YES (Warning) |
| Tank level 95% (critical) | Yes (urgent) | YES (Critical) |
| Tank level 50% (normal swing) | No | NO (log/trend) |
| Production complete | No | NO (info — log ok) |
| Motor started | No | NO (event/log) |

**Rule:** if the operator does not take an action = NOT an alarm; just an event/log.

### 2.2 Performance Targets (EEMUA 191)

| Indicator | Target |
|-----------|--------|
| Alarms per hour | < 6 / hour (average) |
| Alarms per hour | < 10 / hour (peak) |
| Critical ratio | < 5% |
| Same-alarm repeat ratio | < 5% |
| Suppressed-alarm ratio | < 1% |
| Operator acknowledge time | < 5 min (Critical) |

Design against these targets.

### 2.3 Alarm Classification

```
Critical (5%)
  ├─ Safety related (highest priority 1-10)
  ├─ Production stop (priority 11-30)
  └─ Equipment damage risk (priority 31-50)

Warning (30%)
  ├─ Quality risk (priority 51-100)
  ├─ Deviation from target (priority 101-200)
  └─ Maintenance prediction (priority 201-300)

Info (65%)
  └─ Event log only (priority 301-999, AcknRequired=N)
```

---

## 3. Design Steps

### 3.1 Step 1 — Alarm Inventory Table (Bottom-Up)

For every device/process point, list "what could go wrong?":

```
Pump P-101:
  - Trip (fault feedback)         → Critical, priority 5
  - Overload (current high)       → Critical, priority 8
  - Run feedback timeout          → Warning, priority 100
  - Vibration high                → Warning, priority 150
  - Run hours exceeded            → Info, priority 500

Tank T-201:
  - Level HighHigh (>95%)         → Critical, priority 5
  - Level High (>85%)             → Warning, priority 100
  - Level Low (<15%)              → Warning, priority 110
  - Level LowLow (<5%)            → Critical, priority 10
  - Temperature HighHigh          → Critical, priority 7

Conveyor C-301:
  - E-Stop pressed                → Critical, priority 1
  - Light curtain interrupted     → Critical, priority 2
  - Drive fault                   → Critical, priority 9
  - Belt slippage detected        → Warning, priority 120
```

### 3.2 Step 2 — AlarmID Assignment

```
ALM0001..ALM0099: Critical (Safety + E-Stop)
ALM0100..ALM0299: Critical (Production stop)
ALM0300..ALM0999: Warning
ALM1000..ALM9999: Info / Event
```

(Range is flexible — category-based grouping makes life easier.)

### 3.3 Step 3 — Multi-Language Design (GLOBAL_LANG_POLICY)

| Language | Required | Source |
|----------|----------|--------|
| AlarmText_EN | Always mandatory | Design language |
| AlarmText_TR | Mandatory for TR projects | Glossary + manual |
| AlarmText_DE | Mandatory for DE customers | Glossary + manual |
| Other languages | As needed | Extend the glossary |

**Use the glossary:** `01_GLOBAL_STANDARDS/lang_glossary/GLOSSARY_BASE.md` (Phase 5)

Example:
| EN | TR | DE |
|----|----|----|
| Emergency Stop | Acil Durdurma | NOT-AUS |
| Light Curtain | Güvenlik Bariyeri | Lichtvorhang |
| Tank Level High | Tank Seviyesi Yüksek | Tankfüllstand hoch |
| Communication Lost | İletişim Koptu | Kommunikation verloren |

### 3.4 Step 4 — Trigger Design

The trigger for each alarm must be CONCRETE:

```scl
// Tank level alarm design
"DB_Alarm".bAlarm_ALM0020 := 
    "RD01_LT_TK_001".rScaled > "DB_Setpoint".rTankHighHigh;
    
// Debounce filter
TMR_DEBOUNCE_005(IN := "DB_Alarm".bAlarm_ALM0020_Raw, PT := T#1s);
"DB_Alarm".bAlarm_ALM0020 := TMR_DEBOUNCE_005.Q;
```

### 3.5 Step 5 — Mode-Based Suppression

```scl
// Suppress the tank-low alarm in Cleaning mode
IF "DB_System".ModeState.iCurrentMode = 5 THEN  // M05 Cleaning
    "DB_Alarm".bSuppress_ALM0021 := TRUE;
END_IF;

// Suppress the position out-of-range alarm in Setup mode
IF "DB_System".ModeState.iCurrentMode = 3 THEN  // M03 Setup
    "DB_Alarm".bSuppress_ALM0040 := TRUE;
END_IF;
```

### 3.6 Step 6 — RecommendedAction

A **concrete** suggestion to the operator for every alarm:

| Bad | Good |
|-----|------|
| "Check the tank" | "Check Tank T-201 level on screen SCR020; if >85%, open drain valve V-301" |
| "Call maintenance" | "Pump P-101 vibration high; open maintenance request #BAK-2026-005" |
| "System stopped" | "E-Stop North is pressed; release it, press Reset, go to AUTO" |

---

## 4. HMI Alarm Presentation (ISA-101)

### 4.1 Alarm Banner (Always Visible)

```
[Persistent banner at the top of the screen]
[!] CRITICAL: 2 active   [WARNING]: 5 active   [INFO]: 12 active
```

### 4.2 Alarm List Screen (SCR010)

| Time | ID | Class | Pri | Message | State |
|------|----|----|-----|---------|-------|
| 10:23 | ALM0020 | 🔴 CRIT | 5 | Tank Level HighHigh (T-201) | ACTIVE |
| 10:21 | ALM0042 | 🟡 WARN | 100 | Comm slow (PN_Station1) | ACK |
| 10:15 | ALM0500 | 🔵 INFO | 500 | Recipe loaded (R-105) | RTN |

### 4.3 Colour Standard

| Class | Colour | Meaning |
|-------|--------|---------|
| Critical (active) | 🔴 #FF0000 + flash | Urgent intervention |
| Critical (ack) | 🔴 #FF0000 | Still active but seen |
| Warning (active) | 🟡 #FFA500 + flash | Close monitoring |
| Warning (ack) | 🟡 #FFA500 | Seen |
| Info | 🔵 #0080FF | Information |
| RTN (return to normal) | 🟢 #00C800 | Auto-cleared |

---

## 5. Validation

### 5.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD08 \
  --check-critical-ack \
  --check-multilang-coverage \
  --check-trigger-tags \
  --check-priority-unique
```

### 5.2 Manual Checklist

- [ ] AlarmID format correct and sequential
- [ ] Class distribution at the ISA-18.2 target (5% Critical / 30% Warning / 65% Info)
- [ ] Priority unique
- [ ] Critical → AcknRequired=Y
- [ ] AlarmText_EN on every row
- [ ] Multi-lang text (project + customer language)
- [ ] Trigger debounce/filter timer (nuisance prevention)
- [ ] Mode-based suppression configured
- [ ] RecommendedAction concrete

---

## 6. Common Design Pitfalls

- ❌ **Turning events into alarms:** "Motor started" is not an alarm; it's a log/event
- ❌ **Marking everything Critical:** the 5% Critical target gets blown → operators become insensitive to Critical
- ❌ **No debounce:** a chattering sensor produces 10 alarms per second → operator overload
- ❌ **Half multi-lang text:** English only → customer may reject
- ❌ **No mode suppression:** "Tank low" alarms keep firing during Cleaning
- ❌ **RecommendedAction "Call maintenance":** too generic, no concrete step
- ❌ **AcknRequired=N (for Critical):** breaks the conditional rule
- ❌ **Random Priority:** doesn't match the ISA-18.2 distribution

---

## 7. Design-Approval Checklist

- [ ] Alarm inventory complete across every device/process point
- [ ] ISA-18.2 distribution targets checked
- [ ] Multi-lang text (EN + customer language) filled everywhere
- [ ] Debounce filter timers (RD07 LinkedTimer)
- [ ] Mode-based suppression matrix designed
- [ ] HMI alarm screen (SCR010) mockup ready
- [ ] Colour standard applied
- [ ] RecommendedAction concrete and action-oriented
- [ ] Performance simulation done (alarm-flood test)

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_08_ALARM.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_ALARM.md`
- **Previous:** `GREENFIELD_DESIGN_TIMING.md`
- **Next:** `GREENFIELD_DESIGN_USECASE.md`
- **Dependent RDs:** RD01 (TriggerTag), RD05 (LinkedSF), RD07 (LinkedTimer)
- **Language:** `GLOBAL_LANG_POLICY.md` + `lang_glossary/`
- **Standards:** ISA-18.2, IEC 62682, EEMUA 191

---

*v1.1.0 — Full English body (2026-05-23). Greenfield advantage: build the alarm system right from day one. Bad alarm design is a field nightmare — operator overload, real alarms slip past.*
