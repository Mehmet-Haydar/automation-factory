---
title: HMI Design Standard
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_11_HMI.md]
status: ACTIVE
---

# DOMAIN_HMI_STANDARD.md — HMI Design Domain Standard

> Industry standard (ISA-101) + AUTOMATION_FACTORY design discipline for the Factory's HMI projects. Every HMI project follows this standard.

---

## 1. Core Principles (ISA-101)

1. **Minimum colour:** use colour only when it carries meaning; never use it for aesthetics
2. **Hierarchical layout:** Overview → Area → Equipment → Diagnostic (4 levels)
3. **High contrast, low fatigue:** grey-tone background, not white
4. **Operator-design:** the operator's perspective first, not the engineer's
5. **Consistency:** the same function looks the same everywhere

---

## 2. Colour Palette (ISA-101 Standard)

| Status | Colour | Hex | Use |
|--------|--------|-----|-----|
| Background | Light grey | `#F0F0F0` | All screens |
| Text | Dark grey | `#333333` | Standard text |
| Running / OK | Green | `#00C800` | Motor running, valve open OK |
| Idle / Off | Light grey | `#C0C0C0` | Idle, ready |
| Disabled | Dark grey | `#808080` | Out of service |
| Warning | Orange | `#FFA500` | Warning alarm |
| Critical (active) | Red + flash | `#FF0000` | Critical alarm active |
| Critical (ack) | Red (solid) | `#FF0000` | Acknowledged but still active |
| Info | Blue | `#0080FF` | Information message |
| Bypass / Forced | Magenta | `#C800C8` | Temporary override (WARNING) |
| Setpoint highlight | Light yellow | `#FFFFC0` | Active setpoint field |

**Forbidden:** 8+ colours on the same screen, bright neon colours, combinations that fail red-green colour-blindness.

---

## 3. Typography

| Property | Value |
|----------|-------|
| Font family | Sans-serif (Arial / Segoe UI / Roboto) |
| Min size (operator panel) | 14 pt |
| Min size (HMI desktop) | 12 pt |
| Critical alarm text | Bold |
| Title | 18-24 pt bold |
| Number (numeric display) | Monospaced (Consolas) |

---

## 4. Screen Hierarchy (4 Levels)

```
Level 1: PROCESS OVERVIEW (SCR001)
  • The plant on a single screen
  • Pump, conveyor, tank symbols
  • Live KPIs: production count, OEE, alarm count
  • Large touch targets (>40x40 mm)

Level 2: AREA OVERVIEW (SCR002-009)
  • A specific zone (Fill, Mix, Pack, etc.)
  • P&ID-like view
  • Device states + setpoint readouts

Level 3: EQUIPMENT FACEPLATE (SCR020-099)
  • Single-equipment detail
  • Set/Reset buttons
  • Mini trend
  • Alarm history

Level 4: DIAGNOSTIC (SCR090-099)
  • Engineer-only
  • Parameter changes
  • Calibration interfaces
```

---

## 5. Faceplate Standard

All faceplates share the **same layout**:

```
┌─────────────────────────────────┐
│ [Tag Name]    [Equipment Name]  │   ← Title (12 pt bold)
├─────────────────────────────────┤
│                                 │
│  [Status Icon]  Status: Running │   ← Status (green dot)
│                                 │
│  Setpoint: [_____50.0__]  rpm   │   ← Setpoint (NumericInput)
│  Actual:        47.3      rpm   │   ← Actual value
│  Runtime:      127:34     h:m   │
│                                 │
│  [START]  [STOP]  [RESET]       │   ← Buttons (large)
│                                 │
│  ↓ Diagnostics  ↑ Back          │
└─────────────────────────────────┘
```

Type-specific variants:
- Motor faceplate
- Valve faceplate (2-way / 3-way / modulating)
- Sensor faceplate (analog)
- PID faceplate (3-tab: SP/PV, Tuning, Trend)
- Recipe faceplate

---

## 6. Alarm Widget (Top Banner)

Fixed at the TOP of every screen:

```
┌─────────────────────────────────────────────┐
│ [!] 2 CRIT   [⚠] 5 WARN   [i] 12 INFO       │  
│              Last: ALM0042 (Comm Lost)      │
└─────────────────────────────────────────────┘
```

Clicking it goes to SCR010 Alarm List.

---

## 7. Multi-Language Strategy

### 7.1 Language List
- **EN** (always mandatory, fallback language)
- **DE** (German-customer standard)
- **TR** (Turkish customer)
- Others (FR/IT/ES) → as needed

### 7.2 Use the Glossary
All UI text comes from the concept_id system in `01_GLOBAL_STANDARDS/lang_glossary/GLOSSARY_BASE.md`.

### 7.3 Language Switch
- Pre-login language picker
- Or: persistent language switcher in the top-right corner
- Persistent setting (user preference in cookie/file)

---

## 8. Authority Hierarchy (Access Level)

```
Level 0 NONE        → Read-only (can navigate, no writes)
Level 1 OPERATOR    → Start/Stop/Reset, mode change (M01/M02)
Level 2 SUPERVISOR  → Recipe load/save, open M04 Maint
Level 3 ENGINEER    → Calibration, parameter change, M06 LOTO
Level 4 ADMIN       → User management, system configuration
```

Login system:
- Username + password (minimum)
- RFID card support (recommended)
- Auto-logout (15-30 min inactivity)
- Audit log (who, what, when changed)

---

## 9. Touch Discipline

- Min button: 30x30 mm (no gloves), 40x40 mm (with gloves)
- Critical-button feedback: visual + audible + haptic (if available)
- Long-press confirmation (for Reset, opening LOTO)
- Double-confirm dialog: "This will stop production. Continue? [Yes] [Cancel]"

---

## 10. Performance

- Screen open: < 1 s
- Button response: < 200 ms
- Trend chart load: < 2 s (last 1 hour)
- Alarm pop-up: < 500 ms

---

## 11. Browser HMI / WebVisu (CODESYS WebVisu, Siemens UnifiedHMI)

The same standards apply. Additional notes:
- HTML5 + Canvas-based
- HTTPS mandatory (TLS 1.2+)
- Browser compatibility list (Chrome 90+, Edge 90+, Firefox 88+)
- Mobile-responsive design (for tablets)

---

## 12. AUTOMATION_FACTORY Application

- **AI prompt:** `PROMPT_EXTRACT_HMI_FROM_CODE.md` (retrofit) / `PROMPT_SYSTEM_HMI_INTERFACE.md` (greenfield code gen)
- **RD spec:** `MDSCHEMA_RAWDATA_11_HMI.md`
- **Guide (retrofit):** `RETROFIT_EXTRACT_HMI.md`
- **Guide (greenfield):** `GREENFIELD_DESIGN_HMI.md`
- **Knowledge Base:** `KB_PITFALLS_HMI.md`

---

## 13. Standards Reference

- **ISA-101** Human Machine Interfaces for Process Automation Systems
- **IEC 62714-1** Engineering data exchange (AutomationML)
- **NAMUR NE107** Self-monitoring and diagnosis of field devices
- **ISA-88** Batch Control (recipe, procedure)
- **ASM Consortium** Abnormal Situation Management

---

*v1.1.0 — Full English body (2026-05-23). HMI factory domain standard. Every HMI project follows these rules.*
