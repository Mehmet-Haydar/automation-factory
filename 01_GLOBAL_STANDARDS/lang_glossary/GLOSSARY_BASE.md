---
title: Multi-Language Glossary — Base (Canonical Concepts)
version: 1.0.0
last_updated: 2026-05-15
status: ACTIVE
languages: [EN, TR, DE]
last_validated: 2026-05
---

# GLOSSARY_BASE.md — Multi-Language Terminology Reference (Canonical Concepts)

> **This file is the canonical reference for industrial automation terminology.** Each term represents a concept (`concept_id`). Each language file (`GLOSSARY_EN.md`, `GLOSSARY_TR.md`, `GLOSSARY_DE.md`) provides the corresponding expressions for these concepts.

---

## 1. Purpose

- **AI prompt outputs:** German → English / Turkish translation consistency
- **HMI multi-language text:** Filling RD11 Label_EN/TR/DE
- **Alarm multi-language text:** Filling RD08 AlarmText_EN/TR/DE
- **Code comments:** Consistent terminology in output language
- **Engineer communication:** Speaking with customer in same language

---

## 2. Concept Categories

| Category | concept_id prefix | Example |
|----------|-------------------|---------|
| Safety | `safety.*` | safety.estop, safety.lightcurtain |
| Mode/State | `mode.*` / `state.*` | mode.auto, state.execute |
| Mechanical | `mech.*` | mech.motor, mech.valve, mech.conveyor |
| Sensor | `sensor.*` | sensor.temperature, sensor.pressure |
| Action | `action.*` | action.start, action.reset |
| Alarm/Fault | `alarm.*` / `fault.*` | alarm.high, fault.overload |
| Process | `process.*` | process.fill, process.mix |
| Maintenance | `maint.*` | maint.lubrication, maint.calibration |
| Recipe | `recipe.*` | recipe.load, recipe.save |
| Communications | `comm.*` | comm.profinet, comm.lost |

---

## 3. Canonical Concept List

### 3.1 Safety (safety.*)

| concept_id | Description |
|------------|----------|
| safety.estop | Emergency stop button/function |
| safety.estop_pressed | E-Stop pressed condition |
| safety.estop_cleared | E-Stop released and cleared |
| safety.lightcurtain | Safety light curtain |
| safety.lightcurtain_interrupted | Light curtain beam broken |
| safety.guard_door | Safety guard door |
| safety.guard_door_open | Safety guard door open |
| safety.twohand | Two-hand control |
| safety.zone | Safety zone / protected area |
| safety.lockout | Lockout/Tagout (LOTO) |
| safety.silent_loss | Silent safety function loss |
| safety.fpassed | F-PLC system passed |

### 3.2 Mode / State (mode.* / state.*)

| concept_id | Description |
|------------|----------|
| mode.auto | Automatic operating mode |
| mode.manual | Manual operating mode |
| mode.setup | Setup/commissioning mode |
| mode.maintenance | Maintenance mode |
| mode.cleaning | Cleaning mode |
| mode.lockout | Lockout (LOTO) mode |
| mode.emergency | Emergency mode |
| state.idle | System idle (PackML) |
| state.execute | System executing (PackML) |
| state.held | System held (PackML) |
| state.suspended | System suspended (PackML) |
| state.aborted | System aborted (PackML) |

### 3.3 Mechanical (mech.*)

| concept_id | Description |
|------------|----------|
| mech.motor | Motor (general) |
| mech.motor_running | Motor running |
| mech.motor_stopped | Motor stopped |
| mech.motor_fault | Motor fault |
| mech.pump | Pump |
| mech.conveyor | Conveyor |
| mech.belt | Conveyor belt |
| mech.valve | Valve (general) |
| mech.valve_open | Valve open |
| mech.valve_closed | Valve closed |
| mech.mixer | Mixer/agitator |
| mech.tank | Tank/vessel |
| mech.filter | Filter |
| mech.cylinder | Pneumatic/hydraulic cylinder |

### 3.4 Sensor (sensor.*)

| concept_id | Description |
|------------|----------|
| sensor.temperature | Temperature sensor |
| sensor.pressure | Pressure sensor |
| sensor.level | Level sensor |
| sensor.flow | Flow sensor |
| sensor.speed | Speed sensor / encoder |
| sensor.position | Position sensor / encoder |
| sensor.proximity | Proximity sensor |
| sensor.photocell | Photoelectric sensor |
| sensor.limit_switch | Limit switch |
| sensor.vibration | Vibration sensor |
| sensor.current | Current sensor |

### 3.5 Action (action.*)

| concept_id | Description |
|------------|----------|
| action.start | Start command |
| action.stop | Stop command |
| action.reset | Reset command |
| action.acknowledge | Alarm acknowledge |
| action.jog | Jog (manual move) |
| action.home | Homing operation |
| action.calibrate | Calibration action |
| action.load_recipe | Load recipe |
| action.save_recipe | Save recipe |

### 3.6 Alarm / Fault (alarm.* / fault.*)

| concept_id | Description |
|------------|----------|
| alarm.high | High alarm |
| alarm.highhigh | High-High alarm (critical) |
| alarm.low | Low alarm |
| alarm.lowlow | Low-Low alarm (critical) |
| alarm.communication_lost | Communication lost |
| alarm.timeout | Timeout |
| alarm.overload | Overload condition |
| fault.drive | Drive fault |
| fault.sensor | Sensor fault |
| fault.short_circuit | Short circuit |
| fault.open_circuit | Open circuit |
| fault.thermal | Thermal overload |

### 3.7 Process (process.*)

| concept_id | Description |
|------------|----------|
| process.fill | Filling operation |
| process.empty | Emptying operation |
| process.mix | Mixing operation |
| process.heat | Heating |
| process.cool | Cooling |
| process.dry | Drying |
| process.weigh | Weighing |
| process.transfer | Material transfer |
| process.cycle_complete | Cycle complete |

### 3.8 Maintenance (maint.*)

| concept_id | Description |
|------------|----------|
| maint.lubrication | Lubrication routine |
| maint.calibration | Calibration |
| maint.filter_change | Filter change |
| maint.belt_tension | Belt tension adjustment |
| maint.predictive | Predictive maintenance |
| maint.preventive | Preventive maintenance |
| maint.runhours | Run hours / Operating hours |

### 3.9 Recipe (recipe.*)

| concept_id | Description |
|------------|----------|
| recipe.active | Active recipe |
| recipe.load | Load recipe |
| recipe.save | Save recipe |
| recipe.changeover | Recipe changeover |
| recipe.parameter | Recipe parameter |
| recipe.ingredient | Ingredient/material |

### 3.10 Communications (comm.*)

| concept_id | Description |
|------------|----------|
| comm.profinet | PROFINET |
| comm.profibus | PROFIBUS DP |
| comm.ethercat | EtherCAT |
| comm.modbus | Modbus (TCP/RTU) |
| comm.opcua | OPC UA |
| comm.lost | Communication lost |
| comm.heartbeat | Heartbeat signal |
| comm.watchdog | Communication watchdog |

---

## 4. Language Files

Each concept has corresponding expressions in different languages:

- `GLOSSARY_EN.md` — English (canonical source; default AI output language)
- `GLOSSARY_TR.md` — Turkish
- `GLOSSARY_DE.md` — German (critical for legacy code source)

Each file follows the same `concept_id` list and provides corresponding expressions.

---

## 5. Extension Policy

When adding a new concept:
1. Place it in the appropriate category (`<category>.<name>`)
2. Add the concept to THIS file
3. Update ALL 3 language files (missing language = AI defaults to English)
4. Leave update proposal via `script_propose_update.py`

---

## 6. Consistency Rules

- Every `concept_id` uses snake_case + dot separator (`mech.motor_running`, NOT mech.motor.running)
- Description line is in English (canonical)
- All language files maintain the SAME `concept_id` sequence
- If translation is missing in language file, use `[MISSING]` placeholder (script warns about it)

---

## 7. Related Files

- **Language files:** `GLOSSARY_EN.md`, `GLOSSARY_TR.md`, `GLOSSARY_DE.md`
- **Language policy:** `GLOBAL_LANG_POLICY.md`
- **HMI multi-language:** `MDSCHEMA_RAWDATA_11_HMI.md`
- **Alarm multi-language:** `MDSCHEMA_RAWDATA_08_ALARM.md`
- **AI prompts:** Reference this glossary as primary when translating

---

*Glossary v1.0.0 — Industrial automation canonical terminology. Consistency backbone for multi-language projects.*
