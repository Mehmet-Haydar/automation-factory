---
title: Retrofit IO Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md]
---

# RETROFIT_IO_EXTRACT.md

> **Goal:** when retrofitting an existing machine, systematically extract the IO list from EPLAN schematics and import it into TIA Portal.

---

## 1. Prerequisites

- [ ] Customer's EPLAN P8 project received (`.zw1` or PDF)
- [ ] If PDF, OCR quality checked (scanned vs vector?)
- [ ] Data classification performed: customer schematics → 🟠 CONFIDENTIAL
- [ ] Work environment: closed network OR self-hosted AI

---

## 2. Workflow

### 2.1 Raw Data Extraction from EPLAN

#### Method A — EPLAN P8 available (most accurate)

1. Open EPLAN P8 → `Utilities → Reports → Generate Report`
2. Report type: **PLC card overview** or **Terminal diagram**
3. Format: **XLSX** (instead of CSV — avoids Turkish-character issues)
4. Output file: `<project>/03_PLC/IO_RAW_FROM_EPLAN.xlsx`

#### Method B — Only PDF available

1. Check whether the PDF is text-based or scanned:
   ```bash
   pdftotext -f 1 -l 1 schematic.pdf - | head -20
   ```
   - Empty/garbled output → scanned, OCR required (`ocrmypdf`)
   - Readable text → extract directly
2. Extract page by page:
   ```bash
   pdftotext -layout schematic.pdf io_raw.txt
   ```
3. Clean up manually (cross-references, headers, etc.)

#### Method C — Nothing available (field discovery)

See `RETROFIT_HARDWARE_ANALYSIS.md` → **Field walkdown** section.

### 2.2 Building the Standard IO Table

Target format (XLSX):

| Column | Description | Example |
|--------|-------------|---------|
| `Tag` | Tag conforming to the naming standard | `MOT_CV01_001_DRIVE` |
| `Type` | DI / DO / AI / AO / Comm | `DO` |
| `Address_Old` | Old PLC address | `Q4.2` |
| `Address_New` | New PLC address (provisional, post-mapping) | `Q12.2` |
| `Module` | Module slot/channel | `DI 16x24VDC / Slot 4 / Ch 2` |
| `Description` | English description | `Conveyor 1 main drive run command` |
| `Description_DE` | German description (when original is German) | `Förderer 1 Hauptantrieb Lauf` |
| `Voltage` | Signal voltage | `24VDC` |
| `Wire` | Wire number (EPLAN ref) | `=01+S1-X1:12` |
| `Cabinet` | Cabinet code | `+S1` |
| `Notes` | Field notes | `Replaced 2018, freq drive ABB ACS580` |

### 2.3 Tag Renaming

Legacy schematics usually contain German/mixed names. Fix per `GLOBAL_NAMING_STANDARD.md`.

**Automated conversion via AI:**

```
Prompt: "Read the Description column of the IO list below and propose new tag
names that conform to the GLOBAL_NAMING_STANDARD.md tag format
(TYPE_LOCATION_NUMBER_FUNCTION). If you don't know the location, write <LOC?>."

[Paste the XLSX content after anonymizing to PUBLIC/INTERNAL level]
```

### 2.4 Importing into TIA Portal

1. Convert XLSX to CSV (UTF-8, `;` delimited)
2. TIA Portal: `PLC tags → Import → Import file (CSV)`
3. In the mapping dialog:
   - `Tag` → `Name`
   - `Address_New` → `Address`
   - `Type` → `Data type` (Bool/Int/Real)
   - `Description` → `Comment`
4. After import, ALWAYS run `Compile` in TIA Portal → catch conflicts.

### 2.5 Validation

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project_path> \
  --check-naming \
  --check-addresses
```

Output:
- Tags that don't follow the standard
- Address conflicts
- Missing descriptions

---

## 3. Common Pitfalls (KB Records)

> This section is updated from project experience. See `06_KNOWLEDGE_BASE/KB_PITFALLS_RETROFIT_IO.md`.

- ❌ **Double-used address in EPLAN:** in legacy projects DI X.X may be wired to two sensors at once. Don't trust the AI; verify manually.
- ❌ **German characters (ä, ö, ü, ß):** they break in CSV import. Add UTF-8 BOM or convert.
- ❌ **Spare/Reserve labels:** signals marked `Reserve` in EPLAN must not be imported.
- ❌ **24VDC vs 230VAC mix:** legacy machines may have both on the same terminal block. Affects module selection.

---

## 4. AI Prompt Suggestion

`04_AI_PROMPTS/code_gen/PROMPT_IO_MAPPING.md` (not yet created, TODO).

Skeleton:
```
ROLE: You are a TIA Portal engineer.
INPUT: Raw IO list extracted from EPLAN (XLSX/CSV).
RULE: GLOBAL_NAMING_STANDARD.md.
TASK:
  1. Propose a Tag for every row (TYPE_LOCATION_NUMBER_FUNCTION format).
  2. Mark uncertain ones with <LOC?>, <NUM?>.
  3. Output XLSX-compatible CSV.
SECURITY: Customer data 🟠 CONFIDENTIAL — only run on a self-hosted AI.
```

---

## 5. Checklist

When the retrofit IO extraction is complete:

- [ ] All signals in the IO table
- [ ] All tags conform to `GLOBAL_NAMING_STANDARD.md`
- [ ] Old/new address mapping documented
- [ ] TIA Portal compile is clean
- [ ] At least 5 signals physically verified on site (visually/multimeter)
- [ ] `script_consistency_check.py` clean
- [ ] Any gaps/issues recorded in `KB_FEEDBACK_LOG.md`

---

*v1.1.0 — Full English body (2026-05-23). This procedure is applied identically in every retrofit project. For improvement suggestions, use `script_propose_update.py`.*
