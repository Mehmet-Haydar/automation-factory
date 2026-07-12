---
title: AI Prompt - SCL Boundary & Stress Test Generation
version: 1.1.0
last_validated: 2026-05
last_updated: 2026-05-23
applies_to: [S7-1500, CODESYS, S7-300]
prerequisite: [RD01_IO_List.md, RD05_Safety.md, RD10_FB_Spec.md]
target_ai: [Claude Sonnet 4+, Claude Opus 4+]
input_source: RD01 + RD05 + generated SCL code
output_artifacts: [test_boundary_spec.md, plcsim_test_script.py]
role: test_gen
schema: PROMPT_TEST_GEN
---

# PROMPT_TEST_GEN_SCL_BOUNDARY.md — SCL Boundary & Stress Test Generation

> Includes IO boundary values, state-machine edge cases, and random-combination tests.

---

## 1. When to Use?

- After Gate 5 code generation is complete (all FBs ready)
- During the software-verification stage before FAT
- For regression testing after every major code change

---

## 2. System Prompt

```
You are an S7-1500 SCL test engineer. You write signal-forcing-based test
scenarios that run in the PLCSim Advanced environment.

TASK:
1. Produce comprehensive test scenarios using the project data below
2. Write a PLCSim Python API script per scenario
3. Specify expected outputs at the DB-variable level

RULES:
- Every test is independent (does not depend on the result of another)
- Safety tests are always present (E-stop, door interlock, reset)
- Analog tests: try 0, 27648, overflow (+1), negative values
- State machine: every state transition, every watchdog timeout must be tested
- Random/stress: rapid START/STOP spam, parallel alarms, power loss

TEST FORMATTING:
Use this structure for every test:

### T<XXX>: <Test Name>
**Category:** [IO_Boundary | Safety | StateMachine | Stress]
**Dependency:** <state any preceding test, otherwise "Independent">
**Initial Conditions:**
  - CPU: RUN
  - iState: <state number>
  - <other preconditions>

**Actions:**
  1. <signal = value>
  2. <wait duration>
  3. <check>

**Expected Result:**
  - <DB.variable> == <expected>
  - <DB.variable> == <expected>

**PLCSim Python:**
```python
def test_T<XXX>_<name>(plc):
    # PRECONDITION
    plc.write("DB_...", True/False/INT)
    # ACTION
    plc.write("DB_...", True/False/INT)
    time.sleep(X.X)
    # ASSERT
    assert plc.read("DB_...") == <expected>
```
```

---

## 3. User Prompt Template

```
Produce SCL boundary and stress test scenarios for the following project:

=== PROJECT META ===
Project: <project_name>
Platform: <S7-1515-2PN / etc.>
TIA version: <V18/V21>

=== IO LIST (RD01) ===
<contents of RD01_IO_List.md here>

=== SAFETY FUNCTIONS (RD05) ===
<contents or summary of RD05_Safety.md here>

=== FB STRUCTURE (RD10) ===
<FB names and responsibilities>

=== SCL CODE ===
<SCL code to be reviewed (or file names)>

=== TEST REQUIREMENTS ===
Minimum test categories:
1. Boundary test for every analog input (0, 27648, +1, -1)
2. Activation + reset test for every safety function
3. Every state transition + watchdog overrun in the state machine
4. At least 5 stress tests (random combinations)
5. Restart behaviour after a power loss

OUTPUT:
- test_boundary_spec.md (readable test plan)
- plcsim_test_script.py (automation-ready Python scripts)
```

---

## 4. Expected Output Structure

```
05_TESTS/
├── test_boundary_spec.md      ← output of this prompt
├── plcsim_scripts/
│   ├── test_runner.py         ← runs every test
│   ├── test_io_boundary.py    ← IO boundary tests
│   ├── test_safety.py         ← safety tests
│   ├── test_statemachine.py   ← SM tests
│   └── test_stress.py         ← stress tests
└── results/
    └── YYYY-MM-DD_test_log.md ← test results
```

---

## 5. Critical Checkpoints (When Reviewing AI Output)

The engineer checks the following:

```
□ Do the safety tests use NC logic correctly?
  (FALSE = active, TRUE = safe — can never be reversed)

□ Does the analog boundary test use 27648?
  (If 32767 appears, the AI mixed it up with S7-300 — reject)

□ Do the state-machine tests wait for the watchdog times?
  (For a T#30S watchdog, wait 31 seconds)

□ Are the stress tests realistic?
  (Every test must be manually reproducible in PLCSim)

□ Do the Python scripts contain comments?
  (What every block does must be clear)

□ Is test independence preserved?
  (Each test has its own setup/teardown)
```

---

## 6. Example Output — Partial (For Reference)

```markdown
### T001: Analog Pressure Sensor — Lower Limit
**Category:** IO_Boundary
**Dependency:** Independent

**Initial Conditions:**
  - CPU: RUN, iState: 0 (IDLE)
  - iHydraulicPressureRaw: 13824 (nominal)

**Actions:**
  1. Write iHydraulicPressureRaw = 0
  2. Wait 2 scan cycles (20 ms)
  3. Read DB_Inputs.rHydraulicPressure_Bar

**Expected Result:**
  - DB_Inputs.rHydraulicPressure_Bar == 0.0
  - DB_Hydraulic.xHydraulicReady == FALSE (pressure < 120 bar)
  - DB_Hydraulic.iHydraulicFault == 21 (low-pressure alarm)

**PLCSim Python:**
```python
def test_T001_analog_pressure_lower_limit(plc):
    plc.write_int("DB_Inputs", "iHydraulicPressureRaw", 0)
    time.sleep(0.02)
    assert abs(plc.read_real("DB_Inputs", "rHydraulicPressure_Bar") - 0.0) < 0.1
    assert plc.read_bool("DB_Hydraulic", "xHydraulicReady") == False
    assert plc.read_int("DB_Hydraulic", "iHydraulicFault") == 21
```
```

---

*v1.1.0 — Full English body (2026-05-23). test_gen series. Complementary to fat_protocol.py: this prompt has the AI write test scenarios, fat_protocol.py produces the automated skeleton.*
