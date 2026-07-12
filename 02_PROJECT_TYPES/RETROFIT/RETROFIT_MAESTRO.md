---
title: Retrofit Project Master Workflow
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
prerequisite: [FACTORY_MAESTRO.md, GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md]
---

# RETROFIT_MAESTRO.md

> **Goal:** end-to-end workflow for managing the PLC/HMI/electrical retrofit of an existing machine.

---

## 1. Retrofit ≠ Greenfield

| Dimension | Retrofit | Greenfield |
|-----------|----------|------------|
| Mechanical | Exists, preserved | New |
| Electrical | Partially/fully replaced | New |
| PLC/HMI | Replaced | New |
| Process flow | Unknown → must be discovered | Designed |
| Risk | High (unknowns + downtime) | Medium |
| Duration | 2-6 months | 6-18 months |
| **Core work** | **Understand + adapt** | **Design + select** |

In a retrofit you are not building the machine — you are **re-interpreting** it.

---

## 2. Phase 1: Discovery (week 1)

### 2.1 Customer Information Gathering

- [ ] Retrofit scope: PLC only? PLC + HMI? Cabinet included?
- [ ] Legacy PLC: brand, model, version (S5? S7-300? Allen-Bradley?)
- [ ] Legacy HMI: WinCC Flexible? OP/TP? 3rd-party SCADA?
- [ ] Existing documentation: EPLAN P8? PDF only? None?
- [ ] Production cadence: shifts, downtime tolerance, commissioning window
- [ ] Operator profile: language, experience, training needs

**Output:** `01_DOCS/RETROFIT_SCOPE.md`

### 2.2 Field Discovery

Details: `RETROFIT_HARDWARE_ANALYSIS.md` → Field walkdown.

- [ ] Sensor positions photographed
- [ ] Motor/actuator brand-model-rating nameplates recorded
- [ ] High-resolution photos of cabinet interior
- [ ] Legacy PLC program uploaded (online from CPU)
- [ ] Data classification: 🟠 CONFIDENTIAL active

### 2.3 Modelling the Existing Flow

From the legacy program or operator interviews, derive **how the machine actually runs**.

Output: `RETROFIT_FLOWCHART.md` (Mermaid).

Rules when using AI for flow extraction:
- Code is 🟠 CONFIDENTIAL → self-hosted/Enterprise AI
- Even if the AI infers the flow, **operator confirmation is mandatory** (code vs. real behaviour drift)

---

## 3. Phase 2: IO Extraction & Standardisation (weeks 2-3)

Details: `RETROFIT_IO_EXTRACT.md`

Summary:
1. Raw IO from EPLAN/field discovery
2. AI-assisted naming-standard alignment
3. Old ↔ new address mapping
4. TIA Portal import + compile
5. Validation via `script_consistency_check.py`

**Gate:** no hardware purchase until this phase closes.

---

## 4. Phase 3: Hardware Selection (weeks 3-4)

Details: `RETROFIT_HARDWARE_ANALYSIS.md`

- Module selection based on IO type/count
- Compatibility of legacy drives (keep or replace?)
- Safety: is F-PLC required? SIL/PL assessment
- Network: Profibus → Profinet migration?
- Customer standard: preferred module series

**Gate:** BOM approval + order placed.

---

## 5. Phase 4: Software Development (weeks 4-12)

### 5.1 Project Setup

- [ ] Create empty TIA Portal project
- [ ] PLC + network configuration (`DOMAIN_COMMS_NETWORK_PLAN.md`)
- [ ] Import PLC tags (from Phase 2)
- [ ] **Symbol-table contract:** tags are frozen — no changes from this point on

### 5.2 FB Development

For each machine function use the matching AI prompt:
- Motor → `04_AI_PROMPTS/code_gen/PROMPT_CODE_GEN_FB_MOTOR.md` (router) → sub-prompt
- Valve → `04_AI_PROMPTS/code_gen/PROMPT_CODE_GEN_FB_VALVE.md`
- Sequence → `04_AI_PROMPTS/code_gen/PROMPT_CODE_GEN_SEQUENCE.md`

**Rule:** every FB must pass simulation first (`DOMAIN_SIMULATION_PROCESS_MODEL.md`), then go to the field.

### 5.3 HMI Development

Details: `DOMAIN_HMI_STANDARD.md`

Retrofit-specific: **bridge the old HMI to the new one.** The operator already knows the old screens — preserve layout familiarity while improving the functionality. Otherwise expect operator resistance.

### 5.4 Test (lab)

- Unit tests → `DOMAIN_TESTING_UNIT.md`
- Integration tests → `DOMAIN_TESTING_INTEGRATION.md`
- FAT → `DOMAIN_TESTING_FAT.md`

---

## 6. Phase 5: Commissioning

### 6.1 Preparation (1 week before)

- [ ] Backups taken (old PLC program, old HMI project)
- [ ] **Rollback plan written** (retrofit fails → procedure for returning to the old system)
- [ ] Operator training delivered
- [ ] Critical spare-parts stock (fuses, contactors, sensors) ready

### 6.2 Commissioning (1-2 weeks)

Sequential approach:
1. **Power-on test** (control voltage, no motors)
2. **IO test** (every signal, multimeter + PLC monitoring)
3. **Solo test** (each motor/valve alone, manual mode)
4. **Sequence test** (auto mode, low speed)
5. **Production test** (real material, observation)
6. **SAT** → `DOMAIN_TESTING_SAT.md`

### 6.3 Post-Commissioning

- [ ] 2 weeks on-site support
- [ ] As-built documentation: `06_REPORTS/AS_BUILT.md`
- [ ] Lessons learned → Factory feedback log

---

## 7. Phase 6: Close-out

- [ ] Signed customer acceptance
- [ ] Source files archived
- [ ] **At least 1 piece of feedback sent to the Factory** (mandatory)
- [ ] NDA-bound data deleted as required
- [ ] Warranty start date recorded

---

## 8. Typical Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Existing wiring does not match EPLAN | High | 100% verification during walkdown |
| Legacy sensor faulty, new PLC can't see it | Medium | Catch during IO test phase |
| Customer extends downtime | High | Rollback plan mandatory |
| Operator resistance (new HMI) | High | Layout familiarity + early training |
| Profinet retrofit delays | Medium | Communications diagnostics monitoring |
| Safety upgrade detected late | High | SIL/PL evaluation in Phase 1 |

---

## 9. AI Usage Notes

- 🟠 CONFIDENTIAL data is never sent to a public AI
- AI is very useful for naming transforms (`PROMPT_REVIEW_NAMING.md`)
- AI is useful for inferring flow from legacy PLC code (operator validation mandatory)
- FB generation uses the motor/valve sub-prompts
- AI can suggest HMI designs, but customer standards take precedence

---

## 10. Phase-Transition Checklist

- [ ] **Phase 1:** Discovery → SCOPE.md, FLOWCHART.md complete
- [ ] **Phase 2:** IO list standardised, TIA import clean
- [ ] **Phase 3:** BOM approved, order placed
- [ ] **Phase 4:** FBs pass simulation, FAT complete
- [ ] **Phase 5:** SAT signed, in production
- [ ] **Phase 6:** Factory feedback delivered, project closed

---

*v1.1.0 — Full English body (2026-05-23). This document is read at the start of every retrofit project. Deviations are fed back via `script_propose_update.py`.*
