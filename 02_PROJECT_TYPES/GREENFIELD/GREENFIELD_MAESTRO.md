---
title: Greenfield Project Master Workflow
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
prerequisite: [FACTORY_MAESTRO.md, GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md]
---

# GREENFIELD_MAESTRO.md

> **Goal:** end-to-end management of the PLC/HMI/electrical project for a brand-new machine or line built from scratch.

---

## 1. Greenfield ≠ Retrofit

See `RETROFIT_MAESTRO.md` §1.

In greenfield, the core work is **the right design decisions + the right component selection**. There are no unknowns, but everything has to be defined.

---

## 2. Phase 1: Spec and Design (weeks 1-3)

### 2.1 Spec Gathering

If the customer has no spec document (URS — User Requirement Specification), **build it together**:
- [ ] Production target (parts/hour, kg/hour, etc.)
- [ ] Quality requirements (tolerance, defect rate)
- [ ] Operations profile: how many product variants (recipe count)?
- [ ] Environment: temperature, humidity, contamination (drives IP class)
- [ ] Safety: SIL/PL target (`DOMAIN_SAFETY_CONFIG.md`)
- [ ] Standards: are CE, ATEX, FDA, GMP-style certifications required?

**Output:** `01_DOCS/PROJECT_SPEC.md`

### 2.2 Flow Design

See `GREENFIELD_FLOWCHART.md`

- Process steps, transition conditions
- Operating modes: manual, semi-auto, full-auto
- Recipe structure (if any)
- HMI page hierarchy draft

Using AI for flow design:
- Rough draft first: user stories + AI suggestions
- Then Mermaid diagrams
- Customer review → revise → approve

### 2.3 IO Design

See `GREENFIELD_IO_NEWDESIGN.md`

- A tag for every actuator/sensor (per the naming standard)
- Module density (DI/DO/AI/AO module ratio)
- 20% spare ratio (for expansion)

**Output:** `IO_LIST.xlsx` (TIA Portal import-ready)

---

## 3. Phase 2: Hardware Selection (weeks 3-5)

Details: `GREENFIELD_HARDWARE_SELECTION.md`

- PLC selection: S7-1200 vs 1500 vs 1500F
- IO modules (per the IO list)
- HMI: Comfort, Unified, 3rd party?
- Drives (per motor type)
- Network: Profinet topology, switches
- Safety components (E-stops, light curtains, F-PLC)
- Cabinet-builder coordination (EPLAN schematics)

**Gate:** BOM approval + order placed.

---

## 4. Phase 3: Software Development (weeks 5-14)

### 4.1 Project Setup

- [ ] TIA Portal project
- [ ] PLC/network config (`DOMAIN_COMMS_NETWORK_PLAN.md`)
- [ ] Import PLC tags (from Phase 1.3)
- [ ] **Symbol table frozen** — any change requires a request

### 4.2 FB Development

In greenfield it makes sense to build a library:
- `Library_<CustomerName>` or `Library_<ProjectType>`
- Each FB versioned
- The same motor type uses the same FB across the whole project

Prompts:
- Motor → `PROMPT_CODE_GEN_FB_MOTOR.md` (router)
- Valve → `PROMPT_CODE_GEN_FB_VALVE.md`
- Sequence → `PROMPT_CODE_GEN_SEQUENCE.md`
- Recipe → custom (if needed)
- Alarm management → custom

### 4.3 HMI Development

`DOMAIN_HMI_STANDARD.md`. In greenfield:
- Page hierarchy comes from the design
- Icon/colour standards consistent from day one
- Multi-language support (if required)

### 4.4 Test (lab)

- Unit + Integration → `DOMAIN_TESTING_UNIT.md`, `DOMAIN_TESTING_INTEGRATION.md`
- Simulation mandatory → `DOMAIN_SIMULATION_PROCESS_MODEL.md`
- FAT → `DOMAIN_TESTING_FAT.md`

---

## 5. Phase 4: Commissioning

### 5.1 Preparation

- [ ] Mechanical done, electrical done (mechanical first!)
- [ ] Site readiness checks (ventilation, compressed air, water, etc.)
- [ ] Operator training plan
- [ ] Spare-parts stock

### 5.2 Commissioning

1. Power on the control voltage (before loop test)
2. **Loop test** (every IO signal actually reaches the field)
3. Solo test (each actuator manually)
4. Sequence test (auto, low speed)
5. Production test (real material)
6. **Performance test** (can it really hit the production target?)
7. SAT → `DOMAIN_TESTING_SAT.md`

### 5.3 Ramp-up

In greenfield, the production target is hit **gradually**:
- Week 1: 30% capacity
- Week 2: 60%
- Weeks 3-4: 100%

During this period alarm/fault logs are collected → feedback into the library.

---

## 6. Phase 5: Close-out

- [ ] Signed customer acceptance
- [ ] Performance KPIs documented
- [ ] As-built documentation
- [ ] Promote library FBs into the Factory: are they reusable?
- [ ] **Factory feedback** (mandatory)
- [ ] Warranty start

---

## 7. Greenfield-Specific Risks

| Risk | Mitigation |
|------|------------|
| Spec missing/changing | URS sign-off + change-request procedure |
| Mechanical delay blocks PLC work | Simulation mandatory, run in parallel |
| Customer pressure to "add one more thing" | Scope creep → formal change request |
| Architectural mistake found at FAT | Architecture review mandatory in Phase 3.1 |
| Very new technology (e.g. brand-new TIA version) | Pilot project + customer acceptance |

---

## 8. Library Mindset in Greenfield

A greenfield project is a **library opportunity**. If a second project comes from the same customer:
- Deliver the **library**, not just the FBs
- Version it, document it
- The new project only changes configuration

In the long run this strategy is the single biggest source of added value.

---

## 9. Checklist

- [ ] **Phase 1:** spec + flow + IO design done, customer approval
- [ ] **Phase 2:** BOM approved, order placed
- [ ] **Phase 3:** FBs delivered as a library, FAT passed
- [ ] **Phase 4:** commissioning complete, performance KPI met
- [ ] **Phase 5:** close-out + Factory feedback

---

*v1.1.0 — Full English body (2026-05-23). Read at the start of every greenfield project.*
