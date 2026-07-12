# SAFETY_CHANGES.md — Changes Requiring / Recording Engineer Approval

Transparent record of every safety- or compliance-relevant change to the
factory. Kept public on purpose: an integrator evaluating this tool must
be able to see what was found, what was changed, and what an engineer
still has to confirm on site.

---

## PROTOCOL CONTENT CHANGE — 2026-06-13 (SAT v2, Faz 1+3+5 — branch feature/sat-v2-2026-06-12)

**Files:** `05_SCRIPTS/fat_protocol.py`, `05_SCRIPTS/script_protocol_generator.py`,
`05_SCRIPTS/protocol_i18n.py`
**Risk:** SAFETY/COMPLIANCE — customer-facing FAT/SAT test content changed
**Status:** ON BRANCH — awaiting engineer review before merge (GECE RAPORU
2026-06-13, "Mühendis onayı bekleyenler")

### What changed (engineer must review the scenario texts):
1. **SAT is no longer a re-labelled FAT copy.** New SAT sections: loop check
   with real field devices (RD01), motor rotation, sensor/switch alignment,
   REAL E-stop chain + guard door circuit, drive parameter verification,
   network/HMI integration, cybersecurity (IEC 62443/NIS2), backup +
   handover record.
2. **Safety section attribution corrected:** ISO 13849-**2** (Validation)
   instead of 13849-1; every test row now carries a "Ref." column
   (IEC 62381 / IEC 62061 / ISO 13849-2 / EN 60204-1 / IEC 62443 / IEC 62682).
3. **Language:** protocols now default to **DE** (DE/EN/TR selectable).
   The DE/TR translations of all safety scenario texts are NEW and must be
   reviewed by a German-speaking safety engineer before customer use.
4. **IEC 62682 alarm rationalization table** added to the protocol
   (priority / operator response / alarm class from RD08; missing values
   are shown as "—" with a fill-in instruction — never auto-guessed).
5. **Parser fix with safety impact:** markdown table rows with outer pipes
   were silently dropped (column index off-by-one) in the RD01/RD08 parsers
   of script_protocol_generator — IO/alarm test rows could silently vanish
   from protocols. Fixed; proof tests added.

No BLOCKER was added or removed; the RD05 readiness gate (S-17) is
preserved unchanged in both generators (regression-tested).

---

## NEW COMPLIANCE DOCUMENT — 2026-06-13 (CE essential-modification checklist — branch feature/sat-v2-2026-06-12)

**Files:** `05_SCRIPTS/ce_assessment.py`, `05_SCRIPTS/protocol_i18n.py` (ce.* keys)
**Risk:** COMPLIANCE — new customer-facing CE assessment template
**Status:** ON BRANCH — awaiting engineer review of the template TEXT before
merge (GECE RAPORU 2026-06-13, "Mühendis onayı bekleyenler")

- Generates the "wesentliche Veränderung" assessment template (DE/EN/TR,
  MD + PDF) for retrofit projects: machine identity, BMAS-style questions,
  result field, rationale + signature.
- Mandatory disclaimer at the top: the template does NOT replace a legal
  assessment; decision and signature belong to the responsible engineer.
- The tool never pre-answers a question and never pre-ticks the result
  (proof-tested).
- Greenfield projects: produced with a visible non-blocking warning.
- **Engineer must review:** the DE/EN/TR question wording and the cited
  references (BMAS interpretation paper; 2006/42/EC; (EU) 2023/1230).

---

## SISTEMA SUPPORT — 2026-06-13 (Faz 2 — branch feature/sat-v2-2026-06-12)

**Files:** `05_SCRIPTS/sistema_support.py`, `05_SCRIPTS/factory_web.py`,
`05_SCRIPTS/fat_protocol.py`, `05_SCRIPTS/customer_report.py`
**Risk:** SAFETY/COMPLIANCE — functional-safety (PL) verification status now
appears on customer-facing delivery documents
**Status:** ON BRANCH — awaiting engineer review before merge

- Division of labour by design: **the software reminds and documents; the
  engineer calculates and signs.** No automatic PL calculation is performed.
- `sistema_records` (function, file, achieved_pl, date, engineer) are ENGINEER
  DECLARATIONS — same trust model as the Gate-6 "I manually tested this" entry.
  `engineer` is mandatory (a record without a responsible name is rejected).
- **Pending behaviour (user decision 2026-06-12, WARNING not BLOCKER):** when
  RD05 defines a PLr but no matching record exists, the FAT/SAT protocol is
  STILL produced, with a visible "SISTEMA verification PENDING / AUSSTEHEND"
  box listing the function names. **No fake/placeholder report filename is
  ever written.** Re-generating after the engineer enters the records replaces
  the box with the real table.
- **Engineer decision still open (GECE RAPORU):** whether this WARNING should
  be escalated to a delivery BLOCKER (ISO 13849-2 cl. 6.3 pre-delivery
  validation evidence). Not changed tonight — blocker additions were forbidden
  this run.

---

## NIGHT-AUDIT FIXES — 2026-06-13 (Faz 9 — müfettiş→doğrulayıcı, branch feature/sat-v2-2026-06-12)

**Risk:** SAFETY/COMPLIANCE — fixes to tonight's own new code, found by the
independent audit pass. **Status:** ON BRANCH — proof-tested (+10 tests).

Safety/compliance-relevant items the engineer should be aware of:
- **CE disclaimer scope (BULGU-01):** the mandatory legal disclaimer is now
  printed in **all three languages** (DE/EN/TR), not only the selected one — a
  single-language disclaimer is absent for the other recipients.
- **PROJECT_STATE data-loss guard (BULGU-02):** a SISTEMA record write into a
  CORRUPT `PROJECT_STATE.json` now RAISES instead of silently overwriting the
  whole state (gate approvals, platform, TIA settings). Fail-safe: refuse, do
  not clobber.
- **Nightly compile silent-success (BULGU-03):** the passive nightly TIA check
  now reads the compile result — a block that imports but fails to COMPILE is
  reported `[FAIL]`, not `[PASS]`.
- **FAT IO section integrity (BULGU-06):** an empty signal table no longer
  drops the IO section (which silently renumbered the document); the section
  and a visible warning are kept (symmetric with the SAT loop-check).

No BLOCKER added or removed. Log-hygiene fixes (BULGU-07/08/10 — project paths
no longer leak into the GUI log / CLI output) are recorded for completeness but
carry no safety-content change.

---

## POLICY CHANGE — 2026-06-10 (M4, local TIA transfer)

**Files:** `05_SCRIPTS/tia_export.py`, `05_SCRIPTS/factory_web.py`
**Risk:** COMPLIANCE / IP — behaviour change of the classification gate

### Old behaviour:
`CONFIDENTIAL` or `RESTRICTED` project → TIA export/import **always hard-blocked**.
Consequence: real customer retrofit projects (normally CONFIDENTIAL) were
fully locked out of both the folder-export and the direct Openness path.

### New behaviour:
- A TIA transfer is a **local machine transfer** (NO cloud egress) — on that basis:
- `CONFIDENTIAL` → ALLOWED with engineer consent (name + checkbox); the
  consent is written to AI_DECISION_LOG (`tia_local_transfer_consent`).
- `RESTRICTED` → UNCHANGED, always hard-blocked; consent has no effect.
- Unknown/missing classification → fail-closed CONFIDENTIAL assumption remains.

### Safety defaults that stay locked (NOT settable from the GUI):
- `plcsim_only = True` — downloads to a real PLC are never automatic.
- `skip_safety_blocks = True` — F-blocks are skipped on Openness import (RD05).

**Status:** MERGED (2026-06-10) — recorded for engineer awareness.

---

## GUARD CHANGE — 2026-06-02 (v3.3.0)

**File:** `05_SCRIPTS/data_classification_guard.py`
**Risk:** COMPLIANCE — data-privacy policy change
**Change type:** behaviour change (hard-block → soft-block + consent)

### Old behaviour:
`CONFIDENTIAL` project + public provider → `allowed=False` (hard block, workflow stops)

### New behaviour:
`CONFIDENTIAL` project + public provider → `allowed=False, requires_consent=True`
(soft-block — the engineer can pass with `consent_confirmed=True`; the consent
is written to AI_DECISION_LOG)
`RESTRICTED` → unchanged, always hard-blocked

### What engineer consent means:
- The engineer confirms they hold the data-sharing authorisation
- Consent timestamp and a hash of the file list are written to AI_DECISION_LOG
- Responsibility transfers from the system to the engineer
- This mechanism does **not** work for `RESTRICTED` data — always blocked

**Status:** MERGED (2026-06-02) — recorded for engineer awareness.

---

**Date:** 2026-05-30
**Source:** audit/fix cycle — verifier + classifier + fixer agents (automation-factory)
**Status at the time:** CODE READY — not merged. Each item to be applied after engineer approval.
**Scope:** the changes below were NOT merged to `main` at the time of writing. Engineer review and approval was required. (See the summary table at the end for the final outcome.)

---

## CLASS B-1 — FB_Motor_StarDelta: Missing Star-Contactor Feedback

**File:** `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_StarDelta.scl`
**Risk:** SAFETY — phase-to-phase short circuit (STAR+DELTA conducting simultaneously)
**Impact:** The DELTA contactor can be energised without confirmation that the
STAR contactor has physically opened. With a stuck/welded STAR contactor,
STAR+DELTA conduct simultaneously → electrical short circuit + motor/switchgear damage.

### State at the time:
```scl
// step 10 → step 20 transition (time-based only):
IF s_tonStarDur.Q THEN
    out_bStar := FALSE; s_nStep := 20;   // Star done → dead time
END_IF;
```
There was **no** aux-contact feedback input confirming the STAR contactor
physically opened.

### Proposed change:
```scl
// Add to VAR_INPUT:
in_bFeedbackStar : Bool := FALSE;   // STAR contactor aux NC contact (TRUE = star OPEN)

// Add a STAR-phase guard in step 10:
IF s_tonStarDur.Q THEN
    out_bStar := FALSE;
    // Wait for star to physically open before entering dead time
    s_nStep := 15;   // STAR_OPENING — wait for aux feedback
END_IF;

// New step 15 — STAR_OPENING:
15: // STAR_OPENING — waiting for star contactor to open
    out_bMain := TRUE; out_bStar := FALSE; out_bDelta := FALSE;
    s_tonDeadTime(IN := in_bFeedbackStar, PT := in_tDeadTime);   // count only after star open
    IF in_bFeedbackStar AND s_tonDeadTime.Q THEN
        s_nStep := 30;   // Star confirmed open AND dead time elapsed → DELTA
    END_IF;
    // Timeout if star doesn't open within in_tStartTimeout
    s_tonStartTO(IN := NOT in_bFeedbackStar, PT := in_tStartTimeout);
    IF s_tonStartTO.Q THEN
        out_bMain := FALSE;
        out_bError := TRUE; out_wErrorCode := 16#0020;   // 16#0020 = Star contactor stuck closed
        s_nErrorCount := s_nErrorCount + 1;
        s_nStep := 99;
    END_IF;
```

### Questions requiring engineer approval:
1. **Field wiring:** Is the STAR contactor aux contact NC or NO? Feedback
   polarity (in_bFeedbackStar = TRUE: star OPEN or CLOSED?) must be clarified
   against the wiring diagram.
2. **Backward compatibility:** With in_bFeedbackStar defaulting to FALSE the
   dead time in step 15 never elapses → the FB is unusable until the aux
   contact is wired. Does this affect existing projects?
3. **in_tDeadTime:** Should it be referenced to the aux-feedback confirmation,
   or to time alone?

---

## CLASS B-2 — Whole Library: Missing SAFETY NOTICE Block

**Files:** all 18 .scl files
**Risk:** COMPLIANCE / SAFETY — integrators may misuse non-safety blocks in
SIL/PLr applications.

### Proposed change (added to every motor and valve FB header):
```scl
// ============================================================
// *** SAFETY NOTICE ***
// This function block is NOT designed or validated for use in
// Safety Instrumented Systems (SIS) per IEC 61508 / IEC 62061,
// or as a safety-related control function per ISO 13849 (PLr).
// For functional safety applications, use only hardware safety
// relays or F-CPU certified safety functions (SIEMENS STEP 7
// Safety, Pilz, etc.). A qualified safety engineer must review
// all applications where process or personnel safety is involved.
// ============================================================
```

### Questions requiring engineer approval:
1. **Legal wording:** the text above should be reviewed by legal counsel.
2. **Scope:** which FBs receive the notice (all, or motors/valves only)?
3. **OBs:** is the same notice required for OB1/OB82/OB86/OB100?

---

## CLASS D-1 — All Motor FBs: Missing Restart Inhibit After Emergency/Enable

**Files:**
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_Standard.scl`
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_DOL.scl`
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_VFD.scl`
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_StarDelta.scl`
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_SoftStarter.scl`

**Risk:** SAFETY — after an emergency stop, when enable returns TRUE while the
automation start command is still active, the motor restarts unexpectedly.

### State at the time (FB_Motor_Standard example):
```scl
// No inhibit on the disable → enable transition:
IF NOT in_bEnable OR in_iMode = 0 THEN
    s_nStep := 0; out_bMotorRun := FALSE; RETURN;
END_IF;
// in step 0: if t_bStartEnable is TRUE it advances to step 10 in the SAME scan
```

### Proposed change (common template for all motor FBs):
```scl
// Add to VAR:
s_bRestartInhibit : Bool := FALSE;   // Restart guard after emergency/disable
s_bEnableEdgeMem  : Bool := FALSE;   // Edge detection for enable signal

// Add at the top of REGION 01_INPUT_VALIDATION:
// Rising-edge detection for enable
IF in_bEnable AND NOT s_bEnableEdgeMem THEN
    // Enable just went TRUE — inhibit restart until explicit start edge
    s_bRestartInhibit := TRUE;
END_IF;
s_bEnableEdgeMem := in_bEnable;

// Reset inhibit only on fresh rising-edge start command
// (s_bResetTrig already clears faults — add inhibit clear here too)
IF s_bResetTrig THEN
    s_bRestartInhibit := FALSE;
END_IF;

// In state machine step 0 (IDLE), guard start condition:
// IF t_bStartEnable AND NOT out_bError AND NOT s_bRestartInhibit THEN
//     s_nStep := 10;
// END_IF;
// Alternatively: s_bRestartInhibit clears when start command goes FALSE→TRUE
// (requires second edge memory — project engineer chooses reset strategy)
```

### Questions requiring engineer approval:
1. **Reset strategy:** how is the restart inhibit cleared?
   - Option A: operator presses an explicit reset button (`in_bReset` rising edge)
   - Option B: start command goes FALSE then TRUE (fresh edge)
   - Option C: lockout timer + start command
2. **Machinery Directive scope:** risk assessment must clarify whether these
   motors require "unexpected start prevention" (EN ISO 4413/4414) under
   Machinery Directive 2006/42/EC.
3. **Retroactive impact:** if existing projects restart motors on a plain
   enable toggle, this change affects operating procedures.

---

## CLASS C (OUTPUT-HOLD) — Valve FBs: Solenoid Type Ambiguity

**Files:**
- `06_KNOWLEDGE_BASE/blocks/valve/FB_Valve_OnOff.scl`
- `06_KNOWLEDGE_BASE/blocks/valve/FB_Valve_3Way.scl`

**Risk:** OPERATIONAL / SAFETY — the solenoid type (spring-return vs
bistable/monostable) is not parametric; wrong use loses valve position.

### State at the time:
```scl
// step 0 (IDLE) / step 99 (FAULT), every scan:
out_bOpenOutput  := FALSE;   // FB_Valve_OnOff
out_bCloseOutput := FALSE;
// → correct for spring-return solenoids (valve drives to its safe position)
// → wrong for energy-maintained solenoids (valve loses position on command loss)
```

### Proposed change:
```scl
// Add to VAR_INPUT:
in_bSpringReturn : Bool := TRUE;   // TRUE = spring return (fail-closed/open per design)
                                   // FALSE = bistable/monostable (energy-maintained open)

// in step 0 and step 99:
IF in_bSpringReturn THEN
    out_bOpenOutput  := FALSE;   // Spring drives valve to safe position
    out_bCloseOutput := FALSE;
ELSE
    // Energy-maintained: hold last output so the valve retains position
    // (outputs remain as last commanded)
END_IF;
```

### Questions requiring engineer approval:
1. **Instrument datasheets:** solenoid type (spring return / bistable) must be
   determined per valve from the P&ID.
2. **Safe direction:** for spring-return solenoids the fail-safe direction
   (closes or opens) must be confirmed by the project engineer.
3. **Existing projects:** FB_Valve_OnOff users keep identical behaviour with
   in_bSpringReturn=TRUE (backward-compatible default). Confirm TRUE is the
   right project-wide default.

---

## CLASS S-1 — in_bManualMode Not Implemented (5 FBs)

**Files:**
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_VFD.scl`
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_SoftStarter.scl`
- `06_KNOWLEDGE_BASE/blocks/valve/FB_Valve_OnOff.scl`
- `06_KNOWLEDGE_BASE/blocks/valve/FB_Valve_3Way.scl`
- (FB_Motor_StarDelta.scl: `in_tStopTimeout` was also unused — coordinated with S-5)

**Risk:** SAFETY — when switched to manual mode the FB keeps following the
automation command; unexpected motion during maintenance.

### Reference (correct implementation in FB_Motor_Standard):
```scl
IF in_bManualMode THEN
    t_bStartEnable := in_bStartCmd AND NOT in_bStopCmd;
ELSE
    t_bStartEnable := in_bAutoCmd AND NOT in_bStopCmd;
END_IF;
```

### Questions requiring engineer approval:
1. Manual mode on VFD/SoftStarter: does the operator start/stop from the HMI,
   or control via setpoint?
2. Manual mode on valve FBs: direct open/close commands?
3. Do existing projects use manual mode on these FBs? (retroactive impact)

---

## CLASS S-2 — Missing Stop Guard in Transition Phases

**Files:**
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_StarDelta.scl` (step 10 STAR + step 20 DEAD TIME)
- `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_SoftStarter.scl` (step 10 RAMP UP)

**Risk:** SAFETY — an E-stop/stop command during the STAR or ramp phase is not
processed; the motor completes the transition into delta/full speed.

### Proposed change (at the top of every transition phase):
```scl
IF NOT t_bStartEnable OR NOT in_bEnable THEN
    out_bMain := FALSE; out_bStar := FALSE; out_bDelta := FALSE;
    s_nStep := 0;
END_IF;
```

### Questions requiring engineer approval:
1. If a stop arrives during DEAD TIME, what is the safe state — all outputs
   zero, or only DELTA off?
2. Are there EN ISO 13850 emergency-stop response-time requirements?

---

## CLASS S-4 — Type Conversion Defects (Overflow + Sign Bit)

**File:** `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_Standard.scl`

**Risk:** SAFETY-adjacent — the HMI fault code becomes unreliable; maintenance
analysis is corrupted.

### Problem 1: DINT overflow (line 278)
```scl
inout_udMotorData.tRuntime := DINT_TO_TIME(s_dRunSecs * 1000);
// overflows after ≈24.8 days → negative/zero tRuntime on the HMI
```
**Proposal:** `UDT_Motor.tRuntime` → `DInt` (seconds); leave the HMI
conversion to the HMI layer.

### Problem 2: WORD_TO_INT sign bit (lines 123, 275)
```scl
inout_udMotorData.iFaultCode := WORD_TO_INT(out_wErrorCode);
// 16#FFFF → -1 (INT), 16#8000 → -32768 (INT)
```
**Proposal:** `UDT_Motor.iFaultCode` → `WORD` or `DWORD`.

### Questions requiring engineer approval:
1. Changing UDT_Motor types affects existing HMI screens/SCADA tags — confirm
   backward compatibility.
2. Are there motors running continuously for 24.8+ days?

---

## CLASS S-5 — StarDelta: Missing Welded-Delta-Contactor Detection

**File:** `06_KNOWLEDGE_BASE/blocks/motor/FB_Motor_StarDelta.scl`
**Relation:** coordinated with B-1 — close in the same engineer-approval cycle.

**Risk:** SAFETY — with a welded delta contactor the PLC shows IDLE while the
motor stays energised.

### Proposed change (new step 35 — DELTA_STOPPING):
```scl
35: out_bMain := FALSE; out_bDelta := FALSE;
    s_tonStopTO(IN := in_bFeedbackDelta, PT := in_tStopTimeout);
    IF s_tonStopTO.Q THEN
        out_bError := TRUE; out_wErrorCode := 16#0012;  // Welded delta
        s_nErrorCount := s_nErrorCount + 1;
        s_nStep := 99;
    ELSIF NOT in_bFeedbackDelta THEN
        s_nStep := 0;  // Delta confirmed open
    END_IF;
```

### NC/NO decision (Siemens convention — to be confirmed):
`in_bFeedbackDelta = TRUE` → delta CLOSED (energised) → welded risk.
`in_bFeedbackDelta = FALSE` → delta OPEN (safe transition).
Aux contact: **NC (Normally Closed)** — confirm against the field wiring diagram.

### Questions requiring engineer approval:
1. Is `in_bFeedbackDelta` wired NC or NO?
2. Apply together with B-1 (in_bFeedbackStar + step 15)?

---

## Summary — Approval Status

| Class | Files | Risk | Change | Status |
|-------|-------|------|--------|--------|
| B-1 | FB_Motor_StarDelta.scl | SAFETY | in_bFeedbackStar (NC) + step 15 | **APPLIED 2026-06-01** |
| B-2 | 18 .scl files | COMPLIANCE | SAFETY NOTICE header (English) | **APPLIED 2026-06-01** |
| D-1 | 5 motor FBs | SAFETY | s_bRestartInhibit, Option A (in_bReset edge) | **APPLIED 2026-06-01** |
| C valve | FB_Valve_OnOff, FB_Valve_3Way | OPERATIONAL | in_bSpringReturn := TRUE default | **APPLIED 2026-06-01** |
| S-1 | VFD, SoftStarter, OnOff, 3Way | SAFETY | in_bManualMode IF/ELSE + in_bAutoCmd | **APPLIED 2026-06-01** |
| S-2 | StarDelta (step 10,20) + SoftStarter (step 10) | SAFETY | Stop guard in transition phases | **APPLIED 2026-06-01** |
| S-4 | FB_Motor_Standard + UDT_Motor | SAFETY | iFaultCode WORD, tRuntime DInt | **APPLIED 2026-06-01** |
| S-5 | FB_Motor_StarDelta | SAFETY | step 35 + in_bFeedbackDelta (NC) | **APPLIED 2026-06-01** |

**All items closed 2026-06-01. Gate: AUTO_VERIFIED_structural | PENDING_TIA_VERIFY.**
Physical verification (TIA Portal compile + PLCSIM run) required before production deployment.

**NC/NO decision (Siemens convention):**
`in_bFeedbackStar = TRUE` → star contactor OPEN (safe to transition).
`in_bFeedbackDelta = TRUE` → delta contactor CLOSED (energised — welded risk).
Confirm against the field wiring diagram before commissioning.

---

## SAFETY-GATE TUNING — 2026-06-10 (manual TIA V19 verification)

**Files:** `05_SCRIPTS/bridges/tia/openness_core.py`
**Risk:** SAFETY — precision change of the Openness import safety-skip gate

### Found during the first REAL TIA Portal V19 run (mocks never hit this):
The content scan of `_safety_classification` matched the standard library
**SAFETY NOTICE disclaimer** (an explicit NOT-safety declaration present in
every Factory Library block) and the bare word `SAFETY` in ordinary
changelog comments ("SAFETY FIX"). Result: **8 of 11 demo SCL files were
silently skipped** as "safety", the empty rest compiled clean and the run
reported success — silently-wrong output, and an over-broad gate that
pushes users to disable `skip_safety_blocks` entirely (the worse failure
mode).

### Change:
1. The library disclaimer comment block (identified by "SAFETY NOTICE" +
   "NOT designed or validated") is stripped before the content scan.
   Only that block is removed; all other comments are scanned (window
   widened 1000 → 4000 chars).
2. Bare `SAFETY` content hint replaced by compound phrases
   (SAFETY FUNCTION / PROGRAM / CIRCUIT / INTERLOCK / RELAY / DOOR / GATE /
   BLOCK / INSTRUMENTED, F-CPU). Unchanged detection layers: RD05-declared
   names (authoritative), `F_` naming convention, name hints
   (estop/emergency/failsafe/...), SIL1-3, EMERGENCY STOP, NOT-AUS,
   fail-closed `uncertain` for unreadable files.
3. Honest failure: any per-file import/generation error now fails the run
   ("project NOT saved") instead of compiling the remainder and reporting
   success.

### Engineer review requested:
- Confirm the compound-phrase hint list is acceptable for your block
  libraries (anything matching only the bare word "SAFETY" in comments is
  no longer skipped — RD05 declaration remains the authoritative control).

**Tests:** 862 PASS (incl. test_safety_detection.py fail-closed suite).

---

## C4-GUARD CONFIG — 2026-06-24 (FACTORY_ROOT declared PUBLIC)

**Files:** `PROJECT_STATE.json` (new, repo root), `05_SCRIPTS/factory_web.py`
(`ingest_device` comment only), `tests/test_rag_ingest_device.py`
**Risk:** SAFETY/COMPLIANCE — touches the C4 data-classification guard surface
(`data_classification_guard.check_ai_send`), which controls what may be sent to
a public-tier AI provider.
**Status:** APPLIED on `main` working tree — flagged here for engineer review.

### What was wrong
`ingest_device` (datasheet → 09_HARDWARE_LIBRARY) falls back to FACTORY_ROOT
for its classification check when no customer project is open (`self.root is
None`). FACTORY_ROOT had **no** PROJECT_STATE.json, so the guard's fail-closed
default (CONFIDENTIAL) returned a `[C4]` block — **every datasheet ingest with
no project open was silently refused** in production. The guard's own code
comment already assumed "FACTORY_ROOT is PUBLIC", but nothing made that true.

### What changed
- Added a repo-root `PROJECT_STATE.json` declaring the **framework template
  repository** PUBLIC. The guard (`check_ai_send`) now resolves FACTORY_ROOT to
  PUBLIC and allows the call. This is a configuration/data declaration — the
  guard CODE and its fail-closed semantics are **unchanged**.
- `ingest_device` still calls `check_ai_send` for every ingest (the S-1/F-03
  audit contract and its 3 proof tests in `test_safety_checks.py` are intact —
  nothing is bypassed).

### Why this is safe
- No relaxation of any customer-project rule: with a project open, ingest still
  gates on that project's classification (CONFIDENTIAL/RESTRICTED still blocked
  / consent-gated exactly as before).
- FACTORY_ROOT is genuinely public: it is the framework template, not customer
  data, and is being published. Real projects live under `examples/` or the
  configured `projects_folder`, never at the repo root.
- The payload of ingest is a public vendor datasheet, not project data.

### Engineer review requested
1. Confirm the framework repository root is intended to be PUBLIC (it is being
   open-sourced). If a deployment keeps confidential data AT the repo root,
   this declaration must be revisited.

**Proof tests:** `test_factory_root_is_public` (asserts FACTORY_ROOT resolves
PUBLIC + `check_ai_send` allows without consent). Full suite: 1484 PASS, 3
skipped. The 3 S-1/F-03 guard tests in `test_safety_checks.py` still pass
unchanged.
