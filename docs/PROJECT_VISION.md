---
title: Automation Factory - Project Vision
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-08
status: ACTIVE
purpose: master_context_document
---

# PROJECT_VISION.md

> **This file was written to introduce the project to a new Claude/AI conversation.**
> When starting a conversation, paste this file + `SKELETON_BLUEPRINT.md` + `PROGRESS_TRACKER.md` — the AI will have full context.

---

## 1. Goal in One Sentence

To build a consistent and repeatable production pipeline for industrial automation projects (TIA Portal V18+ based) — one that uses AI to draft a large share of the **boilerplate** code, starting from customer data and working toward a TIA Portal project.

> **Reality check (2026-06-10):** The pipeline is now **library-first**: device
> FBs come VERBATIM from the validated 18-block library (SHA-256 proven, never
> AI-regenerated); AI produces only the project glue — RD document drafts and
> one sequence FB. A TIA **Openness compile preflight** exists
> (`AUTO_VERIFIED_compile` tier), so "validated" no longer stops at regex.
> Still pending and still human: PLCSIM behavioural simulation, RD05/safety
> (entirely human by design), the #UNKNOWN/TODO wiring listed in every
> assembly report, and a first real pilot project. Honest framing: the tool
> automates ~90% of the *typing* and the documentation discipline — not 90%
> of the *engineering*.

---

## 2. Why Are We Building This?

In the current automation workflow:
- The same FB skeletons are written by hand on every project (wasted time)
- Every engineer uses their own naming convention (inconsistency)
- AI is given fresh context from scratch on every conversation (inefficient)
- Lessons learned in the field stay with individuals, never reaching the organization (knowledge loss)

**Goal:** Solve all of these once — then reuse the solution on every project.

---

## 3. System Philosophy

### 3.1 Three-Layer Architecture

```
┌─────────────────────────────────────────────┐
│  LAYER 3: Customer Project (Beispielmaschine)│
│  This is where the real work happens        │
└─────────────────────────────────────────────┘
                    ▲
                    │ references
┌─────────────────────────────────────────────┐
│  LAYER 2: Automation Factory (this repo)    │
│  Instructions, templates, AI prompts        │
└─────────────────────────────────────────────┘
                    ▲
                    │ feeds back into
┌─────────────────────────────────────────────┐
│  LAYER 1: Lessons Learned (KB)              │
│  Field knowledge grows the factory          │
└─────────────────────────────────────────────┘
```

### 3.2 Data Flow (Ideal Scenario)

```
[Customer Excel]                                     ← USER INPUT
  • Motor list (tag, type, power, etc.)
  • Valve list
  • Sensor list
  • Process flow diagram reference
       │
       ▼
[Excel → JSON Script]                               ← AUTOMATED
  • Parses the Excel file
  • Produces separate JSON metadata for each device
  • Saves to metadata/ folder
       │
       ▼
[motor.md runs]                                     ← AI (sequentially)
  • Reads metadata/motors/*.json
  • Selects the correct sub-prompt per motor type (DOL/VFD/etc.)
  • Generates FB + DB + instance calls
  • Writes SCL files to _OUTPUT/motor/ folder
  • Marks "motor: DONE" in PROJECT_STATE.json
       │
       ▼
[valve.md runs]                                     ← AI (sequentially)
  • Same logic for valves
       │
       ▼
[sensor.md, pid.md, alarm.md ...]                   ← AI (sequentially)
       │
       ▼
[integrator.md runs]                                ← AI (aggregator)
  • Reviews all generated FBs and DBs
  • Is it consistent with the process flow diagram?
  • Does it comply with the naming standard?
  • Are there conflicts with the IO list?
  • If errors found → writes "feedback: X in motor.md is wrong" to PROJECT_STATE.json
       │
       ▼
[FEEDBACK LOOP]                                     ← If errors exist
  • The relevant MD re-runs and corrects the error
  • integrator.md audits again
  • Continues once clean
       │
       ▼
[test.md runs]                                      ← AI (test)
  • Generates test scenarios for the produced code
  • Simulation scripts (PLCSIM Advanced)
  • If errors found → feeds back to the relevant MD
       │
       ▼
[export.md runs]                                    ← AI (export)
  • Collects all SCL files
  • Generates XML for TIA Portal Openness import (future)
  • For now: zip + manual copy-paste instructions
       │
       ▼
[HUMAN TESTING]                                     ← USER
  • Compilation in TIA Portal
  • Simulation with PLCSIM
  • Field commissioning
       │
       ▼
[FEEDBACK → FACTORY]                                ← MANDATORY ON EVERY PROJECT
  • Gaps/errors found in the field
  • script_propose_update.py
  • Factory grows
```

---

### 3.3 Meta-Project and Customer Project Separation (v2.4)

Automation Factory operates as **a two-level project structure**. When this separation is unclear, logs, versions, and decisions become entangled.

#### Level 1: Automation Factory (Meta-Project)

```
What is it?       The framework itself (this repo)
Output?           NOT SCL code — rules, templates, AI prompts, scripts
Version?          v2.0, v2.1, v2.2, v2.3, v2.4 ... (SemVer in CHANGELOG.md)
Logs?             CHANGELOG.md, FACTORY_IDEAS_BACKLOG.md, KB_FEEDBACK_LOG.md
Decision history? PROGRESS_TRACKER.md Section 3
When does it change? When a new MDSCHEMA, domain file, or script is added
Who changes it?   You + AI conversation (via idea governance)
```

#### Level 2: Customer Project (Production Project)

```
What is it?       An automation project for a real machine
                  Example: Beispielmaschine retrofit, food-line X greenfield
Output?           SCL code, TIA Portal archive, HMI project, documentation
Version?          project_v1.0, v1.1, v1.2 ... (project has its own CHANGELOG)
Logs?             PROJECT_STATE.json + customer changelog inside the project folder
Decision history? Decision log inside the customer project folder
When does it change? Motor added/removed, IO updated, HMI changed, customer request
Who changes it?   Field engineer (you, the team) + AI production sessions
```

#### Which Log Goes Where — Decision Matrix

| Event | Which level? | Which log? |
|-------|-------------|------------|
| New MDSCHEMA added to factory | Meta-project | Factory CHANGELOG (new minor version) |
| New domain file skeleton written | Meta-project | Factory CHANGELOG + IDEAS_BACKLOG |
| Vendor quirk found in the field | Meta-project | KB_FEEDBACK_LOG (factory grows) |
| New AI prompt proposed | Meta-project | IDEAS_BACKLOG |
| 5th motor added to customer X | Customer project | Customer project log (factory untouched) |
| IO list changed in customer X | Customer project | Customer project log |
| HMI screen layout changed in customer X | Customer project | Customer project log |
| "This vendor does X" observation in customer X | **BOTH** | Customer project log (record) + KB_FEEDBACK_LOG (propagate to factory) |

#### Practical Summary

```
Meta-project changes → factory files grow/change → all future projects benefit
Customer project changes → affect only that project → project closes, gets archived
```

**Critical rule:** Changes made in a customer project do not propagate to the factory — **the only exception is field feedback** (`KB_FEEDBACK_LOG`). Changing the factory because "customer X wanted it this way" is wrong. Changing the factory because "we discovered this vendor behavior at customer X and it applies to all projects" is right.

#### To Maintain This Separation

1. When a customer project starts, `script_project_init.py` **copies** from the factory — it does not create a reference
2. Factory gaps found in the customer project are fed back via `script_propose_update.py` (separate process)
3. The factory's version number is **independent** of the customer project's version (e.g. customer project v1.5, factory v2.4)

---

## 4. Decisions (Incremental Development Strategy)

### 4.1 Metadata Format: Excel → JSON Hybrid

**Decision:** Excel for user input, JSON for machine processing.

- Customer/engineer fills in **Excel** (easy, visual, matches existing workflow)
- `script_excel_to_metadata.py` converts Excel to JSON
- All MDs read JSON (fewer parse errors, structured)
- Excel stays as master; JSON is the generated artifact

### 4.2 Orchestration: Manual → Automatic Transition

**Now:** The user manually takes each MD to a new conversation ("now run motor.md").

**Later (Phase 2):** Python orchestration (`script_orchestrator.py`).

**Much later (Phase 3):** Claude Code agent or GUI.

Implication: MDs must be **manually runnable** (meaningful on their own) but also **automatable** in structure (clear input/output).

### 4.3 TIA Portal Openness: Later

**Now:** Generate SCL; user copies-pastes into TIA Portal.

**Later:** Automatic import via Openness API.

Implication: Whatever an MD generates, the output must be **clean SCL** (of a quality that can be fed into Openness).

### 4.4 Inter-MD Communication: Centralized State (PROJECT_STATE.json)

**Decision:** A single `PROJECT_STATE.json` file that all MDs read from and write to.

Contents:
- Current step (e.g. "motor_generation")
- List of completed steps
- Pending feedback (which MD it should go to)
- Paths to generated artifacts
- Error state

Advantage: Easy to say "we stopped at step 4," easy to give context to a new conversation, easy to debug.

---

## 5. Phases (Roadmap)

### Phase 0: Skeleton (CURRENT)

- ✅ Folder structure
- ✅ Naming standard
- ✅ FB template
- ✅ 5 motor sub-prompts
- ✅ Retrofit + Greenfield maestro
- ✅ Hardware analysis files
- ✅ Vision + Skeleton + Tracker files (NEW — these three files)
- ⏳ Create empty skeletons for remaining 28 files (frontmatter + dependencies)

### Phase 1: Content Fill (Coming weeks)

Fill stub files in sequence:
- OB skeletons (OB1, OB100, OB82, OB86)
- Valve sub-prompts (2-way, 3-way, modulating)
- PID, Alarm, Analog scaling, Watchdog
- HMI, Network plan
- Test prompts

Each file is filled **in a separate conversation**. New conversation gets: VISION + SKELETON + TRACKER + the relevant empty file.

### Phase 2: First Real Project

The Beispielmaschine project becomes the pilot. MDs are run manually in sequence. Gaps are fed back via `script_propose_update.py`.

### Phase 3: Automation

`script_excel_to_metadata.py` + `script_orchestrator.py` written. MDs called automatically in sequence.

### Phase 4: Openness Integration

XML import via TIA Portal Openness API. Product ready.

### Phase 5: Public

Publish on GitHub, announce on LinkedIn, open-source / freemium model.

---

## 6. Key Principles

1. **MDs are "software modules."** Each one has a defined input, output, and dependencies.
2. **State is centralized.** A single `PROJECT_STATE.json`; everyone reads from and writes to it.
3. **Feedback is mandatory.** An MD that finds an error routes back to the MD that caused it; downstream does not stop.
4. **AI independence.** The system is not Claude-specific; it should work with GPT/Gemini/local LLM.
5. **Data classification is enforced.** 🟠 CONFIDENTIAL data goes to self-hosted/Enterprise AI, not public AI.

---

## 7. How to Use This File

**When opening a new Claude/AI conversation:**

1. Paste this file → "This is the project vision."
2. Paste `SKELETON_BLUEPRINT.md` → "This is the project structure."
3. Paste `PROGRESS_TRACKER.md` → "This is where we currently are."
4. State the task: *"Fill in PROMPT_VALVE_2WAY_ONOFF.md."*

The AI now works with full context — seamless session handoff.

---

*This file answers the "why" question for the system. The vision stays constant even as the structure evolves.*

---

## 8. Multi-AI Team Architecture (v3.3.0+)

The factory is not tied to a single AI provider. Each provider does what it is best at:

| Provider | Role | Why |
|---|---|---|
| **Claude (Anthropic)** | SCL code generation, safety analysis, gate logic, audit | Best reasoning for safety-critical structured code |
| **Gemini (Google)** | PDF/P&ID/photo analysis, technical translation, large documents | Multimodal; 1M token context; Google Translate backbone |
| **DeepSeek** | Generic template code (PUBLIC projects only) | 10× cheaper; Chinese servers → CONFIDENTIAL blocked by guard |

### Retrofit Pre-Analysis Pipeline

For retrofit projects, the classic bottleneck is manually reading old machine documents (EPLAN PDFs, panel photos, legacy SCL) to produce the IO list. The pipeline now automates this:

```
_raw/                  →  [anonymizer]  →  Gemini Vision   →  Claude         →  Gate 3
(drawings, photos,        (known fields    (multi-file        (consolidate      (engineer
 legacy code)              replaced)        analysis)          RD01 draft)       review)
```

- `_raw/docs/` — PDF manuals, technical specs
- `_raw/drawings/` — EPLAN PDF, P&ID, electrical schematics
- `_raw/photos/` — panel photos, nameplate images
- `_raw/legacy_code/` — old SCL/AWL/STL files

**Data privacy:** The `anonymizer.py` module replaces known customer fields (name, project ID, engineer) and PII patterns (email, phone, address) in **text** before it leaves the machine. **Note:** images, drawings and PDFs sent to Gemini Vision are **not** anonymized — they are uploaded as-is and only *deleted* immediately after each API call, so sensitive markings (logos, title blocks, names) must be redacted manually before upload. The PII regexes are tuned for German-format contact data. CONFIDENTIAL projects require engineer consent (logged to AI_DECISION_LOG); RESTRICTED data is never sent.

### Deferred Ideas (Future Roadmap)

- GUI consent modal for `_raw/` pre-analysis (Faz C)
- Azure Document Intelligence as GDPR-compliant alternative for CONFIDENTIAL drawings
- EPLAN XML export parser (more reliable than PDF OCR for IO extraction)
- Per-step token usage dashboard in GUI
