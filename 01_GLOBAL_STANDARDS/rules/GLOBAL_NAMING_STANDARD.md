---
title: Global Naming Standard
version: 1.0.0
last_validated: 2026-05
platform: TIA Portal V18+
applies_to: [retrofit, greenfield]
---

# GLOBAL_NAMING_STANDARD.md

> **Purpose:** Standardizes variable, FB/FC/DB, tag, and file naming in TIA Portal projects. This rule is the foundation of all AI prompts and templates in the Factory.

---

## 1. General Rules

- **Language:** English (for international project compatibility).
- **Characters:** `A-Z`, `a-z`, `0-9`, `_`. Turkish characters, spaces, dashes (`-`) prohibited.
- **Maximum length:** 24 characters (safe margin to TIA Portal symbol limit).
- **Case:** `SNAKE_CASE_UPPER` instead of PascalCase (for PLC world readability).

---

## 2. Variable Prefixes

### 2.1 Data Type Prefixes

| Prefix | Type | Example |
|--------|------|---------|
| `i` | Bool input | `iStartButton` |
| `q` | Bool output | `qMotorRun` |
| `b` | Bool (general) | `bAlarmActive` |
| `r` | Real | `rPressureBar` |
| `n` | Int / DInt | `nCycleCount` |
| `w` | Word / DWord | `wStatusWord` |
| `t` | Time | `tDelayMs` |
| `s` | String | `sRecipeName` |
| `arr` | Array | `arrTemperatures` |
| `udt` | UDT instance | `udtMotorData` |

### 2.2 Scope Prefixes

| Prefix | Meaning | Example |
|--------|---------|---------|
| `g_` | Global (DB) | `g_rTankLevel` |
| `s_` | Static (FB instance) | `s_nStepNumber` |
| `t_` | Temp (FB local) | `t_rCalcResult` |
| `in_` | FB input | `in_bEnable` |
| `out_` | FB output | `out_bDone` |
| `inout_` | FB inout | `inout_udtMotor` |

---

## 3. Hardware Tags

**Format:** `<TYPE>_<LOCATION>_<NUMBER>_<FUNCTION>`

| Type | Meaning | Example |
|------|---------|---------|
| `MOT` | Motor | `MOT_CV01_001_DRIVE` |
| `VLV` | Valve | `VLV_TK02_005_INLET` |
| `SNS` | Sensor (general) | `SNS_CV01_010_PRES` |
| `PRX` | Proximity sensor | `PRX_ST03_002_HOME` |
| `ENC` | Encoder | `ENC_AX01_001_POS` |
| `TMP` | Temperature sensor | `TMP_TK01_001_INLET` |
| `LVL` | Level sensor | `LVL_TK02_001_HIGH` |
| `PRS` | Pressure sensor | `PRS_LN05_001_MAIN` |
| `FLW` | Flow meter | `FLW_LN03_001_OUTLET` |
| `PB` | Button | `PB_HMI_001_START` |
| `LMP` | Lamp | `LMP_PNL_001_RUN` |
| `ESD` | Emergency stop | `ESD_PNL_001_MAIN` |
| `LS` | Limit switch | `LS_AX01_001_FWD` |

**Location codes (examples):**
- `CV01` → Conveyor 1
- `TK02` → Tank 2
- `AX01` → Axis 1
- `ST03` → Station 3
- `LN05` → Line 5
- `PNL` → Panel
- `HMI` → Operator panel

**Number:** 3 digits, zero-padded (`001`, `015`, `123`).

---

## 4. Program Blocks

### 4.1 Function Block (FB)

**Format:** `FB_<DOMAIN>_<FUNCTION>`

| Example | Description |
|---------|-------------|
| `FB_MOTOR_STANDARD` | Standard motor control FB |
| `FB_VALVE_2WAY` | Two-way valve FB |
| `FB_AXIS_POSITIONING` | Position control FB |
| `FB_RECIPE_MANAGER` | Recipe management FB |
| `FB_AlarmHandler` | Alarm management FB |

### 4.2 Function (FC)

**Format:** `FC_<DOMAIN>_<FUNCTION>`

| Example | Description |
|---------|-------------|
| `FC_SCALE_RAW_TO_REAL` | Scale raw value to engineering unit |
| `FC_BIT_TO_WORD` | Bit to word conversion |

### 4.3 Data Block (DB)

**Format:** `DB_<DOMAIN>_<FUNCTION>` (global) or `iDB_<FB_NAME>` (instance)

| Example | Description |
|---------|-------------|
| `DB_RECIPE_DATA` | Global recipe data |
| `DB_HMI_INTERFACE` | HMI interface DB |
| `iDB_MOT_CV01_001` | Instance DB for `MOT_CV01_001` motor |

### 4.4 User-Defined Type (UDT)

**Format:** `UDT_<DOMAIN>_<FUNCTION>`

| Example | Description |
|---------|-------------|
| `UDT_MOTOR_DATA` | Motor data structure |
| `UDT_AXIS_DATA` | Axis data structure |
| `UDT_RECIPE_STEP` | Recipe step structure |

---

## 5. Network/Comms Names

### 5.1 IP Ranges

See `DOMAIN_COMMS_NETWORK_PLAN.md`. General rule:

| Range | Usage |
|-------|-------|
| `192.168.0.x` | PLC main network |
| `192.168.1.x` | HMI network |
| `192.168.10.x` | Drives (Profinet) |
| `192.168.20.x` | Safety |
| `192.168.100.x` | Engineering (engineer laptop) |

### 5.2 Device Names (Profinet)

**Format:** `<TYPE>-<LOCATION>-<NUMBER>` (Profinet rule: lowercase + dash)

| Example | Description |
|---------|-------------|
| `plc-main-001` | Main PLC |
| `hmi-op-001` | Operator panel |
| `drv-cv01-001` | Conveyor 1 drive |
| `io-pnl-001` | Panel I/O station |

> **Note:** Profinet device names don't use underscore (`_`), only dash (`-`).

---

## 6. File Naming (Factory Repo)

See `FACTORY_MAESTRO.md` Section 2. Briefly:

`[SCOPE]_[DOMAIN]_[SUB_FUNCTION].md`

---

## 7. Prohibited Usage

❌ Turkish characters: `MOTÖR_BAŞLAT`
❌ Space: `Motor Start`
❌ Dash in PLC variable: `Motor-Start`
❌ Unclear abbreviation: `M1`, `S2`, `X` (location not specified)
❌ Numbers only: `Motor1`, `Valve23`
❌ Mixed Camel/Pascal: `motorStart_DB`

✅ Correct: `MOT_CV01_001_DRIVE`, `qMotorRun`, `FB_MOTOR_STANDARD`

---

## 8. Verification

For naming compliance check:

```bash
python 05_SCRIPTS/dev/script_consistency_check.py --project <project_path>
```

Output: List of all symbols not conforming to standard + suggestions.

---

*This standard is the foundation of the Factory. For changes: use `script_propose_update.py`.*
