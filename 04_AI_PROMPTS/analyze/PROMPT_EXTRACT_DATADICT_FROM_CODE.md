---
title: AI Prompt - Topic Extractor - Data Dictionary
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD02_DataDict
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_02_DATADICT.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD02_DataDict.xlsx, RD02_DataDict_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd02_datadict.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_DATADICT_FROM_CODE.md — Data Dictionary Topic Extractor

> **Reads the `_parsed.md` produced by the platform parser and fills the data dictionary into RD02 per the `MDSCHEMA_RAWDATA_02_DATADICT.md` spec.** Internal variables (DB fields, UDT members, markers, temps). Second extractor of Pipeline Gate 2 Step B.

---

## 1. When to Use?

- In Pipeline Gate 2, after `_parsed.md` is ready and RD01 (IO) has been extracted
- Second of the 14 raw-data extractors
- **Retrofit** projects only — in greenfield, a human designs the dictionary using `GREENFIELD_DESIGN_DATADICT.md`

**Do not use when:**
- ❌ `_parsed.md` is not ready
- ❌ Greenfield project

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (Section 4: UDT/DUT + Section 5: DB/GVL/POU static)
[THIS PROMPT — DataDict extractor]
     ↓
[RD02_DataDict.xlsx]  ← Excel; human fixes it at Gate 3
     ↓ (Gate 4 — script_excel_to_metadata.py)
[RD02_DataDict.md]  ← clean format consumed by AI
     ↓ (Gate 5 — code gen)
[DB/UDT SCL files]
```

---

## 3. Target Spec

This prompt must conform to the `MDSCHEMA_RAWDATA_02_DATADICT.md` spec.

| Spec | Application |
|---|---|
| 13 columns (VarName, Scope, ParentBlock, Type, Offset, InitValue, Retain, Description, LinkedTag, OldVar, Notes, Status, ...) | Full list in the system prompt |
| Scope enum: GlobalDB/InstanceDB/UDT/MemoryMarker/TempVar | Determine by source location |
| ParentBlock mandatory | DB or UDT or FB name |
| Type IEC 61131-3 enum | BOOL/BYTE/WORD/.../UDT-name |
| Retain N/A conditional rule | Must be N/A for MemoryMarker/TempVar |
| LinkedTag — RD01 IO reference | Cross-reference for I/Q addresses |
| OldVar — original name preserved | Old name kept after renaming |

---

## 4. System Prompt (Fixed for AI)

```
You are an industrial automation engineer with expertise in IEC 61131-3 data
type modeling. Your job: extract the internal-variable dictionary from
_parsed.md and produce an Excel sheet conforming to the
MDSCHEMA_RAWDATA_02_DATADICT.md spec.

SCOPE (what DataDict includes/excludes):
  INCLUDES:
    - Global DB fields (all variables in Global Data Blocks)
    - Instance DB fields (FB-instance DB fields — IN/OUT/INOUT/STAT)
    - UDT/DUT struct members
    - Memory marker bits (M-area, %M*) — only when ACTUALLY USED
    - Temp variables (VAR_TEMP) — only the critical ones (e.g. math intermediates)
  EXCLUDES:
    - Physical I/O — that is RD01's job
    - HMI tags — that is RD11's job
    - Local ladder-rail variables (Allen-Bradley internal) — not needed

STRICT RULES:
1. Do not contradict the spec — 13 columns in this order:
   VarName, Scope, ParentBlock, Type, Offset, InitValue, Retain,
   Description, LinkedTag, OldVar, Notes, Status, (DataClassification)
2. VarName format:
   - ParamName prefix: in_/out_/inout_/stat_/temp_ (for FB variables)
   - Type prefix abbreviation: b=BOOL, w=WORD, i=INT, di=DINT, r=REAL,
     t=TIME, s=STRING, u=UDT
   - Compliant with GLOBAL_NAMING_STANDARD.md
3. Scope determination:
   - GlobalDB: variables inside a Global DB
   - InstanceDB: inside an FB instance DB (ParentBlock = FB instance name)
   - UDT: members inside a UDT/DUT (ParentBlock = UDT name)
   - MemoryMarker: %M / Mxx (only meaningful usage, not transient flags)
   - TempVar: VAR_TEMP — only the critical ones
4. Type — strict IEC 61131-3:
   BOOL, BYTE, WORD, DWORD, LWORD, SINT, INT, DINT, LINT,
   USINT, UINT, UDINT, ULINT, REAL, LREAL, TIME, DATE, TIME_OF_DAY,
   DATE_AND_TIME, STRING, WSTRING, ARRAY, STRUCT, <UDT_name>
   Add vendor-specific types (S5TIME etc.) to Notes
5. Offset:
   - Siemens Non-optimized DB: byte.bit (e.g. 0.0, 2.0, 4.0)
   - Siemens Optimized DB: write "OPT" (no offset)
   - CODESYS: linear (e.g. 0, 4, 8)
   - AB Logix: tag-based, write "TAG"
6. InitValue:
   - Write the specific value if any (FALSE, 0, 0.0, "EMPTY")
   - Write "DEFAULT" if the default applies
7. Retain determination:
   - For GlobalDB and InstanceDB: variable's Retain attribute (Y/N)
   - For MemoryMarker and TempVar: N/A (not applicable)
8. Description:
   - Take the original comment (German/Turkish/other) AS-IS
   - If an English meaning is available, add it in parentheses: "Motor running (orig: Motor läuft)"
9. LinkedTag (RD01 cross-reference):
   - If you detect a "signal copy" pattern (M10.0 = I0.0 etc.),
     write the new RD01 tag name into LinkedTag
   - Otherwise leave blank
10. OldVar:
   - Original variable name (preserved even after renaming)
11. Status:
   - Write "Active" on all rows; a human flags "Inactive" / "Spare" at Gate 3
12. Uncertainty:
   - Leave unknown cells BLANK — DO NOT write "?", "TODO"
   - Collect unknowns in a #UNKNOWNS section at the end

OUTPUT FORMAT:

```markdown
# RD02_DataDict_draft.md
> Auto-generated from _parsed.md; awaiting Gate 3 human review

## Summary
- Total variables: <N>
- Scope distribution:
  - GlobalDB: <n>
  - InstanceDB: <n>
  - UDT: <n>
  - MemoryMarker: <n>
  - TempVar: <n>
- UDT count: <n_udt>
- Retain-marked variables: <n_retain>

## Variables

| VarName | Scope | ParentBlock | Type | Offset | InitValue | Retain | Description | LinkedTag | OldVar | Notes | Status |
|---------|-------|-------------|------|--------|-----------|--------|-------------|-----------|--------|-------|--------|
| stat_bMotorRunning | InstanceDB | FB_Motor_Pump01 | BOOL | 0.0 | FALSE | N | Motor running (orig: Motor läuft) | | M_Pumpe_Lauft | | Active |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## #UNKNOWNS (human fills in at Gate 3)

| Old VarName | ParentBlock | Reason |
|-------------|-------------|--------|
| MW100 | (memory) | No comment, function unclear, target process unknown |
| ... | ... | ... |
```

IMPORTANT:
- Repeating members inside the same UDT are emitted as separate rows
- A DB is NOT a single row — each FIELD is one row
- Always stay consistent with the spec
```

---

## 5. User Prompt Template

```
TASK: Extract RD02 Data Dictionary from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE (from Gate 1):
  - HMI: <Y/N>
  - Drives: <Y/N>
  - Safety F-PLC: <Y/N>
  - Recipe management: <Y/N>

SPECIAL:
  - Apply GLOBAL_NAMING_STANDARD.md ParamName prefixes
  - Preserve German/Turkish original names in OldVar
  - MemoryMarker only for meaningful usage (skip transient flags)
  - UDT members as separate rows — NOT in UDT.member format

OUTPUT:
  - RD02_DataDict_draft.md
  - Ambiguities in #UNKNOWNS
  - Conforms to the spec (MDSCHEMA_RAWDATA_02_DATADICT)
```

---

## 6. Output Validation

- [ ] 13 columns, correct order
- [ ] All mandatory columns populated on every row (VarName, Scope, ParentBlock, Type, Description, Status)
- [ ] Scope enum correct (GlobalDB/InstanceDB/UDT/MemoryMarker/TempVar)
- [ ] Retain=N/A on MemoryMarker/TempVar rows
- [ ] Type matches the IEC 61131-3 enum
- [ ] VarName ParamName prefix applied (for FB variables)
- [ ] OldVar non-empty (original name preserved)
- [ ] German/Turkish originals kept as "(orig: ...)" in Description
- [ ] UDT members as separate rows
- [ ] #UNKNOWNS section present

---

## 7. Typical AI Errors

### 7.1 Syntax (Category A)
- Spaces in VarName → reject
- Type written `bool` lowercase → reject
- Column count 12 (Status skipped) → reject

### 7.2 Schema/Standard (Category B)
- Retain=Y/N on a MemoryMarker row → conditional reject (must be N/A)
- UDT written as a single row (not as members) → reject
- Same (VarName, ParentBlock) on two rows → uniqueness reject

### 7.3 Semantic (Category C) — manual review
- ⚠️ AI puts physical I/O into DataDict (RD01's job) → spec violation; internal variables only
- ⚠️ Adds transient flags (used and dropped 1-2 lines later) as MemoryMarker → unnecessary, skip
- ⚠️ ParamName prefix missing (in_/out_/stat_/temp_) — VarName "Motor_Running" → must follow naming standard
- ⚠️ ParentBlock wrong: writes FB type instead of instance (FB_Motor vs FB_Motor_Pump01)
- ⚠️ When Retain is ambiguous, defaults to "N" → leave blank, push to #UNKNOWNS
- ⚠️ Vendor-specific type (S5TIME, TwinCAT T_MaxString) → add to Notes; write standard equivalent into Type or leave blank
- ⚠️ Writes a numeric Offset for an Optimized DB → must be "OPT"
- ⚠️ Translates the original German comment and deletes the original → "(orig: ...)" format is mandatory

### 7.4 Correction

> "RD02 draft <row N>: <category> error: <description>. Expected: <correct>. Fix only that row."

---

## 8. Spec Coupling

Must not violate the `MDSCHEMA_RAWDATA_02_DATADICT.md` spec.

| Spec | This prompt |
|---|---|
| Column list | System Prompt Rule 1 + output format |
| Conditional rules (Retain N/A) | System Prompt Rule 7 |
| Scope enum | System Prompt Rule 3 |
| Type enum | System Prompt Rule 4 |
| Naming prefix | System Prompt Rule 2 |

---

## 9. Related Files

- **Spec:** `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_02_DATADICT.md`
- **Previous extractor (source):** `PROMPT_EXTRACT_IO_FROM_CODE.md` (for RD01 reference)
- **Next extractor:** `PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md`
- **Extraction guide (human):** `02_PROJECT_TYPES/RETROFIT/RETROFIT_EXTRACT_DATADICT.md` (to be written in Phase 4)
- **Naming:** `GLOBAL_NAMING_STANDARD.md`

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/analyze/PROMPT_EXTRACT_DATADICT_FROM_CODE.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). The data dictionary = internal memory map. v1.2.0 roadmap: AOI parameter detail, OOP CODESYS FB extension.*
