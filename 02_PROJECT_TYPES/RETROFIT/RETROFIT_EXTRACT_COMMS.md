---
title: Retrofit Communications Extraction Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD09_Comms
prerequisite: [MDSCHEMA_RAWDATA_09_COMMS.md, RETROFIT_EXTRACT_DATADICT.md]
ai_prompt: 04_AI_PROMPTS/analyze/PROMPT_EXTRACT_COMMS_FROM_CODE.md
---

# RETROFIT_EXTRACT_COMMS.md — Communications Extraction Procedure

> **Goal:** extract field-device + SCADA + peer-PLC communication links from legacy PLC code.

---

## 1. Prerequisites

- [ ] HW config (network topology) at hand
- [ ] GSDML/EDS/ESI files (when available) — for slave detail
- [ ] IP plan table (customer network)
- [ ] _parsed.md Section 2 (Network) filled in

---

## 2. Detection Methods

### 2.1 Network Links

Find in the legacy code:
- **HW Config:** PROFINET IO-System, PROFIBUS-DP slave list
- **CP modules:** CP343, CP443, CM1542 (Ethernet/Serial)
- **SCL code:** TSEND_C, TRCV_C, MB_CLIENT, PUT, GET calls
- **Tag table:** symbols prefixed `"PN_*"`, `"DP_*"`, `"MB_*"`

### 2.2 Protocol Detection

```bash
# In AWL/STL
grep -E "(PUT|GET|TSEND|TRCV|MB_CLIENT|MB_SERVER)" *.awl

# In SCL
grep -E "(\.TCON|\.TDIS|MB_CLIENT|TUSEND|TURCV)" *.scl

# In TIA Portal XML
grep -E "(Profinet|Profibus|Modbus)" *.xml
```

---

## 3. Workflow

```
[1] _parsed.md + GSDML/EDS files ready
       ↓
[2] AI prompt: PROMPT_EXTRACT_COMMS_FROM_CODE.md
       ↓
[3] RD09_Comms_draft.md
       ↓
[4] Human review:
   ├─ Compare the slave inventory to the physical field
   ├─ IP addresses consistent with the network plan
   ├─ Cycle time + watchdog values reasonable
   └─ DataBlock_TX/RX references exist in RD02
       ↓
[5] RD09_Comms.xlsx
```

---

## 4. Human Review Checklist

#### A. Protocol Completeness
- [ ] All fieldbus links (PROFINET, PROFIBUS, EtherCAT, Modbus, IO-Link, AS-i)
- [ ] SCADA link (OPC UA, S7_Comm, etc.)
- [ ] PLC-PLC link (if any)
- [ ] Drive links (Profidrive, CIP Motion)

#### B. Addressing Accuracy
- [ ] Ethernet protocols → RemoteIP IPv4 populated (validator enforces)
- [ ] Fieldbus → RemoteAddress populated (PROFIBUS 1-126, AS-i 1-31)
- [ ] No IP conflict (each device unique)

#### C. Performance Parameters
- [ ] CycleTime_ms reasonable for the slave (PROFINET IO: 1-8ms; Modbus TCP: 100-1000ms)
- [ ] WatchdogTime_ms = 3-5 × CycleTime_ms
- [ ] TxByteCount/RxByteCount from GSDML (no guessing)

#### D. Cross-Reference
- [ ] DataBlock_TX/RX defined in RD02
- [ ] ErrorTag in RD01 or RD02

---

## 5. Multi-Network Scenarios

If there's more than one CP/network:
- Separate CommID groups (e.g., COM001-COM099 PROFINET, COM100-COM199 Modbus)
- Different IP segment per network

---

## 6. Common Pitfalls

- ❌ **Treating a PROFINET IO Station as a single link:** each station is its own CommID
- ❌ **Guessing TxByteCount/RxByteCount:** take them VERBATIM from GSDML/EDS
- ❌ **Calling PUT/GET PROFINET:** S7_Comm is a separate protocol
- ❌ **Defaulting watchdog values:** if not in the code, leave blank (#UNKNOWNS)
- ❌ **Writing the OPC UA endpoint URL as just an IP:** put the full URL in Notes

---

## 7. Gate 3 Checklist

- [ ] All links listed
- [ ] Protocol enum correct
- [ ] Ethernet → IP, Fieldbus → Address populated
- [ ] CycleTime + Watchdog reasonable
- [ ] Cross-references clean
- [ ] FORCED I/O or disabled connections noted in Notes

---

## 8. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_09_COMMS.md`
- **AI prompt:** `PROMPT_EXTRACT_COMMS_FROM_CODE.md`
- **Standards:** IEC 61784, IEC 61158-6-*, IEC 62541 (OPC UA)

---

*v1.1.0 — Full English body (2026-05-23). Communications is the machine's nervous system. A bad extraction = data loss and alarm flood in the field.*
