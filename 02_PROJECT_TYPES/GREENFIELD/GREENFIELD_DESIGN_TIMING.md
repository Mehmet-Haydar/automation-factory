---
title: Greenfield Timing/Watchdog Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD07_Timing
prerequisite: [MDSCHEMA_RAWDATA_07_TIMING.md, GREENFIELD_FLOWCHART.md, GREENFIELD_DESIGN_DATADICT.md]
---

# GREENFIELD_DESIGN_TIMING.md — Timing Design Guide

> **Goal:** design timers, delays, and watchdogs in greenfield projects with full IEC 61131-3 compliance from scratch.

---

## 1. Prerequisites

- [ ] RD03 Flowchart design (for step-delay timers)
- [ ] RD09 Comms (for comm watchdogs)
- [ ] PLC scan cycle known (typically 10-100 ms)
- [ ] Reaction-time requirements (process-requirement analysis)

---

## 2. Design Philosophy

Greenfield advantage:
- IEC 61131-3 timer types (TON/TOF/TP/TONR) used directly
- No need to convert from legacy SE/SI/SF/RTO
- Instance DBs can be optimised
- Naming convention applied cleanly (TMR_<CAT>_<NUM>)

---

## 3. Timer-Type Selection Guide

```
Signal behaviour:
    ↓
[Need: delayed turn-on?]
    ├─ Yes → TON (On-delay)
    │
[Need: delayed turn-off?]
    ├─ Yes → TOF (Off-delay)
    │
[Need: fixed-duration pulse?]
    ├─ Yes → TP (Pulse)
    │
[Need: retentive count (survive power loss)?]
    └─ Yes → TONR (Retentive on-delay)
```

| Type | Behaviour | Typical use |
|------|-----------|-------------|
| TON | Q=TRUE when IN=TRUE longer than PT | Step delay, debounce |
| TOF | Q=FALSE when IN=FALSE longer than PT | Motor stop delay, valve close delay |
| TP | Q=TRUE on IN rising edge, Q=FALSE after PT | Pulse output, flasher |
| TONR | Like TON but count preserved when IN=FALSE | Total runtime, attempt counter |

---

## 4. Design Steps

### 4.1 Step 1 — Build the Timer Inventory

```
[1] RD03 Flowchart steps → step-delay timers
[2] RD08 Alarm List → debounce timers
[3] RD09 Comms → communication watchdogs
[4] Sequence FBs → timeout timers
[5] Periodic tasks → cycle-control timers
```

### 4.2 Step 2 — Naming Design

```
TMR_<CATEGORY>_<NUM>:
  TMR_STEP_001       Step S010 delay
  TMR_STEP_002       Step S020 delay
  TMR_WD_001         PROFINET watchdog
  TMR_WD_002         Modbus watchdog
  TMR_DEBOUNCE_001   E-Stop button debounce
  TMR_DEBOUNCE_002   Photocell debounce
  TMR_TIMEOUT_001    Tank fill timeout
  TMR_CYCLE_001      1 Hz cycle pulse
  TMR_ALARM_001      Alarm flicker filter
```

### 4.3 Step 3 — Preset Value Calculation

**Step-delay timers:**
```
PT = (real process time) × (1.5 safety factor)

Example: tank fill takes 30 seconds, add a 45 s fail-safe watchdog:
  TMR_STEP_005 (StepDelay): PT = T#30s
  TMR_TIMEOUT_005 (Timeout): PT = T#45s + LinkedAlarm
```

**Debounce timers:**
| Signal type | Typical debounce |
|-------------|------------------|
| Mechanical button | 20-50 ms |
| Photocell | 10-30 ms |
| Proximity sensor | 5-15 ms |
| Pressure switch | 50-200 ms (lots of jitter) |
| Limit switch | 20-50 ms |

**Watchdog timers:**
| System | Typical watchdog |
|--------|------------------|
| PROFINET IO | 3 × cycle time (e.g. 4 ms cycle → 12 ms WD) |
| Modbus TCP | 3-5 × cycle time |
| OPC UA | 1-5 seconds |
| Sequence step | 1.5 × expected duration |
| SCADA comms | 5-30 seconds |

### 4.4 Step 4 — Watchdog Design (Most Critical)

For every watchdog, ask:

1. **What triggers it?** (heartbeat lost, sequence stuck, comm timeout)
2. **What is the duration?** (table above)
3. **What happens when it trips?** (alarm, safe state, retry)
4. **Which alarm is triggered?** (RD08 LinkedAlarm)

SCL example:

```scl
// PROFINET watchdog
TMR_WD_001(
    IN := NOT "DB_Comm".PN_HeartbeatOK,
    PT := T#500ms
);
IF TMR_WD_001.Q THEN
    "DB_Alarm".bAlarm_ALM0042 := TRUE;
    "DB_System".bCommFault := TRUE;
    // transition to safe state
END_IF;
```

### 4.5 Step 5 — Cycle-Time Resolution Check

PT must be at least 2× the PLC scan cycle:

```
PLC cycle = 50 ms
Minimum reliable PT = 100 ms (50 × 2)
Recommended PT = 200 ms (50 × 4)
```

**Check:** `if PT < 2*CycleTime → warning`

### 4.6 Step 6 — Multi-Instance vs Singleton

| Scenario | Approach |
|----------|----------|
| Generic timer (generic delay) | Multi-instance (separate instance per usage) |
| System-wide (e.g. 1 Hz pulse) | Singleton (one instance used by the whole system) |
| Alarm filter | Separate instance per alarm |
| Step delay | Separate instance per step |

---

## 5. Cycle-Pulse Design (System-Wide)

A single global pulse benefits most systems:

```scl
// 1 Hz pulse (50% duty cycle)
TMR_CYCLE_HZ1(
    IN := NOT "DB_System".bPulse1Hz,
    PT := T#500ms
);
"DB_System".bPulse1Hz := TMR_CYCLE_HZ1.Q;
```

The whole system can use "DB_System.bPulse1Hz" for flasher animations and OEE counters.

Common frequencies:
- 1 Hz (every second) — counters, HMI flashers
- 10 Hz (100 ms) — fast-response counts
- 0.1 Hz (10 s) — low-frequency processing (logs, OEE)

---

## 6. Validation

### 6.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD07 \
  --check-watchdog-alarm-link \
  --check-cycle-resolution \
  --check-naming
```

### 6.2 Manual Checklist

- [ ] TimerType correct on every timer (TON/TOF/TP/TONR)
- [ ] PresetValue in T# format
- [ ] LinkedAlarm populated on IsWatchdog=Y rows
- [ ] Each multi-instance has its own DB_Instance
- [ ] StepDelay timers linked via LinkedStep
- [ ] PT > 2 × cycle time
- [ ] Naming convention `TMR_<CAT>_<NUM>`

---

## 7. Common Design Pitfalls

- ❌ **Watchdog duration too short:** trips under normal jitter → nuisance alarm
- ❌ **Watchdog duration too long:** problems unnoticed → safety impact possible
- ❌ **No LinkedAlarm:** silent failure when the watchdog trips
- ❌ **TON instead of TONR:** retentive behaviour lost (count resets)
- ❌ **Multi-instance/singleton mix:** the same instance called from multiple places → wrong count
- ❌ **PT below cycle:** PT=T#10ms with cycle=50ms → can't be resolved
- ❌ **Debounce overkill:** 500 ms debounce on a button → operator feels lag
- ❌ **Cycle pulse re-generated everywhere:** each FB makes its own pulse instead of a single global one → wasteful

---

## 8. Design-Approval Checklist

- [ ] Timer inventory complete
- [ ] Every watchdog linked via LinkedAlarm
- [ ] Cycle-resolution check done
- [ ] Step-delay timers linked to the Flowchart
- [ ] Naming standard 100% applied
- [ ] Global cycle pulse (1 Hz) designed
- [ ] Comm watchdogs calculated (3-5 × cycle)
- [ ] script_consistency_check.py clean

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_07_TIMING.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_TIMING.md`
- **Previous:** `GREENFIELD_DESIGN_MODE.md`
- **Next:** `GREENFIELD_DESIGN_ALARM.md`
- **Dependent RDs:** RD03 (LinkedStep), RD08 (LinkedAlarm)
- **Standards:** IEC 61131-3 §2.5.2, §6.5.3

---

*v1.1.0 — Full English body (2026-05-23). Watchdog design = the machine's shield against silent failures. In greenfield, build this shield correctly from day one.*
