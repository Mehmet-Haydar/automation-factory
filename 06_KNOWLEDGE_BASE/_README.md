---
title: 06_KNOWLEDGE_BASE — Folder README
version: 1.0.0
last_updated: 2026-05-15
status: ACTIVE
last_validated: 2026-05
---

# `06_KNOWLEDGE_BASE/` — Pitfalls + Vendor Notes + Lessons Learned

> **This folder is the factory's "memory".** Field experience, vendor pitfalls, common AI errors, and customer surprises accumulate here.

---

## 1. Current Files

```
06_KNOWLEDGE_BASE/
├── _README.md  ← this file
│
├── KB_PITFALLS_COMMS.md         (Communications/fieldbus pitfalls)
├── KB_PITFALLS_HMI.md           (ISA-101 HMI design violations)
├── KB_PITFALLS_RETROFIT_IO.md   (IO extraction in legacy systems)
├── KB_PITFALLS_SAFETY.md        (Safety system common errors)
└── KB_VENDOR_QUIRKS.md          (Siemens/AB/Beckhoff special behaviors)
```

---

## 2. KB Writing Standard

Each KB file follows this structure:

```markdown
# KB_<CATEGORY>_<TOPIC>.md

## metadata
```yaml
rag_category: <comms|hmi|retrofit_io|safety|vendor_quirk>
rag_severity_default: <low|medium|high|critical(safety)>
rag_verified_default: <VERIFIED|NOT_VERIFIED>
rag_source_pattern: field_experience_anon
rag_entry_id_prefix: <PREFIX>
rag_entry_split_heading_level: <2|3>
rag_entry_split_prefix: "<Pitfall|>"
```

## Pitfall 1: <Short Name>
**Symptom:** <what was observed>
**Root Cause:** <why it happened>
**Solution:** <how it was resolved>
**Reference:** <standard or anonymized field source>

## Pitfall 2: ...
```

> **KB Entry Contract:** `_SCHEMA_KB_ENTRY.md` — full field definitions, entry-level metadata format (HTML comment block), severity guidance, exclusion rules, and a complete SEW MoviDrive example. Read before adding new entries.

---

## 3. Population Strategy (Future)

This folder grows with real project experience. v3.0.0-alpha has skeleton, v3.1.0+ sprints:

1. Post-sprint lessons-learned meeting
2. Experienced pitfalls added to appropriate KB file
3. Solutions committed alongside
4. Reflected in AI prompts too (`# 8. Typical AI Errors` section)

---

## 4. AI Integration

KB files are referenced in AI prompts as `prerequisite` or `related`:

```yaml
# Example from PROMPT_EXTRACT_IO_FROM_CODE.md frontmatter
prerequisite: [..., 06_KNOWLEDGE_BASE/KB_PITFALLS_RETROFIT_IO.md]
```

When running AI, these KBs are also read and AI tries to avoid the errors documented.

---

## 5. Anonymization Discipline

> ⚠️ Customer data is CONFIDENTIAL. When adding to KB:
> - NEVER write customer name (use category: "Automotive OEM 2026")
> - Anonymize specific tag/block names
> - Record only **concept + solution**

---

## 6. Plan (v3.1.0+)

| Sprint | KB Expansion |
|--------|--------------|
| v3.1.0 | KB_PITFALLS_RETROFIT_IO populated (real S5/S7 cases) |
| v3.1.0 | KB_PITFALLS_SAFETY populated (F-PLC migration cases) |
| v3.2.0 | KB_VENDOR_QUIRKS — TIA Portal V18 changes |
| v3.2.0 | KB_PITFALLS_AI_PROMPTS new file (AI error patterns) |
| v3.3.0 | KB_PITFALLS_COMMS populated (PROFINET IRT, EtherCAT DC) |

---

## 7. Related Folders

- `04_AI_PROMPTS/` — Each prompt's `§7 Typical AI Errors` section develops in parallel with KB
- `02_PROJECT_TYPES/` — Retrofit/Greenfield guides reference KB pitfalls
- `03_DOMAIN_TOOLS/` — Domain specs with cross-references

---

*As memory enriches, the factory grows smarter. Every pitfall is a teacher.*
