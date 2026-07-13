---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD14
generated_at: 2026-07-12T18:27:05+00:00
model: deepseek-chat
step: RD14 Modernization Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

# RD14_Modernization_draft.md

## Finding Summary

| FindingID | Category | Severity | Priority | PLCPlatform | BlockRef | AnnotationRef | AntiPattern | CodeExample_Bad | ModernAlternative | CodeExample_Good | Effort | EffortDetail | Impact | ImpactDetail | StandardRef | LinkedRD | LinkedTag | LinkedStep | LinkedFB | LinkedAlarm | RetrofitApplicable | GreenfieldApplicable | AutoFixable | AutoFixNote | VerificationRequired | VerificationDetail | Notes | Status |
|-----------|----------|----------|----------|-------------|----------|---------------|-------------|-----------------|------------------|------------------|--------|--------------|--------|--------------|-------------|----------|-----------|------------|----------|-------------|-------------------|---------------------|-------------|-------------|---------------------|-------------------|-------|--------|
| FND001 | SAFETY | CRITICAL | 1 | S7-300 CPU314 | FC10 | NW1 | Safety logic executed on non-safety PLC without F-CPU | `U E 1.0; U E 1.1; = A 3.7` | Migrate to F-CPU (S7-1500F) with certified safety program | `U E 1.0; U E 1.1; = A 3.7` (in F-runtime group) | HIGH | 16-80h | SAFETY | | ISO 13849, IEC 62061 | RD13 | E1.0, E1.1, A3.7 | | FC10 | ALM_NotAus | NO | YES | NO | | SAFETY_ENGINEER | Requires F-CPU hardware and safety engineering | DRAFT_UNVERIFIED |
| FND002 | SAFETY | CRITICAL | 2 | S7-300 CPU314 | FC10 | NW1 | Maintenance bypass (M50.0) disables safety function | `UN M 50.0` | Remove bypass or implement key-switch with safety-rated monitoring | | MEDIUM | 4-16h | SAFETY | | ISO 13849 | RD13 | M50.0 | | FC10 | | NO | YES | NO | | SAFETY_ENGINEER | Bypass creates unsafe condition | DRAFT_UNVERIFIED |
| FND003 | SAFETY | CRITICAL | 3 | S7-300 CPU314 | FC10 | NW2 | Light curtain bypassed in maintenance mode without safety-rated monitoring | `UN M 50.0` | Use safety-rated bypass with muting sensors per IEC 61496 | | MEDIUM | 4-16h | SAFETY | | IEC 61496 | RD13 | E1.2, M50.0 | | FC10 | | NO | YES | NO | | SAFETY_ENGINEER | Muting requires safety-rated implementation | DRAFT_UNVERIFIED |
| FND004 | NAMING | MAJOR | 11 | S7-300 CPU314 | FC10-FC70 | _parsed.md §3 | Absolute addresses used instead of symbolic names | `U E 1.0`, `L EW 64`, `T MW 100` | Use symbolic tags per GLOBAL_NAMING_STANDARD | `U "E-Stop_North"`, `L "Temp_RawValue"`, `T "Temp_RawValue"` | LOW | <4h | MAINTAINABILITY | | GLOBAL_NAMING_STANDARD | RD13 | All I/O | | All FCs | | YES | YES | YES | Replace with symbolic names | NONE | | | DRAFT_UNVERIFIED |
| FND005 | STRUCTURE | MAJOR | 12 | S7-300 CPU314 | FC30 | NW1-NW4 | Manual M-bit step chain without structured state machine | `S M 20.0`, `R M 20.0` | Implement IEC 61131-3 state machine using ENUM or UDT | `#State := STATE_FILL; CASE #State OF...` | MEDIUM | 4-16h | MAINTAINABILITY | | PLCopen | RD13 | M20.0-M20.2 | | FC30 | | YES | YES | NO | | NONE | | | DRAFT_UNVERIFIED |
| FND006 | OBSOLETE_PLATFORM | MAJOR | 13 | S7-300 CPU314 | FC30, FC40 | NW3, NW2 | Legacy S5TIME timer used instead of IEC timer | `L S5T#30S; SE T 5` | Use IEC TON/TOF/TP function blocks | `TON_Instance(IN:=..., PT:=T#30S);` | LOW | <4h | MAINTAINABILITY | | IEC 61131-3 | RD13 | T1, T5 | | FC30, FC40 | | NO | YES | YES | Replace with IEC timer | NONE | | | DRAFT_UNVERIFIED |
| FND007 | PERFORMANCE | MAJOR | 14 | S7-300 CPU314 | FC50 | NW1 | Analog value read without scaling or filtering | `L EW 64; T MW 100` | Use NORM_X/SCALE_X blocks with low-pass filter | `#Scaled := SCALE_X(MIN:=0, MAX:=27648, VALUE:=EW64);` | LOW | <4h | RELIABILITY | | IEC 61131-3 | RD13 | EW64, MW100 | | FC50 | | YES | YES | YES | Add scaling and filtering | NONE | | | DRAFT_UNVERIFIED |
| FND008 | MAINTAINABILITY | MINOR | 51 | S7-300 CPU314 | FC50 | NW2 | Hardcoded threshold values without symbolic constants | `L 15500; <I` | Define named constants in a global DB | `IF #TempRaw < CONST_TEMP_LOW THEN` | LOW | <4h | READABILITY | | GLOBAL_NAMING_STANDARD | RD13 | MW100 | | FC50 | | YES | YES | YES | Replace with named constants | NONE | | | DRAFT_UNVERIFIED |
| FND009 | MAINTAINABILITY | MINOR | 52 | S7-300 CPU314 | FC60 | NW1-NW3 | Alarm bits written directly without structured alarm management | `= DB30.DBX 0.0` | Implement ISA-18.2 compliant alarm management with UDT | `#AlarmDB.Alarm_NotAus := TRUE;` | MEDIUM | 4-16h | MAINTAINABILITY | | ISA-18.2 | RD13 | DB30 | | FC60 | ALM_NotAus, ALM_MotorschutzRuehrer | YES | YES | NO | | NONE | | | DRAFT_UNVERIFIED |
| FND010 | STRUCTURE | MAJOR | 15 | S7-300 CPU314 | FC30, FC40, FC50 | NW1-NW3 | Cross-FC dependencies on M-bits create hidden coupling | `U M 20.1` in FC40, FC50 | Encapsulate state in a dedicated FB with interface | `#StateMachine.State := STATE_RUNNING;` | MEDIUM | 4-16h | MAINTAINABILITY | | IEC 61131-3 | RD13 | M20.1 | | FC30, FC40, FC50 | | YES | YES | NO | | NONE | | | DRAFT_UNVERIFIED |
| FND011 | COMMUNICATION | MAJOR | 16 | S7-300 CPU314 | FC50 | NW1 | No communication diagnostics for analog input | `L EW 64` | Add wire-break and out-of-range detection | `IF #TempRaw < 2000 THEN #WireBreak := TRUE;` | LOW | <4h | RELIABILITY | | IEC 61131-3 | RD13 | EW64 | | FC50 | | YES | YES | YES | Add diagnostics | NONE | | | DRAFT_UNVERIFIED |
| FND012 | HMI | MINOR | 53 | S7-300 CPU314 | FC60 | NW3 | No HMI visualization for alarms or process status | `= A 0.6` | Add HMI faceplates per ISA-101 guidelines | | MEDIUM | 4-16h | MAINTAINABILITY | | ISA-101 | RD13 | A0.6 | | FC60 | | YES | YES | NO | | NONE | | | DRAFT_UNVERIFIED |
| FND013 | REDUNDANCY | CRITICAL | 4 | S7-300 CPU314 | FC10-FC70 | _parsed.md §9 | Single CPU without redundancy for safety-critical process | | Implement redundant F-CPU system with PROFIsafe | | VERY_HIGH | >80h | SAFETY | | IEC 62061 | RD13 | | | All FCs | | NO | YES | NO | | SAFETY_ENGINEER | Hardware-dependent | DRAFT_UNVERIFIED |
| FND014 | COMPLIANCE | MAJOR | 17 | S7-300 CPU314 | FC10-FC70 | _parsed.md §9 | No safety validation documentation or SIL/PLr assessment | | Perform SIL/PLr assessment per IEC 62061/ISO 13849 | | HIGH | 16-80h | COMPLIANCE | | IEC 62061, ISO 13849 | RD13 | | | All FCs | | NO | YES | NO | | SAFETY_ENGINEER | Requires formal assessment | DRAFT_UNVERIFIED |
| FND015 | DIAGNOSTICS | MAJOR | 18 | S7-300 CPU314 | FC40 | NW1 | No motor protection diagnostics or status feedback | `UN E 0.4` | Add motor current monitoring and thermal model | | MEDIUM | 4-16h | RELIABILITY | | IEC 61131-3 | RD13 | E0.4 | | FC40 | ALM_MotorschutzRuehrer | YES | YES | NO | | NONE | | | DRAFT_UNVERIFIED |
| FND016 | DATA_MANAGEMENT | MINOR | 54 | S7-300 CPU314 | FC50 | NW1-NW3 | No recipe management for temperature setpoints | `L 15500; L 16500` | Implement recipe DB with configurable parameters | `#Recipe.TempLow := 15500;` | MEDIUM | 4-16h | MAINTAINABILITY | | IEC 61131-3 | RD13 | MW100 | | FC50 | | YES | YES | NO | | NONE | | | DRAFT_UNVERIFIED |

## SummaryByCategory

| Category | Critical | Major | Minor | Info | EstimatedEffort_h | TopPriority |
|----------|----------|-------|-------|------|-------------------|-------------|
| SAFETY | 3 | 0 | 0 | 0 | 24-104 | 1 |
| NAMING | 0 | 1 | 0 | 0 | <4 | 11 |
| STRUCTURE | 0 | 2 | 0 | 0 | 8-32 | 12 |
| OBSOLETE_PLATFORM | 0 | 1 | 0 | 0 | <4 | 13 |
| PERFORMANCE | 0 | 1 | 0 | 0 | <4 | 14 |
| MAINTAINABILITY | 0 | 0 | 2 | 0 | 4-20 | 51 |
| COMMUNICATION | 0 | 1 | 0 | 0 | <4 | 16 |
| HMI | 0 | 0 | 1 | 0 | 4-16 | 53 |
| REDUNDANCY | 1 | 0 | 0 | 0 | >80 | 4 |
| COMPLIANCE | 0 | 1 | 0 | 0 | 16-80 | 17 |
| DIAGNOSTICS | 0 | 1 | 0 | 0 | 4-16 | 18 |
| DATA_MANAGEMENT | 0 | 0 | 1 | 0 | 4-16 | 54 |

## ModernizationDecision

| Option | ApplicableFindings | TotalEffort | Recommendation | Rationale |
|--------|-------------------|-------------|----------------|-----------|
| RETROFIT | 8 (FND004-FND012, FND015-FND016) | MEDIUM | RECOMMENDED | Software-only changes (naming, timers, scaling, alarms) feasible without hardware replacement |
| GREENFIELD | 16 (all findings) | VERY_HIGH | RECOMMENDED | Full safety and redundancy require new F-CPU hardware and architecture |
| HYBRID | 14 (FND001-FND003, FND013-FND014 require hardware; others software) | HIGH | RECOMMENDED | Retrofit software improvements now; plan greenfield for safety-critical hardware migration |