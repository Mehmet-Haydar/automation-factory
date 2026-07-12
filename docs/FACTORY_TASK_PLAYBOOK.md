---
title: Factory Task Playbook
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
purpose: task_to_files_matrix
related: [FACTORY_MAESTRO.md, FACTORY_MOBILE_WORKFLOW.md, MDSCHEMA_PROMPT_CODE_GEN.md, MDSCHEMA_DOMAIN_REFERENCE.md, MDSCHEMA_IDEA_INTEGRATION.md]
---

# FACTORY_TASK_PLAYBOOK.md

> **This file is the matrix that tells the AI the minimum file set when you say "I'm going to do task X".**
>
> Philosophy: don't make the AI guess; give it a fixed reference. Reduces the risk of hitting the token limit and improves output quality.

---

## 1. Why Does This File Exist?

When you open a new chat in Cursor/Claude Code, it is unclear **which files the AI should read**. Three problems:

1. **Token waste:** the AI loads files it does not need
2. **Token limit overrun:** loading too large a file set fills the context and the task can't be done
3. **Inconsistent output:** the AI reads different files each time, so output quality varies

This playbook is the **single source of truth** — the **minimum sufficient set** for each task is here.

---

## 2. How to Use It

### When you open a new chat in Cursor:

1. Find the task in the table below
2. Add the items in the "Files to load" column to the context you open in Cursor
3. Prepare the file/folder in the "Output" column
4. Run the script in the "Quality check" column

### Typical command to the AI:

```
TASK: <task name, take it from the playbook>
LOADED REFERENCES: <tell the AI the list from the playbook has been loaded>
OUTPUT: <take it from the playbook>
QUALITY CHECK: <take it from the playbook>

Start when ready.
```

---

## 3. TASK MATRIX

### 3.1 Sprint 1 — Foundations

#### TASK-1.1: Fill in GLOBAL_METADATA_SCHEMA

| Field | Value |
|-------|-------|
| **Files to load** | `GLOBAL_NAMING_STANDARD.md`, `MDSCHEMA_DOMAIN_REFERENCE.md`, `08_METADATA_INPUT/METADATA_INPUT_GUIDE.md` |
| **Target file** | `01_GLOBAL_STANDARDS/rules/GLOBAL_METADATA_SCHEMA.md` (STUB → FILLED) |
| **Output structure** | JSON schema definition + Excel column mapping for motor, valve, sensor, pid_loop, alarm |
| **Quality check** | `python 05_SCRIPTS/dev/script_md_schema_validator.py` |
| **Estimated tokens** | ~15K input, ~10K output |

#### TASK-1.2: Fill in GLOBAL_AI_INTERFACE

| Field | Value |
|-------|-------|
| **Files to load** | `MDSCHEMA_DOMAIN_REFERENCE.md`, `FACTORY_MAESTRO.md` |
| **Target file** | `01_GLOBAL_STANDARDS/rules/GLOBAL_AI_INTERFACE.md` (STUB → FILLED) |
| **Output structure** | AI contract: input format, output format, error-handling protocol |
| **Quality check** | `script_md_schema_validator.py` |

#### TASK-1.3: Fill in the SCL templates (OB / FC / DB)

| Field | Value |
|-------|-------|
| **Files to load** | `GLOBAL_FB_TEMPLATE.scl` (as reference), `GLOBAL_NAMING_STANDARD.md` |
| **Target file** | `01_GLOBAL_STANDARDS/templates/GLOBAL_OB_TEMPLATE.scl` (STUB → FILLED) — then FC, DB |
| **Output structure** | Three separate working SCL templates |
| **Quality check** | Import into TIA Portal V18 + syntax check |

#### TASK-1.4: Produce Excel metadata templates

| Field | Value |
|-------|-------|
| **Files to load** | `GLOBAL_METADATA_SCHEMA.md` (after TASK-1.1 is done), `METADATA_INPUT_GUIDE.md` |
| **Target file** | `08_METADATA_INPUT/template_motors.xlsx`, `template_valves.xlsx`, `template_sensors.xlsx`, `template_pid_loops.xlsx`, `template_alarms.xlsx` |
| **Output structure** | Empty templates + 1-2 example rows + dropdown validations |
| **Quality check** | Manual: fill in a motor row, can it be converted to JSON |

---

### 3.2 Sprint 2 — OB Skeleton

#### TASK-2.1: Write the OB prompt

| Field | Value |
|-------|-------|
| **Files to load** | `MDSCHEMA_PROMPT_CODE_GEN.md`, `GLOBAL_OB_TEMPLATE.scl` (TASK-1.3 done), `GLOBAL_NAMING_STANDARD.md`, an existing motor prompt (e.g. `PROMPT_MOTOR_DOL.md`) as reference |
| **Target file** | `04_AI_PROMPTS/code_gen/ob/PROMPT_OB_MAIN_OB1.md` (STUB → FILLED) — then OB100, OB82, OB86, Cyclic Interrupt |
| **Output structure** | Prompt fully compliant with MDSCHEMA_PROMPT_CODE_GEN |
| **Quality check** | `script_md_schema_validator.py` |

---

### 3.3 Sprint 0.5 — Filling the Gaps

#### TASK-0.5.1: Fill in the Retrofit/Greenfield Maestro

| Field | Value |
|-------|-------|
| **Files to load** | `MDSCHEMA_DOMAIN_REFERENCE.md`, `DOMAIN_INPUT_SOURCES.md`, existing `RETROFIT_IO_EXTRACT.md` (reference) |
| **Target file** | `02_PROJECT_TYPES/RETROFIT/RETROFIT_MAESTRO.md` (content expansion) |
| **Output structure** | Workflow, decision tables, lessons learned |
| **Quality check** | `script_md_schema_validator.py` |

#### TASK-0.5.2: Write the motor router prompt

| Field | Value |
|-------|-------|
| **Files to load** | `MDSCHEMA_PROMPT_CODE_GEN.md`, the existing 5 motor prompts (DOL, YD, Soft-starter, VFD, Servo) |
| **Target file** | `04_AI_PROMPTS/code_gen/PROMPT_CODE_GEN_FB_MOTOR.md` |
| **Output structure** | Router: a prompt that reads the motor metadata, infers the type, and routes to the correct sub-prompt |

---

### 3.4 Sprint 4 — Domain + HMI

#### TASK-4.1: Fill in DOMAIN_HMI_STANDARD

| Field | Value |
|-------|-------|
| **Files to load** | `MDSCHEMA_DOMAIN_REFERENCE.md`, `GLOBAL_NAMING_STANDARD.md`, `DOMAIN_DRIVES_CONFIG.md` (as an example) |
| **Target file** | `03_DOMAIN_TOOLS/DOMAIN_HMI_STANDARD.md` |
| **Output structure** | HMI tag naming, alarm classification, screen types, multi-language, ISA-101 reference, target platform matrix (WinCC Unified vs Classic) |
| **Dependent IDEA** | IDEA-013, IDEA-021 |

#### TASK-4.2: Fill in DOMAIN_TESTING_* (4 files)

| Field | Value |
|-------|-------|
| **Files to load** | `MDSCHEMA_DOMAIN_REFERENCE.md` |
| **Target file** | `DOMAIN_TESTING_UNIT.md`, `DOMAIN_TESTING_INTEGRATION.md`, `DOMAIN_TESTING_FAT.md`, `DOMAIN_TESTING_SAT.md` |
| **Important rule** | The **`test_environment` field is mandatory** in every file (sim / real_plc / hil / mixed). Per IDEA-012 |

---

### 3.5 Sprint 5 — Review + Test Generation

#### TASK-5.1: Write PROMPT_REVIEW_INTEGRATOR

| Field | Value |
|-------|-------|
| **Files to load** | `MDSCHEMA_PROMPT_CODE_GEN.md`, the existing review prompts (NAMING, SAFETY, FLOWCHART_MATCH) |
| **Target file** | `04_AI_PROMPTS/review/PROMPT_REVIEW_INTEGRATOR.md` |

---

### 3.6 Sprint 6 — Automation

#### TASK-6.1: Write script_excel_to_metadata.py

| Field | Value |
|-------|-------|
| **Files to load** | `GLOBAL_METADATA_SCHEMA.md` (TASK-1.1 done), `METADATA_INPUT_GUIDE.md`, an existing script (e.g. `script_consistency_check.py`) |
| **Target file** | `05_SCRIPTS/dev/script_excel_to_metadata.py` (STUB → FILLED) |
| **Dependency** | `pandas`, `openpyxl`, `jsonschema` |

---

### 3.7 General Tasks

#### TASK-G.1: Evaluate a new IDEA

| Field | Value |
|-------|-------|
| **Files to load** | `FACTORY_IDEAS_BACKLOG.md`, `MDSCHEMA_IDEA_INTEGRATION.md`, `PROJECT_VISION.md`, `FACTORY_MAESTRO.md` |
| **Action** | Fill in the IDEA block, produce a 7-section analysis, run a conflict check, request approval |
| **Output** | Backlog update + (if applied) relevant file changes + CHANGELOG entry |

#### TASK-G.2: Update PROGRESS_TRACKER

| Field | Value |
|-------|-------|
| **Files to load** | `PROGRESS_TRACKER.md` (only this) |
| **Action** | Tick completed checkboxes, update the last-updated date, add a line to the decision history if needed |
| **Mobile-friendly** | Yes, can be done even from a phone |

#### TASK-G.3: Record field feedback

| Field | Value |
|-------|-------|
| **Files to load** | `KB_FEEDBACK_LOG.md`, `FACTORY_MAESTRO.md` (Section 4.3) |
| **Command** | `python 05_SCRIPTS/script_propose_update.py --target <file> --reason <short> --suggestion <proposed change> --project <project name>` |
| **Mobile-friendly** | Partial (the script needs a terminal, but the log entry can be written on mobile) |

#### TASK-G.4: MD schema validation (before every commit)

| Field | Value |
|-------|-------|
| **Files to load** | The relevant schema file |
| **Command** | `python 05_SCRIPTS/dev/script_md_schema_validator.py <file_path>` |
| **Output** | OK / list of errors |

#### TASK-G.5: Stale file audit (every 3 months)

| Field | Value |
|-------|-------|
| **Command** | `python 05_SCRIPTS/dev/script_factory_audit.py` |
| **Output** | Files with a `last_validated` stamp older than 6 months + naming violations + empty STUBs |

---

## 4. Task Dependency Graph

```
TASK-1.1 (METADATA_SCHEMA) ───┬──→ TASK-1.4 (Excel templates)
                              ├──→ TASK-2.1 (OB prompts)
                              └──→ TASK-6.1 (Excel→JSON script)

TASK-1.3 (SCL templates) ─────────→ TASK-2.1 (OB prompts)

TASK-0.5.2 (Motor router) ────────→ after Sprint 1

TASK-4.1 (HMI Standard) ──────────→ post-Sprint-4 HMI prompts (IDEA-022)
```

**Critical:** TASK-1.1 is the priority. Many tasks wait on its output.

---

## 5. Mobile-Friendliness Quick Table

| Task | Mobile-friendly? |
|------|------------------|
| TASK-G.2 (Update tracker) | Yes |
| TASK-G.3 (Field feedback text) | Yes (the script needs a computer, the log text on mobile) |
| Evaluate a new IDEA (TASK-G.1) | Yes (brainstorm) |
| TASK-1.x (content fill-in) | No (long writing) |
| TASK-2.x, 4.x (prompt writing) | No |
| Script writing (TASK-6.x) | No |

See `FACTORY_MOBILE_WORKFLOW.md` for details.

---

## 6. Practical Template for Cursor

Paste this template into a new Cursor chat:

```
This repo is Automation Factory v2.4. Treat FACTORY_TASK_PLAYBOOK.md as the reference.

TASK: TASK-X.Y — <task name>

FILES TO LOAD (I already opened them):
- <file 1>
- <file 2>
- <file 3>

TARGET FILE: <path>

OUTPUT STRUCTURE: <take it from the playbook>

QUALITY CHECK:
1. <script or manual check>
2. Update PROGRESS_TRACKER
3. Add a CHANGELOG entry (if needed)

When the task is done, give a "summary of changes made" + a "commit suggestion".
Start when ready.
```

---

## 7. Maintaining This File

When a new task type is discovered:
1. Add a new TASK sub-section to the relevant Sprint section (3.x)
2. Update the dependency graph (Section 4)
3. Version: minor bump (1.0 → 1.1)

When a task is deleted / changed:
1. Don't delete the old TASK — just add a "DEPRECATED" note
2. If there is a replacement TASK, reference it

---

## 8. No Surprises

This playbook makes the AI's job easier but **does not remove human judgment**. The task context must be reviewed each time; do not apply it blindly.

If there is no exact match for a task in the playbook:
1. First read `FACTORY_MAESTRO.md`
2. Then the relevant MD schema (PROMPT_CODE_GEN / DOMAIN_REFERENCE / IDEA_INTEGRATION)
3. After doing the task, **add a new TASK to this playbook** (for the future)

---

*Task → File → Output: the single source of truth is here.*
