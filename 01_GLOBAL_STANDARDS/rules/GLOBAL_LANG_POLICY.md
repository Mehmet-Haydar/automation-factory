---
title: Global Language Policy — System and Output Languages
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-15
applies_to: [factory_internal, retrofit, greenfield]
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md]
related: [PROJECT_STATE_TEMPLATE.md, PIPELINE_CODE_REWRITE.md]
schema: DOMAIN_REFERENCE
status: FILLED
---

# GLOBAL_LANG_POLICY.md — Language Policy

> **This document formalizes a 3-layer language policy.** It defines which layer uses which language across all Factory and customer project outputs. Single global decision matrix instead of complexity.

---

## 1. Purpose and Scope

**This document:**
- ✅ Global language rule for system documentation, chat, code comments, tag names
- ✅ Per-project flexibility mechanism (via `PROJECT_STATE.json`)
- ✅ Multilingual glossary system (for code comment translation)

**This document is not:**
- ❌ Replacement for `GLOBAL_NAMING_STANDARD.md` (tag characters/regex are there)
- ❌ Translation tool; only **defines the rule**

---

## 2. Three-Layer Language Policy

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — SYSTEM FILES (Factory)                           │
│  Language: TURKISH                                          │
│  Scope: All Factory MDs, PROMPTS, MDSCHEMA files,          │
│         script docstrings, README, FACTORY_MAESTRO         │
│  Reason: Developer (you) reads Turkish.                     │
│  Note: v1.0 public GitHub release will be translated to EN │
│       (after Phase B, bulk translation with cheap model).   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — CHAT / USER INTERFACE                            │
│  Language: TURKISH                                          │
│  Scope: AI chat, USER_GUIDE_BIG_PICTURE,                   │
│         _BUILD_LOG, error messages for you                 │
│  Reason: Natural communication language.                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — PER-PROJECT CODE OUTPUT                          │
│  Language: PROJECT-SPECIFIC (TR / EN / DE / FR / ...)       │
│  Scope: AI-generated SCL code comments,                     │
│         Description columns, Mermaid labels,               │
│         HMI texts, alarm messages                          │
│  Mechanism: PROJECT_STATE.json: output_language field      │
│  Glossary: 01_GLOBAL_STANDARDS/lang_glossary/GLOSSARY_*.md │
│  Reason: Customer's local language.                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Fixed Rules (Language-Independent)

The following elements are **ALWAYS ENGLISH**, regardless of configuration:

| Element | Reason |
|---------|--------|
| **Tag names** (`MOT_CV01_001_DRIVE`) | Industry standard (IEC 81346 KKS-like), GLOBAL_NAMING_STANDARD |
| **FB/FC/DB/UDT names** | Same reason, plus AI/script reading |
| **Address format** (`%I1.2`, `%QW20`) | Vendor syntax |
| **Type names** (`BOOL`, `INT`, `REAL`) | IEC 61131-3 §6.3 |
| **Error code mnemonics** (`16#0001`) | Standard |
| **Parameter names** (`in_bEnable`, `out_wErrorCode`) | API consistency |
| **Region headers** (`(*== INTERFACE ==*)`) | GLOBAL_FB_TEMPLATE.scl |

---

## 4. Per-Project Configuration

Field added to `PROJECT_STATE.json` in each customer project:

```json
{
  "project_meta": {
    "name": "Beispielmaschine_Retrofit_2026",
    "customer": "CustomerName",
    "type": "retrofit"
  },
  "language": {
    "output_language": "tr",
    "fallback_language": "en",
    "glossary_overrides": {}
  }
}
```

**Supported `output_language` values (v3.0.0):**

| Code | Language | Glossary |
|------|----------|----------|
| `tr` | Turkish | GLOSSARY_TR.md |
| `en` | English (default) | GLOSSARY_EN.md |
| `de` | German | GLOSSARY_DE.md |

**To add new language:** Add `01_GLOBAL_STANDARDS/lang_glossary/GLOSSARY_<CODE>.md`, nothing else needed. AI reads this glossary automatically.

`fallback_language`: If AI is unsure about a term translation or it's not in glossary, it falls back to this language (default: `en`).

---

## 5. Which Areas the Output Language Affects

The `output_language` setting influences these output areas:

| Area | Example |
|------|---------|
| **SCL inline comments** | `// Motor start control` (en) vs `// Motor başlatma kontrolü` (tr) |
| **FB header block** | Description paragraph in header |
| **Description column** | In RD01..RD14 files |
| **Mermaid labels** | Node/edge text in flowcharts |
| **HMI screen texts** | TIA Texts entries |
| **Alarm messages** | RD08 alarm message strings |
| **Modernization report** | RD14 finding texts |
| **Validation/error messages** | Script outputs (TBD — future script update) |

---

## 6. Glossary System

### 6.1 Purpose

LLMs can do general translation but are **inconsistent** on industrial terms. Example: "watchdog" → once "bekçi köpeği", once "izleme zamanlayıcı". Glossary prevents this.

### 6.2 Structure

```
01_GLOBAL_STANDARDS/lang_glossary/
├── GLOSSARY_BASE.md       ← Term inventory (EN main list, descriptions)
├── GLOSSARY_EN.md         ← English canonical form (= BASE summary)
├── GLOSSARY_TR.md         ← Turkish equivalents
├── GLOSSARY_DE.md         ← German equivalents
└── (future: AR, FR, ES, IT, ...)
```

### 6.3 Glossary entry format

```yaml
- term: watchdog
  domain: timing
  description_en: A timer that triggers if a regular event fails to occur
  keep_english_in_code: true    # EN stays in tag/parameter names
  translations:
    tr: "bekçi köpeği zamanlayıcısı (watchdog)"
    de: "Watchdog-Zeitgeber"
    ar: "مؤقت المراقبة"

- term: feedback
  domain: io
  description_en: Signal returning from actuator confirming action
  keep_english_in_code: true
  translations:
    tr: "geri besleme"
    de: "Rückmeldung"
```

Terms with `keep_english_in_code: true` stay in code comments with original in parentheses (e.g., "geri besleme (feedback)"). Reason: field technician searching for the term always finds EN version.

### 6.4 Adding new language

1. Open `GLOSSARY_<CODE>.md` (template: `GLOSSARY_EN.md`)
2. Translate each term
3. Becomes available as `output_language` in PROJECT_STATE.json
4. Submit glossary PR (future community contribution)

---

## 7. AI Prompts' Language Directive

Each `04_AI_PROMPTS/code_gen/**` and `04_AI_PROMPTS/analyze/**` prompt gets a common section:

```
## OUTPUT LANGUAGE DIRECTIVE

Read from PROJECT_STATE.json:
  - output_language: <code>
  - fallback_language: <code>

In output:
  - Code comments (// lines, header block): <output_language>
  - Tag/parameter names: EN fixed (see Fixed Rules)
  - Description texts: <output_language>
  - Mermaid labels: <output_language>

Glossary reference: 01_GLOBAL_STANDARDS/lang_glossary/GLOSSARY_<output_language>.md
- Use terms from this glossary EXACTLY
- For term not in glossary, fall back to fallback_language
- If in neither, leave EN and add to UNKNOWN_TERMS list
```

This directive can be added to all prompts at once via `script_prompt_amend.py` (after Phase 4).

---

## 8. v1.0 Public Release Roadmap

This document was written **in Turkish** with v3.0.0. GitHub public release plan:

1. **v3.0.0 → v3.x.x (Turkish system):** All new development in Turkish
2. **v3.x.x → v4.0.0 (English translation):** All Phase A-D system files translated to English (cheap model + bulk amend script)
3. **v4.0.0 GitHub public:** System in EN, but each project still picks own `output_language` (TR/DE/AR whatever)

So **public version** lets every world user generate code in their own language; Factory docs will be English (for international contribution).

---

## 9. AI Usage Notes

- When generating glossary: AI must stick to **official industry terminology** (e.g., German VDI terminology)
- If new term is generated in prompt: first add to GLOSSARY_BASE, then reflect in translations
- When AI writes Description: always preserve original symbol (old tag) in `(orig: <old>)` format

---

## 10. Typical Mistakes

- ❌ Applying `output_language` to tag names → Fixed rule violation, validator rejects
- ❌ Selecting language without glossary → AI produces inconsistent translation
- ❌ Assuming "Turkish system" means EN code comments → LAYER 1 ≠ LAYER 3 confusion
- ❌ Publishing TR system docs in public release → international contribution impossible

---

## 11. Checklist

To verify this policy is implemented:

- [ ] `PROJECT_STATE.json` has `language` block
- [ ] `01_GLOBAL_STANDARDS/lang_glossary/` folder contains at least 3 languages (EN, TR, DE)
- [ ] All new prompts have "Output Language Directive" section
- [ ] Fixed Rules (Section 3) are never violated in any prompt
- [ ] script_consistency_check.py validates tag language (EN regex)

---

## 12. Related Files

- **Dependencies:** `GLOBAL_NAMING_STANDARD.md`, `GLOBAL_DATA_CLASSIFICATION.md`
- **Dependent prompts:** All `04_AI_PROMPTS/**/*.md`
- **Per-project structure:** `07_PROJECT_TEMPLATE/PROJECT_STATE.json`
- **Glossaries:** `01_GLOBAL_STANDARDS/lang_glossary/GLOSSARY_*.md`
- **Pipeline location:** `PIPELINE_CODE_REWRITE.md` Gate 1 (output_language selected during scope query)

---

## 13. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/rules/GLOBAL_LANG_POLICY.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.0.0 — Formalization of Multi-Language Code Output idea. Written together with v3.0.0. Will be translated to English for v4.0.0 (public release).*
