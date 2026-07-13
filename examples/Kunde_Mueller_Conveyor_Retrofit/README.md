---
title: Kunde Müller Conveyor Retrofit — Example Project
last_validated: 2026-05
status: ACTIVE
---

# Kunde Müller Conveyor Retrofit — Example Project

> ⚠️ **This is a synthetic example project.** Not customer data — an end-to-end
> demo designed to show how AUTOMATION_FACTORY works. ("Kunde Müller GmbH" and
> the engineer names are invented.)

---

## Project Scenario

**Customer:** Kunde Müller GmbH (Germany, Düsseldorf) — *fictional*
**Machine:** conveyor line installed in 1995
**Old platform:** Siemens S7-300 (CPU 315-2DP, STEP 7 V5.5 Classic)
**New platform:** Siemens S7-1500F (CPU 1515F-2 PN, TIA Portal V18)
**Project type:** Retrofit
**Language:** German customer → code comments + HMI = DE
**Data class:** 🟠 CONFIDENTIAL

**Scenario:**
- The customer wants to modernize the old PLC (no spare parts left).
- E-Stop is driven from a standard Q output (no F-PLC) → SAFETY CRITICAL finding.
- Conveyor motor + palletizer servo + 2 light curtains.
- HMI panel to be renewed (old WinCC Classic → TIA WinCC Unified).

---

## Folder Layout

```
Kunde_Mueller_Conveyor_Retrofit/
├── README.md                          ← this file
├── PROJECT_MAESTRO.md                 ← project orchestrator
├── PROJECT_STATE.json                 ← machine-readable state
│
├── _input/                            ← old code (synthetic)
│   ├── _parsed.md                     ← platform-parser output
│   ├── old_code_snippet.awl           ← example AWL snippet
│   └── operator_manual_excerpt.md     ← operator notes
│
├── metadata/                          ← 14-Point Raw Data Pack (filled)
│   ├── RD01_IO_List.md             ✅ EXAMPLE
│   ├── RD02_DataDict.md               ✅ EXAMPLE
│   ├── RD03_Flowchart.md              (placeholder)
│   ├── RD04_Mode.md                   ✅ EXAMPLE
│   ├── RD05_Safety_DRAFT_UNVERIFIED.md ✅ EXAMPLE (critical finding)
│   ├── RD06_Motion.md                 (placeholder)
│   ├── RD07_Timing.md                 (placeholder)
│   ├── RD08_Alarm.md                  ✅ EXAMPLE
│   ├── RD09_Comms.md                  (placeholder)
│   ├── RD10_FBSpec.md                 ✅ EXAMPLE
│   ├── RD11_HMI.md                    (placeholder)
│   ├── RD12_UseCase.md                (placeholder)
│   ├── RD13_Annotation.md             ✅ EXAMPLE
│   └── RD14_Modernization.md          ✅ EXAMPLE (decision matrix)
│
└── _output/
    └── FB_Motor_Conveyor.scl          ✅ Gate-5 example SCL (AUTO_VERIFIED_structural | PENDING_TIA_VERIFY)
```

> ⚠️ **This is a synthetic example.** The metadata (RD*) files are drafts
> prepared by hand/AI; this is not a real customer project and has not passed
> human approval. **The Gate-5 output (`_output/FB_Motor_Conveyor.scl`) is
> structurally verified (`AUTO_VERIFIED_structural`) but `PENDING_TIA_VERIFY`** —
> no TIA Portal compile + PLCSIM run was performed. An engineer must compile and
> simulate it before production use. The example shows Gates 1–3 + one example
> Gate-5 SCL draft.

---

## How to Review

### 1. PROJECT_MAESTRO.md
The main document showing overall project status and references.

### 2. _input/_parsed.md
The project summary the platform-parser AI produced from the old S7-300 code.
**This is the factory's "first understanding" output.**

### 3. metadata/RD01_IO_List.md
47 signals — old absolute addresses mapped to the **new naming standard**.

### 4. metadata/RD05_Safety_DRAFT_UNVERIFIED.md ⚠️
**CRITICAL FINDING:** E-Stop detected on a standard PLC. The AI carried this to
RD14 as CRITICAL.

### 5. metadata/RD14_Modernization.md
**Decision matrix:** Retrofit vs Greenfield vs Hybrid recommendation. F-PLC
migration is mandatory for SAFETY.

### 6. _output/FB_Motor_Conveyor.scl
Gate-5 example SCL — derived from RD10 FBSpec, based on the `FB_Motor_DOL`
library pattern (German comments). **Label:
`AUTO_VERIFIED_structural | PENDING_TIA_VERIFY`** — passed the structural gate,
but TIA compile + PLCSIM were NOT done; engineer verification required before use.

---

## Which Pipeline Stage?

```
Gate 1 DISCOVERY          ✅ Customer brief received (synthetic)
Gate 2 EXTRACTION         ✅ AI drafted all 14 RDs (synthetic)
Gate 3 HUMAN REVIEW       🔵 Under review (RD05 safety awaits an engineer)
Gate 4 VALIDATION         ⏸ once RD05 is approved
Gate 5 CODE GENERATION    🟡 Example SCL produced — AUTO_VERIFIED_structural | PENDING_TIA_VERIFY
Gate 6 SIMULATION         ⏸ Gate 6 (TIA compile + PLCSIM) not yet applied
Gate 7 FAT/SAT            ⏸
```

---

## Findings Detected

| ID | Severity | Category | Summary |
|----|----------|----------|---------|
| FND001 | CRITICAL | SAFETY | E-Stop on a standard PLC — F-PLC migration mandatory |
| FND002 | MAJOR | NAMING | 47 absolute addresses → semantic tags |
| FND003 | MAJOR | STRUCTURE | All logic in OB1 — no modular FB structure |
| FND004 | MAJOR | OBSOLETE_PLATFORM | S7-300, end-of-support platform |
| FND005 | MINOR | MAINTAINABILITY | ~30% uncommented code |
| FND006 | MINOR | ALARM | FC40 has 32 alarm bits, not ISA-18.2 |
| FND007 | MINOR | HMI | WinCC Classic, not ISA-101 |
| FND008 | **CRITICAL** | SAFETY | M50.0 maintenance bypass disables the E-Stop (FC10 NW5) |
| FND009 | **CRITICAL** | SAFETY | Fake E-Stop redundancy: NW5/NW6 asymmetry |

**Total effort estimate:** ~192 hours + hardware cost (F-PLC ~€18K)

**Recommendation:** GREENFIELD recommended — the 3 CRITICAL findings
(FND001/008/009) are solved in one pass by F-PLC migration; the hardware is
being renewed anyway.

---

## Regenerate / Verify this demo (deterministic, no API key)

> This section lists the fully **deterministic** (no-AI) steps. The commands
> below run **without an API key** so a fresh user can verify this example end
> to end. The AI gates (Gate 1 DISCOVERY / Gate 2 EXTRACTION / Gate 5 CODE
> GENERATION — produced with Claude/Gemini) **require an API key and are outside
> this runbook.**
>
> Commands run from the repo root (`automation-factory/`). A test venv is
> assumed; otherwise: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.
> Below, `python` = that venv's python.

### 1. Scaffold a fresh skeleton project (init smoke-test)

```bash
python 05_SCRIPTS/script_project_init.py \
  --name TestRetrofit --type retrofit \
  --customer "Test Customer" --output /tmp/init_test --output-lang DE
```

Expected: exit 0, **14 RD templates** (`RD01..RD14`) under `metadata/` + factory
references. (This is the same skeleton this example was derived from.)

### 2. Gate-4 naming consistency check (RD01 IO list)

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project examples/Kunde_Mueller_Conveyor_Retrofit \
  --check-naming \
  --io-file examples/Kunde_Mueller_Conveyor_Retrofit/metadata/RD01_IO_List.xlsx
```

Expected: exit **1** with a **findings list** — this is **by design**. RD01 is a
Gate-3 `DRAFT` and **deliberately contains the legacy naming**; the checker
reports tags not matching the `TYPE_LOC_NUM_FUNC` format of
`GLOBAL_NAMING_STANDARD.md` (`PC_LOAD_001`, `VAL_V01_OUT`, `LIGHT_GREEN`,
`ANALOG_*`, `F_I_EStop_*` …). This is exactly **FND002 (NAMING / MAJOR)** —
resolved during retrofit/greenfield migration (see `metadata/RD14_Modernization.md`).
Tags that already comply (`MOT_CV01_001_*`) pass clean. **These findings are the
example's pedagogical content; they "must not be fixed".**

### 3. Address conflict check (still TODO)

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project examples/Kunde_Mueller_Conveyor_Retrofit --check-addresses
```

Expected: exit 1 + "`--check-naming or --check-addresses required.`" — the
`--check-addresses` flag is a **not-yet-implemented TODO** (also marked `(TODO)`
in the checker's `--help`). This is a tool limitation, not an example-data error.

### 4. IO-list MD ↔ XLSX round-trip

```bash
python - <<'PY'
import sys; sys.path.insert(0, "workbench/core")
import io_list_io as io
from pathlib import Path
md   = Path("examples/Kunde_Mueller_Conveyor_Retrofit/metadata/RD01_IO_List.md")
xlsx = Path("examples/Kunde_Mueller_Conveyor_Retrofit/metadata/RD01_IO_List.xlsx")
md_rows, fm = io.read_md(md)
x_rows,  _  = io.read_xlsx(xlsx)
assert [r.tag for r in md_rows] == [r.tag for r in x_rows], "MD/XLSX tag mismatch"
print(f"OK: {len(md_rows)} rows, MD and XLSX tags match")
PY
```

Expected: exit 0, `OK: 26 rows, MD and XLSX tags match`. (The example RD01 table
has 26 display rows + a "…22 more signals…" placeholder; the real list has 47
signals.)

### 5. Schema validator — scope note

`05_SCRIPTS/dev/script_md_schema_validator.py` only knows the `PROMPT_CODE_GEN`
and `DOMAIN_REFERENCE` schemas; the **RD metadata (RAWDATA) schemas are not
registered in this deterministic tool**, so this example's `metadata/RD*.md`
files are outside this validator's scope (a tool scope, not an example-data error).

### 6. Full test suite

```bash
python -m pytest -q
```

Expected: **725 passed, 1 skipped**.

---

## What This Example Shows You

1. **How AI extraction produces a _parsed.md** → `_input/_parsed.md`
2. **What the 14-Point Pack looks like** → `metadata/RD*.md`
3. **How German/Turkish/English multi-lang is preserved** → `(orig: ...)` format in each file
4. **Why safety needs human approval** → `RD05_Safety_DRAFT_UNVERIFIED.md`
5. **How the modernization decision is made** → `RD14_Modernization.md` ModernizationDecision table
6. **What Gate-5 SCL output looks like** → `_output/FB_Motor_Conveyor.scl` (structurally-verified example)

> Note: Gate 6 (TIA compile + PLCSIM) and beyond are not part of this synthetic
> example; the Gate-5 SCL example is labelled `PENDING_TIA_VERIFY` (engineer
> verification required).

---

## Real Customer Project vs This Example

| | This example | Real project |
|--|--------------|--------------|
| Customer name | "Kunde Müller GmbH" (invented) | Real customer |
| Data | Synthetic (47-signal demo) | Hundreds/thousands of signals |
| Duration | Produced in one day (factory demo) | 2–6 months (per project complexity) |
| Approvals | NO human approval (example) | Human approval at every gate |
| Safety | Demo purpose | Certified engineer + TÜV process |

---

*This example shows the factory's capabilities. Real customer projects follow
this pattern but are always run under a human engineer's supervision.*
