---
title: MD Schema - Code Generation Prompts
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-08
applies_to: [factory_internal]
status: FILLED
schema_for: 04_AI_PROMPTS/code_gen/**/*.md
---

# MDSCHEMA_PROMPT_CODE_GEN.md

> **This template defines the required structure for all code-generation prompt MD files.**
> When writing a new prompt, follow this structure. When modifying existing prompts, preserve this structure.

---

## 1. Why Does This Template Exist?

All code-gen MD files (motor, valve, PID, alarm, etc.) **must follow the same structure** because:
- AI knows where to read in each file → better output
- Bulk edit scripts can target specific sections
- Audit scripts can catch missing sections
- New engineers understand the system in 5 minutes

---

## 2. Required Structure (Copy-Paste Exactly, Then Fill)

The following structure **must appear in every** code-gen MD **in the same order**:

```markdown
---
title: AI Prompt - <Specific Name>
version: <SemVer>
last_validated: YYYY-MM
applies_to: [retrofit|greenfield|both]
device_type: <DOL|VFD|VALVE_2WAY|PID|...>
power_range: <optional, for motors>
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_FB_TEMPLATE.scl, ...]
target_ai: [Claude Sonnet 4+, GPT-4+, Cursor]
metadata_input: <which JSON schema to read, e.g: motors.schema.json>
output_artifacts: [FB, DB, instance_call, test_scenarios]
schema: PROMPT_CODE_GEN
---

# <FILE_NAME>.md

> **<One-liner — what does this prompt do?>**

---

## 1. When to Use?

<In which scenario does this prompt activate?>
- Power range: <if applicable>
- Typical application: <one-sentence example>
- Should NOT be used when: <if applicable>

## 2. Hardware Architecture

<ASCII diagram or Mermaid — visual of physical connection>

```
PLC ──[Q]──► <component> ──► <target>
              │
              └─[feedback]──► PLC
```

**Typical IO:**
- <DI/DO/AI/AO list>

## 3. Metadata Input (JSON)

This prompt reads this JSON schema: `<schema_filename>.schema.json`

**Expected fields:**
```json
{
  "tag": "MOT_CV01_001_DRIVE",
  "type": "DOL",
  "power_kw": 5.5,
  "...": "..."
}
```

## 4. System Prompt (Fixed Instructions for AI)

```
You are an industrial automation engineer expert in TIA Portal V18+.
Task: <specific task definition>

STRICT RULES:
1. Naming: GLOBAL_NAMING_STANDARD.md
2. Structure: GLOBAL_FB_TEMPLATE.scl
3. All comments in English
4. Optimized Access ON
5. Reset rising edge

DEVICE_TYPE-SPECIFIC — CRITICAL:
1. <first critical rule>
2. <second critical rule>
...

MANDATORY STATE MACHINE:
  0   IDLE
  10  ...
  ...
  99  ERROR

MANDATORY INTERFACE:
VAR_INPUT
  ...

VAR_OUTPUT
  ...

ERROR CODES:
  16#0001 = ...
  16#0002 = ...

OUTPUT:
1. Complete SCL code
2. Instance usage example
3. Test scenarios
```

## 5. User Prompt Template (Filled Each Call)

```
TASK: Generate FB for the following <device>.

DEVICE INFO:
- Tag         : <tag>
- <feature 1> : <value>
- ...

OUTPUT: Complete SCL code following GLOBAL_FB_TEMPLATE.scl structure.
```

## 6. Expected FB Name

| Scenario | FB Name |
|----------|---------|
| <situation 1> | `FB_<DOMAIN>_<FUNC>` |
| <situation 2> | `FB_<DOMAIN>_<FUNC2>` |

## 7. Validation Checklist

AI output must contain (checklist):

- [ ] FB name correct format
- [ ] 4 regions present
- [ ] Type-specific requirements
- [ ] ...

## 8. Typical AI Errors

> Common errors AI makes in the field.

### 8.1 Syntax (Category A) — Auto-detectable
- <Error 1 and how to prevent>
- <Error 2>

### 8.2 Schema/Standard (Category B) — Validator catches
- <Naming violations>
- <Missing frontmatter>

### 8.3 Semantic (Category C) — Manual review required
- <Logic errors: "situations where AI gets confused">
- <Counter-measure: which rule in prompt prevents this>

### 8.4 Correction Request Template

If output has one of above:

> "Output has <category> error: <error summary>. <correct expected behavior>. Fix and provide only the corrected part, do not regenerate everything."

## 9. Related Files

- **Dependencies:** `GLOBAL_FB_TEMPLATE.scl`, `GLOBAL_NAMING_STANDARD.md`
- **Related prompts:** `<other prompts>`
- **Test prompt:** `PROMPT_TEST_GEN_UNIT.md`
- **Knowledge base:** `KB_PITFALLS_<domain>.md`

## 10. Feedback

If you find something missing in this prompt:

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "<this file path>" \
  --reason "..." \
  --suggestion "..."
```

---

*v<X.Y.Z> — <short changelog>*
```

---

## 3. Section Explanation

| Section | Required? | Why? |
|---------|-----------|------|
| **Frontmatter** | ✅ Required | Script/audit access |
| **1. When to Use** | ✅ Required | Prevents misuse |
| **2. Hardware Architecture** | ⚠️ If hardware exists | Creates mental model |
| **3. Metadata Input** | ✅ Required | Critical for Excel→JSON flow |
| **4. System Prompt** | ✅ Required | Fixed AI instruction |
| **5. User Prompt Template** | ✅ Required | Variable part for AI |
| **6. Expected FB Name** | ✅ Required | Naming consistency |
| **7. Validation Checklist** | ✅ Required | Human/script audit |
| **8. Typical AI Errors** | ✅ Required | Lessons learned, KB feed |
| **9. Related Files** | ✅ Required | Dependency tracking |
| **10. Feedback** | ✅ Required | Keep Factory alive |

---

## 4. Frontmatter Fields (Complete List)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Descriptive title |
| `version` | semver | ✅ | In 1.0.0 format |
| `last_validated` | YYYY-MM | ✅ | Last validation date |
| `applies_to` | list | ✅ | retrofit, greenfield, both |
| `device_type` | string | ✅ | DOL, VFD, VALVE_2WAY, PID etc. |
| `power_range` | string | ⚪ | Only for power-dependent devices |
| `prerequisite` | list | ✅ | Files to read before this one |
| `target_ai` | list | ✅ | Which AI models this was written for |
| `metadata_input` | string | ✅ | Which JSON schema to read |
| `output_artifacts` | list | ✅ | File types produced |
| `schema` | string | ✅ | Always `PROMPT_CODE_GEN` (for audit) |

---

## 4.5 Error Management Loop (v2.4)

> **Why:** When AI produces bad output, "Generate-Validate-Iterate" principle was unclear in operational flow. This closes that gap.

### 4.5.1 Error Categories

Generated code/MD can contain errors in three categories:

| Category | Sign | Example |
|----------|------|---------|
| **A — Syntax** | Detectable, auto-caught | Missing semicolon in SCL, JSON parse error, malformed YAML |
| **B — Schema/Standard** | Missing frontmatter, naming violation, MD schema mismatch | `PROMPT_VALF_*` (wrong) instead of `PROMPT_VALVE_*` |
| **C — Semantic** | Code runs but behaves wrong | Motor FB START condition reversed, alarm level wrong |

### 4.5.2 Feedback Flow (Operational)

When error found in prompt output **step by step** what to do:

```
[AI generated SCL/MD]
        ↓
[Auto check: script_md_schema_validator + syntax check]
        ├── Passed → Manual review (Category C)
        └── Failed → Loop below starts

LOOP:
1. Identify error category (A / B / C)
2. Create error record:
   - Temporary → KB_FEEDBACK_LOG.md (only affects this project)
   - Systematic → FACTORY_IDEAS_BACKLOG.md (prompt needs improvement)
3. Prepare correction request:
   "This prompt output has error: <category> — <description>.
    Expected: <correct output>. Fix."
4. Feed back to prompt → get new output
5. If not resolved in 3 tries → prompt itself needs work:
   - Open prompt improvement IDEA
   - Solve temporarily with manual intervention
6. After resolved:
   - If prompt changed → increment version (1.0 → 1.1)
   - Write to CHANGELOG: "PROMPT_X fixed (category B error)"
```

### 4.5.3 Required Error Management Section in Every Prompt

Every prompt file has **Section 8 (Typical AI Errors)** which now **must** include this structure:

```markdown
## 8. Typical AI Errors

### 8.1 Syntax (Category A) — Auto-detectable
- <Error 1: what, why, how detected>
- <Error 2: ...>

### 8.2 Schema/Standard (Category B) — Validator catches
- <Naming violation examples>
- <Frontmatter missing examples>

### 8.3 Semantic (Category C) — Manual review required
- <Logic error examples: "typical confusion situations">
- <Counter-measure: which rule in prompt prevents this>

### 8.4 Correction Request Template

If output contains any of above, feed back to AI in this format:

> "Output has <category> error: <error summary>. <correct expected behavior>. Fix and provide only the corrected part, do not regenerate full output."
```

### 4.5.4 Adapting Existing Prompts to This Section

Existing prompts written before v2.4 should reorganize Section 8 into 8.1/8.2/8.3/8.4 subsections. This is **not urgent** — will be standardized as each prompt is worked on (Sprint 2-4). New prompts already follow this structure.

Bulk adaptation via `script_bulk_md_edit.py` is possible.

---

*v1.1.0 — Error management feedback loop formalized.*
