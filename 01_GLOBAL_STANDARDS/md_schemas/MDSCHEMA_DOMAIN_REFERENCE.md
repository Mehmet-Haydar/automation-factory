---
title: MD Schema - Domain Reference Documents
version: 1.0.0
last_validated: 2026-05
applies_to: [factory_internal]
status: FILLED
schema_for: 03_DOMAIN_TOOLS/*.md, 02_PROJECT_TYPES/**/*.md
---

# MDSCHEMA_DOMAIN_REFERENCE.md

> **This template defines the structure for domain reference files (HMI, Safety, Comms, Drives, Testing) and project type files (Retrofit/Greenfield maestro/hardware/IO).**

---

## 1. Why Does This Template Exist?

Domain files are **not prompts**, but engineering references. Structure differs because:
- Aimed at engineers (and context for AI), not AI input
- Procedure-heavy (step-by-step workflows)
- Contains decision tables, comparisons, lessons learned

Yet **consistency** requires a common structure.

---

## 2. Required Structure

```markdown
---
title: <Domain Name>
version: <SemVer>
last_validated: YYYY-MM
applies_to: [retrofit|greenfield|both]
prerequisite: [...]
related_prompts: [PROMPT_*.md]
schema: DOMAIN_REFERENCE
---

# <FILE_NAME>.md

> **<One-liner: What does this file cover?>**

---

## 1. Purpose and Scope

<What it covers, what it doesn't>

**This file covers:**
- ✅ <in-scope 1>
- ✅ <in-scope 2>

**Out of scope:**
- ❌ <explained elsewhere 1>

## 2. Prerequisites

Before starting this file, these must be done:
- [ ] <prerequisite 1> (see `<file>`)
- [ ] <prerequisite 2>

## 3. <Main Content Section 1>

<This section varies by domain. Examples:
- HMI: "Page Hierarchy"
- Safety: "Risk Assessment"
- Comms: "Protocol Selection"
- Testing: "Test Strategy"
- Retrofit: "Phase Flow">

## 4. Decision Matrices / Comparison Tables

<Domain-specific decision tables:>

| Criteria | Option A | Option B | Recommendation |
|----------|----------|----------|-----------------|
| ... | ... | ... | ... |

## 5. Standards / Conventions

<Accepted standards for this domain:>
- <Standard 1 — e.g., TS EN ISO 13849>
- <Standard 2>

## 6. AI Usage Notes

When using AI in this domain:
- 🟠 Is CONFIDENTIAL data involved? See `GLOBAL_DATA_CLASSIFICATION.md`
- Which prompts are linked to this domain? `<list>`
- Typical prompt command: <example "AI, do this">

## 7. Typical Errors (Lessons Learned)

> Common errors encountered in the field.

- ❌ <error 1>
- ❌ <error 2>

This list is kept in sync with `06_KNOWLEDGE_BASE/KB_PITFALLS_<domain>.md`.

## 8. Checklist

When work on this domain is complete:

- [ ] <item 1>
- [ ] <item 2>
- [ ] ...

## 9. Related Files

- **Dependencies:** `<files>`
- **Dependent prompts:** `PROMPT_*.md`
- **Knowledge base:** `KB_*.md`
- **Test reference:** `DOMAIN_TESTING_*.md`

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "<this file>" \
  --reason "..." \
  --suggestion "..."
```

---

*v<X.Y.Z> — <short description>*
```

---

## 3. Section-by-Section Explanation

| Section | Required? | Why? |
|---------|-----------|------|
| **Frontmatter** | ✅ Required | Script/audit access |
| **1. Purpose and Scope** | ✅ Required | Prevents misreading |
| **2. Prerequisites** | ✅ Required | Dependency chain |
| **3. Main Content** | ✅ Required | Core work — domain-specific |
| **4. Decision Matrices** | ⚠️ When decisions needed | Engineer will choose |
| **5. Standards** | ⚠️ If national/international standard exists | Certification |
| **6. AI Usage Notes** | ✅ Required | Prompt linkage |
| **7. Typical Errors** | ✅ Required | Lessons learned |
| **8. Checklist** | ✅ Required | Is work done? |
| **9. Related Files** | ✅ Required | Cross-reference |
| **10. Feedback** | ✅ Required | Keep Factory alive |

---

## 4. Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Domain heading |
| `version` | semver | ✅ | 1.0.0 |
| `last_validated` | YYYY-MM | ✅ | Last validation |
| `applies_to` | list | ✅ | retrofit, greenfield, both, factory_internal |
| `prerequisite` | list | ✅ | Prior files |
| `related_prompts` | list | ⚪ | Linked code-gen prompts |
| `schema` | string | ✅ | Always `DOMAIN_REFERENCE` |

---

## 5. Schema Validator

```bash
python 05_SCRIPTS/dev/script_md_schema_validator.py \
  --schema DOMAIN_REFERENCE \
  --target "03_DOMAIN_TOOLS/*.md"
```

---

*This template is live. When template changes, existing MDs are adapted via bulk edit script.*
