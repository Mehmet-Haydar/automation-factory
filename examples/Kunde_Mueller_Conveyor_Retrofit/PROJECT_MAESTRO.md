---
project_id: KMG-2026-001
project_name: Kunde_Mueller_Conveyor_Retrofit
customer: Kunde Müller GmbH
project_type: retrofit
created: 2026-05-15
factory_version: v3.0.0-alpha
data_classification: CONFIDENTIAL
output_language: DE
safety_engineer: Eng. Hans Becker (TÜV cert. #DE-001234)
last_validated: 2026-05
---

# PROJECT_MAESTRO.md — Kunde_Mueller_Conveyor_Retrofit

> This project is managed to the **AUTOMATION_FACTORY** v3.0.0-alpha standards.
> *(Synthetic example — customer, engineers and dates are invented.)*

---

## 1. Project Meta

| Field | Value |
|------|-------|
| Project ID | KMG-2026-001 |
| Customer | Kunde Müller GmbH (Düsseldorf, DE) |
| Type | RETROFIT |
| Start | 2026-05-01 |
| Target SAT | 2026-09-30 |
| Data class | 🟠 CONFIDENTIAL |
| Output language | DE (Deutsch) |
| Project Lead | Mehmet Haydar |
| Safety Engineer | Hans Becker (TÜV cert.) |

---

## 2. Factory References

| Type | File | Version |
|-----|-------|-------|
| Pipeline | `PIPELINE_CODE_REWRITE.md` | v1.0.0 |
| Naming | `01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md` | v1.0 |
| Data classification | `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md` | v1.0 |
| Lang policy | `01_GLOBAL_STANDARDS/rules/GLOBAL_LANG_POLICY.md` | v1.0.0 |
| Retrofit maestro | `02_PROJECT_TYPES/RETROFIT/RETROFIT_MAESTRO.md` | v1.0 |
| FB template | `01_GLOBAL_STANDARDS/code_templates/GLOBAL_FB_TEMPLATE.scl` | v1.0 |
| Glossary | `01_GLOBAL_STANDARDS/lang_glossary/GLOSSARY_DE.md` | v1.0.0 |

---

## 3. Pipeline Gate Progress

```
Gate 1 DISCOVERY         [completed]  2026-05-01
Gate 2 EXTRACTION        [completed]  2026-05-15 (AI extraction + parsing)
Gate 3 HUMAN REVIEW      [in_progress] 2026-05-15..06-15 (RD05 safety eng.)
Gate 4 VALIDATION        [pending]
Gate 5 CODE GENERATION   [in_progress] (example FB_Motor produced)
Gate 6 SIMULATION        [pending]    PLCSIM Advanced environment to be set up
Gate 7 FAT/SAT           [pending]    FAT 2026-09-01, SAT 2026-09-15
```

---

## 4. 14-Point Raw Data Pack Status

| RD | File | Status | Source | Percent |
|----|-------|--------|--------|-------|
| RD01 | RD01_IO_List.md | DRAFT (AI) | AI extractor (S7-300 parser) | 90% |
| RD02 | RD02_DataDict.md | DRAFT (AI) | AI extractor | 85% |
| RD03 | RD03_Flowchart.md | DRAFT | (placeholder) | 20% |
| RD04 | RD04_Mode.md | DRAFT (AI) | AI + operator interview | 80% |
| RD05 | RD05_Safety_DRAFT_UNVERIFIED.md | **DRAFT_UNVERIFIED** | AI — **Eng. Becker review** | 60% |
| RD06 | RD06_Motion.md | DRAFT | (placeholder) | 30% |
| RD07 | RD07_Timing.md | DRAFT | (placeholder) | 30% |
| RD08 | RD08_Alarm.md | DRAFT (AI) | AI + WinCC export | 75% |
| RD09 | RD09_Comms.md | DRAFT | (placeholder) | 40% |
| RD10 | RD10_FBSpec.md | DRAFT (AI) | AI + manual | 70% |
| RD11 | RD11_HMI.md | DRAFT | (placeholder) | 30% |
| RD12 | RD12_UseCase.md | DRAFT | (placeholder, awaiting workshop) | 25% |
| RD13 | RD13_Annotation.md | DRAFT (AI) | AI annotation | 50% |
| RD14 | RD14_Modernization.md | DRAFT (AI) | AI + customer decision | 80% |

**Overall RD status (for this example):** 5 RDs filled in detail, 9 RDs placeholder.

---

## 5. Project-Specific Decisions

| Date | Decision | Reason | Decided by |
|-------|-------|-------|--------------|
| 2026-05-02 | Output lang: DE | Customer is German, operators speak German | Customer |
| 2026-05-08 | F-PLC migration mandatory | RD05 SAFETY CRITICAL finding | Safety Eng. + Customer |
| 2026-05-10 | GREENFIELD recommended (over Retrofit) | Hardware obsolete + F-PLC extra cost needed anyway | RD14 decision matrix |

---

## 6. Data Classification + AI Policy

```
data_classification: CONFIDENTIAL (🟠)
```

| Class | Applied |
|-------|-----------|
| 🟠 CONFIDENTIAL | Self-hosted Claude API (Anthropic Bedrock) used |
| 🟠 CONFIDENTIAL | Cursor Enterprise tier (code) |
| 🟠 CONFIDENTIAL | Public AI services (ChatGPT.com, claude.ai web) **FORBIDDEN** |

---

## 7. Safety (RD05) Tracking ⚠️

```yaml
safety_engineer:
  name: Hans Becker
  certification: TÜV Süd, IEC 61508
  cert_number: DE-001234
  contact: hans.becker@example.com

risk_assessment:
  document_id: KMG-RA-2026-001
  date: 2026-05-08
  iso_12100: COMPLETED
  result: SIL2 / PLr_d requirement (E-Stop)

sil_requirements:
  - function: SF001 EStop_Operator_Panel
    required: SIL2 / PLr_d
    achieved: PENDING (after F-PLC migration)
    status: DRAFT_UNVERIFIED
  - function: SF002 LightCurtain_Loading_Zone
    required: SIL3 / PLr_e
    achieved: PENDING
    status: DRAFT_UNVERIFIED
```

---

## 8. Team + Responsibility

| Role | Name |
|-----|------|
| Project Lead | Mehmet Haydar |
| Lead Engineer | Mehmet Haydar |
| Safety Engineer | Hans Becker (external consultant, TÜV) |
| HMI Designer | (TBD) |
| Customer Contact | Klaus Müller (production manager) |

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|----------|------|---------|
| F-PLC supply delay | Medium | High | Order early (Siemens lead time 8-12 weeks) |
| German terminology inconsistency | Low | Medium | Use glossary + customer review |
| Uncommented legacy code | High | Medium | RD13 Annotation + operator interview |
| TÜV process delay | Medium | High | Involve safety eng. early |

---

## 10. Sprint Log

| Sprint | Goal | Status |
|--------|-------|--------|
| 2026-W18 | Customer brief + Gate 1 | ✅ |
| 2026-W19 | _input collection + AI extraction | ✅ |
| 2026-W20-21 | Gate 3 review + safety analysis | 🔵 |
| 2026-W22-23 | RD14 final + customer decision | ⏳ |
| 2026-W24-30 | Gate 5 code generation | ⏳ |
| 2026-W31-35 | Gate 6 simulation | ⏳ |
| 2026-W36 | Gate 7 FAT | ⏳ |
| 2026-W39 | SAT + delivery | ⏳ |

---

## 11. Notes

- Customer wants all documentation in German (FAT report + Operator Manual)
- Extra budget approved for F-PLC migration (€18K hardware + ~80h engineering)
- The old machine's electrical schematics are on hand as EPLAN P8 (.zw1)

---

*This file is live. It is updated at every gate advancement.*
