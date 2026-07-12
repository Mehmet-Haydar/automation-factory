---
title: AI Prompt - Operator Manual
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [MDSCHEMA_RAWDATA_12_USECASE.md, MDSCHEMA_RAWDATA_11_HMI.md, MDSCHEMA_RAWDATA_04_MODE.md, DOMAIN_HMI_STANDARD.md]
target_ai: [Claude Sonnet 4+]
input_source: RD11 HMI + RD12 UseCase + RD04 Mode + RD08 Alarm
output_artifacts: [operator_manual.md, operator_manual.pdf]
role: doc_gen
schema: PROMPT_DOC_GEN
---

# PROMPT_DOC_GEN_OPERATOR_MANUAL.md — Operator Manual Generation

> **A daily-use manual for the operator.** Visual, in simple language, multi-lang. Kept on the shop floor.

---

## 1. Content Template

```markdown
# OPERATOR MANUAL — <Machine_Name>

## 1. Quick Start
- Morning power-on routine (5 steps)
- Starting production
- End-of-shift shutdown

## 2. HMI Screens   (from RD11 — each screen screenshot + description)

### 2.1 Main View (SCR001)
[Screenshot]
- A: Production counter
- B: Active mode
- C: Alarm summary
- D: Quick action buttons

## 3. Operating Modes   (RD04 Mode)
| Mode | When | How to switch |
|---|---|---|
| AUTO | Normal production | Press Btn_Auto |
| MANUAL | Maintenance | Auth + Btn_Manual |
| SETUP | Commissioning | Engineer auth |
| LOTO | Maintenance lockout | Key required |

## 4. Emergencies   (RD05 + RD12 Emergency)

### 4.1 When E-Stop Is Pressed
1. Stop
2. Check the danger zone
3. Identify the cause
4. Release the E-Stop
5. Press Reset
6. Return to AUTO

## 5. Daily Maintenance   (from DOMAIN_TESTING)
- Filter check, oil level, vibration check

## 6. Troubleshooting (Top 10 alarms — RD08)
| Alarm | Cause | Solution |
| ALM0042 Comm Lost | Network cable | Check switch port + cable |
| ... | ... | ... |

## 7. Contacts — Maintenance/Engineer/Emergency
```

---

## 2. Multi-Language

The manual is written in the customer's language:
- German customer → German manual
- Turkey → Turkish
- Multi-site → multi-lang version (each language on a separate page or separate PDF)

Use the glossary: `01_GLOBAL_STANDARDS/lang_glossary/`

---

## 3. Visual Discipline

- A screenshot for each HMI screen + numbered callouts (A, B, C, D)
- Emergency procedures: red box emphasis + warning icon ⚠️
- Step by step: numbered 1. 2. 3., short sentences
- Tables (alarm, recipe) easy to look up by page number

---

## 4. PDF Render

```bash
pandoc operator_manual.md -o operator_manual.pdf \
  --template=industrial-manual.tex \
  --pdf-engine=xelatex \
  --highlight-style=tango \
  -V documentclass=article \
  -V geometry:margin=2cm
```

---

## 5. Related Files

- **Source:** RD11 + RD12 + RD04 + RD08
- **Domain:** `DOMAIN_HMI_STANDARD.md`
- **Glossary:** `lang_glossary/`
- **Pipeline:** Gate 7 (presented to the customer before SAT)

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0: Operator manual = the core material for operator training. Kept at hand on the shop floor.*
