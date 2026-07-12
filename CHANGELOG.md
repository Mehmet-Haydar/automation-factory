# Changelog

All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/) — SemVer.

## [3.10.0] - 2026-07-10

> HMI/reconciliation V2 package + two E2E-run finding fixes (F1-F5) + an
> independent multi-agent audit pass (privacy, dead-code, hygiene).

### Added — HMI & reconciliation V2 (2026-07-07)

- **Role-based RD layout** with reading mode and in-app xlsx preview.
- **RD11/RD08 grid editors**: locked/engineer columns, regeneration-proof.
- **Gate-3 reconciliation & preview**: cross-artifact consistency validator
  with named conscious-choice waivers; RED (safety-baseline) findings gate
  the lock unconditionally.
- **Decision-delta cascade engine** + dossier Old→Target view.
- **Approved wiring codegen**: FC_HMI_Wiring generated ONLY from named
  engineer approvals; baseline snapshot + REVISION_LOG delivery artifacts.
- **3-part sidebar**: Workdesk (edit/sign surfaces + badges) and a
  read-only Review pane replace the flat Reports list.
- **Direct .s5d import**: Step5 binary → AWL without an S5-für-Windows
  export (instruction-parity proven; KT timer constants recovered).

### Fixed — E2E finding fixes F1-F5 (2026-07-10)

- **S5D duplicate block versions** are no longer silently overwritten:
  the richest version wins, the discard is reported, counters stay honest.
- **IEC tag 24-char truncation collisions**: colliding long names get a
  stable hash suffix from the untruncated name; table-wide uniqueness
  is guaranteed and regeneration-stable.
- **HMI wiring legacy-operand fallback**: RD11 rows whose Notes lack
  `legacy <operand>` recover it deterministically from RD01 instead of
  dropping the row as "no physical twin".
- **#UNKNOWN classification**: assembly unknowns are grouped as
  operator-panel / internal-flag / possible-device-gap, gap-first, so the
  engineer reviews a short actionable list instead of a 295-line wall.
- **Output-ceiling warning**: routing a long-output task (preanalysis /
  SCL generation) to a provider hard-capped below 16k output tokens now
  warns in the consent modal before tokens are spent.

### Changed — audit pass (2026-07-10)

- Real customer/plant identifiers replaced with generic wording in code
  comments and test docstrings; a guard test keeps them out.
- Dead pre-v3.1 Gate-5 prompt pipeline removed from project_analyzer; the
  prompt library README now states what the runtime actually loads
  (library-first assembly unchanged).
- BM25 index writes are deterministic (sort_keys) — rebuilds no longer
  flood the git diff; remaining Turkish schema titles translated.

## [3.9.0] - 2026-07-02

> Public-release readiness: field-fitness audit fixes + the two-gear flow
> architecture. 1584+ tests passing; GUI smoke-tested live (CDP-driven).

### Added — Two-gear flow (engineer-centred redesign)

- **One-click full analysis**: the discovery consent modal offers
  *"Continue with topic generation automatically"* — one run drafts all 14
  RDs in a single continuous step tracker. The topic phase consumes the
  fresh **unreviewed** Gate-1 drafts by explicit engineer choice; the gap is
  recorded in job warnings and the completion message. Two-stage flow stays
  available (toggle off).
- **Risk-based approval (14 → 3)**: only `CRITICAL_RDS` — RD01 (IO list),
  RD03 (flowchart), RD05 (safety, named sign-off, W-A2 unchanged) — block
  gate advancement and the Gate-3 lock. Remaining produced RDs are stamped
  `auto-accepted (Gate-3 lock)`: honestly attributed in the audit trail,
  badged distinctly (🔒auto), still demoted by any file edit.
- **Delta assembly (change management)**: full assembly writes
  `_assembly_manifest.json` (device → RD01 row hash). The Gate-4 panel
  previews new/changed/removed devices and *Regenerate affected* rewrites
  only the touched instance DBs; unchanged files stay byte-for-byte
  (manual tweaks survive), OB_Main is rebuilt, removed devices are reported
  as orphaned — never deleted. Failed runs do not move the baseline.

### Added — Field-fitness (Monday-morning test) fixes

- `.s7p`/`.zap*`/`.ap*`/`.zip` project archives are now VISIBLE in the raw
  panel with format-specific export instructions (was: silent binary skip
  with a misleading STEP5 message); archive-only projects stop before
  burning AI tokens.
- Legacy-input size pre-warning (soft ~60k / hard ~150k tokens) + live size
  badge in the pre-analysis progress panel.
- TIA bridge preflight: missing `pythonnet` or the *Siemens TIA Openness*
  Windows group now yields `not_configured` with an actionable message —
  never a false READY; the Send-to-TIA panel shows manual SCL import steps
  when no bridge is usable.
- Honest scope: S7-1500-only output warning in the New Project wizard,
  *"Is this tool right for you?"* section in all three READMEs, TIA
  prerequisites spelled out in INSTALLATION.md, Gate 6 renamed
  **PLCSIM / Field Verify**.
- RD11/RD12 platform-based N/A suggestion on pre-TIA machines (S5/S7-300/400).
- Onboarding 3-step quick start; primitive dev workflows hidden from the
  GUI list (`DEV_ONLY_WORKFLOWS`); Gate-5 view states the structural-only
  validation scope.

### Fixed

- Hardcoded `v3.3.0` removed from `index.html` (version now always from
  `get_state()`).
- Dead `Backend.run_action` wrapper removed; unknown pipeline action ids
  surface loudly; silent `.catch(()=>{})` on the SISTEMA status fetch fixed.
- Sample fallback data de-personalized (`Demo` / `Engineer`).

### Changed

- RAG index loading cached (mtime-keyed) — bm25/metadata no longer re-parsed
  on every retrieve call.
- 8 TIA diagnostic scripts take `TIA_PROBE_PROJECT`; Factory IO launcher
  honours `FACTORYIO_EXE`.
- `.github`: issue/PR templates, dependabot; README build/licence badges.
- Dead `set_gate_override` API method and orphan JS wrapper entries removed.

---

## [3.8.1] - 2026-06-14

> Commits: `d64e14f` (security) · `0d345d1` (concurrency). 1383 tests passing.

### Fixed — Security hardening (independent müfettiş AUDIT-001..005)

- **AUDIT-001 Path-traversal** in `ingest_device`: `library_path` from AI output validated against repo root before write.
- **AUDIT-002 Consent chain**: `AutoFlowRunner` propagates `consent_confirmed` through all steps; hardcoded bypass removed.
- **AUDIT-003 Audit-log**: `AI_DECISION_LOG` now included in auto-commit; silent `AuditLogError` surfaced to logger.
- **AUDIT-004 IP leakage**: INTERNAL-classified projects anonymized before AI egress (same as CONFIDENTIAL).
- **AUDIT-005 PII soft-warn**: customer-name detection active on all AI call sites; warnings surfaced in GUI.

### Fixed — Concurrency

- **`PROJECT_STATE.json` race condition**: `Api._state_lock` (`threading.Lock`, class-level so test harness using `object.__new__` also benefits) added; central `_save_state()` helper serializes all 5 write points and the `_update_state_fields` read-modify-write loop.

---

## [3.8.0] - 2026-06-14

> Tag: `v3.8.0` at commit `e670aa3`. 1358 tests passing.

### Added — RAG-KB: Knowledge Base retrieval pipeline (offline-first)

- **KB Entry Contract** (`06_KNOWLEDGE_BASE/_SCHEMA_KB_ENTRY.md`): file-level
  `## metadata` YAML blocks + per-entry `<!-- metadata -->` HTML comments define
  `entry_id`, `category`, `severity`, `verified`, `source`, `vendor`.  5 existing
  KB files migrated; `_README.md §2` updated.

- **RAG engine** (`05_SCRIPTS/rag/`):
  - `ingest.py` — parses `KB_*.md` + `09_HARDWARE_LIBRARY/**/*.md` into chunk
    records; calls OpenAI `text-embedding-3-small` for semantic index
    (`_rag_index/metadata.json` + `embeddings.npy`).
  - **BM25 offline mode** (`--offline` flag) — builds `_rag_index/bm25.json`
    from TF/IDF without any API key. Index committed to repo so the pipeline
    works out of the box on a fresh clone.
  - `retrieve.py` — auto-selects mode: `embeddings.npy` present → semantic;
    only `bm25.json` present → keyword (BM25); neither → `RAGIndexNotFoundError`
    (silent empty list is prohibited).
  - `RAGIndexNotFoundError` in `rag/__init__.py` — fresh-clone guard.

- **Datasheet ingest** (`factory_web.ingest_device`): PDF → `pdfplumber` →
  AIClient prompt → device MD in `09_HARDWARE_LIBRARY/<category>/<vendor>/` →
  incremental RAG update. GUI "Datasheet" button now active (was `disabled`).
  EU AI Act Article 12 audit log written before provider contact.

- **Safety warning chain**:
  - `retrieve()` returns `rag_warning=True` for `severity: critical(safety)`.
  - `factory_web._rag_safety_check()` — graceful wrapper; works in BM25 mode
    without API key; returns `[]` on any error, never raises.
  - `factory_web._inject_rag_safety_box()` — prepends `⚠️ SAFETY NOTU` block
    to generated MD/PDF before delivery.
  - `app.js` — red banner `#pr-rag-banner` + "Gördüm, devam et" confirm button
    in FAT/SAT modal; modal stays open until confirmed.
  - `generate_fat()` / `generate_customer_report()` — RAG check runs first;
    `rag_warnings` key present in every response path including error paths.

- **OB1 vendor context injection**:
  - `factory_web._rag_vendor_notes()` — retrieves VERIFIED `vendor_quirk` /
    `comms` records (non-safety) in BM25 or semantic mode.
  - `factory_web._inject_rag_context_block()` — prepends `// RAG_CONTEXT`
    comment block to generated SCL file after `ob1_generator.write_ob1()`.
  - `generate_ob1()` — returns `rag_notes` (informational) + `rag_warnings`
    (critical safety) as separate keys.

- **Path-traversal protection** in `ingest_device`: `library_path` from AI
  output is validated against repo root before write.

### Tests

- `test_rag_index_missing_error.py` (2) — fresh-clone guard.
- `test_rag_ingest_retrieve.py` (8) — parse round-trip + mock retrieve.
- `test_rag_critical_safety_banner.py` (3) — safety banner trigger.
- `test_rag_not_verified_flag.py` (4) — `NOT_VERIFIED` annotation.
- `test_rag_ingest_device.py` (6) — PDF→device→KB pipeline + path-traversal.
- `test_rag_safety_chain.py` (10) — safety chain + app.js banner elements.
- `test_rag_bm25.py` (8) — BM25 score, filters, rag_warning, top_k.
- `test_rag_ob1_context.py` (8) — vendor notes, SCL injection, BM25 no-key.
- `test_ux_fixes.py` — `pv-datasheet-btn` removed from disabled list.

Full suite: **1358 passing**.

## [3.7.1] - 2026-06-14

> Tag: `v3.7.1` at commit `6a6c2ba`.

### Fixed — pre-final-test comprehensive audit (independent müfettiş)

- **Reveal-folder broken after generating a protocol/SISTEMA/CE doc (B-01):**
  the backend handed the UI an absolute path, which `reveal_path` refuses
  (I-A3), so "open folder" silently did nothing. Backend now returns a
  project-relative path (`factory_web._relpath`).
- **Project-path leak into the GUI log (B-02):** the RD05-not-ready and
  SISTEMA-input errors embedded the full project path, which reached the
  terminal log. Messages are now path-free (only the reason).
- **CE PDF showed literal `<br>` (B-07):** the PDF inliner escaped `<br>` to
  `&lt;br&gt;`; it now renders a real line break in the customer document.
- **SISTEMA prep list was always German (B-03):** the modal now has a DE/EN/TR
  language selector instead of a hardcoded `de`.

## [3.7.0] - 2026-06-13

> Merged from `feature/sat-v2-2026-06-12`. Code verified (1305 tests + e2e CLI
> smoke); the engineer-review items (SAT safety scenario DE/TR wording, SISTEMA
> warning→blocker decision, CE template text, IEC 62443/62682 content) are
> recorded in the internal safety-change / audit log (not shipped in this public tree) and
> still to be confirmed on the customer-facing documents. Live GUI verification
> pending.

### Added — SAT v2 protocol engine (IEC 62381 aligned)

- **Real SAT ≠ FAT.** `--type FAT|SAT|BOTH` now changes content: SAT carries
  site loop-check (real RD01 signals), motor rotation, sensor/switch alignment,
  real E-stop chain + guard-door circuit, drive-parameter verification,
  network/HMI integration, backup + signed handover record.
- **i18n DE/EN/TR** (`05_SCRIPTS/protocol_i18n.py`, default DE) — missing key →
  EN fallback + loud warning (never a silent empty string).
- **"Ref." column** on every test row (IEC 62381 / IEC 62061 / ISO 13849-2 /
  EN 60204-1 / IEC 62443 / IEC 62682); safety section re-attributed to
  ISO 13849-**2** (validation).
- **IEC 62443 / NIS2 cybersecurity** SAT section (access levels, default
  passwords, know-how protection, ports/services, backup+restore, network
  segmentation) with checkbox + signature.
- **IEC 62682 alarm rationalization** columns (priority / operator response /
  alarm class from RD08; missing → "—" + fill-in instruction, never guessed).
- **PDF output** via shared `05_SCRIPTS/pdf_common.py` (customer_report rewired
  onto it, behaviour unchanged); PDF failure → MD + loud warning.

### Added — compliance helpers

- **SISTEMA support** (`05_SCRIPTS/sistema_support.py`): prep list from RD05,
  engineer-declaration records (CRUD), and a non-blocking PENDING box on
  FAT/SAT when a PLr has no record. Software reminds/documents; engineer
  calculates/signs. No fake report names.
- **CE essential-modification (wesentliche Veränderung) assessment**
  (`05_SCRIPTS/ce_assessment.py`) for retrofit projects — DE/EN/TR, MD+PDF,
  trilingual mandatory disclaimer, never pre-answers/pre-ticks.

### Added — GUI + CI prep

- Protocol options modal (type/language/PDF), SISTEMA records form, CE modal,
  command-palette entries (`webgui/app.js`).
- **Passive** nightly TIA compile package: `.github/workflows/nightly-tia.yml`
  (dispatch-only), `05_SCRIPTS/nightly_tia_check.py` (log-hygiene-safe driver),
  `docs/NIGHTLY_TIA_CI_SETUP.md`. Dormant until a self-hosted `tia` runner is
  registered.

### Fixed — night-audit pass (müfettiş→doğrulayıcı)

- CE disclaimer now trilingual regardless of `--lang`; corrupt PROJECT_STATE
  is no longer overwritten by a SISTEMA write; nightly check fails a block that
  imports but fails to compile; FAT IO section is kept (header+warning) when
  signals are empty; project paths no longer leak into the GUI log / CLI.

### Tests

- +~600 lines of new tests (`test_sat_v2_protocols.py`, `test_sistema_support.py`,
  `test_ce_assessment.py`, `test_nightly_tia_check.py`,
  `test_night_audit_2026_06_13.py`). Full suite: **1298 passing**.

## [3.6.0] - 2026-06-11

### Added — Version Compare (what changed between legacy archive versions)

- **Deterministic diff engine** (`05_SCRIPTS/version_compare.py`, stdlib
  only): S5 symbol-table (`.SEQ`) record parsing (cp437, corrupt-record
  counter), unified text diff (4000-line cap, visible truncation), folder
  scan (sha256, depth ≤3 / ≤500 files with truncation flags) and
  multi-folder comparison with per-file status
  (added/removed/modified/unchanged/mixed). Binary MC5 `.s5d` program
  files are never diffed by content — the row carries an honest note
  ("export an AWL listing to compare logic").
- **New full-page view "Version Compare"** in the PROJECT group of the
  activity bar: add ≥2 version folders (e.g. dated `_Versionen/`
  subfolders plus `_aktiv/`) → Compare → file status table → click a row
  for the symbol diff / unified diff / binary note. With more than two
  versions an A/B pair selector appears (default: first ↔ last). The
  deterministic part deliberately works WITHOUT an open project.
- **AI change hypotheses (`DRAFT_UNVERIFIED`)**: optional panel that
  proposes WHY the changes were made, from the diff summary only (binary
  content never reaches the prompt). Requires an OPEN project — the call
  runs the full safety chain (C4 classification gate with consent
  checkbox for CONFIDENTIAL, §11 PII soft warning, S-20 anonymization,
  EU AI Act audit log written BEFORE the provider is contacted).
  Safety-relevant hypotheses are flagged "engineer review required";
  a malformed AI reply is shown raw (no silent loss). New prompt:
  `04_AI_PROMPTS/analyze/PROMPT_COMPARE_VERSIONS.md`.
- Tests: 41 new (`test_version_compare.py`, `test_version_compare_api.py`,
  `test_version_compare_ai.py`) — parser/diff/scan edge cases, API
  traversal refusal, C4/consent/audit/S-20 refusal paths, raw fallback.

## [3.5.0] - 2026-06-11

### UX overhaul — clear language, one source of truth, guided first use

Driven by first-user feedback ("Mode A/B means nothing", "pages show
different steps", "where do I start?") and a 3-agent UI audit.

- **"Mode A/B" language removed everywhere.** The activity bar is grouped
  into **PROJECT** (Explorer, Dashboard, Gates, Flowchart, Report, Git) and
  **LIBRARY** (Prompts, Library, Hardware) with labels and tooltips; the
  Library/Prompt pages carry a plain "LIBRARY WORKSPACE" badge instead of
  "MODE A", the Gate page is a plain title.
- **Single source of truth for gate/RD status.** Navbar, right rail,
  status bar, dashboard and gate view all render from one
  `refreshProjectState()` fetch (`get_state` + `get_gate_model`) — pages
  can no longer disagree about the current step. Shared
  `ACTION_LABELS`/`RD_STATUS_*` maps replace per-page copies; the
  stale-RD warning shows on the dashboard too.
- **Guided first use.** Onboarding leads with one primary **New Project**
  button (template select moved into the form); the form gains Customer,
  Output language and **Data Classification** (with a plain-language
  explanation of what it gates) — persisted validated; after creation a
  toast names the next step. A right-rail **Next step** card always shows
  ONE suggested action (e.g. "Start Retrofit Pre-Analysis" on retrofit
  Gate 1 — the button lives inside the Gate 1 page).
- **Honest buttons only.** `copy_prompt` is a real backend endpoint;
  fake-success `{ok:true}` fallbacks removed; the report's send-to-client
  button is now "Open output folder" (what it actually did);
  Freeze/Version, Generate Ref FB and Datasheet are disabled with
  "manual step" tooltips instead of toast-only stubs. Backend call
  failures surface in the log + a toast; errors logged while the Terminal
  tab is hidden light an unread dot.
- **Native file pickers** for TIA project paths (Settings + Send-to-TIA)
  and the new-project location — no more hand-typing paths.
- **Startup crash fixed:** `whoami /groups` (cp850) + `PYTHONUTF8=1`
  produced a UnicodeDecodeError traceback at every start on German
  Windows; all output-capturing subprocess calls now decode with
  `errors="replace"`.
- 28 regression guards in `tests/test_ux_fixes.py` — 961 pass.

## [3.4.3] - 2026-06-10

### Send to TIA: live step view + compile-error assistance (engineer-approved AI fixes)

The Send-to-TIA modal now narrates the transfer instead of dumping a raw
log, and failed compiles get graded help — from plain hints up to an AI fix
proposal that is **never applied without engineer approval**.

- **Live step view:** the transfer job reports structured steps (Tag XML →
  Portal → Open project → Find PLC → Import tags → Import SCL `n/m` →
  Compile → Save → optional PLCSIM download) rendered as a live checklist;
  the raw log stays available in a collapsible section. Toggle: Settings →
  TIA Portal → "Send to TIA view". A step left `running` by a crash is
  flipped to `fail` — no eternal spinner.
- **Compile-error assistance modes** (Settings → TIA Portal, default
  `hints`): `off` = raw errors only · `hints` = errors grouped by origin
  (AI sequence FB / IO tags / assembler output / library blocks) with a tip
  per group, no AI · `suggest` = adds a **Propose fix (AI)** button on
  sequence-FB errors · `auto_propose` = the proposal is pre-generated after
  a failed compile (only when the data-classification gate allows it
  without extra consent).
- **Hard safety rails:** the AI may only propose fixes for
  `_output/scl/FB_Seq_*.scl` — the single AI-generated artifact. Library
  blocks (SHA-256 verified) and assembler output are never patched inside a
  project (guarded in code + tests). Proposals must pass `scl_validator`
  before they are shown; applying requires engineer name + checkbox, backs
  the old file up to `_output/scl/_history/`, is audit-logged
  (`tia_fix:propose` / `tia_fix:apply`), and re-running Import + Compile
  stays a manual click. There is deliberately **no auto-apply mode**.
- **Bridge layer:** `BridgeBase.step()` callback + structured
  `BridgeResult.compile_errors`; `import_scl_files` gained an `on_file`
  progress callback. New pure module `05_SCRIPTS/tia_fix_assist.py`
  (classification + fix prompt + diff). 30 new tests — 933 pass.

## [3.4.2] - 2026-06-10

### ULAK §11 closed — PII soft warning on every AI call site, visible in the GUI

The v3.2.0 ULAK phase added the §11 soft PII/customer-name warning to the 4
AI call sites that existed then; every call site added since (v3.3.0/v3.4.x)
shipped without it, and the GUI never read the `_pii_warnings` key the
original sites return — so the warning was effectively invisible everywhere.

- **4 uncovered call sites now warn:** `generate_sequence_fb`,
  `rd03_chat_propose`, `run_retrofit_preanalysis`, `_ocr_legacy_pdf` emit
  `_pii_soft_warn()` results through the `_warn(category="privacy")` channel
  (delivered in the same response via `_attach_warnings`)
- **GUI now surfaces §11 warnings:** `Backend._consumeWarnings` reads
  `_pii_warnings` (string array) in addition to `_warnings` — shown in the
  diagnostics log as `[privacy]` plus a toast
- **Regression guard:** `tests/test_pii_warn_callsites.py` — meta test scans
  `factory_web.Api` for methods constructing `AIClient`/`AutoFlowRunner` and
  fails if any lacks `_pii_soft_warn` (same pattern as the C-A4 guard test);
  plus behavior tests (customer name, classification markers, non-public
  provider silence) and a GUI-consumption check. 903 tests pass.

## [3.4.1] - 2026-06-10

### IO Tag Table → TIA Openness (Send to TIA now ships the IO list)

`tia_tag_export.py` existed since Phase 29-B but was never connected to the
Openness bridge — "Send to TIA" imported only the SCL/DB block sources and
the PLC tag tables stayed empty.

- **XML format fixed to Openness V14+ import shape:** `SW.Tags.PlcTagTable`
  element (the old `SW.PlcTagTable` is the V13 format — TIA V19 rejects it),
  document-unique hex IDs, tag comments as `MultilingualText` objects with
  the Culture derived from `PROJECT_STATE.output_language` (DE→de-DE,
  EN→en-US; default en-US)
- **`OpennessCore.import_tag_table()`:** `TagTables.Import(xml,
  ImportOptions.Override)` — re-runs replace the table instead of failing
- **Bridge wiring (V19/V20/V21):** the tag table is imported **before** the
  SCL sources so symbolic IO references resolve at compile time; a tag
  failure is a loud warning in the job log, never an abort (no silent tag
  loss, no blocked direct-addressing projects)
- **send_to_tia:** generates a fresh tag XML from RD01/HW03 on every
  transfer (`_output/tia_import/TIA_TagTable_<proj>.xml`, stable name —
  overwrites instead of accumulating); skip reasons (no RD01/HW03 data,
  export error) are always written to the transfer log; opt out with
  `opts.import_tags=false`
- 13 new tests (XML shape, import ordering, fail-soft, skip transparency)

**Live-verified against real TIA V19** (demo project, 18 sources + 14 tags,
0 compile errors, project saved). The live run surfaced and fixed 4 more
real-API issues:

- **Program names, not IEC names (B2):** the assembled OB1 references raw
  RD01 signal names; the IEC-prefixed export left 11 "Tag not defined"
  compile errors → send_to_tia now exports with `name_source="rd01"`
- **Comment culture (B1, quirk S-8):** `TagTables.Import` rejects the whole
  XML when the comment Culture is not a project language → the bridge reads
  `LanguageSettings.EditingLanguage`, rewrites the XML cultures, and as a
  last resort retries without comments (loud note, never silent)
- **Portal attach (B3):** a new process starting a second TIA instance
  could not open the project left open by the previous run ("already been
  opened by user") → `start_portal` now attaches to a running portal first,
  preferring the instance that holds open projects
- **Statement-free IF body (B4, quirk S-7):** TIA's source compiler refuses
  a comment-only IF body ("Compound part of instruction expected") and
  reports it ~40 lines away — FB_Watchdog's placeholder comms-check IF →
  bare `;` no-op shipped in the library + demo, new `scl_validator`
  EMPTY_BODY rule (error on statement-free THEN, warning on ELSE/loops),
  codegen STRICT RULE 11
- Compile report now lists errors before warnings (the single real error
  was buried under 10 benign warnings)
- New dev helpers under `05_SCRIPTS/dev/`: live send driver, compile-error
  tree dump, block export, probe/cleanup scripts

## [3.4.0] - 2026-06-10

### Flowchart View: Derived Diagram + Change-Request Chat + Gate Staleness

**RD03 Flowchart view (new activity-bar page):**
- The Flow Steps **table is the single source of truth**; the mermaid diagram
  is always **derived deterministically** from it (`workbench/core/rd03_flowchart.py`)
  — never hand-maintained, never AI-drawn
- Mermaid rendered offline in the GUI (`webgui/vendor/mermaid.min.js`, no CDN)
- "Regen diagram" rewrites the mermaid block inside RD03 from the table (no AI)

**Change-request chat (the "no chat interface" gap):**
- Engineer describes the change in plain language; the AI returns a complete
  replacement Flow Steps table (`rd03_chat_propose`) — conversation iterates
  until the proposal is right
- Diagram preview + impact findings of every proposal are computed
  **deterministically from the proposed table**, never by the AI
- `rd03_chat_apply`: swaps the table, regenerates the diagram, demotes
  frontmatter `status:` to DRAFT (re-review mandatory), backs the previous
  version up to `metadata/_history/`; proposals with structural errors
  (missing step targets, unreachable steps…) are refused
- AI prompt hard rule: safety logic (E-Stop, light curtains, F-blocks) is
  never generated — flagged as "SAFETY — engineer review required" instead

**Deterministic impact check (no AI):**
- Graph integrity: duplicate/missing/unreachable steps, dead ends, missing
  Initial, sequences that never terminate
- Cross-references: signals vs RD01/RD02 ("input sensor missing"), timers vs
  RD07, modes vs RD04 — each finding names the file to fix

**Gate staleness warning:**
- `advance_gate` snapshots SHA-256 of every `metadata/RD*.md`; editing an RD
  **after** approval shows a "Changed after approval — re-validate" banner in
  the gate view (advisory — the gate never silently regresses)

**Status enum coordinated rename (was "tracked separately" since v1.1.0 specs):**
- `Aktif/Pasif/Taslak/Yedek` → `Active/Inactive/Draft/Spare` across 13 JSON
  schemas, 14 MDSCHEMA specs, all templates (.md + .xlsx), examples and code
  defaults; tooling still reads legacy Turkish literals from old projects

**Docs:**
- Supported-AI-providers table in all three READMEs (incl. **Gemini free
  tier** note + key URLs); INSTALLATION.md gains Gemini/DeepSeek setup sections

## [3.3.0] - 2026-06-02

### Multi-AI Team: Per-Provider Settings + Retrofit Pre-Analysis Pipeline

**Settings UI — Per-Provider Cards:**
- Settings modal redesigned: one card per AI provider (Anthropic, Google, OpenAI, DeepSeek)
- Each card: API key, model selector, per-provider max tokens limit (256–65536, clamped)
- Recommendation badges: "SCL generation · Code analysis · Safety" (Claude), "PDF/P&ID analysis · Translation · Large context" (Gemini)
- Task Routing section: assign each task type (preanalysis, scl_generation, translation, default) to a provider
- `get_provider_for_task(task)` API: resolves provider+model+max_tokens, falls back to default when key missing

**Retrofit Pre-Analysis Pipeline (Faz A + B):**
- `_raw/` folder concept: engineers drop legacy drawings, photos, EPLAN PDFs, old SCL code here
- `anonymizer.py` (new): PROJECT_STATE.json-aware text anonymizer; replaces customer name, project ID, engineer name + regex patterns (email, phone, address) before sending to cloud AI
- `ai_client.py`: `chat_with_files()` method — Gemini Vision API; uploads files, calls API, **deletes uploaded files immediately** (privacy)
- `ai_runner.py`: `WorkflowStep` gains `provider`, `model`, `use_multimodal` fields; per-step provider override with per-step classification guard check
- New `"Retrofit Pre-Analysis"` workflow: Step 1 Gemini Vision (drawings/photos), Step 2 Claude (legacy code), Step 3 Claude (RD01 draft consolidation)
- `AutoFlowRunner`: client cache by (provider, model); per-step provider resolution

**Guard: CONFIDENTIAL soft-block (SAFETY_CHANGES.md):**
- `AIGateResult` dataclass replaces plain tuple — backward-compat `__iter__` yields `(allowed, reason)`
- `CONFIDENTIAL + public provider` → `requires_consent=True` (was hard-block)
- `check_ai_send(consent_confirmed=True)` allows CONFIDENTIAL with engineer sign-off
- `RESTRICTED` → unchanged hard-block, consent has no effect
- See SAFETY_CHANGES.md for compliance notes

## [3.2.0] - 2026-05-30

### Fixed-FB Library + Acceptance Gate + CI + Direct API (ULAK)

Major feature release closing the machine-checkable verification loop and the direct-API integration.

**Acceptance Gate (the missing link):**
- `06_KNOWLEDGE_BASE/contracts/schema/fb_contract.schema.json` augmented with canonical `meta` (source/license/safety_class), `behaviors` (given/when/then PLCSIM specs), `acceptance` sections
- All 16 seed device contracts carry `_schema_version: "1.0.0"` + `meta` + `behaviors` + `acceptance`
- `05_SCRIPTS/fb_acceptance_check.py` — gate runner: G-01 structural, G-02 interface, G-03 behaviors, G-04 error codes, G-05 forbidden patterns, G-06 PLCreX (optional)
- `05_SCRIPTS/accept_gate.py` — charter §4 CLI wrapper; honest `PENDING_TIA_VERIFY` labels (no fabricated TIA-verified claim)
- **18/18 SCL blocks gate PASS** — `AUTO_VERIFIED_structural | PENDING_TIA_VERIFY`

**FB_Motor_Standard.scl — surgical repair (6 bugs closed):**
- Block name: `FB_Motor_Conveyor` → `FB_Motor_Standard`
- Customer header removed; clean factory attribution
- `CURRENT_TIME()` removed (forbidden Siemens non-standard call)
- Fake speed ramp (`MIN_REAL/MAX_REAL +5%/cycle`) removed → `NO_FAKE_FEEDBACK` rule enforced
- `out_tRuntime += T#100ms` hardcoded scan period → cycle-counter accumulator
- Added `in_bFeedbackRun`, `in_bFeedbackOverload` (mandatory per MOTOR_DOL contract)
- UDT_Motor, inout_udMotorData, in_iMode, multi-instance OB1 example preserved

**PascalCase naming normalization:**
- 7 ALL_CAPS SCL files renamed (git mv — history preserved): `FB_MOTOR_SOFT_STARTER` → `FB_Motor_SoftStarter`, `FB_ALARM_HANDLER` → `FB_AlarmHandler`, etc.
- 3 levels updated per file: filename + FUNCTION_BLOCK declaration + contract `block.name`/`alternatives`

**ULAK — Direct API integration (charter §11):**
- `keyring` installed; Google API key migrated to Windows Credential Vault
- `_pii_soft_warn()` — non-blocking PII/customer-name warning at all 4 AI call sites
- `README.md` — AI Responsibility Disclaimer section added (output status, safety, liability, data privacy, API key storage)
- `INSTALLATION.md` — Cursor/Claude Code requirement removed; direct API key setup documented

**CI — GitHub Actions:**
- `.github/workflows/ci.yml` — "CI — Gate Check": runs `accept_gate.py` for all 18 blocks on every push/PR
- `.github/workflows/tests.yml` (pre-existing) — "Regression Tests": Windows+Linux matrix, Python 3.11/3.12
- Cross-platform path traversal guard fix: `relpath.replace("\\", "/")` before `Path()` parsing

**Bugfixes:**
- `datetime.utcnow()` DeprecationWarning → `datetime.now(timezone.utc)` in `fb_acceptance_check.py`
- `test_reveal_path_guard.py` — traversal test now checks both `/` and `\` separator styles
- `tests/fixtures/FB_Motor_Broken_TEST_ONLY.scl` — dedicated broken fixture (gate rejection regression test)

**Stats:** 458 tests pass, 0 failures · 18/18 blocks gate PASS · CI ✅ green

---

## [Unreleased]

### Field-ready retrofit pipeline (2026-06-10) — M0–M5

End-to-end "old S5/S7 code in → TIA-ready program out", library-first.

- **M0 hotfixes:** per-step API key resolution in `AutoFlowRunner` (the
  mixed-provider Retrofit workflow sent the Gemini key to Anthropic and died
  mid-run); `{out_N}` step-output map (the RD01 consolidation step never saw
  the drawing analysis); no silent cross-provider client fallback;
  `on_flow_done` no longer fires after an error.
- **M1 input layer:** `_raw/legacy_code/` accepts `.txt` and `.pdf`
  ("S5/S7 for Windows" exports). `legacy_pdf_extract.py`: pdfplumber text
  layer + AWL-density quality score + consent-gated Gemini Vision OCR for
  scans; engineer must review/confirm extractions (O↔0, I↔1 warnings) before
  pre-analysis will run.
- **M2 chain closure:** pre-analysis grew to 6 steps and writes RD01/RD02/
  RD03/RD13 drafts directly into `metadata/` as `DRAFT_UNVERIFIED`
  (`rd_draft_writer.py`: approved RDs never overwritten — `.ai_draft.md`
  sidecar; `_history/` backups; audit-logged). Background job + status
  polling replaces the 300 s blocking wait. RD05 is never AI-drafted.
- **M3 library-first assembly:** `program_assembler.py` maps RD01 devices to
  curated library contracts, copies blocks VERBATIM (SHA-256 proof),
  generates instance DBs + an OB1 that actually compiles (instance-DB calls
  with field-signal bindings — the old OB-static VAR block was invalid),
  validates everything (incl. STRUCTURAL_BUG rule) + re-runs contract gates,
  and writes `ASSEMBLY_REPORT.md` with explicit #UNKNOWN/TODO lists.
  `PROMPT_CODE_GEN_SEQUENCE.md` authored — the sequence FB is the only
  AI-generated code artifact.
- **M4 TIA direct path:** the orphaned Openness bridges are wired into the
  GUI — Settings TIA card (detect V19/V20, toggles, DLL override), "Send to
  TIA" with compile preflight and error surfacing, optional PLCSIM download
  behind a separate confirm (real-PLC downloads stay hard-blocked). Clean
  compile ⇒ `AUTO_VERIFIED_compile | PENDING_PLCSIM_VERIFY` +
  `last_validation scope=compile` (W-A5 checkbox no longer needed).
  Classification policy: local TIA transfer allowed for CONFIDENTIAL with
  audited engineer consent; RESTRICTED stays blocked (SAFETY_CHANGES.md).
  `pythonnet` added as a Windows-only optional dependency.
- **M5:** `docs/USER_GUIDE_RETROFIT.md` (exact click path), README/VISION
  honesty updates, CI smoke extended with a deterministic assembler run.
- **Tests:** 730 → 808 passing.

### Production-readiness pass (2026-06-09)

Follow-up to the 2026-06-09 engineering audit (internal, not shipped). Most audit
findings were already closed by the earlier safety/merge cycle; this pass
closes the remaining gaps:

- **Privacy (FIX-4):** Retrofit Pre-Analysis consent modal now explicitly warns
  that photos/drawings/PDFs are sent to Gemini Vision **without** anonymization
  (only legacy code text is anonymized) and instructs redacting logos/nameplates
  first. Backend emits a privacy-category warning before the workflow starts and
  flushes it to the UI (`_attach_warnings`).
- **Validator:** new `STRUCTURAL_BUG` rule in `scl_validator.py` — detects a
  stop-guard IF-block (outputs FALSE + step change, no ELSE) overwritten by
  unconditional TRUE assignments in the same scan (the StarDelta step-10 bug
  class). Severity *error* → blocks the acceptance gate. Proven against the
  pre-fix pattern; zero false positives across the curated library.
- **CI:** `sim/field_pretest.py --runs 1` (mock AI client) added to the test
  workflow — behavioral smoke of the real AutoFlowRunner chain, not just
  structural checks. Fixed a cp1252 `UnicodeEncodeError` crash in the script.
- **Tests:** 730 → 742 (12 new: privacy warning pins + guard-overwrite rule).

### Turkish → English translation actually completed (2026-05-23)

A full audit (`docs/TRANSLATION_AUDIT_2026-05-23.md`) found that earlier "translation
complete" commits had under-delivered — roughly 150 system files still had Turkish
bodies. This work finishes the migration:

- **Phase 1** — fixed 8 files with stale "the system is Turkish" meta-statements.
- **Tier 1** — `04_AI_PROMPTS/analyze/` parsers + extractors (19) + `01_GLOBAL_STANDARDS/md_schemas/` RD specs (13).
- **Tier 2** — `02_PROJECT_TYPES/RETROFIT` (16) + `GREENFIELD` (14) + `03_DOMAIN_TOOLS` (13).
- **Tier 3** — `04_AI_PROMPTS/{review,test_gen,code_gen,doc_gen}` (42) + `09_HARDWARE_LIBRARY` (7) + top-level guides (2).
- **Tier 4** — folder `_README.md` (6) + `07_PROJECT_TEMPLATE` templates (15) + `05_SCRIPTS/*.py` (46).
- **Post-phase** — GLOBAL `*.scl` templates, JSON schema titles, `requirements.txt`, KB block.

**Intentional keeps (multi-language design / legitimate):** `GLOSSARY_TR.md`, the `_TR`/`_DE`
field names and example cells in RD schemas/templates/HMI prompts, the German `Kunde_Mueller`
demo, `MOTÖR_BAŞLAT` bad-example, `output_language: tr` examples, the Turkish→ASCII map and
input-column-matching keywords in scripts, and developer logs (`docs/_BUILD_LOG.md`,
`docs/WORKBENCH_REDESIGN_PLAN.md`).

## [3.1.0-alpha] - 2026-05-22

### Workbench IDE Edition — Embedded Visual Workbench + TIA Send + Library Seed

This release adds a **major new layer** on top of the v3.0.0-alpha foundation: a fully embedded **Workbench IDE** inside `factory_gui` (no separate process), with file-aware actions, platform-aware prompt filtering, native editable IO grid, persistent toolbar + Library panel, and a Send-to-TIA dialog (Openness direct + folder export). 14 commits, 31 files changed, +4,618 / -831 lines.

**Architectural decisions:**
- Workbench IDE is now embedded in the main factory GUI (not standalone) — single-window UX
- All raw `tk` panels migrated to `customtkinter` for visual cohesion with the main GUI
- Standalone launchers (`BASLAT_GUI.bat`, `factory_gui.bat`, `workbench.bat`) consolidated into a single `start.bat`
- Prompts and actions are now **context-aware** — UI surface shrinks to what's relevant to the active file
- Library blocks bootstrap (`06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_Standard.scl`) — first reusable seed for code-gen
- TIA Send modes: **Direct via Openness** (live transfer) + **Folder export** (manual import fallback)
- Parallel `claude/improve-project-workflow-WoZlV` branch (proposed `src/` + `factory/` restructure) **abandoned** — superseded by this branch's incremental approach (workspace remained on numbered `01_-09_` folder layout)

**Phase A — Visual cohesion + fullscreen toggle + narrow terminal**
- Workbench panels migrated to `customtkinter` (dark/blue theme, theme tokens shared with main GUI)
- Sidebar + dashboard auto-hide on workbench open; `☰ Menu` button restores them
- Terminal panel narrowed (~270 px) + left-aligned

**Phase B — Platform-aware prompt filtering**
- When `target_platform` is set in project state, only matching analyze prompts are shown
- File-type filter hides irrelevant prompts (e.g., AB_L5X parser hidden when motor SCL is open)

**Phase C — File-aware dynamic action buttons**
- Action panel buttons change with selected file: `.scl` → TIA Send, RD01 `.md` → IO Validate, `_input/*.xml` → Parse As Input
- Removed redundant "Auto-Flow" mode (already provided by main GUI as "Auto Pipeline")

**Phase D — User prompts: save + optional AI normalize**
- New prompts saved into `04_AI_PROMPTS/<category>/` matching the active file's context
- Optional AI normalization to factory prompt standards via `prompt_normalizer.py`

**Phase E — Entry point cleanup + unified API settings**
- Standalone `workbench/` entry point removed
- API key + model settings unified into a single Settings dialog

**Phase F — Visual polish**
- Sash widths, scrollbar styles, panel widths, smooth show/hide animation, prompt-save confirmation toast

**Phase G — Tabbed editor + Inspector strip + Status bar**
- Multiple files open as tabs (close, dirty indicator)
- Right-side Inspector strip (Gate, Platform, file context)
- Bottom status bar (Customer, Gate, AI model, cost)

**Phase H — Native editable IO grid (Excel-independent)**
- New `io_grid_panel.py` (530 lines): direct in-app editing of RD01 IO Listesi without requiring Excel
- Backed by `io_list_io.py` (read/write parser, 291 lines) + `io_validator.py` (175 lines)

**Phase I — Persistent toolbar + Library panel + KB blocks bootstrap**
- `toolbar.py` (147 lines): always-visible toolbar (New, Save, Validate, TIA Send, Library)
- `library_panel.py` (203 lines): browse + drop reusable blocks (`FB_Motor_Standard`)
- `06_KNOWLEDGE_BASE/blocks/` directory created with first seed block + metadata JSON

**Phase J — Send-to-TIA dialog**
- `send_to_tia_dialog.py` (330 lines): two modes — **Direct via Openness** (auto version detect, project pick) + **Folder export** (manual import for offline machines)

**Post-Phase enhancements**
- `factory_reader.py` expanded (~170 LOC added): richer file type detection + project context inference
- `action_panel.py` action handlers extended (~70 LOC added)
- `file_tree.py` refinements (filter, expand-by-context)
- Library panel: `FB_Motor_Standard.scl` (192 lines, multi-instance) + `.meta.json` (block schema)
- Fix: PanedWindow crash on Windows — removed unsupported `highlightthickness=` parameter (commit `3ec0b54`)

**Files added (this release):**
- `start.bat` (consolidated launcher)
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_Standard.scl` + `.meta.json`
- `workbench/core/`: `claude_bridge.py`, `file_actions.py`, `io_list_io.py`, `io_validator.py`, `library_store.py`, `prompt_normalizer.py`, `prompt_writer.py`
- `workbench/panels/`: `inspector_strip.py`, `io_grid_panel.py`, `library_panel.py`, `send_to_tia_dialog.py`, `status_bar.py`, `toolbar.py`

**Files removed:**
- `BASLAT_GUI.bat`, `factory_gui.bat`, `workbench.bat` (replaced by `start.bat`)
- `workbench_main.py`, `workbench/app.py` (standalone entry; embedded only now)

### Decision Log Additions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-21 | Workbench IDE embedded into `factory_gui`, no standalone process | Single-window UX; eliminates "two GUIs inside one window" feeling; shared theme/state |
| 2026-05-21 | All panels migrated to `customtkinter` (raw `tk` → CTk) | Visual cohesion with main GUI; thick scrollbar + theme tokens |
| 2026-05-21 | Auto-Flow mode removed from Workbench | Already provided by main GUI as "Auto Pipeline" — removed duplication |
| 2026-05-21 | Prompts and actions are context-aware (file type + platform) | Reduces UI surface to what's relevant; teaches the user by hiding noise |
| 2026-05-22 | All `.bat` launchers consolidated into `start.bat` | Single entry point; reduces confusion + maintenance |
| 2026-05-22 | Library blocks bootstrapped in `06_KNOWLEDGE_BASE/blocks/<domain>/` | KB starts producing reusable code seeds, not just documentation |
| 2026-05-22 | TIA Send offers both Openness (direct) and folder export | Openness requires TIA + license; folder export works offline / on customer site |
| 2026-05-22 | Parallel `src/` + `factory/` restructure branch ABANDONED | Existing numbered folder layout (`01_`–`09_`) preserved; restructure didn't justify migration churn |

---

## [3.0.0-alpha] - 2026-05-15

### v3.0.0 Major Expansion — 14-Point Raw Data Pack + Platform-Aware Analysis + Multi-Language Output

This release adds a completely new content layer on top of v2.4.0. The existing structure is **left intact**; only new files are added.

**Architectural decisions:**
- 12-Point Raw Data Pack → 14-Point (RD13 Legacy Annotation + RD14 Modernization Report added)
- Platform-aware analysis: separate parser prompt for each PLC format (S7-1500, S7-300, S5, AB, CoDeSys)
- Multi-language code output: per-project `output_language` config (TR/EN/DE) — system files remain in Turkish (to be translated to English in v4.0.0)
- 8-FACTORY architecture proposal REJECTED + archived (migration cost too high, cosmetic benefit only)
- No branching strategy → commit directly to main; push manually (user decision)

**v3.0.0-alpha COMPLETED (6 sessions, ~98 files):**

### Session 1 — Pattern + Language Policy
- `_BUILD_LOG.md` — cross-session resume system (6 sessions × file tracking)
- `PIPELINE_CODE_REWRITE.md` — 7-Gate end-to-end pipeline
- `MDSCHEMA_RAWDATA_01_IO.md` — RD01 spec pattern
- `PROMPT_ANALYZE_S7_1500_OPENNESS.md` — platform parser pattern
- `PROMPT_EXTRACT_IO_FROM_CODE.md` — topic extractor pattern
- `GLOBAL_LANG_POLICY.md` — 3-layer language policy
- `the internal archive` — 4 files archived

### Session 2 — RD02–RD14 Specs (13 files)
- MDSCHEMA_RAWDATA_02 (DataDict), 03 (Flowchart + Mermaid), 04 (Mode + PackML),
  05 (Safety, DRAFT_UNVERIFIED discipline), 06 (Motion + PLCopen v2.0),
  07 (Timing + IEC), 08 (Alarm + ISA-18.2 + multi-lang), 09 (Comms),
  10 (FB Spec — two pages), 11 (HMI + ISA-101 — two pages), 12 (UseCase),
  13 (Legacy Annotation + WarningFlag), 14 (Modernization + decision matrix)

### Session 3 — Platform Parser + Topic Extractor (18 files)
- 4 platform parsers: PROMPT_ANALYZE_{S5_AWL, S7_300_STL, AB_L5X, CODESYS}.md
- 13 topic extractors: PROMPT_EXTRACT_{DATADICT, FLOWCHART, MODE, SAFETY ⚠️,
  MOTION, TIMING, ALARM, COMMS, FBSPEC, HMI, USECASE, ANNOTATION, MODERNIZATION}_FROM_CODE.md
- `04_AI_PROMPTS/analyze/_README.md`

### Session 4 — Retrofit + Greenfield Guides (11 files)
- 6 retrofit extraction guides: RETROFIT_EXTRACT_{DATADICT, MODE, TIMING, ALARM, USECASE}.md
  + RETROFIT_MODERNIZATION_GUIDE.md (Retrofit/Greenfield/Hybrid decision matrix)
- 5 greenfield design guides: GREENFIELD_DESIGN_{DATADICT, MODE, TIMING, ALARM, USECASE}.md

### Session 5 — Template + Schema + Glossary (32 files)
- 14 MD per-project templates (`07_PROJECT_TEMPLATE/metadata_template/RD01..RD14.md`)
- 14 JSON validation schemas (`08_METADATA_INPUT/schema/rd01..rd14.schema.json`)
- 4 glossaries: GLOSSARY_BASE.md + GLOSSARY_EN/TR/DE.md (concept_id system)
- Decision: XLSX is the MD source-of-truth (converted via script_md_to_xlsx)

### Session 6 — Closing (16 files/updates)
- 8 folder _README.md files (01_GS, 02_PT, 03_DE, 04_AI, 05_SC, 06_KB, 07_PT, 08_MI)
- 3 STUB→FILLED: GLOBAL_METADATA_SCHEMA.md, METADATA_INPUT_GUIDE.md, PROJECT_MAESTRO_TEMPLATE.md
- 2 new scripts: script_md_to_xlsx.py, script_prompt_amend.py
- `_PROMPT_HIERARCHY.md` — AI prompt map (49 prompts)
- `USER_GUIDE_BIG_PICTURE.md` — comprehensive usage guide
- Final PROGRESS_TRACKER + CHANGELOG + _BUILD_LOG updates

**Total:** 7 commits (`60732da` init + `2621e4f` + `c7d87d4` + `113b80e` + `4bb8acb` + `538405c` + Session 6 final commit), ~98 new files, ~20K+ lines.

### Decision Log Additions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-15 | System files remain in Turkish (v3.0) | Developer fluency + fast iteration; EN translation deferred to v4.0.0 |
| 2026-05-15 | Multi-language CODE OUTPUT preserved | Customer code comments in TR/EN/DE per-project config |
| 2026-05-15 | 12-Point → 14-Point Raw Data Pack | Legacy annotation (RD13) + modernization report (RD14) added |
| 2026-05-15 | 8-FACTORY proposal REJECTED + archived | ~30 file migration, cross-reference breakage, zero code quality benefit |
| 2026-05-15 | No branching, commit directly to main | User backed up; no need for experimental branches |
| 2026-05-15 | Push manually, not automatically | User makes every push decision themselves |

---

## [2.4.0] - 2026-05-08

### Added (Operational Maturity)

**New files:**
- `FACTORY_TASK_PLAYBOOK.md` — Task → file matrix. The single source of truth for which files to load when opening a new Cursor/Claude Code conversation for a given task. Saves tokens, ensures consistent output, enables fast starts. (Result of IDEA-003)

**Updated files:**
- `PROJECT_VISION.md` v1.0 → v1.1: Section 3.3 added — "Meta-Project and Customer Project Separation". Clear separation between the factory's own logs/decisions vs. the customer project's logs/decisions, with a decision matrix for which events belong where. (Result of IDEA-016)
- `MDSCHEMA_PROMPT_CODE_GEN.md` v1.0 → v1.1: Section 4.5 added — "Error Management Loop". Three error categories (A: syntax, B: schema/standard, C: semantic), operational feedback flow, mandatory Section 8 sub-structure in prompts. (Result of IDEA-011)
- `FACTORY_MAESTRO.md` v1.1 → v1.2: Missing files added to the folder tree (FACTORY_TASK_PLAYBOOK, DOMAIN_INPUT_SOURCES). Section 7 (TODO list) reorganized according to the "single source of truth" principle — current status now lives in PROGRESS_TRACKER; MAESTRO is for historical record only. (Result of IDEA-010)
- `FACTORY_IDEAS_BACKLOG.md` v1.0 → v1.1: 21 new IDEA blocks added (IDEA-002 through IDEA-022). 5 REJECTED + 8 DEFERRED + 4 APPROVED + 1 REVIEWED + 1 NEW + 2 additional APPLIED.
- `PROGRESS_TRACKER.md` v1.2 → v1.3: Section 1 updated to v2.4 status, v2.4 rows added to Sprint 0, 4 new decisions added to the decision log, Section 4.5 (Active Ideas) populated with real backlog status.

### Decision Log Additions
- Task → file matrix lives in a single file (Cursor/Claude Code discipline)
- Error management loop is part of existing MDSCHEMA, not a separate schema
- Meta-project vs. customer project separation clarified in PROJECT_VISION
- MAESTRO Section 7 in "memory mode" — current status lives in the tracker

### Key Conceptual Gains

**1. The factory can now manage itself.**
v2.3 added idea governance → an idea intake/evaluation mechanism exists. v2.4 **stress-tested this mechanism with a real case** (21 IDEAs processed in one session). Uniform record format used for rejected, deferred, approved, and applied ideas.

**2. Operational discipline complete.**
- New conversation start: the PLAYBOOK matrix tells you which files are needed
- AI makes a mistake: the Section 4.5 loop provides structured feedback
- Two project levels: Vision 3.3 prevents log contamination

**3. Error logging paths clarified.**
- Transient error → Customer project log
- Recurring error → KB_FEEDBACK_LOG
- Structural issue → IDEAS_BACKLOG
- Systematic schema violation → MDSCHEMA update IDEA

### Pilot Validation

The conversation that produced v2.4 was a **real test of the idea-governance system**: the user brought 21 ideas from 3 different AI conversations (a CR proposal, a 10-point analysis, an HMI summary). The system placed each one in the correct category:
- 5 proposals conflicting with existing structure → REJECTED (with written rationale)
- 8 premature proposals → DEFERRED (with documented trigger conditions)
- 4+ proposals aligned with existing principles → APPLIED

This ensures that when the same ideas surface again in the future, we can say: "We discussed this; here is why we made decision X."

---

## [2.3.0] - 2026-05-08

### Added (Idea Governance)

**New files:**
- `FACTORY_IDEAS_BACKLOG.md` — The factory's own product backlog. Ideas from external AIs, user suggestions, and deferred decisions live here. Status flow: NEW → REVIEWED → APPROVED → IN_PROGRESS → APPLIED (or REJECTED / DEFERRED).
- `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_IDEA_INTEGRATION.md` — A 7-section schema for systematically analyzing how an approved idea integrates into the factory structure. The third of the existing MD schemas.

**Pilot application:**
- Another AI's Change Request mechanism proposal was logged as IDEA-2026-05-08-001. It was rejected as-is (missing frontmatter standard, creates a parallel CHANGELOG system), but its core value was preserved through an **alternative implementation**: single backlog + single schema, compatible with the existing CHANGELOG.

### Changed

- `PROGRESS_TRACKER.md` v1.1 → v1.2: Section 4.5 added (Active Ideas / Backlog summary). Two new decisions added to the decision log (Factory is a project, idea governance).
- `FACTORY_MAESTRO.md` folder tree updated (FACTORY_IDEAS_BACKLOG.md added to root, MDSCHEMA_IDEA_INTEGRATION added under md_schemas/).

### Decision Log Additions
- The factory is itself a project — it gets its own backlog (the factory is its own customer)
- Idea governance: single backlog + single schema, no parallel systems (no duplicate CHANGELOG created)

### Key Conceptual Gain
With v2.3, the factory can now **manage its own evolution**. The flow is:
1. New idea arrives → logged as NEW in the backlog
2. Evaluated → REVIEWED
3. If approved → systematic analysis via MDSCHEMA_IDEA_INTEGRATION
4. If conflicting, its own principles stop it
5. Otherwise applied → APPLIED + reflected in CHANGELOG

This represents the transition from factory as orchestrator (FACTORY_MAESTRO) to **factory as its own product manager**.

---

## [2.2.0] - 2026-05-08

### Added (Mobile + Input Discipline)

**New files:**
- `FACTORY_MOBILE_WORKFLOW.md` — Mobile workflow discipline, Claude Project setup guide, mobile-to-desktop division of work
- `03_DOMAIN_TOOLS/DOMAIN_INPUT_SOURCES.md` — Input matrix for retrofit and greenfield, the metadata meeting point for both project types

**Outside the zip:**
- `CLAUDE_PROJECT_SETUP_GUIDE.md` — Personalized setup instructions: which files to upload to Project knowledge, custom instructions text

### Changed

- `PROGRESS_TRACKER.md` v1.0 → v1.1: New conversation transition guide (Section 6) updated to include the Claude Project method. 2 files added in v2.2 registered in Sprint 0 list. 3 new decisions added to the decision log.

### Decision Log Additions
- Mobile workflow discipline lives in a separate file (not inside FACTORY_MAESTRO)
- Input sources matrix as a domain file (independent of project type)
- Working method: Conversation → Claude Project (mobile/desktop sync)

---

## [2.1.0] - 2026-05-06

### Added (MD Schema System)

**MD Templates (new folder):**
- `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_PROMPT_CODE_GEN.md` — Full template for code-generation prompts
- `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_DOMAIN_REFERENCE.md` — Template for domain files

**Bulk Edit Tool (zero tokens!):**
- `05_SCRIPTS/script_bulk_md_edit.py` — For mechanical MD edits:
  - Add/update/remove frontmatter fields
  - Find-and-replace
  - Insert lines after a section
  - Version bumping (semver)
  - All operations safe with --dry-run

**Schema Validator:**
- `05_SCRIPTS/script_md_schema_validator.py` — Validates MD files against their schema

### Changed

- `schema`, `device_type`, `target_ai`, `metadata_input`, `output_artifacts` added to motor prompt frontmatter (via bulk edit, as a demonstration)
- PROGRESS_TRACKER, SKELETON_BLUEPRINT updated

## [2.0.0] - 2026-05-06

### Added (First MVP)

**Manifesto & structure:**
- `FACTORY_MAESTRO.md` — system backbone
- 7 main folders (`01_GLOBAL_STANDARDS` ... `07_PROJECT_TEMPLATE`)
- `.cursorrules` and `.cursor/rules/*.mdc` (markdown + scl rules)

**Standards:**
- `GLOBAL_NAMING_STANDARD.md` — variable, FB/FC/DB, tag, file naming
- `GLOBAL_DATA_CLASSIFICATION.md` — data sharing rules for AI usage
- `GLOBAL_FB_TEMPLATE.scl` — 4-region FB skeleton

**Project type:**
- `RETROFIT_IO_EXTRACT.md` — IO extraction procedure from EPLAN

**AI Prompts:**
- `PROMPT_CODE_GEN_FB_MOTOR.md` — motor FB generation

**Scripts:**
- `script_project_init.py` — create new customer project
- `script_factory_audit.py` — detect outdated/missing files
- `script_consistency_check.py` — naming standard audit
- `script_propose_update.py` — field feedback to factory

### TODO (subsequent sprints)

- `RETROFIT_MAESTRO.md` main workflow content
- `RETROFIT_HARDWARE_ANALYSIS.md`, `RETROFIT_FLOWCHART.md`
- All `GREENFIELD_*` files
- All `DOMAIN_*` files (Safety, HMI, Comms, Drives, Testing FAT/SAT)
- Additional code-gen prompts for valves, axes, sequences
- `KB_PITFALLS_*.md` lessons learned files
