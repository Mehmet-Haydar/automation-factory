---
title: Retrofit Hardware Analysis
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [retrofit]
prerequisite: [RETROFIT_MAESTRO.md, GLOBAL_NAMING_STANDARD.md]
---

# RETROFIT_HARDWARE_ANALYSIS.md

> **Goal:** systematically analyse the existing hardware, decide what stays and what is replaced, and select the new hardware.

---

## 1. Field Walkdown Procedure

### 1.1 Preparation

**Bring with you:**
- [ ] High-resolution camera (a phone with 12 MP+ is fine)
- [ ] Multimeter (CAT III 600 V minimum)
- [ ] Label printer or notepad
- [ ] EPLAN printout (if available) or an empty IO checklist
- [ ] Flashlight (cabinet interiors are dark)
- [ ] PPE: hard hat, insulated gloves, safety glasses, steel-toe boots

**Request from the customer:**
- [ ] Authorised personnel to accompany for Lockout-Tagout (LOTO)
- [ ] Cabinet schematics (PDF or printed)
- [ ] Maintenance staff availability
- [ ] Operator availability for a short interview

### 1.2 Walkdown Order

**Step 1 — outside the cabinet:**
- Cabinet labels (e.g. +S1, +S2)
- Buttons and lamps on the cabinet (label + function)
- HMI screens (brand, model, photograph the screen)
- Emergency stops (count, location, category)

**Step 2 — inside the cabinet (live, with care):**
- PLC and modules (brand, model, order number)
- HMI connection info
- Drives (VFD, soft-starter): brand, model, P (kW), parameters
- Switchgear (contactors, relays): count, current, brand
- Network gear (switches, gateways, slave I/O)
- **High-resolution photographs inside the cabinet** (every angle)

**Step 3 — field equipment:**
- Each motor: tag, brand, kW, RPM, IP, protection class
- Each sensor: tag, brand, model, signal type (PNP/NPN/4-20 mA)
- Each valve: tag, brand, diameter, working pressure
- Encoders/transducers: brand, model, resolution
- Safety: light curtains, mats, edges, E-stop chain

**Step 4 — operator interview:**
- "How is the machine started, and in what order?"
- "What's the most common fault you see?"
- "Which recipes/products are processed?"
- "On the new HMI, what do you definitely want / not want?"
- "What works well in the old system and must stay?"

### 1.3 Walkdown Deliverables

```
01_DOCS/
├── walkdown_photos/          # All photos, dated
├── WALKDOWN_NOTES.md         # Field observations
├── HARDWARE_INVENTORY.xlsx   # Existing-hardware inventory (below)
└── OPERATOR_INTERVIEWS.md    # Interview notes
```

---

## 2. Hardware Inventory Table

| Category | Tag | Brand | Model | Spec | Condition | Decision | Note |
|----------|-----|-------|-------|------|-----------|----------|------|
| PLC | — | Siemens | S7-313C-2DP | DP master | Working | Replace | EOL |
| HMI | — | Siemens | TP277 | 6" mono | Working | Replace | Poor visuals |
| Drive | MOT_CV01_001 | ABB | ACS550 22 kW | Profibus DP | Working | **Keep** | With Profinet GW |
| Motor | MOT_CV01_001 | Siemens | 1LE1003 22 kW | IE2, IP55 | Working | Keep | — |
| Sensor | PRX_CV01_010 | ifm | IFM-IFK3004 | M18 PNP | Working | Keep | — |
| Sensor | TMP_TK01_001 | (no plate) | (?) | 4-20 mA | **Unknown** | Test | Likely: Endress |

**Decisions:**
- **Keep:** compatible with the new PLC, in healthy condition
- **Replace:** EOL, incompatible, faulty
- **Test:** unknown, lab test required
- **Upgrade:** same series, newer version

---

## 3. Old/New Comparison Matrix

Post-walkdown decision matrix, filled in with the customer:

### 3.1 PLC Migration

| Criterion | Existing | New Target | Notes |
|-----------|----------|------------|-------|
| Brand/Model | S7-313C-2DP | S7-1515-2 PN | Customer standardises on Siemens |
| Network | Profibus DP | Profinet | PN/DP gateway for DP slaves |
| IO module | Old ET200M | ET200SP | Not rail-compatible, refresh |
| Safety | None | Integrated F-PLC | Risk assessment required |
| HMI link | MPI | Profinet | — |
| Motor drive | Profibus | Profinet (gateway or new) | Cost comparison |
| Programming language | LAD/FBD | SCL-leaning | Modernisation |

### 3.2 Logic Questions

- [ ] Are the source files for the legacy PLC program available? (Was a backup taken online?)
- [ ] Is there a password? Does the customer have the master password?
- [ ] Is there a safe copy of the legacy backups from within the last 12 months?

---

## 4. Drive Migration Strategy

### 4.1 Profibus DP → Profinet Migration

**Option A: replace all drives**
- Pro: clean architecture, single protocol
- Con: high cost
- Use when: old drives are near EOL or already faulty

**Option B: PN/DP gateway**
- Pro: reuse old drives, low cost
- Con: extra node, diagnostic complexity, bandwidth limit
- Use when: drives are healthy and the customer's budget is tight

**Option C: hybrid**
- New line: Profinet
- Old line: gateway preserved
- Risk: managing two systems

**Decision matrix:**

| Drive | Age | Health | Spares available? | Decision |
|-------|-----|--------|-------------------|----------|
| ABB ACS550 | 8 years | Good | Spare parts still produced | Gateway |
| Siemens MM440 | 12 years | Medium | EOL, spares scarce | Replace (G120) |

### 4.2 Profibus → IO-Link

Moving some sensors to IO-Link buys diagnostics. But not every sensor is supported.
- New sensors on IO-Link → accept
- Existing sensors staying → no point converting to IO-Link

---

## 5. Safety Upgrade

Safety status on the legacy machine:

- [ ] Is there a risk assessment? (TS EN ISO 12100)
- [ ] E-stop category (Cat 0, 1, 3, 4)
- [ ] Is the SIL/PL target defined? If not, **define it with the customer**
- [ ] Existing safety relays (Pilz, Sick) → does migrating to F-PLC make sense?

**Rule of thumb:** in a retrofit, safety must not drop below the previous level. If possible, improve it (e.g. category 1 → category 3).

Details: `DOMAIN_SAFETY_CONFIG.md`.

---

## 6. Selecting the New Hardware

Once the IO list, drive strategy, and safety target are settled:

### 6.1 PLC

**S7-1500 vs 1200:**
- IO count > 100 → 1500
- Safety required → 1500F
- Motion control (servo) → 1500T
- Follow the customer standard if one exists

**Module density:**
- DI 16-channel: cheap, compact → default
- DI 8-channel HF (high feature, diagnostics): for critical signals
- DO 16-channel contactor output: standard
- DO with relay output: where isolation is required

### 6.2 IO Module Selection Table

| IO Type | Suggested Module | Note |
|---------|------------------|------|
| DI 24 VDC | DI 16x24VDC HF (6ES7521-1BH00) | Diagnostic, standard |
| DO 24 VDC | DQ 16x24VDC/0.5A HF (6ES7522-1BH01) | Diagnostic |
| DO Relay | DQ 8x230VAC/2A Relay (6ES7522-5HF00) | High voltage |
| AI 4-20 mA | AI 4xU/I/RTD/TC HF (6ES7531-7QD00) | General-purpose |
| AO 4-20 mA | AQ 2xU/I HS (6ES7532-5NB00) | Speed matters |
| High-speed counter | TM Count 2x24V | For encoders |

> **Note:** order numbers are current as of 2026. For newer-generation products, verify in the Siemens Industry Mall.

### 6.3 Network

- Switch: Scalance XB200 series (managed, small) or XC200 (large)
- Topology: Linear (simple), Ring (redundant, MRP), Star (complex)
- IP plan: `DOMAIN_COMMS_NETWORK_PLAN.md`

---

## 7. BOM (Bill of Materials) Template

Once hardware analysis is done, the BOM is produced:

```
02_HARDWARE/
├── BOM.xlsx                  # Order list
├── BOM_ALTERNATIVES.md       # Alternative brands (back-up plan)
└── HARDWARE_DECISIONS.md     # Rationale for decisions (for audit)
```

BOM columns:
- # | Order Number | Description | Brand | Qty | Unit Price | Lead Time | Supplier | Note

---

## 8. Checklist

- [ ] Field walkdown complete, photos archived
- [ ] Hardware-inventory table filled
- [ ] Operator interviews written up
- [ ] Old/new comparison done
- [ ] Drive strategy decided (replace / gateway / hybrid)
- [ ] Safety target defined
- [ ] New hardware selected
- [ ] BOM ready, awaiting customer approval

---

*v1.1.0 — Full English body (2026-05-23). Weak field discovery causes surprises mid-retrofit. The goal in this phase is 95% precision and 5% on-site surprises.*
