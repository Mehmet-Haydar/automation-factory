---
title: KB - Communications Pitfalls
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-15
applies_to: [both]
prerequisite: [MDSCHEMA_RAWDATA_09_COMMS.md]
status: ACTIVE
---

# KB_PITFALLS_COMMS.md — Communications Pitfalls

> Typical field issues with fieldbus, Ethernet, OPC UA integration.

---

## metadata

```yaml
rag_category: comms
rag_severity_default: medium
rag_verified_default: NOT_VERIFIED
rag_source_pattern: field_experience_anon
rag_entry_id_prefix: COMMS
rag_entry_split_heading_level: 2
rag_entry_split_prefix: "Pitfall"
```

---

## Pitfall 1: PROFINET Cycle Time Too Short

**Symptom:** PROFINET IO cycle 1ms; retransmission on switches, IO drops.

**Solution:** Standard switch minimum cycle 4ms. IRT requires TSN switch.

---

## Pitfall 2: PROFIBUS Slave Address Collision

**Symptom:** Two slaves at same address; one times out.

**Solution:** Physical labeling for each slave. HW Config matching verified. DIP switch photos in documentation.

---

## Pitfall 3: Modbus TCP No Watchdog

**Symptom:** Modbus device cable disconnected, PLC doesn't notice, runs with old value.

**Solution:** Monitor MB_CLIENT STATUS. Watchdog timer → alarm + safe state.

---

## Pitfall 4: Hardcoded IP Addresses

**Symptom:** SCL code has fixed IPs. Customer network changed, code must recompile.

**Solution:** IPs in DB parameters, configurable from HMI.

---

## Pitfall 5: Missing GSDML / EDS

**Symptom:** 3rd party device added, no GSDML — slave not recognized.

**Solution:** Request original GSDML from manufacturer. Prefer GSDML 2.0+.

---

## Pitfall 6: PROFINET IRT vs RT Confusion

**Symptom:** Motion drive wants IRT, network configured RT only.

**Solution:** TIA Portal Network View IRT Topology editor. Sync master + slaves topology.

---

## Pitfall 7: OPC UA Certificate Error

**Symptom:** SCADA can't connect to OPC UA: "Certificate validation failed."

**Solution:** Manually add self-signed certificate to SCADA trust store. Or use CA-signed.

---

## Pitfall 8: PROFINET MRP (Media Redundancy) Wrong Config

**Symptom:** Ring topology breaks one cable, all slaves drop.

**Solution:** One manager (CPU), others client. Ring fault detection time = 200ms.

---

## Pitfall 9: IO-Link Cycle Time

**Symptom:** Smart sensor cycle 80ms (default), control loop wants 10ms.

**Solution:** Read min cycle from IODD file. Master cycle = 2x sensor minimum.

---

## Pitfall 10: EtherCAT DC (Distributed Clocks) Missing

**Symptom:** Multi-axis motion not synchronized, jitter ±50μs.

**Solution:** TwinCAT NC Reference Clock + DC enabled on all slaves.

---

## Pitfall 11: S7_Comm vs PROFINET Confusion

**Symptom:** AI extractor marked PUT/GET as PROFINET.

**Solution:** S7_Comm is protocol, PROFINET is network. Separate in protocol enum.

---

## Pitfall 12: Watchdog Too Long

**Symptom:** Drive disconnect triggers alarm 30 seconds later — motor continued running.

**Solution:** Drive watchdog ≤ 100ms. Disconnect → STO. F-PLC + F-Drive integration mandatory.

---

*v1.0.0 — 12 pitfalls. Covers PROFINET/Modbus/OPC UA/EtherCAT/IO-Link.*
