---
title: AI Prompt - Case Study (Marketing / Lessons Learned)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [all RD specs, FAT/SAT reports]
target_ai: [Claude Sonnet 4+]
input_source: PROJECT_MAESTRO + RD specs + customer feedback
output_artifacts: [case_study_<project>.md, case_study_anonymized.md]
role: doc_gen
schema: PROMPT_DOC_GEN
---

# PROMPT_DOC_GEN_CASE_STUDY.md — Project Case Study Generation

> **After customer approval: marketing material for the factory + an internal lessons-learned record.**

---

## 1. Two Versions

### A. Customer-Approved (Public)
- Customer name + logo (if permission obtained)
- For website / LinkedIn / marketing purposes

### B. Anonymized (Internal)
- Customer name removed ("Automotive OEM, Germany 2026")
- Specific technical data preserved
- For the factory KB + reference for future customers

---

## 2. Content Template

```markdown
# CASE STUDY: <Project Name> — <Sector>

**Customer:** <Customer> or "Automotive OEM, Germany"
**Sector:** Automotive / Food / Pharma / etc.
**Year:** 2026  | **Duration:** 4 months  | **Result:** ✓ Successful SAT

## Challenge
- 1995 S7-300 system (no spare parts left)
- No F-PLC → CE certificate cannot be renewed
- 24/7 production → minimum downtime required
- German-speaking operators + documentation

## Solution
- AUTOMATION_FACTORY v3.0.0-alpha was used
- Systematic extraction with the 14-Point Pack (3 weeks)
- 14 RD drafts with AI (Claude Opus + Sonnet)
- Certified safety engineer RD05 approval (TÜV)
- F-PLC migration (S7-1500F)
- Multi-lang HMI (DE + EN)

## Result (Numbers)
- Migration time: 4 months (typical 9-12 months) → 50% faster
- Engineering hours: 280h (typical 600h+) → 53% less
- AI extraction accuracy: 85% (15% manual correction)
- FAT pass rate: 98% (minor warnings)
- Customer satisfaction: 9/10

## Lessons Learned
1. AI sequence extraction is weak → operator workshop mandatory
2. F-PLC procurement delayed by 8 weeks → ordering ahead is critical
3. Thanks to the multi-lang glossary, HMI text is consistent
4. RD05 discipline (DRAFT_UNVERIFIED) → a certified engineer was brought into the process
5. Watch the communication layer: PROFIBUS→PROFINET migration has compatibility issues with old devices

## Next Step
- The customer awarded us the second line's retrofit
- KB updated (4 new pitfalls added)
- AI prompts improved (v3.1.0)
```

---

## 3. Customer Approval Process

```
[Case study draft (AI)]
       ↓
[Customer review + revision requests]
       ↓
[Customer approval]
       ↓
[Public version (logo+name) → marketing]
[Anonymized version (name removed) → internal KB]
```

**If the customer declines:** Only the anonymized version is used internally.

---

## 4. Marketing Use

- LinkedIn post (visual + short text)
- Website case studies page
- Sales presentation (reference in the new-customer flow)
- Conference presentation (anonymized)

---

## 5. Related Files

- **Anonymization:** `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`
- **KB:** `06_KNOWLEDGE_BASE/` (extract pitfalls from the case study)
- **Sprint:** End-of-sprint lessons-learned

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0: Case study = fuel for the factory's growth. Every successful project brings a new one.*
