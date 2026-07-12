---
title: KB - Vendor-Specific Quirks
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-15
applies_to: [both]
status: ACTIVE
---

# KB_VENDOR_QUIRKS.md — Vendor-Specific Quirks

> Undocumented behaviors from Siemens, Allen-Bradley, Beckhoff, CODESYS, and other vendors.

---

## metadata

```yaml
rag_category: vendor_quirk
rag_severity_default: medium
rag_verified_default: NOT_VERIFIED
rag_source_pattern: field_experience_anon
rag_entry_id_prefix: VQ
rag_entry_split_heading_level: 3
rag_entry_split_prefix: ""
```

---

## SIEMENS

### S-1: TIA Portal Optimized DB Migration
After S7-300 Classic → TIA Portal migration, DBs arrive as "Standard" (non-optimized).
**Action:** Post-migration, manually make critical DBs "Optimized" (refactor + test).

### S-2: F-CPU Programming Without F-DB
Cannot write F-CPU code with normal DB — only F-DB supported.
**Action:** Safety logic + standard logic in SEPARATE POU. Data transport via safety telegram (F-DB).

### S-3: Multi-Instance FB STAT Omission
TIA Portal multi-instance FB: inner FB STAT fields hidden (nested DB).
**Action:** RD10 ParamList: manually verify multi-instance STAT.

### S-4: WinCC Unified Tag Database
WinCC Unified (TIA V18+) tag database incompatible with WinCC Classic.
**Action:** Conversion via migration script.

### S-5: SCL Source Import — (* *) Comment Closes at First "*)"
TIA's external-source parser ends a `(* *)` block comment at the FIRST `*)`.
Comment text like `(iDB_*)` closes the comment early; the remaining comment
text is parsed as CODE → misleading errors ("Type conflict: Object X cannot
be overwritten", "Syntax error: '.'"). Proven in the 2026-06-10 V19 Openness
import test (OB_Main).
**Action:** Generated SCL uses `//` line comments ONLY — never `(* *)`.
Enforced by `scl_validator.py` (BLOCK_COMMENT rules: warning on any `(*`,
error on a stray `*)` outside comments) and by codegen prompt STRICT RULE 10.

### S-6: Openness Import vs. Default "Main" [OB1]
Importing a program-cycle OB from an external source can conflict with the
default empty `Main` [OB1] ("cannot be overwritten") even when block names
differ. Generated blocks must be REPLACED, not overwritten: delete the
same-named program block before `GenerateBlocksFromSource` (the bridge does
this automatically). Never auto-delete the engineer's `Main` — surface a
message instead.

### S-7: SCL Source Compile — Statement-Free IF Body Is Refused
TIA's external-source compiler refuses an `IF ... THEN` body that contains
no statement — comments do NOT count: "Compound part of instruction
expected". Worse, the error is reported at the END of the enclosing
construct (e.g. near the `ELSE` of an outer CASE), far from the culprit —
in the 2026-06-10 V19 live test FB_Watchdog's comment-only placeholder IF
reported ~40 lines away and cost a 6-variant bisect to localize.
**Action:** Placeholder bodies get a bare `;` no-op statement. Enforced by
`scl_validator.py` (EMPTY_BODY: error on statement-free THEN, warning on
statement-free ELSE/loop bodies).

### S-8: Tag Table Import — Comment Culture Must Be a Project Language
`TagTables.Import` rejects the WHOLE XML when a comment `<Culture>` is not
one of the project's languages ("culture 'de-DE' does not exist within the
current project"). Proven in the 2026-06-10 V19 live test.
**Action:** The bridge reads `Project.LanguageSettings.EditingLanguage` and
rewrites the XML cultures before import; if still refused, comments are
dropped and the import retried (tags + addresses beat comments). Handled
automatically by `openness_core.import_tag_table`.

---

## ALLEN-BRADLEY

### AB-1: AOI Version Lock
AOI version change = all usage points become invalid.
**Action:** STAY on SAME VERSION branch OR update all usage points.

### AB-2: Continuous + Periodic Task Priority
Periodic task (10ms) running → Continuous task gets suspended.
**Action:** Time-critical logic on Periodic, bulk data on Continuous.

### AB-3: FactoryTalk View ME vs SE
ME (panel-based) and SE (server-based) incompatible.
**Action:** Choose correct variant at project start.

### AB-4: GuardLogix SafetyTask Time Slice
SafetyTask configured 20ms but actual response 35ms.
**Action:** Real response time measurement (oscilloscope required). Use datasheet "maximum guaranteed" value.

---

## BECKHOFF (TwinCAT)

### TC-1: TMC vs ST POU
PLCopen XML: TMC modules look like standard POU but contain C++ code underneath.
**Action:** AI extractor detects TMC → mark "vendor-specific" in Notes.

### TC-2: NCI vs NC PTP
NCI (CNC) and NC PTP (standalone motion) are SEPARATE systems.
**Action:** Motion extraction: clarify the distinction.

### TC-3: EtherCAT Hot-Connect
Hot-connect group with no slave plugged in → TwinCAT timeout.
**Action:** I/O configuration: verify hot-connect setting.

### TC-4: Beckhoff Persistent vs Retain
TwinCAT default: PERSISTENT; RD02 Retain field may mean "PERSISTENT".
**Action:** Add to Notes.

---

## CODESYS (Generic)

### CS-1: Library Version Conflict
Same project contains Standard 3.5.17.0 AND 3.5.18.0 — namespace collision.
**Action:** Library Manager enforces single version.

### CS-2: METHOD Implementation OOP
FB with METHOD + EXTENDS inheritance — runtime override possible.
**Action:** RD10 FBSpec: OOP detail to Notes. AI marks this pattern as "OOP Method".

---

## LENZE / SEW / SCHNEIDER

### LZ-1: Lenze 9300 → i550 Migration
PROFIBUS telegram parameter mapping differs.
**Action:** Obtain migration table from manufacturer.

### SW-1: SEW MoviAxis vs MoviDrive
Same brand: servo (MoviAxis) and VFD (MoviDrive) use different FB libraries.
**Action:** RD06 DriveModel: specify clearly.

### SC-1: Schneider EcoStruxure Library
PLCopen FBs renamed with vendor prefix (MC_PowerSE).
**Action:** Don't assume standard MC_*. Add vendor to Notes.

---

## GENERIC TIPS

- Read vendor reference manual + application notes (quick start is insufficient)
- Vendor forums + community resources: Siemens Industry Online Support, Rockwell Knowledgebase, Beckhoff InfoSys, CODESYS Forge, PLCTalk.net
- Test new vendor feature in factory simulation environment (not in live project)

---

*v1.0.0 — Vendor quirks grow after each new project. Experience layer = factory competitive advantage.*
