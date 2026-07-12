---
title: 04_AI_PROMPTS — Folder README
version: 1.1.0
last_updated: 2026-07-10
status: ACTIVE
last_validated: 2026-07
---

# `04_AI_PROMPTS/` — AI Prompt Library

> **This folder contains all AI prompts.** Organized into 5 subdirectories: analyze (Gate 2), code_gen (Gate 5), doc_gen, review, test_gen.

> ⚠️ **Runtime vs. manual use (2026-07-10):** the automated pipeline loads
> only the `analyze/` extractors (via `workbench/core/ai_runner.py`) and
> `code_gen/PROMPT_CODE_GEN_SEQUENCE.md`. Gate-5 device code is **NOT**
> prompt-generated at runtime — device FBs are copied verbatim from the
> curated library (`blocks/` + `contracts/`, library-first, SHA-256
> verified) by `05_SCRIPTS/program_assembler.py`. Everything else in
> `code_gen/`, `review/`, `test_gen/`, `doc_gen/` is a **manual-use
> library** for engineers working with an AI IDE (Cursor, Claude Code) —
> not wired into the app.

---

## 1. Subdirectories

```
04_AI_PROMPTS/
├── _README.md  ← this file
├── _PROMPT_HIERARCHY.md  ← prompt map (which prompt at which gate)
│
├── analyze/              ← Gate 2 (DISCOVERY + EXTRACTION)
│   ├── _README.md
│   ├── PROMPT_ANALYZE_<platform>.md   (5 platform parsers)
│   └── PROMPT_EXTRACT_<topic>_FROM_CODE.md  (14 topic extractors)
│
├── code_gen/             ← Gate 5 (CODE GENERATION)
│   ├── PROMPT_CODE_GEN_FB_VALVE.md
│   ├── PROMPT_CODE_GEN_SEQUENCE.md
│   ├── io/               (IO mapping + tag generation)
│   ├── ob/               (OB1, startup, diagnostic, ...)
│   ├── process/          (PID, alarm handler, recipe)
│   ├── system/           (HMI interface, mode manager, watchdog)
│   └── valve/            (2-way, 3-way, modulating, proportional)
│
├── doc_gen/              ← Documentation generation
│   ├── PROMPT_DOC_GEN_AS_BUILT.md
│   ├── PROMPT_DOC_GEN_CASE_STUDY.md
│   └── PROMPT_DOC_GEN_OPERATOR_MANUAL.md
│
├── review/               ← Code review
│   ├── PROMPT_REVIEW_FLOWCHART_MATCH.md
│   ├── PROMPT_REVIEW_INTEGRATOR.md
│   ├── PROMPT_REVIEW_NAMING.md
│   └── PROMPT_REVIEW_SAFETY.md
│
└── test_gen/             ← Test generation (Gate 7 FAT/SAT)
    ├── PROMPT_TEST_GEN_FAT.md
    ├── PROMPT_TEST_GEN_INTEGRATION.md
    └── PROMPT_TEST_GEN_UNIT.md
```

---

## 2. Pipeline Mapping

```
Gate 1: DISCOVERY          → (engineer + customer meeting, no prompt)
Gate 2: EXTRACTION         → analyze/ (parser + extractor)
Gate 3: HUMAN REVIEW       → review/ (human + AI cross-check)
Gate 4: VALIDATION         → 05_SCRIPTS/dev/script_consistency_check.py
Gate 5: CODE GENERATION    → 05_SCRIPTS/program_assembler.py (library-first;
                             code_gen/ prompts = manual-use only, except
                             PROMPT_CODE_GEN_SEQUENCE.md)
Gate 6: SIMULATION         → DOMAIN_SIMULATION_PROCESS_MODEL.md (future)
Gate 7: FAT/SAT            → test_gen/ + doc_gen/
```

Details: `_PROMPT_HIERARCHY.md` (this folder)

---

## 3. Prompt Writing Standard

Each prompt follows this structure:

```
---
title: <name>
version: <semver>
applies_to: [retrofit | greenfield | both]
prerequisite: [<dependent files>]
target_ai: [Claude Sonnet 4+, GPT-4+, ...]
input_source: <source>
output_artifacts: [<outputs>]
schema_target: <validation schema>
role: <platform_parser | topic_extractor | code_gen | review | test_gen | doc_gen>
schema: <PROMPT_ANALYZE | PROMPT_EXTRACT | PROMPT_CODE_GEN | ...>
---

# Title

## 1. When to Use?
## 2. Position in Pipeline
## 3. Target Spec / Input Files
## 4. System Prompt (Fixed section for AI)
## 5. User Prompt Template
## 6. Output Validation
## 7. Typical AI Errors (Categories A/B/C)
## 8. Connection to Spec
## 9. Related Files
## 10. Feedback
```

---

## 4. AI Error Categories (3-Level)

Each prompt lists errors in §7 according to these categories:

| Category | Type | Detection |
|----------|------|-----------|
| **A — Syntax** | Format/regex violation | Automatic (linter) |
| **B — Schema/Standard** | Spec violation | Validator script |
| **C — Semantic** | Semantic error | Manual human |

---

## 5. Target AI Models

| Task | Recommended AI |
|-------|------------|
| Standard extraction | Claude Sonnet 4+ |
| Safety (RD05) | Claude Opus 4+ (reasoning-heavy) |
| Modernization (RD14) | Claude Opus 4+ |
| Code generation | Claude Sonnet 4+ or Cursor enterprise |
| Doc generation | GPT-4+ or Claude Sonnet 4+ |

---

## 6. Data Classification Warning

> ⚠️ Customer code is mostly CONFIDENTIAL. Public AI (ChatGPT.com, claude.ai web) FORBIDDEN. Use self-hosted or Enterprise AI.

Details: `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`

---

## 7. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/<file>" \
  --reason "..." \
  --suggestion "..."
```

---

## 8. Related Folders

- `01_GLOBAL_STANDARDS/md_schemas/` — Target specs for all extractor prompts
- `02_PROJECT_TYPES/` — Human workflow equivalents for prompts
- `05_SCRIPTS/` — Validator + orchestrator scripts
- `08_METADATA_INPUT/schema/` — JSON validation schemas

---

*Single source of truth for all prompts. When adding new AI prompts, follow the structure standard.*
