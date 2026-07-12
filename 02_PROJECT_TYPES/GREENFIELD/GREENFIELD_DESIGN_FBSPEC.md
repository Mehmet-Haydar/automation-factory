---
title: Greenfield FB/FC Specification Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD10_FBSpec
prerequisite: [MDSCHEMA_RAWDATA_10_FBSPEC.md, GLOBAL_FB_TEMPLATE.scl]
---

# GREENFIELD_DESIGN_FBSPEC.md — FB/FC Specification Design Guide

> **Goal:** design the modular FB/FC architecture of a greenfield project correctly from the start. PLCopen + IEC 61131-3 + GLOBAL_FB_TEMPLATE discipline.

---

## 1. Prerequisites

- [ ] RD01 IO + RD02 DataDict designed
- [ ] Customer brief analysed (how many motors, valves, sensors)
- [ ] HW platform selected (S7-1500, AB CompactLogix, Beckhoff)

---

## 2. Design Philosophy

The greenfield advantage: a **clean modular structure**. Avoid the one-giant-OB1 anti-pattern.

```
OB1 (Main Cycle)
  ├── FC_ScanInputs()                  // read all physical inputs
  ├── FB_ModeMgr(...)                  // mode management
  ├── FB_Sequence(...)                 // sequence/state machine
  ├── FB_AlarmMgr(...)                 // alarm management
  ├── FB_Motor(...) (multiple instances)
  ├── FB_Valve(...) (multiple instances)
  ├── FB_PID(...)   (multiple instances)
  └── FC_WriteOutputs()                // write all physical outputs
```

**OB35/OB40 (interrupts):** independent FBs.
**SafetyTask (F-PLC):** completely separate F-FBs.

---

## 3. Standard FB Catalogue (Reusable)

In greenfield, these FBs are derived from **GLOBAL_FB_TEMPLATE**:

| FB Name | Responsibility | Typical instances |
|---------|----------------|-------------------|
| FB_Motor | DOL/Star-Delta motor | 2-20 |
| FB_MotorVFD | VFD motor (analog or bus) | 2-10 |
| FB_Valve | Solenoid valve (2/3-way) | 5-30 |
| FB_ValveModulating | Modulating/proportional valve | 1-5 |
| FB_Sensor_Analog | Analog sensor + scaling | 5-50 |
| FB_PID | PID control loop | 1-5 |
| FB_Axis | Servo axis wrapper | 1-8 |
| FB_ModeMgr | Mode management (singleton) | 1 |
| FB_Sequence | Sequence/SFC wrapper | 1-3 |
| FB_AlarmMgr | Alarm management (singleton) | 1 |
| FB_RecipeMgr | Recipe management | 1 |
| FB_CommMgr | Communications management | 1 |

---

## 4. Design Steps

### 4.1 Step 1 — FB Inventory

Derive the FB inventory from the devices on the customer's machine:

```yaml
machine:
  motors: 5  (Pump01, Pump02, Conv01, Conv02, Mixer01)
  valves: 12 (V01..V12)
  sensors_analog: 8 (TT, PT, LT, FT)
  axes: 2 (X, Y gantry)
  pid_loops: 2 (Temperature, Pressure)

fb_inventory:
  FB_Motor → 5 instances
  FB_Valve → 12 instances
  FB_Sensor_Analog → 8 instances
  FB_Axis → 2 instances
  FB_PID → 2 instances
  FB_ModeMgr → 1 (singleton)
  FB_Sequence → 1
  FB_AlarmMgr → 1
  FB_RecipeMgr → 1
  FB_CommMgr → 1
```

### 4.2 Step 2 — FB Interface Design

**FB_Motor template example:**

```
FB_Motor (Stateful, IEC 61131-3)
├── VAR_INPUT
│   ├── in_bStartCmd      : BOOL
│   ├── in_bStopCmd       : BOOL
│   ├── in_bResetCmd      : BOOL
│   ├── in_rSetSpeed      : REAL    (if VFD)
│   └── in_iMode          : INT     (mode-aware)
│
├── VAR_OUTPUT
│   ├── out_bRunning      : BOOL
│   ├── out_bFault        : BOOL
│   ├── out_iFaultCode    : INT
│   └── out_rActSpeed     : REAL    (if VFD)
│
├── VAR_IN_OUT
│   └── inout_udMotorData : UDT_Motor    (for HMI/SCADA)
│
├── VAR (Static)
│   ├── stat_bInternalRun : BOOL
│   ├── stat_tStartTime   : TIME
│   └── stat_TON_Start    : TON       (multi-instance)
│
└── VAR_TEMP
    └── temp_rCalcBuffer  : REAL
```

### 4.3 Step 3 — UDT Design

A UDT is mandatory for repeating structures:

```
UDT_Motor (struct used by every motor)
├── bRunning      : BOOL
├── bFault        : BOOL
├── iFaultCode    : INT
├── rSetSpeed     : REAL
├── rActSpeed     : REAL
├── tRuntime      : TIME
└── diStartCount  : DINT
```

DB_Motor (FB_Motor instance DB) uses this UDT.

### 4.4 Step 4 — Naming Standard

```
BlockName:
  FB_Motor, FB_Valve, FB_PID         (generic FB)
  FB_Motor_Pump01 (not an instance — the class name is fixed; instance distinguished via the instance DB)

InstanceDB:
  DB_Mot_Pump01, DB_Mot_Pump02, DB_Mot_Conv01
  
ParamName:
  in_bStartCmd                       (prefix + type prefix + name)
  out_rActSpeed
  stat_bInternalRun
  
UDT:
  UDT_Motor, UDT_Valve, UDT_PID
```

### 4.5 Step 5 — TemplateBase

```yaml
FB_Motor:
  TemplateBase: GLOBAL_FB_TEMPLATE
  
FB_Custom_Specialized:
  TemplateBase: Custom
  CustomRationale: "Customer's special control algorithm"
```

FBs derived from GLOBAL_FB_TEMPLATE.scl share the same 4-region structure:
- INTERFACE (parameters)
- INIT (first scan)
- MAIN (main logic)
- FAULT (fault handling)

---

## 5. Multi-Instance vs Singleton

| Type | Use | Example |
|------|-----|---------|
| Multi-instance | Same type, different object | FB_Motor (5 motors) |
| Singleton | System-wide, single instance | FB_ModeMgr, FB_AlarmMgr |

**Singleton naming:** `DB_ModeMgr` (instance DB) — no number suffix because there's only one instance.

---

## 6. Validation (Design Check)

- [ ] A generic FB exists for every device type
- [ ] Where multi-instance is needed, the instance list is defined
- [ ] UDTs designed (for repeating data)
- [ ] ParamName prefix on every parameter
- [ ] Interface signature clear (IN/OUT/INOUT separation)
- [ ] TemplateBase chosen
- [ ] GLOBAL_FB_TEMPLATE pattern applied

---

## 7. Common Design Pitfalls

- ❌ **God FB:** a single FB with 50+ parameters → must be split
- ❌ **Anemic FB:** the FB just sets/resets a BOOL → an FC is enough
- ❌ **Not using multi-instance:** 5 separate FB_Pump01..FB_Pump05 → use a single FB_Motor with 5 instances
- ❌ **Repeating without a UDT:** the same struct copy-pasted in 10 places
- ❌ **Mixing STAT and TEMP:** keeping cross-cycle persistent data in TEMP
- ❌ **Skipping GLOBAL_FB_TEMPLATE:** writing custom → maintenance nightmare

---

## 8. Design-Approval Checklist

- [ ] FB inventory complete (per device)
- [ ] Interface designed for every FB
- [ ] UDTs designed
- [ ] Naming standard applied
- [ ] InstanceDB list (per FB)
- [ ] TemplateBase = GLOBAL_FB_TEMPLATE (wherever possible)
- [ ] RD10_FBSpec populated for Gate 5 code generation

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_10_FBSPEC.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_FBSPEC.md`
- **Template:** `01_GLOBAL_STANDARDS/code_templates/GLOBAL_FB_TEMPLATE.scl`
- **Naming:** `GLOBAL_NAMING_STANDARD.md`

---

*v1.1.0 — Full English body (2026-05-23). In greenfield, the FB inventory is the machine's "anatomy chart". The more modular = the easier the maintenance.*
