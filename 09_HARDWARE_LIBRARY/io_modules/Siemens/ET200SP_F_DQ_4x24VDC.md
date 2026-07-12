# Siemens ET200SP F-DQ 4x24VDC/2A — io_modules

## metadata
```yaml
schema_version: "1.0"
device_id: "SIE_ET200SP_FDQ4"
vendor: "Siemens"
model: "ET200SP F-DQ 4x24VDC/2A PM HF"
category: "io_modules"
subcategory: "safety_do_module"
part_number: "6ES7136-6DB00-0CA0"
datasheet_ref: "ET200SP Fail-safe modules manual (NOT_VERIFIED — confirm order no.)"
library_path: "io_modules/Siemens/ET200SP_F_DQ_4x24VDC.md"
last_verified: "NOT_VERIFIED"
verified: NOT_VERIFIED
severity: critical
```

> **DRAFT / NOT_VERIFIED · SAFETY.** Fail-safe output. The safety function,
> SIL/PL rating and reaction (safe state) MUST be designed and signed off by
> a certified safety engineer.

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | ET200SP Fail-safe Digital Output 4×24 V DC/2A |
| Category | F-DQ Module (PROFIsafe, PM switching) |
| Channels | 4 |
| Switching | 24 V DC, 2 A per channel (PM = plus/minus switching) |
| Safe State | de-energized (0 V) on demand |
| Safety Rating | up to SIL 3 / PL e (design-dependent — NOT_VERIFIED) |

## 2. When to use

Safety outputs: STO to a drive's safety terminals, safe contactor
drop-out, brake release with monitoring. Retrofit safety contactor coils
map here only after the safety design is confirmed.

## 3. Address Model (TIA Portal)

```
Safety output image: %Q[x].0 … (F-CPU only)
Readback / short-circuit test performed by the F-runtime.
```

## 4. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Output passivated | Readback error / cross-circuit | Check load wiring, no external feed |
| Won't energize | F-runtime not in RUN / not reintegrated | Reintegrate after fault acknowledge |

## 5. Notes

- **Human-in-the-loop mandatory** (W-A2). The factory records the module and
  marks `verified: NOT_VERIFIED`; it never sets the SIL.
- PM switching gives higher diagnostic coverage than PP for many loads —
  confirm with the safety calculation (SISTEMA).
