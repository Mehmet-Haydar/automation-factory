---
title: Factory Mobile Workflow
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
status: ACTIVE
applies_to: [factory_internal, mobile_sessions]
purpose: mobile_work_hygiene
related: [PROJECT_VISION.md, PROGRESS_TRACKER.md, FACTORY_MAESTRO.md]
---

# FACTORY_MOBILE_WORKFLOW.md — Mobile Workflow

> **Purpose of this file:** When you are away from the computer (phone/tablet), which Factory tasks are done **efficiently** and which **should not** be done — a clear checklist.
>
> Philosophy: **Mobile = thinking time. Computer = doing time.**

---

## 1. Quick Decision Table

### Comfortable to do on MOBILE

| Task | Why it fits |
|------|-------------|
| **Brainstorm / discuss ideas** | Voice mode available, can talk while walking |
| **Read + review existing files** | Project knowledge is loaded, scroll to read |
| **Update PROGRESS_TRACKER.md** | Short text, checkbox ticking |
| **Field observation into KB_FEEDBACK_LOG.md** | Field observation → 3 lines, save immediately |
| **Add a new decision to the decision history** | Single-line architectural decision |
| **Draft a new sprint plan** | High-level plan, no code |
| **Discuss the content of a domain file** | "What should be in this domain?" style |
| **Identify missing files** | Audit, gap analysis |
| **Add a term to the glossary** | Single-line definition |
| **Look for answers to open questions** | Which decision to make, alternatives |

### Do CAREFULLY on MOBILE

| Task | Problem | How to do it |
|------|---------|--------------|
| **Drafting a short prompt** | Long typing on a phone is tiring | Dictate by voice, then edit |
| **Editing MD frontmatter** | Risk of YAML errors | No schema validator on mobile, be careful |
| **Single word/sentence fix** | Hard to find the spot | Use the GitHub mobile app's inline edit |
| **Small single-file edit (< 30 lines)** | Phone keyboard is painful | Don't do it unless you must |

### DON'T do on MOBILE

| Task | Why not |
|------|---------|
| **Writing 200+ lines of SCL** | Impossible on a phone keyboard, error rate 50%+ |
| **Writing a Python script** | Indent sensitivity + long functions |
| **Running `script_bulk_md_edit.py`** | The script needs a terminal, none on mobile |
| **Schema validation** (`script_md_schema_validator.py`) | Same |
| **`script_consistency_check.py`** | Same |
| **Writing a new domain/prompt file from scratch** | Long structure, quality drops |
| **Bulk refactor** | Hard to undo if something goes wrong |
| **Git merge / conflict resolution** | Hard in a browser, impossible on mobile |
| **Editing an Excel template** | XLSX is hard to manipulate on mobile |
| **Bulk MD edit (many files at once)** | Same reason |

---

## 2. Mobile Setup — Initial Setup (one-time)

Do these steps once **while on the computer**, then use them on mobile:

### 2.1 Create a Claude Project
1. On Claude.ai → **Projects** → **Create new project**
2. Name: `Automation Factory`
3. Upload these files to **Project knowledge** (in order):
   - `PROJECT_VISION.md` (critical)
   - `SKELETON_BLUEPRINT.md` (critical)
   - `PROGRESS_TRACKER.md` (critical)
   - `FACTORY_MAESTRO.md`
   - `01_GLOBAL_STANDARDS/rules/GLOBAL_NAMING_STANDARD.md`
   - `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_PROMPT_CODE_GEN.md`
   - `01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_DOMAIN_REFERENCE.md`
   - `FACTORY_MOBILE_WORKFLOW.md` (this file)

4. Paste this into **Project instructions**:

```
This project is the live workspace of "Automation Factory".

BEHAVIOR RULES:
- Speak Turkish.
- At the start of each answer, state which sprint/file we are working on.
- If it looks like a mobile chat (short messages, voice mode, etc.), respect FACTORY_MOBILE_WORKFLOW.md:
  don't suggest writing long code/scripts; stay brainstorm + plan + short-edit focused.
- If it's clearly from a computer, you may do long, detailed file writing.

QUALITY RULES:
- When writing a new file, follow MDSCHEMA_PROMPT_CODE_GEN or MDSCHEMA_DOMAIN_REFERENCE.
- Frontmatter mandatory: at minimum the title, version, last_validated, status fields.
- Apply the naming in GLOBAL_NAMING_STANDARD.md to every file/variable/tag.

VISION PROTECTION:
- The principles in PROJECT_VISION.md Section 6 are non-negotiable.
- If a suggestion violates one of the principles, warn first, then propose an alternative.

END OF CHAT:
- At the end of every long chat, give a summary of "how PROGRESS_TRACKER should be updated".
- If a new decision was made, suggest "add to the decision history" items.

FIELD MODE:
- If the user uses phrases like "I'm on site", "there's an observation", offer a record in KB_FEEDBACK_LOG format.
```

### 2.2 GitHub repo + mobile app
1. Put the Factory in a GitHub private repo
2. Install the **GitHub mobile app** on your phone (iOS/Android)
3. Favorite the repo
4. Reading files + small edits + commits can be done in the mobile app

### 2.3 Browser shortcut
- `github.dev/<user>/<repo>` → opens VS Code in the phone browser
- OK for small edits, but the Claude Project + GitHub mobile combo is faster

### 2.4 Voice mode test
- Claude mobile app → microphone icon → switch to voice mode
- Ask "Where are we in Sprint 1 of Automation Factory?"
- If the project knowledge is loaded it answers correctly → setup is complete

---

## 3. Typical Mobile Scenarios — Step by Step

### Scenario A: "I'm on the road, let me think about Sprint 1"
1. Open Claude mobile app → enter the Automation Factory project
2. Switch to voice mode
3. Ask "Which files are in Sprint 1, which is the hardest?"
4. Listen to the answer, take voice notes
5. When you get home → on the computer, write the real file based on your notes

### Scenario B: "I'm on site, I saw something odd in the old PLC"
1. Claude mobile app → enter the project
2. Say "I'll add a new entry to KB_FEEDBACK_LOG.md, write this:"
3. Describe the observation (written or by voice)
4. Claude produces a formatted markdown block
5. GitHub mobile app → open KB_FEEDBACK_LOG.md → paste the block → commit
6. **Time: 2 minutes.** This information used to get lost.

### Scenario C: "Let me update the tracker, we finished a task yesterday"
1. Claude mobile app → enter the project
2. Say "In PROGRESS_TRACKER.md, mark this file in Sprint 1 as completed, set the last-updated date to today"
3. Claude gives the exact lines to change (in str_replace format)
4. GitHub mobile → open the file → apply the changes → commit
5. **Time: 3 minutes.**

### Scenario D: "I have a new prompt idea, let me record it"
1. Claude mobile app → enter the project
2. "Let's discuss this idea: [idea]"
3. Claude lays out the pros/cons, suggests alternatives
4. If you decide: "Let's add this idea to PROGRESS_TRACKER as an open question, discuss it in Sprint X"
5. Claude gives the updated lines
6. When back at the computer, apply it to the real file

### Scenario E: "Let me review an existing file"
1. Claude mobile app → enter the project (knowledge already loaded)
2. "Review PROMPT_MOTOR_DOL.md, is there any section that might be missing?"
3. Claude lists critiques/suggestions
4. Apply the ones you like on the computer

---

## 4. Mobile-Computer Sync Discipline

**The one golden rule:** On mobile, only touch `.md` files. Never touch `.scl`, `.py`, `.json`, `.xlsx` files.

### Division of labor:

```
MOBILE (phone/tablet):
- *.md files (especially TRACKER, FEEDBACK_LOG, KB_*)
- Brainstorm
- Review
- Plan

COMPUTER (Cursor/VS Code):
- *.scl (SCL code)
- *.py (scripts)
- *.json (schema, state)
- *.xlsx (metadata input)
- running scripts
- bulk edit
- git merge
- creating new file skeletons
```

### Sync rhythm:

- **A change on mobile** → always commit it. Never leave an "incomplete" mobile change.
- **When back at the computer** → first thing is `git pull`. Pull the commits made on mobile.
- **End of sprint** → PROGRESS_TRACKER must be current. On mobile or computer is fine, but it must be done.

---

## 5. 5 Things to Never Do From Mobile

If you try these five from a phone, you'll get into trouble:

1. **Creating a new `*.scl` template** → indent + syntax is hard
2. **Rewriting `script_*.py`** → logic sensitivity
3. **Editing `08_METADATA_INPUT/template_*.xlsx`** → mobile Excel = agony
4. **Multi-file refactor** → if 3+ files are affected, wait for the computer
5. **Cursor `.cursorrules` or `.mdc` files** → they affect AI behavior, need careful edits

---

## 6. Emergency Protocol

For "I'm on mobile right now but I need something urgently" situations:

| Situation | What to do |
|-----------|------------|
| "I urgently need to start a new project, is the Factory ready?" | `script_project_init.py` must be run → wait for the computer. Collect metadata on site with pen and paper. |
| "I need to show the Factory to a customer" | Convert `PROJECT_VISION.md` and `FACTORY_MAESTRO.md` to PDF and present. Claude mobile can do this. |
| "There's a bug, I need to fix it now" | Is the bug in a `*.md`? Fix + commit. In a `*.scl`/`*.py`? Open a GitHub Issue, return to the computer. |
| "Let me have the AI generate quick code" | Claude mobile + Project knowledge → a small snippet is OK, but the result isn't written to a file, only used as reference. |

---

## 7. Performance Expectation

Mobile productivity with the right setup:

| Task type | Computer time | Mobile time | Mobile-friendly |
|-----------|---------------|-------------|-----------------|
| Tracker update | 2 min | 3 min | Yes |
| Feedback log entry | 3 min | 2 min | **Faster on mobile** |
| Brainstorm chat | 30 min | 30 min | Equal (faster on mobile with voice) |
| New domain file | 60 min | 4 hours | No, computer required |
| SCL template | 90 min | impossible | No, computer required |
| Sprint planning | 45 min | 60 min | OK on mobile too |

---

## 8. Maintaining This File

- New mobile scenarios can be added (Section 3)
- New "don't" rules can be added (Section 5)
- Setup steps change **very rarely**
- The sync discipline is **never relaxed** (Section 4)

---

*Mobile is 30% of the Factory, the computer 70%. With the right division of labor the total is 120%.*
