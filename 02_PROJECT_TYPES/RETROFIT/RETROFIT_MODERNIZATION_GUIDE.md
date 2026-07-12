---
title: Retrofit Modernization Guide (RD14 Implementation Workflow)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD14_Modernization
prerequisite: [MDSCHEMA_RAWDATA_14_MODERNIZATION.md, MDSCHEMA_RAWDATA_13_ANNOTATION.md, RETROFIT_EXTRACT_USECASE.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md
---

# RETROFIT_MODERNIZATION_GUIDE.md — Modernization Implementation Guide

> **Goal:** implement the anti-patterns detected in legacy PLC code (the RD14 findings) using modern industrial-code equivalents. This is the Retrofit-vs-Greenfield decision point.

---

## 1. Prerequisites

- [ ] All previous RDs RD01-RD13 complete (especially RD13 Annotation)
- [ ] **Modernization-scope discussion** held with the customer (budget + schedule)
- [ ] Hardware analysis (RETROFIT_HARDWARE_ANALYSIS.md) — new CPU/module decisions
- [ ] Safety engineer assigned (for CRITICAL findings)

---

## 2. RD14 Production Workflow

### 2.1 Two-Stage Production

RD14 is DIFFERENT from the other RDs: first it is fed from RD13, then it forms the basis for the Retrofit/Greenfield decision.

```
[RD13 Annotation (per-line warnings + confidence level)]
       ↓
[1] AI prompt: PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md
       ↓
[2] RD14_Modernization_draft.md
       ↓
[3] Engineer review + Severity revision (especially SAFETY)
       ↓
[4] SummaryByCategory + ModernizationDecision tables
       ↓
[5] Customer presentation: Retrofit / Greenfield / Hybrid decision
       ↓
[6] Approved RD14 → translated into an implementation plan
```

### 2.2 Severity Re-Evaluation

The AI assigns Severity conservatively, but the real situation can differ. Engineer review:

| AI value | Human evaluation |
|----------|------------------|
| AI: CRITICAL | Human: confirm, never lower |
| AI: MAJOR | Human: evaluate with the customer's operational impact |
| AI: MINOR | Human: may enter a cost/benefit analysis |
| AI: INFO | Human: for documentation purposes |

**SPECIAL RULE:** the AI must not lower the Severity of findings in the SAFETY category on its own initiative. Safety-engineer sign-off is mandatory.

### 2.3 ModernizationDecision Matrix

Three options must be evaluated:

| Option | When to choose |
|--------|----------------|
| **RETROFIT** | Hardware is sound, code can be fixed, customer wants minimal investment |
| **GREENFIELD** | Hardware is obsolete (no spares), many critical findings, customer wants a full replacement |
| **HYBRID** | Some modules change, some stay (e.g. F-PLC added but existing I/O cards remain) |

**Decision factors:**

| Factor | Retrofit | Greenfield | Hybrid |
|--------|----------|------------|--------|
| Budget | Low (€50K-€150K) | High (€200K+) | Medium |
| Duration | 2-3 months | 6-12 months | 4-6 months |
| Risk | Low | High (re-certification) | Medium |
| CE certificate | Stays valid | Re-issued | Per-module |
| Hardware life | Existing reused | New 15+ years | Mixed |
| Safety | F-PLC hard to add | F-PLC native | F-PLC as add-on module |

---

## 3. Anti-Pattern Dictionary and Implementation Steps

### 3.1 NAMING — Absolute-Address Problem

**Problem:** unnamed absolute addresses like %I0.0, %Q0.1, %MW100.

**Modern solution:** tag rename per GLOBAL_NAMING_STANDARD.

**Implementation steps:**

```bash
# 1. The RD01 IO List must be complete
# 2. Build a mapping table
echo "OldAddress,NewTag" > mapping.csv
echo "%I0.0,CONV_BEL_001_START" >> mapping.csv
# ... for every address

# 3. Bulk-rename via script
python 05_SCRIPTS/script_tag_rename.py \
  --source <legacy_code>/ \
  --mapping mapping.csv \
  --output <new_code>/

# 4. TIA Portal compile → conflict check
# 5. FAT test
```

**Estimated effort:** 12-40 hours (depending on project size)

### 3.2 STRUCTURE — One Giant OB1

**Problem:** all logic in a single OB1, no modularity.

**Modern solution:** OB1 → modular FB/FC structure.

**Implementation:**

```scl
// Legacy OB1 (anti-pattern)
// 5000+ lines of linear code

// New OB1 (modular)
OB1:
    "FC_IO_Read"();
    "FB_ModeMgr"(...);
    "FB_Sequence"(...);
    "FB_Motor_Pump01"(...);
    "FB_Motor_Conv01"(...);
    "FC_Alarm_Check"();
    "FC_IO_Write"();
END_OB1;
```

**Effort:** HIGH (40-80 hours) — architectural change.

### 3.3 SAFETY — E-Stop on a Standard PLC

**Problem:** emergency stop controlled via a standard Q output (no F-PLC).

**Modern solution:** F-CPU + F-FB + F-DI/DO modules.

**Implementation:**

⚠️ This finding is CRITICAL. Steps:

1. A certified safety engineer is assigned
2. Risk assessment is performed (ISO 12100, IEC 62061)
3. SIL/PLr level is determined
4. F-CPU procurement (S7-1500F or ET200SP F)
5. F-PLC programming (TIA Safety + SIMATIC Safety block)
6. TÜV/CE certification
7. FAT under safety-engineer supervision

**Effort:** HIGH (80-160 hours) + hardware cost (€10K-€30K)

### 3.4 OBSOLETE_PLATFORM — Legacy Timer/Instructions

**Problem:** S5TIME, ALARM_S, legacy PUT/GET instructions.

**Modern solution:** IEC TON/TOF, ProgramAlarm, modern TSEND/TRCV.

**Implementation:**
- S5TIME → IEC TIME (check preset cycle resolution)
- ALARM_S → SCL ProgramAlarm (TIA V14+)
- PUT/GET → TSEND_C/TRCV_C (Open Communication)

**Effort:** MEDIUM (8-24 hours).

### 3.5 COMMUNICATION — Hardcoded IP

**Problem:** PROFINET/Modbus IPs hard-coded inside SCL.

**Modern solution:** IPs in DB parameters, changeable from the HMI.

```scl
// Legacy (anti-pattern)
"TSEND_C"(REMOTE := '192.168.1.50', ...);

// New
"TSEND_C"(REMOTE := #stat_aRemoteIP, ...);
// stat_aRemoteIP ARRAY[1..4] OF BYTE — set from the HMI
```

**Effort:** LOW (2-4 hours).

### 3.6 ALARM — Unstructured Alarms

**Problem:** alarm-trigger bits hard-coded to Q outputs or HMI tags — no ISA-18.2 classification.

**Modern solution:** ProgramAlarm/ALARM_DIGITAL-based alarm management per RD08.

**Effort:** MEDIUM (16-40 hours).

### 3.7 DATA_MANAGEMENT — Wrong Retain

**Problem:** every DB Retain=Y → SD-card wear; or a critical variable Retain=N → loss on power failure.

**Modern solution:** retain strategy:
- Recipe parameters: Retain=Y
- Counter (product count): Retain=Y
- Process state: Retain=N (cold-start safe)
- Transient variables: Retain=N

**Effort:** LOW-MEDIUM (4-16 hours).

### 3.8 HMI — ISA-101 Non-Compliance

**Problem:** the HMI has no colour standard, no faceplates, no alarm widget.

**Modern solution:** ISA-101 + the AUTOMATION_FACTORY HMI template.

**Effort:** HIGH (40-80 hours).

---

## 4. Implementation Prioritisation

In Priority order:

### Sprint 1 (CRITICAL findings)
- SAFETY findings (F-PLC migration)
- Data-loss risk (Retain mistakes)
- Single point of failure (REDUNDANCY)

### Sprint 2 (MAJOR findings)
- NAMING (cross-cutting, affects other modules — do it first)
- STRUCTURE (modular refactor)
- COMMUNICATION (hardcoded IP)
- ALARM (ISA-18.2 system)

### Sprint 3 (MINOR/INFO)
- HMI improvements
- MAINTAINABILITY (comments, naming)
- PERFORMANCE optimisation

---

## 5. Risk Management

### 5.1 Refactor During Production (Dangerous!)

**NEVER:** change PLC code while production is running.

**Recommended:**
- Test on a pilot machine
- Validate with FAT (Factory Acceptance Test)
- Validate on-site with SAT (Site Acceptance Test)
- A/B test with a backup PLC

### 5.2 Rollback Plan

At the end of each sprint:
- Is the old code backed up? (TIA Portal archive)
- If the HW config is unchanged, rollback < 30 min
- If HW changed, on-site planning is required

### 5.3 Customer Communication

| Sprint | Presentation |
|--------|--------------|
| Kick-off | RD14 report + ModernizationDecision matrix |
| End of Sprint 1 | SAFETY findings + TÜV process |
| End of Sprint 2 | NAMING/STRUCTURE before/after |
| Final | FAT report + KB updates |

---

## 6. Validation

### 6.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD14 \
  --check-safety-verification \
  --check-priority-unique
```

### 6.2 Manual Checklist

- [ ] On SAFETY findings: Severity ≥ MAJOR, VerificationRequired ≠ NONE
- [ ] Priority unique (1-99)
- [ ] SummaryByCategory totals = FindingList count
- [ ] ModernizationDecision has 3 rows (RETROFIT/GREENFIELD/HYBRID)
- [ ] Rationale ≥ 20 chars for every Decision
- [ ] CodeExample_Good compiles cleanly in SCL
- [ ] Effort estimates calibrated against previous projects

---

## 7. Common Pitfalls

- ❌ **Downgrading a SAFETY finding to MINOR:** unauthorised; only the safety engineer can decide
- ❌ **Pushing NAMING out of retrofit scope:** NAMING is required on every retrofit project
- ❌ **Recommending HYBRID in most cases:** usually doubles the cost; NOT_RECOMMENDED is more common
- ❌ **Effort estimate excludes hardware:** F-PLC addition = labour + hardware cost
- ❌ **Skipping the pilot test:** going straight into changes on a production machine → production-stoppage risk
- ❌ **No rollback plan:** refactor started without taking a backup
- ❌ **Customer presentation too technical:** present in cost+benefit + risk language instead of an engineer-focused deck

---

## 8. AI Prompt Suggestion

`04_AI_PROMPTS/analyze/PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md`

The AI plays an important role (anti-pattern detection), but Severity and ModernizationDecision are ALWAYS human calls.

---

## 9. Pre-Customer-Approval Checklist

- [ ] RD14 SummaryByCategory table clear (counts per category)
- [ ] ModernizationDecision: 3 options + Rationale
- [ ] SAFETY findings signed off by the safety engineer
- [ ] Effort estimates calibrated (previous projects + team capacity)
- [ ] Customer presentation ready (PowerPoint/PDF, cost+duration+risk)
- [ ] Sprint plan in 3 stages (CRITICAL → MAJOR → MINOR)
- [ ] Rollback plan documented
- [ ] FAT/SAT plan (derived from RD12 scenarios)

---

## 10. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_14_MODERNIZATION.md`
- **Source:** `MDSCHEMA_RAWDATA_13_ANNOTATION.md`
- **AI prompt:** `PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md`
- **Previous guide:** `RETROFIT_EXTRACT_USECASE.md`
- **Next:** (last document of Phase 4 — transition to GREENFIELD)
- **Hardware analysis:** `RETROFIT_HARDWARE_ANALYSIS.md`
- **Maestro:** `RETROFIT_MAESTRO.md`
- **Naming:** `GLOBAL_NAMING_STANDARD.md`
- **FB template:** `GLOBAL_FB_TEMPLATE.scl`

---

*v1.1.0 — Full English body (2026-05-23). RD14 = the "what-changes-and-why" document. When selling value to the customer, this report is the evidence of cost/benefit balance. No shortcuts on SAFETY — certified-engineer sign-off is mandatory.*
