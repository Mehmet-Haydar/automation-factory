---
title: Greenfield HMI Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD11_HMI
prerequisite: [MDSCHEMA_RAWDATA_11_HMI.md, GLOBAL_LANG_POLICY.md]
---

# GREENFIELD_DESIGN_HMI.md — HMI System Design Guide

> **Goal:** design the HMI of a greenfield project with ISA-101 discipline, multi-lang text support, and a hierarchical screen structure.

---

## 1. Prerequisites

- [ ] HMI platform selected (TIA WinCC Unified, FactoryTalk View, CODESYS Visu)
- [ ] Target devices (HMI panel size + count)
- [ ] Customer design guide (corporate identity)
- [ ] Multi-lang requirements (EN + TR / DE)

---

## 2. ISA-101 Discipline

ISA-101 is the modern HMI gold standard. CRITICAL compliance in greenfield:

### 2.1 Hierarchical Screen Layout

```
Level 1: PROCESS OVERVIEW (SCR001)
  ├── Entire plant on a single screen
  ├── Pump, conveyor, tank states
  └── KPI summary (production count, OEE)
       ↓ (click)
Level 2: AREA OVERVIEW (SCR002-009)
  ├── A specific area (e.g. Fill Area)
  └── More detailed indicators
       ↓
Level 3: EQUIPMENT FACEPLATE (SCR020-099)
  ├── Single equipment detail (Motor faceplate)
  ├── Setpoint entry
  ├── Diagnostic info
  └── Trend
       ↓
Level 4: DIAGNOSTIC (SCR090-099)
  ├── Engineer-only
  └── Parameter changes, calibration
```

### 2.2 Colour Standard (ISA-101)

| Colour | Meaning | Hex |
|--------|---------|-----|
| Green | Running, OK | `#00C800` |
| Light grey | Idle, ready | `#C0C0C0` |
| Dark grey | Disabled, off | `#808080` |
| Yellow | Warning | `#FFA500` |
| Red (flashing) | Critical alarm (active) | `#FF0000` flash |
| Red (solid) | Critical alarm (ack) | `#FF0000` |
| Blue | Info | `#0080FF` |
| Magenta | Bypass / Forced (warning) | `#C800C8` |

### 2.3 Typography
- **Background:** light grey (`#F0F0F0`), not white (easier on the eyes)
- **Font:** sans-serif (Arial / Segoe UI)
- **Min size:** 14 pt for an operator screen
- **Critical alarm:** bold + flashing

---

## 3. Design Steps

### 3.1 Step 1 — Derive Screen Hierarchy

Analyse the brief:

```yaml
screens:
  SCR001: Main Overview
  SCR002: Fill Area
  SCR003: Mix Area
  SCR004: Discharge Area
  SCR010: Alarm List
  SCR020: Recipe Management
  SCR030: Trends
  SCR040: Production Reports
  SCR090: Diagnostics
  SCR100..199: Equipment Faceplates
```

### 3.2 Step 2 — AccessLevel Matrix

| Role | Permitted Screens | Authority |
|------|-------------------|-----------|
| Operator | SCR001..010 + matching faceplates | Start/Stop, Reset, mode change |
| Supervisor | + SCR020, SCR030, SCR040 | Recipes, read parameters |
| Engineer | + SCR090 (Diagnostics) | Calibration, parameter change |
| Admin | All | User management |

### 3.3 Step 3 — Multi-Language Design

```yaml
title_strategy:
  primary: EN (always mandatory)
  customer_lang: DE or TR (per customer language)
  fallback: EN
  
glossary_use: GLOSSARY_BASE.md concept_id system
```

Example:
```
HMI_PUMP_01_RUN:
  Label_EN: "Pump 1 Running"
  Label_DE: "Pumpe 1 läuft"
  Label_TR: "Pompa 1 Çalışıyor"
```

### 3.4 Step 4 — Faceplate Design

A standard faceplate per equipment:

```
┌─────────────────────────────────┐
│ Pump 01 (Conveyor Drive)        │
│                                 │
│ ●●●●●● Status: ● Running         │
│                                 │
│ Setpoint:  [____50.0]  rpm      │
│ Actual:        47.3    rpm      │
│ Runtime:      127:34   h:m      │
│                                 │
│ [START] [STOP] [RESET]          │
│                                 │
│ ↓ Diagnostics  ↑ Back           │
└─────────────────────────────────┘
```

### 3.5 Step 5 — Alarm Widget

ISA-18.2-compliant alarm widget at the top of every screen:

```
┌─────────────────────────────────────────────┐
│ [!] 2 CRITICAL  [⚠] 5 WARN  [i] 12 INFO    │
└─────────────────────────────────────────────┘
```

Clicking it goes to SCR010 Alarm List.

### 3.6 Step 6 — Recipe Screen

```
SCR020 Recipe Management
├── Active recipe display
├── Recipe list (scroll)
├── New recipe / copy / delete
├── Parameter table (by category)
├── Save / Load buttons
└── Recipe history log
```

---

## 4. Validation (FAT)

- [ ] All screens rendered as prototypes
- [ ] AccessLevel login test (3 different users)
- [ ] Multi-lang switch test
- [ ] Alarm-widget trigger test
- [ ] Trend graph record + display
- [ ] Recipe load/save test

---

## 5. Common Design Pitfalls

- ❌ **Flat hierarchy:** every screen at Level 1 → operator gets lost
- ❌ **Red everywhere:** Critical loses its meaning
- ❌ **Multi-lang added later:** the design has to start from scratch
- ❌ **NumericInput without validation:** operator types 9999 → motor blows up
- ❌ **Operator sees Engineer screen:** bypassing AccessLevel is a security weakness
- ❌ **A different faceplate per equipment:** consistency + learnability are lost
- ❌ **White background:** eye fatigue, ISA-101 violation

---

## 6. Checklist

- [ ] Hierarchical screen structure (Levels 1-4)
- [ ] AccessLevel matrix documented
- [ ] Multi-lang text on every widget
- [ ] Colour standard applied
- [ ] Faceplate template consistent across equipment types
- [ ] Alarm widget at the top of every screen
- [ ] Recipe + Trend + Diagnostic screens planned
- [ ] FAT prototypes approved

---

## 7. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_11_HMI.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_HMI.md`
- **Standards:** ISA-101, IEC 62714-1, NAMUR NE107
- **Glossary:** `01_GLOBAL_STANDARDS/lang_glossary/`

---

*v1.1.0 — Full English body (2026-05-23). Greenfield advantage: designing the HMI from the operator perspective from day one. A good HMI = less training + fewer mistakes.*
