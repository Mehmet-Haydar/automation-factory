# RD14_Modernization — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_14_MODERNIZATION.md`. Schema: `rd14_modernization.schema.json`.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <Engineer Name>
filled_at: <YYYY-MM-DD>
customer_decision: <RETROFIT | GREENFIELD | HYBRID | PENDING>
status: <IDENTIFIED | PLANNED | IN_PROGRESS | IMPLEMENTED | VERIFIED>
```

---

## Summary (SummaryByCategory)

| Category | CRITICAL | MAJOR | MINOR | INFO | Total | Estimated Effort (hours) | TopPriority |
|----------|----------|-------|-------|------|-------|---------------------------|-------------|
| NAMING | 0 | 1 | 5 | 2 | 8 | 12 | FND001 |
| STRUCTURE | 0 | 2 | 1 | 0 | 3 | 40 | FND003 |
| SAFETY | 1 | 0 | 0 | 0 | 1 | 80 | FND002 |
| ALARM | 0 | 1 | 2 | 0 | 3 | 16 | FND020 |
| COMMUNICATION | 0 | 1 | 0 | 0 | 1 | 4 | FND030 |
| OBSOLETE_PLATFORM | 0 | 2 | 0 | 0 | 2 | 24 | FND040 |
| **TOTAL** | **1** | **7** | **8** | **2** | **18** | **176** | |

---

## Modernization Decision (ModernizationDecision)

| Option | Applicable Findings | Total Effort | Recommendation | Rationale |
|--------|---------------------|--------------|----------------|-----------|
| RETROFIT | 16 | HIGH | ACCEPTABLE | NAMING and STRUCTURE findings can be resolved via retrofit; adding an F-PLC is required for SAFETY. |
| GREENFIELD | 18 | VERY_HIGH | RECOMMENDED | OBSOLETE_PLATFORM findings are very high; hardware renewal is already required. |
| HYBRID | 17 | HIGH | NOT_RECOMMENDED | A hybrid approach incurs double cost. |

---

## Findings

### FND001 — Absolute Address Usage (NAMING / MAJOR)

- **Category:** NAMING
- **Severity:** MAJOR
- **Priority:** 1
- **PLCPlatform:** S7_300
- **BlockRef:** OB1, FC10, FC20
- **AnnotationRef:** ANN0001, ANN0005, ANN0012

**Anti-Pattern:**
> All I/O and memory bits used with absolute addresses (I0.0, Q0.1, MW100). 47 distinct absolute addresses. Address ↔ function mapping is impossible during maintenance.

**Modern Alternative:**
> Rename all tags per GLOBAL_NAMING_STANDARD. Use meaningful names via the TIA Symbol Table.

- **Effort:** MEDIUM (~12 hours)
- **Impact:** MULTIPLE — MAINTAINABILITY, RELIABILITY, COMPLIANCE
- **Standard:** GLOBAL_NAMING_STANDARD v1.0
- **LinkedRD:** RD01, RD02
- **Retrofit:** YES | **Greenfield:** YES
- **AutoFixable:** PARTIAL — find-replace after RD01 IO List
- **VerificationRequired:** FUNCTIONAL_TEST
- **Status:** IDENTIFIED

### FND002 — E-Stop on Standard PLC (SAFETY / CRITICAL) 🛑

- **Category:** SAFETY
- **Severity:** CRITICAL
- **Priority:** 2
- **PLCPlatform:** S7_300

**Anti-Pattern:**
> Emergency stop is controlled via a standard Q output (no F-PLC). A single fault can disable the E-Stop.

**Modern Alternative:**
> F-CPU (S7-1500F) + F-FB + F-DI/DO modules. SIMATIC Safety block (F_ESTOP1).

- **Effort:** HIGH (80-160 hours + hardware cost)
- **Impact:** SAFETY
- **Standard:** IEC 62061, ISO 13849-1, IEC 61508
- **LinkedRD:** RD05
- **Retrofit:** YES | **Greenfield:** YES
- **AutoFixable:** NO
- **VerificationRequired:** SAFETY_ENGINEER
- **Status:** IDENTIFIED

---

## #UNKNOWNS

| Finding | Reason |
|---------|--------|
| | |

---

## Fill-in Notes

- **FindingID format:** `^FND\d{3}$`
- **Category enum:** NAMING/STRUCTURE/SAFETY/PERFORMANCE/MAINTAINABILITY/COMMUNICATION/HMI/ALARM/MOTION/DATA_MANAGEMENT/DIAGNOSTICS/COMPLIANCE/OBSOLETE_PLATFORM/REDUNDANCY
- **Severity enum:** CRITICAL/MAJOR/MINOR/INFO
- **Priority 1-99 UNIQUE** (1 = highest)
- **AntiPattern + ModernAlternative min 20 chars**
- **Category=SAFETY → VerificationRequired ≠ NONE** (conditional, at minimum FUNCTIONAL_TEST or SAFETY_ENGINEER)
- **Impact=MULTIPLE → ImpactDetail MANDATORY**
- **AutoFixable ≠ NO → AutoFixNote MANDATORY**
- **ModernizationDecision 3 rows** (RETROFIT/GREENFIELD/HYBRID)

---

*Template v1.1.0 — RD14 Modernization Report. Retrofit/Greenfield decision matrix. Full English body (2026-05-23).*
