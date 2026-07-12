---
title: Global Data Classification
version: 1.0.0
last_validated: 2026-05
applies_to: [retrofit, greenfield, factory_internal]
---

# GLOBAL_DATA_CLASSIFICATION.md

> **Purpose:** Regulates sharing of customer project data with AI tools (Claude, ChatGPT, Cursor, Copilot). Prevents NDA violations.

---

## 1. Classification Levels

| Level | Definition | AI Sharing |
|-------|-----------|-----------|
| **🟢 PUBLIC** | General engineering knowledge, Factory standards, open-source examples | ✅ Free to share |
| **🟡 INTERNAL** | Company-internal templates, code snippets without customer names | ⚠️ Anonymize |
| **🟠 CONFIDENTIAL** | Customer code, IO lists, machine design details | ⚠️ Self-hosted/enterprise AI only |
| **🔴 RESTRICTED** | Recipes, production parameters, safety passwords, license keys | ❌ Never share with AI |

---

## 2. Category-Based Rules

### 🟢 PUBLIC (Free to share)

- All content in Factory's `01_GLOBAL_STANDARDS/`, `03_DOMAIN_TOOLS/`, `04_AI_PROMPTS/`
- General TIA Portal structures (example FB skeleton, naming)
- Open-source Siemens example code

### 🟡 INTERNAL (Anonymization required)

Before sharing, apply these transformations:
- Customer name → `<CUSTOMER_X>`
- Machine name → `<MACHINE_TYPE>`
- Project code → `<PROJECT_ID>`
- Operator name/contact → remove
- IP addresses → generalize to `192.168.X.X` format

**Example transformation:**

❌ Before: `// Beispielmaschine Müller GmbH - Projekt 2024-117 - IP 10.45.12.3`
✅ After: `// <MACHINE_TYPE> <CUSTOMER_X> - <PROJECT_ID> - IP 192.168.X.X`

### 🟠 CONFIDENTIAL (Self-hosted AI or prohibited)

Can only be shared with these AI systems:
- Self-hosted LLM (Ollama, LM Studio)
- Enterprise AI (Anthropic Enterprise, ChatGPT Enterprise) — **if customer NDA allows**
- Cursor "Privacy Mode" + Enterprise

Absolutely **never** share with public AI (free/pro tier).

### 🔴 RESTRICTED (Never share with any AI)

- Recipe parameters (trade secret)
- Safety passwords, F-PLC credentials
- License files (`.lic`, `.tlf`)
- VPN configurations
- Customer network topology (with real IPs)

---

## 3. Practical Rules

### 3.1 Cursor Usage

**Cursor Settings → Privacy Mode:**
- Always ON when customer project is open.
- Can be OFF when Factory repo is open (PUBLIC content).

### 3.2 Code Comments

When writing PLC code comments:
```pascal
// CONFIDENTIAL - Customer X - Recipe parameters in DB_RECIPE
```
This comment should not be copied to AI.

### 3.3 Screenshot Sharing

When sharing screenshots with AI:
- Mask customer logos on HMI screens
- Mask customer project names in TIA Portal project tree
- Mask real IPs in network configuration

---

## 4. Violation Procedure

If CONFIDENTIAL/RESTRICTED data is accidentally sent to AI:
1. Immediately delete the AI chat (deletion guarantee not guaranteed, but important).
2. Notify customer contact within 24 hours (NDA requirement).
3. Log incident in `06_KNOWLEDGE_BASE/KB_FEEDBACK_LOG.md`.
4. Update this standard to prevent recurrence.

---

## 5. Decision Tree

```
Should I share this data with AI?
│
├─ Factory PUBLIC content? → ✅ Share
│
├─ Customer data?
│  ├─ Can be anonymized? → 🟡 Anonymize, then share
│  ├─ Self-hosted/Enterprise AI? → 🟠 Share (check NDA)
│  └─ Public AI? → ❌ Don't share
│
└─ Recipe/password/license? → 🔴 Never share
```

---

*Review this standard with each new project customer. If NDA has special clauses, add project-specific supplement (`PROJECT_DATA_CLASSIFICATION.md`).*
