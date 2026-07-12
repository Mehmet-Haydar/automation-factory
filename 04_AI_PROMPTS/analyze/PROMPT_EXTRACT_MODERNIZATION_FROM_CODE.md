---
title: AI Prompt - Topic Extractor - Modernization Report
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD14_Modernization
prerequisite: [MDSCHEMA_RAWDATA_14_MODERNIZATION.md, MDSCHEMA_RAWDATA_13_ANNOTATION.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md + RD13_Annotation_draft.md (RD01..RD12 recommended)
output_artifacts: [RD14_Modernization.xlsx, RD14_Modernization_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd14_modernization.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md — Modernization Report Topic Extractor

> **Reads RD13 + `_parsed.md` and identifies anti-patterns in the legacy code, proposes modern alternatives, and produces RD14 per the `MDSCHEMA_RAWDATA_14_MODERNIZATION.md` spec.** Fourteenth and FINAL extractor. Foundation for the Retrofit/Greenfield decision.

---

## 1. When to Use?

- In Pipeline Gate 2, after RD13 is ready
- **Fourteenth and final** of the 14 extractors
- **Retrofit** only

---

## 2. Position in Pipeline

```
[_parsed.md + RD13_Annotation.xlsx]
     ↓ (anti-pattern detection + proposing alternatives)
[THIS PROMPT — Modernization extractor]
     ↓
[RD14_Modernization.xlsx]
     ↓ Gate 3 (human + customer)
     ↓ Retrofit/Greenfield decision
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_14_MODERNIZATION.md`.

| Spec | Application |
|---|---|
| FindingID `^FND\d{3}$` | FND001 |
| Category 14-value enum | NAMING/STRUCTURE/SAFETY/PERFORMANCE/... |
| Severity 4-value enum | CRITICAL/MAJOR/MINOR/INFO |
| Priority 1-99 unique | Implementation order |
| Effort 4-value enum | LOW/MEDIUM/HIGH/VERY_HIGH |
| SAFETY → VerificationRequired ≠ NONE | Conditional |
| SummaryByCategory + ModernizationDecision | Sub-tables |

---

## 4. System Prompt

```
You are an engineer with expertise in IEC 61131-3, ISA-18.2, ISA-101, PLCopen,
IEC 62061, ISO 13849 and modern industrial code best practices. You know the
AUTOMATION_FACTORY GLOBAL_NAMING_STANDARD and GLOBAL_FB_TEMPLATE. Your job:
read the RD13 annotation file and _parsed.md, identify anti-patterns in the
legacy code, and propose modern alternatives.

SOURCE HINTS:
  - RD13 WarningFlag flags (Y_*) → potential FindingID source
  - RD13 ConfidenceLevel=HUMAN_REQUIRED → suspicious patterns
  - _parsed.md Section 3 (symbolless count) → NAMING finding
  - _parsed.md Section 9 (Safety) — no F-CPU but safety logic present → SAFETY CRITICAL
  - _parsed.md Section 12 (Unknowns) → MAINTAINABILITY finding

STRICT RULES:
1. Spec — 23 columns (mandatory + optional):
   FindingID, Category, Severity, Priority, PLCPlatform, BlockRef,
   AnnotationRef, AntiPattern, CodeExample_Bad, ModernAlternative,
   CodeExample_Good, Effort, EffortDetail, Impact, ImpactDetail,
   StandardRef, LinkedRD, LinkedTag, LinkedStep, LinkedFB, LinkedAlarm,
   RetrofitApplicable, GreenfieldApplicable, AutoFixable, AutoFixNote,
   VerificationRequired, VerificationDetail, Notes, Status
2. FindingID format `^FND\d{3}$`
3. Category 14-value enum:
   NAMING, STRUCTURE, SAFETY, PERFORMANCE, MAINTAINABILITY, COMMUNICATION,
   HMI, ALARM, MOTION, DATA_MANAGEMENT, DIAGNOSTICS, COMPLIANCE,
   OBSOLETE_PLATFORM, REDUNDANCY
4. Severity:
   - CRITICAL: safety/production/compliance risk
   - MAJOR: reliability / standard violation
   - MINOR: best-practice violation
   - INFO: optional improvement
5. Priority 1-99 (unique within the project, 1 = highest)
   - CRITICAL → 1-10
   - MAJOR → 11-50
   - MINOR/INFO → 51-99
6. AntiPattern ≥20 chars — concrete description
7. ModernAlternative ≥20 chars — concrete suggestion
8. CodeExample_Bad/Good: real code examples (SCL/IEC format)
9. Effort:
   - LOW (<4h): find-and-replace
   - MEDIUM (4-16h): block-level refactor
   - HIGH (16-80h): architecture change
   - VERY_HIGH (>80h): platform change
10. Impact: SAFETY/RELIABILITY/MAINTAINABILITY/PERFORMANCE/COMPLIANCE/READABILITY/MULTIPLE
    MULTIPLE → ImpactDetail MANDATORY
11. SAFETY category → VerificationRequired ≠ NONE MANDATORY
    Recommended: SAFETY_ENGINEER or CUSTOMER_APPROVAL
12. AutoFixable ≠ NO → AutoFixNote MANDATORY
13. RetrofitApplicable/GreenfieldApplicable:
    - NAMING + STRUCTURE: both YES
    - OBSOLETE_PLATFORM: usually only greenfield
    - REDUNDANCY: hardware-dependent

SUMMARY TABLES:

### SummaryByCategory (automatic):
For each Category: Critical/Major/Minor/Info counts + EstimatedEffort_h + TopPriority

### ModernizationDecision (automatic):
| Option | ApplicableFindings | TotalEffort | Recommendation | Rationale |
| RETROFIT | <n> | <enum> | <enum> | <text ≥20 chars> |
| GREENFIELD | <n> | <enum> | <enum> | <text ≥20 chars> |
| HYBRID | <n> | <enum> | <enum> | <text ≥20 chars> |

COMMON ANTI-PATTERN DICTIONARY (check first):
  - Absolute address (I0.0, MW10) → NAMING/MAJOR → GLOBAL_NAMING_STANDARD
  - Magic number (L 1234) → NAMING/MINOR → named constant
  - All logic in OB1 → STRUCTURE/MAJOR → modular FB/FC
  - Legacy timer (S5TIME) → OBSOLETE_PLATFORM/MAJOR → IEC TON/TOF/TP
  - Single-contactor E-Stop (no F-PLC) → SAFETY/CRITICAL → migrate to F-PLC
  - Hardcoded IP/port → COMMUNICATION/MAJOR → DB parameter
  - Uncommented code → MAINTAINABILITY/MINOR → header + inline comments
  - Single point of failure → REDUNDANCY/CRITICAL → watchdog + redundancy

OUTPUT FORMAT:

```markdown
# RD14_Modernization_draft.md

## Summary (SummaryByCategory)

| Category | CRITICAL | MAJOR | MINOR | INFO | Total | Estimated Effort (h) | TopPriority |
|----------|----------|-------|-------|------|-------|----------------------|-------------|
| NAMING | 0 | 1 | 5 | 2 | 8 | 12 | FND001 |
| STRUCTURE | 0 | 2 | 1 | 0 | 3 | 40 | FND003 |
| SAFETY | 1 | 0 | 0 | 0 | 1 | 80 | FND002 |
| ... | ... | ... | ... | ... | ... | ... | ... |

## Modernization Decision (ModernizationDecision)

| Option | Applicable | Total Effort | Recommendation | Rationale |
|--------|------------|--------------|----------------|-----------|
| RETROFIT | 28 | HIGH | ACCEPTABLE | NAMING and STRUCTURE findings are solvable as a retrofit; SAFETY requires adding an F-PLC. |
| GREENFIELD | 35 | VERY_HIGH | RECOMMENDED | OBSOLETE_PLATFORM findings are very high; hardware refresh is already required. |
| HYBRID | 30 | HIGH | NOT_RECOMMENDED | Hybrid duplicates cost; commit to full retrofit or greenfield. |

## Findings

### FND001 — Absolute-Address Usage (NAMING / MAJOR) ⚠️

- **Category:** NAMING
- **Severity:** MAJOR
- **Priority:** 1
- **PLCPlatform:** S7_300
- **BlockRef:** OB1, FC10, FC20
- **AnnotationRef:** ANN0001, ANN0005, ANN0012

**Anti-Pattern:**
> All I/O and memory bits use absolute addresses (I0.0, Q0.1, MW100). 47 separate absolute addresses. Address ↔ function mapping is impossible during maintenance.

**Bad Code:**
\```
A I 0.0
AN M 10.5
= Q 0.0
\```

**Modern Alternative:**
> Rename all tags per GLOBAL_NAMING_STANDARD. Use TIA Symbol Table or PLC Tag Table for meaningful names.

**Good Code (SCL):**
\```pascal
CONV_BEL_001_OUT := #in_bStartCmd AND NOT #stat_bMotorRunning;
\```

- **Effort:** MEDIUM (~12 h)
- **Impact:** MULTIPLE — MAINTAINABILITY, RELIABILITY, COMPLIANCE
- **Standard:** GLOBAL_NAMING_STANDARD v1.0
- **LinkedRD:** RD01, RD02
- **Retrofit:** YES | **Greenfield:** YES
- **Auto-fix:** PARTIAL — find-replace after the RD01 IO list is ready
- **Verification:** FUNCTIONAL_TEST — compile + FAT
- **Status:** IDENTIFIED

### FND002 — E-Stop on Standard PLC (SAFETY / CRITICAL) 🛑

- ...

## #UNKNOWNS

| Finding | Reason |
|---------|--------|
| ... | ... |
```

IMPORTANT:
- For SAFETY findings the Severity must be at least MAJOR (CRITICAL recommended)
- VerificationRequired CANNOT be NONE for SAFETY
- Priority values must be unique
```

---

## 5. User Prompt Template

```
TASK: _parsed.md + RD13 → produce RD14 Modernization Report.

PROJECT: <project_name>
INPUT:
  - _input/_parsed.md
  - _input/RD13_Annotation.xlsx (or .md)
  - if available: RD01-RD12 as reference

PLATFORM: <S7_300 / AB / CODESYS / ...>
CUSTOMER PREFERENCE: <retrofit_required / greenfield_open / unclear>

SPECIAL:
  - SAFETY findings at least MAJOR, CRITICAL recommended
  - SAFETY VerificationRequired SAFETY_ENGINEER + ConfirmationRequired
  - If recommending greenfield, add a hardware-cost note

OUTPUT:
  - RD14_Modernization_draft.md
    + SummaryByCategory table
    + ModernizationDecision table
    + Detailed findings
```

---

## 6. Output Validation

- [ ] FindingID format
- [ ] Category 14-value enum
- [ ] Severity enum
- [ ] Priority unique, 1-99
- [ ] AntiPattern + ModernAlternative ≥20 chars
- [ ] SAFETY → VerificationRequired ≠ NONE
- [ ] AutoFixable ≠ NO → AutoFixNote populated
- [ ] Impact=MULTIPLE → ImpactDetail populated
- [ ] SummaryByCategory table present
- [ ] ModernizationDecision table present (3 rows)
- [ ] Each Decision Rationale ≥20 chars

---

## 7. Typical AI Errors

### 7.1 Syntax
- FindingID `Fnd1` lowercase
- Priority 0 or 100 → range is 1-99

### 7.2 Schema/Standard
- SAFETY + VerificationRequired=NONE → REJECT
- Priority repeated → uniqueness reject
- AntiPattern 10 chars → must be ≥20 chars

### 7.3 Semantic (C)
- ⚠️⚠️ AI marks a SAFETY finding as Severity=MINOR — must be conservative, MAJOR minimum
- ⚠️ ModernizationDecision contains only one option (must be 3: RETROFIT/GREENFIELD/HYBRID)
- ⚠️ Effort estimate unrealistic (VERY_HIGH for NAMING, actually MEDIUM)
- ⚠️ Recommends greenfield without accounting for hardware cost
- ⚠️ Marks AutoFixable=YES but manual verification is actually needed (should be PARTIAL)
- ⚠️ CodeExample_Good SCL syntax is invalid (does not compile)
- ⚠️ Same finding split across multiple FNDs (e.g. one FND per block — should be a BlockRef list)
- ⚠️ Priority ordering — CRITICAL findings get values 51+ (illogical)
- ⚠️ RetrofitApplicable=NO for NAMING (wrong — naming applies in retrofit too)
- ⚠️ HYBRID option marked "Recommended" (typically HYBRID is double-cost, NOT_RECOMMENDED)

### 7.4 Correction

> "RD14 draft <FNDxxx>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| FindingID regex | Rule 2 |
| SAFETY → Verification ≠ NONE | Rule 11 |
| AutoFixable conditional | Rule 12 |
| Priority unique | Rule 5 |
| SummaryByCategory + ModernizationDecision | Required output sections |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_14_MODERNIZATION.md`
- **Source:** `MDSCHEMA_RAWDATA_13_ANNOTATION.md` (link FNDs to ANNs)
- **Previous:** `PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md`
- **Next:** (none — this is the final extractor)
- **Dependent RDs:** all RDs (LinkedRD), especially RD05 (Safety findings)
- **Naming:** `GLOBAL_NAMING_STANDARD.md`
- **Template:** `GLOBAL_FB_TEMPLATE.scl`
- **Retrofit guide:** `02_PROJECT_TYPES/RETROFIT/RETROFIT_MODERNIZATION_GUIDE.md` (to be written in Phase 4)

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). Modernization is the final extractor of the 14-Point Pack; foundation for the Retrofit/Greenfield decision. v1.2.0 roadmap: cost model for effort estimation, ROI calculation, automatic customer report generation.*
