# Siemens ET200SP DQ 8x24VDC/2A Relay — io_modules

## metadata
```yaml
schema_version: "1.0"
device_id: "SIE_ET200SP_DQ_RLY"
vendor: "Siemens"
model: "ET200SP DQ 8x24..230VAC/5A relay"
category: "io_modules"
subcategory: "do_module"
part_number: "6ES7132-6HB01-0BB0"
datasheet_ref: "ET200SP System Manual (NOT_VERIFIED — confirm order no. against the panel BOM)"
library_path: "io_modules/Siemens/ET200SP_DQ_16x24VDC_Relay.md"
last_verified: "NOT_VERIFIED"
verified: NOT_VERIFIED
```

> **DRAFT / NOT_VERIFIED.** Structural facts below reflect the standard
> ET200SP relay-output module family and are stable reference data; the
> exact **order number, channel count and current rating MUST be confirmed
> against the project BOM / datasheet** before ordering or wiring.

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | ET200SP Digital Output Module, relay |
| Category | DO Module (relay, potential-free) |
| Channels | 8 (typical relay variant — confirm) |
| Switching Voltage | 24 V DC … 230 V AC |
| Switching Current | up to 5 A per channel (resistive; derate for inductive) |
| Supply | via BaseUnit (24 V DC backplane) |
| Protection Class | IP20 |
| Certifications | CE, cULus (confirm on datasheet) |

## 2. When to use

Potential-free / mixed-voltage loads that a 24 V DC transistor output cannot
switch: contactor coils on foreign voltage, signal lamps, legacy 230 V AC
actuators kept during a retrofit. Relay life is finite — for high-frequency
switching prefer a transistor DQ + interposing relay.

## 3. Address Model (TIA Portal)

```
Output (PLC → module): %Q[x].0 … one bit per channel
No process input image (status via module diagnostics only).
```

## 4. Wiring Notes

- Each relay channel is potential-free (own C/NO terminals) — group commons
  per the BaseUnit type (light/dark BU).
- A new load group needs a BaseUnit with incoming supply (light BU).

## 5. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Contact welding | Inductive load without suppression | Add RC/diode/varistor across the coil |
| Channel dead after retrofit | Wrong BaseUnit potential group | Verify light/dark BU sequence |

## 6. Notes

- Relay modules occupy the same rack model as transistor DQ; the assembler
  treats their bits as ordinary DQ signals.
- **Safety:** relay DO is NOT an F-module — never use for a safety function
  (see the F-DQ entry for SIL-rated outputs).
