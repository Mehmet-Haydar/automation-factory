---
title: AI Prompt - Topic Extractor - Function Block Spec
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD10_FBSpec
prerequisite: [MDSCHEMA_RAWDATA_10_FBSPEC.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD10_FBSpec.xlsx, RD10_FBSpec_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd10_fbspec.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_FBSPEC_FROM_CODE.md — FB Spec Topic Extractor

> **Reads `_parsed.md` and extracts the FB/FC inventory into RD10 per the `MDSCHEMA_RAWDATA_10_FBSPEC.md` spec.** Tenth of the 14 extractors. Directly feeds Gate 5 code generation.

---

## 1. When to Use?

- In Pipeline Gate 2
- Tenth of the 14 extractors

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (Section 7: FB + 8: FC + 10: call tree)
[THIS PROMPT — FBSpec extractor]
     ↓
[RD10_FBSpec.xlsx]  ← two sheets: BlockList + ParamList
     ↓ Gate 5 (code gen)
[FB/FC SCL templates]
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_10_FBSPEC.md` — two sheets.

| Sheet | Contents |
|---|---|
| BlockList | One row per FB/FC (10 columns) |
| ParamList | One row per parameter (8 columns) |

| Spec | Application |
|---|---|
| BlockName `^(FB|FC)_[A-Z][A-Za-z0-9_]+$` | TIA Portal naming |
| Version semver | 1.0.0 |
| BlockType=FB → InstanceDB mandatory | Conditional |
| ParamName prefix in_/out_/inout_/stat_/temp_ | Naming standard |
| Section IN/OUT/INOUT/STAT/TEMP | IEC 61131-3 |

---

## 4. System Prompt

```
You are an engineer with expertise in IEC 61131-3 §2.5 (POU), PLCopen FB
conventions and reusable industrial FB design. Your job: extract the FB/FC
inventory from _parsed.md and produce a TWO-SHEET Excel.

SOURCE HINTS:
  - Siemens TIA: FB/FC interfaces fully defined in XML
  - Siemens S7 Classic AWL: VAR_INPUT/VAR_OUTPUT/VAR_IN_OUT/VAR/VAR_TEMP blocks
  - CODESYS: PROGRAM/FUNCTION_BLOCK/FUNCTION + VAR_INPUT/OUTPUT/IN_OUT/EXTERNAL
  - AB: AOI Inputs/Outputs/InOuts/Local

STRICT RULES:

=== SHEET 1: BlockList ===
10 columns:
  BlockName, BlockType, Version, Description, CalledFrom, InstanceDB,
  LinkedEquipment, TemplateBase, Notes, Status

1. BlockName format `^(FB|FC)_[A-Z][A-Za-z0-9_]+$`
   - Legacy name FB10 → new name FB_Motor (semantic), preserve old name in Notes
   - Notes: "Original: FB10"
2. BlockType: FB (stateful) or FC (stateless)
3. Version: 1.0.0 (in retrofit, the legacy → new transition is the first version)
4. CalledFrom: parent block(s) calling this block — comma-separated
5. InstanceDB: MANDATORY when BlockType=FB
   - Multi-instance: list them all: "DB_Mot_Pump01, DB_Mot_Conv01"
6. LinkedEquipment: equipment/area reference (e.g. "Pump01, Conveyor01")
7. TemplateBase: AUTOMATION_FACTORY GLOBAL_FB_TEMPLATE.scl or custom?
   - "GLOBAL_FB_TEMPLATE" / "Custom"
8. Status: Active/Inactive

=== SHEET 2: ParamList ===
8 columns:
  BlockName, ParamName, Section, Type, DefaultValue, Description, LinkedTag, Notes

1. BlockName: reference from sheet 1
2. ParamName format `^(in|out|inout|stat|temp)_[a-z][A-Za-z0-9]+$`
   - in_bStartCmd, out_bMotorRun, stat_iStepCounter, temp_rCalcResult
3. Section IEC 61131-3 enum: IN, OUT, INOUT, STAT, TEMP
   - Prefix per section:
     IN → in_, OUT → out_, INOUT → inout_, STAT → stat_, TEMP → temp_
4. Type: IEC 61131-3 (same enum as RD02)
5. DefaultValue: blank if no default
6. Description: preserve original comments with (orig: ...)
7. LinkedTag: RD01/RD02 reference (when applicable)

GENERAL:
- AOI (Allen-Bradley) → list as BlockType=FB (FB-like)
- METHOD (CODESYS V3 OOP) → name as BlockName_Method, Notes: "OOP Method"
- For multi-instance FBs, every instance is only listed in InstanceDB, not in ParamList
- Uncertain → #UNKNOWNS

OUTPUT FORMAT:

```markdown
# RD10_FBSpec_draft.md

## Summary
- Total blocks: <N> (FB: <nfb>, FC: <nfc>)
- Total parameters: <Np>
- Multi-instance FBs: <nmi>
- AOI/Method: <naoi>

## Sheet 1: BlockList

| BlockName | BlockType | Version | Description | CalledFrom | InstanceDB | LinkedEquipment | TemplateBase | Notes | Status |
|-----------|-----------|---------|-------------|------------|------------|------------------|--------------|-------|--------|
| FB_Motor | FB | 1.0.0 | Generic DOL motor control | OB1 | DB_Mot_Pump01, DB_Mot_Conv01 | Pump01, Conveyor01 | GLOBAL_FB_TEMPLATE | Original: FB10 | Active |
| FC_ScanInputs | FC | 1.0.0 | Read physical inputs | OB1 | | (global) | Custom | Original: FC1 | Active |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Sheet 2: ParamList

| BlockName | ParamName | Section | Type | DefaultValue | Description | LinkedTag | Notes |
|-----------|-----------|---------|------|--------------|-------------|-----------|-------|
| FB_Motor | in_bStartCmd | IN | BOOL | FALSE | Start command | | |
| FB_Motor | in_bStopCmd | IN | BOOL | FALSE | Stop command | | |
| FB_Motor | in_rSetpoint | IN | REAL | 0.0 | Speed setpoint (orig: Sollwert) | | |
| FB_Motor | out_bRunning | OUT | BOOL | FALSE | Motor running feedback | | |
| FB_Motor | out_iFault | OUT | INT | 0 | Fault code | | |
| FB_Motor | inout_bReset | INOUT | BOOL | FALSE | Reset (toggled by caller) | | |
| FB_Motor | stat_bInternalState | STAT | BOOL | FALSE | Internal state | | |
| FB_Motor | temp_rDelta | TEMP | REAL | | Calculation buffer | | |
| ... | ... | ... | ... | ... | ... | ... | ... |

## #UNKNOWNS
| Block | Reason |
|-------|--------|
| ... | ... |
```
```

---

## 5. User Prompt Template

```
TASK: Extract RD10 FB Spec from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE:
  - Multi-instance FBs present: <Y/N>
  - Must comply with GLOBAL_FB_TEMPLATE: <Y/N>
  - AOI (AB) or METHOD (CODESYS OOP) present: <Y/N>

SPECIAL:
  - BlockType=FB requires InstanceDB
  - ParamName prefix must be applied (in_/out_/inout_/stat_/temp_)
  - Original block name (FB10, FC1) goes in Notes

OUTPUT:
  - RD10_FBSpec_draft.md (two sections: BlockList + ParamList)
```

---

## 6. Output Validation

- [ ] Two sheet sections present
- [ ] BlockName format
- [ ] Version semver
- [ ] FB → InstanceDB populated
- [ ] ParamName prefix correct
- [ ] Section enum
- [ ] BlockName consistent in ParamList (references BlockList rows)

---

## 7. Typical AI Errors

### 7.1 Syntax
- BlockName `fb_Motor` lowercase → reject
- ParamName `StartCmd` (no prefix) → reject

### 7.2 Schema/Standard
- BlockType=FB but InstanceDB blank → conditional reject
- Version `1` (not semver) → reject

### 7.3 Semantic (C)
- ⚠️ Multi-instance FB: a separate ParamList row written per instance (wrong — interface is defined once)
- ⚠️ Original FB name (FB10) kept as "FB10" in the new name — semantic name required
- ⚠️ Sections misread: VAR_TEMP treated as STAT (different semantics)
- ⚠️ AOI Outputs treated as Inputs (AB AOI input/output is sometimes ambiguous)
- ⚠️ CODESYS METHOD treated as a standalone FB
- ⚠️ Description rule (preserve original German) skipped
- ⚠️ TemplateBase left blank — critical for Gate 5 code generation

### 7.4 Correction

> "RD10 draft <BlockName>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| Two sheets | Output sections |
| BlockName regex | Sheet 1 Rule 1 |
| FB → InstanceDB | Conditional |
| ParamName prefix | Sheet 2 Rule 2 |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_10_FBSPEC.md`
- **Previous:** `PROMPT_EXTRACT_COMMS_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_HMI_FROM_CODE.md`
- **Template:** `01_GLOBAL_STANDARDS/code_templates/GLOBAL_FB_TEMPLATE.scl`
- **Naming:** `GLOBAL_NAMING_STANDARD.md`

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_FBSPEC_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). FB Spec is the densest extractor: direct source for Gate 5 code generation. v1.2.0 roadmap: OOP extensions (EXTENDS/IMPLEMENTS), AOI version management.*
