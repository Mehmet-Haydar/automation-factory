---
title: 08_METADATA_INPUT — Folder README
version: 1.1.0
last_updated: 2026-05-23
status: ACTIVE
last_validated: 2026-05
---

# `08_METADATA_INPUT/` — Customer Input Schemas + Validation

> **This folder defines how customer-sourced data (XLSX/JSON) is taken in and validated by the factory.** JSON schema files + input guide.

---

## 1. Contents

```
08_METADATA_INPUT/
├── _README.md  ← this file
├── METADATA_INPUT_GUIDE.md  ← Input guide for the engineer
│
└── schema/                  ← JSON validation schemas (14 files)
    ├── rd01_io.schema.json
    ├── rd02_datadict.schema.json
    ├── rd03_flowchart.schema.json
    ├── rd04_mode.schema.json
    ├── rd05_safety.schema.json
    ├── rd06_motion.schema.json
    ├── rd07_timing.schema.json
    ├── rd08_alarm.schema.json
    ├── rd09_comms.schema.json
    ├── rd10_fbspec.schema.json
    ├── rd11_hmi.schema.json
    ├── rd12_usecase.schema.json
    ├── rd13_annotation.schema.json
    └── rd14_modernization.schema.json
```

---

## 2. Input Channels

### 2.1 Excel from the Customer
```
[Customer Excel]
       ↓ script_excel_to_metadata.py
[JSON metadata]
       ↓ script_consistency_check.py --schema rd01..rd14
[Validation report]
       ↓
[If OK → passes Gate 4, if error → fix]
```

### 2.2 From the Factory Template
```
[07_PROJECT_TEMPLATE/metadata_template/RD<NN>.md] (empty template)
       ↓ Engineer or AI fills it in
[RD<NN>.md (filled in)]
       ↓ script_md_to_xlsx.py (optional — to give the customer an XLSX)
[RD<NN>.xlsx]
       ↓ script_excel_to_metadata.py reverse
[RD<NN>.json]
       ↓ JSON schema validation
[OK]
```

---

## 3. JSON Schema Features

All schemas use the **draft-07** standard. Common features:

| Feature | Example |
|---------|---------|
| **Pattern** | Regex enforcement (Tag, AlarmID, etc.) |
| **Enum** | Limited value sets (Class, ScreenType, etc.) |
| **Conditional (allOf/if/then)** | Critical → AcknRequired=Y |
| **Required** | Minimal fields |
| **Min/Max** | Length, value bounds |

### 3.1 Critical Conditional Examples

```json
// RD01: Analog → Engineering unit mandatory
"if": { "properties": { "Direction": { "enum": ["AI", "AO"] } } },
"then": { "required": ["EngUnit", "RangeMin", "RangeMax"] }

// RD08: Critical alarm → ACK mandatory
"if": { "properties": { "Class": { "const": "Critical" } } },
"then": { "properties": { "AcknRequired": { "const": "Y" } } }

// RD14: SAFETY category → Verification mandatory
"if": { "properties": { "Category": { "const": "SAFETY" } } },
"then": { "properties": { "VerificationRequired": { "not": { "const": "NONE" } } } }
```

---

## 4. Validation Output

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project /path/to/customer-project \
  --schema 08_METADATA_INPUT/schema/rd01_io.schema.json \
  --input /path/to/customer-project/RD01_IO.json
```

Typical output:
```
[OK] RD01_IO.json: 47 signals, 0 errors
[WARN] Row 12: NormalState missing (DI signal)
[ERR] Row 23: Tag format violation — "Motor1" (regex: ^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$)
[ERR] Row 30: AI signal but EngUnit empty (conditional rule)
```

---

## 5. Error Taxonomy

| Category | Type | Action |
|----------|------|--------|
| `[ERR]` | Spec violation | Must be fixed (cannot pass Gate 4) |
| `[WARN]` | Best-practice violation | Should be reviewed |
| `[INFO]` | Information | Log only |

---

## 6. METADATA_INPUT_GUIDE.md

Detailed guide for the human engineer:
- Excel fill-in steps
- Typical errors and solutions
- Hybrid filling strategy with AI
- Data exchange protocol with the customer

---

## 7. Related Folders

- `01_GLOBAL_STANDARDS/md_schemas/` — Spec files (source of the JSON schemas)
- `07_PROJECT_TEMPLATE/metadata_template/` — MD templates to be filled in
- `05_SCRIPTS/dev/script_consistency_check.py` — The validator for this folder
- `05_SCRIPTS/dev/script_excel_to_metadata.py` — Excel ↔ JSON conversion

---

*Input error = output disaster. This folder is the guardian of output cleanliness.*
