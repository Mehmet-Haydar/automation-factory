---
title: Greenfield Hardware Selection
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [greenfield]
prerequisite: [GREENFIELD_MAESTRO.md, GLOBAL_NAMING_STANDARD.md]
---

# GREENFIELD_HARDWARE_SELECTION.md

> **Goal:** systematically select PLC, modules, drives, network, and safety components in a from-scratch project.

---

## 1. Decision Order

```
1. Spec → IO list (GREENFIELD_IO_NEWDESIGN.md)
2. Safety target (SIL/PL) → is an F-PLC required?
3. Motion requirements → 1500T or 1500?
4. PLC family selection
5. IO modules (per the IO list)
6. HMI selection
7. Drive selection (per motor types)
8. Network topology + components
9. Safety components
10. Build the BOM
```

Every step depends on the previous one. Skipping is a risk.

---

## 2. PLC Family Selection

### 2.1 Decision Matrix

| Criterion | S7-1200 | S7-1500 | S7-1500F | S7-1500T |
|-----------|---------|---------|----------|----------|
| IO count | < 100 | 100-2000 | 100-2000 | 100-2000 |
| Cycle-time need | > 10 ms | < 5 ms | < 5 ms | < 1 ms |
| Safety | — | — | F-CPU | F-CPU + Motion |
| Motion control | Limited | Standard | Standard | Advanced |
| Budget | Low | Medium | Medium-High | High |
| Typical use | Simple machine, OEM | Line, complex process | Safety-critical | Servo, robotics |

### 2.2 CPU Performance Classes (within 1500 series)

| CPU | Typical Use |
|-----|-------------|
| 1511 | Small machine, < 200 IO |
| 1513 | Mid-size machine, 200-500 IO |
| 1515 | Large machine, 500-1000 IO, network master |
| 1516+ | Very large, line-level, multi-master |
| 1517 | Plant-level |

> **Rule of thumb:** pick a CPU **one class up** at the start. Changing the project mid-flight because memory is short is expensive.

### 2.3 Memory Calculation

Rough estimate (for a new project):
- Each FB averages 5-10 KB code
- Each DB averages 1-5 KB data
- 50 motors + 30 valves + 100 sensors + main sequence ≈ 1-2 MB load memory

Don't fill more than **50% of CPU memory** (leave room for growth + future change).

---

## 3. IO Module Selection

### 3.1 ET200SP (recommended, modern)

**Advantages:**
- Modular, compact
- Hot-swap (with TM)
- Wide diagnostics
- Profinet native

**IO modules:**

| Type | Module | Order number | Note |
|------|--------|--------------|------|
| DI 16x24 V | DI 16x24VDC ST | 6ES7131-6BH01-0BA0 | Standard |
| DI 16x24 V HF | DI 16x24VDC HF | 6ES7131-6BH00-0DA0 | Diagnostic at channel level |
| DO 16x24 V/0.5 A | DQ 16x24VDC/0.5A ST | 6ES7132-6BH01-0BA0 | Standard |
| DO 8x24 V/2 A | DQ 8x24VDC/2A HF | 6ES7132-6BF00-0DA0 | High current |
| AI 4ch U/I | AI 4xU/I 2-/4-wire ST | 6ES7134-6HD00-0BA1 | Standard |
| AI 4ch HF | AI 4xU/I/RTD/TC HF | 6ES7134-6JD00-0CA1 | General-purpose |
| AO 2ch U/I | AQ 2xU/I ST | 6ES7135-6HB00-0BA1 | — |
| Encoder | TM Count 1x24V | 6ES7138-6AA00-0BA0 | Single encoder |

### 3.2 IO Redundancy

20% spare ratio is **standard**:
- If you need 100 DI → buy 120 DI (8 modules = 128)
- Reason: change requests, future expansion, channel failures

---

## 4. HMI Selection

### 4.1 Option Comparison

| Option | Typical Use | Advantage | Disadvantage |
|--------|-------------|-----------|--------------|
| Comfort Panel (KP/TP) | Classic OEM | Stable, widespread | Aging (TIA Portal V18 last support) |
| **Unified Comfort** | Modern project | Web-based, modern UI | Newer, learning curve |
| Unified PC | SCADA-level | Powerful, scalable | Cost |
| 3rd party (Wonderware, Ignition) | Customer-driven | Flexible | Profinet integration is harder |

**2026 recommendation:** **Unified Comfort** for new projects; Comfort if the customer pushes back.

### 4.2 Size Selection

| Screen | Typical Use |
|--------|-------------|
| 7" | Small machine, start/stop only |
| 10-12" | Mid-size machine, alarms + recipes |
| 15-19" | Line panel, multi-page, multi-operator |
| 22"+ | Control room |

---

## 5. Drive Selection (by Motor Type)

After the motor type is decided (see the `PROMPT_CODE_GEN_FB_MOTOR.md` router):

### 5.1 DOL → just contactor + thermal

- Contactor: Siemens 3RT2 series (Sirius)
- Thermal: 3RU2 (motor protection)
- MCB: 3RV2 (motor circuit breaker)

### 5.2 Star-Delta → 3 contactors + use the PLC instead of a time relay

- 3× 3RT2 contactors + 1× 3RU2 thermal
- The PLC handles timing — the old-style time relay is unnecessary

### 5.3 Soft-Starter

| Brand | Series | Power range |
|-------|--------|-------------|
| Siemens | 3RW44 / 3RW55 | 5-560 kW |
| ABB | PSE / PSTX | 7.5-1250 kW |
| Schneider | ATS22 / ATS480 | 4-900 kW |

### 5.4 VFD

| Brand | Series | Typical Use |
|-------|--------|-------------|
| Siemens | G120 / G120C | General-purpose, 0.55-250 kW |
| Siemens | S120 | High dynamic, axes |
| Siemens | V20 | Simple, OEM |
| ABB | ACS580 | General-purpose |
| ABB | ACS880 | Industrial, heavy |
| Danfoss | FC202 / 302 | HVAC / industry |

**If the customer has a standard, follow it.**

### 5.5 Servo

| Brand | Series |
|-------|--------|
| Siemens | SINAMICS V90 (economic), S210 (modern PN), S120 (high-performance) |
| Beckhoff | AX5xxx, AX8xxx |
| Bosch Rexroth | IndraDrive Mi/MS |

---

## 6. Network Components

### 6.1 Topology Selection

| Topology | Use | Advantage | Disadvantage |
|----------|-----|-----------|--------------|
| Star | Small facility, < 10 devices | Simple, cheap | Single point of failure (switch) |
| **Linear** | Conveyor line, sequential devices | Less cabling | A break loses everything past it |
| **Ring (MRP)** | Critical process | Redundant (200 ms recovery) | Switch complexity |
| Dual Ring | High redundancy | Very safe | Expensive, complex |

**Greenfield default:** Linear or Ring (MRP). Ring if you can't afford a single point of failure.

### 6.2 Switch Selection

| Type | Example | Use |
|------|---------|-----|
| Unmanaged | Scalance XB005 | Small project, no diagnostics needed |
| Managed L2 | Scalance XB208 / XC208 | Standard, most projects |
| Managed L3 | Scalance XR500 | Plant-level, VLAN |

**Minimum for Profinet:** Managed L2 with MRP support.

### 6.3 IP Plan

See `DOMAIN_COMMS_NETWORK_PLAN.md`.

---

## 7. Safety Components

Details: `DOMAIN_SAFETY_CONFIG.md`.

Typical components (for a SIL2 / PLd target):

| Component | Type | Brand example |
|-----------|------|---------------|
| F-CPU | 1500F | Siemens 1515F |
| F-DI/DO | F-DI 8x24V, F-DQ 8x24V/2A | ET200SP F modules |
| E-Stop | E-Stop, category 3 | Siemens 3SU1, Sirius |
| Light curtain | SIL3, Cat 4 | Sick C4000, Pilz PSEN |
| Safety relay (older style) | Pilz PNOZ | Preference: F-PLC |
| Safe door switch | Magnetic, RFID | Sick TR4, Pilz PSENmag |

---

## 8. BOM (Bill of Materials)

When hardware selection is done:

```
02_HARDWARE/
├── BOM.xlsx                  # All hardware, order list
├── BOM_ALTERNATIVES.md       # Back-up plan (for supply delays)
└── HARDWARE_RATIONALE.md     # Decision rationale
```

What goes into the BOM:
- PLC + IO modules + memory card
- HMI + connection cable
- Drives + motor protection
- Switches + cables (Profinet, fiber if needed)
- Safety components
- Inside the cabinet: contactors, relays, fuses, terminal blocks
- Cables (typically out of scope here, handled by the cabinet builder)

---

## 9. Lead-Time Risk

As of 2026, lead times for some critical parts:

| Component | Normal | Risk scenario |
|-----------|--------|---------------|
| S7-1500 CPU | 4-8 weeks | Some models 16+ weeks |
| Comfort Panel | 6-10 weeks | Stabilising |
| Unified Comfort | 8-12 weeks | New generation, rare waits |
| ET200SP module | 4-8 weeks | — |
| SINAMICS G120 | 6-12 weeks | Power modules scarce in some classes |

**Strategy:**
- Pull order timing earlier in the project plan
- Backup plan with an alternative brand (`BOM_ALTERNATIVES.md`)
- Proactive risk warning to the customer

---

## 10. Checklist

- [ ] PLC family selection (capacity verified)
- [ ] IO modules (IO list + 20% spare)
- [ ] HMI selection
- [ ] Drive matched to each motor type
- [ ] Safety components (matching SIL/PL target)
- [ ] Network topology and switches
- [ ] BOM ready, alternatives documented
- [ ] Lead times reflected in the project plan
- [ ] Customer approval

---

*v1.1.0 — Full English body (2026-05-23). Hardware selection is an expensive decision to walk back. Measure twice, cut once.*
