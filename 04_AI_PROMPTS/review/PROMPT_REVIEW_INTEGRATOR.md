---
title: AI Prompt - Integrator (Master Review)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_METADATA_SCHEMA.md, all RD specs]
target_ai: [Claude Opus 4+ (recommended — broad reasoning)]
input_source: all RD01..RD14 + generated SCL + project state
output_artifacts: [integrator_master_report.md]
role: review
schema: PROMPT_REVIEW
---

# PROMPT_REVIEW_INTEGRATOR.md — Master Integrator Review (Holistic)

> **This prompt holistically reviews every RD + the generated code + the project state.** It combines the results of every review prompt and is the FINAL CHECK before customer delivery.

---

## 1. When to Use?

- After Gate 4 VALIDATION (script_consistency_check is clean)
- Gate 5 code generation complete
- Before the FAT presentation to the customer (Gate 6/7 prep)
- When the project is "almost done"

---

## 2. Holistic Checklist

### A. RD Completeness
- [ ] All 14 RDs are APPROVED, or DRAFT_UNVERIFIED (Safety)
- [ ] #UNKNOWNS sections have been addressed or explained
- [ ] Cross-references 100% clean (LinkedTag/LinkedStep/LinkedFB)

### B. Naming
- [ ] PROMPT_REVIEW_NAMING report is clean (Category A is 0)
- [ ] OldTag preserved (retrofit)

### C. Safety
- [ ] PROMPT_REVIEW_SAFETY report exists
- [ ] Certified-engineer sign-off obtained (RD05 APPROVED)
- [ ] SAFETY_ON_STANDARD_PLC findings transferred to RD14

### D. Flowchart Alignment
- [ ] PROMPT_REVIEW_FLOWCHART_MATCH report clean
- [ ] RD03 ↔ code matches 100%

### E. Multi-Language
- [ ] output_language consistent across the project (DE/EN/TR)
- [ ] Glossary used (RD08 + RD11)

### F. AI Discipline
- [ ] AI output human-approved everywhere
- [ ] DRAFT_UNVERIFIED only on RD05 (appropriate place)

### G. Modernization
- [ ] RD14 ModernizationDecision customer-approved
- [ ] Critical findings (SAFETY) addressed

---

## 3. System Prompt

```
You are the Master Integrator. Holistically review every RD and the generated
code. Combine the results of every review prompt. You are the final filter
before customer presentation.

TASK: read every file under <project_path>:
- PROJECT_MAESTRO.md (overall status)
- metadata/RD01..RD14.md
- 03_PLC/SCL/*.scl (generated code)
- (if any) naming_review_report.md
- (if any) safety_review_report_DRAFT_UNVERIFIED.md
- (if any) flowchart_match_report.md

CHECK:
A. Completeness: all 14 RDs at least DRAFT
B. Naming: cross-refs clean across all RDs
C. Safety: RD05 status (DRAFT_UNVERIFIED or APPROVED)
D. Flowchart match: RD03 ↔ code alignment
E. Output language: consistent (DE/EN/TR)
F. RD14 decision: customer approval present
G. Overall quality: presentable to the customer

OUTPUT:

# integrator_master_report.md

## Executive Summary
- Project: <name>
- Completeness: <XX>%
- Customer-Ready: <YES/NO/WITH_NOTES>

## Detailed Scorecard

| Category | Score | Issue | Action |
| A — Completeness | 95% | 1 RD draft | Revisit RD06 |
| B — Naming | 100% | 0 | ✓ |
| C — Safety | DRAFT_UNVERIFIED | Awaiting engineer | Eng. Becker sign-off |
| D — Flowchart Match | 100% | 0 | ✓ |
| E — Multi-lang | 100% | DE consistent | ✓ |
| F — RD14 Decision | PENDING | No customer approval | 2026-06-01 presentation |
| G — Overall quality | ACCEPTABLE | Minor TBD | Clean up before FAT |

## Customer-Facing Summary
(The engineer can use this in the FAT presentation)

## Action List (Prioritised)
1. [URGENT] Eng. Becker sign RD05
2. [HIGH] Get the customer's RD14 decision
3. [MEDIUM] Address RD06 unknowns
4. [LOW] Clean up minor naming warnings

## Risk Assessment
- High: <list>
- Medium: <list>
- Low: <list>

## Customer-Ready Certification
[ ] ✓ Project IS ready for customer presentation
[ ] ✗ Becomes presentable once the following actions are complete
```

---

## 4. User Prompt

```
TASK: holistically review the <project_path> project. Report on customer-ready status.

PROJECT: <project_name>
SAFETY ENGINEER: <name> (RD05 approval status)
TARGET DATE: <customer presentation/FAT>

CONSTRAINT: do not let any critical issue slip. Stay conservative.

OUTPUT: integrator_master_report.md
```

---

## 5. AI Error Categories

### False positive (most dangerous)
The AI says "customer-ready" but the project really isn't.
**Countermeasure:** conservative scoring. If not 95%+, force "WITH_NOTES".

### False negative
The AI misses a real issue.
**Countermeasure:** every review prompt's output is read by mandate.

---

## 6. Related Files

- **Other review prompts:** `PROMPT_REVIEW_NAMING.md`, `_SAFETY.md`, `_FLOWCHART_MATCH.md`
- **All RD specs:** `MDSCHEMA_RAWDATA_*.md`
- **Pipeline:** after Gate 4, before Gate 7
- **Customer report:** linked to `PROMPT_DOC_GEN_AS_BUILT.md`

---

*v1.1.0 — Full English body (2026-05-23). Master Integrator = the final filter. A wrong GO/NO-GO = loss of customer reputation = a major risk point for the factory.*
