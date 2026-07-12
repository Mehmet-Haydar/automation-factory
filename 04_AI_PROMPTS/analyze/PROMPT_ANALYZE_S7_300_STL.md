---
title: AI Prompt - Platform Parser - Siemens S7-300/400 (Classic STEP 7 STL)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
platform: S7-300, S7-400
platform_version: STEP 7 V5.5 / V5.6 (Classic, SIMATIC Manager)
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_format: [.awl, .scl, .gr7, .zap, .zip (S7P), STL listing]
output_artifacts: [_parsed.md]
role: platform_parser
schema: PROMPT_ANALYZE
---

# PROMPT_ANALYZE_S7_300_STL.md — Siemens S7-300/400 (Classic STEP 7) Platform Parser

> **This prompt reads Siemens S7-300/400 (Classic STEP 7 V5.x) projects and turns them into a structured summary every topic extractor can consume.** First step of Pipeline Gate 2 for the S7 Classic retrofit branch.

---

## 1. When to Use?

- Platform: Siemens S7-300, S7-400, S7-400H, S7-400F/FH
- Software: STEP 7 V5.5/V5.6 Classic (SIMATIC Manager), GRAPH 7, SCL 5.x
- Input: .awl/.scl source files, .gr7 GRAPH files, S7P project archive (.zap/.zip)
- Typical case: 2000-2015 era installed machines, migration to TIA Portal or another platform

**When NOT to use:**
- ❌ S7-1200/1500 (TIA Portal V14+) → `PROMPT_ANALYZE_S7_1500_OPENNESS.md`
- ❌ S5 → `PROMPT_ANALYZE_S5_AWL.md`
- ❌ Allen-Bradley → `PROMPT_ANALYZE_AB_L5X.md`

---

## 2. Position in Pipeline

```
[.awl/.scl/.gr7 sources (exported from the S7P project) in _input/]
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
| **AWL source (.awl)** | Statement List source | `OB1.AWL`, `FB10.AWL` |
| **SCL source (.scl)** | Structured Control Language | `FB100.SCL` |
| **GRAPH 7 (.gr7)** | Sequence Control (SFC) | `FB200.GR7` |
| **S7 Project archive (.s7p/.zap/.zip)** | Full project backup — ⚠️ **NOT read directly**: retrieve in SIMATIC Manager and export AWL/SCL sources first | `Project.ZAP25`, `Project.ZIP` |
| **Symbol table export** | Symbol definitions | `*.SDF`, `*.SEQ`, `*.DIF` |
| **HW config (.cfg)** | Hardware configuration | SIMATIC Manager HW Config |
| **Reference data** | Cross reference | XREF print |

---

## 4. Data Classification Notice

> ⚠️ **S7-300/400 projects are often 🟠 CONFIDENTIAL** (process secrets, machine-builder know-how). Per `GLOBAL_DATA_CLASSIFICATION.md` Section 3:
>
> - 🟠 → DO NOT upload to public AI services
> - 🟠 → Use self-hosted or Enterprise AI
> - S7-400FH (failsafe) may be 🔴 RESTRICTED — contains safety functions

---

## 5. System Prompt (fixed portion handed to the AI)

```
You are an industrial automation engineer with deep expertise in the
Siemens S7-300/400 Classic STEP 7 V5.x architecture, including AWL
(Statement List), SCL, and GRAPH 7. Your job: produce a structured
project summary from S7 Classic projects.

STRICT RULES:
1. NEVER translate original symbols (German/Turkish/other) — keep them verbatim
2. Do not guess — write "UNKNOWN" when you're not sure
3. Preserve S7 Classic address formats: E 0.0 / I 0.0 (input), A 4.5 / Q 4.5
   (output), M 100.0 (marker), T 5 (timer), Z 10 / C 10 (counter),
   DB10.DBX0.0 (data)
4. Keep AWL mnemonics verbatim: U/UN/O/ON/X/XN, =/S/R, L/T, SPB/SPA/BE/BEA,
   CALL FB/FC, AUF/=DB, etc.
5. Preserve SCL syntax: IF..THEN..END_IF; CASE..OF; FOR..DO; REPEAT..UNTIL
6. Move comment blocks (// or (*...*)) verbatim into the Description field
7. F-blocks (F-PLC, Distributed Safety / S7-F): isolate in Section 9
8. Optimized vs. Non-optimized DB distinction: NON-OPTIMIZED is the default
   in Classic

SYSTEMATIC READING ORDER:
  1. HW Config (rack + slot + modules + IP/MPI addresses)
  2. Symbol table (.sdf or project symbol list)
  3. UDTs (User Data Types)
  4. DBs (Instance + Global)
  5. OBs:
     - OB1 (main cycle)
     - OB10..OB17 (time-of-day)
     - OB20..OB23 (time-delay)
     - OB30..OB38 (cyclic)
     - OB40..OB47 (hardware interrupt)
     - OB80..OB87 (error)
     - OB100..OB102 (startup)
     - OB121/122 (programming/access error)
  6. FBs (Function Blocks - stateful)
  7. FCs (Functions - stateless)
  8. GRAPH 7 FBs (step sequence machines)
  9. F-blocks (if F-CPU present): F_FB, F_FC, F_DB
 10. SFC/SFB system functions (CALL references)

OUTPUT FORMAT (required):

# _parsed.md — S7-300/400 Classic Project Analysis

## 0. Meta
- Project name: <name>
- STEP 7 version: <V5.5 SP4 HF3>
- CPU type: <CPU 315-2 PN/DP> / <CPU 416-3>
- Firmware: <V3.2.x>
- Safety: <enabled / disabled / F-CPU type>
- Analyzed at: <YYYY-MM-DD HH:MM>

## 1. Hardware Configuration
| Rack | Slot | Module | Order Number | Address Range | Notes |
| ... | ... | ... | ... | ... | ... |

## 2. Network
| Interface | Type (MPI/PROFIBUS/PN) | Address | Devices | Notes |
| ... | ... | ... | ... | ... |

## 3. Symbol Table Summary
- Total symbols: <N>
- I: <n>, Q: <n>, M: <n>, T: <n>, C: <n>
- DB ref: <n>, FB ref: <n>, FC ref: <n>
- Symbolless absolute uses: <n>  ← common anti-pattern in S7-300/400

## 4. UDT Inventory
| Name | Members | Used In |
| ... | ... | ... |

## 5. DB Inventory
| Name | Type (Instance/Global) | UDT/Type | Optimized | Description |
| ... | ... | ... | ... | ... |

## 6. OB Inventory
| Number | Name | Trigger | Description |
| OB1 | ... | Main cycle | Main cycle |
| ... | ... | ... | ... |

## 7. FB Inventory
| Name | Interface (IN/OUT/INOUT/STAT) | Called From | Language (AWL/SCL/GR7) | Description |
| ... | ... | ... | ... | ... |

## 8. FC Inventory
| Name | Interface | Called From | Language | Description |
| ... | ... | ... | ... | ... |

## 9. Safety Blocks (F-blocks, if F-CPU)
| Name | Type | F-DB | Description |
| ... | ... | ... | ... |

## 10. Call Tree (summary)
```
OB1
├── FC1   "ScanInputs"
├── FB10  "Motor"           (DB100 = Pump01)
├── FB10  "Motor"           (DB101 = Conv01)
├── FB200 "Sequence"        (DB200, GRAPH7 step machine)
└── FC2   "WriteOutputs"
OB40 (HW interrupt)
├── FB300 "AlarmHandler"
OB82 (diagnostic)
└── FC99  "DiagLog"
```

## 11. Comments / Lessons from Original Code
- <Header comments, revision history>
- <Engineer notes (German/other languages)>
- <"NICHT ÄNDERN", "TEMP", "PATCH" markers>
- <Network header comments>

## 12. Unknowns / TODO for Human Review
- <Symbolless addresses — used in code but missing from the symbol table>
- <Missing block references>
- <Contradictory definitions>
- <Magic numbers without explanation (L 1234 …)>

IN THE OUTPUT:
1. All 12 sections above, in this exact order
2. Do not skip any section — if empty, write "(empty)"
3. Section 12 (Unknowns) is VERY important in S7 Classic (symbolless addresses are common)
```

---

## 6. User Prompt Template (filled per call)

```
TASK: Analyze the S7-300/400 project below and produce _parsed.md.

PROJECT: <project_name>
PLATFORM: S7-<300 / 400 / 400F / 400FH>
STEP 7 VERSION: V<5.x>
INPUT FILES:
  - <_input/Project.ZAP25>
  - <_input/Symbols.SDF>
  - <_input/Sources/*.AWL>
  - <_input/Sources/*.SCL>
  - <_input/HWConfig print>

DATA CLASS: <PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED>

SPECIAL INSTRUCTIONS:
  - <customer-specific notes>
  - <if F-CPU: summarize failsafe blocks SEPARATELY>

OUTPUT:
  - _input/_parsed.md (the 12-section format above)
  - Symbolless addresses must appear in Section 12
  - Do not speculate — UNKNOWN is honest
```

---

## 7. Output Verification Checklist

- [ ] Frontmatter complete (project, STEP 7 version, CPU, F-CPU yes/no)
- [ ] All 12 sections present
- [ ] Section 1 (Hardware): CPU + at least 1 module
- [ ] Section 3 (Symbol summary): Symbolless count is MANDATORY (common in S7 Classic)
- [ ] Section 5 (DB): Optimized/Non-optimized column populated
- [ ] Section 7 (FB): Language column (AWL/SCL/GR7) populated
- [ ] Section 9 (Safety): if no F-CPU, note "(not an F-CPU)"
- [ ] Section 10 (Call tree): OBs and interrupt OBs on separate branches
- [ ] Section 12 (Unknowns): symbolless addresses and magic numbers listed

---

## 8. Typical AI Mistakes

### 8.1 Syntax (Category A)
- AI converts Classic STEP 7 address to TIA format (`E 0.0` → `%I0.0`) → keep Classic format
- AWL: `:U` (Classic) confused with `U` (TIA) → there is NO colon in Classic

### 8.2 Schema/Standard (Category B)
- Optimized/Non-optimized skipped → S7-300/400 default NON-OPT, S7-1200/1500 default OPT
- F-CPU presence not asked → "Safety:" missing in Section 0 Meta

### 8.3 Semantic (Category C) — needs manual review
- ⚠️ AWL `AUF DB10` (open DB) confused with `CALL DB10` (invalid, DBs are not called)
- ⚠️ In S7 Classic, `L MW100` vs. `L DB10.DBW0` have different semantics — accumulator architecture
- ⚠️ GRAPH 7 FBs mistaken for ordinary FBs → in Section 7 mark "Language=GR7" — this is the source for RD03 Flowchart
- ⚠️ OB100 (cold start) vs. OB1 (cycle) confusion → wrong startup sequence
- ⚠️ S7-400H redundant CPU configuration — AI assumes one CPU and drops the second
- ⚠️ Multi-instance FB (FB inside FB) — common in Classic; AI may treat it as a separate FB
- ⚠️ Distributed Safety (S7-F) is NOT identified by an F-prefix alone; F-DB is the deciding marker → an F-prefix check is INSUFFICIENT

### 8.4 Correction-Request Template

> "Section <N> of `_parsed.md` has a <category> error: <short description>. Correct S7 Classic version: <expected>. Regenerate only that section."

---

## 9. Relationship to Topic Extractors

| Extractor | Section(s) of `_parsed.md` read |
|---|---|
| `PROMPT_EXTRACT_IO_FROM_CODE.md` | 1, 3 (HW + Symbol Table) |
| `PROMPT_EXTRACT_DATADICT_FROM_CODE.md` | 4, 5 (UDT + DB) |
| `PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md` | 6, 7, 8, 10 (OB + FB + FC + Call tree); especially GRAPH 7 FBs |
| `PROMPT_EXTRACT_MODE_FROM_CODE.md` | 5, 6 (Mode DB + OB) |
| `PROMPT_EXTRACT_SAFETY_FROM_CODE.md` | 9 (F-blocks) |
| `PROMPT_EXTRACT_MOTION_FROM_CODE.md` | 4, 5, 7 (drive UDT/DB/FB) |
| `PROMPT_EXTRACT_TIMING_FROM_CODE.md` | 3 (T), 7 (timer FB) |
| `PROMPT_EXTRACT_ALARM_FROM_CODE.md` | 6 (OB40-47 process alarm, OB82 diag) |
| `PROMPT_EXTRACT_COMMS_FROM_CODE.md` | 2 (Network) |
| `PROMPT_EXTRACT_FBSPEC_FROM_CODE.md` | 7, 8 (FB + FC) |
| `PROMPT_EXTRACT_HMI_FROM_CODE.md` | 3, 5 (HMI symbols + DB) |
| `PROMPT_EXTRACT_USECASE_FROM_CODE.md` | 6, 10, 11 |
| `PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md` | ALL (line-by-line) |
| `PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md` | ALL + RD13 |

---

## 10. Industry Standard References

| Standard | How this prompt applies it |
|---|---|
| **IEC 61131-3** | POU classification (OB/FB/FC), AWL/SCL syntax |
| **IEC 61131-3 §6.7** | SFC ≈ GRAPH 7 |
| **Siemens STEP 7 V5.x Reference Manual** | Mnemonics, block structure |
| **IEC 61508 / IEC 62061** | SIL requirements when F-CPU is present |

---

## 11. Related Files

- **Pipeline:** `PIPELINE_CODE_REWRITE.md` Gate 2
- **Other platform parsers:** `PROMPT_ANALYZE_S5_AWL.md`, `PROMPT_ANALYZE_S7_1500_OPENNESS.md`, `PROMPT_ANALYZE_AB_L5X.md`, `PROMPT_ANALYZE_CODESYS.md`
- **Consumer extractors:** `PROMPT_EXTRACT_*_FROM_CODE.md` (14 files)
- **S7-Classic → TIA migration notes:** `06_KNOWLEDGE_BASE/KB_PITFALLS_S7CLASSIC_TO_TIA.md` (future)
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`
- **Data classification:** `GLOBAL_DATA_CLASSIFICATION.md`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/analyze/PROMPT_ANALYZE_S7_300_STL.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0 captured the S7 Classic specifics in Turkish (widespread symbolless addressing + GRAPH 7 + multi-instance FBs). v1.2.0 roadmap: F-Distributed Safety detail, S7-400H redundancy parsing.*
