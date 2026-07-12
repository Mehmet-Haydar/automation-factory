---
title: Project State Report Template
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-16
applies_to: [both]
status: ACTIVE
---

# GLOBAL_PROJECT_STATE_TEMPLATE.md — Project State Template

> Weekly-updated status report template for customer projects. Copied via `script_project_init.py`.

---

## Template

```markdown
# PROJECT_STATE.md — <Project Name>

> Updated weekly. First thing Monday morning.

---

## <YYYY-MM-DD> — Week <N>

### Completed
- [ ] RD01 IO List — APPROVED (engineer Mehmet Haydar)
- [ ] RD02 DataDict — DRAFT (75% filled)
- [ ] ...

### In Progress
- RD05 Safety engineer review (Hans Becker — end of this week)
- RD08 Alarm German translation (glossary used)

### Blocked / Risk
- F-PLC procurement 8-week delay → customer notified
- Old WinCC export symbolic tag missing → operator interview needed

### AI Usage Notes
- PROMPT_EXTRACT_IO ran, accuracy 85%
- PROMPT_EXTRACT_SAFETY ran (DRAFT_UNVERIFIED preserved)
- AI error: mistagged M10.5 symbol (human corrected)

### Customer Interaction
- 2026-05-12: Operator workshop (sequence detail)
- 2026-05-18: Plan: RD14 modernization decision presentation

### Next Week Plan
- Get RD05 safety APPROVED
- Run Gate 4 validation
- Start Gate 5 (FB_Motor generation)

### Scorecard
| Metric | Target | Current |
|--------|--------|---------|
| RD completeness | 14/14 | 8/14 |
| AI accuracy | >80% | 85% |
| Customer satisfaction | >8 | 8 |
| Timeline | 16 weeks | Week 4 (on track) |
| Budget | €60K | €15K (25%) |
```

---

## Usage

This template is copied by `script_project_init.py`. At the beginning of each week:

1. Mark previous week section as "history"
2. Add new `## <date> — Week <N>` section
3. Fill Completed/In Progress/Blocked areas
4. Add AI usage notes (for learning)
5. Track customer interactions
6. Update scorecard

---

## Related Files

- **Init script:** `05_SCRIPTS/script_project_init.py` (copies this template)
- **Project maestro:** `07_PROJECT_TEMPLATE/PROJECT_MAESTRO_TEMPLATE.md`

---

*v1.0.0 — Track project health weekly. Sprint discipline ecosystem.*
