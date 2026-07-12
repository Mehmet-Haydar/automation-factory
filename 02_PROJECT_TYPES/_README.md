---
title: 02_PROJECT_TYPES — Folder README
version: 1.1.0
last_updated: 2026-05-23
status: ACTIVE
last_validated: 2026-05
---

# `02_PROJECT_TYPES/` — Retrofit + Greenfield Workflows

> **This folder contains the human workflow guides for the two main project types.** Retrofit = renewing an old system; Greenfield = design from scratch. A separate guide for each RD point.

---

## 1. Subdirectories

```
02_PROJECT_TYPES/
├── _README.md  ← this file
│
├── RETROFIT/             ← Old code → standard RD extraction
│   ├── RETROFIT_MAESTRO.md           (project orchestrator)
│   ├── RETROFIT_HARDWARE_ANALYSIS.md
│   ├── RETROFIT_IO_EXTRACT.md        (RD01)
│   ├── RETROFIT_EXTRACT_DATADICT.md  (RD02)
│   ├── RETROFIT_FLOWCHART.md         (RD03; STUB)
│   ├── RETROFIT_EXTRACT_MODE.md      (RD04)
│   ├── RETROFIT_EXTRACT_TIMING.md    (RD07)
│   ├── RETROFIT_EXTRACT_ALARM.md     (RD08)
│   ├── RETROFIT_EXTRACT_USECASE.md   (RD12)
│   └── RETROFIT_MODERNIZATION_GUIDE.md (RD14 + decision matrix)
│
└── GREENFIELD/           ← Design from scratch
    ├── GREENFIELD_MAESTRO.md          (project orchestrator)
    ├── GREENFIELD_HARDWARE_SELECTION.md
    ├── GREENFIELD_IO_NEWDESIGN.md     (RD01)
    ├── GREENFIELD_DESIGN_DATADICT.md  (RD02)
    ├── GREENFIELD_FLOWCHART.md        (RD03; STUB)
    ├── GREENFIELD_DESIGN_MODE.md      (RD04)
    ├── GREENFIELD_DESIGN_TIMING.md    (RD07)
    ├── GREENFIELD_DESIGN_ALARM.md     (RD08)
    └── GREENFIELD_DESIGN_USECASE.md   (RD12)
```

---

## 2. Retrofit vs Greenfield Decision Matrix

| Factor | Retrofit | Greenfield |
|--------|----------|------------|
| **Existing system** | Exists, you have the code | None / to be replaced |
| **Budget** | Low (€50K-150K) | High (€200K+) |
| **Duration** | 2-3 months | 6-12 months |
| **Risk** | Low | High (re-certification) |
| **CE certificate** | Stays as-is | Re-obtained |
| **Hardware lifetime** | Existing is reused | New 15+ years |

**Decision document:** the ModernizationDecision matrix in `RETROFIT_MODERNIZATION_GUIDE.md` (RD14).

---

## 3. RD Coverage Mapping

The guides written in Phase 4 cover 5 common RDs:

| RD | Retrofit | Greenfield |
|----|----------|------------|
| RD02 DataDict | RETROFIT_EXTRACT_DATADICT.md | GREENFIELD_DESIGN_DATADICT.md |
| RD04 Mode | RETROFIT_EXTRACT_MODE.md | GREENFIELD_DESIGN_MODE.md |
| RD07 Timing | RETROFIT_EXTRACT_TIMING.md | GREENFIELD_DESIGN_TIMING.md |
| RD08 Alarm | RETROFIT_EXTRACT_ALARM.md | GREENFIELD_DESIGN_ALARM.md |
| RD12 UseCase | RETROFIT_EXTRACT_USECASE.md | GREENFIELD_DESIGN_USECASE.md |

Guides for the other 9 RDs will be added in v3.1.0+ sprints (RD03 Flowchart, RD05 Safety, RD06 Motion, RD09 Comms, RD10 FBSpec, RD11 HMI, RD13 Annotation).

---

## 4. AI Integration

Each guide references the relevant AI prompt via the `ai_prompt:` frontmatter field:

```
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_DATADICT_FROM_CODE.md
```

Workflow:
```
[1] Run the AI prompt → produce a draft RD
       ↓
[2] Apply the human guide in THIS folder → revise the AI output
       ↓
[3] Gate 3 (HUMAN REVIEW) → approval
```

---

## 5. Related Folders

- `01_GLOBAL_STANDARDS/md_schemas/` — The target specs of these guides
- `04_AI_PROMPTS/analyze/` — The AI prompts matching these guides
- `07_PROJECT_TEMPLATE/metadata_template/` — The per-project templates to be filled in

---

## 6. Maestro Files

- `RETROFIT_MAESTRO.md` — Orchestrator for all retrofit projects
- `GREENFIELD_MAESTRO.md` — Orchestrator for all greenfield projects

When starting a new project:
```bash
python 05_SCRIPTS/script_project_init.py \
  --type retrofit \
  --customer <customer> \
  --name <project>
```

---

*Human workflow guides — cannot be delegated to AI. Every line comes from experience.*
