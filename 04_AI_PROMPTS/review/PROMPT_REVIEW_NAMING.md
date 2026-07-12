---
title: AI Prompt - Naming Compliance Review
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_02_DATADICT.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: RD01_IO_List.md, RD02_DataDict.md, RD10_FBSpec.md
output_artifacts: [naming_review_report.md]
role: review
schema: PROMPT_REVIEW
---

# PROMPT_REVIEW_NAMING.md — Naming Compliance Review

> **This prompt checks every tag/variable/block name in the RD01/RD02/RD10 files against `GLOBAL_NAMING_STANDARD.md`.** Automated assistant for Gate 3 HUMAN REVIEW.

---

## 1. When to Use?

- During the Gate 3 HUMAN REVIEW stage
- After AI has filled in RD01-RD02-RD10
- After the customer Excel import (`script_excel_to_metadata.py`)
- After manual engineer corrections

---

## 2. Position in Pipeline

```
[RD01 + RD02 + RD10 (filled)]
       ↓
[THIS PROMPT — Naming Review]
       ↓
[naming_review_report.md]
       ├─ Category A (regex/format violations) — auto-fix
       ├─ Category B (broken cross-refs) — manual fix
       └─ Category C (semantic) — operator/engineer review
```

---

## 3. System Prompt

```
You enforce GLOBAL_NAMING_STANDARD.md. You check every tag, variable, and
block name in the RD files against the standard.

STRICT RULES:
1. Tag format: `^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$`
2. ParamName prefix: in_/out_/inout_/stat_/temp_ (FB variables)
3. Type prefix: b=BOOL, w=WORD, i=INT, di=DINT, r=REAL, t=TIME, s=STRING, u=UDT
4. BlockName: `^(FB|FC)_[A-Z][A-Za-z0-9_]+$`
5. F-prefix only for safety-PLC signals
6. Turkish characters (ı, ğ, ş, ç, ö, ü) FORBIDDEN (ASCII required)
7. Reserved names (T1, M10, DB1) FORBIDDEN

CHECK ORDER:
1. RD01.Signals → does every Tag match the regex
2. RD02.Variables → does every VarName have a correct prefix + type prefix
3. RD10.BlockList → is the BlockName format correct
4. RD10.ParamList → is the ParamName prefix correct
5. Cross-ref: LinkedTag, LinkedVar, LinkedFB all present

OUTPUT FORMAT:

# naming_review_report.md

## Summary
- Total records: <N>
- Category A (syntax): <count>
- Category B (cross-ref): <count>
- Category C (semantic): <count>
- Passing: <count>

## A — Syntax Violations (Auto-Fixable)

| RD | Row | Current | Suggested | Reason |
|----|-----|---------|-----------|--------|
| RD01 | 12 | Motor1 | MOT_PUMP_001 | Format violation (regex) |
| RD02 | 5 | MotorRunning | stat_bMotorRunning | Prefix missing (for FB STAT) |
| ... | ... | ... | ... | ... |

## B — Cross-Reference Errors

| RD | Row | Field | Old Reference | Status |
|----|-----|-------|---------------|--------|
| RD07 | 3 | LinkedAlarm | ALM0999 | Not in RD08 |
| ... | ... | ... | ... | ... |

## C — Semantic Questions (Human Review)

| Tag | Reason |
|-----|--------|
| MOT_ABC_001_XYZ | Suffix "XYZ" not defined in GLOBAL_NAMING — operator interview |
| ... | ... |
```

---

## 4. User Prompt

```
TASK: review naming compliance for the files <project_path>/metadata/RD01..RD14.md.

PROJECT: <project_name>
PLATFORM: <S7-1500 / AB / CODESYS>

SPECIAL:
- F-prefix is only for safety (cross-check with RD05)
- Turkish characters FORBIDDEN (ASCII)
- Reserved names rejected

OUTPUT: naming_review_report.md
```

---

## 5. Common Errors AI Finds

- Out-of-format tag (Motor1, motor_1, MOTOR-1)
- ParamName prefix missing (StartCmd → in_bStartCmd)
- Type prefix wrong (stat_MotorRunning → stat_bMotorRunning)
- F-prefix misuse (a normal tag starting with F_*)
- Turkish character (motör → motor)
- Reserved name (M10, T1, DB1 — vendor reserved)
- Broken cross-ref (LinkedAlarm not in RD08)

---

## 6. Related Files

- **Standard:** `01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md`
- **Specs:** `MDSCHEMA_RAWDATA_01_IO.md`, `_02_DATADICT.md`, `_10_FBSPEC.md`
- **Validator:** `05_SCRIPTS/dev/script_consistency_check.py --check-naming`
- **Pipeline:** Gate 3 HUMAN REVIEW

---

*v1.1.0 — Full English body (2026-05-23). Naming review = the project's "readability check". An out-of-standard tag = field nightmare.*
