---
title: Retrofit Safety Functions Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD05_Safety
prerequisite: [MDSCHEMA_RAWDATA_05_SAFETY.md, GLOBAL_DATA_CLASSIFICATION.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_SAFETY_FROM_CODE.md
safety_critical: TRUE
---

# RETROFIT_EXTRACT_SAFETY.md — Safety Functions Extraction Procedure

> ⚠️ **SAFETY-CRITICAL:** this procedure runs under a certified safety engineer's supervision. AI outputs are marked **DRAFT_UNVERIFIED** and do NOT go to production without engineer sign-off.

---

## 1. Prerequisites

- [ ] **Certified safety engineer assigned** (TÜV/VDE/IEC 61508 certified)
- [ ] Customer's **risk-assessment document** (ISO 12100) at hand
- [ ] CE/TÜV requirements known (SIL/PLr targets)
- [ ] RD01 IO List complete (F-prefix tags identified)
- [ ] _parsed.md ready

---

## 2. Workflow (3 Stages, Under Engineer Supervision)

```
[1] AI prompt: PROMPT_EXTRACT_SAFETY_FROM_CODE.md
       ↓
[2] RD05_Safety_DRAFT_UNVERIFIED.md
       ├─ SIL_Level: BLANK (AI cannot fill)
       ├─ Category: BLANK (AI cannot fill)
       └─ Status: DRAFT_UNVERIFIED (AI NEVER changes this)
       ↓
[3] SAFETY ENGINEER REVIEW
       ├─ Compare against the risk-assessment document
       ├─ Determine the SIL/PLr level
       ├─ Determine the Category (B/1/2/3/4)
       ├─ Compute ProofTestInterval_h
       └─ Status → APPROVED (with signature)
```

---

## 3. What the AI Extracts

The AI extracts only the following:
- F-prefixed blocks (F_FB, F_DB, F_I, F_Q)
- TriggerCondition (inputs, NC/NO distinction)
- SafeAction (drop circuit, stop motor)
- ResetType (Auto/Manual/Tooled)

**The AI NEVER extracts:**
- SIL Level
- Category
- ProofTestInterval

---

## 4. SAFETY_ON_STANDARD_PLC (CRITICAL Finding)

If the legacy code has safety logic on a **standard PLC** (no F-CPU):

```scl
// EXAMPLE ANTI-PATTERN — E-Stop on a standard Q output
AN    I      0.3    // E-Stop NC contact
=     Q      0.7    // Contactor drop
```

This is a **CRITICAL finding**. It is auto-transferred to RD14:
- Severity: CRITICAL
- Category: SAFETY
- ModernAlternative: F-PLC (S7-1500F + F-FB)
- VerificationRequired: SAFETY_ENGINEER

---

## 5. Human Engineer Checklist

#### A. Risk-Assessment Comparison
- [ ] Every function in the customer's risk-assessment document is detected
- [ ] Functions in the document but missing from the AI extraction pushed to `#UNKNOWNS`
- [ ] Functions in the AI extraction but not in the document validated with the customer

#### B. SIL/Category Assignment
- [ ] SIL_Level filled for each FunctionID (SIL1/SIL2/SIL3/PLr_a..e)
- [ ] Category filled (B/1/2/3/4)
- [ ] ProofTestInterval_h computed
- [ ] Verified_By contains engineer name + certificate number

#### C. F-Component Check
- [ ] F_InputTag exists in RD01 with F-prefix
- [ ] F_OutputTag exists in RD01 with F-prefix
- [ ] F_DB and F_FB defined in RD02/RD10

#### D. Response Time Verification
- [ ] ResponseTime_ms validated with a real measurement (PLC trace)
- [ ] Risk-assessment response-time requirement is met

#### E. Status Transition
- [ ] DRAFT_UNVERIFIED → HUMAN_REVIEWED → APPROVED
- [ ] For APPROVED, Verified_By + ReviewDate are mandatory

---

## 6. Common Pitfalls

- ❌ **No F-prefix but F-CPU present:** S7-300 Distributed Safety doesn't require the F-prefix; the F-CPU's presence is enough
- ❌ **F-prefix present but no F-CPU:** that's only a naming convention; not real safety
- ❌ **Accepting an AI SIL guess:** outright reject — only the engineer decides
- ❌ **Skipping standard-PLC safety logic detection:** SAFETY_ON_STANDARD_PLC is a very critical finding
- ❌ **Skipping multi-channel diagnostics:** Cat 3/4 architecture requires 2-channel redundancy

---

## 7. Gate 3 Approval Checklist

- [ ] AI draft produced (DRAFT_UNVERIFIED)
- [ ] Certified safety engineer reviewed
- [ ] SIL/Category fields filled
- [ ] Verified_By + ReviewDate signed
- [ ] Status: APPROVED
- [ ] SAFETY findings transferred to RD14 (if any)
- [ ] Safety report delivered to customer

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_05_SAFETY.md`
- **AI prompt:** `PROMPT_EXTRACT_SAFETY_FROM_CODE.md`
- **Standards:** IEC 62061, ISO 13849-1, IEC 61508, IEC 61511, Machinery Directive 2006/42/EC

---

*v1.1.0 — Full English body (2026-05-23). No shortcuts on safety. Certified engineer sign-off is mandatory — by law and for human safety.*
