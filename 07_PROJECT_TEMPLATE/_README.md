---
title: 07_PROJECT_TEMPLATE — Folder README
version: 1.1.0
last_updated: 2026-05-23
status: ACTIVE
---

# `07_PROJECT_TEMPLATE/` — New Project Template

> **This folder is copied as a new project skeleton.** `script_project_init.py` copies this folder to the target project directory and fills in the placeholders.

---

## 1. Contents

```
07_PROJECT_TEMPLATE/
├── _README.md  ← this file
│
├── README.md                       ← Project README (placeholder)
├── PROJECT_MAESTRO_TEMPLATE.md     ← Project maestro/orchestrator template
├── PROJECT_STATE_TEMPLATE.json     ← Project state JSON template
│
└── metadata_template/              ← 14-Point Raw Data Pack templates
    ├── RD01_IO_List.md
    ├── RD02_DataDict.md
    ├── RD03_Flowchart.md
    ├── RD04_Mode.md
    ├── RD05_Safety_DRAFT_UNVERIFIED.md
    ├── RD06_Motion.md
    ├── RD07_Timing.md
    ├── RD08_Alarm.md
    ├── RD09_Comms.md
    ├── RD10_FBSpec.md
    ├── RD11_HMI.md
    ├── RD12_UseCase.md
    ├── RD13_Annotation.md
    └── RD14_Modernization.md
```

---

## 2. Starting a New Project

```bash
python 05_SCRIPTS/script_project_init.py \
  --type <retrofit|greenfield> \
  --customer "<customer name>" \
  --name "<project name>" \
  --output-lang <TR|EN|DE> \
  --target /path/to/projects/
```

What the script does:
1. Copies the contents of `07_PROJECT_TEMPLATE/` to the target
2. Replaces placeholders (e.g. project code → real value)
3. Generates `PROJECT_STATE.json` (including output_language)
4. Copies the maestro file (RETROFIT/GREENFIELD MAESTRO depending on project type)
5. Makes the first commit (`feat: project <name> initialized`)

---

## 3. 14-Point Pack Templates

Each RD file:
- **Frontmatter** with project meta (project_id, filled_by, output_language, etc.)
- **Spec reference** (`MDSCHEMA_RAWDATA_<NN>.md`)
- **JSON schema reference** (`08_METADATA_INPUT/schema/rd<NN>_*.schema.json`)
- **Example rows** (template data you will delete)
- **Fill-in notes** (summary of critical rules)
- **#UNKNOWNS section** (for human review)

XLSX equivalent: generated automatically from MD with `script_md_to_xlsx.py`.

---

## 4. PROJECT_STATE.json

Per-project state file. Contents:

```json
{
  "project_id": "AUTO-2026-001",
  "project_name": "Customer XYZ Conveyor Line",
  "customer": "Customer XYZ",
  "project_type": "retrofit",
  "output_language": "DE",
  "current_gate": 2,
  "gates_status": {
    "gate1_kesif": "completed",
    "gate2_cikartim": "in_progress",
    "gate3_review": "pending",
    "gate4_validation": "pending",
    "gate5_kod_uretimi": "pending",
    "gate6_simulasyon": "pending",
    "gate7_fat_sat": "pending"
  },
  "rd_status": {
    "RD01_IO": "approved",
    "RD02_DataDict": "draft",
    "...": "..."
  },
  "data_classification": "CONFIDENTIAL",
  "safety_engineer": "Eng. Müller (cert. TÜV)"
}
```

> Note: the `gates_status` keys (`gate1_kesif`, `gate2_cikartim`, `gate5_kod_uretimi`, `gate6_simulasyon`) are the literal JSON keys used by the tooling and are kept as-is.

---

## 5. Maestro Template

`PROJECT_MAESTRO_TEMPLATE.md` is the orchestrator document for each project:
- Customer meta
- Factory references (rule + schema files)
- Data classification
- Project-specific decisions
- Gate progress table

---

## 6. Related Folders

- `01_GLOBAL_STANDARDS/md_schemas/` — Template target specs
- `08_METADATA_INPUT/schema/` — JSON validation
- `05_SCRIPTS/script_project_init.py` — The script that uses this folder
- `05_SCRIPTS/dev/script_md_to_xlsx.py` — Template MD → XLSX conversion

---

*The starting point of a new project. Each file is the physical representation of a project rule.*
