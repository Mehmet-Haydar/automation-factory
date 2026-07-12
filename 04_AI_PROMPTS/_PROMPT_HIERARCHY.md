---
title: AI Prompt Hierarchy Map
version: 1.1.0
last_updated: 2026-06-11
status: ACTIVE
last_validated: 2026-05
---

# `_PROMPT_HIERARCHY.md` — AI Prompt Hierarchy Map

> **This file maps all AI prompts to pipeline gates, RDs, and roles.** Provides instant answers to engineers: "Which prompt should I use for this task?"

---

## 1. Pipeline Gate Mapping

```
Gate 1: DISCOVERY
    (engineer + customer meeting; no AI prompt)
       ↓
Gate 2A: PLATFORM PARSING
    ├── PROMPT_ANALYZE_S5_AWL.md
    ├── PROMPT_ANALYZE_S7_300_STL.md
    ├── PROMPT_ANALYZE_S7_400_STL.md
    ├── PROMPT_ANALYZE_S7_1500_OPENNESS.md
    ├── PROMPT_ANALYZE_AB_L5X.md
    └── PROMPT_ANALYZE_CODESYS.md
       ↓ (_parsed.md generated)
Gate 2B: TOPIC EXTRACTION
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
       ↓
Gate 3: HUMAN REVIEW
    ├── PROMPT_REVIEW_NAMING.md
    ├── PROMPT_REVIEW_SAFETY.md
    ├── PROMPT_REVIEW_FLOWCHART_MATCH.md
    └── PROMPT_REVIEW_INTEGRATOR.md
       ↓
Gate 4: VALIDATION
    (Python validator; no AI prompt)
       ↓
Gate 5: CODE GENERATION
    RUNTIME: 05_SCRIPTS/program_assembler.py — library-first (blocks/ +
    contracts/, verbatim copy, SHA-256). The ONLY runtime AI code-gen
    prompt is PROMPT_CODE_GEN_SEQUENCE.md (sequence FB from reviewed
    RD03). The rest of code_gen/ is a manual-use library (AI IDE).
    code_gen/
    ├── PROMPT_CODE_GEN_FB_VALVE.md
    ├── PROMPT_CODE_GEN_SEQUENCE.md
    ├── io/PROMPT_IO_MAPPING.md
    ├── io/PROMPT_IO_TAG_GEN.md
    ├── ob/PROMPT_OB_MAIN_OB1.md
    ├── ob/PROMPT_OB_CYCLIC_INTERRUPT.md
    ├── ob/PROMPT_OB_DIAGNOSTIC_OB82.md
    ├── ob/PROMPT_OB_RACK_FAILURE_OB86.md
    ├── ob/PROMPT_OB_STARTUP_OB100.md
    ├── process/PROMPT_PROCESS_ALARM_HANDLER.md
    ├── process/PROMPT_PROCESS_ANALOG_SCALING.md
    ├── process/PROMPT_PROCESS_PID_LOOP.md
    ├── process/PROMPT_PROCESS_RECIPE_MANAGER.md
    ├── system/PROMPT_SYSTEM_DIAGNOSTIC_BUFFER.md
    ├── system/PROMPT_SYSTEM_HMI_INTERFACE.md
    ├── system/PROMPT_SYSTEM_MODE_MANAGER.md
    ├── system/PROMPT_SYSTEM_WATCHDOG.md
    └── valve/PROMPT_VALVE_*.md
       ↓
Gate 6: SIMULATION
    (process model + test infrastructure; AI prompt to be added in v3.2.0+)
       ↓
Gate 7: FAT/SAT
    test_gen/
    ├── PROMPT_TEST_GEN_FAT.md
    ├── PROMPT_TEST_GEN_INTEGRATION.md
    └── PROMPT_TEST_GEN_UNIT.md

    doc_gen/
    ├── PROMPT_DOC_GEN_AS_BUILT.md
    ├── PROMPT_DOC_GEN_CASE_STUDY.md
    └── PROMPT_DOC_GEN_OPERATOR_MANUAL.md

Out-of-pipeline (GUI tools, not gate-bound):
    └── analyze/PROMPT_COMPARE_VERSIONS.md   → Version Compare view
        (change hypotheses from the deterministic version diff;
         output stays DRAFT_UNVERIFIED, never persisted as an RD)
```

---

## 2. Classification by Role

| Role | Count | Folder |
|------|-------|--------|
| platform_parser | 6 | `analyze/PROMPT_ANALYZE_*.md` |
| topic_extractor | 14 | `analyze/PROMPT_EXTRACT_*_FROM_CODE.md` |
| change_analyst | 1 | `analyze/PROMPT_COMPARE_VERSIONS.md` (Version Compare view) |
| code_gen | ~20 | `code_gen/` (subfolders) |
| review | 4 | `review/` |
| test_gen | 3 | `test_gen/` |
| doc_gen | 3 | `doc_gen/` |
| **TOTAL** | **~50** | |

---

## 3. RD Mapping (14-Point Pack)

| RD | Extractor (Gate 2) | Code Gen (Gate 5) | Review (Gate 3) |
|----|--------------------|--------------------|------------------|
| RD01 IO | PROMPT_EXTRACT_IO | PROMPT_IO_MAPPING, PROMPT_IO_TAG_GEN | PROMPT_REVIEW_NAMING |
| RD02 DataDict | PROMPT_EXTRACT_DATADICT | (code_gen/db future) | PROMPT_REVIEW_NAMING |
| RD03 Flowchart | PROMPT_EXTRACT_FLOWCHART | PROMPT_CODE_GEN_SEQUENCE | PROMPT_REVIEW_FLOWCHART_MATCH |
| RD04 Mode | PROMPT_EXTRACT_MODE | PROMPT_SYSTEM_MODE_MANAGER | (manual) |
| RD05 Safety ⚠️ | PROMPT_EXTRACT_SAFETY | (human + certified engineer) | PROMPT_REVIEW_SAFETY |
| RD06 Motion | PROMPT_EXTRACT_MOTION | (code_gen/motion future) | (manual) |
| RD07 Timing | PROMPT_EXTRACT_TIMING | PROMPT_SYSTEM_WATCHDOG | (manual) |
| RD08 Alarm | PROMPT_EXTRACT_ALARM | PROMPT_PROCESS_ALARM_HANDLER | (manual) |
| RD09 Comms | PROMPT_EXTRACT_COMMS | (code_gen/comm future) | (manual) |
| RD10 FBSpec | PROMPT_EXTRACT_FBSPEC | PROMPT_CODE_GEN_FB_VALVE, etc. | PROMPT_REVIEW_INTEGRATOR |
| RD11 HMI | PROMPT_EXTRACT_HMI | PROMPT_SYSTEM_HMI_INTERFACE | (manual) |
| RD12 UseCase | PROMPT_EXTRACT_USECASE | (test_gen source) | (manual) |
| RD13 Annotation | PROMPT_EXTRACT_ANNOTATION | - | (manual) |
| RD14 Modernization | PROMPT_EXTRACT_MODERNIZATION | (recommendations applied by human) | (customer approval) |

---

## 4. Platform-Specific Prompts

Some prompts are platform-specific:

| Platform | Parser | Migration KB |
|----------|--------|--------------|
| Siemens S5 | PROMPT_ANALYZE_S5_AWL | KB_PITFALLS_S5_TO_S7 (future) |
| Siemens S7-300 Classic | PROMPT_ANALYZE_S7_300_STL | KB_PITFALLS_S7CLASSIC_TO_TIA (future) |
| Siemens S7-400 Classic (incl. 400H/F) | PROMPT_ANALYZE_S7_400_STL | KB_PITFALLS_S7CLASSIC_TO_TIA (future) |
| Siemens S7-1200/1500 (TIA) | PROMPT_ANALYZE_S7_1500_OPENNESS | (native) |
| Allen-Bradley | PROMPT_ANALYZE_AB_L5X | KB_PITFALLS_AB_TO_SIEMENS (future) |
| CODESYS / TwinCAT / EcoStruxure | PROMPT_ANALYZE_CODESYS | KB_PITFALLS_CODESYS_TO_SIEMENS (future) |

---

## 5. AI Model Recommendations

| Category | Recommended AI |
|----------|------------|
| Platform parsing (large XML) | Claude Sonnet 4+ or Opus 4+ |
| Standard extraction | Claude Sonnet 4+ |
| Safety extraction (RD05) | Claude Opus 4+ (critical reasoning) |
| Modernization (RD14) | Claude Opus 4+ |
| Code generation | Claude Sonnet 4+ or Cursor enterprise |
| Doc generation | GPT-4+ or Claude Sonnet 4+ |
| Translation (v4.0.0) | More economical model (Haiku 4+, GPT-4o-mini) |

---

## 6. Data Classification Table

All prompts read customer code. Data class matters:

| Class | Permitted AI |
|-------|----------------|
| 🟢 PUBLIC | Any platform |
| 🟡 INTERNAL | Cursor enterprise, Claude.ai Team+ |
| 🟠 CONFIDENTIAL | Self-hosted or Enterprise tier (Bedrock, Azure OpenAI Enterprise) |
| 🔴 RESTRICTED | Air-gapped system, AI forbidden or severely limited |

---

## 7. Cross-Reference: Which Prompt Uses Which Spec?

```
prompt.prerequisite frontmatter field establishes this chain:

PROMPT_EXTRACT_IO_FROM_CODE.md
  prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_01_IO.md, ...]

PROMPT_EXTRACT_DATADICT_FROM_CODE.md
  prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_02_DATADICT.md, ...]
  ...

Result: When running AI prompt, these specs are included in context.
```

---

## 8. Sprint Plan (v3.0.0-alpha onwards)

| Sprint | Addition |
|--------|----------|
| v3.1.0 | code_gen/motion/ (code generation for RD06) |
| v3.1.0 | code_gen/comm/ (code generation for RD09) |
| v3.1.0 | code_gen/db/ (DB generation for RD02) |
| v3.2.0 | sim/ folder (Gate 6 prompts) |
| v3.2.0 | review/PROMPT_REVIEW_MODE_TRANSITION.md |
| v3.3.0 | doc_gen/PROMPT_DOC_GEN_TUV_PACKAGE.md (CE/TUV document preparation) |

---

## 9. Related Files

- **Folder README:** `04_AI_PROMPTS/_README.md`
- **Pipeline:** `PIPELINE_CODE_REWRITE.md`
- **14-Point Pack:** `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_*.md`
- **Schemas:** `08_METADATA_INPUT/schema/rd*.schema.json`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/`

---

*v1.0.0 — AI prompt map. This file must be updated when new prompts are added.*
