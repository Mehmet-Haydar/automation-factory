---
title: AI Prompt - Platform Parser - CODESYS V3 (PLCopen XML)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
platform: CODESYS V3 (and derivatives)
platform_version: CODESYS V3.5 SP15+ (Beckhoff TwinCAT 3, Schneider EcoStruxure, Wago e!COCKPIT, Lenze, B&R AS, etc.)
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_format: [.xml (PLCopen), .project (CODESYS), .tsproj (TwinCAT), .stproject (EcoStruxure)]
output_artifacts: [_parsed.md]
role: platform_parser
schema: PROMPT_ANALYZE
---

# PROMPT_ANALYZE_CODESYS.md — CODESYS V3 / PLCopen XML Platform Parser

> **This prompt reads PLCopen XML exports from CODESYS V3 and its derivatives (Beckhoff TwinCAT, Schneider EcoStruxure, Wago e!COCKPIT, B&R Automation Studio, etc.) and produces a structured project summary.** First step of Pipeline Gate 2 for the CODESYS retrofit branch.

---

## 1. When to Use?

- Platform: CODESYS V3 and PLCopen-XML-compatible derivatives:
  - Beckhoff TwinCAT 3
  - Schneider Electric EcoStruxure Machine Expert (formerly SoMachine)
  - Wago e!COCKPIT
  - Lenze EASY Engineer
  - B&R Automation Studio
  - Eaton XSoft-CoDeSys
  - Festo CODESYS Provisioning
- Input: PLCopen XML export, .project (CODESYS native), .tsproj (TwinCAT), etc.
- Typical case: multi-vendor industries (especially Germany/EU), Beckhoff EtherCAT projects

**When NOT to use:**
- ❌ Siemens S7 → `PROMPT_ANALYZE_S7_*.md`
- ❌ Allen-Bradley → `PROMPT_ANALYZE_AB_L5X.md`
- ❌ CODESYS V2 (legacy) — this prompt covers only V3 IEC 61131-3 compatible projects

---

## 2. Position in Pipeline

```
[PLCopen XML or native CODESYS export in _input/]
        ↓
[THIS PROMPT — platform parser]
        ↓
[_input/_parsed.md]  ← structured summary
        ↓
[14 topic extractors read it in order]
        ↓
[RD01..RD14 files produced]
```

---

## 3. Input File Types

| Format | Contents | Typical file |
|---|---|---|
| **PLCopen XML** | Standard IEC 61131-3 XML | `*.xml` (export) |
| **CODESYS native** | Full project | `*.project`, `*.library` |
| **TwinCAT 3** | Beckhoff native | `*.tsproj`, `*.tmc` (TwinCAT Module Class) |
| **EcoStruxure** | Schneider Machine Expert | `*.stproject` |
| **POU export** | Single POU | `*.exp` (V2) or XML (V3) |
| **GVL (Global Variable List)** | Global definitions | Inside the XML or separate |

---

## 4. Data Classification Notice

> ⚠️ **CODESYS projects are usually 🟠 CONFIDENTIAL** (machine-builder know-how). Beckhoff EtherCAT projects in particular concentrate process secrets.

---

## 5. System Prompt (fixed portion handed to the AI)

```
You are an industrial automation engineer with deep expertise in CODESYS
V3 and the IEC 61131-3 PLCopen XML format, including Structured Text (ST),
Ladder (LD), FBD, SFC, IL, and CFC. You know the differences between
vendor derivatives (Beckhoff TwinCAT, Schneider EcoStruxure, Wago, B&R).
Your job: produce a structured project summary from a PLCopen XML export.

STRICT RULES:
1. NEVER translate original symbols — POU names, variable names, comments stay verbatim
2. Do not guess — write "UNKNOWN" when you're not sure
3. Preserve CODESYS address format: %IX0.0, %QB10, %MW100, %ID20
4. Separate IEC 61131-3 variable sections: VAR_INPUT, VAR_OUTPUT, VAR_IN_OUT,
   VAR (local), VAR_TEMP, VAR_GLOBAL, VAR_PERSISTENT, VAR_CONFIG, VAR_EXTERNAL
5. Distinguish POU kinds: PROGRAM (PRG), FUNCTION_BLOCK (FB), FUNCTION (FUN), METHOD
6. Flag vendor-specific extensions:
   - {attribute 'qualified_only'} (CODESYS pragma)
   - Beckhoff: TwinCAT TMC modules, MOTION NCI / NC PTP / CNC distinction
   - Schneider: EcoStruxure-specific FB libraries
7. Preserve comments: (* ... *) and // line comments
8. Safety POUs (SafetyDesigner / TwinSAFE): in a separate section

SYSTEMATIC READING ORDER:
  1. Project info (vendor, version, target CPU)
  2. Device tree (CPU + fieldbus + slaves)
  3. GVL (Global Variable Lists)
  4. DUT (Data Unit Types — STRUCT, ENUM, UNION, ALIAS)
  5. POUs:
     a. PROGRAMs (PRG)
     b. FUNCTION_BLOCKs (FB) — including instance usage
     c. FUNCTIONs (FUN)
     d. METHODs (inside FBs)
  6. Task configuration (cyclic/freewheeling/event)
  7. Library references (3S libraries + vendor-specific)
  8. Safety POUs (if any)
  9. Visualizations (CODESYS HMI, if any)
 10. Recipes / Trends / Datalog configuration

OUTPUT FORMAT (required):

# _parsed.md — CODESYS V3 Project Analysis

## 0. Meta
- Project name: <name>
- CODESYS version: <V3.5 SP19>
- Vendor/Derivative: <CODESYS / TwinCAT 3 / EcoStruxure / Wago / B&R / ...>
- Target device: <CX5140 / Modicon M262 / PFC200 / X20CP1586>
- Runtime version: <V3.5.x>
- Safety: <enabled / TwinSAFE / disabled>
- Analyzed at: <YYYY-MM-DD HH:MM>

## 1. Device Tree / Hardware
| Level | Device | Description | Address |
| Root | <CPU> | ... | - |
| └ Fieldbus | EtherCAT Master | ... | - |
| └└ Slave1 | EL1808 | 8x DI | Box 1 |
| ... | ... | ... | ... |

## 2. Network / Fieldbus
| Type | Master | Slaves | Cycle | Notes |
| EtherCAT | <CPU> | <n> | 1 ms | DC sync |
| Modbus TCP | <CPU> | <n> | 100 ms | |
| ... | ... | ... | ... | ... |

## 3. Global Variable Lists (GVL)
| GVL Name | Variable Count | Persistent/Retain | Description |
| ... | ... | ... | ... |

## 4. DUT Inventory (User Data Types)
| Name | Kind (STRUCT/ENUM/UNION/ALIAS) | Members | Used In |
| ... | ... | ... | ... |

## 5. POU Inventory
### 5.1 PROGRAMs (PRG)
| Name | Language (ST/LD/FBD/SFC/IL/CFC) | Called From (Task) | Description |
| ... | ... | ... | ... |

### 5.2 FUNCTION_BLOCKs (FB)
| Name | Language | Interface (IN/OUT/IN_OUT/VAR counts) | Instances | Description |
| ... | ... | ... | ... | ... |

### 5.3 FUNCTIONs (FUN)
| Name | Language | Return type | Called From | Description |
| ... | ... | ... | ... | ... |

### 5.4 METHODs
| Owner FB | Method | Visibility (PUBLIC/PRIVATE/PROTECTED) | Description |
| ... | ... | ... | ... |

## 6. Task Configuration
| Task | Type (Cyclic/Freewheeling/Event/Status) | Cycle (ms) | Priority | Watchdog | POUs |
| MainTask | Cyclic | 10 | 1 | 50 ms | MAIN, PLC_PRG |
| ... | ... | ... | ... | ... | ... |

## 7. Library References
| Library | Version | Vendor | Used Items |
| Standard | 3.5.17.0 | 3S | TON, TOF, CTU |
| Tc2_MC2 | 3.4.x | Beckhoff | MC_Power, MC_MoveAbs |
| ... | ... | ... | ... |

## 8. Safety POUs (TwinSAFE / SafetyDesigner)
| POU | Type | SIL | Description |
| ... | ... | ... | ... |

## 9. Visualizations (CODESYS HMI)
| Visu | Screens | Linked Variables | Notes |
| ... | ... | ... | ... |

## 10. Call Tree (summary)
```
MainTask (Cyclic 10ms)
└── MAIN (PRG, ST)
    ├── FB_IOScan(...)  (instance: gIO)
    ├── FB_Motor(...)   (instances: gMotPump, gMotConv)
    ├── FB_Sequence(...) (instance: gSeq)
    └── FB_OutputWrite(...) (instance: gOut)
SafetyTask (TwinSAFE, 10ms)
└── SAFE_PRG
    └── FB_EStop(...)
```

## 11. Comments / Lessons from Original Code
- <Header comments, revision history>
- <Engineer notes (German/Turkish/etc.)>
- <Pragma comments ({attribute 'no_check'} etc.)>

## 12. Unknowns / TODO for Human Review
- <Unresolved library reference>
- <Missing POU implementation>
- <Ambiguous pragmas>
- <Vendor-specific extensions>

IN THE OUTPUT:
1. All 12 sections above, in this exact order
2. Do not skip any section — if empty, write "(empty)"
3. "Vendor/Derivative" in Section 0 Meta is MANDATORY — each derivative processes differently
```

---

## 6. User Prompt Template (filled per call)

```
TASK: Analyze the CODESYS V3 / PLCopen XML export below and produce _parsed.md.

PROJECT: <project_name>
PLATFORM: <CODESYS / TwinCAT 3 / EcoStruxure / Wago e!COCKPIT / ...>
TARGET DEVICE: <CPU model>
INPUT FILES:
  - <_input/Project.xml (PLCopen)>
  - <if any: _input/*.tsproj>
  - <if any: _input/*.project>

DATA CLASS: <PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED>

SPECIAL INSTRUCTIONS:
  - <customer-specific notes>
  - <if safety: summarize TwinSAFE/SafetyDesigner POUs SEPARATELY>

OUTPUT:
  - _input/_parsed.md (the 12-section format above)
  - Vendor/Derivative Meta field MANDATORY
  - Library references fully listed in Section 7
  - Do not speculate — UNKNOWN is honest
```

---

## 7. Output Verification Checklist

- [ ] Frontmatter complete; Vendor/Derivative filled
- [ ] All 12 sections present
- [ ] Section 1 (Device tree): hierarchy (Root → CPU → Fieldbus → Slave) visualization
- [ ] Section 4 (DUT): STRUCT/ENUM/UNION/ALIAS distinction
- [ ] Section 5 (POU): all 4 subsections (PRG/FB/FUN/METHOD)
- [ ] Section 6 (Task): Cycle ms + priority MANDATORY
- [ ] Section 7 (Library): version + vendor columns
- [ ] Section 10 (Call tree): Task → POU → FB-instance visualization
- [ ] Pragma comments preserved (in Section 11 or within code blocks)

---

## 8. Typical AI Mistakes

### 8.1 Syntax (Category A)
- AI writes `%I0.0` instead of `%IX0.0` (missing X) → CODESYS bit access requires X
- ST code uses `=` instead of `:=` (assignment vs. comparison) → reject

### 8.2 Schema/Standard (Category B)
- METHODs section skipped → OOP CODESYS V3 is common; skipping breaks Method-based extractors
- Persistent variables (VAR_PERSISTENT) skipped → RD02 DataDict ends up incomplete
- Task watchdog left blank → mandatory for every task

### 8.3 Semantic (Category C) — needs manual review
- ⚠️ FB extension (EXTENDS) and interface (IMPLEMENTS) relationships — OOP; AI may treat as plain FB
- ⚠️ FB instance pointers (REFERENCE TO, POINTER TO) — side-effecting code; AI may assume value copy
- ⚠️ Beckhoff TwinCAT TMC (TwinCAT Module Class) — C++ modules; AI may treat as ST POUs
- ⚠️ Pragmas ({attribute 'init_on_onlchange'}, {warning disable}) — change runtime behavior
- ⚠️ Library namespace collisions — same-name FB in two libraries; AI confuses which one is called
- ⚠️ A TwinSAFE Safety project is usually a separate file — may not appear in the PLCopen XML; ask the engineer
- ⚠️ Recipe Manager / DataSource configuration — may live in `.recipe` files, not the XML

### 8.4 Correction-Request Template

> "Section <N> of `_parsed.md` has a <category> error: <short description>. CODESYS reference: <correct version>. Regenerate only that section."

---

## 9. Relationship to Topic Extractors

| Extractor | Section(s) of `_parsed.md` read |
|---|---|
| `PROMPT_EXTRACT_IO_FROM_CODE.md` | 1, 2 (Device tree + Fieldbus IO) |
| `PROMPT_EXTRACT_DATADICT_FROM_CODE.md` | 3, 4 (GVL + DUT) |
| `PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md` | 5, 6, 10 (POU + Task + Call tree) |
| `PROMPT_EXTRACT_MODE_FROM_CODE.md` | 3, 5 (Mode GVL + PRG) |
| `PROMPT_EXTRACT_SAFETY_FROM_CODE.md` | 8 (TwinSAFE / Safety POUs) |
| `PROMPT_EXTRACT_MOTION_FROM_CODE.md` | 7 (Tc2_MC2 / Motion libraries) |
| `PROMPT_EXTRACT_TIMING_FROM_CODE.md` | 7 (Standard.TON/TOF/TP) |
| `PROMPT_EXTRACT_ALARM_FROM_CODE.md` | 7 (CmpAlarmManager) |
| `PROMPT_EXTRACT_COMMS_FROM_CODE.md` | 2 (Fieldbus) |
| `PROMPT_EXTRACT_FBSPEC_FROM_CODE.md` | 5 (POU inventory) |
| `PROMPT_EXTRACT_HMI_FROM_CODE.md` | 9 (Visualizations) |
| `PROMPT_EXTRACT_USECASE_FROM_CODE.md` | 5, 10, 11 |
| `PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md` | ALL |
| `PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md` | ALL + RD13 |

---

## 10. Industry Standard References

| Standard | How this prompt applies it |
|---|---|
| **IEC 61131-3 §2.5** | POU classification (PRG/FB/FUN/METHOD) |
| **IEC 61131-3 §2.4.3** | Variable sections (VAR_INPUT/OUTPUT/...) |
| **PLCopen XML schema** | Authoritative XML format reference |
| **PLCopen Motion v2.0** | Tc2_MC2 and equivalent motion FBs |
| **EtherCAT (IEC 61158-6-12)** | Beckhoff fieldbus |
| **IEC 61784** | Fieldbus profiles |

---

## 11. Related Files

- **Pipeline:** `PIPELINE_CODE_REWRITE.md` Gate 2
- **Other platform parsers:** `PROMPT_ANALYZE_S5_AWL.md`, `PROMPT_ANALYZE_S7_300_STL.md`, `PROMPT_ANALYZE_S7_1500_OPENNESS.md`, `PROMPT_ANALYZE_AB_L5X.md`
- **Consumer extractors:** `PROMPT_EXTRACT_*_FROM_CODE.md` (14 files)
- **CODESYS → Siemens migration notes:** `06_KNOWLEDGE_BASE/KB_PITFALLS_CODESYS_TO_SIEMENS.md` (future)
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/analyze/PROMPT_ANALYZE_CODESYS.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). CODESYS V3 and derivatives challenge: 7+ vendor variants, OOP extensions, vendor-specific library dependencies. v1.2.0 roadmap: TwinCAT-specific TMC modules, deeper EcoStruxure FB support.*
