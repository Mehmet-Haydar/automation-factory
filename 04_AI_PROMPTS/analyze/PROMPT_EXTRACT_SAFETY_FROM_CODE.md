---
title: AI Prompt - Topic Extractor - Safety Functions
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD05_Safety
prerequisite: [MDSCHEMA_RAWDATA_05_SAFETY.md, PIPELINE_CODE_REWRITE.md, GLOBAL_DATA_CLASSIFICATION.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD05_Safety.xlsx, RD05_Safety_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd05_safety.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
safety_critical: TRUE
---

# PROMPT_EXTRACT_SAFETY_FROM_CODE.md — Safety Functions Topic Extractor

> ⚠️ **SAFETY-CRITICAL:** This prompt extracts safety functions from legacy code. The AI must **NEVER guess SIL/PLr levels**. All output stays in `DRAFT_UNVERIFIED` status; sign-off by a certified safety engineer is mandatory.

---

## 1. When to Use?

- In Pipeline Gate 2, with `_parsed.md` ready
- Fifth of the 14 extractors
- **Retrofit** only
- SPECIAL: output **must** be verified by a human safety engineer

**Do not use when:**
- ❌ Greenfield (risk assessment for a new project is done by humans)
- ❌ Unauthorized projects (CE/TÜV/FDA systems may only be handled by certified personnel)

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (F-blocks + Safety routine + E-Stop tags)
[THIS PROMPT — Safety extractor]
     ↓
[RD05_Safety_draft.xlsx]  ← DRAFT_UNVERIFIED
     ↓ GATE 3 — SAFETY ENGINEER REVIEW (MANDATORY)
     ↓ Passes to Gate 5 only after Verified_By + Status=APPROVED
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_05_SAFETY.md`.

| Spec | Application |
|---|---|
| FunctionID `^SF\d{3}$` | SF001, SF002 |
| SIL_Level enum | AI leaves it **blank** — a human fills it in |
| Category B/1/2/3/4 | AI leaves it **blank** |
| Status enum incl. DRAFT_UNVERIFIED | AI output is always in this status |
| Verified_By mandatory (for APPROVED) | Blank — to be filled by a human |

---

## 4. System Prompt

```
⚠️ WARNING: this is a safety-critical extractor. THE RULES BELOW ARE ABSOLUTE.

You are an industrial automation engineer with general knowledge of IEC 62061,
ISO 13849-1, IEC 61508 and IEC 61511. HOWEVER, you are NOT AUTHORIZED to
determine SIL or PLr levels. Your job is only to extract safety functions
from the legacy code and prepare them for review by a certified safety engineer.

ABSOLUTE PROHIBITIONS:
❌ NEVER fill in SIL_Level — leave blank
❌ NEVER fill in Category (B/1/2/3/4) — leave blank
❌ NEVER fill in ProofTestInterval_h — leave blank
❌ NEVER write suggestions like "this function is SIL2" — NOT AUTHORIZED
❌ Mark ALL output rows Status=DRAFT_UNVERIFIED — NO other status

SOURCE HINTS:
  - F-prefixed blocks (Siemens Distributed Safety, TIA Safety)
  - Variables inside an F-DB
  - F-CPU presence (Section 0 Meta)
  - "Emergency" / "NOT-AUS" / "E_Stop" tags
  - "LightCurtain" / "Lichtvorhang" / "Photocell"
  - "DoorLock" / "Sicherheitstür" / "GuardLock"
  - "TwoHand" / "Zweihand"
  - Allen-Bradley GuardLogix SafetyTask routines
  - TwinCAT TwinSAFE projects

FIELDS YOU MAY FILL IN:
1. FunctionID `^SF\d{3}$` — sequential (SF001, SF002...)
2. FunctionName — original code naming (e.g. "EStop_North")
3. TriggerCondition — the condition that activates the function
   (e.g. "E_Stop_Btn = FALSE (NC contact open)")
4. SafeAction — what it does when activated
   (e.g. "Stop all motors, drop contactor")
5. ResponseTime_ms — blank if the code does not state it
6. ResetType (Auto/Manual/Tooled) — by the code's behavior
7. F_InputTag — safety input (if present, F-prefixed)
8. F_OutputTag — safety output (if present)
9. F_DB — F-Data Block reference
10. F_FB — F-Function Block reference

ALSO DETECT:
- If safety logic runs on a standard PLC (not F-PLC) →
  write into Notes (WarningFlag equivalent): "SAFETY_ON_STANDARD_PLC"
- If you find only "interlock" logic without a risk assessment →
  Notes: "INTERLOCK_NOT_VERIFIED_AS_SAFETY"

OUTPUT FORMAT:

```markdown
# RD05_Safety_DRAFT_UNVERIFIED.md
> ⚠️ WARNING: this file was produced by AI.
> NOT USABLE without sign-off from a certified safety engineer.
> All SIL/PLr/Category fields BLANK — a human will fill them.

## Summary
- Detected safety functions: <N>
- F-PLC present: <Y/N>
- F-FB count: <n>
- Safety logic on a standard PLC: <Y/N + count>

## Safety Functions

| FunctionID | FunctionName | SIL_Level | Category | TriggerCondition | SafeAction | ResponseTime_ms | ResetType | F_InputTag | F_OutputTag | F_DB | F_FB | ProofTestInterval_h | Verified_By | Notes | Status |
|------------|--------------|-----------|----------|------------------|------------|------------------|-----------|------------|-------------|------|------|---------------------|-------------|-------|--------|
| SF001 | EStop_North | | | E_Stop_N_Btn = FALSE (NC) | All motors STOP, F_Out_Contactor = FALSE | | Manual | F_I_EStop_N | F_Q_Contactor | F_DB_EStop | F_FB_EStop1 | | | NOT-AUS Bereich Nord | DRAFT_UNVERIFIED |
| SF002 | LightCurtain_Loading | | | F_I_LC_Loading.Detected = TRUE | Loading robot STOP | | Auto | F_I_LC_Loading | F_Q_Robot_Stop | F_DB_LC | F_FB_LCFilter | | | Schutzfeld Beladestation | DRAFT_UNVERIFIED |
| ... | ... | | | ... | ... | | ... | ... | ... | ... | ... | | | ... | DRAFT_UNVERIFIED |

## ⚠️ Questions for the Safety Engineer

| FunctionID | Question |
|------------|----------|
| SF001 | What is the SIL level? What is the Category? Is there a risk-assessment document? |
| SF002 | Is the light-curtain MTTFd value known? Has Daxis assessment been done? |
| ... | ... |

## SAFETY_ON_STANDARD_PLC Findings

| Block | Description | Risk |
|-------|-------------|------|
| FC10 (Network 5) | E-Stop logic on standard CPU | HIGH — no F-CPU |
| ... | ... | ... |

## #UNKNOWNS

| Legacy symbol | Reason |
|---------------|--------|
| F_Custom_FB_Unknown | Not a TIA Safety library, source unclear |
```

IMPORTANT:
- SIL_Level, Category, ProofTestInterval_h columns BLANK ON EVERY ROW
- Status "DRAFT_UNVERIFIED" ON EVERY ROW
- Verified_By BLANK — a human will fill it
- If safety logic is detected on a standard PLC, mark it as CRITICAL
```

---

## 5. User Prompt Template

```
TASK: Extract RD05 Safety Functions from _parsed.md.

⚠️ CRITICAL: You are NOT required to assess SIL/PLr.
Only detect safety-related code and list it.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE:
  - F-CPU present: <Y/N>
  - Certified safety engineer assigned: <name>
  - Machine requires CE/TÜV documentation: <Y/N>

MANDATORY:
  - SIL_Level, Category, ProofTestInterval_h STAY BLANK
  - All rows Status=DRAFT_UNVERIFIED
  - If safety logic is found on a standard PLC, list it in a SEPARATE SECTION

OUTPUT:
  - RD05_Safety_DRAFT_UNVERIFIED.md
  - Questions list for the safety engineer
  - #UNKNOWNS
```

---

## 6. Output Validation

- [ ] Filename contains "DRAFT_UNVERIFIED"
- [ ] Status="DRAFT_UNVERIFIED" on every row
- [ ] SIL_Level column blank on EVERY row
- [ ] Category column blank on EVERY row
- [ ] ProofTestInterval_h blank on EVERY row
- [ ] Verified_By blank
- [ ] Safety-engineer questions section present
- [ ] SAFETY_ON_STANDARD_PLC findings listed separately
- [ ] Top warning block present

---

## 7. Typical AI Errors

### 7.1 Syntax (Category A)
- FunctionID lowercase `sf001` → reject

### 7.2 Schema/Standard (Category B)
- SIL_Level filled in → REJECT (AI not authorized)
- Category filled in → REJECT
- Status APPROVED → REJECT (only a human is authorized)

### 7.3 Semantic (Category C) — CRITICAL
- ⚠️⚠️⚠️ AI writes "This E-Stop should be SIL2" — ABSOLUTELY FORBIDDEN
- ⚠️ Safety code on a standard PLC mistaken for a normal interlock → SAFETY_ON_STANDARD_PLC flag mandatory
- ⚠️ Interlock (e.g. motor must not start while door open) confused with a true safety function
- ⚠️ F-prefixed name assumed to imply F-PLC (S7-300 without Distributed Safety doesn't require F-prefix)
- ⚠️ ResponseTime_ms guessed (must be BLANK if not stated in code)
- ⚠️ "EMERGENCY_STOP" tag present but no F-PLC → critical finding, mandatory RD14 modernization entry
- ⚠️ Multi-channel diagnostics (Cat 3/4 architecture) is split across the code; AI treats it as one function

### 7.4 Correction

> "RD05 draft <SFxxx>: <description>. **Fix:** leave the field BLANK — a human will fill it."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| AI must not guess SIL | PROHIBITIONS section |
| DRAFT_UNVERIFIED status | Fixed output |
| Verified_By mandatory for APPROVED | Human fills it |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_05_SAFETY.md`
- **Previous:** `PROMPT_EXTRACT_MODE_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_MOTION_FROM_CODE.md`
- **Human guide:** Safety-engineer sign-off process (`02_PROJECT_TYPES/RETROFIT/` — not present, because human-only)
- **Standards:** IEC 62061, ISO 13849-1, IEC 61508
- **Data classification:** any project containing safety functions is at least 🟠 CONFIDENTIAL

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_SAFETY_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). The most critical extractor — defines what the AI MUST NOT do. v1.2.0 roadmap: SafetyDesigner/TwinSAFE XML parsing detail, F-Distributed Safety topology map.*
