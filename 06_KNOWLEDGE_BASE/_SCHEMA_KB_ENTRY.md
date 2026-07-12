---
title: KB Entry Contract — Schema Definition
version: 1.0.0
created: 2026-06-14
status: ACTIVE
purpose: RAG ingestion contract for 06_KNOWLEDGE_BASE/
---

# _SCHEMA_KB_ENTRY.md — KB Entry Contract

> This schema defines: (a) the file-level `## metadata` block each KB file must carry for RAG ingestion, and (b) the canonical structure for new individual KB entries. Existing entry bodies are **not** modified — `ingest.py` uses the file-level block to derive per-entry defaults when no per-entry override is present.

---

## 1. File-Level Metadata Block

Every `KB_*.md` file carries exactly one `## metadata` section (placed after the H1 heading and intro paragraph, before the first entry). `ingest.py` reads this block to build per-entry records.

```yaml
rag_category: <comms|hmi|retrofit_io|safety|vendor_quirk>
rag_severity_default: <low|medium|high|critical(safety)>
rag_verified_default: <VERIFIED|NOT_VERIFIED>
rag_source_pattern: field_experience_anon   # never a customer name or PII
rag_entry_id_prefix: <COMMS|HMI|RETRO|SAFETY|VQ>
rag_entry_split_heading_level: <2|3>        # heading level that marks entry start
rag_entry_split_prefix: "<Pitfall|>"        # text prefix after heading marker; empty = any heading at that level
```

**Rules:**
- `rag_source_pattern` MUST be anonymized — no customer names, project codes, or PII.
- `rag_severity_default: critical(safety)` requires human engineer sign-off before the entry appears in any production output.
- `rag_verified_default: NOT_VERIFIED` entries are returned by `retrieve.py` only when `not_verified=True` is explicitly passed.

---

## 2. Entry-Level Format (new entries written after 2026-06-14)

New KB entries MUST follow this template. Per-entry metadata lives in an HTML comment block immediately below the heading — invisible in rendered Markdown, readable by `ingest.py`.

```markdown
## <PREFIX-NNN>: <Short Title>

<!-- metadata
entry_id: <PREFIX-NNN>
category: <comms|hmi|retrofit_io|safety|vendor_quirk>
severity: <low|medium|high|critical(safety)>
verified: <VERIFIED|NOT_VERIFIED>
source: field_experience_anon
vendor: <Siemens|SEW|Beckhoff|Allen-Bradley|>   # optional; omit if not vendor-specific
applies_to: <retrofit|greenfield|both>
standard_ref: <IEC 62061|ISO 13849-1|IEC 61131-3|>  # optional; required for critical(safety)
related_entries: []  # optional cross-references
-->

**Symptom:** <What was observed — objective, measurable>

**Root Cause:** <Why it happens — technical explanation>

**Solution:** <Step-by-step fix — actionable>

**Reference:** <Standard, datasheet, or anonymized field source>
```

---

## 3. Field Definitions

| Field | Type | Required | Allowed values |
|-------|------|----------|----------------|
| `entry_id` | string | YES | `PREFIX-NNN` e.g. `COMMS-001`, `SAFETY-012`, `VQ-SW-1` |
| `category` | enum | YES | `comms` · `hmi` · `retrofit_io` · `safety` · `vendor_quirk` |
| `severity` | enum | YES | `low` · `medium` · `high` · `critical(safety)` |
| `verified` | enum | YES | `VERIFIED` · `NOT_VERIFIED` |
| `source` | string | YES | Anonymized — no customer name, project code, or PII |
| `vendor` | string | NO | Specific vendor when quirk is vendor-specific |
| `applies_to` | enum | NO | `retrofit` · `greenfield` · `both` |
| `standard_ref` | string | NO | Normative reference; **required** for `critical(safety)` |
| `related_entries` | list | NO | Cross-references to other `entry_id` values |

### Severity Guidance

| Level | Meaning | Retrieve default |
|-------|---------|-----------------|
| `low` | Minor inconvenience; workaround trivial | Returned |
| `medium` | Significant rework risk; field validation recommended | Returned |
| `high` | Production loss or compliance gap probable | Returned |
| `critical(safety)` | Safety function failure possible; **engineer sign-off mandatory** | Returned with `rag_warning` flag |

### Body Sections

| Section | Required | Notes |
|---------|----------|-------|
| `**Symptom:**` | YES | Observable effect; not the internal cause |
| `**Root Cause:**` | NO | Recommended for `severity: high` and above |
| `**Solution:**` | YES | Must be actionable; no vague recommendations |
| `**Reference:**` | NO | Required for `critical(safety)` entries |

---

## 4. Exclusion Rules

The following MUST NOT appear in any KB entry:

- Customer company names, project codes, order numbers
- Machine serial numbers or installation-site addresses
- Engineer names, email addresses, phone numbers
- Un-anonymized field test data (keep concept + solution only)
- Internal commercial terms or pricing
- IP addresses or network credentials

---

## 5. Full Example — SEW MoviDrive Quirk

A new entry that follows this contract in full (extends the existing `SW-1` skeleton in `KB_VENDOR_QUIRKS.md`):

```markdown
## VQ-SW-1: SEW MoviAxis vs MoviDrive — Different FB Libraries

<!-- metadata
entry_id: VQ-SW-1
category: vendor_quirk
severity: medium
verified: VERIFIED
source: field_experience_anon_2026-05
vendor: SEW
applies_to: both
-->

**Symptom:** Both MoviAxis (servo) and MoviDrive (VFD) appear in the same project; engineer applies the MoviDrive FB library to MoviAxis units — compile error or unexpected runtime behaviour.

**Root Cause:** Despite sharing the SEW brand, MoviAxis and MoviDrive use incompatible FC/FB sets. MoviAxis requires the `SEW_Servo_MC` library; MoviDrive uses `SEW_Drive_FC`. Library Manager shows separate namespaces with no cross-compatibility.

**Solution:** Identify drive type at project start (RD06 `DriveModel` field). Install the correct library for each axis group. If both types are present in one project, install both libraries and keep FB calls strictly separated. Verify in TIA Portal Library Manager before FAT.

**Reference:** SEW Application Notes — MoviDrive B Application Manual; SEW MoviAxis Commissioning Guide; field_experience_anon_2026-05
```

---

## 6. Ingest Notes (for `05_SCRIPTS/rag/ingest.py`)

- Read the `## metadata` YAML block from each file for defaults.
- Split file into chunks at heading level `rag_entry_split_heading_level` where the heading text starts with `rag_entry_split_prefix` (empty prefix = any heading at that level).
- Per-entry override: check for `<!-- metadata ... -->` HTML comment immediately after the heading; fields present there override file-level defaults.
- `entry_id` for legacy entries (no per-entry block): `{rag_entry_id_prefix}-{zero_padded_sequential}` e.g. `COMMS-001`.
- `chunk_text`: heading line + all content until the next entry boundary (exclusive).
- Index key: `entry_id` — must be unique across the entire repository.
- `retrieve.py` default: return only `verified: VERIFIED` chunks. Pass `not_verified=True` to include `NOT_VERIFIED`. Always attach `severity` and `entry_id` to returned records so callers can apply safety banner logic.
