---
title: Platform Compatibility Matrix
version: 1.0.0
last_validated: 2026-05
last_updated: 2026-05-16
applies_to: [factory_internal]
status: ACTIVE
---

# GLOBAL_PLATFORM_MATRIX.md — Platform Compatibility Matrix

> Which Factory feature works with which PLC platform.

---

## 1. Supported Platforms

| Platform | Parser | Code Gen | Validation | Safety | Notes |
|----------|--------|----------|------------|--------|-------|
| **Siemens S7-1500 (TIA V14+)** | ✅ | ✅ | ✅ | ✅ F-PLC | Primary — strongest support |
| **Siemens S7-1200 (TIA V14+)** | ✅ | ✅ | ✅ | ⚠️ Limited safety | Modern, small machines |
| **Siemens S7-300/400 Classic** | ✅ Read-only | ⚠️ Legacy | ✅ | ✅ F-CPU (if present) | Migration source |
| **Siemens S5** | ⚠️ OCR + manual | ❌ | Limited | ❌ | Retrofit source only |
| **Allen-Bradley ControlLogix** | ✅ | ⚠️ Beta | ✅ | ✅ GuardLogix | L5X export |
| **Allen-Bradley CompactLogix** | ✅ | ⚠️ Beta | ✅ | ⚠️ Compact GuardLogix | L5X export |
| **Beckhoff TwinCAT 3** | ✅ | ⚠️ Beta | ✅ | ✅ TwinSAFE | PLCopen XML |
| **CODESYS V3** | ✅ | ⚠️ Beta | ✅ | ⚠️ SafetyDesigner | PLCopen XML |
| **Schneider EcoStruxure** | ⚠️ Limited | ❌ | ⚠️ Limited | ❌ | v3.2.0 target |
| **Mitsubishi GX Works** | ❌ | ❌ | ❌ | ❌ | v4.0.0+ target |
| **Omron Sysmac** | ❌ | ❌ | ❌ | ❌ | v4.0.0+ target |

✅ = Full support
⚠️ = Partial/beta
❌ = Not available

---

## 2. Legacy Platform Support

| Legacy | Modern Equivalent | Migration Path |
|------|-----------------|----------------|
| S5 (1980-2005) | S7-1500F | S5 → S7-300 → TIA Portal V18 |
| S7-300 STL (2000-2020) | S7-1500 + TIA SCL | TIA Migration Tool + AI extraction |
| PLC-5 / SLC-500 (1995-2015) | ControlLogix L8 | RSLogix 5/500 → Studio 5000 |
| Lenze 9300 (1995-2010) | Lenze i550 | Drive param migration table |
| WinCC Classic V7 | WinCC Unified V18 | HMI Migration Tool |

---

## 3. AI Prompt Mapping

| Platform | Parser Prompt |
|----------|---------------|
| Siemens S7-1500 (TIA) | `PROMPT_ANALYZE_S7_1500_OPENNESS.md` |
| Siemens S7-300/400 | `PROMPT_ANALYZE_S7_300_STL.md` |
| Siemens S5 | `PROMPT_ANALYZE_S5_AWL.md` |
| Allen-Bradley | `PROMPT_ANALYZE_AB_L5X.md` |
| CODESYS + TwinCAT + EcoStruxure | `PROMPT_ANALYZE_CODESYS.md` |

---

## 4. Hardware Tiers

### Tier 1 (Fully Supported)
- S7-1500 + ET200SP / ET200MP
- ControlLogix 5570 + 1756 I/O
- TwinCAT CX5140 + EL terminals

### Tier 2 (Beta)
- S7-1200 + Compact modules
- CompactLogix 5380
- CODESYS PFC200 (Wago)

### Tier 3 (Limited)
- Schneider M340/M580
- Mitsubishi Q-series

---

## 5. Network Protocol Support

| Protocol | Support | Notes |
|----------|---------|-------|
| PROFINET RT/IRT | ✅ | TIA + ET200 |
| PROFIsafe | ✅ | F-PLC required |
| EtherCAT | ✅ | Beckhoff dominant |
| EtherNet/IP | ✅ | Allen-Bradley |
| PROFIBUS-DP | ✅ Legacy | Old projects |
| Modbus TCP/RTU | ✅ | 3rd party |
| OPC UA | ✅ | SCADA integration |
| IO-Link | ⚠️ Limited | Smart sensor |
| CC-Link | ❌ | Mitsubishi (future) |

---

## 6. Version Roadmap

| Version | New Platform Support |
|---------|----------------------|
| v3.0.0-alpha | S5 / S7-300 / S7-1500 / AB / CODESYS ✅ |
| v3.1.0 | Schneider EcoStruxure beta |
| v3.2.0 | Mitsubishi GX Works (parser) |
| v3.3.0 | Omron Sysmac Studio (parser) |
| v4.0.0 | All Tier 3 platforms full support |

---

## 7. Related Files

- **AI prompts:** `04_AI_PROMPTS/analyze/` (5 platform parsers)
- **Vendor quirks:** `06_KNOWLEDGE_BASE/KB_VENDOR_QUIRKS.md`
- **Hardware selection:** `02_PROJECT_TYPES/GREENFIELD/GREENFIELD_HARDWARE_SELECTION.md`

---

*v1.0.0 — Platform matrix defines the Factory's application boundaries.*
