# Siemens ET200SP F-DI 8x24VDC — io_modules

## metadata
```yaml
schema_version: "1.0"
device_id: "SIE_ET200SP_FDI8"
vendor: "Siemens"
model: "ET200SP F-DI 8x24VDC HF"
category: "io_modules"
subcategory: "safety_di_module"
part_number: "6ES7136-6BA00-0CA0"
datasheet_ref: "ET200SP Fail-safe modules manual (NOT_VERIFIED — confirm order no.)"
library_path: "io_modules/Siemens/ET200SP_F_DI_8x24VDC.md"
last_verified: "NOT_VERIFIED"
verified: NOT_VERIFIED
severity: critical
```

> **DRAFT / NOT_VERIFIED · SAFETY.** This is a fail-safe module. The SIL/PL
> capability, wiring architecture (1oo1 / 1oo2) and evaluation MUST be
> designed and signed off by a **certified safety engineer** — the factory
> only records the module; it never determines the safety rating.

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | ET200SP Fail-safe Digital Input 8×24 V DC |
| Category | F-DI Module (PROFIsafe) |
| Channels | 8 (usable as up to 8×1oo1 or 4×1oo2, per design) |
| Safety Rating | up to SIL 3 / PL e (design-dependent — NOT_VERIFIED) |
| Protocol | PROFIsafe over PROFINET |
| Supply | via BaseUnit (24 V DC), sensor supply via module |

## 2. When to use

Safety inputs: E-stop, safety door, light curtain OSSD, two-hand control.
Retrofit rule: hardwired safety relays in the legacy panel map here ONLY
after a safety engineer confirms the architecture — the AI drafts the IO
row as `SAFE_DI` and stops.

## 3. Address Model (TIA Portal)

```
Safety input image: %I[x].0 … (F-CPU only; PROFIsafe F-address configured)
Passivation on discrepancy/short — evaluated by the F-runtime, not user code.
```

## 4. Wiring Architectures

| Architecture | Use | Note |
|--------------|-----|------|
| 1oo1 (single) | lower SIL, non-redundant sensor | 1 channel/input |
| 1oo2 (redundant) | higher SIL, dual-channel sensor | 2 channels evaluated together |

## 5. Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Channel passivated | Discrepancy time exceeded (1oo2) | Check both contacts + wiring symmetry |
| No F-address | Module not assigned in Safety Admin | Configure PROFIsafe F-dest address |

## 6. Notes

- **Human-in-the-loop mandatory:** SIL/PLr are engineer decisions
  (W-A2 gate precondition). The factory emits `verified: NOT_VERIFIED`.
- Requires an F-CPU and the TIA Safety Advanced option.
