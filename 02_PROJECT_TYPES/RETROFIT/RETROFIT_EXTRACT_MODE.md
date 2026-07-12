---
title: Retrofit Operating Modes Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD04_Mode
prerequisite: [MDSCHEMA_RAWDATA_04_MODE.md, RETROFIT_EXTRACT_DATADICT.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_MODE_FROM_CODE.md
---

# RETROFIT_EXTRACT_MODE.md — Operating Modes Extraction Procedure

> **Goal:** extract the legacy machine's operating modes (AUTO/MANUAL/SETUP, etc.) and bring them into compliance with OMAC PackML / ISA-88 §4.7.

---

## 1. Prerequisites

- [ ] RD01 IO + RD02 DataDict complete
- [ ] Operator/engineer interview held: "How many modes does this machine run in?"
- [ ] HMI screenshots or video recording (for mode buttons and their colours)
- [ ] Is a Mode-Word or Mode-Step used? (Varies on legacy systems)

---

## 2. Workflow

### 2.1 Mode Detection — Source Clues

| Source | Clue |
|--------|------|
| **HMI screen** | Mode_Auto / Mode_Hand / Mode_Setup buttons, indicator lamp colours |
| **DB content** | `CurrentMode` (INT/WORD/ENUM), `Mode_Word`, `MachineMode` |
| **Symbol names** | "Modus", "Operation_Mode", "Betriebsart" (German) |
| **OB1 structure** | `IF Mode = AUTO THEN ... ELSIF Mode = MANUAL THEN ...` |
| **PackML** | Separate "MachineMode" + "MachineState" → OMAC was applied deliberately |

### 2.2 Operator Interview (CRITICAL)

An interview with the operator or maintenance staff is **more reliable than code analysis**. Questions:

1. "How many different operating modes does this machine have?"
2. "When is each mode used?" (Production, maintenance, calibration, cleaning, etc.)
3. "How do you switch to each mode?" (HMI key, switch, sequence)
4. "Outside of emergencies, are there constraints between modes?"
5. "Is there a LOTO (Lock-Out Tag-Out) procedure?"
6. "Does Setup mode run the machine slowly / single-step?"

### 2.3 Standard Mode Set

Most industrial machines revolve around these modes:

| ModeID | Standard Name | German | OMAC PackML | Colour |
|--------|---------------|--------|-------------|--------|
| M00 | Emergency | NOT-AUS | Aborted | 🔴 #FF0000 |
| M01 | Auto | Automatik | Execute | 🟢 #00C800 |
| M02 | Manual | Hand | Suspended | 🟠 #FFA500 |
| M03 | Setup | Einrichten | Suspended | 🟡 #FFFF00 |
| M04 | Maintenance | Wartung | Stopped | 🔵 #0080FF |
| M05 | Cleaning | Reinigung | Suspended | 🟣 #C800C8 |
| M06 | Lockout (LOTO) | Sicherungs-modus | Stopped | ⚫ #000000 |

### 2.4 Hybrid Workflow

```
[1] _parsed.md ready
       ↓
[2] AI prompt: PROMPT_EXTRACT_MODE_FROM_CODE.md
       ↓
[3] RD04_Mode_draft.md (AI proposal)
       ↓
[4] Operator interview results + human review
       ↓
[5] Map to the standard mode table
       ↓
[6] Apply HMI colour standard (AUTOMATION_FACTORY rule)
       ↓
[7] RD04_Mode.xlsx (approved)
```

### 2.5 Human Review Checklist

#### A. Mode Completeness
- [ ] M00 Emergency present (mandatory on every machine)
- [ ] At least one production mode (M01 AUTO or equivalent)
- [ ] If maintenance mode (M04) exists, link to LOTO has been considered
- [ ] Cleaning mode (may be mandatory for food/pharma industries)

#### B. Priority Assignment
- [ ] M00 = Priority 0 (fixed rule)
- [ ] Production modes 50+ Priority
- [ ] Emergency/safety modes Priority 1-10
- [ ] All Priority values are UNIQUE

#### C. PackMLState Mapping
- [ ] OMAC PackML v3.0 enum valid (Idle/Execute/Held/Suspended/...)
- [ ] AUTO typically Execute, MANUAL typically Suspended
- [ ] Emergency typically Aborted

#### D. EntryCondition / ExitCondition
- [ ] Concrete conditions (boolean expression) for every mode
- [ ] M00 ExitCondition: "Reset_Cmd AND E_Stop = FALSE"
- [ ] AUTO EntryCondition: "NOT M00 AND Safety_OK AND Op_Auto_Btn"

#### E. PermittedActions / RestrictedActions
- [ ] Production actions forbidden in maintenance mode
- [ ] Single-step allowed in setup mode
- [ ] All actions forbidden in LOTO mode (only reset/unlock)

#### F. HMI Information
- [ ] HMI_Color in `#RRGGBB` hex format
- [ ] HMI_Text multi-lang (EN mandatory, DE for the customer, TR for your project)
- [ ] DB_ModeWord variable defined in RD02

---

## 3. Field-Discovery Strategy

### 3.1 If the Existing Modes Are Unclear

1. **Watch the HMI for 30 minutes:** which buttons does the operator press when changing modes?
2. **Shell document:** the operations manual written by the old engineer (PDF/Word)
3. **Maintenance log:** mode names appear in maintenance records
4. **CE certificate:** modes are listed in the risk-assessment file

### 3.2 Mode-Word Structure

A pattern often seen in legacy projects:

```
DB_System
  ModeWord: WORD       // 1=AUTO, 2=MANUAL, 3=SETUP, ...
  ModeBits: ARRAY OF BOOL  // one bit per mode
```

or:

```
M10.0 = Auto_Active
M10.1 = Manual_Active
M10.2 = Setup_Active
```

### 3.3 PackML Signatures

If the software was written with PackML discipline, you will see these markers in the code:
- Separate `MachineMode` and `MachineState` variables
- `Producing`, `Held`, `Suspended` state names
- `STATE_ENUM` or `MODE_ENUM` UDTs
- References to "PackTags" (OMAC standard tag names)

---

## 4. Validation

### 4.1 Automated

```bash
python 05_SCRIPTS/dev/script_consistency_check.py \
  --project <project> \
  --schema RD04 \
  --check-uniqueness Priority \
  --check-emergency-priority-zero
```

### 4.2 Manual

| Check | Target |
|-------|--------|
| M00 present | Mandatory |
| M00 Priority=0 | Fixed |
| Priority unique | Across all modes |
| PackMLState OMAC enum | v3.0 |
| HMI_Color 6-digit hex | `#RRGGBB` |
| DB_ModeWord in RD02 | Cross-ref |

---

## 5. Common Pitfalls

- ❌ **AI mis-maps PackML:** treats "Manual" as `Held` when the correct mapping is `Suspended`. Cross-check against the OMAC v3 reference.
- ❌ **Wrong HMI_Color intuition:** the AI assigns green to Setup — the standard is yellow (#FFFF00).
- ❌ **Reset permission in LOTO mode:** leaving Reset in PermittedActions defeats the lockout → safety issue.
- ❌ **Inventing modes:** the legacy code only has 2 modes but the AI writes 6 → constrain via the operator interview.
- ❌ **Weak EntryCondition:** "Mode_Btn_Pressed" is not enough; use "Mode_Btn_Pressed AND NOT M00 AND Auth_Level >= OPERATOR".
- ❌ **Missing multi-lang text:** English only → TR/DE missing, the customer may reject the deliverable.

---

## 6. AI Prompt Suggestion

`04_AI_PROMPTS/analyze/PROMPT_EXTRACT_MODE_FROM_CODE.md` — run the system prompt twice (AI draft first, then revise with operator input).

---

## 7. Gate 3 Checklist

- [ ] M00 Emergency present, Priority=0
- [ ] Operator interview held, results documented
- [ ] All Priority values unique
- [ ] PackMLState matches the OMAC enum
- [ ] HMI_Color standard applied
- [ ] Multi-lang HMI_Text (project language + German)
- [ ] DB_ModeWord variable defined in RD02
- [ ] EntryCondition/ExitCondition concrete for every mode
- [ ] PermittedActions/RestrictedActions matrix complete
- [ ] If a LOTO mode exists, the safety engineer has signed off

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_04_MODE.md`
- **AI prompt:** `PROMPT_EXTRACT_MODE_FROM_CODE.md`
- **Previous guide:** `RETROFIT_EXTRACT_DATADICT.md`
- **Next:** `RETROFIT_EXTRACT_TIMING.md`
- **Dependent RDs:** RD02 (DB_ModeWord), RD03 (Step ModeReq), RD11 (HMI multi-lang)
- **Standards:** OMAC PackML v3.0, ISA-88 §4.7

---

*v1.1.0 — Full English body (2026-05-23). Modes are the machine's "personality". Wrong mode definition → whole project is wrong. The operator interview cannot be skipped.*
