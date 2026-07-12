---
title: Global Metadata Schema
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-15
applies_to: [factory_internal]
prerequisite: [GLOBAL_NAMING_STANDARD.md]
status: ACTIVE
---

# GLOBAL_METADATA_SCHEMA.md — Global Metadata Schema

> **Purpose:** Ensure consistent data structure across all projects. Manager for JSON validation schemas for the 14-Point Raw Data Pack.

---

## 1. General Structure

The Factory metadata system has 3 layers:

```
[Customer Input (Excel/PDF/PLC code)]
       ↓ extraction
[Per-RD JSON file]
       ↓ schema validation (08_METADATA_INPUT/schema/)
[Approved RD (after Gate 4)]
       ↓ code generation
[SCL/HMI/Test outputs]
```

---

## 2. 14-Point Raw Data Pack Schema Map

| RD | Spec | JSON Schema | Per-Project Template |
|----|------|-------------|----------------------|
| RD01 | MDSCHEMA_RAWDATA_01_IO.md | rd01_io.schema.json | RD01_IO_List.md |
| RD02 | MDSCHEMA_RAWDATA_02_DATADICT.md | rd02_datadict.schema.json | RD02_DataDict.md |
| RD03 | MDSCHEMA_RAWDATA_03_FLOWCHART.md | rd03_flowchart.schema.json | RD03_Flowchart.md |
| RD04 | MDSCHEMA_RAWDATA_04_MODE.md | rd04_mode.schema.json | RD04_Mode.md |
| RD05 | MDSCHEMA_RAWDATA_05_SAFETY.md | rd05_safety.schema.json | RD05_Safety_DRAFT_UNVERIFIED.md |
| RD06 | MDSCHEMA_RAWDATA_06_MOTION.md | rd06_motion.schema.json | RD06_Motion.md |
| RD07 | MDSCHEMA_RAWDATA_07_TIMING.md | rd07_timing.schema.json | RD07_Timing.md |
| RD08 | MDSCHEMA_RAWDATA_08_ALARM.md | rd08_alarm.schema.json | RD08_Alarm.md |
| RD09 | MDSCHEMA_RAWDATA_09_COMMS.md | rd09_comms.schema.json | RD09_Comms.md |
| RD10 | MDSCHEMA_RAWDATA_10_FBSPEC.md | rd10_fbspec.schema.json | RD10_FBSpec.md |
| RD11 | MDSCHEMA_RAWDATA_11_HMI.md | rd11_hmi.schema.json | RD11_HMI.md |
| RD12 | MDSCHEMA_RAWDATA_12_USECASE.md | rd12_usecase.schema.json | RD12_UseCase.md |
| RD13 | MDSCHEMA_RAWDATA_13_ANNOTATION.md | rd13_annotation.schema.json | RD13_Annotation.md |
| RD14 | MDSCHEMA_RAWDATA_14_MODERNIZATION.md | rd14_modernization.schema.json | RD14_Modernization.md |

---

## 3. Common Schema Structure

All RD JSON files start with this basic frontmatter:

```json
{
  "project_id": "AUTO-2026-001",          // unique project ID
  "project_name": "Customer XYZ Conv.",
  "customer": "Customer XYZ GmbH",
  "filled_by": "Eng. Müller",
  "filled_at": "2026-05-15",
  "output_language": "DE",                // TR/EN/DE
  "status": "DRAFT|REVIEWED|APPROVED",
  "data_classification": "CONFIDENTIAL",
  "<RD-specific payload>": { ... }
}
```

---

## 4. Conditional Rule Template

All schemas use the `allOf` + `if/then` pattern:

```json
{
  "allOf": [
    {
      "if": {
        "properties": { "<field>": { "<condition>": "<value>" } }
      },
      "then": {
        "required": ["<dependent_field>"],
        "properties": {
          "<dependent_field>": { "<constraint>": "<value>" }
        }
      }
    }
  ]
}
```

**Common conditional rules:**

| Category | Rule |
|----------|-------|
| RD01 IO | Direction=AI/AO → EngUnit, RangeMin, RangeMax required |
| RD02 DataDict | Scope=MemoryMarker/TempVar → Retain=N/A |
| RD03 Flowchart | StepType=Initial → EntryCondition=TRUE |
| RD04 Mode | ModeID=M00 → Priority=0 |
| RD05 Safety | Status=APPROVED → Verified_By, SIL_Level, Category required |
| RD07 Timing | IsWatchdog=Y → LinkedAlarm required |
| RD08 Alarm | Class=Critical → AcknRequired=Y |
| RD09 Comms | Ethernet protocol → RemoteIP IPv4 required |
| RD10 FBSpec | BlockType=FB → InstanceDB required |
| RD11 HMI | ElementType=NumericInput → MinValue, MaxValue required |
| RD13 Annotation | WarningFlag≠N → WarningDetail required |
| RD14 Modernization | Category=SAFETY → VerificationRequired≠NONE |

---

## 5. Running Validation

```bash
# Validate single RD
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project /path/to/project \
  --rd 01

# Validate all RD's sequentially
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project /path/to/project \
  --rd all

# Strict mode (warnings treated as errors)
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project /path/to/project \
  --strict
```

---

## 6. Error Category Mapping

All specs use 3 categories (in `MDSCHEMA_RAWDATA_*.md` Section 6):

| Code | Category | Detection | Solution |
|-----|----------|--------|-------|
| `Axx-yyy` | A — Syntax | JSON parser / regex | Auto-fix |
| `Bxx-yyy` | B — Schema/Standard | jsonschema validator | Fix per validator output |
| `Cxx-yyy` | C — Semantic | Manual review | Human judgment |

---

## 7. Schema Extension

When adding a new RD (future v3.1.0+):

1. Write `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_<NN>.md` spec
2. Derive `08_METADATA_INPUT/schema/rd<NN>_*.schema.json` JSON schema
3. Write `07_PROJECT_TEMPLATE/metadata_template/RD<NN>_*.md` template
4. Write `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_<TOPIC>_FROM_CODE.md` extractor
5. Add human guide in `02_PROJECT_TYPES/` (RETROFIT + GREENFIELD)
6. Introduce new RD to `script_consistency_check.py`
7. Add row to this file (Sections 2 and 4)

---

## 8. Versioning Discipline

- Spec change → schema, template, prompt **updated simultaneously**
- Backward-compatible change → minor bump (1.0.0 → 1.1.0)
- BREAKING change → major bump + migration guide
- All changes reflected in `CHANGELOG.md`

---

## 9. Related Files

- **Specs:** `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_*.md`
- **Schemas:** `08_METADATA_INPUT/schema/rd*.schema.json`
- **Templates:** `07_PROJECT_TEMPLATE/metadata_template/RD*.md`
- **Validator:** `05_SCRIPTS/dev/script_consistency_check.py`
- **Naming:** `GLOBAL_NAMING_STANDARD.md`
- **Input guide:** `08_METADATA_INPUT/METADATA_INPUT_GUIDE.md`

---

*v1.0.0 — 14-Point Raw Data Pack global schema discipline. Spec-schema-template-prompt quad always in sync.*
