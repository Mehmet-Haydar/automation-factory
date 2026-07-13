---
title: RD14_Modernization — Kunde Müller Conveyor Retrofit
last_validated: 2026-05
status: ACTIVE
---

# RD14_Modernization — Kunde Müller Conveyor Retrofit

> Produced by the AI (PROMPT_EXTRACT_MODERNIZATION_FROM_CODE.md) — sourced from RD13 Annotation and _parsed.md.

---

## Frontmatter

```yaml
project_id: KMG-2026-001
filled_by: AI Engine + Mehmet Haydar (review)
filled_at: 2026-05-15
customer_decision: PENDING (customer presentation 2026-06-01)
status: IDENTIFIED
```

---

## Summary (SummaryByCategory)

| Category | CRITICAL | MAJOR | MINOR | INFO | Total | Est. Effort (h) | TopPriority |
|----------|----------|-------|-------|------|--------|---------------------|-------------|
| SAFETY | 3 | 0 | 0 | 0 | 3 | 96 | FND001, FND008, FND009 |
| NAMING | 0 | 1 | 0 | 0 | 1 | 12 | FND002 |
| STRUCTURE | 0 | 1 | 0 | 0 | 1 | 40 | FND003 |
| OBSOLETE_PLATFORM | 0 | 1 | 0 | 0 | 1 | 16 | FND004 |
| MAINTAINABILITY | 0 | 0 | 1 | 0 | 1 | 8 | FND005 |
| ALARM | 0 | 0 | 1 | 0 | 1 | 4 | FND006 |
| HMI | 0 | 0 | 1 | 0 | 1 | 16 | FND007 |
| **TOTAL** | **3** | **3** | **3** | **0** | **9** | **192** | |

**Hardware cost:** ~€18,000 (F-PLC + F-IO + new HMI panel)

---

## Modernization Decision (ModernizationDecision)

| Option | Applicable Findings | Total Effort | Recommendation | Rationale |
|---------|---------------------|-------------|-------|---------|
| **RETROFIT** | 9 | HIGH (192h + €18K) | ACCEPTABLE | NAMING and STRUCTURE findings are solvable; an F-PLC can be added but the old hardware stays. Risk: the spare-parts problem persists. FND008/FND009 (E-Stop bypass + fake redundancy) are already resolved by F-PLC migration. |
| **GREENFIELD** ⭐ | 9 | VERY_HIGH (256h + €45K) | **RECOMMENDED** | Hardware is obsolete (1995 — 31 years old), no spare parts. F-PLC is required anyway — comes with the new CPU. TIA Portal V18 native. A modern 15+ year investment. All three CRITICAL findings are solved by one migration. |
| HYBRID | 9 | HIGH (216h + €30K) | NOT_RECOMMENDED | A mixed approach doubles the cost. Either full retrofit or full greenfield. |

**Recommendation:** **GREENFIELD** — combined, the old-hardware problem and the F-PLC requirement bring the total cost close, but the lifespan is far longer.

---

## Findings

### FND001 — E-Stop + Light Curtain on a Standard PLC (SAFETY / CRITICAL) 🛑

- **Category:** SAFETY
- **Severity:** CRITICAL
- **Priority:** 1
- **PLCPlatform:** S7_300
- **BlockRef:** FC10 (Networks 5, 6, 8, 9)
- **AnnotationRef:** ANN0042, ANN0051, ANN0078 (from RD13)

**Anti-Pattern:**
> Emergency stop (2× E-Stop) and the safety barrier (2× Light Curtain) are implemented on a standard PLC — there is no F-CPU. The master contactor (Q3.7) is driven from a standard DO output. The light curtain has bypass logic under "maintenance mode" (FC10 NW8).
>
> A single fault (PLC cycle error, module failure, broken cable, etc.) can disable the safety function. CE documentation cannot legally be renewed.

**Bad Code Example (FC10 NW5):**
```
NETWORK 5: E-Stop Logic
    A     I    100.0    // NOT-AUS Nord (NC)
    A     I    100.1    // NOT-AUS Süd (NC)
    AN    M    50.0     // Wartungs-Bypass
    =     Q    3.7      // Hauptschütz
```

**Modern Alternative:**
> Safety functions are re-implemented on an F-PLC (Siemens S7-1500F or GuardLogix). F-I/O connected via PROFIsafe telegram. Uses the SIMATIC Safety block F_ESTOP1.

**Good Code Example:**
```scl
// F_FB_EStop_Operator_001 (TIA Safety, F-FB)
"F_FB_EStop_OP_001"(
    E_STOP := "F_I_EStop_North" AND "F_I_EStop_South",  // Two-channel
    ACK_NEC := TRUE,                                     // Manual reset
    ACK := "DB_Safety".bResetReq,
    Q := "DB_Safety".bEStopOK,
    DIAG := "DB_Safety".dwEStopDiag
);

// Light Curtain with proper muting (no manual bypass)
"F_FB_MutingP_001"(
    AOPD := "F_I_LC_Loading",
    M1 := "F_I_Muting_S1",     // 2 muting sensors + time window
    M2 := "F_I_Muting_S2",
    Q := "DB_Safety".bLC_OK
);
```

- **Effort:** HIGH (~80 hours + hardware)
- **EffortDetail:** F-CPU programming 40h + risk assessment 16h + FAT/TÜV 24h
- **Impact:** SAFETY
- **StandardRef:** IEC 62061, ISO 13849-1, Machinery Directive 2006/42/EC
- **LinkedRD:** RD05 (SF001-SF004)
- **Retrofit:** YES (F-CPU as an additional module)
- **Greenfield:** YES (the new CPU already includes the F-PLC)
- **AutoFixable:** NO (requires a human + certified engineer)
- **VerificationRequired:** SAFETY_ENGINEER
- **VerificationDetail:** Hans Becker (TÜV cert.) + risk assessment + FAT response-time test
- **Notes:** the light-curtain bypass must be removed — alternative: door interlock + muting redesign
- **Status:** IDENTIFIED (awaiting certified engineer review)

---

### FND002 — 47 Absolute Addresses Mixed with German Names (NAMING / MAJOR)

- **Category:** NAMING
- **Severity:** MAJOR
- **Priority:** 2
- **PLCPlatform:** S7_300
- **BlockRef:** OB1, FC1, FC2, FC30
- **AnnotationRef:** ANN0001..ANN0035

**Anti-Pattern:**
> All IO and memory markers mix German symbols with absolute addresses (E_Start, A_Schuetz, MW100). 47 absolute addresses detected. Mapping address ↔ function during maintenance is difficult.

**Modern Alternative:**
> GLOBAL_NAMING_STANDARD.md (AUTOMATION_FACTORY): tag format `^[A-Z]+_[A-Z0-9]+_\d{3}(_[A-Z]+)?$`. The old German names are preserved in the `OldTag` column, and in the Description as `(orig: ...)`.

**Good Code Example:**
```scl
// Old: A I 0.0 (E_Start) → A I 0.2 (E_Motor_Lauf) → = Q 0.0 (A_Schuetz)
// New:
CONV_BEL_001_OUT := MOT_CV01_001_START AND NOT MOT_CV01_001_RUN;
```

- **Effort:** MEDIUM (~12 hours)
- **Impact:** MULTIPLE — MAINTAINABILITY, RELIABILITY, COMPLIANCE
- **ImpactDetail:** easier maintenance + IEC 61131-3 compliance + customer documentation
- **LinkedRD:** RD01, RD02
- **Retrofit:** YES (PARTIAL — via a find-replace script)
- **Greenfield:** YES (already standard)
- **AutoFixable:** PARTIAL
- **AutoFixNote:** bulk-rename with `script_tag_rename.py` after RD01 approval; manual verification
- **VerificationRequired:** FUNCTIONAL_TEST
- **Status:** IDENTIFIED

---

### FND003 — All Logic in OB1 (STRUCTURE / MAJOR)

- **Severity:** MAJOR | **Priority:** 3 | **Effort:** HIGH (~40h)

OB1 is 2400+ lines, no modularity. Modern alternative: modular FB_Motor + FB_Valve + FB_Sequence + FB_ModeMgr structure (RD10 FBSpec).

---

### FND004 — S7-300 Is an End-of-Support Platform (OBSOLETE_PLATFORM / MAJOR)

- **Severity:** MAJOR | **Priority:** 4 | **Effort:** MEDIUM (~16h)

Siemens S7-300 is end-of-life (2023). Spare-parts availability is decreasing. TIA Portal V14+ still supports S7-300 but it will be removed in future versions.

---

### FND005 — ~30% Uncommented Code (MAINTAINABILITY / MINOR)

- **Severity:** MINOR | **Priority:** 50 | **Effort:** LOW (~8h)

Network header comments are missing, magic numbers are unexplained. Modern approach: header + inline comments.

---

### FND006 — Alarm Management Not ISA-18.2 Compliant (ALARM / MINOR)

- **Severity:** MINOR | **Priority:** 60 | **Effort:** LOW (~4h)

FC40 sets 32 alarm bits with no classification. Modern approach: RD08 ISA-18.2 (Critical/Warning/Info) + ALARM_S/ProgramAlarm.

---

### FND007 — HMI (WinCC Classic) Not ISA-101 Compliant (HMI / MINOR)

- **Severity:** MINOR | **Priority:** 70 | **Effort:** MEDIUM (~16h)

The legacy HMI is over-colorful, has no access levels, and lacks multi-lang support. Modern approach: TIA WinCC Unified + ISA-101 discipline (RD11).

---

### FND008 — M50.0 Maintenance Bypass Disables the E-Stop (SAFETY / CRITICAL) 🛑

- **Category:** SAFETY
- **Severity:** CRITICAL
- **Priority:** 1 (same level as FND001 — handled together)
- **PLCPlatform:** S7_300
- **BlockRef:** FC10 Network 5
- **AnnotationRef:** (from the snippet analysis — `_input/old_code_snippet.awl`)
- **Source:** AWL snippet IO extract session (2026-05-22)

**Anti-Pattern:**
> The master-contactor logic in FC10 NW5 is:
>
> ```
> A   I 100.0   // NOT-AUS Nord (NC)
> A   I 100.1   // NOT-AUS Süd  (NC)
> AN  M 50.0    // Wartungs-Bypass
> =   Q 3.7     // Hauptschütz
> ```
>
> The `AN M50.0` logic can disable both E-Stop input chains in software. When M50.0 = TRUE, the master contactor (Q3.7) stays energized despite the E-Stop being pressed. This is the concrete manifestation of FND001 (E-Stop on a standard PLC) and is reported as a separate finding in a TÜV audit.

**Modern Alternative:**
> Two-channel E-Stop on an F-PLC (F-CPU). The bypass logic is removed; maintenance mode is managed by a separate certified F-FB (guaranteed via a door interlock + key switch).

**Good Code Example:**
```scl
// No bypass — maintenance mode via a hardware key switch
"F_FB_EStop_OP_001"(
    E_STOP  := "F_I_EStop_North" AND "F_I_EStop_South",
    ACK_NEC := TRUE,
    ACK     := "DB_Safety".bResetReq,
    Q       := "DB_Safety".bEStopOK
);
// Maintenance mode only via an F-IO key switch, NOT a software marker
```

- **Effort:** MEDIUM (~8 hours — no additional cost if handled together with FND001)
- **EffortDetail:** anti-pattern detection + risk assessment + F-FB verification
- **Impact:** SAFETY (human life safety)
- **StandardRef:** IEC 62061, ISO 13849-1, Machinery Directive 2006/42/EC
- **LinkedRD:** RD01 (MASTER_CONTACTOR Q3.7, F_I_EStop_*), RD05 (SF001), RD14 (linked to FND001)
- **Retrofit:** YES (automatically fixed by F-CPU migration)
- **Greenfield:** YES
- **AutoFixable:** NO
- **VerificationRequired:** SAFETY_ENGINEER
- **VerificationDetail:** Hans Becker (TÜV cert.) — verifies the bypass is actually removed + maintenance mode is protected by a hardware lock
- **Notes:** a sub-finding of FND001; reported separately so the customer sees the concrete risk
- **Status:** IDENTIFIED (awaiting certified engineer review)

---

### FND009 — Broken E-Stop Redundancy: NW5 vs NW6 Asymmetry (SAFETY / CRITICAL) 🛑

- **Category:** SAFETY
- **Severity:** CRITICAL
- **Priority:** 1 (same level as FND001)
- **PLCPlatform:** S7_300
- **BlockRef:** FC10 Networks 5 and 6
- **AnnotationRef:** (from the snippet analysis — `_input/old_code_snippet.awl`)
- **Source:** AWL snippet IO extract session (2026-05-22)

**Anti-Pattern:**
> FC10 processes the E-Stop across two separate networks, but the apparent redundancy is fake:
>
> - **NW5:** `A I100.0 & A I100.1 & AN M50.0 = Q3.7` — drives the master contactor (with bypass)
> - **NW6:** `A I100.0 & A I100.1 = M50.7` — only sets an internal flag, drives no hardware output
>
> NW6 is **not a physical redundancy** for NW5, just a flag mirror. If the PLC skips executing NW5 (cycle fault, jump, dispatcher bug) the E-Stop never reaches any hardware output — NW6's output is unused. This is a classic anti-pattern that visually looks "two-channel" but fails at a single point.

**Modern Alternative:**
> On an F-PLC, the E-Stop is read from two hardware channels; the F-CPU automatically performs diversity + cross-comparison. A fake redundancy like a flag mirror is not possible (the compiler rejects it).

**Good Code Example:**
```scl
// From two F-IO hardware channels, automatically compared by the F-FB
// Guaranteed by F-CPU diversity, not software redundancy
"F_FB_EStop_OP_001"(
    E_STOP_CH1 := "F_I_EStop_North_K1",  // F-IO module 1
    E_STOP_CH2 := "F_I_EStop_North_K2",  // F-IO module 2 (different CPU core)
    Q          := "DB_Safety".bEStopOK   // cross-comparison timeout on the F-CPU
);
```

- **Effort:** MEDIUM (~8 hours — no additional cost if handled together with FND001)
- **EffortDetail:** NW5/NW6 logic analysis + diversity design + F-IO layer selection
- **Impact:** SAFETY (PFH/SIL has not been calculated, actual PLr is reduced)
- **StandardRef:** ISO 13849-1 Category 3/4 (diversity requirement), IEC 62061
- **LinkedRD:** RD01 (F_I_EStop_*, MASTER_CONTACTOR), RD05 (SF001), RD14 (linked to FND001)
- **Retrofit:** YES (automatically fixed by F-CPU migration)
- **Greenfield:** YES
- **AutoFixable:** NO
- **VerificationRequired:** SAFETY_ENGINEER
- **VerificationDetail:** Hans Becker (TÜV cert.) — PFH/Category calculation + F-IO diversity verification
- **Notes:** would not have been detected without the snippet analysis — a concrete benefit of the "read the code" discipline
- **Status:** IDENTIFIED (awaiting certified engineer review)

---

## #UNKNOWNS

| Finding | Reason |
|-------|-------|
| Customer budget decision | RETROFIT €32K vs GREENFIELD €60K — customer preference unclear |
| TÜV process duration | 4-12 weeks depending on the customer's region — needs clarification |

---

## Customer Presentation Summary (2026-06-01)

```
KUNDE MÜLLER GMBH — MODERNIZATION REPORT
============================================

9 modernization findings detected (3 CRITICAL, 3 MAJOR, 3 MINOR).

CRITICAL findings:
  FND001 — NO F-PLC (E-Stop + Light Curtain on a standard PLC)
  FND008 — M50.0 maintenance bypass disables the E-Stop in software
  FND009 — Fake E-Stop redundancy (NW5/NW6 asymmetry)

All three share the same root cause: F-PLC migration resolves all of them.
CE documentation cannot be renewed in the current configuration.

3 Options:
  A) RETROFIT — €32K, 4 months, F-PLC add-on module
  B) GREENFIELD — €60K, 6 months, full renewal (RECOMMENDATION ⭐)
  C) HYBRID — €45K, 5 months (not recommended)

Our recommendation: GREENFIELD
  - Hardware is already old (1995)
  - F-PLC native
  - 15+ year lifespan
  - TIA Portal V18 modern platform

Please confirm your choice by 2026-06-15.
```

---

*v1.0.0 — This example RD14 is a real decision document meant to be presented to the customer. A concrete summary of the factory's value proposition.*
