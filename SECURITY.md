# 🔒 Security Policy

AUTOMATION_FACTORY is an AI-assisted industrial PLC automation framework. It handles
**AI API keys** and may process **confidential industrial / customer data**. We take
security seriously and appreciate responsible disclosure.

This is an actively developed, solo/community-maintained project — there is no
dedicated security team. Responses are best-effort (see timelines below).

---

## 📦 Supported versions

| Version | Supported |
|---------|-----------|
| 3.3.x (current) | ✅ Yes — receives security fixes |
| < 3.3 | ❌ No — please upgrade to the latest 3.3.x |

The factory follows SemVer; see [CHANGELOG.md](CHANGELOG.md) for release history.

---

## 🚨 Reporting a vulnerability

**Please do not open a public GitHub Issue for a security vulnerability.**

Use GitHub's private vulnerability reporting:

1. Go to the repository's
   [**Security → Advisories**](https://github.com/Mehmet-Haydar/automation-factory/security/advisories)
   tab.
2. Click **"Report a vulnerability"**.
3. Describe the issue, affected version, and steps to reproduce.

This keeps the report private between you and the maintainer
([@Mehmet-Haydar](https://github.com/Mehmet-Haydar)) until a fix is available.

If private advisories are unavailable to you for some reason, you may open a regular
issue **marked as a security concern** — but include **no sensitive detail** in it
(no proof-of-concept exploit, no leaked data), and the maintainer will move the
discussion to a private channel.

### What to include
- The affected component (e.g. `data_classification_guard`, `ai_client`, the web GUI).
- Version / commit.
- Reproduction steps and impact assessment.
- Any suggested remediation.

### ⚠️ Do not include sensitive data in your report
This factory's entire premise is keeping customer data out of the open. When
reporting, **never** attach real customer code, IO lists, API keys, or
CONFIDENTIAL/RESTRICTED material. Use synthetic data to demonstrate the issue, in
line with `01_GLOBAL_STANDARDS/rules/GLOBAL_DATA_CLASSIFICATION.md`.

---

## ⏱️ Response expectations

This is a best-effort process, not a contractual SLA:

- **Acknowledgement:** we aim to acknowledge a report within roughly **7 days**.
- **Assessment & fix:** triage and remediation depend on severity and maintainer
  availability. Critical issues are prioritized.
- **Disclosure:** we ask for **coordinated disclosure** — please give us reasonable
  time to ship a fix before any public discussion. Credit is gladly given to
  reporters who want it.

---

## 🛡️ Current security posture

The factory has the following security measures built in. These are described
accurately — they reduce risk, they are **not** absolute guarantees:

- **API keys in the OS keystore.** Keys are stored via `keyring` in the OS credential
  manager (Windows Credential Vault / macOS Keychain), never in plaintext JSON and
  never committed to git. Guarded by `tests/test_settings_keys.py`.
- **Data-classification guard.** `data_classification_guard` runs at AI-call time.
  CONFIDENTIAL data to a public AI provider requires explicit engineer consent
  (soft-block / `requires_consent`), and **RESTRICTED data is a hard block — consent
  has no effect**. Guarded by `tests/test_classification_guard.py`.
- **PII anonymization before cloud AI.** `anonymizer.py` strips known customer fields
  (name, project ID, engineer) and regex-matched PII (email, phone, address) from text
  before it is sent to a cloud AI provider. Uploaded files used by the Retrofit
  Pre-Analysis pipeline are deleted from the provider's servers immediately after
  each call.
- **EU AI Act audit logging.** `ai_decision_log.py` keeps an append-only, SHA256
  hash-chained JSONL audit log of AI actions (EU AI Act Article 12 intent). It records
  **hashes** of prompts/responses — not raw text — so no PII enters the log, and it is
  **fail-closed**: if the log cannot be written, the AI call must not proceed silently.
- **Safety output is DRAFT until verified.** All AI-generated SCL and documents carry
  `AUTO_VERIFIED_structural | PENDING_TIA_VERIFY` and remain a DRAFT until a qualified
  engineer compiles and tests them. AI output is **never authoritative** for
  Safety-Instrumented Systems — SIL/PLr assignment requires a certified safety
  engineer (see README "AI Responsibility Disclaimer").

### What this is *not*
These controls help engineers follow good data discipline; they do not replace it.
The user remains responsible for correctly classifying a project, for honoring
customer NDAs, and for choosing an appropriate AI provider tier (self-hosted /
enterprise for CONFIDENTIAL data). The software authors accept no liability for
production incidents or data handled outside these controls — see the
[LICENSE](LICENSE) and the README disclaimer.

---

## 🔑 Good practice for users
- Keep your AI API keys in the keystore via the Settings UI; never paste them into
  files or commits.
- Keep `customer_projects/` in a **separate** repo/folder from the factory
  (`GLOBAL_GIT_DISCIPLINE.md` §1).
- Review a project's data classification **before** opening it or running any AI step.

---

Thank you for helping keep AUTOMATION_FACTORY and its users safe. 🏭
