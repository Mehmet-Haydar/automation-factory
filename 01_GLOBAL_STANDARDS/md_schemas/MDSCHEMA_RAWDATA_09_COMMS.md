---
title: Raw Data Schema #09 — Communications
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit, greenfield, both]
prerequisite: [GLOBAL_NAMING_STANDARD.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_02_DATADICT.md]
related: [PIPELINE_CODE_REWRITE.md, MDSCHEMA_RAWDATA_01_IO.md, MDSCHEMA_RAWDATA_02_DATADICT.md, PROMPT_EXTRACT_COMMS_FROM_CODE.md]
schema: RAWDATA
rd_number: 09
deliverable: [RD09_Comms.xlsx, RD09_Comms.md, rd09_comms.schema.json]
mandatory_for: [retrofit, greenfield]
references_standards: [IEC 61784, IEC 61158-6-10, IEC 61784-2, Modbus RTU/TCP spec]
---

# MDSCHEMA_RAWDATA_09_COMMS.md — Communications Specification

> **This file defines how the project's "09 — Communications" raw data file should be structured.** Documents every communication link the PLC has with other devices (drives, sensors, SCADA, ERP, other PLCs) — protocols, data mapping and watchdogs.

---

## 1. What Does This File Define?

This is **a "schema"** — the actual communications configuration (`RD09_Comms.xlsx` / `.md`) must conform to this spec.

- ✅ Protocol and device info per communication channel
- ✅ Data size (bytes sent/received)
- ✅ Cycle time and watchdog parameters
- ✅ Related DB references (TX/RX data blocks)
- ✅ Error-detection mechanism

**This file is NOT:**
- ❌ Network topology diagram (that's a network-design document — Visio/Draw.io)
- ❌ PROFINET device configuration (that's TIA Portal Hardware Configuration)
- ❌ OPC UA node list (that's SCADA configuration — OPC UA server config)

---

## 2. When Is It Generated, Where Does It Come From?

| Type | Source | Producer | Validator |
|---|---|---|---|
| **Retrofit** | Legacy PLC network configuration + HW config + GSD/GSDML files | AI (`PROMPT_EXTRACT_COMMS_FROM_CODE.md`) — uses _parsed.md Section 2 (Network) | `script_consistency_check.py` |
| **Greenfield** | Network design document + device lists + SCADA requirements | Human (automation engineer + IT/OT owner) | `script_consistency_check.py` |

Pipeline placement: **Gate 2** → **Gate 3** → **Gate 4** (GREEN).

---

## 3. Excel Column Definition (Required)

`RD09_Comms.xlsx` must contain the following columns **in this order**:

| # | Column | Type | Required | Enum / Regex | Description |
|---|---|---|---|---|---|
| 1 | `CommID` | string | ✅ | `^COM\d{3}$` | Link identifier (e.g., `COM001`) |
| 2 | `Protocol` | enum | ✅ | `PROFINET`, `PROFIBUS_DP`, `Modbus_RTU`, `Modbus_TCP`, `EtherNet_IP`, `EtherCAT`, `OPC_UA`, `S7_Comm`, `IO_Link`, `AS_Interface`, `Other` | Communication protocol |
| 3 | `LocalDevice` | string | ✅ | (free) | Local device (typically the PLC CPU name — TIA Portal device name) |
| 4 | `RemoteDevice` | string | ✅ | (free) | Remote device name (drive, sensor, SCADA, another PLC) |
| 5 | `RemoteIP` | string | ⚪ | IPv4 regex | Remote device IP address (for Ethernet-based protocols) |
| 6 | `RemoteAddress` | string | ⚪ | (free) | Remote device address (PROFIBUS: 1-126; Modbus RTU: 1-247; IO-Link port) |
| 7 | `Direction` | enum | ✅ | `TX`, `RX`, `Bidirectional` | Data direction (from PLC perspective) |
| 8 | `TxByteCount` | integer | ⚪ | ≥0 | Bytes sent by PLC |
| 9 | `RxByteCount` | integer | ⚪ | ≥0 | Bytes received by PLC |
| 10 | `CycleTime_ms` | integer | ⚪ | >0 | Communication cycle (ms). PROFINET typical: 1-8ms |
| 11 | `WatchdogTime_ms` | integer | ⚪ | >0 | Link-loss detection time (ms) |
| 12 | `DataBlock_TX` | string | ⚪ | (free) | DB holding outgoing data (cross-reference to RD02 ParentBlock) |
| 13 | `DataBlock_RX` | string | ⚪ | (free) | DB holding incoming data (cross-reference to RD02 ParentBlock) |
| 14 | `ErrorTag` | string | ⚪ | (free) | Communication-error signal (cross-reference to RD01 or RD02) |
| 15 | `Notes` | string | ⚪ | (free) | Special configuration note, GSD/GSDML reference |
| 16 | `Status` | enum | ✅ | `Active`, `Inactive`, `Spare` | Renamed to English (2026-06-10); legacy Turkish literals (`Aktif`/`Pasif`/`Taslak`/`Yedek`) in existing projects remain readable by the tooling |

### 3.1 Column Descriptions (Detail)

**Protocol (2):**
- `PROFINET` → Siemens RT/IRT (IEC 61158-6-10). Most common Siemens fieldbus
- `PROFIBUS_DP` → legacy Siemens communication (RS-485 based)
- `Modbus_RTU` → serial (RS-232/RS-485), Modbus protocol
- `Modbus_TCP` → Modbus over Ethernet (IP-based)
- `EtherNet_IP` → Allen-Bradley/Rockwell protocol (IEC 61784-2)
- `EtherCAT` → Beckhoff real-time Ethernet (IEC 61158-12)
- `OPC_UA` → OPC Unified Architecture (IEC 62541) — SCADA/MES integration
- `S7_Comm` → Siemens S7 protocol (ISO-on-TCP, between S7-300/400/1500)
- `IO_Link` → smart sensor/actuator protocol (IEC 61131-9)
- `AS_Interface` → actuator-sensor interface (IEC 62026-2)

**RemoteIP (5):** IPv4 format: `192.168.1.10`. Blank for PROFIBUS/Modbus RTU (no IP).

**TxByteCount / RxByteCount (8-9):** I/O module size for PROFINET. Register count × 2 for Modbus. These values directly affect DB size and PLC memory planning.

**WatchdogTime_ms (11):** How long the PLC waits after a link drop before raising an error. Too short: false alarms on transient network glitches. Too long: real faults detected late.

---

## 4. JSON Schema (Validation)

`08_METADATA_INPUT/schema/rd09_comms.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RD09 — Communications",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["CommID","Protocol","LocalDevice","RemoteDevice","Direction","Status"],
    "additionalProperties": false,
    "properties": {
      "CommID":           { "type": "string", "pattern": "^COM\\d{3}$" },
      "Protocol":         { "enum": ["PROFINET","PROFIBUS_DP","Modbus_RTU","Modbus_TCP","EtherNet_IP","EtherCAT","OPC_UA","S7_Comm","IO_Link","AS_Interface","Other"] },
      "LocalDevice":      { "type": "string", "minLength": 1 },
      "RemoteDevice":     { "type": "string", "minLength": 1 },
      "RemoteIP":         { "type": "string", "pattern": "^(\\d{1,3}\\.){3}\\d{1,3}$" },
      "RemoteAddress":    { "type": "string" },
      "Direction":        { "enum": ["TX","RX","Bidirectional"] },
      "TxByteCount":      { "type": "integer", "minimum": 0 },
      "RxByteCount":      { "type": "integer", "minimum": 0 },
      "CycleTime_ms":     { "type": "integer", "minimum": 1 },
      "WatchdogTime_ms":  { "type": "integer", "minimum": 1 },
      "DataBlock_TX":     { "type": "string" },
      "DataBlock_RX":     { "type": "string" },
      "ErrorTag":         { "type": "string" },
      "Notes":            { "type": "string" },
      "Status":           { "enum": ["Active","Inactive","Spare"] }
    },
    "allOf": [
      {
        "if":   { "properties": { "Protocol": { "enum": ["PROFINET","Modbus_TCP","EtherNet_IP","OPC_UA","S7_Comm","EtherCAT"] } } },
        "then": { "required": ["RemoteIP"] }
      }
    ]
  }
}
```

**Conditional rule:** for Ethernet-based protocols (PROFINET, Modbus_TCP, etc.) `RemoteIP` is mandatory.

---

## 5. MD Output Format

`RD09_Comms.md` produced at Gate 4:

````markdown
---
title: RD09 — Communications
project: <project_name>
generated: YYYY-MM-DD
source: RD09_Comms.xlsx
filter: Status=Active
total_connections: <N>
schema: RD09
---

# RD09 — Communications

## Connection Summary

| CommID | Protocol | RemoteDevice | RemoteIP | Direction | CycleTime_ms |
|--------|----------|--------------|----------|-----------|--------------|
| COM001 | PROFINET | G120_Drive_CV01 | 192.168.1.20 | Bidirectional | 4 |
| COM002 | Modbus_TCP | SCADA_Server | 192.168.2.100 | RX | 100 |
| ... | ... | ... | ... | ... | ... |
````

---

## 6. AI Filling Instructions (Retrofit)

```
INPUT: _parsed.md Section 2 (Network — IP addresses, PROFINET devices, subnet)
TASK:
  1. Every PROFINET slave → one COM row
  2. Every PROFIBUS slave → one COM row (RemoteAddress = DP address)
  3. Every S7 PUT/GET block → one COM row (Protocol = S7_Comm)
  4. SCADA/HMI link → OPC_UA or S7_Comm row
  5. RemoteIP: from HW config (GSDML parameter)
  6. TxByteCount/RxByteCount: from the I/O module or PLC data block size
  7. WatchdogTime_ms: from the HW config PROFINET watchdog parameter
  8. DataBlock_TX/RX: from PUT/GET block parameters in PLC code
  9. ErrorTag: PROFINET ioCom error bit or Modbus error register
```

---

## 7. AI Filling Instructions (Greenfield)

```
INPUT: _input/brief.md + network design + device lists
TASK:
  1. One COM row per fieldbus device
  2. RemoteIP: from the IP plan (192.168.x.y)
  3. CycleTime_ms: propose typical PROFINET 4ms, Modbus TCP 100ms
  4. WatchdogTime_ms: propose CycleTime_ms × 3-5 (typical 20-50ms PROFINET)
  5. DataBlock_TX/RX: plan DB names (DB_<Device>_Comms)
  6. SCADA link: propose OPC_UA (industry standard, security features)
  7. ErrorTag: plan an error signal per link (RD01 DI or RD02 BOOL)
```

---

## 8. Industry Standards Reference

| Standard | How Applied in This Spec |
|---|---|
| **IEC 61784** | Fieldbus profile framework — Protocol enum |
| **IEC 61158-6-10** | PROFINET protocol spec — PROFINET, CycleTime, WatchdogTime |
| **IEC 61784-2** | Ethernet-based fieldbus (incl. EtherNet/IP) — RemoteIP mandatory |
| **IEC 62541** | OPC UA standard — OPC_UA protocol type |
| **IEC 61131-9** | IO-Link standard — IO_Link protocol type |
| **Modbus.org spec** | Modbus RTU and TCP spec — RemoteAddress (RTU slave ID) |

---

## 9. Typical AI Errors (Lessons Learned)

### 9.1 Syntax (Category A) — Auto-detectable
- CommID `COMM001` (COM prefix, not 3 digits) → regex reject
- RemoteIP `192.168.1` (missing octet) → pattern reject
- TxByteCount negative → minimum reject

### 9.2 Schema/Standard (Category B) — Validator catches
- PROFINET link with RemoteIP blank → conditional rule reject
- Protocol `Profinet` (case mismatch) → enum reject

### 9.3 Semantic (Category C) — Manual review required
- ⚠️ PROFIBUS_DP confused with PROFINET — legacy uses PROFIBUS, new design uses PROFINET; HW config must clarify
- ⚠️ WatchdogTime_ms smaller than CycleTime_ms → PLC raises link errors permanently (impossible timing)
- ⚠️ Bidirectional link written as two separate TX/RX rows — a single `Bidirectional` row is enough
- ⚠️ RemoteAddress populated for OPC UA (in OPC UA the address concept is different — node endpoint, IP is enough)
- ⚠️ S7_Comm reference without a DB — missing which DB the PUT/GET reads/writes; DB address unknown during code gen

### 9.4 Correction Request Template

> "Error in RD09 row `<CommID>`: <category> issue: <description>. Expected: <correct value>. Fix only that row."

---

## 10. Per-Project Template

`07_PROJECT_TEMPLATE/metadata_template/RD09_Comms.xlsx` blank template:
- 16 columns, header + 3 example rows (PROFINET drive / Modbus_TCP SCADA / IO_Link sensor)
- Data Validation: Protocol, Direction, Status dropdowns
- Conditional Formatting: rows with ErrorTag blank → yellow (every link should have error monitoring)

---

## 11. Related Files

- **Dependency:** `MDSCHEMA_RAWDATA_01_IO.md` (ErrorTag cross-reference)
- **Dependency:** `MDSCHEMA_RAWDATA_02_DATADICT.md` (DataBlock_TX/RX cross-reference)
- **Next spec:** `MDSCHEMA_RAWDATA_10_FBSPEC.md`
- **Producer prompt:** `04_AI_PROMPTS/analyze/PROMPT_EXTRACT_COMMS_FROM_CODE.md`
- **Per-project template:** `07_PROJECT_TEMPLATE/metadata_template/RD09_Comms.xlsx`
- **Validation schema:** `08_METADATA_INPUT/schema/rd09_comms.schema.json`

---

## 12. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py \
  --target "01_GLOBAL_STANDARDS/md_schemas/MDSCHEMA_RAWDATA_09_COMMS.md" \
  --reason "..." \
  --suggestion "..."
```

---

*v1.1.0 — Full English body (2026-05-23). Deliverable filenames updated to `RD09_Comms.xlsx/.md` to match actual project files. Status enum renamed to `Active/Inactive/Spare` (English, 2026-06-10 coordinated update; see RD02 spec §3.1). v1.2.0 roadmap: OPC UA subscription list (node mapping), MQTT/Sparkplug B protocol (IIoT integration), dual-ring PROFINET (MRP) topology documentation.*
