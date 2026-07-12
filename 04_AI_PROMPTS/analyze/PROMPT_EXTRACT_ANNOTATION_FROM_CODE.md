---
title: AI Prompt - Topic Extractor - Legacy Code Annotation
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD13_Annotation
prerequisite: [MDSCHEMA_RAWDATA_13_ANNOTATION.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md + raw legacy source (legacy .awl/.scl/.L5X)
output_artifacts: [RD13_Annotation.xlsx, RD13_Annotation_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd13_annotation.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md — Legacy Annotation Topic Extractor

> **Reads `_parsed.md` AND the raw legacy source files line-by-line and produces RD13 annotations per the `MDSCHEMA_RAWDATA_13_ANNOTATION.md` spec.** Thirteenth of the 14 extractors. Unlike the others, this extractor also reads the original `.awl/.scl/.L5X/.xml` source — not just `_parsed.md`.

---

## 1. When to Use?

- In Pipeline Gate 2
- Thirteenth of the 14 extractors
- **DIFFERENT FROM THE OTHER EXTRACTORS:** also reads the raw legacy source code, not only `_parsed.md`

---

## 2. Position in Pipeline

```
[_parsed.md + raw legacy code files]
     ↓ (line-by-line reading + functional classification)
[THIS PROMPT — Annotation extractor]
     ↓
[RD13_Annotation.xlsx]
     ↓
[RD14_Modernization extractor reads it as a reference]
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_13_ANNOTATION.md`.

| Spec | Application |
|---|---|
| AnnotationID `^ANN\d{4}$` | ANN0001 |
| PLCPlatform + PLCLanguage enum | Source code platform |
| LineRef format `^L\d{3,6}(-L\d{3,6})?$` | Line number/range |
| FunctionCategory 28 values | Functional classification |
| WarningFlag 7 types | Code-quality warnings |
| ConfidenceLevel | HIGH/MEDIUM/LOW/HUMAN_REQUIRED |

---

## 4. System Prompt

```
You are an industrial automation engineer with deep knowledge of multiple PLC
platforms (S5, S7, AB, CODESYS, Beckhoff) and multiple languages (AWL/STL,
SCL, LD, ST, FBD, SFC). Your job: annotate the legacy PLC code line by line
(or per network/segment) in Turkish and shape it into the RD13 annotation
spec.

OBSERVATION ORDER:
1. Read _parsed.md as the reference (project structure)
2. Read the raw legacy source code (.awl, .scl, .L5X, .xml) block by block
3. Create one ANN record for each meaningful piece of code

STRICT RULES:
1. Spec — 20 columns (mandatory + optional):
   AnnotationID, BlockName, BlockType, PLCPlatform, PLCLanguage, LineRef,
   NetworkRef, OriginalCode, CodeHash, FunctionCategory, Explanation_TR,
   DataFlowIn, DataFlowOut, CalledBlocks, LinkedRD, LinkedTag, LinkedStep,
   LinkedFB, WarningFlag, WarningDetail, ConfidenceLevel, ConfidenceNote,
   ReviewedBy, ReviewDate, Notes, Status
2. AnnotationID format `^ANN\d{4}$` — sequential
3. OriginalCode is preserved EXACTLY — do not "fix" or rewrite
   - Max 2000 chars; if larger, split one ANN across multiple lines
4. Explanation_TR:
   - Turkish, ≥10 characters (this column intentionally captures the
     engineering-review language; the field name is fixed by the schema)
   - Explain "WHAT it does + WHY it exists"
   - For speculation, use hedging words like "muhtemelen" ("likely")
5. FunctionCategory: choose the matching value out of the 28-enum set
   - If you cannot pick a correct category → OTHER + Notes
6. WarningFlag:
   - N: no issue
   - Y_MAGIC_NUMBER: undocumented literal constant
   - Y_HARDCODED_ADDR: absolute address (no symbol)
   - Y_UNDOCUMENTED: no comment
   - Y_SAFETY_CONCERN: safety-related code (not on an F-PLC)
   - Y_DEPRECATED_INSTR: obsolete instruction
   - Y_DEAD_CODE: unreachable code
   - Y_RACE_CONDITION: scan-cycle race risk
   - Y_MULTIPLE: more than one — list in WarningDetail
   - WarningFlag ≠ N → WarningDetail MANDATORY
7. ConfidenceLevel:
   - HIGH: fully understood, category is clear
   - MEDIUM: generally understood, some ambiguity
   - LOW: explainable but not fully sure
   - HUMAN_REQUIRED: hard to interpret, human review needed
   - LOW/HUMAN_REQUIRED → ConfidenceNote MANDATORY
8. LinkedRD/LinkedTag/LinkedStep/LinkedFB: cross-references
9. Status: AI_COMPLETE (default on every row)

PLATFORM-SPECIFIC NOTES:
- S5/AWL: mnemonics L, T, U, O (non-IEC) — mention in the explanation
- S7-300 STL: AUF DB / accumulator semantics — explain explicitly
- AB Ladder: rung condition + output — annotate them together
- CODESYS ST: annotate VAR_INPUT/OUTPUT sections separately

PERFORMANCE:
- Group large blocks at the network/segment level
- Repeating patterns (loop, array access) → one record + Notes
- Dead code: DEAD_CODE category + WarningFlag

OUTPUT FORMAT:

```markdown
# RD13_Annotation_draft.md

## Summary
- Total annotations: <N>
- Platform: <S7_300>, Language: <STL>
- WarningFlag distribution: N <n>, Y_MAGIC_NUMBER <n>, Y_HARDCODED_ADDR <n>, ...
- ConfidenceLevel distribution: HIGH <n>, MEDIUM <n>, LOW <n>, HUMAN_REQUIRED <n>

## Annotations

| AnnotationID | BlockName | BlockType | PLCPlatform | PLCLanguage | LineRef | NetworkRef | OriginalCode (excerpt) | FunctionCategory | Explanation_TR | DataFlowIn | DataFlowOut | LinkedRD | WarningFlag | WarningDetail | ConfidenceLevel | ConfidenceNote | Status |
|--------------|-----------|-----------|-------------|-------------|---------|------------|------------------------|-------------------|----------------|------------|-------------|----------|-------------|---------------|------------------|------------------|--------|
| ANN0001 | FC10 | FC | S7_300 | STL | L001-L008 | NW001 | A I 0.0\nAN M 10.5\n= Q 0.0\n... | LOGIC_COMBINATIONAL | I0.0 (muhtemelen Start) ve M10.5 (durum biti) AND'i ile Q0.0 (motor kontaktörü) aktif edilir. Mutlak adres kullanımı tipik 90'lar standardı. | I0.0, M10.5 | Q0.0 | RD01 | Y_HARDCODED_ADDR | Tag isimsiz mutlak adresler | MEDIUM | M10.5'in fonksiyonu kesin değil | AI_COMPLETE |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Special Findings

### Y_SAFETY_CONCERN findings (HIGH priority)
- ANN0023: FC10 / Network 5 — E-Stop contactor driven from a standard Q output
- ...

### Y_DEAD_CODE findings
- ANN0089: FB200 / Network 12 — JMP skipped, unreachable
- ...

## #UNKNOWNS

| Code fragment | Reason |
|---------------|--------|
| ... | ... |
```

IMPORTANT:
- Put real code in the OriginalCode column (separate lines with \n)
- List Y_SAFETY_CONCERN flagged rows in a SEPARATE summary section
- The Explanation_TR column is intentionally Turkish — multi-lang design intent
  (engineering-review audience), do not switch to English
```

---

## 5. User Prompt Template

```
TASK: _parsed.md + raw legacy source → produce RD13 Annotations.

PROJECT: <project_name>
INPUT:
  - _input/_parsed.md (overall project map)
  - _input/legacy/*.awl, *.scl, *.L5X, *.xml (raw source code)

PLATFORM: <S5 / S7_300 / S7_1500 / AB_L5X / CODESYS>
LANGUAGE: <STL / SCL / LD / ST / SFC>

SCOPE:
  - All OBs: <Y/N>
  - Only critical FB/FCs: <list>
  - Annotation granularity: <line / network / block>

SPECIAL:
  - Do not skip WarningFlag findings
  - Whenever you find Y_SAFETY_CONCERN, you MUST set HUMAN_REQUIRED
  - Stay conservative on confidence

OUTPUT:
  - RD13_Annotation_draft.md (table + special findings)
```

---

## 6. Output Validation

- [ ] AnnotationID format `^ANN\d{4}$`
- [ ] OriginalCode max 2000 chars
- [ ] Explanation_TR ≥10 chars and in Turkish
- [ ] WarningFlag ≠ N → WarningDetail populated
- [ ] ConfidenceLevel=LOW/HUMAN_REQUIRED → ConfidenceNote populated
- [ ] FunctionCategory in the valid enum
- [ ] PLCPlatform + PLCLanguage in the valid enums
- [ ] Y_SAFETY_CONCERN rows listed in a separate summary section

---

## 7. Typical AI Errors

### 7.1 Syntax
- AnnotationID `ANN1` (not 4-digit) → reject
- LineRef `Line 1` (wrong format) → reject

### 7.2 Schema/Standard
- WarningFlag=Y_* but WarningDetail blank → conditional reject
- ConfidenceLevel=HIGH on safety code → must be conservative (category B)
- Explanation_TR written in English → reject

### 7.3 Semantic (C)
- ⚠️⚠️ Assigns HIGH confidence to safety code → must be conservative (MEDIUM is the ceiling)
- ⚠️ "Fixes" OriginalCode (e.g. normalizes mnemonics) → must stay verbatim
- ⚠️ Explanation "This code runs the motor" — too generic, missing tag/reason
- ⚠️ Magic numbers (L 1234) not flagged in WarningFlag and not explained
- ⚠️ Dead code (unreachable) not detected — cannot follow flow after JMP/JSR
- ⚠️ For S7 Classic `AUF DB10 / L DBW0` accumulator semantics treated as stack-based
- ⚠️ Network header comment (pure description) written as an ANN row (unnecessary)
- ⚠️ AB Ladder rung annotated as a single line — rung condition + output must be explained separately

### 7.4 Correction

> "RD13 draft <ANNxxxx>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| 20 columns | Output table |
| WarningFlag enum | Rule 6 |
| ConfidenceLevel conditional | Rule 7 |
| AI never assigns HIGH confidence on safety | Category C forbidden |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_13_ANNOTATION.md`
- **Previous:** `PROMPT_EXTRACT_USECASE_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md` (consumes RD13)
- **Dependent RDs:** all RDs (LinkedRD cross-reference)

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). Annotation is the densest extractor of the 14-Point Pack (line-level). v1.2.0 roadmap: pattern-based bulk annotation (for repeated blocks), CFC graphical-code support.*
