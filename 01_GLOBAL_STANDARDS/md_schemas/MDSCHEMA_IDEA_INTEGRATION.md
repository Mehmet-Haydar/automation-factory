---
title: MD Schema - Idea Integration Analysis
version: 1.0.0
last_validated: 2026-05
applies_to: [factory_internal]
status: FILLED
schema_for: FACTORY_IDEAS_BACKLOG entries (APPROVED → IN_PROGRESS analysis)
prerequisite: [PROJECT_VISION.md, FACTORY_MAESTRO.md, GLOBAL_NAMING_STANDARD.md]
related: [FACTORY_IDEAS_BACKLOG.md, MDSCHEMA_PROMPT_CODE_GEN.md, MDSCHEMA_DOMAIN_REFERENCE.md]
---

# MDSCHEMA_IDEA_INTEGRATION.md

> **This template systematically analyzes how an approved idea will be integrated into the Factory structure.** Exists so Factory's own rules make the decision, not subjective AI judgment.

---

## 1. Why Does This Template Exist?

The Factory is essentially **its own customer**. Constant flow of "add this, change that" ideas from external AIs or internal discussions. When a user likes an idea and says "apply it," AI has two dangerous behaviors:

1. **Guessing:** "Maybe put this file there" — intuitive decision, creates conflicts later
2. **Jumping:** Creating files without impact analysis, later shows up as "inconsistency"

This template **forces discipline on AI**. Cannot proceed to implementation until all 7 sections are filled.

**Usage rule:** For every idea in `FACTORY_IDEAS_BACKLOG.md` with status = APPROVED, before applying it, an analysis file following this schema is generated. Files/code cannot be created until analysis is approved.

---

## 2. Required Structure

The following 7 sections are mandatory. Fill each one, don't skip. You can say "not applicable" but cannot skip without explanation.

```markdown
---
title: Idea Integration Analysis - <IDEA-ID>
version: 1.0.0
last_validated: YYYY-MM
status: ANALYSIS | APPROVED_FOR_IMPLEMENTATION | IMPLEMENTED | ROLLED_BACK
schema: IDEA_INTEGRATION
backlog_ref: IDEA-YYYY-MM-DD-NNN
---

# IDEA_INTEGRATION_<IDEA-ID>.md

> **Idea essence:** <one-liner>

---

## 1. Understanding the Idea

**One-liner explanation:**
<what the idea wants in one sentence>

**What problem does it solve:**
<concrete, measurable problem>

**Which Factory principle does it touch:**
PROJECT_VISION.md Section 6 — which of the 5 principles:
- [ ] 6.1 Single source of truth
- [ ] 6.2 AI is disciplined
- [ ] 6.3 Feedback is mandatory
- [ ] 6.4 Timestamp is mandatory
- [ ] 6.5 Frontmatter is required
- [ ] 6.6 Single platform: TIA Portal V18+
- [ ] 6.7 Generate-validate-iterate loop
- [ ] 6.8 Mobile-friendly hygiene

**How it touches:** [supports / neutral / creates risk]
<explanation: if supports how, if risk why>

---

## 2. Structural Positioning

**File type decision:**
- [ ] New file
- [ ] Addition to existing (which: ___)
- [ ] Change to existing (which: ___)
- [ ] New script (new file in 05_SCRIPTS .py)
- [ ] Philosophy change only (PROJECT_VISION update)

**If new file:**
- Which folder? [01_GLOBAL_STANDARDS / 02_PROJECT_TYPES / 03_DOMAIN_TOOLS / 04_AI_PROMPTS / 05_SCRIPTS / 06_KNOWLEDGE_BASE / 07_PROJECT_TEMPLATE / 08_METADATA_INPUT]
- Full path: ___
- File name proposal: ___ (per FACTORY_MAESTRO.md Section 2 naming standard)
- Format check: `[SCOPE]_[DOMAIN]_[SUB].md`?
  - SCOPE: ___ (GLOBAL/RETROFIT/GREENFIELD/DOMAIN/PROMPT/SCRIPT/KB/MDSCHEMA)
  - DOMAIN: ___
  - SUB: ___ (optional)

**Which MD schema will it follow:**
- [ ] MDSCHEMA_PROMPT_CODE_GEN (if AI code-generation prompt)
- [ ] MDSCHEMA_DOMAIN_REFERENCE (if engineering reference)
- [ ] MDSCHEMA_IDEA_INTEGRATION (this template — meta level)
- [ ] New schema needed (reason: ___)
- [ ] No schema (CHANGELOG, README like standard-exempt)

---

## 3. Dependency Analysis

**This new file/change will read from:**
| Source File | What It Reads |
|------------|---------------|
| ... | ... |

**These files will reference this new one:**
| Target File | How It References |
|------------|-------------------|
| ... | ... |

**Output type:**
- [ ] SCL code (goes to TIA Portal)
- [ ] JSON metadata (`08_METADATA_INPUT/` format)
- [ ] Markdown documentation
- [ ] Python script
- [ ] Standards/rules only (no output artifact, just rules)

**Output path:** ___

---

## 4. Conflict Check (Most Critical Section)

Following checklist **all green** before moving to Section 5. If any red, idea revised or rejected.

### 4.1 Naming
- [ ] Conforms to FACTORY_MAESTRO.md Section 2 standard?
  - If not: Corrected name: ___
- [ ] Conforms to GLOBAL_NAMING_STANDARD.md (variable/tag names)?
  - If not: Correction: ___

### 4.2 Single Source of Truth
- [ ] Does existing file already do this job?
  - If yes, which: ___
  - Decision: [Merge / Reject new file / Modify existing]
- [ ] Will same info be in two places?
  - If yes: Which is "master": ___
  - How does other place reference: ___

### 4.3 Vision Alignment
- [ ] Does it enter PROJECT_VISION.md Section 7 ("What We Don't Do") list?
  - If yes, which: ___ → **REJECT**
- [ ] Does it break single-platform principle? (extending beyond TIA Portal V18+?)
  - If yes, reason: ___ → **REJECT or separate VISION UPDATE process**

### 4.4 Structural Hygiene
- [ ] Is frontmatter template correct? (title, version, last_validated, status minimum)
- [ ] Estimated line count exceeds 500?
  - If yes: split strategy: ___
- [ ] Mobile-friendliness: does it enter FACTORY_MOBILE_WORKFLOW.md Section 5 "don'ts" list?

### 4.5 Reversibility
- [ ] Is this change reversible?
- [ ] If not reversible (e.g., output format change, old projects affected) — is this acceptable?

**Conflict check result:**
- [ ] ✅ All clear — proceed to Section 5
- [ ] ⚠️ Corrections needed — idea will be revised
- [ ] ❌ Rejected — reason: ___

---

## 5. Implementation Steps

Ordered, concrete, copy-paste-ready steps. Each step touches one file.

| # | Step | File | Command/Action |
|---|------|------|-----------------|
| 1 | <what to do> | <which file> | <bash command or edit summary> |
| 2 | ... | ... | ... |
| 3 | ... | ... | ... |
| ... | ... | ... | ... |
| N | Update CHANGELOG | `CHANGELOG.md` | Add v2.X.0 entry |
| N+1 | Update TRACKER | `PROGRESS_TRACKER.md` | Add to Sprint X, decision log |
| N+2 | Update BACKLOG | `FACTORY_IDEAS_BACKLOG.md` | IDEA-X status: APPLIED + CHANGELOG ref |

**Estimated time:** ___ minutes
**Can be done on mobile:** [Yes / No — reason: ___]

---

## 6. Rollback Plan

**If problem occurs after application:**

| Issue Type | Rollback Method |
|-----------|-----------------|
| New file in wrong location | `git mv` to move, update references |
| Existing file damaged | `git revert <commit>` |
| Multiple files affected | Revert entire change commit, IDEA status: ROLLED_BACK |

**Which commit to return to:** ___ (commit hash before implementation)

**Rollback verification:**
- [ ] `script_consistency_check.py` runs?
- [ ] `script_md_schema_validator.py` runs?

---

## 7. Validation

**After application, success criteria:**

| Criteria | How to Test |
|----------|-------------|
| New file in correct location | `find` command path check |
| Valid frontmatter | `script_md_schema_validator.py --target ___` |
| Naming standard compliant | `script_consistency_check.py` |
| Dependencies unbroken | Manual: open referenced files, grep to verify |
| Vision aligned | Manual review (user approval) |

**Which other file tests this new thing (if any):**
- ___

**First actual usage:** When will this be first used in practice: ___

---

*When analysis complete: status → APPROVED_FOR_IMPLEMENTATION. After application: status → IMPLEMENTED.*
```

---

## 3. Filling Discipline

### 3.1 When Is This Filled?

```
FACTORY_IDEAS_BACKLOG.md     →    This Template                →   Implementation
───────────────────────          ─────────────────────             ────────────────
IDEA-X status:                   New file:                         Files change
NEW                              IDEA_INTEGRATION_X.md             CHANGELOG added
↓ (user reads)                   ↓ (AI fills)                      IDEA-X status:
REVIEWED                         ANALYSIS                          APPLIED
↓ (user: "apply")               ↓ (user approves)
APPROVED                        APPROVED_FOR_IMPLEMENTATION
                                ↓ (implementation runs)
                                IMPLEMENTED
```

### 3.2 Where Is It Saved?

Recommended location: `06_KNOWLEDGE_BASE/idea_integrations/IDEA_INTEGRATION_<ID>.md`

Folder auto-created on first file. Applied analyses become archive — in the future when similar idea arrives, can reference "last time we did this for these reasons."

### 3.3 Cannot-Skip Section

**Section 4 (Conflict Check) is mandatory.** Other sections can be marked "not applicable," but Section 4 is fully required for every idea. Because:
- New file: conflict check is physical
- Existing file change: conflict check is logical
- Philosophy change only: conflict check is visional

All valid.

---

## 4. Typical Usage of This Schema

### Scenario: "Another AI suggested this idea, I like it, apply it"

```
You   : "Apply IDEA-2026-05-08-001 from FACTORY_IDEAS_BACKLOG.md"
AI    : "Understood. Creating analysis per MDSCHEMA_IDEA_INTEGRATION.md."
        [generates analysis file, fills all 7 sections]
        "Conflict check found issue: Section 4.2 shows existing file
         already does similar work (CHANGELOG.md). Recommendation:
         Instead of rejecting idea, expand existing system."
You   : "OK, revise"
AI    : [analysis revised, status: APPROVED_FOR_IMPLEMENTATION]
        "Ready to implement?"
You   : "Go"
AI    : [executes Section 5 steps one by one, completes]
        "Done. IDEA-X status: APPLIED. v2.3.0 entry in CHANGELOG."
```

---

## 5. Maintaining This Schema

- New Factory principle added → Sections 1 and 4.3 updated
- New folder added → Section 2 updated
- New MD schema added → Section 2.3 updated
- New frequently-skipped check found → added to Section 4
- Process evolves → update this file

---

*This is how the Factory improves itself. Place where AI is disciplined.*
