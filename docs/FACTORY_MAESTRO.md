---
title: Automation Factory Manifesto
version: 1.2.0
last_validated: 2026-05
last_updated: 2026-05-08
platform: TIA Portal V18+
maintainer: <name-surname>
related: [PROJECT_VISION.md, PROGRESS_TRACKER.md, FACTORY_MOBILE_WORKFLOW.md, FACTORY_TASK_PLAYBOOK.md, FACTORY_IDEAS_BACKLOG.md]
---

# FACTORY_MAESTRO.md — Automation Factory Manifesto

> **Purpose:** The central framework for managing industrial automation projects (retrofit & greenfield) in a consistent, repeatable, and scalable way — powered by AI and grounded in engineering discipline.
>
> This file explains **what the system is**, **why it was designed this way**, and **how to use it**. All sub-files are anchored to this manifesto.

---

## 1. Philosophy

Automation Factory is a **living framework**. It operates on two layers:

1. **Factory Layer (this repo)** → Instructions, templates, scripts, prompts. Managed as an independent project in Cursor.
2. **Project Layer (customer projects)** → Copies templates from the factory, follows its rules. Feeds errors and gaps back to the factory when found.

**Core principles:**
- **Single source of truth:** A rule is defined in exactly one place. No duplication.
- **AI is disciplined:** Every AI instruction is a versioned, tested, traceable file.
- **Feedback is mandatory:** Every gap found in the field must be reported back to the factory before the project closes.
- **Timestamp is mandatory:** Every file has a `last_validated` field. Files older than 6 months must be audited.

---

## 2. Naming Standard

**Format:** `[SCOPE]_[DOMAIN]_[SUB_FUNCTION].md`

| Part | Description | Valid Values |
|------|-------------|--------------|
| **SCOPE** | The file's domain of applicability | `GLOBAL`, `RETROFIT`, `GREENFIELD`, `DOMAIN`, `PROMPT`, `SCRIPT`, `KB` |
| **DOMAIN** | Engineering domain | `MAESTRO`, `IO`, `HARDWARE`, `SAFETY`, `HMI`, `COMMS`, `DRIVES`, `TESTING`, `FB`, `NAMING`, `DATA` |
| **SUB_FUNCTION** | Specific function (optional) | `EXTRACT`, `TEMPLATE`, `ANALYSIS`, `NEWDESIGN`, `GEN`, `CONFIG`, `REVIEW`, `FAT`, `SAT` |

**Examples:**
- `RETROFIT_IO_EXTRACT.md` → IO extraction from EPLAN in a retrofit project
- `DOMAIN_SAFETY_CONFIG.md` → Safety (F-PLC) configuration (valid for all project types)
- `PROMPT_CODE_GEN_FB_MOTOR.md` → AI prompt to generate a motor FB
- `KB_PITFALLS_PROFINET.md` → Typical issues encountered with PROFINET

---

## 3. Folder Structure

```
AUTOMATION_FACTORY/
│
├── FACTORY_MAESTRO.md                  ← This file (system backbone, folder + workflow)
├── PROJECT_VISION.md                   ← Vision and principles (north star)
├── SKELETON_BLUEPRINT.md               ← Detailed file inventory
├── PROGRESS_TRACKER.md                 ← Current status, sprint tracking, decision log
├── FACTORY_MOBILE_WORKFLOW.md          ← Mobile workflow discipline [v2.2]
├── FACTORY_IDEAS_BACKLOG.md            ← Factory's own backlog (idea governance) [v2.3]
├── FACTORY_TASK_PLAYBOOK.md            ← Task → file matrix (Cursor/Claude Code) [v2.4]
├── README.md                           ← Quick start guide
├── CHANGELOG.md                        ← Factory version history
├── .cursorrules                        ← Meta-instruction for Cursor
├── .cursor/rules/                      ← Cursor domain rules
│
├── 01_GLOBAL_STANDARDS/                ← Universal rules independent of project type
│   ├── rules/                          ← Human + AI readable (.md)
│   │   ├── GLOBAL_NAMING_STANDARD.md
│   │   ├── GLOBAL_GIT_DISCIPLINE.md
│   │   ├── GLOBAL_DATA_CLASSIFICATION.md
│   │   ├── GLOBAL_PLATFORM_MATRIX.md
│   │   ├── GLOBAL_METADATA_SCHEMA.md
│   │   └── GLOBAL_AI_INTERFACE.md
│   ├── md_schemas/                     ← Internal structure standards for MD files
│   │   ├── MDSCHEMA_PROMPT_CODE_GEN.md       [v2.1]
│   │   ├── MDSCHEMA_DOMAIN_REFERENCE.md      [v2.1]
│   │   └── MDSCHEMA_IDEA_INTEGRATION.md      [v2.3]
│   └── templates/                      ← Copy-paste artifacts
│       ├── GLOBAL_FB_TEMPLATE.scl
│       ├── GLOBAL_OB_TEMPLATE.scl
│       ├── GLOBAL_FC_TEMPLATE.scl
│       ├── GLOBAL_DB_TEMPLATE.scl
│       ├── GLOBAL_PROJECT_STATE_SCHEMA.json
│       └── GLOBAL_PROJECT_STATE_TEMPLATE.md
│
├── 02_PROJECT_TYPES/
│   ├── RETROFIT/                       ← Existing machine modernization
│   │   ├── RETROFIT_MAESTRO.md
│   │   ├── RETROFIT_IO_EXTRACT.md
│   │   ├── RETROFIT_HARDWARE_ANALYSIS.md
│   │   └── RETROFIT_FLOWCHART.md
│   └── GREENFIELD/                     ← Projects built from scratch
│       ├── GREENFIELD_MAESTRO.md
│       ├── GREENFIELD_IO_NEWDESIGN.md
│       ├── GREENFIELD_HARDWARE_SELECTION.md
│       └── GREENFIELD_FLOWCHART.md
│
├── 03_DOMAIN_TOOLS/            ← Specialist domains independent of project type
│   ├── DOMAIN_INPUT_SOURCES.md         ← Retrofit/Greenfield input matrix [v2.2]
│   ├── DOMAIN_SAFETY_CONFIG.md
│   ├── DOMAIN_HMI_STANDARD.md
│   ├── DOMAIN_COMMS_PROTOCOLS.md
│   ├── DOMAIN_COMMS_NETWORK_PLAN.md
│   ├── DOMAIN_DRIVES_CONFIG.md
│   ├── DOMAIN_SIMULATION_PROCESS_MODEL.md
│   ├── DOMAIN_TESTING_UNIT.md
│   ├── DOMAIN_TESTING_INTEGRATION.md
│   ├── DOMAIN_TESTING_FAT.md
│   └── DOMAIN_TESTING_SAT.md
│
├── 04_AI_PROMPTS/                      ← AI directive templates
│   ├── code_gen/
│   │   ├── PROMPT_CODE_GEN_FB_MOTOR.md
│   │   ├── PROMPT_CODE_GEN_FB_VALVE.md
│   │   └── PROMPT_CODE_GEN_SEQUENCE.md
│   ├── review/
│   │   ├── PROMPT_REVIEW_SAFETY.md
│   │   └── PROMPT_REVIEW_NAMING.md
│   └── doc_gen/
│       └── PROMPT_DOC_GEN_CASE_STUDY.md
│
├── 05_SCRIPTS/                         ← Automation and utility scripts
│   ├── script_project_init.py          ← Create new project folder
│   ├── script_factory_audit.py         ← Detect outdated files
│   ├── script_consistency_check.py     ← Naming standard audit
│   ├── script_propose_update.py        ← Field feedback to factory
│   └── script_weekly_status.sh         ← Weekly git summary
│
├── 06_KNOWLEDGE_BASE/                  ← Lessons learned
│   ├── KB_PITFALLS_COMMS.md
│   ├── KB_PITFALLS_SAFETY.md
│   ├── KB_VENDOR_QUIRKS.md
│   └── KB_FEEDBACK_LOG.md              ← Feedback received from the field
│
└── 07_PROJECT_TEMPLATE/                ← Skeleton to be copied for new projects
    ├── PROJECT_MAESTRO.md
    ├── PROJECT_STATE.md
    └── README.md
```

---

## 4. Workflow

### 4.1 Starting a New Project

```bash
python 05_SCRIPTS/script_project_init.py \
  --name "Beispielmaschine_Retrofit" \
  --type retrofit \
  --customer "CustomerName" \
  --output ~/projects/
```

The script performs the following:
1. Copies the contents of `07_PROJECT_TEMPLATE/` to the target folder.
2. Writes the factory reference and project metadata into `PROJECT_MAESTRO.md`.
3. Adds a reference to `RETROFIT_MAESTRO.md` or `GREENFIELD_MAESTRO.md` based on project type.
4. Initializes a git repo (optional).

### 4.2 Daily Work

1. Open the customer project in Cursor.
2. `PROJECT_MAESTRO.md` contains a symbolic link/reference back to the factory.
3. When instructing the AI: *"Generate a motor FB according to `PROMPT_CODE_GEN_FB_MOTOR.md` in the factory."*
4. The AI reads the factory rule and applies it to the project.

### 4.3 Feedback Loop (Critical)

When a gap or error is found in the field:

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md" \
  --reason "Encoder naming is missing" \
  --suggestion "ENC_<location>_<axis>"
```

The script performs the following:
1. Adds a new entry to `06_KNOWLEDGE_BASE/KB_FEEDBACK_LOG.md`.
2. Opens a new git branch in the factory repo.
3. Flags the relevant file and queues it for manual correction.

**Rule:** Before a customer project is closed, it must be verified that at least one feedback item has been sent back to the factory.

### 4.4 Periodic Maintenance

```bash
# Every 3 months
python 05_SCRIPTS/dev/script_factory_audit.py
```

Output:
- Files with a `last_validated` timestamp older than 6 months
- Files not complying with the naming standard
- Files left empty (containing TODO)

### 4.5 Idea Governance — Factory's Own Evolution Management [v2.3]

The factory is **its own customer**. Field feedback (Section 4.3) covers changes **triggered by customer projects**. But ideas also arrive from other sources:
- Architectural suggestions from other AI systems
- The user's own thoughts
- Inspiration from literature or training
- Observations from similar frameworks

These do not go into `KB_FEEDBACK_LOG` — they go into a dedicated place: **`FACTORY_IDEAS_BACKLOG.md`**.

**Flow:**
```
[New idea arrives]
  → Logged as NEW in FACTORY_IDEAS_BACKLOG.md
[Evaluation]
  → REVIEWED → APPROVED / REJECTED / DEFERRED
[If APPROVED]
  → 7-section analysis per MDSCHEMA_IDEA_INTEGRATION.md
  → Conflict check (Section 4 of MDSCHEMA)
  → Approval → implementation → APPLIED
  → Reflected in CHANGELOG
```

**Analogy:** The backlog is the "idea waiting room"; CHANGELOG is the "record of what was built". They are not parallel systems — they are sequential stages.

---

## 5. Cursor Integration

When the factory is opened as a Cursor project:

1. `.cursorrules` → tells Cursor "this repo is Automation Factory."
2. `.mdc` files under `.cursor/rules/` provide domain-specific rules to Cursor.
3. When AI edits a file, the relevant rules are automatically loaded.

---

## 6. Versioning Policy

- **Major (X.0.0):** Folder structure changes, backwards-incompatible naming changes.
- **Minor (1.X.0):** New domain, new prompt, new script.
- **Patch (1.0.X):** Correction to an existing file, addition of lessons learned.

All changes are documented in `CHANGELOG.md`.

---

## 7. Stub Files (TODO List)

> **As of v2.4, this list no longer lives here — for current status see: `PROGRESS_TRACKER.md` Section 2 and `FACTORY_TASK_PLAYBOOK.md`.**
>
> Current "what is filled vs. what is empty" is maintained in a single place (Single Source of Truth). This section only preserves v1.0 records and can be referenced for historical context.

### Files that were filled as of v1.0 (historical record)

- `FACTORY_MAESTRO.md`
- `01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md`
- `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`
- `01_GLOBAL_STANDARDS/templates/GLOBAL_FB_TEMPLATE.scl`
- `02_PROJECT_TYPES/RETROFIT/RETROFIT_IO_EXTRACT.md`
- `04_AI_PROMPTS/code_gen/PROMPT_CODE_GEN_FB_MOTOR.md`
- `05_SCRIPTS/*.py`
- `.cursorrules`

### Key files added in v2.x (for context)

- v2.1: `MDSCHEMA_PROMPT_CODE_GEN.md`, `MDSCHEMA_DOMAIN_REFERENCE.md`, `script_bulk_md_edit.py`, `script_md_schema_validator.py`
- v2.2: `FACTORY_MOBILE_WORKFLOW.md`, `DOMAIN_INPUT_SOURCES.md`
- v2.3: `FACTORY_IDEAS_BACKLOG.md`, `MDSCHEMA_IDEA_INTEGRATION.md`
- v2.4: `FACTORY_TASK_PLAYBOOK.md`, `MDSCHEMA_PROMPT_CODE_GEN.md` Section 4.5 (Error Management Loop), `PROJECT_VISION.md` Section 3.3 (Meta-Project vs. Customer Project)

### For files still marked as STUB

`PROGRESS_TRACKER.md` is updated every sprint. Check it for the current fill status. For which files are needed for a given task → `FACTORY_TASK_PLAYBOOK.md`.

---

*This file is the backbone of Automation Factory. Changes are tracked in `CHANGELOG.md`, decisions in `PROGRESS_TRACKER.md` Section 3, and ideas in `FACTORY_IDEAS_BACKLOG.md`.*
