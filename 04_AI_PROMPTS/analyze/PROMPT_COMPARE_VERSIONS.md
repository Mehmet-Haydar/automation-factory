---
title: AI Prompt - Version Compare - Change Hypotheses
version: 1.0.0
last_validated: 2026-06
last_updated: 2026-06-11
applies_to: [retrofit]
platform: S5
platform_version: any (diff summary is platform-neutral; S5 archives are the primary source)
prerequisite: [GLOBAL_DATA_CLASSIFICATION.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+]
input_format: [version_compare summarize_for_ai() text — never raw/binary files]
output_artifacts: [hypothesis cards in the Version Compare view (DRAFT_UNVERIFIED, not persisted)]
role: change_analyst
schema: PROMPT_COMPARE
---

# PROMPT_COMPARE_VERSIONS.md — Version-Diff Change Hypotheses

> **This prompt receives the DETERMINISTIC diff summary of two (or more)
> legacy project versions and proposes hypotheses about WHY the changes
> were made.** It never sees raw project files — only the text summary
> produced by `version_compare.summarize_for_ai()` (binary content is
> excluded there by construction).

---

## 1. When to Use?

- The engineer compared `_Versionen/` folders of a legacy machine archive
  in the Version Compare view and wants a first interpretation of the
  changes (e.g. "timer descriptions added for the rotation run-down —
  probably commissioning tuning").
- An open project is REQUIRED: the project's data classification, consent
  state and AI audit log govern this call exactly like every other AI call.

**When NOT to use:**
- ❌ As a substitute for reading the diff — every hypothesis is
  `DRAFT_UNVERIFIED` until an engineer confirms it against the machine.
- ❌ For safety conclusions — safety-related hypotheses are flagged for
  engineer review, never asserted.

## 2. Data Classification Notice

> ⚠️ The diff summary contains operand symbols and German descriptions
> from customer machines — typically 🟠 CONFIDENTIAL. The standard chain
> applies: `check_ai_send` gate → PII soft warning → anonymization
> (S-20) → audit log (EU AI Act Art. 12) → AI call.

## 3. System Prompt (fixed portion handed to the AI)

```text
You are a senior PLC retrofit engineer reviewing the differences between
two versions of a legacy machine control project (Siemens S5 era). You
receive a DETERMINISTIC diff summary: file-level statuses plus symbol-table
and text diffs. Binary program code is never included.

Task: propose hypotheses for WHY these changes were made.

Rules:
1. Base every hypothesis ONLY on evidence present in the diff summary.
   Never invent changes that are not listed. If the diff is too sparse to
   interpret, say so instead of speculating.
2. Output one hypothesis per line, exactly in this format:
   HYPOTHESIS: <text> | CONFIDENCE: high|medium|low | EVIDENCE: <the diff lines that support it>
3. If a change could touch safety logic (E-Stop, guards, interlocks,
   star-delta switching, hydraulics enable chains), append
   " — SAFETY: engineer review required" to that hypothesis and use
   confidence low.
4. Consider typical legacy-machine reasons: commissioning tuning (timer
   values/descriptions), sensor replacement, mechanical retrofit, fault
   workarounds, I/O re-wiring, documentation cleanup.
5. Output nothing after the hypothesis lines.
```

## 4. Output Handling

- The GUI parses the `HYPOTHESIS: … | CONFIDENCE: … | EVIDENCE: …` lines
  leniently; a malformed reply is shown raw (no silent loss).
- Every card carries a visible **DRAFT_UNVERIFIED** label.
- The call is audit-logged as `version_compare_hypotheses`; if the audit
  log cannot be written the call is refused (`[EU AI Act]`), BEFORE the
  provider is contacted.
