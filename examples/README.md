---
title: "examples/ — Synthetic Demo Projects"
last_validated: 2026-07
status: ACTIVE
---

# `examples/` — Synthetic Demo Projects

> ⚠️ **This folder contains SYNTHETIC examples.** No real customer data.
> Purpose: training, demos and pattern reference.

---

## The Important Distinction: Synthetic vs. Real Customer Project

### This folder (`examples/`)
- ✅ INSIDE the factory, public on GitHub
- ✅ Synthetic customers (invented names like "Kunde Müller GmbH")
- ✅ Invented data (47 signals, fake AWL code snippets)
- ✅ Training + demo material
- ✅ Reference for new engineers

### Real customer projects
- ❌ OUTSIDE the factory, separate folder tree
- ❌ Never committed to this repo
- ❌ 🟠 CONFIDENTIAL data class
- ❌ Customer-owned; NDAs apply

**Recommended location:** a `customer_projects/` folder next to the factory.

```
D:\automation_workspace\
├── AUTOMATION_FACTORY\        ← this repo (incl. synthetic examples/)
└── customer_projects\         ← real customer projects (OUTSIDE the factory)
    ├── CustomerA_Conveyor_2026\
    ├── Arcelik_Press_2026\
    └── ...
```

---

## Available Synthetic Examples

### 1. `Kunde_Mueller_Conveyor_Retrofit/`

**Scenario:** retrofit of a 1995 S7-300 conveyor system (Germany, synthetic
customer).

**What it demonstrates:**
- Legacy PLC code (AWL) → modern SCL conversion
- All files of the 14-Point Raw Data Pack
- An RD05 Safety **CRITICAL finding example** (no F-PLC)
- RD14 modernization decision matrix (retrofit vs. greenfield)
- Generated code with German comments
- Multi-language HMI / alarm texts (DE/EN/TR)

**How to explore:** [Kunde_Mueller_Conveyor_Retrofit/README.md](Kunde_Mueller_Conveyor_Retrofit/README.md)

### 2. `Demo_Beispielmaschine_4711/`

**Scenario:** a Step5-era machine (synthetic) taken through the CURRENT
pipeline end-to-end — the stronger, more recent showcase.

**What it demonstrates:**
- Direct S5 legacy import and extraction on the current pipeline
- Library-first assembly output (`_output/scl/*.scl`) with the
  `REPORTS/ASSEMBLY_REPORT.md` proof trail
- TIA import bundle (`_output/tia_import/*.xml`) with a recorded
  TIA compile result (`REPORTS/gate_results/tia_compile.json`)
- A project advanced to Gate 4 with the real gate/state machinery

**How to explore:** [Demo_Beispielmaschine_4711/README.md](Demo_Beispielmaschine_4711/README.md) —
also referenced by the walkthrough in [docs/SHOWCASE.md](../docs/SHOWCASE.md).

---

## Adding a New Synthetic Example

When adding a new training demo:

1. **Use a synthetic name** — "Customer Demo", "Test GmbH", "Example Corp", …
2. **No real data leakage** — private IPs only (192.168.x.x), generic tags
3. **Customer identity must stay ambiguous** — industry category is fine,
   a specific company name is not
4. **Mark the README as SYNTHETIC** — start with the ⚠️ banner

Template layout:
```
examples/<synthetic_project_name>/
├── README.md (⚠️ SYNTHETIC banner + scenario)
├── PROJECT_MAESTRO.md
├── PROJECT_STATE.json
├── _input/ (synthetic source data)
├── metadata/RD01..RD14 (filled examples)
└── _output/ (generated code samples)
```

---

## Starting a Real Customer Project

NOT in this folder — under `customer_projects/`:

```bash
# Workspace layout:
# D:\automation_workspace\
# ├── AUTOMATION_FACTORY\      ← here
# └── customer_projects\       ← customers go here

# Script call (inside the FACTORY):
python 05_SCRIPTS/script_project_init.py \
  --name "Real_Customer_Project" \
  --type retrofit \
  --customer "Real Customer Inc" \
  --output "D:\automation_workspace\customer_projects" \
  --output-lang EN
```

---

## Details

- **Installation:** [INSTALLATION.md](../INSTALLATION.md)
- **Folder layout recommendation:** [README.md](../README.md)
- **Data classification:** `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`

---

*Synthetic examples are the factory's showroom. Real production lives in a
separate folder.*
