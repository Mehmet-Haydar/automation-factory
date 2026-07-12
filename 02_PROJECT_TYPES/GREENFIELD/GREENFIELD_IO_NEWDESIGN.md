---
title: Greenfield IO List Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD01_IO
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_01_IO.md, GREENFIELD_HARDWARE_SELECTION.md]
---

# GREENFIELD_IO_NEWDESIGN.md — IO List Design Guide

> **Goal:** plan the IO list of a greenfield project from the start in a way that complies with `GLOBAL_NAMING_STANDARD` and follows a modular hardware design.

---

## 1. Prerequisites

- [ ] Mechanical design (P&ID, instruments list)
- [ ] Hardware selected (`GREENFIELD_HARDWARE_SELECTION.md`)
- [ ] CPU + I/O module catalogue defined (DI/DO/AI/AO capacity of each module)
- [ ] Internal naming-convention training delivered

---

## 2. Design Steps

### 2.1 Step 1 — Equipment Inventory

List every piece of equipment/sensor from the P&ID:

```yaml
motors:
  - Pump01 (5.5 kW DOL)
  - Pump02 (5.5 kW DOL)
  - Conveyor01 (3 kW VFD)
  - Mixer01 (7.5 kW VFD)

valves:
  - V01..V05 (24 VDC solenoid)
  - V10..V12 (4-20 mA modulating)

sensors_analog:
  - LT_TK_001..LT_TK_003 (level)
  - TT_TK_001..TT_TK_003 (temperature)
  - PT_PI_001..PT_PI_002 (pressure)
  - FT_FL_001..FT_FL_002 (flow)

sensors_digital:
  - Photocell PC01..PC04
  - Limit switches LS_LIM_001..LS_LIM_010
  - E-Stop F_I_EStop_N (North), F_I_EStop_S (South)
```

### 2.2 Step 2 — Tag Assignment (GLOBAL_NAMING_STANDARD)

```
Tag format: ^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$

Motor signals:
  MOT_PUMP_01_OUT    (motor contactor output)
  MOT_PUMP_01_RUN    (motor run feedback)
  MOT_PUMP_01_FAULT  (motor fault input)

Valve signals:
  VAL_V01_OUT        (solenoid output)
  VAL_V01_FB         (limit-switch feedback)

Analog signals:
  ANALOG_LT_TK_001   (tank level)
  ANALOG_TT_TK_001   (tank temperature)

Safety:
  F_I_EStop_North
  F_I_EStop_South
  F_I_LC_Loading
```

### 2.3 Step 3 — Module Assignment

Slot-based assignment to I/O modules:

```
Rack 0:
  Slot 0: CPU 1515-2 PN
  Slot 1: PS 25 W
  Slot 2: DI 32x24VDC (CONV_DI_001)
  Slot 3: DI 32x24VDC (CONV_DI_002)
  Slot 4: DO 32x24VDC (CONV_DO_001)
  Slot 5: DO 32x24VDC (CONV_DO_002)
  Slot 6: AI 8xU/I (CONV_AI_001)
  Slot 7: AO 4xU/I (CONV_AO_001)

ET200SP Station 1 (PROFINET):
  Slot 1: F-DI 8x24VDC (F_DI_001)  ← Safety
  Slot 2: F-DO 4x24VDC (F_DO_001)  ← Safety
  Slot 3: DI 16x24VDC (ET01_DI_001)
  Slot 4: DO 16x24VDC (ET01_DO_001)
```

### 2.4 Step 4 — Address Assignment

```
Tag                  Address      SourceModule
MOT_PUMP_01_OUT      %Q0.0        CONV_DO_001
MOT_PUMP_01_RUN      %I0.0        CONV_DI_001
ANALOG_LT_TK_001     %IW64        CONV_AI_001 Ch0
F_I_EStop_North      %I600.0      F_DI_001
```

### 2.5 Step 5 — Spare I/O

```
%I0.7   spare (DI)
%Q0.7   spare (DO)
%IW64   used (AI Ch0)
%IW66   spare (AI Ch1)
```

Typically 15-20% spare is left.

---

## 3. Naming-Standard Application

### 3.1 Equipment-Prefix Dictionary

| Equipment | Prefix | Example |
|-----------|--------|---------|
| Motor | MOT_ | MOT_PUMP_01 |
| Valve | VAL_ | VAL_V01 |
| Sensor (analog) | ANALOG_ | ANALOG_TT_001 |
| Photocell | PC_ | PC_01 |
| Limit Switch | LS_ | LS_LIM_001 |
| Safety Input | F_I_ | F_I_EStop_N |
| Safety Output | F_Q_ | F_Q_Contactor |
| Conveyor | CONV_ | CONV_BEL_001 |

### 3.2 Equipment-Code Dictionary

| Kind | Code | Example |
|------|------|---------|
| Pump | PUMP, PI | MOT_PUMP_01 |
| Tank | TK | LT_TK_001 |
| Conveyor | CV, BEL | CONV_BEL_001 |
| Mixer | MX | MOT_MX_001 |
| Heater | HT | OUT_HT_001 |

### 3.3 Function-Suffix Dictionary

| Function | Suffix |
|----------|--------|
| Output (command) | _OUT |
| Run feedback | _RUN |
| Fault feedback | _FAULT |
| Position open | _OPEN |
| Position closed | _CLOSED |
| Ready | _RDY |

---

## 4. Validation

- [ ] Tag regex `^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$`
- [ ] All signals included from the equipment inventory
- [ ] 15-20% spare I/O left
- [ ] No address collisions
- [ ] F-prefix only on safety-PLC signals
- [ ] EngUnit + RangeMin/Max populated for AI signals
- [ ] NormalState (NO/NC) populated for DI signals

---

## 5. Common Design Pitfalls

- ❌ **No spare reserved:** adding modules in the field for extra signals is expensive
- ❌ **Skipping NormalState:** mixing up E-Stop NC vs NO is dangerous
- ❌ **EngUnit empty:** mandatory for analog signals
- ❌ **Random tag names:** naming-standard discipline is essential
- ❌ **Misusing the F-prefix:** standard signals being given the F-prefix
- ❌ **Insufficient module capacity:** total signal count exceeds module slot capacity

---

## 6. Checklist

- [ ] Equipment inventory complete from the P&ID
- [ ] Tag names per the naming standard
- [ ] Module + slot assignment done
- [ ] Address plan (traditional or structural) written
- [ ] 15-20% spare I/O
- [ ] Safety signals separated with the F-prefix
- [ ] EngUnit + Range for analog
- [ ] NormalState for DI
- [ ] script_consistency_check.py clean

---

## 7. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_01_IO.md`
- **Retrofit equivalent:** `RETROFIT_IO_EXTRACT.md`
- **Naming:** `GLOBAL_NAMING_STANDARD.md`
- **Hardware selection:** `GREENFIELD_HARDWARE_SELECTION.md`

---

*v1.1.0 — Full English body (2026-05-23). In greenfield, naming = cornerstone. Right start = endless benefit.*
