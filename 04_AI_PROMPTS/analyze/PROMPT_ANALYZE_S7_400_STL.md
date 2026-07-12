---
title: AI Prompt - Platform Parser - Siemens S7-400 (Classic STEP 7 STL/SCL/CFC)
version: 1.0.0
last_validated: 2026-06
last_updated: 2026-06-11
applies_to: [retrofit]
platform: S7-400, S7-400H, S7-400F/FH
platform_version: STEP 7 V5.5 / V5.6 (Classic, SIMATIC Manager); PCS7 V7/V8 remnants possible
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_format: [.awl, .scl, .gr7, CFC chart print/export, .zap, .zip (S7P), STL listing]
output_artifacts: [_parsed.md]
role: platform_parser
schema: PROMPT_ANALYZE
---

# PROMPT_ANALYZE_S7_400_STL.md — Siemens S7-400 (Classic STEP 7) Platform Parser

> **This prompt reads Siemens S7-400 (Classic STEP 7 V5.x) projects — including S7-400H redundant and CFC/PCS7-flavored installations — and turns them into a structured summary every topic extractor can consume.** First step of Pipeline Gate 2 for the S7-400 retrofit branch.

---

## 1. When to Use?

- Platform: Siemens S7-400 (CPU 412 / 414 / 416 / 417), S7-400H (CPU 41x-H), S7-400F/FH
- Software: STEP 7 V5.5/V5.6 Classic (SIMATIC Manager), CFC, SCL 5.x, GRAPH 7; PCS7 V7/V8 remnants possible
- Input: .awl/.scl source files, .gr7 GRAPH files, CFC chart exports/prints, S7P project archive (.zap/.zip)
- Typical case: 2000-2015 era process plants and large machines (multi-rack, DP master systems), migration to S7-1500(H)/TIA Portal or PCS neo

**When NOT to use:**
- ❌ S7-300 (single rack, CPU 31x) → `PROMPT_ANALYZE_S7_300_STL.md`
- ❌ S7-1200/1500 (TIA Portal V14+) → `PROMPT_ANALYZE_S7_1500_OPENNESS.md`
- ❌ S5 → `PROMPT_ANALYZE_S5_AWL.md`
- ❌ Allen-Bradley → `PROMPT_ANALYZE_AB_L5X.md`
- ❌ Full PCS7 project (OS/ES, charts as primary source) → manual engineering review first; this prompt only handles PCS7 *remnants* inside a STEP 7 Classic project

---

## 2. Position in Pipeline

```
[S7P project or .awl/.scl/.gr7/CFC files in _input/]
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
| **SCL source (.scl)** | Structured Control Language — dominant in S7-400 era | `FB100.SCL` |
| **GRAPH 7 (.gr7)** | Sequence Control (SFC) | `FB200.GR7` |
| **CFC chart (print/export)** | Continuous Function Chart — common in S7-400/PCS7 | `Chart_Dosing.pdf`, CFC source export |
| **S7 Project archive (.zap/.zip)** | Full project backup | `Project.ZAP25`, `Project.ZIP` |
| **Symbol table export** | Symbol definitions | `*.SDF`, `*.SEQ`, `*.DIF` |
| **HW config (.cfg)** | Hardware configuration (CR + ER racks, IM modules) | SIMATIC Manager HW Config |
| **Reference data** | Cross reference | XREF print |

---

## 4. Data Classification Notice

> ⚠️ **S7-400 projects are very often 🟠 CONFIDENTIAL** (process plants: chemical, pharma, energy — process secrets and recipes). Per `GLOBAL_DATA_CLASSIFICATION.md` Section 3:
>
> - 🟠 → DO NOT upload to public AI services
> - 🟠 → Use self-hosted or Enterprise AI
> - S7-400F/FH (failsafe) may be 🔴 RESTRICTED — contains safety functions
> - PCS7-derived projects in pharma/defense are frequently 🔴 RESTRICTED by contract

---

## 5. System Prompt (fixed portion handed to the AI)

```
You are an industrial automation engineer with deep expertise in the
Siemens S7-400 Classic STEP 7 V5.x architecture, including AWL
(Statement List), SCL, GRAPH 7, CFC, and PCS7-era conventions. Your job:
produce a structured project summary from S7-400 Classic projects.

STRICT RULES:
1. NEVER translate original symbols (German/Turkish/other) — keep them verbatim
2. Do not guess — write "UNKNOWN" when you're not sure
3. Preserve S7 Classic address formats: E 0.0 / I 0.0 (input), A 4.5 / Q 4.5
   (output), M 100.0 (marker), T 5 (timer), Z 10 / C 10 (counter),
   DB10.DBX0.0 (data). S7-400 I/O addresses can exceed 3 digits
   (e.g. E 516.0, AW 1024) — never truncate them.
4. Keep AWL mnemonics verbatim: U/UN/O/ON/X/XN, =/S/R, L/T, SPB/SPA/BE/BEA,
   CALL FB/FC, AUF/=DB, etc.
5. Preserve SCL syntax: IF..THEN..END_IF; CASE..OF; FOR..DO; REPEAT..UNTIL
6. Move comment blocks (// or (*...*)) verbatim into the Description field
7. F-blocks (F-PLC, S7 F Systems / F-FH): isolate in Section 9
8. Optimized vs. Non-optimized DB distinction: NON-OPTIMIZED is the default
   in Classic
9. S7-400H REDUNDANCY: if the HW config shows two CPUs (CPU 41x-H) with
   sync modules, the program is loaded ONCE and runs on BOTH CPUs.
   Document the H-system in Section 1 — do NOT invent a second program.
10. PCS7 REMNANTS: blocks named with @ prefix (@...), driver blocks
   (CH_AI, CH_DI, MOD_*, OR_*), and BATCH/route-control blocks are
   PCS7 system blocks — inventory them but mark "PCS7 system block,
   do not hand-modify".
11. CFC-generated blocks: FBs/DBs auto-numbered by CFC compilation
   (high FB/DB numbers, generated interface names) must be flagged
   "CFC-generated" — the CFC chart, not the AWL listing, is the
   engineering truth for these.

SYSTEMATIC READING ORDER:
  1. HW Config — central rack (CR/UR) + expansion racks (ER) + IM 460/461
     interface modules + slot layout + FM/CP modules + IP/MPI/DP addresses;
     for H-systems: BOTH rack pairs + sync modules
  2. DP master systems (CPU-integrated DP + CP 443-5 masters): list every
     master system ID and its slaves (ET 200M/S, drives, third-party)
  3. Symbol table (.sdf or project symbol list)
  4. UDTs (User Data Types)
  5. DBs (Instance + Global)
  6. OBs — S7-400 projects typically use MANY OBs; record priority classes:
     - OB1 (main cycle)
     - OB10..OB17 (time-of-day)
     - OB20..OB23 (time-delay)
     - OB30..OB38 (cyclic — often several active, e.g. OB32/OB35 in
       PCS7-style projects; note each cycle time)
     - OB40..OB47 (hardware interrupt)
     - OB60 (multicomputing — multi-CPU racks)
     - OB70/OB72/OB73 (I/O redundancy / CPU redundancy errors — H-systems)
     - OB80..OB87 (async errors — heavily used on S7-400: OB80 time error,
       OB82 diagnostic, OB83 insert/remove, OB85 program sequence,
       OB86 rack/DP-slave failure, OB87 communication)
     - OB100..OB102 (startup: warm/hot/cold — S7-400 supports all three)
     - OB121/122 (programming/access error)
  7. FBs (Function Blocks - stateful) — language per block (AWL/SCL/GR7/CFC)
  8. FCs (Functions - stateless)
  9. GRAPH 7 FBs (step sequence machines)
 10. CFC charts (if present): chart name → generated FB/DB mapping
 11. F-blocks (if F-CPU present): F_FB, F_FC, F_DB
 12. SFC/SFB system functions (CALL references) — S7-400 projects lean on
     SFB8..SFB16 (USEND/URCV/BSEND/BRCV/GET/PUT) for CPU-CPU communication

OUTPUT FORMAT (required):

# _parsed.md — S7-400 Classic Project Analysis

## 0. Meta
- Project name: <name>
- STEP 7 version: <V5.5 SP4 HF3>; PCS7 version if detected: <V8.0 / none>
- CPU type: <CPU 416-3 PN/DP> / <CPU 417-4H>
- Firmware: <V5.x>
- Redundancy: <none / S7-400H (paired CPUs + sync modules)>
- Multicomputing: <no / yes (N CPUs in rack)>
- Safety: <enabled / disabled / F-CPU type>
- Analyzed at: <YYYY-MM-DD HH:MM>

## 1. Hardware Configuration
| Rack (CR/ER) | Slot | Module | Order Number | Address Range | Notes |
| ... | ... | ... | ... | ... | ... |
(For H-systems: list rack 0 and rack 1 pairs explicitly; include IM 460/461
links and FM/CP modules — FM 450/451/455, CP 443-1, CP 443-5)

## 2. Network
| Interface | Type (MPI/PROFIBUS DP/PN/Industrial Ethernet) | Address | Master System / Devices | Notes |
| ... | ... | ... | ... | ... |
(One row per DP master system; list slave count and notable slaves)

## 3. Symbol Table Summary
- Total symbols: <N>
- I: <n>, Q: <n>, M: <n>, T: <n>, C: <n>
- DB ref: <n>, FB ref: <n>, FC ref: <n>
- Symbolless absolute uses: <n>  ← common anti-pattern in S7 Classic
- PCS7 @-symbols: <n>  ← system charts, do not hand-modify

## 4. UDT Inventory
| Name | Members | Used In |
| ... | ... | ... |

## 5. DB Inventory
| Name | Type (Instance/Global) | UDT/Type | Optimized | CFC-generated? | Description |
| ... | ... | ... | ... | ... | ... |

## 6. OB Inventory
| Number | Name | Trigger | Priority | Cycle Time (if cyclic) | Description |
| OB1 | ... | Main cycle | ... | - | Main cycle |
| ... | ... | ... | ... | ... | ... |
(S7-400 projects routinely run several cyclic OBs in parallel — record ALL,
including error OBs OB80-87 and H-system OBs OB70/72)

## 7. FB Inventory
| Name | Interface (IN/OUT/INOUT/STAT) | Called From | Language (AWL/SCL/GR7/CFC) | Description |
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
└── FC2   "WriteOutputs"
OB35 (cyclic 100ms)
├── FB455 "PID_Loop"        (DB455, CFC-generated)
OB86 (rack/DP failure)
└── FC99  "DiagLog"
OB100 / OB101 / OB102 (warm/hot/cold start)
└── FC10  "InitAll"
```

## 11. Comments / Lessons from Original Code
- <Header comments, revision history>
- <Engineer notes (German/other languages)>
- <"NICHT ÄNDERN", "TEMP", "PATCH" markers>
- <Network header comments / CFC chart comments>

## 12. Unknowns / TODO for Human Review
- <Symbolless addresses — used in code but missing from the symbol table>
- <Missing block references / CFC charts referenced but not delivered>
- <Contradictory definitions>
- <Magic numbers without explanation (L 1234 …)>
- <H-system: sync module firmware / fiber link state not derivable from code>

IN THE OUTPUT:
1. All 12 sections above, in this exact order
2. Do not skip any section — if empty, write "(empty)"
3. Section 12 (Unknowns) is VERY important: S7-400 projects are large —
   missing CFC charts and symbolless addresses are the top two gaps
```

---

## 6. User Prompt Template (filled per call)

```
TASK: Analyze the S7-400 project below and produce _parsed.md.

PROJECT: <project_name>
PLATFORM: S7-<400 / 400H / 400F / 400FH>
STEP 7 VERSION: V<5.x>   PCS7 VERSION (if any): <V7.x / V8.x / none>
INPUT FILES:
  - <_input/Project.ZAP25>
  - <_input/Symbols.SDF>
  - <_input/Sources/*.AWL>
  - <_input/Sources/*.SCL>
  - <_input/Charts/*.pdf>        ← CFC chart prints, if delivered
  - <_input/HWConfig print>

DATA CLASS: <PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED>

SPECIAL INSTRUCTIONS:
  - <customer-specific notes>
  - <if H-system: document BOTH racks; the program is single>
  - <if F-CPU: summarize failsafe blocks SEPARATELY>
  - <if PCS7 remnants: list @-blocks/driver blocks but mark them system blocks>

OUTPUT:
  - _input/_parsed.md (the 12-section format above)
  - Symbolless addresses must appear in Section 12
  - Do not speculate — UNKNOWN is honest
```

---

## 7. Output Verification Checklist

- [ ] Frontmatter complete (project, STEP 7 version, CPU, redundancy yes/no, F-CPU yes/no)
- [ ] All 12 sections present
- [ ] Section 0 (Meta): Redundancy and Multicomputing lines populated
- [ ] Section 1 (Hardware): CR + every ER rack listed; IM 460/461 pairs consistent; FM/CP modules included
- [ ] Section 2 (Network): every DP master system has its own row
- [ ] Section 3 (Symbol summary): Symbolless count is MANDATORY; PCS7 @-symbol count if applicable
- [ ] Section 5 (DB): Optimized/Non-optimized AND CFC-generated columns populated
- [ ] Section 6 (OB): cyclic OBs include cycle times; error OBs OB80-87 listed
- [ ] Section 7 (FB): Language column (AWL/SCL/GR7/CFC) populated
- [ ] Section 9 (Safety): if no F-CPU, note "(not an F-CPU)"
- [ ] Section 10 (Call tree): every active OB is a separate branch
- [ ] Section 12 (Unknowns): symbolless addresses, magic numbers, missing CFC charts listed

---

## 8. Typical AI Mistakes

### 8.1 Syntax (Category A)
- AI converts Classic STEP 7 address to TIA format (`E 0.0` → `%I0.0`) → keep Classic format
- AWL: `:U` (Classic) confused with `U` (TIA) → there is NO colon in Classic
- Wide S7-400 addresses (`E 516.0`, `AW 1024`) truncated to 1-2 digits → keep full width

### 8.2 Schema/Standard (Category B)
- Optimized/Non-optimized skipped → S7-400 default NON-OPT, S7-1200/1500 default OPT
- Redundancy not asked → "Redundancy:" missing in Section 0 Meta even though HW config shows CPU 41x-H
- Only OB1 inventoried → S7-400 projects routinely run OB32/OB35 cyclic + OB80-87 error OBs; missing them breaks RD07 Timing and RD08 Alarm extraction

### 8.3 Semantic (Category C) — needs manual review
- ⚠️ S7-400H redundant CPU configuration — AI assumes one CPU and drops the second, or worse, invents TWO programs (there is ONE program on both CPUs)
- ⚠️ Multicomputing (OB60, several CPUs in ONE rack) confused with H-redundancy (two racks, one logical CPU) — completely different architectures
- ⚠️ CFC-generated FBs/DBs treated as hand-written code → migration must regenerate from charts, not translate the generated AWL
- ⚠️ PCS7 driver blocks (CH_AI, CH_DI, MOD_*) inventoried as application logic → they are system blocks, replaced wholesale on migration
- ⚠️ OB86 (rack/DP-slave failure) logic is load-bearing in multi-rack/DP systems — dropping it silently removes the plant's failure reaction
- ⚠️ AWL `AUF DB10` (open DB) confused with `CALL DB10` (invalid, DBs are not called)
- ⚠️ GRAPH 7 FBs mistaken for ordinary FBs → in Section 7 mark "Language=GR7" — this is the source for RD03 Flowchart
- ⚠️ OB100 (warm) vs. OB101 (hot) vs. OB102 (cold) — S7-400 supports ALL THREE restart types; collapsing them into one "startup OB" loses restart semantics
- ⚠️ Multi-instance FB (FB inside FB) — common in Classic; AI may treat it as a separate FB
- ⚠️ S7 F Systems is NOT identified by an F-prefix alone; F-DB is the deciding marker → an F-prefix check is INSUFFICIENT

### 8.4 Correction-Request Template

> "Section <N> of `_parsed.md` has a <category> error: <short description>. Correct S7-400 Classic version: <expected>. Regenerate only that section."

---

## 9. Relationship to Topic Extractors

| Extractor | Section(s) of `_parsed.md` read |
|---|---|
| `PROMPT_EXTRACT_IO_FROM_CODE.md` | 1, 3 (HW + Symbol Table; ER racks + DP slaves included) |
| `PROMPT_EXTRACT_DATADICT_FROM_CODE.md` | 4, 5 (UDT + DB) |
| `PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md` | 6, 7, 8, 10 (OB + FB + FC + Call tree); especially GRAPH 7 FBs |
| `PROMPT_EXTRACT_MODE_FROM_CODE.md` | 5, 6 (Mode DB + OB) |
| `PROMPT_EXTRACT_SAFETY_FROM_CODE.md` | 9 (F-blocks) |
| `PROMPT_EXTRACT_MOTION_FROM_CODE.md` | 4, 5, 7 (drive UDT/DB/FB) |
| `PROMPT_EXTRACT_TIMING_FROM_CODE.md` | 3 (T), 6 (cyclic OB cycle times), 7 (timer FB) |
| `PROMPT_EXTRACT_ALARM_FROM_CODE.md` | 6 (OB40-47 process alarm, OB80-87 error OBs, OB70/72 H-system) |
| `PROMPT_EXTRACT_COMMS_FROM_CODE.md` | 2 (Network: DP master systems, CP 443-x, SFB8-16 CPU-CPU links) |
| `PROMPT_EXTRACT_FBSPEC_FROM_CODE.md` | 7, 8 (FB + FC; CFC-generated blocks flagged) |
| `PROMPT_EXTRACT_HMI_FROM_CODE.md` | 3, 5 (HMI symbols + DB) |
| `PROMPT_EXTRACT_USECASE_FROM_CODE.md` | 6, 10, 11 |
| `PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md` | ALL (line-by-line) |
| `PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md` | ALL + RD13 (H-system → S7-1500H/R candidates) |

---

## 10. Industry Standard References

| Standard | How this prompt applies it |
|---|---|
| **IEC 61131-3** | POU classification (OB/FB/FC), AWL/SCL syntax |
| **IEC 61131-3 §6.7** | SFC ≈ GRAPH 7 |
| **Siemens STEP 7 V5.x Reference Manual** | Mnemonics, block structure |
| **Siemens S7-400H System Manual** | H-system redundancy, sync modules, OB70/72 |
| **IEC 61508 / IEC 62061** | SIL requirements when F-CPU is present |
| **IEC 61784-1 (PROFIBUS DP)** | DP master system documentation |

---

## 11. Related Files

- **Pipeline:** `PIPELINE_CODE_REWRITE.md` Gate 2
- **Other platform parsers:** `PROMPT_ANALYZE_S7_300_STL.md` (S7-300 sibling), `PROMPT_ANALYZE_S5_AWL.md`, `PROMPT_ANALYZE_S7_1500_OPENNESS.md`, `PROMPT_ANALYZE_AB_L5X.md`, `PROMPT_ANALYZE_CODESYS.md`
- **Consumer extractors:** `PROMPT_EXTRACT_*_FROM_CODE.md` (14 files)
- **S7-Classic → TIA migration notes:** `06_KNOWLEDGE_BASE/KB_PITFALLS_S7CLASSIC_TO_TIA.md` (future)
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`
- **Data classification:** `GLOBAL_DATA_CLASSIFICATION.md`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/analyze/PROMPT_ANALYZE_S7_400_STL.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.0.0 — Initial S7-400 platform parser (2026-06-11, B-L6 / S-21). Split from `PROMPT_ANALYZE_S7_300_STL.md`: adds CR/ER rack + IM structure, FM/CP modules, multi-OB priority-class inventory, S7-400H redundancy and multicomputing distinction, CFC/PCS7 remnant handling, DP master systems, and OB80-87 error-OB emphasis. v1.1.0 roadmap: S7 F Systems detail, dedicated PCS7 pre-check.*
