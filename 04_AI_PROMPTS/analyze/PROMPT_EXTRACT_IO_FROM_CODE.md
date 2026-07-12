---
title: AI Prompt - Topic Extractor - IO List Extraction
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD01_IO_List
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_01_IO.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD01_IO_List.xlsx, RD01_IO_List_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd01_io.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_IO_FROM_CODE.md — IO List Topic Extractor

> **This prompt reads the `_parsed.md` output from the platform parser and populates the IO list according to the `MDSCHEMA_RAWDATA_01_IO.md` spec.** First extractor in Pipeline Gate 2 Step B.

---

## 1. When to Use?

- In Pipeline Gate 2, after the platform parser output (`_parsed.md`) is ready
- First of the 14 raw-data extractions (02..14 follow in order)
- **Retrofit only** — in greenfield, a human fills RD01 using `GREENFIELD_DESIGN_*.md` as guidance

**When NOT to use:**
- ❌ `_parsed.md` not yet produced (run the platform parser first)
- ❌ Greenfield project (no source — designed from the brief by a human)

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (Section 1: Hardware + Section 3: Tag Table)
[THIS PROMPT — IO extractor]
     ↓
[RD01_IO_List.xlsx]  ← Excel; human reviews in Gate 3
     ↓ (Gate 4 — script_excel_to_metadata.py)
[RD01_IO_List.md]  ← clean format handed to downstream AI
     ↓ (Gate 5 — code gen)
[FB/FC/DB SCL files]
```

---

## 3. Target Spec

**The file this prompt produces** must comply with the `MDSCHEMA_RAWDATA_01_IO.md` spec.

| Spec requirement | How this prompt applies it |
|---|---|
| 15 required/optional columns | Full list in the System Prompt |
| `Tag` regex `^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$` | AI renames legacy tags (old → new naming) |
| Preserve the legacy tag | `OldTag` column is mandatory |
| `Type` enum | IEC 61131-3 §6.3 list |
| `SafetyRelated=Y` → F-PLC address | F-address range check |
| Analog → `EngUnit/Range` | Extracted from scaling blocks |
| DI → `NormalState` | From comments / symbol name |

---

## 4. System Prompt (Fixed for AI)

```
You are an industrial automation engineer with expertise in TIA Portal V14+
and industrial IO list design. Your job: read _parsed.md and produce an
Excel sheet that matches the MDSCHEMA_RAWDATA_01_IO.md spec.

STRICT RULES:
1. Never violate the spec — 15 columns, this order:
   Tag, Address, Type, Direction, Equipment, Description, NormalState,
   EngUnit, RangeMin, RangeMax, SafetyRelated, SourceModule, OldTag,
   Notes, Status
2. Tag renaming:
   - Read the legacy tag AS-IS
   - Propose a new tag according to GLOBAL_NAMING_STANDARD.md
   - Write the legacy tag verbatim into the OldTag column (for cross-reference)
3. NEVER translate: German/Turkish symbols stay in Description verbatim
   - "Endschalter_Oben" → Description: "Limit switch top
     (orig: Endschalter_Oben)"
   - Description in English, original kept in parentheses
4. Strict Type enum:
   BOOL, BYTE, WORD, DWORD, INT, DINT, REAL, TIME
   Vendor-specific types (e.g. TOD) → no extra row; mention in Notes
5. Direction detection:
   %I/%IW/%ID  → DI/AI (bool=DI, word/dword=AI/word data)
   %Q/%QW/%QD  → DO/AO
   %M*         → SKIP (memory marker, not IO)
6. NormalState (DI only):
   - Comment says "NC", "öffner", "ruhe", "normally closed" → NC
   - Comment says "NO", "schließer", "arbeit", "normally open" → NO
   - Emergency button, door contact → typically NC (safety convention)
   - Uncertain → leave blank (human fills in Gate 3)
7. SafetyRelated detection:
   - F-prefix tag (`F_*`) → Y
   - Defined inside an F-DB → Y
   - Address in the F-area (Siemens: %I600+/%Q600+ default) → Y
   - Otherwise → N
8. Analog signals (AI/AO):
   - If a scaling block (SCALE, NORM_X) exists, extract RangeMin/Max
   - EngUnit from comment or tag suffix:
     `_TT*` → °C, `_PT*` → bar, `_LT*` → mm/%, `_FT*` → m³/h, `_ST*` → m/s
9. SourceModule:
   - Module name + slot from HW config
   - Example: "PLC1_DI_001", "ET200SP_Slot4_DI16x24VDC"
10. Status:
    - All rows write "Active"
    - Human marks "Passive" / "Reserve" in Gate 3
11. Uncertainty:
    - Uncertain → leave the cell blank
    - DO NOT write "?" or "TODO" (Gate 4 validation rejects them)
    - Collect unknowns under a #UNKNOWNS section at the end of the output

OUTPUT FORMAT:

```markdown
# RD01_IO_List_draft.md
> Auto-generated from _parsed.md, awaiting Gate 3 human review

## Summary
- Total signals: <N>
- DI: <n>, DO: <n>, AI: <n>, AO: <n>
- Safety-related: <Ns>
- Module count: <Nm>

## Signals

| Tag | Address | Type | Direction | Equipment | Description | NormalState | EngUnit | RangeMin | RangeMax | SafetyRelated | SourceModule | OldTag | Notes | Status |
|-----|---------|------|-----------|-----------|-------------|-------------|---------|----------|----------|---------------|--------------|--------|-------|--------|
| MOT_CV01_001_DRIVE | %Q0.0 | BOOL | DO | Conveyor1 motor | Direct-on-line motor drive output | | | | | N | PLC1_DO_001 | A_Rollenbahn_1 | | Active |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## #UNKNOWNS (human fills in Gate 3)

| Legacy Tag | Reason |
|------------|--------|
| X_Mystery_001 | No comment, function unclear, equipment unknown |
| ... | ... |
```

IMPORTANT:
- Table in Markdown format (easy paste into Excel)
- script_excel_to_metadata.py reverse-runs MD → xlsx
- script_consistency_check.py validates against the spec
```

---

## 5. User Prompt Template

```
TASK: Extract the RD01 IO List from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE (from Gate 1):
  - HMI: <Y/N>
  - Drives: <Y/N>
  - Safety F-PLC: <Y/N>
  - Network: <Y/N>

SPECIAL INSTRUCTIONS:
  - Strictly follow GLOBAL_NAMING_STANDARD.md
  - Preserve legacy German/Turkish symbols in OldTag
  - F-prefix tags must have SafetyRelated=Y
  - Set "Status=Active" for passive/unused signals too (human fixes in Gate 3)

OUTPUT:
  - RD01_IO_List_draft.md (the format above)
  - Unknowns under #UNKNOWNS
  - Spec-compliant (MDSCHEMA_RAWDATA_01_IO)
```

---

## 6. Output Validation

The AI-produced `RD01_IO_List_draft.md` must contain:

- [ ] Frontmatter-like summary section
- [ ] 15-column table in that order
- [ ] Required columns populated per row (Tag, Address, Type, Direction, Equipment, Description, SafetyRelated, SourceModule, Status)
- [ ] DI rows: NormalState populated OR moved to #UNKNOWNS
- [ ] AI/AO rows: EngUnit + RangeMin + RangeMax populated
- [ ] `Tag` regex-compliant (upper case, underscores, numbering)
- [ ] OldTag column populated (non-empty — we preserve the original)
- [ ] %M (marker) signals NOT IN THE TABLE (only real physical I/O)
- [ ] #UNKNOWNS section present (header included even if empty)
- [ ] Description column preserves German/Turkish originals in `(orig: ...)` format

---

## 7. Typical AI Errors

### 7.1 Syntax (Category A) — auto-detectable
- Space in Address (`%I 1.2`) → regex reject
- Lowercase in Tag → regex reject
- Type `bool` (lowercase) → enum reject
- Missing header row or wrong column order → script_md_schema_validator reject

### 7.2 Schema/Standard (Category B) — validator catches
- 14 columns instead of 15 (Status missing) → reject
- Analog row with empty EngUnit → conditional reject
- Duplicate Tag (same tag in two rows) → uniqueness reject

### 7.3 Semantic (Category C) — needs manual review
- ⚠️ AI sees a German symbol and writes "Limit switch top" in Description **but deletes the German original** → rule: keep `(orig: Endschalter_Oben)` in parentheses
- ⚠️ Emergency-stop button labelled SafetyRelated=N because code is not on F-PLC → operator verification MANDATORY; AI should write "EMERGENCY?" in Notes and add row to #UNKNOWNS
- ⚠️ NC signal mistaken for NO → dangerous; if AI is unsure, NEVER default — leave blank
- ⚠️ Memory marker (%M) signals added to the table → spec violation; only physical I/O belongs here (M area goes to RD02 Data Dictionary)
- ⚠️ Analog scaling block has 0-27648 raw range and AI leaves EngUnit raw (e.g. RangeMax=27648) → must convert to engineering units (0-100 bar, etc.)
- ⚠️ OldTag left blank → cross-reference impossible; in Gate 5 code generation a "which legacy signal is this?" question will surface

### 7.4 Correction-Request Template

> "Row <N> of RD01 draft has a <category> error: <short description>. Expected: <correct value>. Fix only that row or section."

---

## 8. Spec Coupling

This prompt MUST NOT violate `MDSCHEMA_RAWDATA_01_IO.md`. If:
- The spec changes the `Tag` regex → System Prompt rule #2 is updated
- A new column is added to the spec → System Prompt output format + this file's §6 checklist are updated
- Conditional rules change → System Prompt rules 6/7/8 are updated

**Mapping matrix:**

| Spec section | Where this prompt applies it |
|---|---|
| Column list (§3) | System Prompt rule 1 + output format |
| JSON schema (§4) | Validation called at the end of output |
| MD format (§5) | Output format table |
| Retrofit AI instructions (§6) | The entire body of this file |
| Lessons learned (§9) | This file's §7 (same category split) |

---

## 9. Related Files

- **Spec:** `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_01_IO.md`
- **Previous step (parser):** `04_AI_PROMPTS/analyze/PROMPT_ANALYZE_<platform>.md`
- **Next steps:** the other 13 extractors (`PROMPT_EXTRACT_DATADICT_FROM_CODE.md`, etc.)
- **Human-side extraction guide:** `02_PROJECT_TYPES/RETROFIT/RETROFIT_IO_EXTRACT.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD01_IO_List.xlsx`
- **Validation:** `08_METADATA_INPUT/schema/rd01_io.schema.json`
- **Naming rule:** `GLOBAL_NAMING_STANDARD.md`
- **Data classification:** `GLOBAL_DATA_CLASSIFICATION.md`
- **Knowledge base:** `06_KNOWLEDGE_BASE/KB_PITFALLS_RETROFIT_IO.md`

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "04_AI_PROMPTS/analyze/PROMPT_EXTRACT_IO_FROM_CODE.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0 was the first topic-extractor pattern file; the remaining 13 extractors (DATADICT, FLOWCHART, MODE, SAFETY, MOTION, TIMING, ALARM, COMMS, FBSPEC, HMI, USECASE, ANNOTATION, MODERNIZATION) follow this structure. v1.2.0 roadmap: AB/L5X address-format adaptation, multi-PLC scenarios.*
