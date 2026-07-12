---
title: Greenfield Communications Design
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
designs: RD09_Comms
prerequisite: [MDSCHEMA_RAWDATA_09_COMMS.md]
---

# GREENFIELD_DESIGN_COMMS.md — Communications Design Guide

> **Goal:** design the communications architecture between field devices, SCADA, and higher-level systems for a greenfield project.

---

## 1. Prerequisites

- [ ] Machine + field-device inventory
- [ ] Performance requirements (cycle time, response time)
- [ ] Customer IT infrastructure (existing network, IP plan)
- [ ] SCADA/MES integration requirements

---

## 2. Protocol Selection (Decision Matrix)

| Application | Recommended Protocol | Typical cycle |
|-------------|----------------------|---------------|
| High-speed field I/O | PROFINET IRT or EtherCAT | 1-4 ms |
| Standard field I/O | PROFINET RT | 4-32 ms |
| Drive comms (motion) | PROFIdrive (PROFINET) or CIP Motion | 1-8 ms |
| Drive comms (standard) | PROFIBUS-DP or PROFINET | 8-100 ms |
| Smart sensor | IO-Link | 2-10 ms |
| Low-power ON/OFF device | AS-i | 5 ms |
| 3rd-party device (energy meter) | Modbus TCP/RTU | 100-1000 ms |
| SCADA/Historian | OPC UA | 100-5000 ms |
| MES/ERP | OPC UA, REST API, MQTT | 1-60 s |

---

## 3. Network Topology

### 3.1 Hierarchical (Classic OT)

```
[MES Layer]                 (Ethernet, OPC UA, REST)
     │
[SCADA Layer]               (Ethernet, OPC UA, S7_Comm)
     │
[Control Layer (PLC)]
     │
[Fieldbus Layer]            (PROFINET, EtherCAT)
     │
[Sensor/Actuator Layer]     (IO-Link, AS-i, hardwired)
```

### 3.2 Modern (TSN, Convergent)

A single network with PROFINET TSN or OPC UA over TSN — but overkill for most machines.

---

## 4. Design Steps

### 4.1 Step 1 — Network Segments

```yaml
PROFINET_Production:
  subnet: 192.168.1.0/24
  cpu_ip: 192.168.1.10
  io_stations: 192.168.1.20-99
  drives: 192.168.1.100-149

Modbus_Energy:
  subnet: 192.168.10.0/24
  cpu_ip: 192.168.10.10
  meters: 192.168.10.20-99

OPC_UA_SCADA:
  subnet: 192.168.100.0/24
  cpu_endpoint: opc.tcp://192.168.100.10:4840
```

### 4.2 Step 2 — CommID Numbering

```
COM001-COM099  PROFINET IO (one per station)
COM100-COM149  Drive (motion bus)
COM150-COM199  Modbus 3rd party
COM200-COM249  OPC UA SCADA
COM250-COM299  PLC-PLC links
```

### 4.3 Step 3 — Cycle Time + Watchdog

**Formula:**
- Watchdog = 3 × cycle_time (minimum)
- Watchdog = 5 × cycle_time (recommended)

```yaml
PROFINET fast (motion): cycle=4 ms, watchdog=12 ms
PROFINET standard:      cycle=32 ms, watchdog=100 ms
Modbus TCP polling:     cycle=1000 ms, watchdog=5000 ms
```

### 4.4 Step 4 — Data Structure (DB Design)

```scl
DB_PN_TX_S1 (PROFINET TX to Station 1)
  bMotorCmd : BOOL
  rSetSpeed : REAL
  iModeWord : INT
  ...

DB_PN_RX_S1 (PROFINET RX from Station 1)
  bMotorRun : BOOL
  rActSpeed : REAL
  iStatusWord : INT
  ...

DB_Comm (Comms status)
  bPN_S1_OK : BOOL
  bMB_Meter_OK : BOOL
  iComm_Error_Count : INT
```

### 4.5 Step 5 — Error Handling

For every connection:
- **Heartbeat:** the PLC toggles a tag every cycle, the slave watches it
- **Watchdog:** if the heartbeat is lost, the slave enters its safe state
- **Retry logic:** transient errors retried automatically
- **Alarm:** persistent error → triggers an RD08 alarm

---

## 5. SCADA Integration (OPC UA)

Modern best practice:
- OPC UA Server on the PLC (Siemens Unified HMI, AB FactoryTalk Linx)
- Information Model (companion specifications): PackML, Eumabois, etc.
- Security: X.509 certificates, signing + encryption

---

## 6. IT/OT Boundary

| OT (control) | DMZ | IT (corporate) |
|--------------|-----|----------------|
| PLC, HMI, drives | OPC UA Gateway | MES, ERP, Cloud |
| Fieldbus | Firewall + VLAN | Standard Ethernet |

OT-IT data flow is usually one-way (OT→IT) — for cyber-security.

---

## 7. Validation (FAT)

- [ ] Connection test per CommID (ping + telegram)
- [ ] Watchdog test (pull the cable, time the alarm)
- [ ] Throughput test (max payload)
- [ ] OPC UA endpoint test (with UA Expert)
- [ ] Firewall + VLAN validation

---

## 8. Common Design Pitfalls

- ❌ **Watchdog too short:** nuisance alarms under normal jitter
- ❌ **Watchdog too long:** device failures detected late
- ❌ **Scattered IP plan:** different protocols on the same subnet → unmanageable
- ❌ **No OT-IT boundary:** SCADA straight to MES → cyber-security hole
- ❌ **No heartbeat:** slave can't tell whether the PLC is alive
- ❌ **Flat DataBlocks:** without UDTs maintenance gets hard

---

## 9. Checklist

- [ ] Protocol matrix decided
- [ ] IP plan written
- [ ] CommID numbering designed
- [ ] Cycle time + watchdog calculated
- [ ] DataBlock structures designed (UDT)
- [ ] Error-handling plan (heartbeat + retry + alarm)
- [ ] OPC UA endpoint planned (if any)
- [ ] FAT test procedure written

---

## 10. Related Files

- **Spec:** `MDSCHEMA_RAWDATA_09_COMMS.md`
- **Retrofit equivalent:** `RETROFIT_EXTRACT_COMMS.md`
- **Standards:** IEC 61784, IEC 61158-6-*, IEC 62541 (OPC UA), TSN

---

*v1.1.0 — Full English body (2026-05-23). Greenfield advantage: designing the network architecture correctly from day one. Changing it later = cable + downtime.*
