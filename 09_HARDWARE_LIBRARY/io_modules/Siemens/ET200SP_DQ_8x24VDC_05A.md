# SIEMENS ET 200SP DQ 8x24VDC/0.5A BA — IO_MODULES

## metadata
```yaml
schema_version: "1.0"
device_id: "SIE_ET200SP_DQ8_05A"
vendor: "Siemens"
model: "ET 200SP DQ 8x24VDC/0.5A BA"
category: "io_modules"
subcategory: "do_module"
part_number: "6ES7132-6BF01-0BA0"
datasheet_ref: "SIMATIC ET 200SP Digital output module DQ 8x24VDC/0.5A BA Manual (A5E03573344)"
library_path: "io_modules/Siemens/ET200SP_DQ_8x24VDC_05A.md"
last_verified: "2026-07"
```

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | SIMATIC ET 200SP, digital output module DQ 8x24VDC/0.5A Basic |
| Category | DO Module (transistor, PNP source) |
| Channels | 8 |
| Rated Output | 24 V DC, 0.5 A per channel |
| Supply | Via BaseUnit L+/M (light-colored BU for new potential group) |
| Protection Class | IP20 |
| Certifications | CE, UL, cUL, ATEX Zone 2 (per manual) |

## 2. Communication Interfaces

| Interface | Protocol | Telegram / Data Length | Notes |
|-----------|----------|------------------------|-------|
| ET 200SP backplane | — | 1 byte output data | Via IM 155-6 PROFINET/PROFIBUS head |

## 3. PROFINET Configuration (for S7-1500)

```
GSDML File:    via IM 155-6 head module GSDML (or TIA HW catalog direct)
Device Family: ET 200SP
Module Entry:  DQ 8x24VDC/0.5A BA (6ES7132-6BF01-0BA0)
BaseUnit:      BU15