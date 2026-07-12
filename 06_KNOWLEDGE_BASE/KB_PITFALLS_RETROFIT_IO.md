---
title: KB - Retrofit IO Pitfalls
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-15
applies_to: [retrofit]
prerequisite: [RETROFIT_IO_EXTRACT.md]
status: ACTIVE
---

# KB_PITFALLS_RETROFIT_IO.md — Retrofit IO Pitfalls

> Common pitfalls when extracting IO from legacy PLC projects and their solutions. Compiled from field experience.

---

## metadata

```yaml
rag_category: retrofit_io
rag_severity_default: medium
rag_verified_default: NOT_VERIFIED
rag_source_pattern: field_experience_anon
rag_entry_id_prefix: RETRO
rag_entry_split_heading_level: 2
rag_entry_split_prefix: "Pitfall"
```

---

## Pitfall 1: Dual-Used Address in EPLAN

**Symptom:** EPLAN schematic shows %I 0.0 connected to two sensors.

**Root Cause:** Legacy designs used "hardware sharing" — limit switch + photocell in parallel for same contactor enable condition.

**Solution:**
- Field verification mandatory (multimeter test)
- Check symbol table: which sensor is actually defined at which address
- New IO list: assign each signal its own address (if hardware available)

**Source:** Automotive OEM 2024, retrofit project

---

## Pitfall 2: German Characters Corrupted in CSV Import

**Symptom:** TIA Portal Excel import: "Förderer" → "F?rderer"

**Root Cause:** CSV lacks UTF-8 BOM; Windows defaults to ANSI.

**Solution:**
- Save CSV with UTF-8 BOM encoding
- TIA Portal import dialog: manually select UTF-8 encoding
- Alternative: Use XLSX (UTF-8 native)

**Source:** German machine builder 2024

---

## Pitfall 3: "Reserve" Tagged Signals

**Symptom:** EPLAN has signals tagged `Reserve` or `frei` (empty); AI adds them to IO list.

**Root Cause:** Legacy design reserved spare module channels that are never used.

**Solution:**
- IO extractor prompt: filter out "Reserve" tags
- Or manually delete from AI output
- New projects: reserve 15-20% spare capacity (reusable)

**Source:** Appliance manufacturer 2024

---

## Pitfall 4: 24VDC vs 230VAC Confusion

**Symptom:** Same terminal block has DI 24VDC and DO 230VAC; wrong card selected.

**Root Cause:** Old machine uses single-row terminals, not separate module cards.

**Solution:**
- IO list requires Voltage column (24VDC / 230VAC / 110VAC distinction)
- Verify module selection matches voltage requirement
- F-modules already 24VDC standard

**Source:** Legacy 1990s machine retrofit

---

## Pitfall 5: Mixed German/Turkish/English Naming

**Symptom:** Symbol table has "Endschalter_oben" AND "limit_top" AND "üst_LS_001" for same signal.

**Root Cause:** Different engineers over years named in different languages.

**Solution:**
- IO extractor prompt: preserve OldTag exactly as-is
- New name per GLOBAL_NAMING_STANDARD (LS_LIM_001_TOP)
- Description field includes all originals: `(orig: Endschalter_oben | limit_top | üst_LS_001)`

**Source:** German customer retrofit in Turkey

---

## Pitfall 6: Inconsistent NC/NO Symbol

**Symptom:** E-Stop marked "NC" in schematic; code uses "AN" (AND NOT) — actually NO logic.

**Root Cause:** Schematic and code written at different times; one not updated.

**Solution:**
- AI extractor: conservative on NC/NO inference, mark "(uncertain)"
- Field verification mandatory (multimeter test)
- IO list documents NC/NO plus actual code behavior

**Source:** Safety-critical pitfall — can cause accident

---

## Pitfall 7: Analog Signal Scaling Missing

**Symptom:** AI outputs RD01 with RangeMin=0, RangeMax=27648 (raw value).

**Root Cause:** Legacy code uses raw values without SCALE_X function block.

**Solution:**
- Convert to engineering units: 4-20mA → 0-100°C
- RD01: RangeMin=0, RangeMax=100, EngUnit=°C
- Raw value scaling info in Notes

**Source:** Dairy factory retrofit

---

## Pitfall 8: Memory Marker Mistaken for IO

**Symptom:** AI extractor adds M10.0 to IO list as DI.

**Root Cause:** Symbol table shows M10.0 labeled "Limit_Switch_OK" → AI thinks it's physical signal.

**Solution:**
- Spec violation: M-area NOT in RD01 (belongs in RD02)
- IO extractor prompt: only accept %I/%Q/%PI/%PQ addresses
- Memory markers move to RD02 DataDict

---

## Pitfall 9: F-prefix Missing in HMI

**Symptom:** HMI tag list has "EStop_Status" but PLC has F_I_EStop_North.

**Root Cause:** Legacy WinCC didn't use F-prefix; tracked as normal tag.

**Solution:**
- HMI tag mapping: mark F_* signals
- New HMI: safety tags in separate section (HMI_SAFETY_*)
- Operator panel: safety status indicator in distinct color

---

## Pitfall 10: Legacy Addressing System (S5 vs S7)

**Symptom:** S5 project uses E 0.0; S7 uses I 0.0 — AI sometimes confuses them.

**Root Cause:** Siemens S5 → S7 address notation difference:
- S5: E 0.0 (Eingang), A 0.0 (Ausgang)
- S7: I 0.0 (Input), Q 0.0 (Output)

**Solution:**
- Platform parser prompt: correctly detect source platform
- Output uses target platform notation (modern: I/Q)
- Migration table shows old/new address pairs

---

## Pitfall 11: Bus Coupler Address Gaps

**Symptom:** PROFINET IO module addresses non-sequential: %I64-79, %I96-111 (gap in between).

**Root Cause:** TIA Portal Auto-Address places modules arbitrarily.

**Solution:**
- Extract address map **by word** (16 bytes per module, etc.)
- Document spare areas
- New projects: manual address assignment (sequential)

---

## Pitfall 12: Hardware Filter Migration

**Symptom:** Legacy project DI filter 1ms; new TIA defaults to 3ms — fast signals missed.

**Root Cause:** S7-1500 modules have longer default input filter time.

**Solution:**
- Module parameters: manually set input filter (0.1-3ms options)
- Fast signals (encoder, photocell): use shortest filter
- Test phase: measure pulse width with oscilloscope

---

*v1.0.0 — 12 pitfalls. KB updated after every new project.*
