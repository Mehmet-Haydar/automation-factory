# Siemens ET200SP IM 155-6 PN — io_modules

## metadata
```yaml
schema_version: "1.0"
device_id: "SIE_IM155_6_PN"
vendor: "Siemens"
model: "ET200SP IM 155-6 PN ST"
category: "io_modules"
subcategory: "interface_module"
part_number: "6ES7155-6AU01-0BN0 (confirm variant — NOT_VERIFIED)"
datasheet_ref: "ET200SP IM 155-6 PN Manual (NOT_VERIFIED)"
library_path: "io_modules/Siemens/ET200SP_IM155_6_PN.md"
last_verified: "NOT_VERIFIED"
verified: NOT_VERIFIED
```

> **DRAFT / NOT_VERIFIED.** The interface module (head station) of an
> ET200SP drop. Confirm the exact variant (ST/HF/HS) and max module count
> against the datasheet.

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | ET200SP PROFINET Interface Module IM 155-6 PN |
| Category | Interface / head module |
| Max IO modules | up to 30/64 per station (variant-dependent) |
| Interface | PROFINET IO (2-port switch, X1 P1/P2) |
| Supply | 24 V DC (own + module backplane) |
| Bus | ET200SP backplane (BaseUnits click on right) |

## 2. Role in the station

Every ET200SP drop starts with an IM155-6 (the head), then a sequence of
BaseUnits + IO modules, closed by a server module. The factory's IO modules
(DI/DQ/AI/AQ/F-DI/F-DQ) all sit behind this head.

## 3. Address / Config

```
The IM carries the station's PROFINET device name + IP.
IO module addresses (%I/%Q) are assigned by slot in HW config.
```

## 4. Wiring / Topology Notes

- Light BaseUnit (BU..D) = new potential group (brings in 24 V);
  dark BaseUnit (BU..B) = continues the previous group.
- The FIRST BaseUnit after the IM must be a light BU.
- A server module (dummy) terminates the station.

## 5. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Whole drop missing | IM device name/IP unset | Assign in TIA "Assign device name" |
| Modules shifted | Missing/extra BaseUnit | Match HW config slot order to hardware |

## 6. Notes

- One IM per ET200SP station; large lines use several stations on one PN.
- Redundant/HF variants exist for higher availability — confirm need.
