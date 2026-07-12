---
title: Metadata Input Guide
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_METADATA_SCHEMA.md, GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md]
status: ACTIVE
---

# METADATA_INPUT_GUIDE.md — Metadata Input Guide for Customer/Engineer

> **Purpose:** Explains how to enter customer Excel files, engineer MD templates, or AI outputs into the factory in the correct way.

---

## 1. Prerequisites

- [ ] `GLOBAL_NAMING_STANDARD.md` read (tag format rules)
- [ ] `GLOBAL_DATA_CLASSIFICATION.md` read (data class determined)
- [ ] Project type determined (retrofit / greenfield)
- [ ] Target RD list determined (usually all 01-14, some may be skipped depending on mode)

---

## 2. Three Input Channels

### 2.1 Channel A — Customer Excel

If the customer provides Excel in their own format:

```
[Customer Excel (e.g. "MotorList.xlsx")]
       ↓
[1] Convert to JSON with script_excel_to_metadata.py
       ↓
[2] Validate with script_consistency_check.py
       ↓
[3] The engineer fills in the missing fields
       ↓
[4] Convert to factory format with script_md_to_xlsx.py (optional)
```

**Command:**
```bash
python 05_SCRIPTS/dev/script_excel_to_metadata.py \
  --input <customer>/MotorList.xlsx \
  --output <project>/RD01_IO.json \
  --mapping <project>/customer_column_mapping.yaml
```

### 2.2 Channel B — Factory Template

Fill in the factory's standard MD templates:

```
[07_PROJECT_TEMPLATE/metadata_template/RD<NN>.md (empty)]
       ↓ copy
[<project>/RD<NN>.md]
       ↓ fill in (engineer or AI)
[validate]
```

### 2.3 Channel C — AI Extraction (Retrofit)

Extraction from old code with AI:

```
[Old PLC code]
       ↓ PROMPT_ANALYZE_<platform>.md
[_parsed.md]
       ↓ PROMPT_EXTRACT_<topic>_FROM_CODE.md
[RD<NN>_draft.md]
       ↓ Gate 3 human review
[RD<NN>.md (approved)]
```

---

## 3. Fill-In Order (Recommended)

Order based on dependencies:

```
1. RD01 IO List           (first — others reference its tags)
2. RD02 DataDict          (after RD01 — for LinkedTag)
3. RD09 Comms             (hardware inventory)
4. RD06 Motion            (RD01 + RD02 references)
5. RD05 Safety            (⚠️ awaits safety engineer approval)
6. RD04 Mode              (RD02 DB_ModeWord reference)
7. RD03 Flowchart         (RD04 ModeReq references)
8. RD07 Timing            (RD03 LinkedStep + RD08 LinkedAlarm)
9. RD08 Alarm             (RD05/RD07 cross-ref)
10. RD11 HMI              (pulls tags from all previous RDs)
11. RD10 FBSpec           (knows the whole structure — later)
12. RD12 UseCase          (RD03/RD04/RD10 cross-ref + operator workshop)
13. RD13 Annotation       (retrofit-specific — old code lines)
14. RD14 Modernization    (fed from RD13, last)
```

---

## 4. Typical Fill-In Mistakes

### 4.1 NAMING Mistakes
- ❌ `Motor1` (not uppercase, out of format)
- ✅ `MOT_PUMP_01` (`^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$`)
- ❌ Turkish character `MOTÖR_001`
- ✅ Pure ASCII `MOTOR_001`

### 4.2 Cross-Reference Mistakes
- ❌ RD07 Timer `LinkedStep: S015` but S015 doesn't exist in RD03
- ✅ RD03 must be complete BEFORE filling in RD07
- ❌ RD08 Alarm `TriggerTag: I0.0` (absolute address)
- ✅ `TriggerTag: F_I_EStop_N` (symbolic, from RD01)

### 4.3 Conditional Rule Violation
- ❌ AI signal but EngUnit empty → validator reject
- ❌ Critical alarm but AcknRequired=N → validator reject
- ❌ Retain=Y on a MemoryMarker → validator reject (Retain must be N/A)

### 4.4 Multi-Language Gaps
- ❌ AlarmText_EN filled, AlarmText_DE empty (for a German customer)
- ✅ Translate quickly using the glossary

### 4.5 Safety (RD05) Specific
- ❌ The AI writing SIL_Level=SIL2 → REJECT (unauthorized)
- ✅ AI records only in DRAFT_UNVERIFIED status, SIL empty
- ✅ APPROVED with the safety engineer's signature

---

## 5. Data Classification

A class must be determined for every RD file:

| Class | Example | Upload |
|-------|---------|--------|
| 🟢 PUBLIC | General pattern examples | Anywhere |
| 🟡 INTERNAL | In-company standard | Cursor/Claude tier |
| 🟠 **CONFIDENTIAL** | Customer code, machine secret | **Self-hosted or Enterprise AI MANDATORY** |
| 🔴 RESTRICTED | ITAR/EAR, defense | Air-gapped system |

Detail: `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`

---

## 6. Excel ↔ JSON Mapping

The factory's standard Excel format is converted to JSON as follows:

```
Excel Column     → JSON Field
─────────────────────────────
Tag              → Signals[].Tag
Address          → Signals[].Address
Type             → Signals[].Type
...              → ...
```

**If the customer Excel is not in factory format:**

Create a `<project>/customer_column_mapping.yaml` file:

```yaml
column_mapping:
  "Motor Bezeichnung": "Description"
  "Adresse": "Address"
  "Sinyal Tipi": "Type"
  "Schrank": "SourceModule"
  "Notiz": "Notes"
```

Then:
```bash
python 05_SCRIPTS/dev/script_excel_to_metadata.py \
  --input customer.xlsx \
  --mapping customer_column_mapping.yaml
```

---

## 7. Hybrid Filling with AI

In retrofit, the AI only produces a draft. Workflow:

```
Step 1: Run the AI prompt
   ↓ e.g. PROMPT_EXTRACT_IO_FROM_CODE.md
Step 2: AI output RD<NN>_draft.md
   ↓
Step 3: The engineer checks (Gate 3)
   ↓ fill in the #UNKNOWNS section, fix errors
Step 4: The AI output moves to APPROVED status
```

⚠️ **CRITICAL:** AI output does not go directly to production. Always human approval.

---

## 8. Validation Command

```bash
# Single RD
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --rd 01

# All RDs in order
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --rd all

# Output report
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --rd all \
  --report /tmp/validation_report.md
```

---

## 9. Cross-Validation (Gate 4)

Even if a single RD is correct, there can be cross-reference errors:

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --cross-ref
```

This check:
- RD07 Timer LinkedStep → does it exist in RD03?
- RD08 Alarm LinkedSF → does it exist in RD05?
- RD12 UseCase LinkedFB → does it exist in RD10?
- etc.

---

## 10. Practical Tips

### 10.1 For Excel
- Add a UTF-8 BOM (for non-ASCII characters)
- The header row is FIXED (the script expects it)
- Empty rows are accepted (gapless numbering is not required)
- Multiple sheets → select with `--sheet <name>`

### 10.2 For MD
- Frontmatter must be complete
- Table headers EXACTLY as in the template
- The `(orig: ...)` format in Description is for preservation

### 10.3 For AI output
- Never skip the `#UNKNOWNS` section
- Review ConfidenceLevel=LOW/HUMAN_REQUIRED items first
- Safety findings always require safety engineer approval

---

## 11. Related Files

- **Schema manager:** `01_GLOBAL_STANDARDS/rules/GLOBAL_METADATA_SCHEMA.md`
- **JSON schemas:** `08_METADATA_INPUT/schema/rd*.schema.json`
- **Templates:** `07_PROJECT_TEMPLATE/metadata_template/`
- **Validator:** `05_SCRIPTS/dev/script_consistency_check.py`
- **Excel conversion:** `05_SCRIPTS/dev/script_excel_to_metadata.py`
- **AI prompts:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_*_FROM_CODE.md`

---

## 12. Version

| v | Date | Change |
|---|------|--------|
| 1.0.0 | 2026-05-15 | First release — full 14-Point Pack covered |
| 1.1.0 | 2026-05-23 | Full English translation of the guide body |

---

*Input consistency is the foundation of output quality. This guide is the engineers' daily reference.*
