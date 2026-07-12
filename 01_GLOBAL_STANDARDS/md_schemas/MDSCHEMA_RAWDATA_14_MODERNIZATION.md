---
title: MDSCHEMA_RAWDATA_14_MODERNIZATION — Modernization Report
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
---

# MDSCHEMA_RAWDATA_14_MODERNIZATION — Modernization Report

---

## 0. File Identity

| Field | Value |
|------|-------|
| Schema name | MDSCHEMA_RAWDATA_14_MODERNIZATION |
| Version | 1.1.0 |
| Status | ACTIVE |
| Created | 2026-05-15 |
| Last updated | 2026-05-23 |
| Author | AUTOMATION_FACTORY AI Engine |
| Document language | EN |
| RD point | RD14 — Modernization Report |
| Dependencies | RD01–RD13 (all) |

---

## 1. Purpose and Scope

This schema documents the anti-patterns, technical debt and improvement opportunities found in legacy PLC projects. Each record covers the issue, the modern industrial alternative, the implementation effort and the related standard.

**RD14's role:**
- Determine the modernization priorities of the legacy code
- Give the engineer a "where, how much effort" summary
- Steer which patterns are used during AI code generation (Gate 5)
- Feed the customer's technical report (German standards CE/TÜV)
- Provide data for the Retrofit vs Greenfield decision

**Out of scope:**
- New-project design decisions (covered by RD10 FB Spec + RD03 Flowchart)
- Safety non-compliance reports (RD05 Safety covers them — different approval flow)
- Hardware/electrical issues (covered by the project's mechanical/electrical documents)

---

## 2. Column Definitions

### 2A. Main Table: FindingList

| Column | Type | Required | Description |
|-------|-----|---------|----------|
| FindingID | STRING | YES | Unique finding id. Format: `^FND\d{3}$`. Example: `FND001` |
| Category | ENUM | YES | Finding category. See §2B |
| Severity | ENUM | YES | `CRITICAL` / `MAJOR` / `MINOR` / `INFO` |
| Priority | INT | YES | Implementation priority. 1=highest, 99=lowest. Must be unique within the project. |
| PLCPlatform | ENUM | YES | `S5` / `S7_300` / `S7_400` / `S7_1200` / `S7_1500` / `AB_L5X` / `CODESYS` / `Other` / `ALL` |
| BlockRef | STRING | NO | Related legacy code block. Example: `FC10`, `OB35`, `DB1` |
| AnnotationRef | STRING | NO | Related RD13 ANN record. Example: `ANN0001, ANN0005` |
| AntiPattern | TEXT | YES | Description of the detected issue. Min 20 characters. |
| CodeExample_Bad | TEXT | NO | Problematic legacy code example. |
| ModernAlternative | TEXT | YES | Proposed modern alternative and rationale. Min 20 characters. |
| CodeExample_Good | TEXT | NO | Proposed modern code example (SCL/IEC 61131-3 format). |
| Effort | ENUM | YES | `LOW` / `MEDIUM` / `HIGH` / `VERY_HIGH` |
| EffortDetail | TEXT | NO | Effort description. Estimated hours or impact area. |
| Impact | ENUM | YES | `SAFETY` / `RELIABILITY` / `MAINTAINABILITY` / `PERFORMANCE` / `COMPLIANCE` / `READABILITY` / `MULTIPLE` |
| ImpactDetail | TEXT | CONDITIONAL | MANDATORY when Impact=MULTIPLE. List the impact areas. |
| StandardRef | STRING | NO | Related standard. Example: `IEC 61131-3 §2.5`, `ISA-18.2` |
| LinkedRD | STRING | NO | Related RD points. Comma-separated. |
| LinkedTag | STRING | NO | Related RD01 tag. |
| LinkedStep | STRING | NO | Related RD03 StepID. |
| LinkedFB | STRING | NO | New FB name to be used after modernization (RD10). |
| LinkedAlarm | STRING | NO | Related RD08 AlarmID. |
| RetrofitApplicable | ENUM | YES | `YES` / `NO` / `PARTIAL` — Applicable in a retrofit scenario? |
| GreenfieldApplicable | ENUM | YES | `YES` / `NO` — Applicable in a greenfield scenario? |
| AutoFixable | ENUM | YES | `YES` / `NO` / `PARTIAL` — Can AI/tools apply it automatically? |
| AutoFixNote | TEXT | CONDITIONAL | MANDATORY when AutoFixable ≠ NO. Describe the automation approach. |
| VerificationRequired | ENUM | YES | `NONE` / `FUNCTIONAL_TEST` / `SAFETY_ENGINEER` / `CUSTOMER_APPROVAL` |
| VerificationDetail | TEXT | CONDITIONAL | MANDATORY when VerificationRequired ≠ NONE. What verification is required? |
| Notes | TEXT | NO | Free-text notes. |
| Status | ENUM | YES | `IDENTIFIED` / `PLANNED` / `IN_PROGRESS` / `IMPLEMENTED` / `VERIFIED` / `DEFERRED` / `WONT_FIX` |

### 2B. Category Enumeration

| Value | Description |
|-------|----------|
| `NAMING` | Variable, block, label naming issues (unnamed addresses, unclear names) |
| `STRUCTURE` | Code structure issues (lack of modularity, spaghetti code, one giant OB) |
| `SAFETY` | Safety logic issues (F-block usage, disabling safety) |
| `PERFORMANCE` | Performance issues (unnecessary scan load, inefficient loops) |
| `MAINTAINABILITY` | Maintenance issues (uncommented code, complex logic, untestable structure) |
| `COMMUNICATION` | Communication issues (legacy protocol, hardcoded address, no error handling) |
| `HMI` | HMI integration issues (ISA-101 non-compliance, missing access control) |
| `ALARM` | Alarm management issues (ISA-18.2 non-compliance, nuisance alarms, too many/few alarms) |
| `MOTION` | Motion control issues (PLCopen non-compliance, missing ramp control) |
| `DATA_MANAGEMENT` | Data management issues (wrong Retain, no backup, variable collision) |
| `DIAGNOSTICS` | Diagnostic issues (no error code, no logging) |
| `COMPLIANCE` | Standard compliance issues (CE, TÜV, industry standard) |
| `OBSOLETE_PLATFORM` | Platform obsolescence (hardware end-of-life, spare-parts issue) |
| `REDUNDANCY` | Redundancy issues (single point of failure, no SCADA backup) |

### 2C. Summary Table: SummaryByCategory

Summary table generated at the end of the report:

| Column | Type | Description |
|-------|-----|----------|
| Category | ENUM | Category from above |
| CriticalCount | INT | CRITICAL severity count |
| MajorCount | INT | MAJOR severity count |
| MinorCount | INT | MINOR severity count |
| InfoCount | INT | INFO severity count |
| TotalCount | INT | Total finding count |
| EstimatedEffort_h | FLOAT | Estimated total effort (hours) |
| TopPriority | STRING | Highest-priority FindingID |

### 2D. Summary Table: ModernizationDecision

Retrofit vs Greenfield decision matrix:

| Column | Type | Description |
|-------|-----|----------|
| Option | ENUM | `RETROFIT` / `GREENFIELD` / `HYBRID` |
| ApplicableFindings | INT | Number of findings applicable in this scenario |
| TotalEffort | ENUM | Total estimated effort class |
| Recommendation | ENUM | `RECOMMENDED` / `ACCEPTABLE` / `NOT_RECOMMENDED` |
| Rationale | TEXT | Rationale for the decision |

---

## 3. JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "MDSCHEMA_RAWDATA_14_MODERNIZATION",
  "title": "RD14 — Modernization Report",
  "type": "object",
  "properties": {
    "FindingList": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": [
          "FindingID", "Category", "Severity", "Priority",
          "PLCPlatform", "AntiPattern", "ModernAlternative",
          "Effort", "Impact", "RetrofitApplicable",
          "GreenfieldApplicable", "AutoFixable", "VerificationRequired", "Status"
        ],
        "properties": {
          "FindingID": {
            "type": "string",
            "pattern": "^FND\\d{3}$"
          },
          "Category": {
            "type": "string",
            "enum": [
              "NAMING", "STRUCTURE", "SAFETY", "PERFORMANCE",
              "MAINTAINABILITY", "COMMUNICATION", "HMI",
              "ALARM", "MOTION", "DATA_MANAGEMENT",
              "DIAGNOSTICS", "COMPLIANCE", "OBSOLETE_PLATFORM", "REDUNDANCY"
            ]
          },
          "Severity": {
            "type": "string",
            "enum": ["CRITICAL", "MAJOR", "MINOR", "INFO"]
          },
          "Priority": {
            "type": "integer",
            "minimum": 1,
            "maximum": 99
          },
          "PLCPlatform": {
            "type": "string",
            "enum": ["S5", "S7_300", "S7_400", "S7_1200", "S7_1500", "AB_L5X", "CODESYS", "Other", "ALL"]
          },
          "BlockRef": { "type": "string" },
          "AnnotationRef": { "type": "string" },
          "AntiPattern": {
            "type": "string",
            "minLength": 20
          },
          "CodeExample_Bad": { "type": "string" },
          "ModernAlternative": {
            "type": "string",
            "minLength": 20
          },
          "CodeExample_Good": { "type": "string" },
          "Effort": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
          },
          "EffortDetail": { "type": "string" },
          "Impact": {
            "type": "string",
            "enum": [
              "SAFETY", "RELIABILITY", "MAINTAINABILITY",
              "PERFORMANCE", "COMPLIANCE", "READABILITY", "MULTIPLE"
            ]
          },
          "StandardRef": { "type": "string" },
          "LinkedRD": { "type": "string" },
          "LinkedTag": { "type": "string" },
          "LinkedStep": {
            "type": "string",
            "pattern": "^S\\d{3}[A-Z]?$"
          },
          "LinkedFB": { "type": "string" },
          "LinkedAlarm": { "type": "string" },
          "RetrofitApplicable": {
            "type": "string",
            "enum": ["YES", "NO", "PARTIAL"]
          },
          "GreenfieldApplicable": {
            "type": "string",
            "enum": ["YES", "NO"]
          },
          "AutoFixable": {
            "type": "string",
            "enum": ["YES", "NO", "PARTIAL"]
          },
          "VerificationRequired": {
            "type": "string",
            "enum": ["NONE", "FUNCTIONAL_TEST", "SAFETY_ENGINEER", "CUSTOMER_APPROVAL"]
          },
          "Notes": { "type": "string" },
          "Status": {
            "type": "string",
            "enum": ["IDENTIFIED", "PLANNED", "IN_PROGRESS", "IMPLEMENTED", "VERIFIED", "DEFERRED", "WONT_FIX"]
          }
        },
        "allOf": [
          {
            "if": {
              "properties": { "Impact": { "const": "MULTIPLE" } }
            },
            "then": {
              "required": ["ImpactDetail"],
              "properties": {
                "ImpactDetail": { "type": "string", "minLength": 10 }
              }
            }
          },
          {
            "if": {
              "properties": { "AutoFixable": { "not": { "const": "NO" } } }
            },
            "then": {
              "required": ["AutoFixNote"],
              "properties": {
                "AutoFixNote": { "type": "string", "minLength": 10 }
              }
            }
          },
          {
            "if": {
              "properties": { "VerificationRequired": { "not": { "const": "NONE" } } }
            },
            "then": {
              "required": ["VerificationDetail"],
              "properties": {
                "VerificationDetail": { "type": "string", "minLength": 10 }
              }
            }
          }
        ],
        "additionalProperties": false
      }
    },
    "SummaryByCategory": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["Category", "CriticalCount", "MajorCount", "MinorCount", "InfoCount", "TotalCount"],
        "properties": {
          "Category": { "type": "string" },
          "CriticalCount": { "type": "integer", "minimum": 0 },
          "MajorCount": { "type": "integer", "minimum": 0 },
          "MinorCount": { "type": "integer", "minimum": 0 },
          "InfoCount": { "type": "integer", "minimum": 0 },
          "TotalCount": { "type": "integer", "minimum": 0 },
          "EstimatedEffort_h": { "type": "number", "minimum": 0 },
          "TopPriority": { "type": "string", "pattern": "^FND\\d{3}$" }
        }
      }
    },
    "ModernizationDecision": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["Option", "ApplicableFindings", "TotalEffort", "Recommendation", "Rationale"],
        "properties": {
          "Option": {
            "type": "string",
            "enum": ["RETROFIT", "GREENFIELD", "HYBRID"]
          },
          "ApplicableFindings": { "type": "integer", "minimum": 0 },
          "TotalEffort": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
          },
          "Recommendation": {
            "type": "string",
            "enum": ["RECOMMENDED", "ACCEPTABLE", "NOT_RECOMMENDED"]
          },
          "Rationale": { "type": "string", "minLength": 20 }
        }
      }
    }
  },
  "required": ["FindingList"]
}
```

---

## 4. Markdown Output Format

```markdown
# RD14 — Modernization Report | [PROJECT_NAME]

**Platform:** [PLCPlatform] | **Analysis date:** [DATE] | **Total findings:** [N]

---

## Summary: Distribution by Category

| Category | CRITICAL | MAJOR | MINOR | INFO | Total | Estimated Effort |
|----------|----------|-------|-------|------|-------|------------------|
| NAMING | 0 | 3 | 5 | 2 | 10 | 8 h |
| ...      | ...      | ...   | ...   | ...  | ...   | ...              |

## Decision Matrix: Retrofit vs Greenfield

| Option | Applicable Findings | Effort | Recommendation |
|--------|---------------------|--------|----------------|
| RETROFIT | 28 | HIGH | ACCEPTABLE |
| GREENFIELD | 35 | VERY_HIGH | RECOMMENDED |

---

## Findings

### FND001 — [AntiPattern title] ⛔ CRITICAL

**Category:** [Category] | **Effort:** [Effort] | **Impact:** [Impact]
**Block:** [BlockRef] | **Annotation:** [AnnotationRef]

**Anti-Pattern:**
> [AntiPattern]

**Bad Example:**
\```
[CodeExample_Bad]
\```

**Modern Alternative:**
> [ModernAlternative]

**Good Example (SCL):**
\```pascal
[CodeExample_Good]
\```

**Standard:** [StandardRef]
**Verification:** [VerificationRequired] — [VerificationDetail]
**Automation:** [AutoFixable] — [AutoFixNote]

---
```

---

## 5. AI Filling Instructions

### 5.1 General Principles

```
RD14 — MODERNIZATION FILLING RULES

[MANDATORY]
- Write a concrete, applicable ModernAlternative for each finding.
- CodeExample_Good: real SCL code or an example in IEC 61131-3 format.
- Be conservative when choosing Severity: when in doubt, pick the higher level.
- Priority: 1=most critical, ordered consistently with other findings in the project.

[FORBIDDEN]
- Lowering the Severity of safety findings on AI's own initiative.
- Writing VerificationRequired=NONE when the category is SAFETY.
- Writing GreenfieldApplicable=NO for NAMING and STRUCTURE
  (every greenfield project requires standard naming).
- Writing CodeExample_Bad based on assumptions — use only the real code from RD13.

[PERFORMANCE]
- If the same anti-pattern appears in multiple blocks: single FND record + list all in BlockRef.
- List the NAMING category first — it's the first fix during code generation.
- Recommendation: Severity=CRITICAL findings should sit in Priority 1-10.
```

### 5.2 Severity Guide

| Severity | When to use |
|----------|----------------|
| `CRITICAL` | Safety risk, data loss, production stop, non-compliance (CE/TÜV) |
| `MAJOR` | Reliability issue, significant maintenance pain, standard violation |
| `MINOR` | Readability, small best-practice violation, improvement opportunity |
| `INFO` | Informational note, optional improvement |

### 5.3 Effort Guide

| Effort | Estimated effort |
|--------|-------------|
| `LOW` | < 4 hours — find-and-replace or simple rename |
| `MEDIUM` | 4-16 hours — block refactor, change requiring tests |
| `HIGH` | 16-80 hours — architectural change, new FB design, extensive testing |
| `VERY_HIGH` | > 80 hours — platform change, full system redesign |

### 5.4 Common Anti-Pattern Dictionary

| Anti-Pattern | Category | Severity | ModernAlternative |
|-------------|----------|----------|-------------------|
| Absolute address (I0.0, Q0.0, MW10) | NAMING | MAJOR | GLOBAL_NAMING_STANDARD tag names |
| Magic number (L 1234 undocumented) | NAMING | MINOR | Named constant / DB parameter |
| All logic in a single OB1 | STRUCTURE | MAJOR | Modular FB/FC structure |
| S5Timer instead of IEC timer | OBSOLETE_PLATFORM | MAJOR | TON/TOF/TP/TONR (IEC 61131-3) |
| UC (unconditional call) instead of CALL | STRUCTURE | MINOR | Conditional call, enable input |
| No alarm / fixed Q output | ALARM | MAJOR | ISA-18.2 alarm system |
| Hardcoded IP (e.g., Modbus) | COMMUNICATION | MAJOR | DB parameter or HMI configuration |
| Wrong Retain variables | DATA_MANAGEMENT | MAJOR | Retain only for the truly necessary variables |
| Uncommented code, no names | MAINTAINABILITY | MINOR | Descriptive names + brief comment |
| Repeated analog linear scaling | PERFORMANCE | MINOR | SCALE_X / FC math library |
| Manual bit manipulation | PERFORMANCE | MINOR | Bit mapping via Struct/UDT |
| PROFIBUS instead of Ethernet | OBSOLETE_PLATFORM | MAJOR | PROFINET IRT / EtherCAT |
| Safety bypass logic | SAFETY | CRITICAL | F-PLC + TIA Safety block |
| Single point of failure | REDUNDANCY | CRITICAL | Redundant PLC / watchdog |

---

## 6. Error Taxonomy

### Category A — Syntax Errors (Auto-detectable)

| Code | Error | Fix |
|-----|------|-------|
| `A14-001` | FindingID format invalid (expects `FND001`) | apply pattern `^FND\d{3}$` |
| `A14-002` | Priority outside 1-99 range | correct the value |
| `A14-003` | LinkedStep format invalid | apply `^S\d{3}[A-Z]?$` |
| `A14-004` | SummaryByCategory TotalCount inconsistent | CriticalCount+MajorCount+MinorCount+InfoCount = TotalCount |

### Category B — Schema / Standard Errors (Validator-detected)

| Code | Error | Fix |
|-----|------|-------|
| `B14-001` | Impact=MULTIPLE but ImpactDetail missing | add ImpactDetail |
| `B14-002` | AutoFixable ≠ NO but AutoFixNote missing | add AutoFixNote |
| `B14-003` | VerificationRequired ≠ NONE but VerificationDetail missing | add VerificationDetail |
| `B14-004` | AntiPattern shorter than 20 characters | expand the description |
| `B14-005` | ModernAlternative shorter than 20 characters | detail the alternative |
| `B14-006` | SAFETY category but VerificationRequired=NONE | use at least FUNCTIONAL_TEST or SAFETY_ENGINEER |
| `B14-007` | Priority repeats within the project | make priorities unique |

### Category C — Semantic Errors (Manual Review)

| Code | Error | Fix |
|-----|------|-------|
| `C14-001` | Severity does not reflect reality (too low) | use CRITICAL/MAJOR for safety-impacting findings |
| `C14-002` | ModernAlternative not applicable/realistic | propose an alternative that fits the project context |
| `C14-003` | CodeExample_Good has SCL syntax error | review the code |
| `C14-004` | Same finding written as multiple FNDs | merge them; list BlockRef |
| `C14-005` | RetrofitApplicable=NO wrong (all findings are retrofit-applicable) | only platform-dependent findings may be NO |
| `C14-006` | ModernizationDecision Rationale insufficient | add concrete data supporting the decision |
| `C14-007` | Effort estimate unrealistic | calibrate against reference projects |

---

## 7. Related Files

| File | Relationship |
|-------|--------|
| `MDSCHEMA_RAWDATA_13_ANNOTATION.md` | RD13 AnnotationRef and WarningFlags feed RD14 findings |
| `MDSCHEMA_RAWDATA_01_IO_LIST.md` | Tag names in NAMING findings |
| `MDSCHEMA_RAWDATA_05_SAFETY.md` | F-FB requirements in SAFETY findings |
| `MDSCHEMA_RAWDATA_09_COMMS.md` | Protocol requirements in COMMUNICATION findings |
| `MDSCHEMA_RAWDATA_10_FBSPEC.md` | New FB design fed from STRUCTURE findings |
| `GLOBAL_NAMING_STANDARD.md` | Reference standard for NAMING-category findings |
| `GLOBAL_FB_TEMPLATE.scl` | Code template for STRUCTURE and MAINTAINABILITY |
| `05_RETROFIT_GUIDES/RETROFIT_MODERNIZATION_GUIDE.md` | Application guide for RD14 findings |
| `05_RETROFIT_GUIDES/GREENFIELD_DESIGN_TEMPLATE.md` | Design template for the greenfield scenario |
| `04_AI_PROMPTS/extract/PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md` | AI prompt that fills this schema |

---

## 8. Sample Records

### Sample 1 — NAMING MAJOR

```yaml
FindingID: FND001
Category: NAMING
Severity: MAJOR
Priority: 1
PLCPlatform: S7_300
BlockRef: "OB1, FC10, FC20"
AnnotationRef: "ANN0001, ANN0005, ANN0012"
AntiPattern: >
  All input/output and memory bits use absolute addresses (I0.0, Q0.1, MW100, etc.).
  No variable has a meaningful identifier. 47 distinct absolute addresses were detected.
  During maintenance it is impossible to tell which address does what.
CodeExample_Bad: |
  A     I      0.0
  AN    M      10.5
  =     Q      0.0
ModernAlternative: >
  Per the AUTOMATION_FACTORY GLOBAL_NAMING_STANDARD, every tag must be renamed in the
  `^[A-Z]+_[A-Z0-9]+_\d{3}$` format. Use the TIA Portal Symbol Table or PLC Tag Table
  to assign a meaningful name to each address.
CodeExample_Good: |
  // GLOBAL_NAMING_STANDARD format
  #in_bStartCmd := CONV_BEL_001;
  #stat_bMotorRunning := CONV_MOT_001_RUN;
  CONV_BEL_001_OUT := #in_bStartCmd AND NOT #stat_bMotorRunning;
Effort: MEDIUM
EffortDetail: "47 addresses × 15 min = ~12 hours. Can start after the I/O list (RD01) is complete."
Impact: MULTIPLE
ImpactDetail: "MAINTAINABILITY: maintenance becomes 60% harder. RELIABILITY: risk of wrong-address mistakes. COMPLIANCE: CE certification needs descriptive names."
StandardRef: "AUTOMATION_FACTORY GLOBAL_NAMING_STANDARD v1.0"
LinkedRD: "RD01, RD02"
RetrofitApplicable: YES
GreenfieldApplicable: YES
AutoFixable: PARTIAL
AutoFixNote: "After the RD01 IO list is complete, a find-replace script can produce the tag table. Manual verification required."
VerificationRequired: FUNCTIONAL_TEST
VerificationDetail: "After renaming, every logic block must compile and FAT tests must pass."
Status: IDENTIFIED
```

### Sample 2 — SAFETY CRITICAL

```yaml
FindingID: FND002
Category: SAFETY
Severity: CRITICAL
Priority: 2
PLCPlatform: S7_300
BlockRef: FC10
AnnotationRef: ANN0023
AntiPattern: >
  The emergency stop (E-Stop) logic is implemented through a standard PLC output bit
  Q0.7. No safety PLC (F-CPU) or safety module is used. On a single program error or
  CPU failure the E-Stop may not engage. A function that may require IEC 62061 SIL 2
  is running on a standard CPU.
CodeExample_Bad: |
  AN    I      0.3    // E-Stop button (NC contact)
  =     Q      0.7    // Conveyor contactor
ModernAlternative: >
  The E-Stop safety function must be implemented on an F-PLC (S7-1500F or ET200SP F)
  with a SIMATIC Safety block (F_ESTOP1 or equivalent), based on an IEC 62061 / ISO 13849
  risk assessment. The SIL level must be determined by a safety engineer.
  AUTOMATION_FACTORY AI NEVER guesses the SIL level.
Effort: HIGH
EffortDetail: "F-CPU procurement + Safety programming + TÜV documentation = 40-80 hours + hardware cost."
Impact: SAFETY
StandardRef: "IEC 62061, ISO 13849-1, IEC 61508-3, Machinery Directive 2006/42/EC"
LinkedRD: "RD05"
RetrofitApplicable: YES
GreenfieldApplicable: YES
AutoFixable: NO
VerificationRequired: SAFETY_ENGINEER
VerificationDetail: "A certified safety engineer must conduct a risk assessment and determine the SIL/PLr level. TÜV or equivalent accreditation may be required."
Notes: "This finding must be communicated to the customer BEFORE project approval (Gate 3)."
Status: IDENTIFIED
```

---

## 9. Version History

| Version | Date | Change |
|-------|-------|------------|
| 1.0.0 | 2026-05-15 | Initial release — 14-Point Pack RD14 |
| 1.1.0 | 2026-05-23 | Full English body (translation audit Phase 2 Tier 1b). Status enum (`IDENTIFIED/PLANNED/.../WONT_FIX`) preserved as-is — RD14 uses a workflow-specific Status, not the project-wide `Active/Inactive/Spare`. |

---

## 10. Warnings and Limitations

> **SAFETY:** Every finding with Severity=CRITICAL and Category=SAFETY must be assessed by a certified safety engineer before the project takes it into scope. RD14 is a technical analysis document, NOT a safety document.

> **DECISION AUTHORITY:** The RETROFIT/GREENFIELD recommendations in the ModernizationDecision table are AI-produced. The final project decision requires sign-off from customer + engineer + management.

> **EFFORT ESTIMATION:** Effort and EstimatedEffort_h values are indicative. The real effort depends on project complexity, engineer experience and hardware condition.

> **FRESHNESS:** RD14 findings are produced at Gate 2 EXTRACT and reviewed at Gate 3 HUMAN REVIEW. As the project progresses, the Status field must be updated; WONT_FIX decisions must be justified.

---

*v1.1.0 — Full English body (2026-05-23). 14-Point Raw Data Pack — final file. Modernization findings for legacy PLC code and the Retrofit/Greenfield decision matrix. Status enum (`IDENTIFIED/PLANNED/IN_PROGRESS/IMPLEMENTED/VERIFIED/DEFERRED/WONT_FIX`) is unique to RD14 (lifecycle-workflow oriented) — not the project-wide `Active/Inactive/Spare` set.*
