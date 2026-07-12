---
title: Greenfield Data Dictionary Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD02_DataDict
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_02_DATADICT.md, GREENFIELD_IO_NEWDESIGN.md]
---

# GREENFIELD_DESIGN_DATADICT.md — Data Dictionary Design Guide

> **Goal:** design the RD02 Data Dictionary of a greenfield project correctly from the start. Different from retrofit "extraction": here we are making **design decisions**.

---

## 1. Prerequisites

- [ ] Customer brief + machine spec ready
- [ ] RD01 IO List designed (via GREENFIELD_IO_NEWDESIGN)
- [ ] Hardware platform selected (S7-1500, AB CompactLogix, Beckhoff, etc.)
- [ ] Modularity decision made: how many FBs, with what responsibilities?

---

## 2. Design Philosophy (Difference from Retrofit)

| Retrofit | Greenfield |
|----------|------------|
| Extraction from legacy code | Design from scratch |
| "Fixing" old names | "Applying" standard names |
| Understanding the existing DB structure | Choosing the optimal DB structure |
| Compromise (legacy constraints) | Best practice (no constraints) |
| Speed: find-and-replace | Speed: foundational decisions + consistency |

Greenfield advantage: you NEVER use absolute addresses, the naming standard is applied 100%, and optimized DBs are used.

---

## 3. DataDict Architecture Decisions

### 3.1 DB Type Selection

| DB Kind | When | Example |
|---------|------|---------|
| **Global DB** | System-wide variables | DB_System, DB_Recipe, DB_HMI |
| **Instance DB** | FB instance state (common) | DB_Mot_Pump01 (FB_Motor instance) |
| **UDT** | Repeating data structure | UDT_Motor, UDT_ValveCtrl |
| **Memory Marker** | Generally **don't use** | Only for legacy integration |

**Greenfield rule:** the %M area (Memory Marker) is **avoided wherever possible**. All variables live inside DBs. Memory Marker = absolute address = outside the naming standard.

### 3.2 Optimized vs Non-Optimized DB

| | Optimized | Non-Optimized |
|--|-----------|---------------|
| TIA Portal default | S7-1200/1500 | S7-300/400 (Classic) |
| Offset | OPT (none) | byte.bit |
| Memory efficient | Yes | No |
| HMI tag access | Symbolic | Symbolic + Absolute |
| Migration difficulty | Low | High |

**Greenfield rule:** **use Optimized DBs**. Use non-optimized only if integration with old hardware requires it.

### 3.3 Modular FB Structure

```
FB_Motor (Generic motor controller)
  └── DB_Mot_Pump01    (Instance 1 — Pump 1)
  └── DB_Mot_Pump02    (Instance 2 — Pump 2)
  └── DB_Mot_Conv01    (Instance 3 — Conveyor)
  └── DB_Mot_Mixer01   (Instance 4 — Mixer)
```

One FB, many instances. Each instance = its own DB = its own data.

### 3.4 UDT Strategy

A UDT is mandatory for repeating data structures:

```
UDT_Motor
  bRunning:      BOOL   // Running
  bFault:        BOOL   // Fault present
  iFaultCode:    INT    // Fault code
  rSetSpeed:     REAL   // Setpoint speed (RPM)
  rActSpeed:     REAL   // Actual speed
  tRuntime:      TIME   // Total runtime
```

This UDT is used on 10 different motors; code is maintained in a single place.

---

## 4. Design Workflow

```
[1] Brief + IO List (RD01) ready
       ↓
[2] Derive FB inventory (together with RD10 FBSpec)
       ↓
[3] Instance list per FB
       ↓
[4] Design UDTs (for repeating data structures)
       ↓
[5] Design Global DBs (system, recipe, HMI)
       ↓
[6] Retain strategy (which variables persist)
       ↓
[7] RD02_DataDict.xlsx
```

### 4.1 FB Inventory (Typical Industrial Machine)

| FB | Responsibility | Typical instance count |
|----|----------------|------------------------|
| FB_Motor | DOL/VFD motor control | 2-10 |
| FB_Valve | Solenoid valve | 5-20 |
| FB_Sensor_Analog | Analog sensor + scaling | 5-30 |
| FB_PID | PID control loop | 1-5 |
| FB_Axis | Servo axis | 1-8 |
| FB_ModeMgr | Mode management | 1 (singleton) |
| FB_Sequence | Sequence/state machine | 1-3 |
| FB_AlarmMgr | Alarm management | 1 |
| FB_RecipeMgr | Recipe management | 1 |
| FB_CommMgr | Communications management | 1 |

### 4.2 Naming Design

Parameter set (ParamList) per FB:

```
FB_Motor parameters:
  IN:
    in_bStartCmd         BOOL   (RD01 IO reference)
    in_bStopCmd          BOOL
    in_bResetCmd         BOOL
    in_rSetSpeed         REAL
  OUT:
    out_bRunning         BOOL
    out_bFault           BOOL
    out_iFaultCode       INT
    out_rActSpeed        REAL
  INOUT:
    inout_udMotorData    UDT_Motor   (UDT reference)
  STAT:
    stat_bInternalState  BOOL
    stat_tStartTime      TIME
  TEMP:
    temp_rCalcBuffer     REAL
```

### 4.3 Global DB Design

```
DB_System (Global, Retain selectively)
  sSystemName        STRING[64]   Retain=Y
  iMachineState      INT          Retain=N   (cold start = 0)
  diProductCounter   DINT         Retain=Y   (production count must not be lost)
  bHeartbeat         BOOL         Retain=N
  rOEE_Daily         REAL         Retain=Y
```

```
DB_Recipe (Global, mostly Retain=Y)
  iActiveRecipe      INT          Retain=Y
  arrRecipes         ARRAY[1..50] OF UDT_Recipe   Retain=Y
```

```
DB_HMI (Global, Retain=N)
  bBtn_Start         BOOL
  bBtn_Stop          BOOL
  bBtn_Reset         BOOL
  iSelectedScreen    INT
  // The HMI only writes to / reads from this DB
```

---

## 5. Retain Strategy

| Variable kind | Retain | Reason |
|---------------|--------|--------|
| Recipe parameters | Y | Must not be lost on power failure |
| Counter (production count) | Y | Counts continue across the work day |
| Cumulative runtime | Y | For maintenance planning |
| Mode/State | N | Cold start must be safe |
| Transient timer | N | Always starts from 0 |
| HMI button | N | Must not be remembered when off |
| Setpoint | Y | Operator shouldn't have to enter again |
| Alarm acknowledge | N | Should be cleared when power returns |

---

## 6. Validation

### 6.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD02 \
  --check-naming \
  --check-memory-marker-usage \
  --check-retain-strategy
```

### 6.2 Manual Checklist

- [ ] Memory Marker usage minimal (preferably zero)
- [ ] Optimized DB preferred
- [ ] Separate instance DB per FB
- [ ] UDTs used for repeating structures
- [ ] ParamName prefix (in_/out_/inout_/stat_/temp_) on all
- [ ] Type-prefix abbreviation (b/w/i/di/r/t/s/u) on all
- [ ] Retain strategy documented
- [ ] Descriptions in English + project language

---

## 7. Common Pitfalls (Greenfield)

- ❌ **Using Memory Markers:** in greenfield, using the %M area violates the naming standard
- ❌ **Every DB Retain=Y:** performance/SD-card wear
- ❌ **Repetition without a UDT:** 5 motors with 5 separate structs → maintenance nightmare
- ❌ **Giving up Optimized:** using the old style is unnecessary
- ❌ **Mixing HMI tags into DBs:** DB_HMI must stay separate
- ❌ **Global/Instance mix:** putting FB_Motor instance data into a Global DB

---

## 8. Design-Approval Checklist

- [ ] FB inventory complete (together with RD10)
- [ ] UDTs designed
- [ ] Global DBs designed (System, Recipe, HMI)
- [ ] Retain strategy decided
- [ ] Naming standard 100% applied
- [ ] Description multi-lang (EN + project language)
- [ ] script_consistency_check.py clean

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_02_DATADICT.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_DATADICT.md`
- **Previous guide:** `GREENFIELD_IO_NEWDESIGN.md` (RD01)
- **Next:** `GREENFIELD_DESIGN_MODE.md`
- **Naming:** `GLOBAL_NAMING_STANDARD.md`
- **FB template:** `GLOBAL_FB_TEMPLATE.scl`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD02_DataDict.xlsx` (Phase 5)

---

*v1.1.0 — Full English body (2026-05-23). Greenfield advantage: a clean start. Don't waste this opportunity — get naming + modularity + retain strategy right from day one.*
