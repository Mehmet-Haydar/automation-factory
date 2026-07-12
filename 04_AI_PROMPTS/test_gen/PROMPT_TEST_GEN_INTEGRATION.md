---
title: AI Prompt - Integration Test Scenarios
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [DOMAIN_TESTING_INTEGRATION.md, PROMPT_TEST_GEN_UNIT.md]
target_ai: [Claude Sonnet 4+]
input_source: RD03_Flowchart.md, RD04_Mode.md, RD10_FBSpec.md
output_artifacts: [integration_test_plan.md, integration_test_scripts/]
role: test_gen
schema: PROMPT_TEST_GEN
---

# PROMPT_TEST_GEN_INTEGRATION.md — Integration Test Generation

> **Multi-FB interaction tests.** After unit tests, before FAT. Validates the Sequence + Mode + Drive integration.

---

## 1. When to Use?

- During the Gate 6 SIMULATION stage
- After unit tests pass
- Before FAT, to validate that every FB works with the others

---

## 2. Test Scenarios

### A. Sequence + Mode Interaction
```python
def test_sequence_blocked_in_manual_mode(plc_sim):
    """RD03 + RD04 — Auto sequence must not start in MANUAL mode"""
    plc_sim.write("DB_System.ModeState.iCurrentMode", 2)  # MANUAL
    plc_sim.write("DB_HMI.bBtn_Cycle_Start", True)
    
    # Wait 3 seconds, sequence must not start
    time.sleep(3.0)
    assert plc_sim.read("DB_Sequence.iActiveStep") == 0
```

### B. Motor + Safety Interaction
```python
def test_motor_stops_on_estop(plc_sim):
    """RD05 + RD10 — E-Stop stops every motor"""
    setup_auto_running(plc_sim)
    
    plc_sim.write("F_I_EStop_North_Sim", False)
    time.sleep(0.5)
    
    assert not plc_sim.read("MOT_PUMP_01_OUT")
    assert not plc_sim.read("MOT_PUMP_02_OUT")
    assert not plc_sim.read("MOT_CONV_01_OUT")
```

### C. Recipe + Setpoint Propagation
```python
def test_recipe_load_propagates_setpoints(plc_sim):
    """RD02 + RD10 — Loading a recipe updates the FB instance setpoints"""
    plc_sim.write("DB_Recipe.iSelectedRecipe", 2)
    plc_sim.write("DB_HMI.bBtn_RecipeLoad", True)
    time.sleep(1.0)
    
    # In Recipe 2, Pump01 setpoint = 75%
    assert abs(plc_sim.read("DB_Mot_Pump01.rSetSpeed") - 75.0) < 0.1
```

### D. Comm + Alarm Interaction
```python
def test_comm_loss_triggers_alarm(plc_sim):
    """RD08 + RD09 — Comm watchdog → alarm + safe state"""
    setup_auto_running(plc_sim)
    
    plc_sim.simulate_comm_loss("PN_Station1")
    time.sleep(2.0)  # watchdog 500 ms × 3
    
    assert plc_sim.read("DB_Alarm.bAlarm_ALM0042")
    assert not plc_sim.read("MOT_CONV_01_OUT")  # safe state
```

---

## 3. PLC Simulation Environment

| Platform | Sim Tool |
|----------|----------|
| Siemens | PLCSIM Advanced (V18+) |
| Allen-Bradley | Emulate 5000 |
| Beckhoff | TwinCAT XAE Simulator |
| CODESYS | CODESYS Control Win SoftPLC |

---

## 4. Related Files

- **Domain:** `DOMAIN_TESTING_INTEGRATION.md`
- **Previous:** `PROMPT_TEST_GEN_UNIT.md`
- **Next:** `PROMPT_TEST_GEN_FAT.md`

---

*v1.1.0 — Full English body (2026-05-23). Integration tests fill the gap between unit tests and FAT.*
