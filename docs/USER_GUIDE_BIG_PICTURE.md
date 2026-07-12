---
title: USER_GUIDE_BIG_PICTURE — Comprehensive Factory Guide
version: 1.2.0
last_updated: 2026-06-14
status: ACTIVE
audience: AUTOMATION_FACTORY developers
last_validated: 2026-06-14
---

# USER_GUIDE_BIG_PICTURE.md — Big Picture Guide

> **This guide is written for the factory developer.** It explains, in one place, how the whole system works, how to run a project, and which file to consult when.

---

## 1. What Is AUTOMATION_FACTORY?

**Context:** An automation engineer in the DACH region — most customers are German; old machines need retrofitting, and there are new projects too.

**Problem:** Every project starts from scratch. You make the same mistakes. AI help is inconsistent. Customer standards are in different languages. Safety is critical but you can't trust the AI.

**Solution = AUTOMATION_FACTORY:** An AI-assisted industrial PLC programming system.
- Old PLC code (S5/S7/AB/CODESYS) → a standardized 14-point pack (RD01..RD14)
- Generation of new industry-standard SCL code with AI
- Output code in TR / EN / DE **via per-project configuration**
- Pipeline controlled by 7 gates (Discovery → Extraction → Review → Validation → Code → Simulation → FAT/SAT)
- For safety, the AI **NEVER** estimates SIL — certified engineer approval is mandatory

---

## 2. Core Concepts

### 2.1 14-Point Raw Data Pack (RD01..RD14)

The 14 standard documents filled in for each project:

| RD | Name | What it contains |
|----|------|------------------|
| 01 | IO List | Physical input/output signals |
| 02 | Data Dictionary | Internal variables (DB/UDT/marker) |
| 03 | Flowchart | Sequence/SFC + Mermaid diagram |
| 04 | Modes | OMAC PackML compliant |
| 05 | **Safety** ⚠️ | F-FB + SIL/PLr (human approval) |
| 06 | Motion | PLCopen Motion v2.0 |
| 07 | Timing | Timer/watchdog |
| 08 | Alarms | ISA-18.2 multi-lang |
| 09 | Communication | PROFINET/EtherCAT/Modbus/OPC UA |
| 10 | FB Spec | Reusable blocks |
| 11 | HMI | ISA-101 screen + tag |
| 12 | Use Cases | FAT/SAT source |
| 13 | Legacy Annotation | Old-code line meaning (retrofit) |
| 14 | Modernization | Anti-pattern + decision matrix (retrofit) |

### 2.2 7-Gate Pipeline

```
Gate 1 DISCOVERY
   ↓ (customer + machine + brief)
Gate 2 EXTRACTION (AI-intensive)
   ↓ (the 14 RDs are filled in)
Gate 3 HUMAN REVIEW
   ↓ (#UNKNOWNS resolved, safety approval obtained)
Gate 4 VALIDATION
   ↓ (script_consistency_check.py)
Gate 5 CODE GENERATION (AI-intensive)
   ↓ (SCL FB/FC/DB generated, comments in the target language)
Gate 6 SIMULATION
   ↓ (offline test environment)
Gate 7 FAT/SAT
   ↓ (factory + site acceptance test)
DELIVERY
```

### 2.3 3-Layer Language Policy

| Layer | Language | Example |
|-------|----------|---------|
| System files | EN (translated 2026-05; was TR through v3.0.0) | All of this factory's MDs |
| User interface | EN | CLI, error messages |
| Code output | per-project (TR/EN/DE) | Comments + HMI text |

The system-file English translation was carried out in 2026-05 (see `docs/TRANSLATION_AUDIT_2026-05-23.md`). Helper that prepares translation batches: `script_prompt_amend.py --action prepare-translation`

### 2.4 Data Classification (4-color)

| Class | Color | Example | AI |
|-------|-------|---------|-----|
| PUBLIC | 🟢 | Pattern examples | Anywhere |
| INTERNAL | 🟡 | In-company | Cursor/Claude Team+ |
| **CONFIDENTIAL** | 🟠 | Customer code | **Self-hosted/Enterprise** |
| RESTRICTED | 🔴 | ITAR/EAR | Air-gapped |

---

## 3. Folder Map

```
AUTOMATION_FACTORY/
├── PIPELINE_CODE_REWRITE.md      ← Pipeline main orchestrator (Gate 1-7)
├── FACTORY_MAESTRO.md            ← Factory-wide orchestrator
├── PROGRESS_TRACKER.md           ← Sprint tracking
├── CHANGELOG.md                  ← Version history
├── FACTORY_IDEAS_BACKLOG.md      ← Idea pool
├── _BUILD_LOG.md                 ← Per-session build log (RESUME HERE)
├── USER_GUIDE_BIG_PICTURE.md     ← THIS FILE
│
├── 01_GLOBAL_STANDARDS/   ← Factory rules
│   ├── rules/             (NAMING, DATA_CLASSIFICATION, LANG_POLICY, ...)
│   ├── md_schemas/        (MDSCHEMA_RAWDATA_01..14)
│   ├── lang_glossary/     (BASE + EN + TR + DE)
│   ├── code_templates/    (GLOBAL_FB_TEMPLATE.scl)
│   └── templates/
│
├── 02_PROJECT_TYPES/      ← Human workflow guides
│   ├── RETROFIT/          (old → standard)
│   └── GREENFIELD/        (design from scratch)
│
├── 03_DOMAIN_TOOLS/       ← Industry-domain standards (mostly STUB)
│
├── 04_AI_PROMPTS/         ← AI prompt library
│   ├── analyze/           (Gate 2: parser + extractor)
│   ├── code_gen/          (Gate 5)
│   ├── review/            (Gate 3)
│   ├── doc_gen/           (Gate 7+)
│   ├── test_gen/          (Gate 7)
│   └── _PROMPT_HIERARCHY.md
│
├── 05_SCRIPTS/            ← Python tools
│
├── 06_KNOWLEDGE_BASE/     ← Pitfalls + lessons learned (mostly STUB)
│
├── 07_PROJECT_TEMPLATE/   ← New project skeleton
│   └── metadata_template/ (RD01..RD14 empty MDs)
│
└── 08_METADATA_INPUT/     ← Validation schemas
    └── schema/            (rd01..rd14.schema.json)
```

---

## 4. Starting a New Project — Step by Step

### 4.1 Step 1 — New project skeleton

```bash
python 05_SCRIPTS/script_project_init.py \
  --type retrofit \
  --customer "Kunde XYZ GmbH" \
  --name "Förderlinie A" \
  --output-lang DE \
  --target ~/projects/
```

Result:
```
~/projects/KundeXYZ_Forderlinie_A/
├── README.md
├── PROJECT_STATE.json
├── PROJECT_MAESTRO.md
├── metadata_template/RD01..RD14.md
├── _input/        (customer source files)
└── _output/       (generated code)
```

### 4.2 Step 2 — Add the customer source files

```bash
# Get a TIA Portal export from the customer, Openness XML
cp customer_files/*.xml ~/projects/KundeXYZ_Forderlinie_A/_input/
```

### 4.3 Step 3 — Gate 2 EXTRACTION (AI-intensive)

```bash
# First the platform parser
# To Cursor/Claude API:
#   prompt: 04_AI_PROMPTS/analyze/PROMPT_ANALYZE_S7_1500_OPENNESS.md
#   input: ~/projects/.../_input/*.xml
#   output: ~/projects/.../_input/_parsed.md

# Then the 14 extractors in order (for the recommended order: METADATA_INPUT_GUIDE.md Section 3)
# Each produces RD<NN>_draft.md
```

### 4.4 Step 4 — Gate 3 HUMAN REVIEW

Human guide: `02_PROJECT_TYPES/RETROFIT/RETROFIT_EXTRACT_<TOPIC>.md`

- Review the AI draft
- Fill in the `#UNKNOWNS` section
- Naming + cross-reference check
- **Safety (RD05):** Certified engineer approval

### 4.5 Step 5 — Gate 4 VALIDATION

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project ~/projects/KundeXYZ_Forderlinie_A \
  --rd all \
  --cross-ref \
  --strict
```

Gate 5 is not entered until all errors are fixed.

### 4.6 Step 6 — Gate 5 CODE GENERATION (AI-intensive)

For each RD, the relevant code_gen prompt is run.

### 4.7 Step 7 — Gate 6 SIMULATION + Gate 7 FAT/SAT

(skeleton in v3.0.0-alpha; to be detailed in v3.2.0+)

---

## 5. Common Scenarios

### 5.1 "The customer Excel is in a different format"
→ `08_METADATA_INPUT/METADATA_INPUT_GUIDE.md` Section 6 (column mapping YAML)

### 5.2 "Which prompt should I give the AI?"
→ `04_AI_PROMPTS/_PROMPT_HIERARCHY.md` (pipeline gate + role + RD mapping)

### 5.3 "How is a safety function recorded?"
→ `02_PROJECT_TYPES/RETROFIT/RETROFIT_EXTRACT_<...>.md` (none — Phase 4 covered a limited set of RDs)
→ For now: `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_SAFETY_FROM_CODE.md` (AI limited; human guide in v3.1.0)

### 5.4 "I need to change an existing spec"
→ Spec → schema → template → prompt are updated **simultaneously**
→ `GLOBAL_METADATA_SCHEMA.md` Section 7 (extension steps)

### 5.5 "A new AI model is out"
```bash
python 05_SCRIPTS/script_prompt_amend.py \
  --action add-target-ai \
  --model "Claude Sonnet 5+" \
  --dry-run  # check first
```

### 5.6 "Translate all system files to English (v4.0.0)"
```bash
python 05_SCRIPTS/script_prompt_amend.py \
  --action prepare-translation \
  --source-lang TR --target-lang EN \
  --output /tmp/translation_input.txt
# Then: feed it as input to a cheap AI model (Haiku 4+)
```

---

## 6. Critical Disciplines (NEVER Skip These)

### 6.1 Data Classification
Specify at the start of every project:
- 🟢 PUBLIC: pattern example (the factory itself)
- 🟡 INTERNAL: in-company (Cursor enterprise OK)
- 🟠 **CONFIDENTIAL**: customer code (self-hosted AI MANDATORY)
- 🔴 RESTRICTED: ITAR/EAR (special rules)

### 6.2 Safety (RD05)
- The AI **NEVER** estimates SIL/PLr
- All RD05 outputs are `DRAFT_UNVERIFIED`
- Does not go to production without certified safety engineer approval
- If safety logic is detected on a standard PLC, it is a CRITICAL finding

### 6.3 #UNKNOWNS Discipline
The `#UNKNOWNS` section in the AI output can NEVER be skipped. Every uncertainty is addressed by a human.

### 6.4 Cross-Reference
The RDs are linked to each other via LinkedTag/LinkedStep/LinkedFB. Verified with `script_consistency_check.py --cross-ref`.

### 6.5 Naming Standard
`^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$` — all tags. ParamName prefix (`in_/out_/inout_/stat_/temp_`) for FB variables.

### 6.6 Git Discipline
- At the end of every session, CHANGELOG + PROGRESS_TRACKER are updated
- Commit message: `feat(v3.0.0-alpha): session N - <summary>`
- Push manually (user's decision), no branches (on main)

---

## 7. Reminders (Notes to Self)

- System files were translated to English in 2026-05 (kept Turkish through v3.0.0 for fast development)
- The English migration was completed in 2026-05 (originally planned for the v4.0.0 public release)
- The 8-FACTORY proposal was REJECTED (archived internally)
- The 12-Point → 14-Point Pack was expanded (RD13 Annotation + RD14 Modernization added)
- Per-project XLSX files are generated with `script_md_to_xlsx.py` (MD is the source of truth)
- No branches, directly to main; pushing is done manually

---

## 8. Post-v3.0.0-alpha Roadmap

| Version | Goal |
|---------|------|
| v3.0.0-beta | requirements.txt + CI/CD + script test coverage |
| v3.0.0 | Pilot project (end-to-end test with a real customer) |
| v3.1.0 | Remaining retrofit/greenfield guides for 9 RDs (RD03/05/06/09/10/11/13) |
| v3.1.0 | KB filling (PITFALLS_RETROFIT_IO, SAFETY, etc.) |
| v3.2.0 | code_gen/motion/, code_gen/comm/, sim/ |
| v3.3.0 | Filling domain files (HMI_STANDARD, SAFETY_CONFIG, ...) |
| v4.0.0 | GitHub public release (English system translation — done 2026-05) |

---

## 9. Related Files

- **Pipeline:** `PIPELINE_CODE_REWRITE.md`
- **Factory Maestro:** `FACTORY_MAESTRO.md`
- **Sprint tracking:** `PROGRESS_TRACKER.md`
- **Build log:** `_BUILD_LOG.md`
- **Idea pool:** `FACTORY_IDEAS_BACKLOG.md`
- **Version:** `CHANGELOG.md`

---

## 10. Philosophy Note

> "AI accelerates, the engineer decides, the customer signs."

The factory's entire design rests on this three-way balance:
- **AI** does most of the routine work (extraction, code gen) but is not the decision-maker
- **The engineer** checks at every gate, revises the AI output, makes the critical decisions
- **The customer** signs at SAT, and gives staged approval before that (workshop, FAT, certification)

This philosophy is critical **especially for safety** (RD05): the AI does not estimate SIL, it only detects; the engineer determines SIL; the customer/TÜV approves.

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0: For you. This file is the map of how to use the factory. Every new feature should be reflected here.*
