---
title: AI Prompt - FAT Test Procedure
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [DOMAIN_TESTING_FAT.md, MDSCHEMA_RAWDATA_12_USECASE.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+]
input_source: RD12_UseCase.md (rows with FATTestable=Y)
output_artifacts: [FAT_test_plan.md, FAT_test_scripts/test_*.py]
role: test_gen
schema: PROMPT_TEST_GEN
---

# PROMPT_TEST_GEN_FAT.md — Factory Acceptance Test Generation

> **This prompt automatically generates FAT test procedures and pytest-style test scripts from RD12 UseCases.** Gate 7 preparation.

---

## 1. When to Use?

- Gate 7 FAT preparation stage
- Converting `FATTestable=Y` use cases from RD12 into tests
- Test-plan generation for customer-witness FAT

---

## 2. System Prompt

```
You are a FAT test-plan generator. You take RD12 UseCases as input and produce
concrete test procedures and automation scripts.

TASK: for every FATTestable=Y use case, produce:
1. A test-plan markdown (read by engineer and customer)
2. A Python pytest script (for automation)

PYTEST TEMPLATE:
```python
import pytest
import time

def test_<usecase_id>_<usecase_name>(plc_conn):
    """RD12 UC<XXX> — <UseCaseName>"""
    
    # === PRECONDITION ===
    plc_conn.write("DB_System.bResetCmd", True)
    time.sleep(1.0)
    assert plc_conn.read("DB_System.ModeState.iCurrentMode") != 0
    
    # === TRIGGER ===
    t_start = time.perf_counter()
    plc_conn.write("DB_HMI.bBtn_AutoStart", True)
    
    # === ASSERT ===
    wait_until(lambda: plc_conn.read("DB_System.ModeState.iCurrentMode") == 1,
               timeout=3.0)
    t_elapsed = time.perf_counter() - t_start
    
    assert plc_conn.read("DB_System.ModeState.iCurrentMode") == 1
    assert plc_conn.read("DB_System.ModeState.iPackMLState") == 3
    assert t_elapsed < 3.0
    
    # === CLEANUP ===
    plc_conn.write("DB_HMI.bBtn_AutoStop", True)
```

MD TEMPLATE:
```markdown
## TEST-FAT-<UC_ID>-001 — <UseCaseName>

**Based on:** UC<XXX>
**Priority:** HIGH/MEDIUM/LOW
**Estimated time:** 5 min
**Automation:** YES (pytest)

### Precondition
- ...

### Test Steps
1. Setup: ...
2. Action: ...
3. Wait: ...

### Expected Result
- DB tag X = value Y
- HMI shows Z

### Pass/Fail Criteria
- ✓ Tag check pass
- ✓ Timing < Xms
- ✓ No unexpected alarms

### Cleanup
- ...

### Test Record
- Date: ___
- Tester: ___
- PLC Trace: attached
- Result: PASS / FAIL
- Notes: ___
```

OUTPUT:
- FAT_test_plan.md (engineer + customer presentation)
- FAT_test_scripts/test_<ucXXX>.py (one file per UC)
```

---

## 3. Critical Tests (Mandatory)

### E-Stop Response Time
```python
def test_estop_response_time(plc_conn):
    """UC010 — E-Stop response < 250 ms"""
    # Setup: AUTO running
    setup_auto_mode(plc_conn)
    
    # Trigger
    t = time.perf_counter()
    plc_conn.write("F_I_EStop_Sim", False)
    
    # Measure
    wait_until(lambda: not plc_conn.read("MOT_PUMP_01_OUT"),
               timeout=0.5)
    response_ms = (time.perf_counter() - t) * 1000
    
    assert response_ms < 250, f"Response {response_ms}ms > 250 ms target"
```

### Mode Transition
```python
def test_mode_transition_auto_to_manual(plc_conn):
    """UC002 — AUTO → MANUAL graceful"""
    setup_auto_mode(plc_conn)
    
    plc_conn.write("DB_HMI.bBtn_Manual", True)
    wait_until(lambda: plc_conn.read("DB_System.ModeState.iCurrentMode") == 2,
               timeout=3.0)
    
    assert plc_conn.read("DB_System.ModeState.iPackMLState") == 9  # Suspended
```

---

## 4. PLC Connection Layer

`FAT_test_scripts/conftest.py`:
```python
import pytest
from plc_connector import PLCConnector  # snap7 / pycomm3 / pyads

@pytest.fixture(scope="session")
def plc_conn():
    """PLC connection fixture."""
    conn = PLCConnector(ip="192.168.1.10", rack=0, slot=1)
    conn.connect()
    yield conn
    conn.disconnect()

def wait_until(condition, timeout=5.0, interval=0.05):
    """Helper: wait until a condition is met."""
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        if condition():
            return True
        time.sleep(interval)
    return False
```

---

## 5. Running

```bash
cd <project>/05_TESTS
pytest FAT_test_scripts/ -v --html=fat_report.html

# Specific test
pytest FAT_test_scripts/test_uc010_estop.py -v

# By marker (e.g. only safety)
pytest -m safety -v
```

---

## 6. Customer Presentation

FAT tests are performed with the customer as witness:
1. Test plan is sent to the customer in advance (for revision)
2. On FAT day, each test is executed in order
3. The customer signs off on each test result
4. The final FAT report is signed off as a PDF

---

## 7. Related Files

- **Domain:** `DOMAIN_TESTING_FAT.md`
- **Source:** `MDSCHEMA_RAWDATA_12_USECASE.md`
- **Pipeline:** Gate 7
- **Related test gen:** `PROMPT_TEST_GEN_UNIT.md`, `PROMPT_TEST_GEN_INTEGRATION.md`

---

*v1.1.0 — Full English body (2026-05-23). FAT = final check before customer acceptance. AI produces tests, engineer reviews them, customer signs off.*
