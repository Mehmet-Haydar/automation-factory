---
title: Retrofit FB/FC Specification Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD10_FBSpec
prerequisite: [MDSCHEMA_RAWDATA_10_FBSPEC.md, RETROFIT_EXTRACT_DATADICT.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_FBSPEC_FROM_CODE.md
---

# RETROFIT_EXTRACT_FBSPEC.md — FB/FC Spec Extraction Procedure

> **Goal:** extract the FB/FC inventory and parameter interfaces from legacy PLC code. THE DIRECT SOURCE for Gate 5 code generation.

---

## 1. Prerequisites

- [ ] _parsed.md Section 7 (FB) + Section 8 (FC) filled in
- [ ] RD01 IO + RD02 DataDict complete
- [ ] Legacy block-number → new-name mapping table (if available)

---

## 2. Legacy Block → New Block Conversion

```
Legacy (S5/S7 Classic):         New (modern):
  FB10  (motor control)           FB_Motor
  FB20  (valve control)           FB_Valve
  FC1   (IO scan)                 FC_ScanInputs
  FC2   (IO write)                FC_WriteOutputs
  FB100 (main sequence)           FB_Sequence_Main
```

**Rule:**
- Give a semantic name (FB_Motor, not FB10)
- Put the legacy name into Notes: "Original: FB10"
- For multi-instance, list every instance in InstanceDB (e.g., `"DB_Mot_Pump01, DB_Mot_Conv01"`)

---

## 3. Workflow

```
[1] _parsed.md + RD01 + RD02 ready
       ↓
[2] AI prompt: PROMPT_EXTRACT_FBSPEC_FROM_CODE.md
       ↓
[3] RD10_FBSpec_draft.md (two sheets: BlockList + ParamList)
       ↓
[4] Prepare the legacy-name → new-name mapping table
       ↓
[5] Apply ParamName prefixes (in_/out_/inout_/stat_/temp_)
       ↓
[6] Identify multi-instance FBs
       ↓
[7] RD10_FBSpec.xlsx
```

---

## 4. Human Review Checklist

#### A. Sheet 1: BlockList
- [ ] BlockName format `^(FB|FC)_[A-Z][A-Za-z0-9_]+$`
- [ ] BlockType correct (FB stateful, FC stateless)
- [ ] Version 1.0.0 (retrofit baseline)
- [ ] For FB, InstanceDB populated (every instance comma-separated)
- [ ] LinkedEquipment (Pump01, Conveyor01) consistent with RD01
- [ ] TemplateBase: GLOBAL_FB_TEMPLATE or Custom
- [ ] Legacy block name preserved in Notes

#### B. Sheet 2: ParamList
- [ ] Each parameter on its own row
- [ ] Correct ParamName prefix:
  - VAR_INPUT → `in_`
  - VAR_OUTPUT → `out_`
  - VAR_IN_OUT → `inout_`
  - VAR (static) → `stat_`
  - VAR_TEMP → `temp_`
- [ ] Type prefix abbreviation (b/w/i/di/r/t/s/u) inside ParamName
- [ ] Section enum correct (IN/OUT/INOUT/STAT/TEMP)
- [ ] Type IEC 61131-3
- [ ] Description preserves the German/Turkish original `(orig: ...)`

#### C. Multi-Instance Information
- [ ] Multi-instance FBs have their parameters written **ONCE** (not per instance)
- [ ] Instance information goes in the BlockList InstanceDB column

---

## 5. AOI / METHOD Special Cases

### 5.1 Allen-Bradley AOI
- List with BlockType=FB
- For AOI version differences use a SEPARATE BlockName (e.g., FB_Motor_v1, FB_Motor_v2)

### 5.2 CODESYS METHOD (OOP)
- BlockName format `<ParentFB>_<Method>`
- Notes: "OOP Method (CODESYS V3)"
- Visibility (PUBLIC/PRIVATE/PROTECTED) goes to Notes too

---

## 6. Common Pitfalls

- ❌ **Multi-instance FB written as separate ParamList rows per instance:** the interface is written ONCE
- ❌ **Keeping the legacy block name as the new name:** FB10 → FB_Motor (semantic)
- ❌ **No ParamName prefix:** "StartCmd" → "in_bStartCmd" (Section + Type prefix)
- ❌ **Misreading sections:** VAR_TEMP treated as STAT (different semantics)
- ❌ **AB AOI Input/Output confusion:** sometimes ambiguous
- ❌ **Non-semver Version:** "1" → "1.0.0"

---

## 7. Gate 3 Checklist

- [ ] All FB/FCs listed
- [ ] Semantic names assigned (legacy number → semantic name)
- [ ] Multi-instance distinction correct
- [ ] ParamName prefixes applied
- [ ] Legacy names captured in Notes
- [ ] TemplateBase chosen
- [ ] Ready for Gate 5 code generation

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_10_FBSPEC.md`
- **AI prompt:** `PROMPT_EXTRACT_FBSPEC_FROM_CODE.md`
- **Template:** `01_GLOBAL_STANDARDS/code_templates/GLOBAL_FB_TEMPLATE.scl`

---

*v1.1.0 — Full English body (2026-05-23). FBSpec is the skeleton of the new code. Correct extraction = a clean start.*
