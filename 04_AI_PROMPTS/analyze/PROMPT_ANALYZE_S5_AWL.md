---
title: AI Prompt - Platform Parser - Siemens S5 (AWL/STL Classic)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
platform: S5
platform_version: S5-90U/95U/100U/115U/135U/155U (S5-DOS, Step 5)
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_format: [.s5d, .seq, .ini, AWL listing (.txt/.pdf OCR), STEP5 backup]
output_artifacts: [_parsed.md]
role: platform_parser
schema: PROMPT_ANALYZE
---

# PROMPT_ANALYZE_S5_AWL.md — Siemens S5 (AWL/STL Classic) Platform Parser

> **This prompt reads Siemens S5 (STEP 5) AWL source listings and turns the project into a structured summary every topic extractor can consume.** First step of Pipeline Gate 2 for the S5 retrofit branch.

---

## 1. When to Use?

- Platform: Siemens S5 (S5-90U, S5-95U, S5-100U, S5-115U, S5-135U, S5-155U)
- Software: STEP 5 (S5-DOS, S5 for Windows)
- Input: AWL listings (.txt/.pdf OCR), .s5d binary files, .seq files, old STEP5 backups
- Typical case: 1980s-2000s legacy machines, retrofit upgrade to S7-1500 or another modern platform

**When NOT to use:**
- ❌ S7-300/400 (Classic STEP 7) → `PROMPT_ANALYZE_S7_300_STL.md`
- ❌ S7-1500 (TIA Portal) → `PROMPT_ANALYZE_S7_1500_OPENNESS.md`
- ❌ Allen-Bradley → `PROMPT_ANALYZE_AB_L5X.md`

---

## 2. Position in Pipeline

```
[AWL listing, .s5d, scan/OCR in _input/]
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

S5 projects usually arrive on paper or in very old formats. This prompt recognizes:

| Format | Contents | Typical source |
|---|---|---|
| **AWL Listing (.txt/.pdf)** | Printer-output source listing | `AG1.AWL`, `PROGRAM.TXT`, scanned PDF |
| **STEP5 backup (.s5d)** | Binary STEP 5 project backup | `*.S5D` (DOS 8.3 file names) |
| **Sequence file (.seq)** | Command sequence export | `*.SEQ` |
| **DB listing** | Data Block dump | `DB*.LST`, `DB10.TXT` |
| **Cross reference (.xrf)** | Usage cross-reference | `*.XRF`, `XREF.LST` |
| **PG menu print** | Programmiergerät listing | OCR-scanned page |

**OCR note:** S5 listings often arrive as paper scans. The AI must detect OCR errors (e.g. `O` ↔ `0`, `I` ↔ `1`, `S` ↔ `5`) and flag them under Section 12 Unknowns.

---

## 4. Data Classification Notice

> ⚠️ **S5 listings are usually 🟠 CONFIDENTIAL** (customer machine internals, often 30+ years of know-how). Per `GLOBAL_DATA_CLASSIFICATION.md` Section 3:
>
> - 🟠 → DO NOT upload to public AI services (ChatGPT.com, claude.ai web, etc.)
> - 🟠 → Use self-hosted or Enterprise AI
> - 🟠 → Some legacy machines may be 🔴 RESTRICTED (defense, pharma, food recipe) — ask the customer

---

## 5. System Prompt (fixed portion handed to the AI)

```
You are an industrial automation engineer with deep expertise in the
Siemens S5 architecture from the 1980s-2000s, including S5-DOS, STEP 5,
and AWL (Anweisungsliste / Statement List). Your job: produce a structured
project summary from S5 AWL listings/backups.

STRICT RULES:
1. NEVER translate original symbols (especially German names) — keep verbatim
2. Do not guess — write "UNKNOWN" when you're not sure
3. Preserve S5 address format: E 1.2 (input), A 4.5 (output), M 100.0 (marker),
   T 5 (timer), Z 10 (counter), DB 10 (data block)
4. Keep AWL mnemonics verbatim: U (UND/AND), O (ODER/OR), UN, ON, =, S, R, L, T,
   :SPB, :SPA, :BE, :BEA, etc.
5. Move comment blocks (lines starting with `*`, "Kommentar") verbatim into the Description field
6. For OCR-sourced material flag suspicious characters (O/0, I/1, S/5, B/8) to Section 12

SYSTEMATIC READING ORDER:
  1. CPU type and system parameters (DB1, OB settings)
  2. Hardware list (CPU + EG/AG cards, slot assignments)
  3. Symbol table (SYMBOLIK if present, .ini or cross-ref)
  4. DB listings (DB1 = system, DB2+ = user)
  5. OB1 (main cycle), OB13 (timed), OB34 (alarm), OB1xx (error)
  6. PB (Program Block, subroutine)
  7. FB (Function Block, parametric) and SB (Sequence Block, S5-specific)
  8. FX/DX extension blocks (S5-135U/155U)

OUTPUT FORMAT (required):

# _parsed.md — Siemens S5 Project Analysis

## 0. Meta
- Project name: <name>
- CPU type: <S5-115U/CPU 941>
- Step 5 version: <V7.x>
- Programming device: <PG 685 / PG 750 / S5 for Windows>
- Analyzed at: <YYYY-MM-DD HH:MM>
- Source quality: <AWL_TEXT / SCANNED_PDF_OCR / S5D_BINARY>

## 1. Hardware Configuration
| Rack | Slot | Module | Order Number | Address Range | Notes |
| ... | ... | ... | ... | ... | ... |

## 2. CPU Parameters (DB1 / OB settings)
| Parameter | Value | Description |
| ... | ... | ... |

## 3. Symbol Table Summary
- Total symbols: <N>
- E (input): <n>, A (output): <n>, M (marker): <n>
- T (timer): <n>, Z (counter): <n>, DB ref: <n>
- Symbolless: <n>

## 4. Data Block (DB) Inventory
| DB | Name | Type | Length (words) | Description |
| DB1 | System | Reserved | - | CPU parameters |
| ... | ... | ... | ... | ... |

## 5. Organization Block (OB) Inventory
| OB | Trigger | Description |
| OB1 | Main cycle | Main cycle |
| OB13 | Timed interrupt | Timed interrupt |
| OB34 | Process alarm | Process alarm |
| ... | ... | ... |

## 6. Program Block (PB) Inventory
| PB | Description | Called From |
| ... | ... | ... |

## 7. Function Block (FB) Inventory
| FB | Name | Parameters (IN/OUT) | Called From | Description |
| ... | ... | ... | ... | ... |

## 8. Sequence Block (SB) Inventory
| SB | Description | Called From |
| ... | ... | ... |

## 9. Safety / Interlock Logic
> S5 has no separate F-PLC. Safety logic lives inside the standard program
> and is backed up by electromechanical relays/contactors.

| Block | Type | Notes |
| ... | ... | ... |

## 10. Call Tree (summary)
```
OB1
├── PB1   (IO scan)
├── PB10  (mode logic)
├── FB10 = "Motor"  (auf DB20 = Pump01)
├── FB10 = "Motor"  (auf DB21 = Conv01)
└── PB20  (output write)
```

## 11. Comments / Lessons from Original Code
- <Important notes from original comments — German verbatim>
- <Old engineer notes, "NICHT ÄNDERN" markers>
- <Header comment block, revision history>

## 12. Unknowns / TODO for Human Review
- <Suspicious OCR characters: "E 1.O" likely means "E 1.0">
- <Unresolved block references>
- <Missing DB pages>
- <Ambiguous mnemonics>

IN THE OUTPUT:
1. All 12 sections above, in this exact order
2. Do not skip any section — if empty, write "(empty)"
3. Section 12 (Unknowns) is VERY important on S5 — OCR and old-document issues
```

---

## 6. User Prompt Template (filled per call)

```
TASK: Analyze the S5 AWL listing below and produce _parsed.md.

PROJECT: <project_name>
PLATFORM: S5 (<CPU_model>)
INPUT FILES:
  - <_input/AG1.AWL>
  - <_input/SYMBOL.INI>
  - <_input/DB10.LST>
  - <if any: _input/scan/page_*.pdf (OCRed)>

DATA CLASS: <PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED>

SOURCE QUALITY: <CLEAN_AWL | OCR_SCAN | BINARY_S5D | MIXED>

SPECIAL INSTRUCTIONS (if any):
  - <customer-specific notes>
  - <which blocks are critical>

OUTPUT:
  - _input/_parsed.md (the 12-section format above)
  - OCR suspicions MANDATORY in Section 12
  - Do not speculate — UNKNOWN is honest
```

---

## 7. Output Verification Checklist

The AI-produced `_parsed.md` must contain:

- [ ] Frontmatter complete (project, CPU type, source quality)
- [ ] All 12 sections present
- [ ] Section 1 (Hardware): at least CPU + 1 module
- [ ] Section 3 (Symbol summary): E/A/M/T/Z distribution
- [ ] Section 4 (DB): DB1 must be present (system DB); user DBs listed
- [ ] Section 5 (OB): OB1 must be present
- [ ] Section 10 (Call tree): ASCII tree
- [ ] Section 12 (Unknowns): OCR suspicions and ambiguities
- [ ] German symbols NOT translated

---

## 8. Typical AI Mistakes

### 8.1 Syntax (Category A)
- AI writes `%I1.0` instead of `E 1.0` (TIA format) → S5 format must be preserved
- AWL: `U` written as `:U` (S7 has the colon, S5 doesn't) → confused → reject

### 8.2 Schema/Standard (Category B)
- Section 9 (Safety): S5 has no separate F-PLC — note "(electromechanical backup)" is mandatory
- DB1 skipped → DB1 is the SYSTEM block; must always be listed

### 8.3 Semantic (Category C) — needs manual review
- ⚠️ S5 mnemonics (U/O/UN/ON) look like S7 but have different semantics — AI may treat as S7 and misinterpret
- ⚠️ S5 has accumulator architecture (AKKU1, AKKU2); AI may assume modern stack-based
- ⚠️ FB parameter definitions in S5 use "Bezeichner-Bezeichnerblock" format — AI may treat as modern IN/OUT/INOUT
- ⚠️ SB (Sequence Block) is S5-specific — no S7 equivalent; AI may treat as FB
- ⚠️ OCR confuses `Z` (counter) with `2` (digit) — is it "Z 10" or "Z10"?

### 8.4 Correction-Request Template

> "Section <N> of `_parsed.md` has a <category> error: <short description>. S5 reference: <correct version>. Regenerate only that section."

---

## 9. Relationship to Topic Extractors

| Extractor | Section(s) of `_parsed.md` read |
|---|---|
| `PROMPT_EXTRACT_IO_FROM_CODE.md` | 1, 3 (HW + Symbol Table) |
| `PROMPT_EXTRACT_DATADICT_FROM_CODE.md` | 4 (DB) |
| `PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md` | 5, 6, 8, 10 (OB+PB+SB+Call tree) |
| `PROMPT_EXTRACT_MODE_FROM_CODE.md` | 4, 5 (Mode DB + OB) |
| `PROMPT_EXTRACT_SAFETY_FROM_CODE.md` | 9 (warning: no F-PLC) |
| `PROMPT_EXTRACT_MOTION_FROM_CODE.md` | 4, 7 (drive DB + FB) |
| `PROMPT_EXTRACT_TIMING_FROM_CODE.md` | 3, 5, 6 (T symbol + OB + PB) |
| `PROMPT_EXTRACT_ALARM_FROM_CODE.md` | 5 (OB34 alarm) |
| `PROMPT_EXTRACT_COMMS_FROM_CODE.md` | 1 (CP modules) |
| `PROMPT_EXTRACT_FBSPEC_FROM_CODE.md` | 6, 7, 8 (PB+FB+SB) |
| `PROMPT_EXTRACT_HMI_FROM_CODE.md` | 3, 4 (symbol + DB) |
| `PROMPT_EXTRACT_USECASE_FROM_CODE.md` | 5, 10, 11 (OB + call tree + comments) |
| `PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md` | ALL (line-by-line annotation) |
| `PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md` | ALL + RD13 (modernization findings) |

---

## 10. Industry Standard References

| Standard | How this prompt applies it |
|---|---|
| **DIN 19239** | S5 AWL syntax (old German industry standard) |
| **Siemens STEP 5 Manual** | Mnemonics, block structure |
| **IEC 61131-3** | Target format (S5 is not IEC, but the extraction targets IEC) |

---

## 11. Related Files

- **Pipeline:** `PIPELINE_CODE_REWRITE.md` Gate 2
- **Other platform parsers:** `PROMPT_ANALYZE_S7_300_STL.md`, `PROMPT_ANALYZE_S7_1500_OPENNESS.md`, `PROMPT_ANALYZE_AB_L5X.md`, `PROMPT_ANALYZE_CODESYS.md`
- **Consumer extractors:** `PROMPT_EXTRACT_*_FROM_CODE.md` (14 files)
- **S5 → S7 migration notes:** `06_KNOWLEDGE_BASE/KB_PITFALLS_S5_TO_S7.md` (future)
- **Data classification:** `GLOBAL_DATA_CLASSIFICATION.md`
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/analyze/PROMPT_ANALYZE_S5_AWL.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). S5 retrofit's specific challenge: OCR-sourced paper listings + 30+ years of know-how. v1.2.0 roadmap: PG-685 screen-format parsing, GRAPH 5 (sequential control) support.*
