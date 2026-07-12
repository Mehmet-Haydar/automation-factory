# RD09_Comms — Per-Project Template

> Spec: `MDSCHEMA_RAWDATA_09_COMMS.md`. Schema: `rd09_comms.schema.json`.

---

## Frontmatter

```yaml
project_id: <PROJECT_CODE>
filled_by: <Engineer Name>
filled_at: <YYYY-MM-DD>
status: <DRAFT | REVIEWED | APPROVED>
```

---

## Summary

- Total connections: __
- Protocol: PROFINET __ | EtherCAT __ | Modbus_TCP __ | PROFIBUS_DP __
- Ethernet: __ | Fieldbus: __

---

## Connections

| CommID | Protocol | LocalDevice | RemoteDevice | RemoteIP | RemoteAddress | Direction | TxByteCount | RxByteCount | CycleTime_ms | WatchdogTime_ms | DataBlock_TX | DataBlock_RX | ErrorTag | Notes | Status |
|--------|----------|-------------|--------------|----------|---------------|-----------|-------------|-------------|--------------|------------------|--------------|--------------|----------|-------|--------|
| COM001 | PROFINET | CPU_1515 | ET200SP_Station1 | 192.168.1.20 | | Bidirectional | 32 | 32 | 4 | 12 | DB_PN_TX_S1 | DB_PN_RX_S1 | gComm.S1_Error | IO Station 1 | Active |
| COM002 | Modbus_TCP | CPU_1515 | Energy_Meter | 192.168.10.50 | | RX | 0 | 64 | 1000 | 5000 | | DB_MB_Meter | gComm.MB_Meter_Err | Schneider energy meter | Active |
| COM003 | PROFIBUS_DP | CPU_1515 | VFD_SINAMICS_G120 | | 5 | Bidirectional | 8 | 8 | 8 | 100 | DB_DP_VFD_TX | DB_DP_VFD_RX | gComm.VFD_Err | Drive comm | Active |

---

## #UNKNOWNS

| Connection | Reason |
|------------|--------|
| | |

---

## Fill-in Notes

- **CommID format:** `^COM\d{3}$`
- **Protocol enum:** PROFINET/PROFIBUS_DP/Modbus_RTU/Modbus_TCP/EtherNet_IP/EtherCAT/OPC_UA/S7_Comm/IO_Link/AS_Interface/Other
- **Ethernet protocols (PROFINET/Modbus_TCP/EtherNet_IP/EtherCAT/OPC_UA/S7_Comm) → RemoteIP MANDATORY** (IPv4)
- **Fieldbus (PROFIBUS_DP/Modbus_RTU/IO_Link/AS_Interface) → RemoteAddress MANDATORY**
- **Direction enum:** TX/RX/Bidirectional
- **TxByteCount/RxByteCount:** Exact value from GSDML/EDS; if guessing, leave BLANK
- **DataBlock_TX/RX:** RD02 reference
- **Standards:** IEC 61784, IEC 61158-6-*

---

*Template v1.0.0 — RD09 Communications.*
