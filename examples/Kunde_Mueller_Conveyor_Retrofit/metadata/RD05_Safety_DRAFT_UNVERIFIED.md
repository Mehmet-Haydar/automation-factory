---
title: RD05_Safety_DRAFT_UNVERIFIED — Kunde Müller Conveyor Retrofit
last_validated: 2026-05
status: DRAFT_UNVERIFIED
review_pending: safety_engineer
---

# RD05_Safety_DRAFT_UNVERIFIED — Kunde Müller Conveyor Retrofit

> ⚠️ **WARNING:** This file was produced by AI. NOT USABLE without sign-off from a certified safety engineer (Hans Becker, TÜV). All SIL/PLr/Category fields are BLANK — a human will fill them.

---

## Frontmatter

```yaml
project_id: KMG-2026-001
filled_by: AI Engine (DRAFT)
filled_at: 2026-05-15
status: DRAFT_UNVERIFIED                 # NEVER changed by the AI
safety_engineer: Hans Becker (TÜV cert. #DE-001234)
risk_assessment_doc: KMG-RA-2026-001 (2026-05-08)
review_pending: TRUE
```

---

## Summary

- **Safety functions detected: 4**
- **F-PLC present: NO** (CPU 315-2 DP standard)
- **F-FB count: 0** (no safety blocks at all)
- **Safety logic on a standard PLC: 4 functions (CRITICAL)** 🛑

---

## Safety Functions

| FunctionID | FunctionName | SIL_Level | Category | TriggerCondition | SafeAction | ResponseTime_ms | ResetType | F_InputTag | F_OutputTag | F_DB | F_FB | ProofTestInterval_h | Verified_By | Notes | Status |
|------------|--------------|-----------|----------|------------------|------------|------------------|-----------|------------|-------------|------|------|---------------------|-------------|-------|--------|
| SF001 | EStop_North_Panel | | | F_I_EStop_North = FALSE (NC) | All motor outputs OFF, Q3.7 = FALSE | | Manual | F_I_EStop_North | Q3.7 (MASTER_CONTACTOR) | (standard DB10) | FC10 NW5 (standard code) | | | ⚠️ **STANDARD PLC — F-PLC migration mandatory** | DRAFT_UNVERIFIED |
| SF002 | EStop_South_Panel | | | F_I_EStop_South = FALSE (NC) | Same (parallel circuit) | | Manual | F_I_EStop_South | Q3.7 | - | FC10 NW6 | | | ⚠️ Standard PLC | DRAFT_UNVERIFIED |
| SF003 | LightCurtain_Loading | | | F_I_LC_Loading = TRUE (beam broken) | Conveyor STOP (Q0.0 = FALSE) | | Auto | F_I_LC_Loading | Q0.0 | - | FC10 NW8 | | | ⚠️ **BYPASS EXISTS (while maintenance mode is active)** — risk assessment needed | DRAFT_UNVERIFIED |
| SF004 | LightCurtain_Unloading | | | F_I_LC_Unloading = TRUE (beam broken) | Conveyor2 STOP | | Auto | F_I_LC_Unloading | Q0.1 | - | FC10 NW9 | | | ⚠️ Standard PLC | DRAFT_UNVERIFIED |

---

## ⚠️ Questions for the Safety Engineer

| FunctionID | Question |
|------------|------|
| SF001 | What SIL should the E-Stop require? (estimate from the preliminary risk graph: SIL2 / PLr_d) |
| SF001 | What is the response-time requirement? Is there a customer spec? |
| SF002 | Is redundancy required? The two E-Stops are currently wired in parallel |
| SF003 | **Is the light-curtain bypass acceptable?** May violate EN 61496-1 |
| SF003 | Is a different protection strategy possible instead of muting? (e.g. door interlock) |
| SF004 | How close does the operator get to the hazard zone in the unloading area? |
| ALL | Has the time + budget for F-PLC migration been approved? |

---

## SAFETY_ON_STANDARD_PLC Findings (CRITICAL) 🛑

> This section is carried into RD14_Modernization.md → FND001.

| Block | Network | Description | Risk Level |
|-------|---------|-------------|---------------|
| FC10 | NW5 | E-Stop North → MASTER_CONTACTOR (Q3.7) | **CRITICAL** — a single fault can disable the E-Stop |
| FC10 | NW6 | E-Stop South → MASTER_CONTACTOR | **CRITICAL** |
| FC10 | NW8 | Light curtain + BYPASS logic | **CRITICAL** — bypass authorization unclear |
| FC10 | NW9 | Light curtain (unloading) | **CRITICAL** |

**Conclusion:** CE documentation cannot be renewed for this machine without adding an F-CPU.

---

## Findings Report for the Customer

```
SAFETY FINDING — KUNDE MÜLLER GMBH (KMG-2026-001)
====================================================

Date: 2026-05-15
Prepared by: Mehmet Haydar (project engineer) + Hans Becker (TÜV)
Confidentiality: 🟠 CONFIDENTIAL

Finding:
  Four safety functions on your machine (2× E-Stop, 2× Light Curtain) are
  implemented on a standard PLC. There is no F-CPU (SIL-rated safety PLC).

Impact:
  - CE documentation cannot be renewed (Machinery Directive 2006/42/EC)
  - SIL/PLr level cannot be measured/assigned
  - Single-point-of-failure risk (a PLC cycle fault disables the E-Stop)
  - A light-curtain bypass exists — an operator risk assessment is required

Recommendation:
  F-PLC migration (RD14_Modernization.md FND001):
  - Hardware: S7-1500F + F-DI + F-DO ≈ €18,000
  - Engineering: ~80 hours
  - TÜV certification: ~€8,000
  - Total: ~€32,000 + timeline: 8-12 weeks

  ALTERNATIVE: Greenfield (full system renewal) — a longer-term investment
  covering both the F-PLC and up-to-date hardware. RD14 ModernizationDecision
  recommends GREENFIELD.

Legal Note:
  This finding must be disclosed to the customer under German and EU Machinery
  Directive requirements. Continuing to operate the machine without action
  carries legal risk.
```

---

## #UNKNOWNS

| Old symbol | Reason |
|-------------|-------|
| (NW8 Bypass logic) | Who is authorized to enable the bypass? Is there a documented procedure? |
| (Response time) | The current system's response time has not been measured — an oscilloscope test is needed |

---

## Fill-in Notes (for this example)

- **SIL_Level, Category, ProofTestInterval_h fields are BLANK** (the AI cannot fill them)
- **Every row is Status=DRAFT_UNVERIFIED** (the limit of AI authority)
- **Verified_By is BLANK** — moves to APPROVED once Hans Becker signs off
- **SAFETY_ON_STANDARD_PLC findings are in a separate section** + carried into RD14

---

*v1.0.0 — This example is the concrete form of the RD05 discipline. The AI only detects; the engineer decides; the customer signs.*
