---
title: AI Prompt - Unit Test Scenarios
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [both]
prerequisite: [DOMAIN_TESTING_UNIT.md, MDSCHEMA_RAWDATA_10_FBSPEC.md]
target_ai: [Claude Sonnet 4+]
input_source: RD10_FBSpec.md (per FB)
output_artifacts: [unit_test_plan.md, unit_test_scripts/test_<fb>.py]
role: test_gen
schema: PROMPT_TEST_GEN
---

# PROMPT_TEST_GEN_UNIT.md — Unit Test Generation (per FB)

> **Generates independent (mocked) tests per FB.** The base of the test pyramid: fast, many, isolated.

---

## 1. When to Use?

- After Gate 5 code generation
- One test set per FB
- Runs automatically in the CI/CD pipeline

---

## 2. Test Template (per FB)

### Unit tests for FB_Motor

```python
import pytest
from plc_sim_mock import MockPLCInstance

class TestFB_Motor:
    """RD10 FB_Motor unit tests."""
    
    @pytest.fixture
    def fb_instance(self):
        """A clean FB instance for every test."""
        return MockPLCInstance("FB_Motor", initial_state={
            "stat_bInternalRunReq": False,
            "out_bRunning": False,
            "out_bFault": False
        })
    
    def test_start_when_safety_ok(self, fb_instance):
        """Safety OK + start cmd → motor should start."""
        fb_instance.set_input("in_bStartCmd", True)
        fb_instance.set_input("in_bSafetyOK", True)
        fb_instance.set_input("in_iMode", 1)  # AUTO
        
        fb_instance.cycle()  # 1 PLC cycle
        
        assert fb_instance.get_output("out_bRunning") == True
        assert fb_instance.get_output("out_bFault") == False
    
    def test_no_start_when_safety_not_ok(self, fb_instance):
        """Safety NOT OK → start cmd must be ignored."""
        fb_instance.set_input("in_bStartCmd", True)
        fb_instance.set_input("in_bSafetyOK", False)  # ⚠️
        fb_instance.set_input("in_iMode", 1)
        
        fb_instance.cycle()
        
        assert fb_instance.get_output("out_bRunning") == False
        assert fb_instance.get_output("out_bFault") == True
        assert fb_instance.get_output("out_iFaultCode") == 1
    
    def test_stop_when_emergency_mode(self, fb_instance):
        """Mode = M00 → motor stop."""
        # Start first
        fb_instance.set_input("in_bStartCmd", True)
        fb_instance.set_input("in_bSafetyOK", True)
        fb_instance.set_input("in_iMode", 1)
        fb_instance.cycle()
        assert fb_instance.get_output("out_bRunning") == True
        
        # Now M00
        fb_instance.set_input("in_iMode", 0)
        fb_instance.cycle()
        
        assert fb_instance.get_output("out_bRunning") == False
    
    def test_speed_ramp(self, fb_instance):
        """Speed ramp: 5% per cycle up, 10% per cycle down."""
        fb_instance.set_input("in_rSetSpeed", 50.0)
        fb_instance.set_input("in_bStartCmd", True)
        fb_instance.set_input("in_bSafetyOK", True)
        fb_instance.set_input("in_iMode", 1)
        
        # First cycle
        fb_instance.cycle()
        assert fb_instance.get_output("out_rActSpeed") == 5.0
        
        # After 10 cycles
        for _ in range(10):
            fb_instance.cycle()
        assert fb_instance.get_output("out_rActSpeed") == 50.0
    
    def test_runtime_counter(self, fb_instance):
        """Runtime counter must increase each PT cycle."""
        fb_instance.set_input("in_bStartCmd", True)
        fb_instance.set_input("in_bSafetyOK", True)
        fb_instance.set_input("in_iMode", 1)
        fb_instance.set_input("in_rSetSpeed", 100.0)
        
        for _ in range(5):
            fb_instance.cycle()
        
        # After multiple cycles it switches to running and runtime increases
        assert fb_instance.get_output("out_tRuntime") > 0
```

---

## 3. MockPLCInstance Structure

```python
# unit_test_scripts/plc_sim_mock.py
class MockPLCInstance:
    """SCL FB simulator — runs without a real PLC."""
    
    def __init__(self, fb_name, initial_state):
        self.inputs = {}
        self.outputs = {}
        self.stat = dict(initial_state)
        self.fb_name = fb_name
    
    def set_input(self, name, value):
        self.inputs[name] = value
    
    def get_output(self, name):
        return self.outputs.get(name)
    
    def cycle(self):
        """Run the FB logic for 1 PLC cycle."""
        # Either port the FB_Motor SCL logic into Python here,
        # or execute commands against a real PLC simulation
        self._execute_fb_logic()
```

---

## 4. Test Coverage Targets

| FB | Min tests | Coverage target |
|----|-----------|-----------------|
| FB_Motor | 5 | 85%+ |
| FB_Valve | 4 | 80%+ |
| FB_PID | 6 | 85%+ |
| FB_ModeMgr | 8 | 95%+ (critical) |
| FB_Sequence | 10 | 90%+ |
| F_FB_EStop | 6 | 100% (safety) |

---

## 5. Running

```bash
cd <project>/05_TESTS
pytest unit_test_scripts/ -v --cov=. --cov-report=html
```

---

## 6. Related Files

- **Domain:** `DOMAIN_TESTING_UNIT.md`
- **Source:** `MDSCHEMA_RAWDATA_10_FBSPEC.md`
- **Next:** `PROMPT_TEST_GEN_INTEGRATION.md`

---

*v1.1.0 — Full English body (2026-05-23). Unit tests give fast feedback. Should run on every commit in CI/CD.*
