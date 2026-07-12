---
title: AI Prompt - As-Built Documentation
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [all RD specs, INTEGRATOR review]
target_ai: [Claude Opus 4+ (detailed documentation)]
input_source: all RD01..RD14 + generated SCL + FAT report
output_artifacts: [as_built_documentation.pdf, as_built.md]
role: doc_gen
schema: PROMPT_DOC_GEN
---

# PROMPT_DOC_GEN_AS_BUILT.md — As-Built Documentation Generation

> **The final technical document delivered to the customer.** The project's "birth certificate" — whoever maintains it years later will read this document.

---

## 1. When to Use?

- After Gate 7 SAT (once the customer has signed off)
- The technical documentation section of the customer delivery package
- File for TÜV/CE certification

---

## 2. As-Built Content Template

```markdown
# AS-BUILT DOCUMENTATION
## Project: <Project_Name>  | Customer: <Customer>  | Delivery: <YYYY-MM-DD>

## 1. Executive Summary
- System purpose + main components + capacity/performance + critical notes

## 2. Hardware Configuration   (RD01 IO + HW config)
## 3. Software Architecture     (RD10 FBSpec + RD03 Flowchart + Mermaid)
## 4. Safety System              (RD05 APPROVED + SIL/PLr + engineer signature)
## 5. Communication              (RD09 + network topology + IP plan)
## 6. HMI                        (RD11 + screen hierarchy + access matrix)
## 7. Alarm Management           (RD08 multi-lang + ISA-18.2 indicators)
## 8. Operating Procedures       (RD12 UseCase normal/emergency/maint)
## 9. Test Records               (FAT/SAT pass/fail + response time measurement)
## 10. Maintenance Schedule      (lubrication/filter/calibration/proof test)
## 11. Spare Parts List          (RD01 SourceModule + manufacturer ordering)
## 12. Contact + Support

## Appendix A: Tag List           (RD01)
## Appendix B: Variable Dictionary (RD02)
## Appendix C: FB Inventory        (RD10)
## Appendix D: SCL Source Code     (03_PLC/SCL/)
## Appendix E: HMI Screenshots     (RD11)
## Appendix F: Risk Assessment     (reference)
## Appendix G: CE Conformity Decl. (if any)
```

---

## 3. System Prompt

```
You are an As-Built documentation generator. Take all RDs + generated code + test reports,
and produce a professional technical document.

LANGUAGE: PROJECT_MAESTRO.md output_language (DE/EN/TR)
FORMAT: Markdown + PDF (pandoc render)
STYLE: Professional technical, readable years later, diagram-rich

OUTPUT: as_built.md + as_built.pdf
```

---

## 4. Multi-Language + PDF Render

```bash
# Markdown → PDF (pandoc + xelatex)
pandoc as_built.md -o as_built.pdf \
  --template=industrial-asbuilt.tex \
  --pdf-engine=xelatex \
  --toc --toc-depth=3 \
  --highlight-style=tango \
  -V geometry:margin=2cm
```

---

## 5. Related Files

- **Previous:** All RD specs, FAT/SAT reports
- **Other doc gen:** `PROMPT_DOC_GEN_OPERATOR_MANUAL.md`, `PROMPT_DOC_GEN_CASE_STUDY.md`
- **Standards:** GAMP 5 (pharma), VDI 4500 (technical documentation)

---

*v1.1.0 — Full English body (2026-05-23). v1.0.0: As-Built = the project's historical record. Done well, the customer still uses it 20 years later.*
