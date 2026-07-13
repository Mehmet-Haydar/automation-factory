---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD09
generated_at: 2026-07-12T18:25:52+00:00
model: deepseek-chat
step: RD09 Communication Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

# RD09_Comms_draft.md

| CommID | Protocol | LocalDevice | RemoteDevice | RemoteIP | RemoteAddress | Direction | TxByteCount | RxByteCount | CycleTime_ms | WatchdogTime_ms | DataBlock_TX | DataBlock_RX | ErrorTag | Notes | Status |
|--------|----------|-------------|--------------|----------|---------------|-----------|-------------|-------------|--------------|-----------------|--------------|--------------|----------|-------|--------|
| COM001 | S7_Comm | S7-300 CPU 314 | HMI/SCADA | | | Bidirectional | | | | | | | | Legacy S7 connection via MPI/DP (no Ethernet CP identified) | DRAFT_UNVERIFIED |
| COM002 | PROFIBUS_DP | S7-300 CPU 314 | ET200S (distributed I/O) | | 3 | Bidirectional | | | | | | | | Assumed DP slave for remote I/O (EW64, E1.x, A0.x) | DRAFT_UNVERIFIED |
| COM003 | PROFIBUS_DP | S7-300 CPU 314 | ET200pro (motor starter) | | 4 | TX | | | | | | | | Motor starter for Band (A0.0) and Ruehrer (A0.1-A0.3) | DRAFT_UNVERIFIED |
| COM004 | Modbus_RTU | S7-300 CPU 314 | Temperature transmitter | | 1 | RX | | | | | | | | 4-20mA analog input (EW64) via Modbus RTU (legacy, removed 2013) | DRAFT_UNVERIFIED |
| COM005 | PROFIBUS_DP | S7-300 CPU 314 | Safety relay (Pilz) | | 5 | RX | | | | | | | | NOT-AUS chain (E1.0, E1.1) and light curtain (E1.2) via safety relay | DRAFT_UNVERIFIED |
