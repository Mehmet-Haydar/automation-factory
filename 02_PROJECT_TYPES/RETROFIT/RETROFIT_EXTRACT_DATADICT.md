---
title: Retrofit Data Dictionary Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD02_DataDict
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md, MDSCHEMA_RAWDATA_02_DATADICT.md, RETROFIT_IO_EXTRACT.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_DATADICT_FROM_CODE.md
---

# RETROFIT_EXTRACT_DATADICT.md — Data Dictionary Extraction Procedure

> **Goal:** systematically extract the internal-variable dictionary (DB fields, UDT members, markers) from legacy PLC code and document it per the RD02 spec.

---

## 1. Prerequisites

- [ ] **RD01 IO List complete** (mandatory for LinkedTag references)
- [ ] Legacy PLC code is in the `_input/` folder (exported or parsed)
- [ ] `_parsed.md` produced (Platform parser output)
- [ ] Data classification done: customer DBs → typically 🟠 CONFIDENTIAL
- [ ] Engineer: has access to the legacy platform's symbol table

---

## 2. Workflow

### 2.1 Which Variables Belong in DataDict?

**IN SCOPE for RD02:**
- All variables inside global DBs (e.g. `DB_Recipe.RecipeID`, `DB_System.HeartbeatBit`)
- FB fields inside instance DBs (IN/OUT/INOUT/STAT sections)
- UDT/DUT struct members
- Memory markers in meaningful use (M-area)
- Critical VAR_TEMP variables

**NOT IN SCOPE for RD02:**
- Physical I/O → RD01 IO List
- HMI tags → RD11 HMI
- Throwaway flags (used in 1-2 lines and discarded) → skip

### 2.2 Hybrid Workflow (AI + Human)

```
[1] _parsed.md ready
       ↓
[2] Run the AI prompt (self-hosted if CONFIDENTIAL)
       ↓ PROMPT_EXTRACT_DATADICT_FROM_CODE.md
[3] RD02_DataDict_draft.md (AI output)
       ↓
[4] Human review (this document — Section 3)
       ↓
[5] RD02_DataDict.xlsx (approved)
       ↓
[6] Gate 4 validation (script_consistency_check)
       ↓
[7] RD02_DataDict.md (clean format for Gate 5 code generation)
```

### 2.3 Running the AI Prompt

```bash
# Self-hosted Claude/GPT or Cursor Enterprise
# Data classification: 🟠 → DO NOT upload to a public AI

# Run prompt
python 05_SCRIPTS/script_run_extractor.py \
  --prompt 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_DATADICT_FROM_CODE.md \
  --input <project>/_input/_parsed.md \
  --output <project>/_input/RD02_DataDict_draft.md \
  --context <project>/_input/RD01_IO_List.md   # cross-reference
```

(NOTE: `script_run_extractor.py` is to be written in Phase 6. Until then, copy and paste manually.)

### 2.4 Human Review Checklist (at Gate 3)

#### A. Naming-Standard Check
- [ ] Does every FB variable carry the ParamName prefix? (`in_/out_/inout_/stat_/temp_`)
- [ ] Is the Type prefix correct? (b=BOOL, w=WORD, i=INT, di=DINT, r=REAL, t=TIME, s=STRING, u=UDT)
- [ ] Full compliance with GLOBAL_NAMING_STANDARD?

#### B. Scope Correctness
- [ ] GlobalDBs: correct ParentBlock (DB name)
- [ ] InstanceDBs: correct FB-instance reference (`DB_Mot_Pump01`, etc.)
- [ ] UDT members: ParentBlock = UDT name
- [ ] MemoryMarker rows have Retain = N/A
- [ ] TempVar rows have Retain = N/A

#### C. Cross-Reference (with RD01)
- [ ] LinkedTag populated for variables identified as "signal-copy" patterns
  (e.g. `M10.0 := I0.0` → LinkedTag = new tag name from RD01 I0.0)
- [ ] DB fields exposed to HMI marked with "HMI" in Notes

#### D. Preserving German/Turkish Originals
- [ ] Description retains the `(orig: <German/Turkish>)` format
- [ ] OldVar column not empty — the original variable name is preserved

#### E. Retain Values
- [ ] **DANGER:** a wrong Retain setting causes data loss on power failure
- [ ] Recipe variables → Retain=Y
- [ ] Counter variables (counts must not be lost) → Retain=Y
- [ ] Transient state (process state) → Retain=N
- [ ] Push unclear ones into #UNKNOWNS and ask the customer

### 2.5 Typical Corrections (after AI)

| Issue | Seen in AI output | Fix |
|-------|-------------------|-----|
| ParamName prefix missing | `MotorRunning` | `stat_bMotorRunning` |
| Wrong Type prefix | `stat_MotorRunning` (no b) | `stat_bMotorRunning` |
| Retain=N on a MemoryMarker | `M10.0 / Retain=N` | `M10.0 / Retain=N/A` |
| UDT as a single row | `UDT_Motor / 12 bytes / ...` | One row per member of UDT_Motor |
| Offset value on an Optimized DB | `0.0` | `OPT` |
| German comment dropped | `"Motor running"` | `"Motor running (orig: Motor läuft)"` |
| Vendor-specific type | `Type=S5TIME` | `Type=TIME; Notes="S5TIME (S5/S7 Classic)"` |

---

## 3. Field Discovery (When the Symbol Table Is Missing)

In older projects the symbol table may be lost. In that case:

### 3.1 STEP 5 Projects
- Request the `.ini` symbol file from a PG-685/PG-750
- If not available: usually located under the "Symbolik" heading at the bottom of AWL listings
- If none exists: from the engineer's paper notes (manual)

### 3.2 STEP 7 V5.x Projects
- SIMATIC Manager → Symbols editor → `Export → .SEQ or .DIF`
- Cross reference: `Options → Reference Data → Generate`
- Symbol-less addresses: clues from comments

### 3.3 TIA Portal Projects
- `PLC tags → All tags → Export to XLSX`
- DB structures: UDT export from SCL source
- HMI tag binding: HMI → Tags → Export

### 3.4 Allen-Bradley
- Studio 5000 → Tools → Export → Tags and Logic Comments (.csv)
- Per-routine: Logic → Export Routine
- AOI parameters: inside the AOI file

### 3.5 CODESYS / TwinCAT
- Project → Export → PLCopen XML
- Beckhoff TwinCAT: `*.tmc` module files
- GVLs and POU interfaces inside the XML

---

## 4. Validation

### 4.1 Automated Check

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project_path> \
  --schema RD02 \
  --check-naming \
  --check-cross-reference
```

Output:
- Naming-standard violations
- Invalid Scope/Retain combinations
- LinkedTag empty where required
- Missing UDT members
- Duplicate (VarName, ParentBlock) records

### 4.2 Manual Validation

| Category | Check |
|----------|-------|
| Naming | `^[a-z]+_[a-z][A-Za-z0-9]+$` regex |
| Scope vs Retain | MemoryMarker/TempVar → Retain=N/A |
| Cross-ref | Is LinkedTag in RD01 |
| Type enum | Non-IEC 61131-3 types documented in Notes |
| Description | Original German/Turkish preserved |

---

## 5. Common Pitfalls (KB Records)

> Details: `06_KNOWLEDGE_BASE/KB_PITFALLS_RETROFIT_DATADICT.md` (future)

- ❌ **Mixing Optimized DBs and Non-optimized DBs:** TIA Portal Optimized DBs don't expose offsets. Classic DBs use byte.bit offsets. Mixing them causes address-overflow surprises.
- ❌ **Multi-instance FB parameters are not duplicated per instance:** ParamList is written once per FB; instance info stays in the InstanceDB column.
- ❌ **Treating MemoryMarker as IO:** the %M area belongs to RD02, not RD01. Only meaningful uses (don't add throwaway flags to the RD).
- ❌ **Wrong use of Retain=Y:** setting every DB to Retain=Y causes performance/SD-card wear issues. Only retain what truly must persist.
- ❌ **Confusing CODESYS PERSISTENT with RETAIN:** PERSISTENT = preserved even after a cold start; RETAIN = preserved on a warm start. They are distinct concepts in CODESYS V3.
- ❌ **Putting AB AOI parameters into DataDict:** AOI parameters belong to RD10 FBSpec, not RD02.

---

## 6. AI Prompt Suggestion

The AI side of this procedure: `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_DATADICT_FROM_CODE.md`

Skeleton:
```
ROLE: engineer expert in IEC 61131-3 data-type modelling
INPUT: _parsed.md (platform-parser output) + RD01 (cross-reference)
SCOPE: internal variables (DB/UDT/MemoryMarker/TempVar) — physical I/O EXCLUDED
RULES: MDSCHEMA_RAWDATA_02_DATADICT.md spec + GLOBAL_NAMING_STANDARD.md prefix
SECURITY: 🟠 CONFIDENTIAL — self-hosted/enterprise AI
OUTPUT: RD02_DataDict_draft.md + #UNKNOWNS
```

---

## 7. Gate 3 Approval Checklist

When the retrofit DataDict extraction is complete:

- [ ] All Global DB fields extracted
- [ ] All Instance DB fields (per FB) extracted
- [ ] UDT/DUT members listed as separate rows
- [ ] Meaningful MemoryMarkers included, throwaway flags skipped
- [ ] ParamName prefix correct on all FB variables
- [ ] LinkedTag (RD01 reference) populated where required
- [ ] OldVar populated on every row (original preserved)
- [ ] Retain values confirmed with the customer
- [ ] script_consistency_check.py clean
- [ ] #UNKNOWNS section addressed by a human (decision on every row)

---

## 8. Related Files

- **Spec:** `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_02_DATADICT.md`
- **AI prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_DATADICT_FROM_CODE.md`
- **Previous guide:** `RETROFIT_IO_EXTRACT.md` (RD01)
- **Next:** `RETROFIT_EXTRACT_MODE.md` (RD04)
- **Naming:** `GLOBAL_NAMING_STANDARD.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD02_DataDict.xlsx` (Phase 5)

---

*v1.1.0 — Full English body (2026-05-23). This procedure is applied identically in every retrofit project. For AI-improvement suggestions, use `script_propose_update.py`.*
