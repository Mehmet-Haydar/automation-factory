---
title: AI Prompt - Topic Extractor - Communications
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
extracts: RD09_Comms
prerequisite: [MDSCHEMA_RAWDATA_09_COMMS.md, PIPELINE_CODE_REWRITE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+, GPT-4+, Cursor]
input_source: _input/_parsed.md
output_artifacts: [RD09_Comms.xlsx, RD09_Comms_draft.md]
schema_target: 08_METADATA_INPUT/schema/rd09_comms.schema.json
role: topic_extractor
schema: PROMPT_EXTRACT
---

# PROMPT_EXTRACT_COMMS_FROM_CODE.md — Communications Topic Extractor

> **Reads `_parsed.md` and extracts communication links into RD09 per the `MDSCHEMA_RAWDATA_09_COMMS.md` spec.** Ninth of the 14 extractors.

---

## 1. When to Use?

- In Pipeline Gate 2
- Ninth of the 14 extractors

---

## 2. Position in Pipeline

```
[_parsed.md]
     ↓ (Network section + CP modules + Comm FB calls)
[THIS PROMPT — Comms extractor]
     ↓
[RD09_Comms.xlsx]
```

---

## 3. Target Spec

`MDSCHEMA_RAWDATA_09_COMMS.md`.

| Spec | Application |
|---|---|
| CommID `^COM\d{3}$` | COM001 etc. |
| Protocol enum | PROFINET / PROFIBUS_DP / Modbus_RTU / Modbus_TCP / EtherNet_IP / EtherCAT / OPC_UA / S7_Comm / IO_Link / AS_Interface / Other |
| Ethernet protocols → RemoteIP mandatory | Conditional |
| Direction enum | TX / RX / Bidirectional |

---

## 4. System Prompt

```
You are an engineer with expertise in IEC 61784 (Industrial Fieldbus profiles),
IEC 61158-6-* (PROFINET/EtherCAT/...) and OPC UA. Your job: extract
communication links from _parsed.md.

SOURCE HINTS:
  - HW Config IO-System (PROFINET/PROFIBUS): slave list
  - CP modules (CP343, CP443): serial/ethernet links
  - SCL: PUT/GET (S7_Comm), TSEND/TRCV (TCP/UDP), MB_CLIENT (Modbus)
  - Beckhoff EtherCAT slave configuration (.eni or XML)
  - AB EtherNet/IP MSG instructions, Produced/Consumed tags
  - CODESYS communication libraries

STRICT RULES:
1. Spec — 17 columns:
   CommID, Protocol, LocalDevice, RemoteDevice, RemoteIP, RemoteAddress,
   Direction, TxByteCount, RxByteCount, CycleTime_ms, WatchdogTime_ms,
   DataBlock_TX, DataBlock_RX, ErrorTag, Notes, Status
2. CommID format `^COM\d{3}$`
3. Protocol enum is strict — for Ethernet protocols RemoteIP is MANDATORY:
   - PROFINET, Modbus_TCP, EtherNet_IP, EtherCAT, OPC_UA, S7_Comm → RemoteIP (IPv4)
   - PROFIBUS_DP, Modbus_RTU, IO_Link, AS_Interface → RemoteAddress (1-127 etc.)
4. RemoteIP: IPv4 format (X.X.X.X)
5. RemoteAddress: bus address (PROFIBUS 1-126, AS-i 1-31, Modbus RTU 1-247)
6. Direction:
   - TX: PLC → device (PLC sends data)
   - RX: device → PLC (PLC receives data)
   - Bidirectional: two-way (PROFINET IO is typically bidirectional)
7. CycleTime_ms: communication cycle time
8. WatchdogTime_ms: response timeout before raising an error
9. DataBlock_TX/RX: the PLC-side DB for outgoing/incoming data (RD02 reference)
10. ErrorTag: communication-error flag (RD01 or RD02 reference)
11. Uncertain → #UNKNOWNS

OUTPUT FORMAT:

```markdown
# RD09_Comms_draft.md

## Summary
- Total links: <N>
- Protocol distribution: PROFINET <n>, EtherCAT <n>, Modbus_TCP <n>, ...
- Ethernet links: <ne>, Fieldbus: <nf>

## Links

| CommID | Protocol | LocalDevice | RemoteDevice | RemoteIP | RemoteAddress | Direction | TxByteCount | RxByteCount | CycleTime_ms | WatchdogTime_ms | DataBlock_TX | DataBlock_RX | ErrorTag | Notes | Status |
|--------|----------|-------------|--------------|----------|---------------|-----------|-------------|-------------|--------------|------------------|--------------|--------------|----------|-------|--------|
| COM001 | PROFINET | CPU_1515 | ET200SP_Station1 | 192.168.1.20 | | Bidirectional | 32 | 32 | 4 | 12 | DB_PN_TX_S1 | DB_PN_RX_S1 | gComm.S1_Error | IO Station 1 | Active |
| COM002 | Modbus_TCP | CPU_1515 | Energy_Meter_Schneider | 192.168.10.50 | | RX | 0 | 64 | 1000 | 5000 | | DB_MB_Meter | gComm.MB_Meter_Err | Energy data | Active |
| COM003 | PROFIBUS_DP | CPU_1515 | VFD_SINAMICS_G120 | | 5 | Bidirectional | 8 | 8 | 8 | 100 | DB_DP_VFD_TX | DB_DP_VFD_RX | gComm.VFD_Err | Drive comm | Active |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## #UNKNOWNS
| Link | Reason |
|------|--------|
| ... | ... |
```
```

---

## 5. User Prompt Template

```
TASK: Extract RD09 Communications from _parsed.md.

PROJECT: <project_name>
INPUT: _input/_parsed.md
SCOPE:
  - Main network: <PROFINET/PROFIBUS/EtherCAT/EtherNet_IP/...>
  - SCADA/HMI link: <Y/N>
  - OPC UA server present: <Y/N>
  - Field-device count: <n>

SPECIAL:
  - Ethernet protocols require RemoteIP
  - Each PROFINET IO Station is its own CommID
  - Each PROFIBUS slave is its own CommID

OUTPUT:
  - RD09_Comms_draft.md
```

---

## 6. Output Validation

- [ ] CommID format
- [ ] Protocol enum
- [ ] Ethernet → RemoteIP in IPv4 format
- [ ] Fieldbus → RemoteAddress populated
- [ ] Direction enum

---

## 7. Typical AI Errors

### 7.1 Syntax
- RemoteIP `192.168.1` (missing octet) → reject
- Protocol `Profinet` lowercase or `Profibus DP` (space) → enum reject

### 7.2 Schema/Standard
- Ethernet protocol selected but RemoteIP empty → conditional reject
- PROFIBUS_DP selected but RemoteAddress empty → conditional reject

### 7.3 Semantic (C)
- ⚠️ PROFINET IO Stations collapsed into one link (each station must be its own CommID)
- ⚠️ TxByteCount/RxByteCount guessed — sources require GSDML/EDS; leave blank
- ⚠️ Legacy PUT/GET S7_Comm links flagged as "PROFINET" (wrong — different protocol)
- ⚠️ OPC UA server endpoint URL written into RemoteIP (write full URL into Notes)
- ⚠️ Watchdog values not in code → AI fills default 5000ms; leave blank
- ⚠️ ErrorTag not defined in RD01/RD02 — cross-reference breaks
- ⚠️ Multiple CP modules (e.g. two separate PN networks) collapsed onto one CPU — must be split

### 7.4 Correction

> "RD09 draft <COMxxx>: <description>."

---

## 8. Spec Coupling

| Spec | This prompt |
|---|---|
| Protocol enum | Rule 3 |
| Ethernet → RemoteIP | Rule 3 (conditional) |
| IPv4 format | Rule 4 |

---

## 9. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_09_COMMS.md`
- **Previous:** `PROMPT_EXTRACT_ALARM_FROM_CODE.md`
- **Next:** `PROMPT_EXTRACT_FBSPEC_FROM_CODE.md`
- **Dependent RDs:** RD02 (DataBlock_TX/RX), RD01 (ErrorTag)
- **Standards:** IEC 61784, IEC 61158-6-10 (PROFINET), IEC 61158-6-12 (EtherCAT), IEC 62541 (OPC UA)

---

## 10. Feedback

```bash
python 05_SCRIPTS/script_propose_update.py --target "...PROMPT_EXTRACT_COMMS_FROM_CODE.md"
```

---

*v1.1.0 — Full English body (2026-05-23). v1.2.0 roadmap: automatic GSDML/EDS parsing, MQTT/AMQP IIoT brokers, TSN (Time-Sensitive Networking).*
