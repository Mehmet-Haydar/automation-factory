---
title: RD09_Comms — Kunde Müller (placeholder)
last_validated: 2026-05
status: ACTIVE
---

# RD09_Comms — Kunde Müller (placeholder)

```yaml
status: DRAFT (40%)
```

## Summary (legacy system)
- PROFIBUS-DP master (CPU 315-2DP) — the new project migrates to PROFINET

## Connections (legacy)

| CommID | Protocol | LocalDevice | RemoteDevice | RemoteIP | RemoteAddress | Direction | Status |
|--------|----------|-------------|--------------|----------|---------------|-----------|--------|
| COM001 | PROFIBUS_DP | CPU_315 | SINAMICS_G120 | | 5 | Bidirectional | DRAFT (to be migrated) |
| COM002 | PROFIBUS_DP | CPU_315 | ET200M | | 6 | Bidirectional | DRAFT (to be migrated) |
| COM003 | MPI | CPU_315 | PG (programming device) | | 2 | Bidirectional | DRAFT |

## Connections (after the new project — GREENFIELD proposal)

| CommID | Protocol | LocalDevice | RemoteDevice | RemoteIP | Direction | CycleTime_ms | Status |
|--------|----------|-------------|--------------|----------|-----------|--------------|--------|
| COM001 | PROFINET | CPU_1515F | SINAMICS_G120 (new) | 192.168.1.20 | Bidirectional | 8 | TARGET |
| COM002 | PROFINET | CPU_1515F | ET200SP_F (with safety modules) | 192.168.1.30 | Bidirectional | 4 | TARGET |
| COM003 | OPC UA | CPU_1515F | SCADA (new) | 192.168.10.10 | Bidirectional | 1000 | TARGET (NEW feature) |

## Notes
- PROFIBUS-DP is legacy; will be migrated to PROFINET as part of modernization
- OPC UA is a new feature — the customer wants SCADA integration

*v1.0.0 — Migration plan aligned with RD14.*
