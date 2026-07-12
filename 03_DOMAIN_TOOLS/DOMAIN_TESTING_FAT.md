---
title: Factory Acceptance Test (FAT)
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [MDSCHEMA_RAWDATA_12_USECASE.md]
status: ACTIVE
---

# DOMAIN_TESTING_FAT.md — Factory Acceptance Test (FAT) Domain Standard

> Tests performed at the factory before customer acceptance. Derived from RD12 UseCases. The factory side of pipeline Gate 7.

---

## 1. What's FAT, What's SAT?

| | FAT | SAT |
|--|-----|-----|
| Full name | Factory Acceptance Test | Site Acceptance Test |
| Location | At the factory (manufacturer) | On site (at the customer's machine) |
| Purpose | Verify compliance with the spec | Site integration + final acceptance |
| Customer present? | Sometimes (witness) | Always (sign-off) |
| Test environment | Simulation or stub I/O | Real machine |
| Followed by | Site installation | Production starts |

---

## 2. FAT Preparation Stage

### 2.1 Preconditions

- [ ] All of RD01-RD14 at `APPROVED` status
- [ ] Gate 5 code generation complete
- [ ] Gate 6 simulation environment ready (at least PLCSIM Advanced)
- [ ] Test plan presented to the customer and approved

### 2.2 Test Environment (Factory)

```
[PLC (real or simulated)]
       ↔ (PROFINET)
[ET200SP Station 1 (real or simulated)]
       ↔
[HMI (real panel or WinCC RT)]
       ↔ (OPC UA)
[SCADA (simulation)]
```

Typical factory test setup:
- **PLC:** Real S7-1500F (1 unit, in a desktop cabinet)
- **HMI:** Real HMI panel or WinCC RT (on PC)
- **I/O:** Stub box (manual switches + LEDs) or PLCSIM Advanced
- **Drive:** Drive simulator or real drive with empty shaft
- **SCADA:** Simulation (Ignition Edge / Aveva test)

---

## 3. Test Plan Generation (from RD12)

### 3.1 UseCase → Test Mapping

In `RD12_UseCase.xlsx`, every scenario with `FATTestable=Y` is automatically converted into a FAT test.

```
UC001 Operator_Starts_Auto_Cycle
   ↓ AI: PROMPT_TEST_GEN_FAT.md
TEST-FAT-001-001 (1 precondition step + 1 trigger + 5 assertions)

UC010 Emergency_Stop_During_Production
   ↓
TEST-FAT-010-001 (E-Stop response-time test)
```

### 3.2 Test Plan Template

```yaml
test_id: TEST-FAT-001-001
test_name: Operator_Starts_Auto_Cycle
based_on: UC001
priority: HIGH (Gate 7 critical test)

precondition:
  - PLC mode: RUN
  - Safety_OK = TRUE
  - HMI: SCR001 active
  - Recipe: Recipe_Default loaded

trigger:
  - action: HMI_BTN_START_AUTO.click()
  - timeout: 5s

expected_result:
  - DB_System.ModeState.iCurrentMode == 1 (AUTO)
  - DB_System.ModeState.iPackMLState == 3 (Execute)
  - DB_Sequence.iActiveStep > 0
  - HMI_LED_MODE.color == "#00C800" (green)

failure_conditions:
  - Timeout > 5s
  - Mode did not change
  - ALM0010 (Safety not OK) triggered

cleanup:
  - HMI_BTN_STOP.click()
  - Wait until Mode == M00 or M02

verification: automated (PLC trace)
```

---

## 4. Critical FAT Tests

### 4.1 Safety-Function FAT (most critical)

```yaml
TEST-FAT-SAFETY-001 (E-Stop Response Time):
  setup: Production cycle running (AUTO mode, motor running)
  trigger: Physical E-Stop button press (RED button)
  measure: 
    - Time from press → all motor outputs FALSE
    - Use oscilloscope or PLC trace with hi-res timestamp
  pass_criteria: 
    - response_time < 250ms (requirement)
    - All F_Q outputs cleared
  documentation:
    - Photo of the E-Stop button
    - Oscilloscope screenshot
    - Trace export
```

### 4.2 Mode-Transition FAT

```yaml
TEST-FAT-MODE-001 (M01 → M00 emergency):
  setup: AUTO mode active, production cycle running
  trigger: E-Stop press
  expected:
    - Mode → M00 within 100ms
    - All outputs in safe state
    - HMI shows red flashing alarm
  
TEST-FAT-MODE-002 (M00 → M01 recovery):
  setup: E-Stop active (M00), production stopped
  trigger: 
    1. Release E-Stop
    2. Press RESET button (HMI)
    3. Press AUTO button (HMI)
  expected:
    - Mode → M01 successfully
    - Alarm ALM0001 cleared
```

### 4.3 Communication FAT

```yaml
TEST-FAT-COMM-001 (PROFINET cable disconnect):
  setup: All systems running
  trigger: Disconnect PROFINET cable (ET200SP Station 1)
  expected:
    - Alarm ALM0042 within 200ms (watchdog)
    - Safe state for that station's outputs
    - HMI shows comm error
  recovery:
    - Reconnect cable
    - Alarm clears within 5s
```

### 4.4 Recipe-Management FAT

```yaml
TEST-FAT-RECIPE-001 (Recipe load + execute):
  setup: System in IDLE
  trigger:
    1. HMI → Recipe Management → Select "Recipe_Standard"
    2. Click LOAD
    3. Start AUTO cycle
  expected:
    - Recipe parameters propagated to all FB instances
    - Production runs with recipe-specific setpoints
```

---

## 5. FAT Deliverables

After FAT is complete, the following are delivered:

1. **FAT Test Report** (PDF + Excel)
   - Pass/fail for every test_id
   - Root cause + fix for failed tests
   - Re-test results

2. **PLC Trace Export** (for critical tests)
   - DB trace
   - Variable trace
   - Cycle-time measurements

3. **HMI Screenshot Package**
   - Active view of every screen
   - Alarm-trigger examples

4. **Safety Response-Time Report**
   - E-Stop response (oscilloscope)
   - Light curtain response
   - Safety-function FAT log

5. **Compliance Statement**
   - Which requirements were met (CE, TÜV)
   - Gaps and action plan

---

## 6. FAT Automation

Automated test generation via `04_AI_PROMPTS/test_gen/PROMPT_TEST_GEN_FAT.md`.

Modern test-framework integrations:
- **TIA Test Suite** (Siemens factory testing)
- **FactoryTalk Test** (Rockwell)
- **TwinCAT XAE TestRunner** (Beckhoff)
- **Python pytest** + PLC tag binding (vendor-agnostic)

```python
# Example pytest test
def test_estop_response_time(plc_connection):
    # Setup: AUTO mode running
    plc_connection.write("DB_HMI.bBtn_StartAuto", True)
    wait_until(lambda: plc_connection.read("DB_System.ModeState.iCurrentMode") == 1)
    
    # Trigger + measure
    t_start = time.perf_counter()
    plc_connection.write("F_I_EStop_Sim", False)  # E-Stop press simulation
    wait_until(lambda: not plc_connection.read("MOT_PUMP_01_OUT"))
    t_end = time.perf_counter()
    
    # Assert
    response_time_ms = (t_end - t_start) * 1000
    assert response_time_ms < 250, f"Response time {response_time_ms}ms > 250ms"
```

---

## 7. Pass/Fail Criteria

| Test Category | Pass Criteria |
|---------------|---------------|
| Safety | 100% pass — a SINGLE fail = FAT fail |
| Mode | 100% pass |
| Communication | 95%+ pass (intermittent comm issues acceptable but logged) |
| HMI | 95%+ pass |
| Recipe | 100% pass |
| Performance | 90%+ pass (load test) |

---

## 8. Post-FAT Actions

```
[FAT 100% pass]
       ↓
[Customer witness FAT (if planned)]
       ↓
[FAT report + sign-off]
       ↓
[Pack + Ship to site]
       ↓
[Site installation]
       ↓
[SAT (Site Acceptance Test) — DOMAIN_TESTING_SAT.md]
```

---

## 9. Related Files

- **AI prompt:** `04_AI_PROMPTS/test_gen/PROMPT_TEST_GEN_FAT.md`
- **RD spec:** `MDSCHEMA_RAWDATA_12_USECASE.md`
- **Pipeline:** Gate 7 (FAT/SAT)
- **SAT equivalent:** `DOMAIN_TESTING_SAT.md` (STUB; v3.1.0+)
- **Integration testing:** `DOMAIN_TESTING_INTEGRATION.md` (STUB)

---

## 10. Standards

- **IEC 61511-1** Section 13 (FAT/SAT for SIS)
- **ANSI/ISA-84.00.01** Functional safety: Safety instrumented systems
- **VDI/VDE 3814** Process control engineering testing
- **GAMP 5** Good Automated Manufacturing Practice (pharma)

---

*v1.1.0 — Full English body (2026-05-23). FAT domain standard. Customer witness FAT is done whenever possible — builds reputation + trust.*
