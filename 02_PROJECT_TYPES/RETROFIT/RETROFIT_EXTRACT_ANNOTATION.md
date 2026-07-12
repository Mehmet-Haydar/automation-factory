---
title: Retrofit Legacy Code Annotation Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD13_Annotation
prerequisite: [MDSCHEMA_RAWDATA_13_ANNOTATION.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md
---

# RETROFIT_EXTRACT_ANNOTATION.md — Legacy Code Annotation Procedure

> **Goal:** annotate the legacy PLC code line by line in Turkish and document its meaning. The raw source for the RD14 Modernization Report.

> **Note:** this RD applies only to **RETROFIT** projects (greenfield has no legacy code).

---

## 1. Prerequisites

- [ ] Legacy PLC code available in raw form (.awl, .scl, .L5X, .xml)
- [ ] _parsed.md ready (overall project map)
- [ ] RD01 + RD02 + RD10 complete (for cross-references)
- [ ] Engineer has a sufficient time budget (densest extraction — hours)

---

## 2. Granularity Decision

Annotate line-by-line, network-level, or block-level?

| Granularity | When to use |
|-------------|-------------|
| **Line** | Critical blocks (E-Stop logic, safety, complex math) |
| **Network/Segment** | Standard sequence code |
| **Block** | Very large, generic block (e.g., utility FC) |
| **Pattern (repeating)** | Loop, array access — one record + a "repeating pattern" note |

**Decision matrix:**
- Total code very large (>1000 networks) → block-level
- Critical/SAFETY → line-level
- Repeating patterns → single record + Notes

---

## 3. Workflow

```
[1] Raw source code + _parsed.md ready
       ↓
[2] Granularity decision (per project size)
       ↓
[3] AI prompt: PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md
       ↓
[4] RD13_Annotation_draft.md (AI draft)
       ↓
[5] Human review:
   ├─ Are the Turkish explanations sufficient
   ├─ Were all WarningFlags caught
   ├─ Is ConfidenceLevel realistic
   └─ Are Y_SAFETY_CONCERN rows on a special list
       ↓
[6] RD13_Annotation.xlsx
       ↓
[7] The RD14 Modernization extractor reads this
```

---

## 4. Human Review Checklist

#### A. Annotation Completeness
- [ ] All critical blocks included
- [ ] Dead code (DEAD_CODE) detected
- [ ] OB100 initialization included separately
- [ ] Interrupt OBs (OB40-47, OB80-87) included

#### B. Warning Flag Completeness
- [ ] `Y_HARDCODED_ADDR` absolute addresses flagged
- [ ] `Y_MAGIC_NUMBER` undocumented literals
- [ ] `Y_UNDOCUMENTED` uncommented blocks
- [ ] `Y_SAFETY_CONCERN` safety-related code (special focus)
- [ ] `Y_DEPRECATED_INSTR` legacy instructions (S5TIME, etc.)
- [ ] `Y_DEAD_CODE` unreachable code

#### C. Confidence Level Realism
- [ ] HIGH confidence only for fully understood blocks
- [ ] **NEVER HIGH confidence on safety code** (max MEDIUM)
- [ ] HUMAN_REQUIRED rows asked to the customer/operator

#### D. Cross-Reference
- [ ] LinkedRD populated (which RDs are related)
- [ ] LinkedTag exists in RD01
- [ ] LinkedFB exists in RD10

#### E. Turkish Quality
- [ ] Explanations are technical (not just "the code runs")
- [ ] Cause + function explained
- [ ] If translated from German comments, `(orig: ...)` preserved

---

## 5. Special-Findings Classification

```markdown
## Y_SAFETY_CONCERN Findings (HIGH priority, RD14 input)

| ANN ID | Block | Description | RD14 Suggestion |
|--------|-------|-------------|-----------------|
| ANN0023 | FC10 NW5 | E-Stop contactor on a standard Q output | F-PLC migration |
| ANN0089 | FC15 NW3 | Motor bypass logic with light curtain | risk assessment |

## Y_DEAD_CODE Findings

| ANN ID | Block | Description |
|--------|-------|-------------|
| ANN0145 | FB200 NW12 | JMP skipped, unreachable |
```

These are the base data for the RD14 modernization report.

---

## 6. Common Pitfalls

- ❌ **AI keeps the Turkish explanation generic:** "this code runs the motor" → make it specific (which motor, which condition)
- ❌ **OriginalCode is "fixed":** it must be preserved verbatim
- ❌ **WarningFlag completeness:** AI only sees the obvious; the rest requires human detection
- ❌ **ConfidenceLevel always HIGH:** must be conservative
- ❌ **Dead code skipped:** flow after JMP/JSR not followed

---

## 7. Gate 3 Checklist

- [ ] Granularity decided and applied
- [ ] All WarningFlag types detected
- [ ] Y_SAFETY_CONCERN rows on a separate list
- [ ] ConfidenceLevel realistic (no HIGH on safety code)
- [ ] LinkedRD/LinkedTag/LinkedFB cross-references clean
- [ ] Turkish explanations technical + concrete
- [ ] Ready for the RD14 Modernization extractor

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_13_ANNOTATION.md`
- **AI prompt:** `PROMPT_EXTRACT_ANNOTATION_FROM_CODE.md`
- **Next step:** `RETROFIT_MODERNIZATION_GUIDE.md` (RD14)

---

*v1.1.0 — Full English body (2026-05-23). Annotation = "talking" to the legacy code. You can't modernize what you don't understand.*
