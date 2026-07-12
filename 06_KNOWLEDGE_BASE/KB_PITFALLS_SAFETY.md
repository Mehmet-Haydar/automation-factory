---
title: KB - Safety System Pitfalls
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-15
applies_to: [both]
prerequisite: [MDSCHEMA_RAWDATA_05_SAFETY.md]
status: ACTIVE
safety_critical: TRUE
---

# KB_PITFALLS_SAFETY.md — Safety System Pitfalls

> WARNING: Safety-critical — each pitfall impacts life safety or legal compliance. All action recommendations must be reviewed by certified safety engineer.

---

## metadata

```yaml
rag_category: safety
rag_severity_default: "critical(safety)"
rag_verified_default: NOT_VERIFIED
rag_source_pattern: field_experience_anon
rag_entry_id_prefix: SAFETY
rag_entry_split_heading_level: 2
rag_entry_split_prefix: "Pitfall"
```

---

## Pitfall 1: E-Stop Logic on Standard PLC

**Symptom:** Old machine has no F-CPU; E-Stop controlled by standard Q output.

**Risk:** Cannot assign SIL/PLr, CE certification issue, legal liability.

**Solution:** Add F-CPU (S7-1500F or GuardLogix). Rewrite with F-FB (F_ESTOP1). Risk assessment + TÜV review required.

**Source:** 1990s machines; common anti-pattern.

---

## Pitfall 2: NC Contact Bypass Resistor

**Symptom:** Parallel resistor across E-Stop circuit (looks "OK" even when circuit cut).

**Root Cause:** Production crew added "temporary" bypass; never removed.

**Solution:** Field inspection with multimeter. If bypass found, machine stops immediately. Legal notification may be required.

---

## Pitfall 3: Light Curtain Muting Manipulation

**Symptom:** Muting needs 2 sensors; only 1 installed.

**Solution:** Standard cross-muting (2 muting sensors + time window). Use F_MUT_P (parallel) or F_MUT_S (sequential).

---

## Pitfall 4: Incorrect SIL Calculation

**Symptom:** Engineer says "SIL2 sufficient" but risk matrix shows SIL3 required.

**Root Cause:** F (Frequency) parameter underestimated.

**Solution:** Cross-check with IEC 62061 + ISO 13849-1. Independent expert review required.

---

## Pitfall 5: F-FB Manual Reset Bypassed

**Symptom:** F_ESTOP1 function block ACK pulse triggers automatically.

**Solution:** F_ESTOP1 reset ALWAYS manual (physical button). Automatic bit on ACK input FORBIDDEN.

---

## Pitfall 6: Response Time Exceeded

**Symptom:** E-Stop pressed; motor stops after 800ms but requirement is 250ms.

**Solution:** F-PLC scan time optimization + Drive STO directly from F-DO + reduce PROFIsafe cycle. Verify with oscilloscope.

---

## Pitfall 7: Proof Test Skipped

**Symptom:** Machine used 5 years; no proof test ever performed.

**Solution:** Proof Test Interval (typically 10-20 years) marked on machine label. Integrate into CMMS system.

---

## Pitfall 8: Common Cause Failure (CCF) Missed

**Symptom:** Two F-FBs read same sensor — common cause possible.

**Solution:** Cat 3+/SIL2+ requires independent second channel + diversity (different sensor type). IEC 62061 CCF score >= 65.

---

## Pitfall 9: Safety Door Bypass Key Uncontrolled

**Symptom:** Bypass key has no authorization control — anyone can open.

**Solution:** Engineer level only + physical key + SLS (Safely Limited Speed) enabled during bypass.

---

## Pitfall 10: PROFIsafe Address Collision

**Symptom:** Two F-CPUs use same PROFIsafe address.

**Solution:** Each F-CPU different F-DA range. Verify with TIA Safety Administration Editor.

---

## Pitfall 11: Safety Documentation Not Updated

**Symptom:** Field changes not reflected in safety documentation.

**Solution:** Engineering Change Order (ECO) system required. Major changes: mandatory TÜV notification.

---

## Pitfall 12: AI Predicting SIL

**Symptom:** AI extractor output shows "SIL_Level: SIL2".

**Solution:** AI prompt filling unauthorized field. script_consistency_check.py demands empty SIL_Level in DRAFT_UNVERIFIED status.

---

*v1.0.0 — 12 pitfalls. KB updated after each safety incident.*
