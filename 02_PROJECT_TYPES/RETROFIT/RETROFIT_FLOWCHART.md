---
title: Retrofit Flowchart Extraction Procedure (v1)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD03_Flowchart
prerequisite: [MDSCHEMA_RAWDATA_03_FLOWCHART.md, RETROFIT_EXTRACT_DATADICT.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md
note: Alias of the canonical guide. The sibling `RETROFIT_EXTRACT_FLOWCHART.md` referenced by other files does not yet exist — content lives here.
---

# RETROFIT_FLOWCHART.md — Flowchart Extraction (Short Version)

> This file documents the same workflow as the planned `RETROFIT_EXTRACT_FLOWCHART.md` (which is not yet present in the repo). The name is kept for historical reasons.

---

## 1. Summary

Extract the sequence/state-machine structure of the legacy PLC code into RD03 with **IEC 61131-3 SFC** + **ISA-88** discipline.

---

## 2. Source Patterns

| Pattern | Source |
|---------|--------|
| Siemens GRAPH 7 | Direct SFC extraction |
| Manual M-bit | Pseudo-FSM detection |
| Step DB integer | CASE/IF control |
| State-machine FB | CASE OF with ENUM |
| AB SFC routine | Routine type=SFC |

---

## 3. Workflow

```
[_parsed.md + RD02 + RD04]
       ↓
[AI: PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md]
       ↓
[RD03 draft (table + Mermaid)]
       ↓
[Operator verification + Engineer review]
       ↓
[RD03_Flowchart.xlsx (approved)]
```

---

## 4. Critical Rules

- StepID `^S\d{3}[A-Z]?$`, spacing by 10 (S010, S020, …)
- Initial step → EntryCondition=TRUE
- Distinguish Alternative (OR-divergence) vs Parallel (AND-divergence)
- An ErrorStep for each critical step (typically S099)
- ModeReq on every step
- Mermaid stateDiagram-v2 syntax must be clean

---

## 5. Detailed Checklist

For details see `RETROFIT_EXTRACT_FLOWCHART.md` (when published). Summary here:

- [ ] All steps numbered correctly
- [ ] StepType in the valid enum
- [ ] Initial → EntryCondition=TRUE
- [ ] ErrorStep present for each step
- [ ] ModeReq on every step
- [ ] ISA88Level appropriate
- [ ] Operator confirmed
- [ ] Mermaid is renderable

---

## 6. Related Files

- **Detailed guide:** `RETROFIT_EXTRACT_FLOWCHART.md` (planned)
- **Spec:** `MDSCHEMA_RAWDATA_03_FLOWCHART.md`
- **AI prompt:** `PROMPT_EXTRACT_FLOWCHART_FROM_CODE.md`
- **Standards:** IEC 61131-3 §6.7 SFC, ISA-88 §4

---

*v1.1.0 — Full English body (2026-05-23). The detailed flowchart-extraction content lives here until `RETROFIT_EXTRACT_FLOWCHART.md` is created.*
