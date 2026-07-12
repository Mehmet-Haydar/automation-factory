# Siemens ET200SP AQ 4xU/I — io_modules

## metadata
```yaml
schema_version: "1.0"
device_id: "SIE_ET200SP_AQ4"
vendor: "Siemens"
model: "ET200SP AQ 4xU/I ST"
category: "io_modules"
subcategory: "ao_module"
part_number: "6ES7135-6HD00-0BA1"
datasheet_ref: "ET200SP System Manual (NOT_VERIFIED — confirm order no.)"
library_path: "io_modules/Siemens/ET200SP_AQ_4xU_I.md"
last_verified: "NOT_VERIFIED"
verified: NOT_VERIFIED
```

> **DRAFT / NOT_VERIFIED.** Ranges and resolution below are the standard
> ET200SP analog-output family values; confirm the exact order number and
> per-channel range against the datasheet before commissioning.

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | ET200SP Analog Output Module 4×U/I |
| Category | AO Module (voltage / current) |
| Channels | 4 |
| Output Ranges | ±10 V, 0..10 V, 0..20 mA, 4..20 mA (per channel) |
| Resolution | 16 bit (incl. sign) |
| Supply | via BaseUnit (24 V DC) |
| Protection Class | IP20 |

## 2. When to use

Continuous setpoints to field devices without a fieldbus: VFD analog speed
reference (0..10 V / 4..20 mA), proportional-valve command, chart recorders.
For PROFIdrive drives prefer the telegram (see the SINAMICS entry) over an
analog reference.

## 3. Address Model (TIA Portal)

```
Output (PLC → module): %QW[x], %QW[x+2], … one WORD per channel
Scaling: 0..27648 = 0..100 % of the configured range (Siemens norm).
```

## 4. SCL Scaling Template

```scl
// engineering value → raw (4..20 mA over 0..100 %)
#raw := REAL_TO_INT(#eng_percent / 100.0 * 27648.0);
// %QW[x] := #raw;   // set the channel address per HW config
```

## 5. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Output stuck at 0 | Range set to current, wiring on voltage terminals | Match HW-config range to the terminal used |
| 4 mA offset ignored | Using 0..20 mA range for a 4..20 mA device | Reconfigure channel to 4..20 mA |

## 6. Notes

- The assembler binds an AO signal to FB analog-command ports the same way
  it binds an AI to a raw-value input (conservative, unique-token).
- **Safety:** standard AO — not for safety-rated setpoints.
