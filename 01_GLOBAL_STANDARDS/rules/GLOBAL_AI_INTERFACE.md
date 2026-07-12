---
title: Global AI Interface Standard
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-16
applies_to: [factory_internal]
prerequisite: [GLOBAL_NAMING_STANDARD.md, GLOBAL_DATA_CLASSIFICATION.md]
status: ACTIVE
---

# GLOBAL_AI_INTERFACE.md — AI Provider Integration Standard

> Defines how the Factory communicates with AI services. Which model, which tier, which discipline.

---

## 1. AI Provider Hierarchy

| Provider | Model | Data Class | Usage |
|----------|-------|-----------|-------|
| **Anthropic Claude** | Sonnet 4+ / Opus 4+ | 🟠 CONFIDENTIAL → API Enterprise / AWS Bedrock; 🟢/🟡 → claude.ai | Primary AI provider |
| **OpenAI GPT** | GPT-4+ | 🟠 → Enterprise tier; 🟢/🟡 → ChatGPT Plus | Alternative |
| **Cursor** | Sonnet 4+ embed | 🟠 → Business tier; 🟢/🟡 → Pro | Within IDE |
| **Local LLM** | Llama 3.1, Mixtral | 🔴 RESTRICTED | Air-gapped system |

---

## 2. Model Selection Matrix

| Task | Recommended Model |
|------|------------------|
| Platform parsing (XML) | Sonnet 4+ |
| Topic extraction (RD01-12) | Sonnet 4+ |
| **Safety extraction (RD05)** | **Opus 4+ (critical reasoning)** |
| **Modernization (RD14)** | **Opus 4+** |
| Code generation (SCL) | Sonnet 4+ or Cursor |
| Review prompts | Sonnet 4+ |
| **Integrator review** | **Opus 4+** |
| Doc generation | Sonnet 4+ |
| Translation (v4.0.0) | Haiku 4+ (cheap) |

---

## 3. Frontmatter Discipline

Every AI prompt file must have a `target_ai:` field:

```yaml
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
```

This list:
- Which models the prompt was tested with
- Which models are recommended
- Which models are PROHIBITED (e.g., old versions)

---

## 4. Data Classification Discipline

```
🟢 PUBLIC      → Any AI
🟡 INTERNAL    → Cursor/Claude Team+ and above
🟠 CONFIDENTIAL → Self-hosted or Enterprise (Bedrock, Azure OpenAI Enterprise)
🔴 RESTRICTED  → Air-gapped local LLM
```

**Customer code (usually 🟠) PROHIBITED on ChatGPT.com / claude.ai web.**

---

## 5. Prompt Structure Standard

Each prompt has 12 sections:
1. Frontmatter
2. When to use?
3. Location in pipeline
4. System Prompt (fixed input for AI)
5. User Prompt template
6. Output validation
7. Typical AI errors (A/B/C categories)
8. Link to spec
9. Related files
10. Feedback
11. (optional) Industry standards
12. Version history

Detail: `04_AI_PROMPTS/_README.md`

---

## 6. Cost Discipline

| Task | Token estimate | Cost (Sonnet 4+) |
|------|----------------|-----------------|
| Platform parse (S7-1500) | 50K-200K input | $0.15-$0.60 |
| Topic extraction (RD) | 20K-50K | $0.06-$0.15 |
| Code gen (FB) | 10K-30K | $0.03-$0.10 |
| All 14 RD generation | ~500K total | $2-5 per project |

**Recommended:** Reserve budget before customer project starts (~€20-50 AI cost).

---

## 7. Rate Limiting

API limit tracking:
- Anthropic: 50 req/min (Tier 2), 1000 req/min (Tier 4)
- OpenAI: 500 req/min (Tier 2)
- For large project (14 RD parallel), Tier 3+ recommended

---

## 8. Audit Log

AI usage should be logged:
- Which prompt was called
- Which model
- Token count
- Output file
- Customer project ID

Location: `<project>/AI_DECISION_LOG.jsonl` (project root, JSON Lines —
hash-chained; see `05_SCRIPTS/ai_decision_log.py`)

---

## 9. Prohibitions

❌ Upload customer data to public AI
❌ Use AI output directly in production (human review required)
❌ Have AI estimate SIL (RD05)
❌ Give AI final decision authority (including review prompts)

---

## 10. Related Files

- **Data classification:** `GLOBAL_DATA_CLASSIFICATION.md`
- **Naming:** `GLOBAL_NAMING_STANDARD.md`
- **AI Prompts:** `04_AI_PROMPTS/_README.md`
- **Hierarchy:** `04_AI_PROMPTS/_PROMPT_HIERARCHY.md`

---

*v1.0.0 — AI is the Factory's "electricity". Disciplined use = sustainable cost.*
