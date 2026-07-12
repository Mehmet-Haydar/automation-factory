---
title: Project Input Sources Matrix
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield]
status: ACTIVE
prerequisite: [GLOBAL_NAMING_STANDARD.md, FACTORY_MAESTRO.md]
related: [GLOBAL_METADATA_SCHEMA.md, METADATA_INPUT_GUIDE.md]
purpose: input_inventory
---

# DOMAIN_INPUT_SOURCES.md — Project Input Sources Matrix

> **Purpose of this file:** when starting a new project (retrofit or greenfield), answer **which source files provide which information** at a glance. Prevent starting without the required inputs.
>
> **Guiding principle:** both project types ultimately produce JSON in the same `08_METADATA_INPUT/` format. The paths differ; the destination is the same.

---

## 1. Two Paths — One Convergence Point

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│        RETROFIT PATH        │         │       GREENFIELD PATH       │
│                             │         │                             │
│ Legacy project archive      │         │ Customer spec / URS         │
│ (TIA Portal/S5/S7)          │         │ P&ID                        │
│ Legacy EPLAN                │         │ Mechanical design           │
│ Legacy HMI (WinCC)          │         │ Empty Excel template        │
│ Field observation           │         │                             │
│           ↓                 │         │           ↓                 │
│   EXTRACT prompts           │         │   FILL prompts + manual     │
│           ↓                 │         │           ↓                 │
└─────────────────────────────┘         └─────────────────────────────┘
              ↓                                       ↓
              └───────────────┬───────────────────────┘
                              ↓
              ┌─────────────────────────────────┐
              │   08_METADATA_INPUT/            │
              │   - motors.json                 │
              │   - valves.json                 │
              │   - sensors.json                │
              │   - pid_loops.json              │
              │   - alarms.json                 │
              │   - io_list.json                │
              │   - hardware_topology.json      │
              └─────────────────────────────────┘
                              ↓
              [from here on both projects share the same flow]
                              ↓
              SCL generation, OB skeleton, HMI tags, etc.
```

---

## 2. RETROFIT — Expected Inputs

### 2.1 Mandatory inputs (don't start without them)

| Source | Format | Content | Factory file that uses it |
|--------|--------|---------|---------------------------|
| **Legacy PLC project** | `.zap*`, `.zip`, `.s7p`, `.ap*` | Legacy FB/FC/DB/OB code | `RETROFIT_LEGACY_CODE_EXTRACT.md` (future) |
| **Legacy electrical schematics** | `.elk` (EPLAN), PDF | IO list, hardware inventory | `RETROFIT_IO_EXTRACT.md`, `RETROFIT_HARDWARE_ANALYSIS.md` |
| **Field hardware inventory** | Excel/manual | List of existing PLC, IO modules, drives | `RETROFIT_HARDWARE_ANALYSIS.md` |
| **Site photos/videos** | Visual | Label names, unlabelled wires, user buttons | KB_FEEDBACK_LOG (for record) |

### 2.2 Important inputs (you can work without them, but risk goes up)

| Source | Format | Content | What happens if missing |
|--------|--------|---------|------------------------|
| **Legacy HMI project** | WinCC Flex/Classic, RT | Screen tags, alarm texts | HMI from scratch + alarms guessed |
| **Mechanical drawing** | DWG/PDF | Sensor/valve locations | Tag naming becomes guesswork |
| **Process description** | Word/PDF/verbal | What the machine does | Sequence reverse-engineered |
| **Customer tag list** | Excel | "This valve is called X on our side" | More manual tag migration |
| **Fault/maintenance records** | Excel/CMMS | Frequent fault points | KB_PITFALLS won't fill up |

### 2.3 Bonus inputs (golden if available)

| Source | Value |
|--------|-------|
| **Legacy FAT/SAT report** | Basis for test scenarios |
| **Legacy operator manual** | For HMI logic |
| **Prior retrofit experience** (if any) | Lessons learned |
| **OEE / production records** | Real process behaviour |

### 2.4 Retrofit input → output map

| From this input file | This metadata is produced |
|---------------------|---------------------------|
| Legacy TIA archive (FB/FC) | `motors.json`, `valves.json`, partial `pid_loops.json` |
| Legacy TIA archive (DB) | `alarms.json`, parameter values |
| Legacy TIA archive (OB) | Sequence/state machine draft |
| EPLAN export | `io_list.json`, `hardware_topology.json` |
| WinCC export | HMI tag list, alarm texts |
| Field inventory | `hardware_topology.json` verification |

---

## 3. GREENFIELD — Expected Inputs

### 3.1 Mandatory inputs

| Source | Format | Content | Factory file |
|--------|--------|---------|--------------|
| **URS / Functional Spec** | Word/PDF | What the customer wants, functional scope | `GREENFIELD_FUNCTIONAL_SPEC_TO_SEQUENCE.md` (future) |
| **P&ID** | DWG/PDF | Equipment list, connection topology | `GREENFIELD_PI_DIAGRAM_PARSER.md` (future) |
| **Hardware selection list** (or selection criteria) | Excel | PLC type, IO module selection | `GREENFIELD_HARDWARE_SELECTION.md` |
| **Filled metadata Excel** | XLSX | `08_METADATA_INPUT/template_*.xlsx` | `METADATA_INPUT_GUIDE.md` |

### 3.2 Important inputs

| Source | Content | What happens if missing |
|--------|---------|------------------------|
| **Mechanical-design output** | Sensor/valve positions, axis count | Tag naming becomes guesswork |
| **Customer standard** (if any) | Naming format, colour code, language | Factory standard applied |
| **Risk analysis (HAZOP/risk register)** | Safety requirements | Safety model becomes guesswork |
| **Operator-team input** | HMI ergonomics | A single screen template gets designed |

### 3.3 Bonus inputs

| Source | Value |
|--------|-------|
| **Legacy project of a similar machine** | Fast template source |
| **HMI from the customer's other projects** | Style consistency |
| **OEM documentation** (motor/drive/sensor) | Vendor-specific parameters |

### 3.4 Greenfield input → output map

| From this input file | This metadata is produced |
|---------------------|---------------------------|
| URS | Sequence/state machine draft, functional mode list |
| P&ID | Initial inventory of `motors.json`, `valves.json`, `sensors.json` |
| Filled Excel | `motors.json`, `valves.json`, `sensors.json`, `pid_loops.json`, `alarms.json` (final) |
| Hardware selection | `hardware_topology.json`, `io_list.json` |
| Risk analysis | F-PLC requirements, safety FB list |

---

## 4. Comparison Table — Which Input, When

| Input type | Retrofit | Greenfield | Notes |
|------------|----------|------------|-------|
| URS / Spec | Optional | **Mandatory** | In retrofit the legacy machine acts as the "spec" |
| P&ID | Optional | **Mandatory** | In retrofit the legacy electrical schematic is usually enough |
| Legacy PLC code | **Mandatory** | N/A | This is the definition of retrofit |
| EPLAN | **Mandatory** | Important | May be freshly drawn in greenfield |
| Filled metadata Excel | Optional (produced) | **Mandatory** | Primary source for greenfield |
| Field observation | **Mandatory** | Optional | In retrofit the machine exists, you must see it |
| Risk analysis | Recommended | **Mandatory** | New machine = new CE |
| Legacy HMI project | Important | N/A | |

---

## 5. Missing-Input Situation — Decision Tree

```
New project arrives.
│
├─ Retrofit or Greenfield?
│   │
│   ├─ RETROFIT
│   │   ├─ Is legacy PLC code available?
│   │   │   ├─ NO → treat as greenfield (big risk!)
│   │   │   └─ YES → continue
│   │   ├─ Is EPLAN available?
│   │   │   ├─ NO → manual IO list from field + photos (fallback inside RETROFIT_IO_EXTRACT)
│   │   │   └─ YES → use script_eplan_xml_to_io.py (future)
│   │   └─ Is the process description available?
│   │       ├─ NO → extract from code via RETROFIT_SEQUENCE_REVERSE.md (future)
│   │       └─ YES → use as URS
│   │
│   └─ GREENFIELD
│       ├─ Is URS available?
│       │   ├─ NO → STOP, request from the customer. Without a URS the project does not start.
│       │   └─ YES → continue
│       ├─ Is P&ID available?
│       │   ├─ NO → derive equipment list from URS (with missing-info note)
│       │   └─ YES → parse via script
│       └─ Is the metadata Excel filled?
│           ├─ NO → fill template_*.xlsx with the customer (METADATA_INPUT_GUIDE)
│           └─ YES → convert to JSON, continue
```

---

## 6. Input-Gathering Checklist (Project Kick-Off)

When starting a new project, work through this list explicitly (don't rely on memory):

### For retrofit projects:
- [ ] Legacy PLC archive received (`.zap`, `.zip`, etc.)
- [ ] Legacy PLC archive opened, FB/FC inventory extracted
- [ ] Electrical schematic (EPLAN/PDF) received
- [ ] Field hardware inventory done (PLC, IO, drive list)
- [ ] Site-visit photos taken
- [ ] Legacy HMI project received (if any)
- [ ] Is the process description available? (if not, plan reverse engineering)
- [ ] Tag list received (legacy name → new name mapping starts)
- [ ] Customer's special requests recorded in writing

### For greenfield projects:
- [ ] URS / functional spec received
- [ ] P&ID received
- [ ] Mechanical design output (if any)
- [ ] Hardware selection criteria defined
- [ ] `template_motors.xlsx` filled with the customer
- [ ] `template_valves.xlsx` filled
- [ ] `template_sensors.xlsx` filled
- [ ] `template_pid_loops.xlsx` filled (if any)
- [ ] `template_alarms.xlsx` filled
- [ ] Risk analysis / HAZOP report received
- [ ] Customer standards (if any) taken as a reference

---

## 7. What to Do When Inputs Are Missing in the Field

The inputs are incomplete but the project must start. What to do?

| Missing | Stop-gap | Long-term |
|---------|----------|-----------|
| No legacy PLC code | Derive the state machine from site observation + operator interviews | Push the customer, find a backup |
| No EPLAN | Manual IO list (Excel) | Draw new EPLAN |
| No URS | Workshop with the customer, build a joint document | URS is never skipped |
| No P&ID | Derive from mechanical design | P&ID is required |
| No metadata Excel | Initial draft via AI from URS + P&ID, customer approval | Metadata Excel is required on every project |

**Every missing input is logged in `KB_FEEDBACK_LOG.md`.** Records of "this was missing on this project, here's how we solved it" help future projects.

---

## 8. Maintenance of This File

- If a new input type is discovered (e.g. simulation CAD model) → add to the relevant table
- If a new project type is added (today retrofit/greenfield, in the future maybe "modernization") → extend the matrix
- The missing-input remedies (Section 7) get richer with site experience

---

## 9. Related Files

- `02_PROJECT_TYPES/RETROFIT/RETROFIT_MAESTRO.md` — retrofit workflow
- `02_PROJECT_TYPES/GREENFIELD/GREENFIELD_MAESTRO.md` — greenfield workflow
- `01_GLOBAL_STANDARDS/rules/GLOBAL_METADATA_SCHEMA.md` — JSON schemas
- `08_METADATA_INPUT/METADATA_INPUT_GUIDE.md` — metadata Excel guide
- `06_KNOWLEDGE_BASE/KB_FEEDBACK_LOG.md` — site missing-input log

---

*v1.1.0 — Full English body (2026-05-23). No project comes out right without the right inputs. This file is the gatekeeper.*
