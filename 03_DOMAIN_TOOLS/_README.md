---
title: 03_DOMAIN_TOOLS — Folder README
version: 1.1.0
last_updated: 2026-05-23
status: ACTIVE
last_validated: 2026-05
---

# `03_DOMAIN_TOOLS/` — Industry-Domain-Specific Standards

> **This folder holds knowledge specific to particular industries/domains.** Domain guides for HMI standards, drive configuration, communication protocols, safety, and testing (FAT/SAT/Integration).

---

## 1. Current Files

```
03_DOMAIN_TOOLS/
├── _README.md  ← this file
│
├── DOMAIN_COMMS_NETWORK_PLAN.md       (STUB)
├── DOMAIN_COMMS_PROTOCOLS.md          (STUB)
├── DOMAIN_DRIVES_CONFIG.md            (STUB)
├── DOMAIN_HMI_STANDARD.md             (STUB)
├── DOMAIN_OPENNESS_INTEGRATION.md     (STUB)
├── DOMAIN_SAFETY_CONFIG.md            (STUB)
├── DOMAIN_SIMULATION_PROCESS_MODEL.md (STUB)
├── DOMAIN_TESTING_FAT.md              (STUB)
├── DOMAIN_TESTING_INTEGRATION.md      (STUB)
├── DOMAIN_TESTING_SAT.md              (STUB)
└── DOMAIN_TESTING_UNIT.md             (STUB)
```

---

## 2. Status

> ⚠️ **Most files in this folder are STUBs (v0.1.x).** Under v3.0.0-alpha the pipeline + 14-point pack + AI prompts were prioritised. Domain details are pushed to v3.1.0+ sprints.

---

## 3. Fill-In Priority (Future)

| Sprint | File | Reason |
|--------|------|--------|
| v3.1.0 | DOMAIN_HMI_STANDARD.md | ISA-101 + multi-lang HMI text |
| v3.1.0 | DOMAIN_SAFETY_CONFIG.md | F-PLC topology + risk assessment |
| v3.2.0 | DOMAIN_DRIVES_CONFIG.md | SINAMICS / Servo parameter reference |
| v3.2.0 | DOMAIN_COMMS_PROTOCOLS.md | PROFINET / EtherCAT / OPC UA detail |
| v3.3.0 | DOMAIN_TESTING_FAT.md | Gate 7 FAT procedure template |
| v3.3.0 | DOMAIN_TESTING_SAT.md | Site-acceptance test template |
| v3.4.0 | DOMAIN_SIMULATION_PROCESS_MODEL.md | Gate 6 simulation environment |

---

## 4. Usage

The existing RD specs (01_GLOBAL_STANDARDS/md_schemas/) carry the general rules.
Domain files are for **industry/product-specific** details.

Example:
- RD06 Motion = general motion spec (PLCopen)
- DOMAIN_DRIVES_CONFIG = SINAMICS S120 parameter table

---

## 5. STUB Fill-In Standard

Before filling in a STUB:
1. Version bump v0.1.x → v1.0.0 (status: ACTIVE)
2. Identify reference files (similar filled file)
3. Domain-expertise check (subject knowledge required)
4. Must be written by an engineer, not AI (experience needed)

---

## 6. Related Folders

- `01_GLOBAL_STANDARDS/md_schemas/` — General RD specs (this folder elaborates on them)
- `06_KNOWLEDGE_BASE/` — Pitfalls (KB_PITFALLS_*) reference these domains
- `02_PROJECT_TYPES/` — Project guides draw on these domains

---

*Domain knowledge accumulates over years. This folder grows slowly but deeply.*
