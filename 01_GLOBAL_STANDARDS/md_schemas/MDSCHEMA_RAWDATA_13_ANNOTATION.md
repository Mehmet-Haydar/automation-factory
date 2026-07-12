---
title: MDSCHEMA_RAWDATA_13_ANNOTATION — Legacy Code Annotation
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
---

# MDSCHEMA_RAWDATA_13_ANNOTATION — Legacy Code Annotation

---

## 0. File Identity

| Field | Value |
|-------|-------|
| Schema name | MDSCHEMA_RAWDATA_13_ANNOTATION |
| Version | 1.1.0 |
| Status | ACTIVE |
| Created | 2026-05-15 |
| Last updated | 2026-05-23 |
| Author | AUTOMATION_FACTORY AI Engine |
| Document language | EN |
| Output field language | TR (Explanation_TR is intentionally Turkish — engineering-review audience, multi-lang design intent) |
| RD point | RD13 — Legacy Code Annotation |
| Dependencies | RD01, RD02, RD03, RD06, RD10 |

---

## 1. Purpose and Scope

This schema documents legacy PLC code blocks extracted from old projects, line by line. Each record stores the original code snippet, annotation language, Turkish functional explanation, which RD point it relates to, and warning flags.

**RD13's role:**
- Build a reference document for understanding the legacy code
- Record which lines the AI understood and why
- Guide the human engineer through manual code review
- Feed RD14 modernization findings
- Serve as a reference for legacy behavior during FAT/SAT

**Out of scope:**
- New project code (RD10 FB Spec covers that)
- Variable list only (RD01 IO List / RD02 Data Dictionary cover that)
- Safety function analysis (RD05 Safety covers that)

---

## 2. Column Definitions

### 2A. Main Table: AnnotationList

| Column | Type | Required | Description |
|-------|-----|---------|----------|
| AnnotationID | STRING | YES | Unique record id. Format: `^ANN\d{4}$`. Example: `ANN0001` |
| BlockName | STRING | YES | Block name. POU/OB/DB name from the legacy project. Example: `FC10`, `OB35`, `DB1` |
| BlockType | ENUM | YES | `OB` / `FB` / `FC` / `DB` / `UDT` / `VAT` / `SFC` / `SFB` / `Other` |
| PLCPlatform | ENUM | YES | `S5` / `S7_300` / `S7_400` / `S7_1200` / `S7_1500` / `AB_L5X` / `CODESYS` / `Other` |
| PLCLanguage | ENUM | YES | `STL` / `LAD` / `FBD` / `SCL` / `AWL` / `IL` / `SFC` / `CFC` / `Other` |
| LineRef | STRING | YES | Line number or range. Format: `^L\d{3,6}(-L\d{3,6})?$`. Example: `L001`, `L001-L025` |
| NetworkRef | STRING | NO | Network/segment number. Example: `NW001`, `NW001-NW003` |
| OriginalCode | TEXT | YES | Original code snippet. Lines separated by `\n`. Max 2000 characters. |
| CodeHash | STRING | NO | SHA256 hash (first 12 characters). For change detection. |
| FunctionCategory | ENUM | YES | Functional category of the code. See §2B |
| Explanation_TR | TEXT | YES | Turkish explanation. Min 10 characters. Explains WHAT this code does and WHY it exists. Field name is intentionally `_TR` (multi-lang design intent — the review audience uses Turkish). |
| DataFlowIn | STRING | NO | Input variable or addresses. Comma-separated. Example: `I0.0, MW10, DB1.DBX0.0` |
| DataFlowOut | STRING | NO | Output variable or addresses. Comma-separated. |
| CalledBlocks | STRING | NO | Other blocks called from this code. Comma-separated. Example: `FC20, SFC14` |
| LinkedRD | STRING | NO | Related RD points. Comma-separated. Example: `RD01, RD03` |
| LinkedTag | STRING | NO | RD01 tag related to this code line. |
| LinkedStep | STRING | NO | Related RD03 StepID. Example: `S010` |
| LinkedFB | STRING | NO | Related RD10 BlockName. |
| WarningFlag | ENUM | YES | `N` / `Y_MAGIC_NUMBER` / `Y_HARDCODED_ADDR` / `Y_UNDOCUMENTED` / `Y_SAFETY_CONCERN` / `Y_DEPRECATED_INSTR` / `Y_DEAD_CODE` / `Y_RACE_CONDITION` / `Y_MULTIPLE` |
| WarningDetail | TEXT | CONDITIONAL | MANDATORY when WarningFlag ≠ N. Detailed description of the warning. |
| ConfidenceLevel | ENUM | YES | AI's confidence in this annotation. `HIGH` / `MEDIUM` / `LOW` / `HUMAN_REQUIRED` |
| ConfidenceNote | TEXT | CONDITIONAL | MANDATORY when ConfidenceLevel = LOW or HUMAN_REQUIRED. Why the confidence is low. |
| ReviewedBy | STRING | NO | Human engineer name (after review). |
| ReviewDate | DATE | NO | Review date. ISO 8601: `YYYY-MM-DD` |
| Notes | TEXT | NO | Free-text notes. |
| Status | ENUM | YES | `DRAFT` / `AI_COMPLETE` / `HUMAN_REVIEWED` / `APPROVED` / `OBSOLETE` |

### 2B. FunctionCategory Enumeration

| Value | Description |
|-------|----------|
| `IO_READ` | Physical input read (I, PIW, PIQW) |
| `IO_WRITE` | Physical output write (Q, PQW) |
| `ANALOG_SCALING` | Analog signal scaling/conversion |
| `LOGIC_COMBINATIONAL` | Combinational logic (AND/OR/NOT/XOR) |
| `LOGIC_SEQUENTIAL` | Sequential logic, state machine |
| `TIMER` | Timer block (TON/TOF/TP/TONR/SE/SA/SS) |
| `COUNTER` | Counter block (CTU/CTD/CTUD) |
| `MATH` | Arithmetic operations |
| `COMPARISON` | Comparison operations |
| `DATA_MOVE` | Data copy/move (MOVE, BLKMOV) |
| `TYPE_CONVERT` | Type conversion (INT_TO_REAL, DINT_TO_INT, etc.) |
| `STRING_OP` | String operations |
| `ARRAY_OP` | Array operations |
| `DB_ACCESS` | Data block access |
| `BLOCK_CALL` | Sub-block call (CALL, UC, CC) |
| `INTERRUPT` | Interrupt management |
| `COMM_SEND` | Communication send |
| `COMM_RECEIVE` | Communication receive |
| `MOTION_CMD` | Motion command |
| `SAFETY_LOGIC` | Safety logic (F-block or safety-related) |
| `ALARM_TRIGGER` | Alarm trigger/management |
| `MODE_CONTROL` | Mode control logic |
| `RECIPE_PARAM` | Recipe/parameter management |
| `DIAGNOSTIC` | Diagnostic |
| `INITIALIZATION` | Loading initial values (first scan) |
| `WATCHDOG` | Monitoring/watchdog logic |
| `DEAD_CODE` | Unreachable or unused code |
| `OTHER` | Anything not in the categories above |

---

## 3. JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "MDSCHEMA_RAWDATA_13_ANNOTATION",
  "title": "RD13 — Legacy Code Annotation",
  "type": "object",
  "properties": {
    "AnnotationList": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": [
          "AnnotationID", "BlockName", "BlockType", "PLCPlatform",
          "PLCLanguage", "LineRef", "OriginalCode", "FunctionCategory",
          "Explanation_TR", "WarningFlag", "ConfidenceLevel", "Status"
        ],
        "properties": {
          "AnnotationID": {
            "type": "string",
            "pattern": "^ANN\\d{4}$"
          },
          "BlockName": {
            "type": "string",
            "minLength": 1,
            "maxLength": 64
          },
          "BlockType": {
            "type": "string",
            "enum": ["OB", "FB", "FC", "DB", "UDT", "VAT", "SFC", "SFB", "Other"]
          },
          "PLCPlatform": {
            "type": "string",
            "enum": ["S5", "S7_300", "S7_400", "S7_1200", "S7_1500", "AB_L5X", "CODESYS", "Other"]
          },
          "PLCLanguage": {
            "type": "string",
            "enum": ["STL", "LAD", "FBD", "SCL", "AWL", "IL", "SFC", "CFC", "Other"]
          },
          "LineRef": {
            "type": "string",
            "pattern": "^L\\d{3,6}(-L\\d{3,6})?$"
          },
          "NetworkRef": {
            "type": "string"
          },
          "OriginalCode": {
            "type": "string",
            "minLength": 1,
            "maxLength": 2000
          },
          "CodeHash": {
            "type": "string",
            "pattern": "^[a-f0-9]{12}$"
          },
          "FunctionCategory": {
            "type": "string",
            "enum": [
              "IO_READ", "IO_WRITE", "ANALOG_SCALING",
              "LOGIC_COMBINATIONAL", "LOGIC_SEQUENTIAL",
              "TIMER", "COUNTER", "MATH", "COMPARISON",
              "DATA_MOVE", "TYPE_CONVERT", "STRING_OP", "ARRAY_OP",
              "DB_ACCESS", "BLOCK_CALL", "INTERRUPT",
              "COMM_SEND", "COMM_RECEIVE",
              "MOTION_CMD", "SAFETY_LOGIC",
              "ALARM_TRIGGER", "MODE_CONTROL", "RECIPE_PARAM",
              "DIAGNOSTIC", "INITIALIZATION", "WATCHDOG",
              "DEAD_CODE", "OTHER"
            ]
          },
          "Explanation_TR": {
            "type": "string",
            "minLength": 10
          },
          "DataFlowIn": {
            "type": "string"
          },
          "DataFlowOut": {
            "type": "string"
          },
          "CalledBlocks": {
            "type": "string"
          },
          "LinkedRD": {
            "type": "string"
          },
          "LinkedTag": {
            "type": "string"
          },
          "LinkedStep": {
            "type": "string",
            "pattern": "^S\\d{3}[A-Z]?$"
          },
          "LinkedFB": {
            "type": "string"
          },
          "WarningFlag": {
            "type": "string",
            "enum": [
              "N",
              "Y_MAGIC_NUMBER",
              "Y_HARDCODED_ADDR",
              "Y_UNDOCUMENTED",
              "Y_SAFETY_CONCERN",
              "Y_DEPRECATED_INSTR",
              "Y_DEAD_CODE",
              "Y_RACE_CONDITION",
              "Y_MULTIPLE"
            ]
          },
          "ConfidenceLevel": {
            "type": "string",
            "enum": ["HIGH", "MEDIUM", "LOW", "HUMAN_REQUIRED"]
          },
          "ReviewedBy": {
            "type": "string"
          },
          "ReviewDate": {
            "type": "string",
            "format": "date"
          },
          "Notes": {
            "type": "string"
          },
          "Status": {
            "type": "string",
            "enum": ["DRAFT", "AI_COMPLETE", "HUMAN_REVIEWED", "APPROVED", "OBSOLETE"]
          }
        },
        "allOf": [
          {
            "if": {
              "properties": { "WarningFlag": { "not": { "const": "N" } } }
            },
            "then": {
              "required": ["WarningDetail"],
              "properties": {
                "WarningDetail": { "type": "string", "minLength": 10 }
              }
            }
          },
          {
            "if": {
              "properties": {
                "ConfidenceLevel": { "enum": ["LOW", "HUMAN_REQUIRED"] }
              }
            },
            "then": {
              "required": ["ConfidenceNote"],
              "properties": {
                "ConfidenceNote": { "type": "string", "minLength": 10 }
              }
            }
          }
        ],
        "additionalProperties": false
      }
    }
  },
  "required": ["AnnotationList"]
}
```

---

## 4. Markdown Output Format

The project RD13 file is produced in the following format:

```markdown
# RD13 — Legacy Code Annotation | [PROJECT_NAME]

**Platform:** [PLCPlatform] | **Extraction date:** [DATE] | **Status:** [STATUS]

---

## Block: [BlockName] ([BlockType]) — [PLCLanguage]

### ANN0001 — Line [LineRef] ([FunctionCategory])

**Original Code:**
\```
[OriginalCode]
\```

**Explanation (TR):** [Explanation_TR]

**Data Flow:**
- In: [DataFlowIn]
- Out: [DataFlowOut]

**Warning:** [WarningFlag] — [WarningDetail]
**Confidence:** [ConfidenceLevel] — [ConfidenceNote]
**Related RD:** [LinkedRD] | **Tag:** [LinkedTag] | **Step:** [LinkedStep]

---
```

---

## 5. AI Filling Instructions

### 5.1 General Principles

```
RD13 — ANNOTATION FILLING RULES

[MANDATORY]
- Create a separate ANN record for each meaningful code block.
- OriginalCode: copy the original text VERBATIM; do not fix or interpret.
- Explanation_TR: explain in Turkish what it does AND why it exists.
- WarningFlag: flag code-quality issues; do not leave blank.
- ConfidenceLevel: if you cannot fully understand the code, write HUMAN_REQUIRED.

[FORBIDDEN]
- Modifying or "fixing" the original code.
- Speculating in the explanation — if unsure, use LOW or HUMAN_REQUIRED.
- Marking safety-related code with HIGH confidence.
- Adding non-mnemonic lines (comments/labels) from STL/AWL as a main record.

[PERFORMANCE]
- Group large blocks at the network/segment level, not line-by-line.
- Do not skip dead code — document it with the DEAD_CODE category.
- Repeating patterns (loop, array access) can be a single record + a note.
```

### 5.2 Source Platform Notes

| Platform | Special Note |
|----------|----------|
| S5/AWL | `L`, `T`, `U`, `O` mnemonics are non-IEC 61131-3; mention in the explanation |
| S7_300 STL | `OPN DB`, `A`, `AN`, `O`, etc. — annotate accumulator architecture |
| S7_300 LAD | Write the network title to NetworkRef |
| AB_L5X | Add the rung condition to OriginalCode |
| CODESYS | Add namespace and library dependencies to CalledBlocks |

### 5.3 WarningFlag Guide

| Flag | When to use |
|------|----------------|
| `Y_MAGIC_NUMBER` | Undocumented literal: `L 1234`, `== 27.5` |
| `Y_HARDCODED_ADDR` | Absolute address: `L MW100`, `A I 0.0` (no symbol) |
| `Y_UNDOCUMENTED` | No comment, no name, intent unclear |
| `Y_SAFETY_CONCERN` | Logic that may touch a safety function |
| `Y_DEPRECATED_INSTR` | Instruction no longer recommended by the platform |
| `Y_DEAD_CODE` | Unreachable or unused code |
| `Y_RACE_CONDITION` | Scan-cycle-dependent race-condition risk |
| `Y_MULTIPLE` | More than one warning — list in WarningDetail |

---

## 6. Error Taxonomy

### Category A — Syntax Errors (Auto-detectable)

| Code | Error | Fix |
|-----|------|-------|
| `A13-001` | AnnotationID format invalid (expects `ANN0001`) | apply pattern `^ANN\d{4}$` |
| `A13-002` | LineRef format invalid | apply `^L\d{3,6}(-L\d{3,6})?$` |
| `A13-003` | LinkedStep format invalid | apply `^S\d{3}[A-Z]?$` |
| `A13-004` | ReviewDate not ISO 8601 | use `YYYY-MM-DD` |
| `A13-005` | CodeHash not 12 hex characters | use SHA256[0:12] |

### Category B — Schema / Standard Errors (Validator-detected)

| Code | Error | Fix |
|-----|------|-------|
| `B13-001` | WarningFlag ≠ N but WarningDetail missing | add WarningDetail (min 10 characters) |
| `B13-002` | ConfidenceLevel=LOW/HUMAN_REQUIRED but ConfidenceNote missing | add ConfidenceNote |
| `B13-003` | Explanation_TR shorter than 10 characters | expand the explanation |
| `B13-004` | OriginalCode exceeds 2000 characters | split the code into multiple ANN records |
| `B13-005` | Status=APPROVED but ReviewedBy or ReviewDate missing | add human review info |

### Category C — Semantic Errors (Manual Review)

| Code | Error | Fix |
|-----|------|-------|
| `C13-001` | FunctionCategory does not fit the code | revise the category; use OTHER + Notes if needed |
| `C13-002` | ConfidenceLevel does not reflect reality (too high) | be conservative, especially on safety logic |
| `C13-003` | WarningFlag missed a safety issue | request safety-engineer review |
| `C13-004` | Explanation_TR not technical, meaningless | write a detailed, technical explanation |
| `C13-005` | LinkedRD points to the wrong RD point | revise the RD points |
| `C13-006` | Dead code not flagged | mark unreachable branches with DEAD_CODE |

---

## 7. Related Files

| File | Relationship |
|-------|--------|
| `MDSCHEMA_RAWDATA_01_IO_LIST.md` | Source of LinkedTag |
| `MDSCHEMA_RAWDATA_02_DATADICT.md` | LinkedFB and DB references |
| `MDSCHEMA_RAWDATA_03_FLOWCHART.md` | Source of LinkedStep |
| `MDSCHEMA_RAWDATA_05_SAFETY.md` | Cross-check for the Y_SAFETY_CONCERN flag |
| `MDSCHEMA_RAWDATA_10_FBSPEC.md` | Source of CalledBlocks and LinkedFB |
| `MDSCHEMA_RAWDATA_14_MODERNIZATION.md` | RD13 findings feed RD14 FindingID |
| `04_AI_PROMPTS/analyze/PROMPT_ANALYZE_S7_300_STL.md` | AI prompt that fills this schema |
| `04_AI_PROMPTS/analyze/PROMPT_ANALYZE_S5_AWL.md` | Prompt for S5/AWL source |
| `04_AI_PROMPTS/analyze/PROMPT_ANALYZE_AB_L5X.md` | Prompt for AB L5X source |
| `04_AI_PROMPTS/analyze/PROMPT_ANALYZE_CODESYS.md` | Prompt for CODESYS source |

---

## 8. Sample Record (S7-300 STL)

```yaml
AnnotationID: ANN0001
BlockName: FC10
BlockType: FC
PLCPlatform: S7_300
PLCLanguage: STL
LineRef: L001-L008
NetworkRef: NW001
OriginalCode: |
  A     I      0.0
  AN    M      10.5
  =     Q      0.0
  A     I      0.0
  AN    M      10.5
  L     T#3S
  SE    T      1
  NOP 0
FunctionCategory: LOGIC_COMBINATIONAL
Explanation_TR: >
  I0.0 girişi (muhtemelen Start butonu) ve M10.5 bellek biti (muhtemelen motor çalışıyor
  sinyali değil) koşullu AND ile kontrol edilerek Q0.0 çıkışı (muhtemelen konveyör
  motoru kontaktörü) Active ediliyor. Aynı koşulda 3 saniyelik bir zamanlayıcı başlatılıyor.
  M10.5'in ne olduğu belirsiz — yorumsuz adres kullanımı.
DataFlowIn: "I0.0, M10.5"
DataFlowOut: "Q0.0, T1"
FunctionCategory: TIMER
LinkedRD: "RD01, RD07"
LinkedTag: ""
WarningFlag: Y_MULTIPLE
WarningDetail: >
  1) Y_HARDCODED_ADDR: I0.0, M10.5, Q0.0, T1 absolute addresses without symbols.
  2) Y_UNDOCUMENTED: no network comment; meaning of M10.5 unclear.
  3) NOP 0: meaningless instruction, likely development residue not cleaned up.
ConfidenceLevel: MEDIUM
ConfidenceNote: >
  Because the I/O mappings are unknown, the explanation is assumption-based.
  The exact function of M10.5 needs human review.
Status: AI_COMPLETE
```

---

## 9. Version History

| Version | Date | Change |
|-------|-------|------------|
| 1.0.0 | 2026-05-15 | Initial release — 14-Point Pack RD13 |
| 1.1.0 | 2026-05-23 | Full English body (translation audit Phase 2 Tier 1b). Explanation_TR field name and Turkish sample content preserved (multi-lang design intent). |

---

## 10. Warnings and Limitations

> **AI LIMITATION:** Legacy-code annotation is context-dependent. Without context the AI cannot know what absolute addresses do. Annotations done without the IO list (RD01) and data dictionary (RD02) provided in advance will have low confidence.

> **SAFETY:** All lines flagged `Y_SAFETY_CONCERN` must be reviewed by a safety engineer. AI annotation does NOT replace safety analysis.

> **QUALITY:** All records with ConfidenceLevel=HUMAN_REQUIRED must be reviewed by an engineer before project approval (Gate 3 HUMAN REVIEW).

---

*v1.1.0 — Full English body (2026-05-23). 14-Point Raw Data Pack — thirteenth file. Line-level annotation and warning system for legacy PLC code. Status enum (`DRAFT/AI_COMPLETE/HUMAN_REVIEWED/APPROVED/OBSOLETE`) is unique to RD13 (review-workflow oriented) — not the project-wide `Active/Inactive/Spare` set.*
