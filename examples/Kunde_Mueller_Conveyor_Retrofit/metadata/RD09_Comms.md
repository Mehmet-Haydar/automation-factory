---
title: RD09_Comms — Kunde Müller (placeholder)
last_validated: 2026-05
status: ACTIVE
---

# RD09_Comms — Kunde Müller (placeholder)

```yaml
status: DRAFT (40%)
```

## Özet (eski sistem)
- PROFIBUS-DP master (CPU 315-2DP) — yeni proje PROFINET'e geçecek

## Bağlantılar (eski)

| CommID | Protocol | LocalDevice | RemoteDevice | RemoteIP | RemoteAddress | Direction | Status |
|--------|----------|-------------|--------------|----------|---------------|-----------|--------|
| COM001 | PROFIBUS_DP | CPU_315 | SINAMICS_G120 | | 5 | Bidirectional | DRAFT (taşınacak) |
| COM002 | PROFIBUS_DP | CPU_315 | ET200M | | 6 | Bidirectional | DRAFT (taşınacak) |
| COM003 | MPI | CPU_315 | PG (programming device) | | 2 | Bidirectional | DRAFT |

## Bağlantılar (yeni proje sonrası — GREENFIELD önerisi)

| CommID | Protocol | LocalDevice | RemoteDevice | RemoteIP | Direction | CycleTime_ms | Status |
|--------|----------|-------------|--------------|----------|-----------|--------------|--------|
| COM001 | PROFINET | CPU_1515F | SINAMICS_G120 (yeni) | 192.168.1.20 | Bidirectional | 8 | TARGET |
| COM002 | PROFINET | CPU_1515F | ET200SP_F (safety modülleri ile) | 192.168.1.30 | Bidirectional | 4 | TARGET |
| COM003 | OPC UA | CPU_1515F | SCADA (yeni) | 192.168.10.10 | Bidirectional | 1000 | TARGET (YENİ özellik) |

## Notlar
- PROFIBUS-DP eski; modernizasyon ile PROFINET'e migrate edilecek
- OPC UA yeni özellik — müşteri SCADA entegrasyonu istiyor

*v1.0.0 — Migration planı RD14 ile uyumlu.*
