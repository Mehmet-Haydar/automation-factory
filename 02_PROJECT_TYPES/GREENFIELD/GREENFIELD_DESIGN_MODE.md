---
title: Greenfield Operating Modes Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD04_Mode
prerequisite: [MDSCHEMA_RAWDATA_04_MODE.md, GREENFIELD_DESIGN_DATADICT.md]
---

# GREENFIELD_DESIGN_MODE.md — Operating Modes Design Guide

> **Goal:** design modes in greenfield projects in full compliance with OMAC PackML / ISA-88 §4.7. The difference from retrofit: no constraints, the standard is applied.

---

## 1. Prerequisites

- [ ] Customer brief: what operating modes does the machine have? (operator + maintenance + cleaning?)
- [ ] Risk assessment (CE/TÜV): are Emergency + LOTO mandatory?
- [ ] HMI design guidelines (colour + language)
- [ ] Is PackML compliance mandatory? (often yes for food/pharma customers)

---

## 2. Standard Mode Set

Reference matrix for greenfield projects:

| ModeID | Mode | Priority | PackMLState | HMI Color | Required |
|--------|------|----------|-------------|-----------|----------|
| M00 | Emergency | 0 | Aborted | #FF0000 | **MANDATORY** |
| M01 | Auto | 50 | Execute | #00C800 | A production mode is mandatory |
| M02 | Manual | 40 | Suspended | #FFA500 | Usually |
| M03 | Setup | 30 | Suspended | #FFFF00 | If commissioning is required |
| M04 | Maintenance | 20 | Stopped | #0080FF | Usually |
| M05 | Cleaning | 25 | Suspended | #C800C8 | Mandatory for food/pharma |
| M06 | Lockout (LOTO) | 5 | Stopped | #000000 | Safety critical |

**M00 fixed:** Priority=0, PackMLState=Aborted.

---

## 3. Mode Design Steps

### 3.1 Step 1 — Which Modes Are Needed?

Question guide:

- [ ] Production mode? → M01 AUTO (always present)
- [ ] Manual jog required? → M02 MANUAL
- [ ] Setup/Commissioning? → M03 SETUP
- [ ] Maintenance separated from production? → M04 MAINTENANCE
- [ ] Cleaning required (food/pharma)? → M05 CLEANING
- [ ] LOTO procedure? → M06 LOCKOUT

### 3.2 Step 2 — Mode-Word Design

```scl
TYPE UDT_ModeState :
STRUCT
    iCurrentMode     : INT;          // 0..99 (numeric ModeID)
    iRequestedMode   : INT;          // mode requested by the operator
    bModeChangeOK    : BOOL;         // transition allowed
    sCurrentModeName : STRING[16];   // "AUTO" / "MANUAL" etc.
    iPackMLState     : INT;          // OMAC enum
    sPackMLState     : STRING[16];   // "Execute" / "Suspended" etc.
    bEmergencyActive : BOOL;         // is M00 active
    bMaintAuth       : BOOL;         // maintenance authorisation
    bSupAuth         : BOOL;         // supervisor authorisation
END_STRUCT
END_TYPE
```

Inside the DB:
```
DB_System.ModeState : UDT_ModeState
```

### 3.3 Step 3 — Transition Logic (FB_ModeMgr)

```scl
FUNCTION_BLOCK FB_ModeMgr
VAR_INPUT
    in_bEStop          : BOOL;
    in_bAutoBtn        : BOOL;
    in_bManualBtn      : BOOL;
    in_bSetupBtn       : BOOL;
    in_iAuthLevel      : INT;    // 1=Op, 2=Sup, 3=Eng
END_VAR
VAR_IN_OUT
    inout_ModeState    : UDT_ModeState;
END_VAR
VAR
    stat_iLastMode     : INT;
END_VAR

// M00 always wins
IF in_bEStop THEN
    inout_ModeState.iCurrentMode := 0;
    inout_ModeState.sCurrentModeName := 'EMERGENCY';
    inout_ModeState.bEmergencyActive := TRUE;
    inout_ModeState.iPackMLState := 7; // Aborted
    RETURN;
END_IF;

// After the E-Stop is cleared
inout_ModeState.bEmergencyActive := FALSE;

// Transition to AUTO
IF in_bAutoBtn AND in_iAuthLevel >= 1 AND SafetyOK THEN
    inout_ModeState.iCurrentMode := 1;
    inout_ModeState.sCurrentModeName := 'AUTO';
    inout_ModeState.iPackMLState := 3; // Execute
END_IF;
// ... other modes
END_FUNCTION_BLOCK
```

### 3.4 Step 4 — Transition-Rules Matrix

| Current | → Target | Condition | Action |
|---------|----------|-----------|--------|
| Any | M00 | E-Stop pressed | Immediate, override all |
| M00 | M01 | E-Stop cleared + Reset + Auto button | Reset all outputs |
| M01 | M02 | Manual button + AuthLevel≥1 | Pause production |
| M01 | M04 | Maint button + AuthLevel≥2 | Pass through M02 first |
| M04 | M06 | Lockout key + AuthLevel≥3 | Set LOTO flag |
| M06 | Any | Lockout removed + Reset | Only to M04 |

### 3.5 Step 5 — HMI Integration

For every mode on the HMI:

```
[Mode Indicator] — fixed top-left corner
  - Circle + colour (HMI_Color)
  - Mode name (HMI_Text, multi-lang)
  - PackMLState sub-text

[Mode Buttons] — on the operator panel
  - M00 (Emergency) — physical button + HMI indicator
  - M01 Auto / M02 Manual / M03 Setup — HMI buttons
  - M04 Maint / M06 Lockout — Supervisor/Engineer authorised

[Mode Transition Animation] — during transition
  - "AUTO → MANUAL" animation (1-2 seconds)
  - Show reason ("Operator request")
```

---

## 4. PackML v3.0 State Machine

The standard OMAC PackML state machine:

```
            ┌──── Resetting ────┐
            ↓                   │
       [Stopped]                │
            ↓                   │
       Starting                 │
            ↓                   │
       [Idle]                   │
            ↓                   │
       Starting                 │
            ↓                   │
       [Execute] ────────────── Held ──── [Held]
            │                              ↓
            │                          Unholding
            ↓                              ↓
       Completing                          ↑
            ↓                              │
       [Complete]                          │
            ↓                              │
       Resetting                           │
            ↓                              │
       [Stopped] ───── Aborting ──── [Aborted]
```

Each mode maps to a state in this state machine. This mapping **must be documented** in the design.

---

## 5. Authority Levels (ISA-101)

| Authority | Permitted actions | Typical user |
|-----------|-------------------|--------------|
| 0 None | Read-only | Guest |
| 1 Operator | Start/Stop/Reset, mode change (M01/M02) | Shift operator |
| 2 Supervisor | Recipe changes, open M04 Maint | Shift lead |
| 3 Engineer | Calibration, parameter change, M06 LOTO | Maintenance engineer |
| 4 Admin | User management, system configuration | IT/system admin |

---

## 6. Validation

### 6.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD04 \
  --check-emergency-priority \
  --check-packml-mapping
```

### 6.2 Manual Checklist

- [ ] M00 Emergency present, Priority=0
- [ ] All Priority values unique
- [ ] PackMLState matches the OMAC v3.0 enum
- [ ] HMI_Color in 6-digit hex
- [ ] Multi-lang HMI_Text (EN + DE + TR)
- [ ] Mode-transition matrix documented
- [ ] AuthLevel authorisation designed
- [ ] FB_ModeMgr SCL code written

---

## 7. Common Design Pitfalls

- ❌ **Skipping M00:** mandatory on every machine, even SIL-independent
- ❌ **Not applying PackML:** can be mandatory if the customer is an OEM
- ❌ **No authority level:** the operator jumps straight into M04 → safety issue
- ❌ **Not adding LOTO mode:** OSHA / EN ISO 14118 — required
- ❌ **Random mode transitions:** the transition matrix must be documented
- ❌ **No HMI colour standard:** operator training restarts from scratch on every machine
- ❌ **No authority on recipe changes:** unclear who can load which recipe

---

## 8. Design-Approval Checklist

- [ ] Mode list approved by the customer
- [ ] PackML compliance applied per the chosen direction
- [ ] FB_ModeMgr code written + tested
- [ ] AuthLevel applied on the HMI
- [ ] Transition matrix documented (PDF or md)
- [ ] HMI mockup confirms the visuals of the modes
- [ ] Risk assessment performed for LOTO/Emergency

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_04_MODE.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_MODE.md`
- **Previous:** `GREENFIELD_DESIGN_DATADICT.md`
- **Next:** `GREENFIELD_DESIGN_TIMING.md`
- **Standards:** OMAC PackML v3.0, ISA-88 §4.7, ISA-101 (HMI authority), EN ISO 14118 (LOTO)

---

*v1.1.0 — Full English body (2026-05-23). In greenfield, modes are the machine's "personality". Right design = operator productivity + maintenance ease + safety. PackML discipline is not an extra — it's foundational.*
