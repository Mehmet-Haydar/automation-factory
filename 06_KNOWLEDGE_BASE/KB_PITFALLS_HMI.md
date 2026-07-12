---
title: KB - HMI Design Pitfalls
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-15
applies_to: [both]
prerequisite: [MDSCHEMA_RAWDATA_11_HMI.md]
status: ACTIVE
---

# KB_PITFALLS_HMI.md — HMI Design Pitfalls

> ISA-101 violations and typical HMI design errors. Impacts operator efficiency and field safety.

---

## metadata

```yaml
rag_category: hmi
rag_severity_default: medium
rag_verified_default: NOT_VERIFIED
rag_source_pattern: field_experience_anon
rag_entry_id_prefix: HMI
rag_entry_split_heading_level: 2
rag_entry_split_prefix: "Pitfall"
```

---

## Pitfall 1: Excessive Color Usage

**Symptom:** Screen has 8+ colors; critical alarms get "lost" in the clutter.

**Solution:** ISA-101 minimal palette: grayscale + 3-4 meaningful colors. Critical = red flashing only.

---

## Pitfall 2: Inconsistent Faceplates

**Symptom:** Each equipment type has different layout — operator must learn each one separately.

**Solution:** Standard faceplate template (motor, valve, sensor, PID). Same layout, different tags.

---

## Pitfall 3: Multi-Language Missing

**Symptom:** HMI for Germany delivery is English-only.

**Solution:** Multi-language from project start (minimum 2 languages). Tag database includes Label_EN + Label_DE/TR.

---

## Pitfall 4: No Access Levels

**Symptom:** Operator can change recipe parameters.

**Solution:** ISA-101 hierarchy (Operator/Supervisor/Engineer/Admin). Login system required.

---

## Pitfall 5: NumericInput Validation Missing

**Symptom:** Operator enters 99999, motor explodes.

**Solution:** All NumericInput fields require MinValue + MaxValue. Range check also on drive controller.

---

## Pitfall 6: Alarm Flood

**Symptom:** Single failure triggers 30 alarms.

**Solution:** Root cause analysis: one fault = one alarm. Suppression: parent active → children suppressed.

---

## Pitfall 7: Trend Data Local Only

**Symptom:** HMI crashes, 30 days of trend data lost.

**Solution:** Write trend data to historian/SCADA. HMI keeps only last 24 hours in ring buffer.

---

## Pitfall 8: Pop-up Stacking

**Symptom:** Alarm + recipe + diagnostic pop-ups stack on top of each other.

**Solution:** Max 1 modal pop-up. Non-modal notifications only (bottom-right corner).

---

## Pitfall 9: Touch Sensitivity Too Low

**Symptom:** Operator can't hit button while wearing gloves.

**Solution:** Industrial resistive touch or capacitive glove-friendly. Minimum button 30x30mm.

---

## Pitfall 10: Diagnostic Screen for Operators

**Symptom:** Operator accidentally changed parameter, production stopped.

**Solution:** Diagnostic = Engineer level only. Operators get read-only summary view.

---

## Pitfall 11: HMI Tag = PLC Tag Direct Mapping

**Symptom:** PLC tag changed, now HMI needs 100 manual updates.

**Solution:** Abstraction layer: HMI reads/writes only DB_HMI. Bridge FB handles PLC ↔ DB_HMI.

---

## Pitfall 12: Complex Recipe UI

**Symptom:** Operator spends 30 minutes changing 50 parameters.

**Solution:** Category-based UI (Temperatures, Speeds, Times). Add search/filter. Enable recipe template copy.

---

*v1.0.0 — 12 pitfalls. ISA-101 discipline = operator efficiency.*
