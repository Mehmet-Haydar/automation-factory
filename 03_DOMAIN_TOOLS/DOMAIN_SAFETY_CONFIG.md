---
title: Safety Configuration (F-PLC)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [MDSCHEMA_RAWDATA_05_SAFETY.md]
status: ACTIVE
safety_critical: TRUE
---

# DOMAIN_SAFETY_CONFIG.md — Safety PLC Configuration Domain Standard

> ⚠️ Safety critical. This standard is applied under the supervision of a certified safety engineer. Every safety project in the Factory follows this standard.

---

## 1. F-PLC Platform Selection

| Platform | Type | SIL/PLr | Use |
|----------|------|---------|-----|
| Siemens S7-1500F | Standalone F-CPU | SIL3 / PLr_e | TIA Safety + Distributed Safety |
| Siemens ET200SP F-CPU | Distributed | SIL3 / PLr_e | Modular, small machines |
| Siemens S7-400F/FH | Standalone (redundant) | SIL3 / PLr_e | High availability |
| Allen-Bradley GuardLogix | Standalone | SIL3 / PLr_e | Rockwell ecosystem |
| Beckhoff TwinSAFE | EtherCAT-based | SIL3 / PLr_e | Beckhoff platform |
| Pilz PNOZ multi | Standalone | SIL3 / PLr_e | Standalone safety controller |

---

## 2. F-I/O Module Selection

### 2.1 Siemens TIA Safety

| Module | Description | Channels |
|--------|-------------|----------|
| F-DI 8x24VDC HF | Safety digital input (high feature) | 8 |
| F-DI 16x24VDC HF | 16 channel | 16 |
| F-DO 4x24VDC/2A | Safety digital output | 4 |
| F-RO 4xRelay | Relay output (for contactors) | 4 |
| F-AI 4xU/I HS | Safety analog input | 4 |

### 2.2 Allen-Bradley GuardLogix

| Module | Description |
|--------|-------------|
| 5069-IB16S | Safety DI 16x24VDC |
| 5069-OBV8S | Safety DO 8x24VDC |
| 5069-OW16S | Safety RO 16xRelay |

---

## 3. PROFIsafe Configuration

```yaml
profisafe:
  base_address: 100         # F-DA (F-Destination Address)
  f_monitoring_time: 150ms  # F-PLC cycle time × 3
  f_dest_addr_pool: 100-499 # address pool allocated to this F-CPU
  f_source_addr: 1          # F-CPU address

watchdog:
  cpu_cycle: 50ms
  f_io_watchdog: 150ms      # 3 × CPU cycle
  response_time_target: 250ms (max)
```

---

## 4. Standard Safety-Function Templates

### 4.1 Emergency Stop (E-Stop)

```scl
// F_FB_EStop_Generic instance
"F_FB_EStop1_001"(
    E_STOP := "F_I_EStop_North",      // F-DI input
    ACK_NEC := TRUE,                   // manual reset required
    ACK := "DB_Safety".bResetReq,      // operator reset button
    TIME_DEL := T#0s,                  // no delay (immediate)
    Q := "DB_Safety".bEStopOK,         // 1 = OK, 0 = E-Stop active
    ACK_REQ := "DB_Safety".bAckReq,    // reset pending
    DIAG := "DB_Safety".dwEStopDiag    // diagnostic word
);
```

### 4.2 Safety Light Curtain

```scl
"F_FB_MutingP_001"(    // Parallel muting
    AOPD := "F_I_LightCurtain",
    MUT_EN := "DB_Safety".bMutingEnable,
    M1 := "F_I_Muting_S1",            // muting sensor 1
    M2 := "F_I_Muting_S2",            // muting sensor 2
    M3 := "F_I_Muting_S3",
    M4 := "F_I_Muting_S4",
    Q := "DB_Safety".bLCOK
);
```

### 4.3 Safety Door (Two-Channel)

```scl
"F_FB_SafetyDoor_001"(
    IN1 := "F_I_Door_Limit1",        // NC contact 1
    IN2 := "F_I_Door_Limit2",        // NC contact 2
    DISCREP := T#500ms,              // discrepancy tolerance between channels
    Q := "DB_Safety".bDoorClosed,
    DIAG := "DB_Safety".dwDoorDiag
);
```

### 4.4 Two-Hand Control (Cat 4)

```scl
"F_FB_TwoHand_001"(
    IN1 := "F_I_LH_Button",
    IN2 := "F_I_RH_Button",
    DISCREP := T#500ms,              // max delay between the two buttons
    Q := "DB_Safety".bTwoHandOK
);
```

### 4.5 Safe Torque Off (STO) — Drive Integration

```scl
"F_FB_STO_001"(
    SAFE_REQ := "DB_Safety".bSTORequest OR NOT "DB_Safety".bEStopOK,
    DRIVE_OK := "DB_Drive".bSTOFeedback,
    Q := "DB_Safety".bSTOActive,
    RESP_TIME := "DB_Safety".tSTOResponseTime
);
```

---

## 5. Risk-Assessment Process

```
1. Hazard Identification
   └── ISO 12100 method
   └── Mechanical, electrical, ergonomic, thermal

2. Risk Calculation
   ├── ISO 13849-1 (Risk graph — PLr)
   │   ├── S (Severity): S1 minor / S2 serious
   │   ├── F (Frequency): F1 rare / F2 frequent
   │   └── P (Possibility of avoidance): P1 possible / P2 difficult
   │
   └── IEC 62061 (Risk matrix — SIL)
       ├── S (Severity): 1-4
       ├── F (Frequency): 1-5
       ├── P (Probability): 1-5
       └── W (Wahrscheinlichkeit): 1-5

3. SIL/PLr Target Setting
   └── Target SIL/PLr → function design

4. Performance Verification
   ├── DC (Diagnostic Coverage): ≥ 90%
   ├── CCF (Common Cause Failure): ≥ 65 points
   └── MTTFd: ≥ 30 years (high category)

5. Validation + Verification
   └── FAT response-time test
   └── TÜV certification (if required)
```

---

## 6. Proof Test

Periodic test for every safety function:

| Type | Interval | Test content |
|------|----------|--------------|
| Visual inspection | 1 year | Check cables, terminals, labels |
| Functional test | 1 year | Press E-Stop, measure response |
| Full proof test | 5-20 years | Hardware change, full SIL revalidation |

Test records live in the CMMS (Computerized Maintenance Management System).

---

## 7. Documentation Package (TÜV)

Documents to be delivered to the customer:

1. **Risk Assessment Document** (ISO 12100)
2. **SIL/PLr Calculation Worksheet** (IEC 62061 / ISO 13849-1)
3. **Safety Function List** (RD05_Safety.xlsx — APPROVED)
4. **F-PLC Configuration Report** (TIA Safety Admin Report)
5. **FAT Test Report** (response times measured)
6. **SAT Test Report** (on-site verification)
7. **Maintenance + Proof Test Schedule**
8. **Operator Training Record**
9. **TÜV/CE Conformity Declaration** (if required)

---

## 8. Common Pitfalls (KB reference)

Details: `06_KNOWLEDGE_BASE/KB_PITFALLS_SAFETY.md`

Summary:
- E-Stop on a standard PLC (move to F-PLC)
- Bypass resistance not detected
- SIL calculation error
- Response-time overrun
- Proof test skipped

---

## 9. AUTOMATION_FACTORY Application

- **AI prompt (extraction):** `PROMPT_EXTRACT_SAFETY_FROM_CODE.md` (DRAFT_UNVERIFIED discipline)
- **AI prompt (review):** `PROMPT_REVIEW_SAFETY.md`
- **RD spec:** `MDSCHEMA_RAWDATA_05_SAFETY.md`
- **Retrofit guide:** `RETROFIT_EXTRACT_SAFETY.md`
- **Greenfield guide:** `GREENFIELD_DESIGN_SAFETY.md`
- **KB:** `KB_PITFALLS_SAFETY.md`

---

## 10. Standards

- **IEC 62061** Safety of machinery — Functional safety of electrical, electronic and programmable control systems
- **ISO 13849-1** Safety of machinery — Safety-related parts of control systems
- **IEC 61508-1..7** Functional safety (electrical/electronic/programmable systems)
- **IEC 61511** Functional safety — Safety instrumented systems for the process industry
- **Machinery Directive 2006/42/EC** (CE marking)
- **OSHA 29 CFR 1910.147** Lockout/Tagout (US)
- **EN ISO 14118** Prevention of unexpected start-up (LOTO)

---

*v1.1.0 — Full English body (2026-05-23). Safety domain standard. AI NEVER estimates SIL — certified-engineer sign-off is required.*
