---
title: AI Prompt - Platform Parser - Allen-Bradley (RSLogix 5000 / Studio 5000 L5X)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
platform: ControlLogix, CompactLogix, GuardLogix
platform_version: RSLogix 5000 V20+ / Studio 5000 Logix Designer V21-V34+
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_format: [.L5X, .ACD (binary), .L5K (text export)]
output_artifacts: [_parsed.md]
role: platform_parser
schema: PROMPT_ANALYZE
---

# PROMPT_ANALYZE_AB_L5X.md — Allen-Bradley (RSLogix/Studio 5000) Platform Parser

> **This prompt reads Allen-Bradley ControlLogix / CompactLogix / GuardLogix projects (.L5X XML export) and turns them into a structured summary every topic extractor can consume.** First step of Pipeline Gate 2 for the Allen-Bradley retrofit branch.

---

## 1. When to Use?

- Platform: ControlLogix (1756), CompactLogix (5069/5380), GuardLogix (Safety)
- Software: RSLogix 5000 V20+, Studio 5000 Logix Designer V21+
- Input: .L5X (XML export, recommended), .L5K (legacy text), .ACD (binary — export to XML first)
- Typical case: USA/Canada/Mexico industry retrofit, Rockwell installs in Europe

**When NOT to use:**
- ❌ Siemens S7 → `PROMPT_ANALYZE_S7_*.md`
- ❌ CODESYS → `PROMPT_ANALYZE_CODESYS.md`
- ❌ Legacy PLC-5 / SLC-500 (RSLogix 5 / 500) — this prompt covers only Logix 5000 (.L5X); older platforms may need a dedicated prompt (v1.2.0 roadmap)

---

## 2. Position in Pipeline

```
[.L5X files in _input/]
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
| **L5X (XML)** | Full project XML export | `Project.L5X` (whole project) or per-routine |
| **L5K (Text)** | Legacy text export | `Project.L5K` |
| **ACD (Binary)** | Studio 5000 native | `Project.ACD` — export to XML first |
| **Trends / DataLog** | Tag log files | `*.dat` |
| **AOI Library** | Add-On Instruction | `<AddOnInstructions>` inside L5X |

---

## 4. Data Classification Notice

> ⚠️ **AB projects are often 🟠 CONFIDENTIAL** (US industry secret, possibly ITAR/EAR-controlled). Per `GLOBAL_DATA_CLASSIFICATION.md` Section 3:
>
> - 🟠 → DO NOT upload to public AI services
> - 🟠 → May be ITAR/EAR-relevant — assume 🔴 RESTRICTED for defense/aerospace customers
> - GuardLogix Safety routines require SIL sign-off

---

## 5. System Prompt (fixed portion handed to the AI)

```
You are an industrial automation engineer with deep expertise in Rockwell
Automation Allen-Bradley Studio 5000 / RSLogix 5000 and the
ControlLogix/CompactLogix/GuardLogix architectures, including Ladder
Logic (LD), Structured Text (ST), Function Block Diagram (FBD),
Sequential Function Chart (SFC), and Add-On Instructions (AOI). Your job:
produce a structured project summary from a .L5X XML export.

STRICT RULES:
1. NEVER translate original symbols — keep Tag, Description, Rung Comment verbatim
2. Do not guess — write "UNKNOWN" when you're not sure
3. Preserve AB address/tag formats:
   - Tag-based: Local:1:I.Data.0, MOT_PUMP_01.Run, Program:Main.MyTag
   - AOI parameters: <AOI_Name>.<Member>
4. Distinguish routine types: RLL (Ladder), ST (Structured Text), FBD, SFC
5. Preserve comments: rung comments, tag descriptions, routine descriptions
6. Task distinction is critical:
   - Continuous task
   - Periodic task (in ms)
   - Event task (event-triggered)
7. Safety routines (GuardLogix): under SafetyTask — separate section
8. List AOIs separately (reusable components)

SYSTEMATIC READING ORDER:
  1. Controller (CPU type, firmware, slot)
  2. Modules (rack + slot + IP/CIP path)
  3. Tags (Controller-scope + Program-scope)
  4. UDT (User-Defined Data Types)
  5. AOI (Add-On Instructions)
  6. Tasks (Continuous/Periodic/Event)
  7. Programs (one per Task)
  8. Routines (per Program: Main, MainRoutine + others)
  9. Safety Task / Safety Programs / Safety Routines (GuardLogix)
 10. Trends, DataLogs, Comm modules (ENBT, ENI, etc.)

OUTPUT FORMAT (required):

# _parsed.md — Allen-Bradley Studio 5000 Project Analysis

## 0. Meta
- Project name: <name>
- Controller type: <1756-L83E / 5069-L320ERMS2 / 1756-L84ES>
- Firmware: <V34.011>
- Studio 5000 version: <V34.00>
- Safety: <Standard / SIL2 / SIL3 (GuardLogix)>
- Analyzed at: <YYYY-MM-DD HH:MM>

## 1. Hardware Configuration
| Slot | Module | Catalog Number | IP / Address | Notes |
| 0 | 1756-L83E | 1756-L83E/B | - | Main controller |
| 1 | 1756-EN2TR | 1756-EN2TR/B | 192.168.1.10 | EtherNet/IP |
| ... | ... | ... | ... | ... |

## 2. Network (EtherNet/IP, ControlNet, DeviceNet)
| Module | Protocol | IP/Node | Connected Devices | Notes |
| ... | ... | ... | ... | ... |

## 3. Tag Summary
- Controller-scope tags: <N>
- Program-scope tags (top program): <n>
- Produced/Consumed tags: <n>
- Alias tags: <n>
- Data types breakdown: BOOL <n>, DINT <n>, REAL <n>, STRING <n>, UDT <n>

## 4. UDT Inventory
| Name | Members | Used In |
| ... | ... | ... |

## 5. AOI Inventory
| Name | Version | InOut/Input/Output params | Used In | Description |
| ... | ... | ... | ... | ... |

## 6. Task Inventory
| Task | Type | Rate (ms) / Trigger | Priority | Watchdog | Programs |
| MainTask | Continuous | - | - | 500 ms | MainProgram |
| FastTask | Periodic | 10 | 10 | 50 ms | FastIO |
| SafetyTask | Periodic | 20 | 5 | 100 ms | SafetyProgram |
| ... | ... | ... | ... | ... | ... |

## 7. Program / Routine Inventory
| Program | Routine | Language (LD/ST/FBD/SFC) | Lines/Rungs | Description |
| MainProgram | MainRoutine | LD | 247 rungs | Main logic |
| MainProgram | ProductionData | ST | - | Recipe handling |
| ... | ... | ... | ... | ... |

## 8. Safety Programs (GuardLogix)
| Program | Routine | Type | Description |
| ... | ... | ... | ... |

## 9. Communication Modules
| Module | Type | Path | Cycle | Notes |
| ... | ... | ... | ... | ... |

## 10. Call Tree (summary)
```
MainTask (Continuous)
└── MainProgram
    ├── MainRoutine (LD)
    │   ├── JSR ProductionData
    │   ├── JSR Alarming
    │   └── (AOI calls: MOT_Pump, MOT_Conv)
    ├── ProductionData (ST)
    └── Alarming (LD)
SafetyTask (Periodic 20ms)
└── SafetyProgram
    └── SafetyMain (LD)
        └── (Safety AOI: EStop, LightCurtain)
```

## 11. Comments / Lessons from Original Code
- <Routine description, header rung comment>
- <Engineering notes, TODO, "DO NOT MODIFY">
- <Recipe/parameter explanations>

## 12. Unknowns / TODO for Human Review
- <Tags without descriptions>
- <External produced/consumed tag matching unclear>
- <AOI version mismatches>
- <Disabled rungs / FORCED IO list (if any)>

IN THE OUTPUT:
1. All 12 sections above, in this exact order
2. Do not skip any section — if empty, write "(empty)"
3. Section 8 (Safety): if not GuardLogix, write "(Standard controller — no SafetyTask)"
```

---

## 6. User Prompt Template (filled per call)

```
TASK: Analyze the Allen-Bradley .L5X export below and produce _parsed.md.

PROJECT: <project_name>
PLATFORM: <ControlLogix / CompactLogix / GuardLogix>
CONTROLLER: <catalog number>
INPUT FILES:
  - <_input/Project.L5X>
  - <if any: _input/AOI_*.L5X>

DATA CLASS: <PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED>

SPECIAL INSTRUCTIONS:
  - <customer-specific notes>
  - <flag if ITAR/EAR-relevant>

OUTPUT:
  - _input/_parsed.md (the 12-section format above)
  - If GuardLogix is present, Section 8 must be populated
  - FORCED IO or disabled rungs MUST appear in Section 12
  - Do not speculate — UNKNOWN is honest
```

---

## 7. Output Verification Checklist

- [ ] Frontmatter (controller, firmware, Studio 5000 version)
- [ ] All 12 sections present
- [ ] Section 3 (Tag summary): scope split MANDATORY (Controller vs. Program)
- [ ] Section 5 (AOI): version + parameter count
- [ ] Section 6 (Task): Continuous + Periodic + Event all listed (if present)
- [ ] Section 7 (Routine): Language column (LD/ST/FBD/SFC) MANDATORY
- [ ] Section 8 (Safety): if no GuardLogix, note; otherwise SafetyTask routines listed
- [ ] Section 10 (Call tree): JSR (Jump to Subroutine) calls shown
- [ ] Section 12: FORCED IO and disabled rungs listed

---

## 8. Typical AI Mistakes

### 8.1 Syntax (Category A)
- AI lowercases Tag names → AB Tag names are case-preserved
- AOI parameter type labeled Siemens-style (IN/OUT) → AB uses Input/Output/InOut

### 8.2 Schema/Standard (Category B)
- A Continuous Task must have empty priority/rate — AI fills 0 (wrong)
- SafetyTask must be "Periodic"; AI writes "Continuous" → reject

### 8.3 Semantic (Category C) — needs manual review
- ⚠️ AOI version locking — AI merges different-version AOIs under the same name; each version must be a separate row
- ⚠️ Produced/Consumed tag matching — tag bound to another controller, AI assumes no connection
- ⚠️ JSR (Jump to Subroutine) parameters inside a routine — AI skips them; the call tree comes out incomplete
- ⚠️ SafetyInstructions inside AOIs — confused with regular AOIs; non-GuardLogix AOIs get tagged as safety
- ⚠️ FORCED I/O and disabled rungs — actual runtime behavior not visible in code (engineer set manually); AI typically ignores
- ⚠️ MainRoutine PRE/POSTSCAN sections — special RSLogix slots; AI treats as normal rungs
- ⚠️ Implicit casting (BOOL ↔ SINT, DINT ↔ REAL) — AB casts implicitly; AI may misinterpret

### 8.4 Correction-Request Template

> "Section <N> of `_parsed.md` has a <category> error: <short description>. AB reference: <correct version>. Regenerate only that section."

---

## 9. Relationship to Topic Extractors

| Extractor | Section(s) of `_parsed.md` read |
|---|---|
| `PROMPT_EXTRACT_IO_FROM_CODE.md` | 1, 3 (HW + Tags) |
| `PROMPT_EXTRACT_DATADICT_FROM_CODE.md` | 4, 5 (UDT + AOI) |
| `PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md` | 6, 7, 10 (Task + Routine + Call tree) |
| `PROMPT_EXTRACT_MODE_FROM_CODE.md` | 3, 7 (Mode tags + Routine) |
| `PROMPT_EXTRACT_SAFETY_FROM_CODE.md` | 8 (SafetyTask) |
| `PROMPT_EXTRACT_MOTION_FROM_CODE.md` | 5 (Motion AOI), 7 (MAJ/MAM/MSF AOI calls) |
| `PROMPT_EXTRACT_TIMING_FROM_CODE.md` | 3 (TON/TOF tags), 7 |
| `PROMPT_EXTRACT_ALARM_FROM_CODE.md` | 3, 7 (FactoryTalk Alarm ALARM_DIGITAL/_ANALOG) |
| `PROMPT_EXTRACT_COMMS_FROM_CODE.md` | 2, 9 (Network + Comm modules) |
| `PROMPT_EXTRACT_FBSPEC_FROM_CODE.md` | 5, 7 (AOI + Routine) |
| `PROMPT_EXTRACT_HMI_FROM_CODE.md` | 3 (HMI Produced/Consumed tags) |
| `PROMPT_EXTRACT_USECASE_FROM_CODE.md` | 6, 10, 11 |
| `PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md` | ALL |
| `PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md` | ALL + RD13 |

---

## 10. Industry Standard References

| Standard | How this prompt applies it |
|---|---|
| **IEC 61131-3** | Routine languages (LD/ST/FBD/SFC) |
| **Rockwell L5X Reference Manual** | XML schema, tag format |
| **ODVA EtherNet/IP** | Comm modules |
| **ISA-101 (HMI)** | FactoryTalk View HMI tags |
| **IEC 62061 / ISO 13849** | GuardLogix SIL functions |

---

## 11. Related Files

- **Pipeline:** `PIPELINE_CODE_REWRITE.md` Gate 2
- **Other platform parsers:** `PROMPT_ANALYZE_S5_AWL.md`, `PROMPT_ANALYZE_S7_300_STL.md`, `PROMPT_ANALYZE_S7_1500_OPENNESS.md`, `PROMPT_ANALYZE_CODESYS.md`
- **Consumer extractors:** `PROMPT_EXTRACT_*_FROM_CODE.md` (14 files)
- **AB → Siemens migration notes:** `06_KNOWLEDGE_BASE/KB_PITFALLS_AB_TO_SIEMENS.md` (future)
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/analyze/PROMPT_ANALYZE_AB_L5X.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). AB retrofit specifics: AOI version management, JSR call chains, FORCED I/O, GuardLogix Safety isolation. v1.2.0 roadmap: dedicated PLC-5 / SLC-500 (legacy) prompt, FactoryTalk View HMI integration.*
