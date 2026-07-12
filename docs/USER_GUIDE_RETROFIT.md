---
title: User Guide — Retrofit, end to end (old code in → TIA-ready program out)
version: 1.0.0
last_validated: 2026-06
last_updated: 2026-06-10
status: ACTIVE
---

# Retrofit User Guide — old S5/S7 code → new TIA program

This is the exact click path for the field workflow. Time budget for a
mid-size machine: ~1–2 hours of engineer time (most of it reviewing AI
drafts — by design).

## What you need

- API keys (Settings → provider cards): **Google** (Gemini — drawings/PDF
  analysis, OCR) and **Anthropic** (Claude — code analysis, drafts).
  The pre-flight check refuses to start if a needed key is missing.
- Old program export from **S5/S7 for Windows** (or STEP5/STEP7):
  text/AWL (`.awl`, `.txt`, `.stl`, `.src`) — or a **PDF print**.

  **Straight from a STEP5 archive folder** (e.g. `4711st.s5d`,
  `4711Z0.SEQ`, `*.INI`):
  - `.SEQ` (symbol table) → **drop it in as-is** — it carries tag +
    description (the raw IO list) and is read directly.
  - `.s5d` (binary program) → **cannot be read directly** (binary MC5
    code). Drop it in anyway: the tool detects the binary and tells you
    to export an AWL listing via S5/S7 for Windows. One export step —
    `File → Print/Export → AWL listing as text or PDF` — and you're done.
  - `.INI` (cross-reference) → not needed; skip.
- Optional: panel photos, EPLAN PDFs.
- For the direct TIA path: TIA Portal **V19, V20 or V21** on this machine
  + `pip install pythonnet` + an existing `.ap19`/`.ap20`/`.ap21` project
  with a PLC device in it.

## Step by step

### 1. Project + inputs
1. **New Project** (the primary button on the welcome screen) → pick the
   retrofit template and set customer, output language and data
   classification directly in the form.
2. Drop files into the project's `_raw/` folders:
   - `_raw/legacy_code/` — old code (text **or PDF**)
   - `_raw/drawings/` — EPLAN PDFs, P&IDs
   - `_raw/photos/` — panel/nameplate photos
3. Gate 1 panel shows what it found.

### 2. PDF extraction (only if you dropped code as PDF)
1. Gate 1 → **Extract PDF text**. Text-layer PDFs extract locally
   (pdfplumber). Scans need **OCR consent** (the PDF goes to Gemini
   Vision **unanonymized** — modal explains; consent is audited).
2. **Review & confirm** each transcription. Watch for O↔0, I↔1, B↔8 in
   addresses (`E 1.0` vs `E 1.O`). Pre-analysis refuses to run while any
   legacy PDF is unconfirmed.

### 3. Retrofit Pre-Analysis (AI)
1. **Start Retrofit Pre-Analysis** — the button lives inside the
   **Gate 1 page** (Gates view); the right-rail *Next step* card also
   points there. It opens a consent modal (note: photos/drawings are
   sent **without** anonymization — redact logos first). The modal also has an
   **Output language** selector (TR / EN / DE): generated prose — descriptions,
   comments, alarm/HMI texts — follows it, while tag names and SCL keywords
   stay English. The choice is saved per project and reused by the later
   generators (Topic Extraction, SCL, reports).
2. **Gate 1 (Discovery)** generates only the discovery RDs in the background:
   drawings → legacy analysis → RD01 (IO list), RD02 (data dict), RD03 (step
   sequence + Mermaid), RD13 (annotation). Drafts land in `metadata/` as
   **DRAFT_UNVERIFIED** (originals backed up to `metadata/_history/`;
   engineer-approved RDs are never overwritten — sidecar `.ai_draft.md`).

### 4. Engineer review (the real work) — 3-state verification
Each RD goes 🟡 **DRAFT** → 🟢 **reviewed** → 🔒 **locked**:
1. Open each RD via the doc row, verify every row against the machine, fix
   tags/addresses, then click **Approve** to turn it 🟢 (pre-approval;
   reversible). Editing a reviewed RD afterwards demotes it back to 🟡.
2. **Gate 2 (Extraction)** has its own **Start Topic Extraction** button that
   generates the remaining RDs — RD04–RD12, RD14 and RD05 — *using* the
   approved Gate-1 analysis. It stays **locked until RD01/02/03/13 are
   approved**, so you only build on an analysis you trust. Review those drafts
   the same way (🟢).
3. **RD05 (Safety) is AI-drafted too**, but turning it green requires a
   **named certified-engineer sign-off** (e.g. `H. Becker, TÜV`); the AI never
   guesses SIL/PLr and never has the final word.
4. When all RDs are 🟢, the **Human Review** gate (Gate 3) can be **locked**
   (🔒) with your signature — that bulk sign-off seals them and unlocks Code
   Generation (Gate 4).

### 5. Assemble Program (deterministic — no AI)
1. Gate 3/4 → **Assemble Program**. What happens:
   - RD01 devices are matched to the **curated library** (DOL/VFD/
     star-delta/soft-starter motors, on-off/3-way/modulating valves,
     analog scale, PID) — blocks are copied **verbatim** (SHA-256 proof
     in the report), never AI-regenerated.
   - Instance DBs (`iDB_*.db`) + `OB_Main.scl` with real field-signal
     bindings (feedbacks, overloads, main outputs). Control ports
     (start/stop/enable) stay default — they belong to the sequence FB.
   - Everything passes `scl_validator` + each block's contract gate.
2. Read `REPORTS/ASSEMBLY_REPORT.md`: the **#UNKNOWN** list and unwired-
   port TODOs are your remaining manual work — nothing is silently
   dropped.
3. Optional: **generate_sequence_fb** produces `FB_Seq_<Project>.scl`
   from your reviewed RD03 — the ONLY AI-generated code artifact.
   Review it like a junior engineer's first draft.

### 6. Into TIA Portal
**Path A — direct (Openness):**
1. Settings → **TIA Portal** card: enable the detected V19/V20 bridge,
   set PLC name + `.apXX` project path.
2. **Send to TIA** → import + **compile preflight** runs in TIA; the
   modal shows a **live step list** (Portal → Open project → Tags →
   SCL import → Compile → Save), with the raw log collapsible below
   (toggle: Settings → TIA Portal → "Send to TIA view"). The TIA
   Portal window itself opens visibly, so you can watch the blocks
   arrive. CONFIDENTIAL projects need a consent checkbox (local
   transfer — audited). First run: accept the Windows Openness
   firewall dialog once.
3. If the compile FAILS, the modal groups the errors by origin —
   **Compile error assistance** (Settings → TIA Portal):

   | Mode | What you get |
   |------|--------------|
   | Off | raw errors only — fix everything yourself in TIA |
   | Hints (default) | errors grouped by origin + a tip per group (no AI) |
   | AI suggest | + a **Propose fix (AI)** button on sequence-FB errors |
   | AI auto-propose | the proposal is pre-generated after a failed compile |

   The AI can only propose fixes for `FB_Seq_*` — the one AI-generated
   artifact. Library blocks (SHA-256 verified) and assembler output are
   never patched inside a project. A proposal is shown as a diff and is
   applied **only** after an engineer enters their name and approves
   (audited, old file backed up to `_output/scl/_history/`); re-running
   Import + Compile afterwards is always your manual click.
4. Clean compile ⇒ label upgrades to `AUTO_VERIFIED_compile |
   PENDING_PLCSIM_VERIFY` and the gate no longer needs the
   "accept structural-only" checkbox.
5. Optional: PLCSIM Advanced download (separate confirm; real-PLC
   downloads are hard-blocked by design).

**Path B — folder export (no TIA needed here):**
**Export TIA** → `_output/tia_import/` with sources sorted into
ProgramBlocks/GlobalDB/UDT + an import checklist. Drag into TIA's
External Sources and "Generate blocks from source".

### 7. What is still YOURS (by design — not tool gaps)

- **TODO ports + #UNKNOWN devices** (from `ASSEMBLY_REPORT.md`): the
  assembler binds only what it is *certain* about. Ambiguous signals and
  unmapped devices are listed for you — wiring them takes minutes in
  TIA; guessing them wrong in software costs hours in the field.
- **Sequence FB review**: treat `FB_Seq_<Project>` like a junior
  engineer's first draft — read every transition.
- **RD05 / functional safety — entirely human.** Approval does NOT make
  the AI write safety code; it never does, under any consent. It only
  *reports* safety signals it found in the legacy code. F-programs:
  certified engineer, TIA Safety.
- **PLCSIM behavioural test + FAT/SAT (Gates 6–7).** Compile preflight
  proves the code compiles, not that the logic is right. Download to
  PLCSIM is one click; running start/stop/timeout scenarios at the watch
  table is still your job (automated behaviour harness = next roadmap
  item).

### Output format — what exactly do I get?

TIA Portal **external sources**: `.scl` files (device FBs, `OB_Main`,
sequence FB) + `.db` files (instance DBs) + IEC tag table. These import
directly: **Send to TIA** does it via Openness (import + compile into
*your* existing `.ap19/.ap20/.ap21` project), or **Export TIA** gives a
folder for TIA's *External Sources → Generate blocks from source*. A
ready-made `.ap21` cannot be produced outside TIA Portal — no tool can;
that is precisely why the Openness path drives TIA itself.

> **OPC UA note (TIA V21):** OPC UA affects how the *running* PLC talks
> to SCADA/MES — it does not change code generation or import. Relevant
> for RD09 (Comms) planning only.

## Honest labels

| Label | Means |
|---|---|
| `DRAFT_UNVERIFIED` | AI draft — review every row |
| `AUTO_VERIFIED_structural` | keyword/structure checks only — NOT compiled |
| `AUTO_VERIFIED_compile` | compiled clean in TIA via Openness — NOT simulated |
| `PENDING_PLCSIM_VERIFY` | behavioural simulation still pending |

Anything below the last row is **not field-ready**. The tool's promise is
"~90% of the *typing*", not 90% of the *engineering*.
