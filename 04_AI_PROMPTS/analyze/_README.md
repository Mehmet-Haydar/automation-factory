---
title: 04_AI_PROMPTS / analyze — Folder README
version: 1.3.0
last_updated: 2026-06-11
status: ACTIVE
last_validated: 2026-05
---

# `04_AI_PROMPTS/analyze/` — Pipeline Gate 2 Prompt Library

> **This folder contains all the AI prompts that read old PLC code and produce the 14-Point Raw Data Pack (RD01–RD14).** Used in the pipeline's **Gate 2 EXTRACTION** stage.

---

## 1. Folder Structure and the Two Prompt Families

```
analyze/
├── _README.md  ← this file
│
├── PROMPT_ANALYZE_<platform>.md     ← Platform Parser family (6 prompts)
│   ├── PROMPT_ANALYZE_S5_AWL.md
│   ├── PROMPT_ANALYZE_S7_300_STL.md
│   ├── PROMPT_ANALYZE_S7_400_STL.md
│   ├── PROMPT_ANALYZE_S7_1500_OPENNESS.md  (pattern reference)
│   ├── PROMPT_ANALYZE_AB_L5X.md
│   └── PROMPT_ANALYZE_CODESYS.md
│
├── PROMPT_COMPARE_VERSIONS.md       ← Version Compare GUI view (NOT a Gate 2 prompt)
│
└── PROMPT_EXTRACT_<topic>_FROM_CODE.md  ← Topic Extractor family (14 prompts)
    ├── PROMPT_EXTRACT_IO_FROM_CODE.md           → RD01
    ├── PROMPT_EXTRACT_DATADICT_FROM_CODE.md     → RD02
    ├── PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md    → RD03
    ├── PROMPT_EXTRACT_MODE_FROM_CODE.md         → RD04
    ├── PROMPT_EXTRACT_SAFETY_FROM_CODE.md       → RD05 ⚠️
    ├── PROMPT_EXTRACT_MOTION_FROM_CODE.md       → RD06
    ├── PROMPT_EXTRACT_TIMING_FROM_CODE.md       → RD07
    ├── PROMPT_EXTRACT_ALARM_FROM_CODE.md        → RD08
    ├── PROMPT_EXTRACT_COMMS_FROM_CODE.md        → RD09
    ├── PROMPT_EXTRACT_FBSPEC_FROM_CODE.md       → RD10
    ├── PROMPT_EXTRACT_HMI_FROM_CODE.md          → RD11
    ├── PROMPT_EXTRACT_USECASE_FROM_CODE.md      → RD12
    ├── PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md   → RD13
    └── PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md → RD14
```

> **`PROMPT_COMPARE_VERSIONS.md` is the one prompt in this folder that is
> NOT part of the Gate 2 pipeline:** it powers the **Version Compare** GUI
> view (diff between `_Versionen/` archive folders). It receives only the
> deterministic diff summary (`version_compare.summarize_for_ai()`), never
> raw files, and its output stays `DRAFT_UNVERIFIED` in the view.

---

## 2. Workflow (Gate 2)

```
[Raw old PLC code in the _input/ folder]
        │
        ▼  Step A: Platform detection
[PROMPT_ANALYZE_<platform>.md]  ← one of the 6 platform parsers is chosen
        │
        ▼  Output:
[_input/_parsed.md]  ← structured project summary (12 sections)
        │
        ▼  Step B: the 14 extractors read _parsed.md in order
[PROMPT_EXTRACT_IO_FROM_CODE.md]        ──→ RD01_IO.xlsx
[PROMPT_EXTRACT_DATADICT_FROM_CODE.md]  ──→ RD02_DataDict.xlsx
[PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md] ──→ RD03_Flowchart.xlsx
[...]
[PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md] ──→ RD14_Modernization.xlsx
        │
        ▼
[14-Point Raw Data Pack complete, moves to Gate 3]
```

---

## 3. Platform Selection Guide

| Old System | Parser to Use |
|---|---|
| Siemens S5 (S5-DOS, STEP 5, AWL) | `PROMPT_ANALYZE_S5_AWL.md` |
| Siemens S7-300 (Classic STEP 7 V5.x, AWL/SCL/GR7) | `PROMPT_ANALYZE_S7_300_STL.md` |
| Siemens S7-400 / 400H / 400F-FH (Classic STEP 7 V5.x, AWL/SCL/GR7/CFC, PCS7 remnants) | `PROMPT_ANALYZE_S7_400_STL.md` |
| Siemens S7-1200/1500 (TIA Portal V14+, Openness XML) | `PROMPT_ANALYZE_S7_1500_OPENNESS.md` |
| Allen-Bradley ControlLogix/CompactLogix/GuardLogix (.L5X) | `PROMPT_ANALYZE_AB_L5X.md` |
| CODESYS V3 and derivatives (TwinCAT, EcoStruxure, Wago, B&R) | `PROMPT_ANALYZE_CODESYS.md` |

**Mixed system (e.g. Siemens + AB):** Run a separate parser for each platform and merge the results manually, or name the `_parsed.md` files (`_parsed_siemens.md`, `_parsed_ab.md`) and give them to the extractors as multiple inputs.

---

## 4. Extractor Order (Dependency Chain)

The extractors reference each other (LinkedTag/LinkedStep/LinkedFB...). Recommended order:

| Order | Extractor | RD | Dependency |
|-------|-----------|----|-----------| 
| 1 | IO | RD01 | _parsed.md |
| 2 | DataDict | RD02 | _parsed.md + RD01 |
| 3 | Flowchart | RD03 | _parsed.md + RD02 |
| 4 | Mode | RD04 | _parsed.md + RD02 |
| 5 | Safety | RD05 ⚠️ | _parsed.md |
| 6 | Motion | RD06 | _parsed.md + RD01, RD02 |
| 7 | Timing | RD07 | _parsed.md + RD03 |
| 8 | Alarm | RD08 | _parsed.md + RD05, RD07 |
| 9 | Comms | RD09 | _parsed.md + RD02 |
| 10 | FBSpec | RD10 | _parsed.md (most comprehensive) |
| 11 | HMI | RD11 | _parsed.md + RD01, RD08 |
| 12 | UseCase | RD12 | _parsed.md + RD03, RD04, RD10 |
| 13 | Annotation | RD13 | _parsed.md + raw source code |
| 14 | Modernization | RD14 | RD13 + _parsed.md |

---

## 5. Safety Warning (RD05)

> ⚠️ **PROMPT_EXTRACT_SAFETY_FROM_CODE.md** is a special prompt:
> - The AI **NEVER** estimates a SIL or PLr level
> - All output is in `DRAFT_UNVERIFIED` status
> - Cannot go to product/production WITHOUT certified safety engineer approval
> - For details: `MDSCHEMA_RAWDATA_05_SAFETY.md`

---

## 6. Output Files (Naming Convention)

| Stage | File | Location |
|-------|------|----------|
| Platform parser output | `_parsed.md` | `<project>/_input/` |
| Extractor draft (Excel) | `RD<NN>_<Topic>.xlsx` | `<project>/_input/` |
| Extractor draft (MD) | `RD<NN>_<Topic>_draft.md` | `<project>/_input/` |
| Safety draft (special) | `RD05_Safety_DRAFT_UNVERIFIED.md` | `<project>/_input/` |
| Approved after Gate 3 | `RD<NN>_<Topic>.md` (draft suffix removed) | `<project>/metadata/` |

---

## 7. Data Classification

All of these prompts read old customer code. Data classification rules:

| Class | Upload | Example |
|-------|--------|---------|
| 🟢 PUBLIC | Anywhere | General pattern examples |
| 🟡 INTERNAL | Cursor/Claude tier | In-company use |
| 🟠 **CONFIDENTIAL** | Self-hosted or Enterprise AI | **Most customer projects** |
| 🔴 RESTRICTED | Air-gapped only | ITAR/EAR, defense, pharma |

Details: `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`

---

## 8. AI Target Model

All prompts have been tested with the following AI models:

| AI | Recommended version |
|----|---------------------|
| Anthropic Claude | Sonnet 4+ / Opus 4+ |
| OpenAI GPT | GPT-4+ |
| Cursor | Composer / Tab autocomplete (with Sonnet 4+) |

Opus 4+ is recommended for **RD05 Safety, RD13 Annotation, RD14 Modernization** (high reasoning intensity).

---

## 9. Language Policy

- **Prompts (system):** English (since v3.1.0-alpha; previously Turkish in v3.0.0)
- **AI output (original code comments):** preserved AS-IS (German/Turkish/other)
- **AI output (new explanations):** English by default; per-project `output_language` can switch to TR/DE
- **Details:** `01_GLOBAL_STANDARDS/rules/GLOBAL_LANG_POLICY.md`

---

## 10. Feedback

At the end of each prompt:
```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/analyze/PROMPT_<...>.md" \
  --reason "..." \
  --suggestion "..."
```

---

## 11. Related Files

- **Pipeline orchestrator:** `PIPELINE_CODE_REWRITE.md` (root)
- **Specs:** `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_*.md` (14 files)
- **Naming rule:** `01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md`
- **Data classification:** `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`
- **Language policy:** `01_GLOBAL_STANDARDS/rules/GLOBAL_LANG_POLICY.md`
- **Retrofit guides:** `02_PROJECT_TYPES/RETROFIT/` (to be completed in Phase 4)
- **Knowledge base:** `06_KNOWLEDGE_BASE/` (platform-specific pitfalls)

---

## 12. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-15 | First release — 5 parsers + 14 extractors; full 14-Point Pack coverage |
| 1.1.0 | 2026-05-23 | Full English translation of the README body |
| 1.2.0 | 2026-06-11 | `PROMPT_ANALYZE_S7_400_STL.md` added — dedicated S7-400 parser (B-L6 / S-21); parser family 5 → 6 |
| 1.3.0 | 2026-06-11 | `PROMPT_COMPARE_VERSIONS.md` added — change-hypotheses prompt for the Version Compare GUI view (out-of-pipeline) |

---

*The single authoritative prompt library for Pipeline Gate 2. If a new platform or RD is added, it must be reflected here.*
