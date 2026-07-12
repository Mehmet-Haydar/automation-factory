---
title: AI Prompt - Platform Parser - Siemens S7-1500 (TIA Portal Openness XML)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
platform: S7-1500
platform_version: TIA Portal V14+
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_format: [.xml, .scl, .udt, .db, project.zip]
output_artifacts: [_parsed.md]
role: platform_parser
schema: PROMPT_ANALYZE
---

# PROMPT_ANALYZE_S7_1500_OPENNESS.md — TIA V14+ Platform Parser

> **This prompt reads a Siemens TIA Portal V14+ Openness XML export and turns the project into a structured summary every topic extractor can consume.** First step of Pipeline Gate 2.

---

## 1. When to Use?

- Platform: Siemens S7-1500 (TIA Portal V14, V15, V16, V17, V18+)
- Input format: Openness export (.xml), direct .scl/.db/.udt files, or a TIA `project.zip`
- Typical case: retrofit project with existing TIA Portal code; the new code targets the same or a different PLC platform

**When NOT to use:**
- ❌ S7-300/400 (STL/Classic STEP 7) → `PROMPT_ANALYZE_S7_300_STL.md`
- ❌ S5 → `PROMPT_ANALYZE_S5_AWL.md`
- ❌ Allen-Bradley → `PROMPT_ANALYZE_AB_L5X.md`

---

## 2. Position in Pipeline

```
[TIA export in _input/]
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

A TIA Portal project can be exported in several formats. This prompt recognizes:

| Format | Contents | Typical file |
|---|---|---|
| **Openness XML** | XML representation of every PLC block | `*.xml` (per-block) or `project.zip` |
| **SCL source** | Structured Control Language source | `*.scl` |
| **UDT** | User Data Types | `*.udt` |
| **DB** | Data Blocks | `*.db` |
| **Tag table export** | Symbol table (variables) | `*.xml` (PlcTagTable) |
| **HW config** | Hardware configuration | `*.xml` (Device tree) |

---

## 4. Data Classification Notice

> ⚠️ **TIA Portal export files are usually 🟠 CONFIDENTIAL** (customer trade secret, machine internals). Per `GLOBAL_DATA_CLASSIFICATION.md` Section 3:
>
> - 🟠 → DO NOT upload to public AI services (ChatGPT.com, claude.ai web, etc.)
> - 🟠 → Use self-hosted or Enterprise AI (Claude API on a private deploy, Azure OpenAI Enterprise)
> - 🟠 → In Cursor, use a local model or enterprise tier
>
> This prompt cannot run until the data class has been verified.

---

## 5. System Prompt (fixed portion handed to the AI)

```
You are an industrial automation engineer with expertise in TIA Portal V14+
and the Siemens S7-1500 architecture. Your job: produce a structured project
summary from a TIA Portal Openness export.

STRICT RULES:
1. NEVER translate original symbols (German, Turkish, any language) — keep them verbatim
2. Do not guess — write "UNKNOWN" when you're not sure
3. Preserve address format (including the % sign): %I1.2, %QW20, %MD100
4. Move comment blocks (// or (*...*)) verbatim into the Description field
5. CONFIDENTIAL: keep no proprietary data in the summary except the project/customer name
6. Output is Markdown — not JSON. AI-friendly structure.

SYSTEMATIC READING ORDER:
  1. HW Config (Device tree) → CPU type, modules, IPs
  2. PlcTagTable → all symbol definitions
  3. UDTs → struct definitions
  4. DBs → data blocks (instance and global)
  5. OBs (Organization Blocks) → main program, alarm OBs, error OBs
  6. FBs (Function Blocks) → reusable logic
  7. FCs (Functions) → stateless functions
  8. Safety blocks (if any, F-prefixed) → in a separate section

OUTPUT FORMAT (required):

# _parsed.md — TIA Portal Project Analysis

## 0. Meta
- Project name: <name>
- TIA version: <V18.0.x>
- CPU type: <CPU 1515-2 PN>
- Firmware: <V2.9.x>
- Safety: <enabled/disabled>
- Analyzed at: <YYYY-MM-DD HH:MM>

## 1. Hardware Configuration
| Slot | Module | Order Number | Address Range | Notes |
| ... | ... | ... | ... | ... |

## 2. Network
| Interface | IP | Subnet | Profinet Devices | Notes |
| ... | ... | ... | ... | ... |

## 3. Tag Table Summary
- Total symbols: <N>
- DI: <n>, DO: <n>, AI: <n>, AO: <n>
- M (markers): <n>
- DB references: <n>

## 4. UDT Inventory
| Name | Members | Used In |
| ... | ... | ... |

## 5. DB Inventory
| Name | Type (Instance/Global) | UDT/Type | Optimized | Description |
| ... | ... | ... | ... | ... |

## 6. OB Inventory
| Number | Name | Cycle/Event | Description |
| ... | ... | ... | ... |

## 7. FB Inventory
| Name | Interface (IN/OUT/INOUT/STAT) counts | Called From | Description |
| ... | ... | ... | ... |

## 8. FC Inventory
| Name | Interface | Called From | Description |
| ... | ... | ... | ... |

## 9. Safety Blocks (F-blocks)
| Name | Type | F-DB | Description |
| ... | ... | ... | ... |

## 10. Call Tree (summary)
```
OB1
├── FC_ScanInputs
├── FB_Motor (DB_Motor_Pump01)
├── FB_Motor (DB_Motor_Conveyor01)
├── FC_Sequence
│   └── FB_TimedStep
└── FC_WriteOutputs
```

## 11. Comments / Lessons from Original Code
- <Important comments / header info captured from the original code>
- <Engineer notes, "DO NOT TOUCH" markers, etc.>

## 12. Unknowns / TODO for Human Review
- <Ambiguities the AI could not resolve>
- <Missing file references>
- <Contradictory definitions>

IN THE OUTPUT:
1. The 12 sections above, in this exact order
2. Do not skip any section — if empty, write "(empty)"
3. Section 12 (Unknowns) carries real value — this is where the AI is honest
```

---

## 6. User Prompt Template (filled per call)

```
TASK: Analyze the TIA Portal export below and produce _parsed.md.

PROJECT: <project_name>
PLATFORM: S7-1500 (TIA V<version>)
INPUT FILES:
  - <_input/PlcTagTable.xml>
  - <_input/Blocks/*.xml>
  - <_input/HwConfig.xml>
  - <if any: _input/project.zip contents>

DATA CLASS: <PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED>

SPECIAL INSTRUCTIONS (if any):
  - <customer-specific notes>

OUTPUT:
  - _input/_parsed.md (the 12-section format above)
  - Any contradictions listed in Section 12
  - Do not speculate — UNKNOWN is honest
```

---

## 7. Output Verification Checklist

The AI-produced `_parsed.md` must contain (checklist):

- [ ] Frontmatter complete (project, TIA version, CPU, date)
- [ ] All 12 sections present (header + "(empty)" if vacant)
- [ ] Section 1 (Hardware): at least CPU + 1 module listed
- [ ] Section 3 (Tag summary): total count + distribution
- [ ] Sections 6/7/8 (OB/FB/FC): at minimum the "Called From" column populated
- [ ] Section 10 (Call tree): ASCII tree rendered
- [ ] Section 11 (Comments): at least 3 noteworthy comments quoted from the original
- [ ] Section 12 (Unknowns): non-empty (every real project has at least one ambiguity)
- [ ] German/Turkish symbol names NOT translated

---

## 8. Typical AI Mistakes

### 8.1 Syntax (Category A) — auto-detectable
- AI accidentally writes `%I 1.2` (space) → Markdown linter catches it
- ASCII call tree uses `+--` instead of `├──` → Markdown rendering breaks

### 8.2 Schema/Standard (Category B) — validator catches
- AI skips one or two of the 12 sections → `script_md_schema_validator.py --schema PROMPT_ANALYZE` rejects
- Frontmatter missing TIA version → reject

### 8.3 Semantic (Category C) — needs manual review
- ⚠️ AI sees German symbol `Greifer_oben` and writes "Gripper top" in the Description **while deleting the original** — rule: keep the original; any translation belongs in the comment field
- ⚠️ AI mistakes Safety blocks (F-prefix) for ordinary FBs, places them in Section 7 instead of Section 9 → F-prefix check is mandatory
- ⚠️ Instance DB vs. Global DB distinction gets dropped → Section 5 `Type` column is mandatory
- ⚠️ Dead-code FBs (never called) are still reported as "in use" → if "Called From" is empty, mark as `(orphan)`
- ⚠️ A "TODO" sits in a comment but the AI files it in Section 11 instead of Section 12 → TODOs always go to Section 12

### 8.4 Correction-Request Template

> "Section <N> of `_parsed.md` has a <category> error: <short description>. Correct version: <expected>. Regenerate only that section."

---

## 9. Relationship to Topic Extractors

This prompt only produces `_parsed.md`. The 14 topic extractors then read that file in order:

| Extractor | Section(s) of `_parsed.md` read |
|---|---|
| `PROMPT_EXTRACT_IO_FROM_CODE.md` | 1, 3 (HW + Tag Table) |
| `PROMPT_EXTRACT_DATADICT_FROM_CODE.md` | 4, 5 (UDT + DB) |
| `PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md` | 6, 7, 10 (OB + FB + Call tree) |
| `PROMPT_EXTRACT_MODE_FROM_CODE.md` | 5, 6 (Mode DBs + OBs) |
| `PROMPT_EXTRACT_SAFETY_FROM_CODE.md` | 9 (F-blocks) |
| `PROMPT_EXTRACT_MOTION_FROM_CODE.md` | 4, 5, 7 (drive UDT + DB + FB) |
| `PROMPT_EXTRACT_TIMING_FROM_CODE.md` | 5, 7 (timer instance DBs + FB call) |
| `PROMPT_EXTRACT_ALARM_FROM_CODE.md` | 6 (alarm OBs) |
| `PROMPT_EXTRACT_COMMS_FROM_CODE.md` | 2 (Network) |
| `PROMPT_EXTRACT_FBSPEC_FROM_CODE.md` | 7, 8 (FB + FC) |
| `PROMPT_EXTRACT_HMI_FROM_CODE.md` | 3, 5 (HMI tags + DBs) |
| `PROMPT_EXTRACT_USECASE_FROM_CODE.md` | 6, 10, 11 (OB + call tree + comments) |
| `PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md` | 6, 7, 8, 10, 11 (legacy code documentation) |
| `PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md` | All (pattern detection across the project) |

---

## 10. Industry Standard References

| Standard | How this prompt applies it |
|---|---|
| **IEC 61131-3 §2.5** | POU (Program Organization Unit) classification — OB/FB/FC distinction preserved |
| **PLCopen** | FB interface conventions — IN/OUT/INOUT/STAT layers counted |
| **Siemens Openness API reference** | XML schema structure, attribute names |

---

## 11. Related Files

- **Pipeline:** `PIPELINE_CODE_REWRITE.md` Gate 2
- **Other platform parsers:** `PROMPT_ANALYZE_S5_AWL.md`, `PROMPT_ANALYZE_S7_300_STL.md`, `PROMPT_ANALYZE_AB_L5X.md`, `PROMPT_ANALYZE_CODESYS.md`
- **Consumer extractors:** `PROMPT_EXTRACT_*_FROM_CODE.md` (14 files)
- **Data classification:** `GLOBAL_DATA_CLASSIFICATION.md`
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`
- **Knowledge base:** `06_KNOWLEDGE_BASE/KB_PITFALLS_SAFETY.md` (for F-block analysis)

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/analyze/PROMPT_ANALYZE_S7_1500_OPENNESS.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0 was the platform-aware analysis pattern file in Turkish; the remaining four platforms (S5, S7-300, AB, CoDeSys) follow this structure. v1.2.0 roadmap: deeper F-PLC handling for Failsafe TIA, multi-CPU systems.*
