---
title: 01_GLOBAL_STANDARDS — Folder README
version: 1.1.0
last_updated: 2026-05-23
status: ACTIVE
last_validated: 2026-05
---

# `01_GLOBAL_STANDARDS/` — Industry Standards + Factory Rules

> **This folder contains the factory's "laws".** All projects comply with these rules. Naming, language policy, data classification, MD schemas, multilingual glossary, code templates are here.

---

## 1. Subdirectories

```
01_GLOBAL_STANDARDS/
├── _README.md  ← this file
│
├── rules/                ← Factory core rules
│   ├── GLOBAL_NAMING_STANDARD.md
│   ├── GLOBAL_DATA_CLASSIFICATION.md
│   ├── GLOBAL_LANG_POLICY.md
│   ├── GLOBAL_AI_INTERFACE.md
│   ├── GLOBAL_GIT_DISCIPLINE.md
│   ├── GLOBAL_METADATA_SCHEMA.md
│   └── GLOBAL_PLATFORM_MATRIX.md
│
├── md_schemas/           ← 14-Point Raw Data Pack specifications
│   ├── MDSCHEMA_RAWDATA_01_IO.md
│   ├── MDSCHEMA_RAWDATA_02_DATADICT.md
│   ├── ...
│   └── MDSCHEMA_RAWDATA_14_MODERNIZATION.md
│
├── lang_glossary/        ← Multilingual terminology
│   ├── GLOSSARY_BASE.md
│   ├── GLOSSARY_EN.md
│   ├── GLOSSARY_TR.md
│   └── GLOSSARY_DE.md
│
├── code_templates/       ← Industrial SCL templates
│   ├── GLOBAL_FB_TEMPLATE.scl
│   └── ...
│
└── templates/            ← Other factory templates
    └── GLOBAL_PROJECT_STATE_TEMPLATE.md
```

---

## 2. Usage Flow

| Who | What for |
|-----|----------|
| **Engineer** | Naming + data classification + language policy guide |
| **AI prompts** | Reference via `prerequisite:` frontmatter |
| **Validator scripts** | Schema, naming, classification checks |
| **Customer** | Standards compliance proof (CE/TÜV documentation) |

---

## 3. Critical Files

### 3.1 `rules/GLOBAL_NAMING_STANDARD.md`
All tag, block, and variable naming. Format: `^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$`

### 3.2 `rules/GLOBAL_DATA_CLASSIFICATION.md`
4 levels: 🟢 PUBLIC / 🟡 INTERNAL / 🟠 CONFIDENTIAL / 🔴 RESTRICTED
Customer code is mostly 🟠 — public AI prohibited.

### 3.3 `rules/GLOBAL_LANG_POLICY.md`
3-layer: system (EN, since 2026-05) / interface (EN) / code output (per-project TR/EN/DE)

### 3.4 `md_schemas/MDSCHEMA_RAWDATA_*.md`
14-Point Raw Data Pack. Each RD is separate spec. JSON schema + AI filling instructions + error taxonomy.

### 3.5 `lang_glossary/GLOSSARY_*.md`
Canonical concept_id system. AI translation consistency backbone. Alarm + HMI multi-lang text reference.

---

## 4. Versioning

- Each rule/spec file has independent semver
- BREAKING change → affects all projects, reflected in CHANGELOG
- New addition → backward-compatible, minor bump

---

## 5. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/<file>" \
  --reason "..." \
  --suggestion "..."
```

---

## 6. Related Folders

- `02_PROJECT_TYPES/` — Retrofit/Greenfield guides apply these rules
- `04_AI_PROMPTS/` — All prompts reference these rules via `prerequisite`
- `07_PROJECT_TEMPLATE/metadata_template/` — Per-project templates applying these rules

---

*Foundation of the factory. Changes in this folder affect the entire system — handle with care.*
