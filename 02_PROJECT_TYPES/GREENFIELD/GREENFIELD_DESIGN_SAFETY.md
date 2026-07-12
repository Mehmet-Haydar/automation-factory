---
title: Greenfield Safety Functions Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD05_Safety
prerequisite: [MDSCHEMA_RAWDATA_05_SAFETY.md]
safety_critical: TRUE
---

# GREENFIELD_DESIGN_SAFETY.md — Safety System Design Guide

> ⚠️ **SAFETY CRITICAL:** in greenfield, safety is designed with an F-PLC from day one. A certified safety engineer MUST be the designer.

---

## 1. Prerequisites

- [ ] Certified safety engineer assigned
- [ ] Risk assessment done (ISO 12100, EN ISO 13849-1)
- [ ] Machinery Directive 2006/42/EC requirements understood
- [ ] Target CE/TÜV process planned

---

## 2. Design Steps (5-Stage)

### 2.1 Step 1 — Risk Assessment

With the engineer or an independent expert:
- List hazard sources (mechanical, electrical, thermal, ergonomic)
- For each hazard assign S (Severity) + F (Frequency) + P (Possibility of avoidance)
- Determine PLr (Performance Level required) using the ISO 13849-1 risk graph
- Determine SIL (Safety Integrity Level) using the IEC 62061 method

### 2.2 Step 2 — Safety-Functions List

Typical functions:

| FunctionID | Function | Typical SIL/PLr |
|------------|----------|-----------------|
| SF001 | Emergency Stop (E-Stop) | SIL2 / PLr_d |
| SF002 | Safety Light Curtain | SIL2-3 / PLr_d-e |
| SF003 | Safety Guard Door | SIL2 / PLr_d |
| SF004 | Two-Hand Control | SIL3 / PLr_e |
| SF005 | Safe Speed Monitoring (SSM) | SIL2 / PLr_d |
| SF006 | Safely Limited Speed (SLS) | SIL2 / PLr_d |
| SF007 | Safe Torque Off (STO) | SIL2-3 / PLr_d-e |
| SF008 | Lockout/Tagout (LOTO) | SIL2 / PLr_d |

### 2.3 Step 3 — Hardware Selection

**F-CPU selection:**
- Siemens S7-1500F (TIA Safety + Distributed Safety)
- Allen-Bradley GuardLogix (1756-L8xES)
- Beckhoff TwinSAFE (CX5140 + TwinSAFE module)
- Pilz PNOZ multi (standalone safety controller)

**F-I/O modules:**
- F-DI (safety inputs — 2-channel)
- F-DO (safety outputs — dual)
- F-RO (relay output, for contactors)

**Drive integration:**
- Safety-rated VFD (e.g. SINAMICS S120 with Safety Integrated)
- STO, SBC, SS1, SS2, SLS functions

### 2.4 Step 4 — F-FB Design

Use standard F-FBs (don't write your own):

```scl
// Siemens TIA Safety F-FB example
"F_FB_EStop1_001"(
    E_STOP := "F_I_EStop_North",
    ACK := "DB_Safety".bResetCmd,
    Q := "DB_Safety".bEStopOK
);
```

Common F-FBs:
- F_ESTOP1, F_ESTOP_R (E-Stop)
- F_FDBACK (contactor feedback)
- F_SFDOOR (safety door)
- F_TWO_H_EN (two-hand)
- F_MUT_P, F_MUT_S (muting — light-curtain bypass)

### 2.5 Step 5 — Validation + Certification

- [ ] FAT (Factory Acceptance Test) — controlled E-Stop test, response-time measurement
- [ ] SAT (Site Acceptance Test) — on-site validation
- [ ] TÜV/CE certification (if required)
- [ ] Proof-test schedule (typically every 10-20 years)

---

## 3. Design Best Practice

### 3.1 Independence Discipline
- The F-PLC runs a separate cycle, independent from the standard PLC
- Safety telegrams over the F-bus (PROFIsafe)
- A single fault does not lose the safety function (Cat 3+/SIL2+)

### 3.2 Diagnostic Coverage (DC)
- Target DC ≥ 90% (for high Cat)
- Cross-check, voltage monitoring, plausibility check

### 3.3 Common Cause Failure (CCF)
- IEC 62061 scoring ≥ 65 points
- Different design principles (electromechanical + electronic)

---

## 4. AI Boundary

In greenfield, AI does **not contribute directly** to safety design:
- SIL/PLr estimation forbidden
- Risk assessment is human work
- F-FB selection is an engineering decision

AI only helps with **documentation**:
- Assistant filling out risk-assessment templates
- Syntax check on F-FB call sites
- SIL formula verification (for check purposes, not a decision)

---

## 5. Design-Approval Checklist

- [ ] Risk-assessment document (ISO 12100)
- [ ] PLr/SIL calculation (ISO 13849-1 / IEC 62061)
- [ ] F-CPU + F-I/O hardware list
- [ ] F-FB inventory (TIA Safety / GuardLogix / TwinSAFE)
- [ ] FAT procedure written (response-time test included)
- [ ] TÜV certification dossier ready (if required)
- [ ] Proof-test schedule documented
- [ ] Signed by the certified engineer

---

## 6. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_05_SAFETY.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_SAFETY.md`
- **Standards:** IEC 62061, ISO 13849-1, IEC 61508, IEC 61511, 2006/42/EC

---

*v1.1.0 — Full English body (2026-05-23). Greenfield advantage: designing safety with F-PLC from day one. Adding it later = very expensive + high risk.*
