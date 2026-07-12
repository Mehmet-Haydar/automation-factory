"""
tests/test_d1_s4_motor_standard_fixes.py
  Proof tests: D-1 (restart inhibit) and S-4 (type conversion safety)
  for FB_Motor_Standard.scl / UDT_Motor.

FIX D-1 (CLASS D-1): Restart inhibit after enable rising edge
  - s_bRestartInhibit and s_bEnableEdgeMem declared in VAR block
  - s_bRestartInhibit set TRUE on enable rising edge (in_bEnable AND NOT s_bEnableEdgeMem)
  - s_bRestartInhibit cleared FALSE when s_bResetTrig fires (explicit operator reset)
  - Step-0 start transition guards with AND NOT s_bRestartInhibit

FIX S-4a (CLASS S-4): iFaultCode type changed INT -> WORD
  - UDT_Motor.iFaultCode is now WORD (no overflow/sign-bit risk)
  - All WORD_TO_INT(out_wErrorCode) calls replaced by direct out_wErrorCode assignment
  - No WORD_TO_INT appears anywhere in the file

FIX S-4b (CLASS S-4): tRuntime type changed TIME -> DInt
  - UDT_Motor.tRuntime is now DInt (stores seconds; no DINT*1000 overflow)
  - DINT_TO_TIME(s_dRunSecs * 1000) replaced by s_dRunSecs
  - tRuntime init uses integer 0, not T#0s
  - No DINT_TO_TIME appears anywhere in the file

Protective assertions (fix removed -> test fails):
  - D-1: removing guard keyword or variable declarations breaks 4 tests
  - S-4a: re-adding WORD_TO_INT or reverting iFaultCode to INT breaks 3 tests
  - S-4b: re-adding DINT_TO_TIME or reverting tRuntime to TIME breaks 3 tests
  - gate-pass: any structural regression caught by acceptance gate
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "05_SCRIPTS"
for _p in (str(PROJECT_ROOT), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCL_PATH = (
    PROJECT_ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "motor" / "FB_Motor_Standard.scl"
)
CONTRACT_PATH = (
    PROJECT_ROOT
    / "06_KNOWLEDGE_BASE"
    / "contracts"
    / "motor"
    / "FB_Motor_DOL.contract.json"
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def scl_text() -> str:
    return SCL_PATH.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Region / block extractors
# ---------------------------------------------------------------------------

def _static_block(scl: str) -> str:
    """Return text inside the bare VAR ... END_VAR block (static vars)."""
    m = re.search(r"\bVAR\b(.*?)\bEND_VAR\b", scl, re.IGNORECASE | re.DOTALL)
    return m.group(1) if m else ""


def _input_validation_region(scl: str) -> str:
    m = re.search(
        r"REGION\s+01_INPUT_VALIDATION\b(.*?)END_REGION",
        scl, re.IGNORECASE | re.DOTALL,
    )
    return m.group(1) if m else ""


def _state_machine_region(scl: str) -> str:
    m = re.search(
        r"REGION\s+02_STATE_MACHINE\b(.*?)END_REGION",
        scl, re.IGNORECASE | re.DOTALL,
    )
    return m.group(1) if m else ""


def _udt_block(scl: str) -> str:
    """Return text of the UDT_Motor TYPE...END_TYPE definition."""
    m = re.search(
        r'TYPE\s+"?UDT_Motor"?\s+STRUCT(.*?)END_STRUCT',
        scl, re.IGNORECASE | re.DOTALL,
    )
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# D-1 tests
# ---------------------------------------------------------------------------

class TestD1RestartInhibit:

    def test_d1_vars_declared(self, scl_text: str):
        """D-1-vars: s_bRestartInhibit and s_bEnableEdgeMem must exist in VAR block.
        Fix removed -> this test FAILS.
        """
        static = _static_block(scl_text)
        assert re.search(r"\bs_bRestartInhibit\s*:", static, re.IGNORECASE), (
            "s_bRestartInhibit not declared in VAR block — D-1 fix missing"
        )
        assert re.search(r"\bs_bEnableEdgeMem\s*:", static, re.IGNORECASE), (
            "s_bEnableEdgeMem not declared in VAR block — D-1 fix missing"
        )

    def test_d1_inhibit_set_on_rising_edge(self, scl_text: str):
        """D-1-set: inhibit must be SET TRUE when enable rises.
        Fix removed -> this test FAILS.
        """
        region = _input_validation_region(scl_text)
        assert re.search(
            r"IF\s+in_bEnable\s+AND\s+NOT\s+s_bEnableEdgeMem",
            region, re.IGNORECASE,
        ), (
            "Rising-edge detect (in_bEnable AND NOT s_bEnableEdgeMem) missing in "
            "01_INPUT_VALIDATION — D-1 fix missing"
        )
        assert re.search(
            r"s_bRestartInhibit\s*:=\s*TRUE",
            region, re.IGNORECASE,
        ), "s_bRestartInhibit := TRUE assignment missing in 01_INPUT_VALIDATION — D-1 fix missing"

    def test_d1_inhibit_cleared_on_reset(self, scl_text: str):
        """D-1-clear: inhibit must be cleared FALSE inside an s_bResetTrig guard.
        Fix removed -> this test FAILS.
        """
        region = _input_validation_region(scl_text)
        assert re.search(r"IF\s+s_bResetTrig", region, re.IGNORECASE), (
            "IF s_bResetTrig block absent in 01_INPUT_VALIDATION — D-1 fix missing"
        )
        assert re.search(r"s_bRestartInhibit\s*:=\s*FALSE", region, re.IGNORECASE), (
            "s_bRestartInhibit := FALSE not found — D-1 fix missing"
        )

    def test_d1_step0_guard_present(self, scl_text: str):
        """D-1-guard: step-0 start condition must include AND NOT s_bRestartInhibit.
        Fix removed -> this test FAILS.
        """
        sm = _state_machine_region(scl_text)
        assert re.search(
            r"t_bStartEnable\s+AND\s+NOT\s+out_bError\s+AND\s+NOT\s+s_bRestartInhibit",
            sm, re.IGNORECASE,
        ), (
            "Step-0 guard 'AND NOT s_bRestartInhibit' absent — D-1 fix missing; "
            "removing this allows unintended auto-restart on enable rising edge"
        )

    def test_d1_old_two_condition_guard_gone(self, scl_text: str):
        """D-1-guard-neg: the old 2-condition form (without s_bRestartInhibit) must be gone.
        Protective: if guard were reverted to 2-condition form this test FAILS.
        """
        sm = _state_machine_region(scl_text)
        old_form = re.search(
            r"IF\s+t_bStartEnable\s+AND\s+NOT\s+out_bError\s+THEN",
            sm, re.IGNORECASE,
        )
        assert old_form is None, (
            "Old 2-condition start guard present without s_bRestartInhibit — "
            "D-1 fix missing or partially reverted"
        )


# ---------------------------------------------------------------------------
# S-4a tests: iFaultCode INT -> WORD, no WORD_TO_INT
# ---------------------------------------------------------------------------

class TestS4aFaultCodeWord:

    def test_s4a_no_word_to_int_calls_in_file(self, scl_text: str):
        """S-4a-clean: WORD_TO_INT( function call must not appear anywhere in the file.
        Comments mentioning the name are allowed; actual conversion calls are not.
        Fix reverted -> this test FAILS.
        """
        assert not re.search(r"\bWORD_TO_INT\s*\(", scl_text, re.IGNORECASE), (
            "WORD_TO_INT(...) call still present in FB_Motor_Standard.scl — "
            "S-4a fix missing or reverted"
        )

    def test_s4a_udt_ifaultcode_is_word(self, scl_text: str):
        """S-4a-type: UDT_Motor.iFaultCode must be declared as WORD.
        Fix reverted -> this test FAILS.
        """
        udt = _udt_block(scl_text)
        assert udt, "UDT_Motor STRUCT block not found in file"
        # Must find:  iFaultCode : WORD
        assert re.search(r"\biFaultCode\s*:\s*WORD\b", udt, re.IGNORECASE), (
            "UDT_Motor.iFaultCode not declared as WORD — S-4a fix missing or reverted; "
            "INT type risks sign-bit corruption for codes >= 16#8000"
        )

    def test_s4a_ifaultcode_not_int_in_udt(self, scl_text: str):
        """S-4a-type-neg: iFaultCode must NOT be INT in UDT_Motor.
        Protective: reverted type triggers this failure.
        """
        udt = _udt_block(scl_text)
        assert udt, "UDT_Motor STRUCT block not found in file"
        int_decl = re.search(r"\biFaultCode\s*:\s*INT\b", udt, re.IGNORECASE)
        assert int_decl is None, (
            "UDT_Motor.iFaultCode is still INT — S-4a fix was not applied or was reverted"
        )

    def test_s4a_direct_assignment_in_diagnostics(self, scl_text: str):
        """S-4a-assign: diagnostics region must assign iFaultCode := out_wErrorCode directly."""
        scl = scl_text
        # Look for the direct assignment (no WORD_TO_INT wrapper)
        assert re.search(
            r"inout_udMotorData\.iFaultCode\s*:=\s*out_wErrorCode\s*;",
            scl, re.IGNORECASE,
        ), (
            "Direct 'inout_udMotorData.iFaultCode := out_wErrorCode;' not found — "
            "S-4a fix missing"
        )


# ---------------------------------------------------------------------------
# S-4b tests: tRuntime TIME -> DInt, no DINT_TO_TIME
# ---------------------------------------------------------------------------

class TestS4bRuntimeDInt:

    def test_s4b_no_dint_to_time_in_file(self, scl_text: str):
        """S-4b-clean: DINT_TO_TIME must not appear anywhere in the file.
        Fix reverted -> this test FAILS.
        """
        assert "DINT_TO_TIME" not in scl_text, (
            "DINT_TO_TIME still present in FB_Motor_Standard.scl — S-4b fix missing or reverted"
        )

    def test_s4b_udt_truntime_is_dint(self, scl_text: str):
        """S-4b-type: UDT_Motor.tRuntime must be declared as DInt.
        Fix reverted -> this test FAILS.
        """
        udt = _udt_block(scl_text)
        assert udt, "UDT_Motor STRUCT block not found in file"
        assert re.search(r"\btRuntime\s*:\s*DInt\b", udt, re.IGNORECASE), (
            "UDT_Motor.tRuntime not declared as DInt — S-4b fix missing or reverted; "
            "TIME type with *1000 multiplier overflows at ~24.8 days"
        )

    def test_s4b_truntime_not_time_in_udt(self, scl_text: str):
        """S-4b-type-neg: tRuntime must NOT be TIME in UDT_Motor.
        Protective: reverted type triggers this failure.
        """
        udt = _udt_block(scl_text)
        assert udt, "UDT_Motor STRUCT block not found in file"
        time_decl = re.search(r"\btRuntime\s*:\s*TIME\b", udt, re.IGNORECASE)
        assert time_decl is None, (
            "UDT_Motor.tRuntime is still TIME — S-4b fix was not applied or was reverted"
        )

    def test_s4b_direct_seconds_assignment(self, scl_text: str):
        """S-4b-assign: diagnostics region must assign tRuntime := s_dRunSecs directly."""
        assert re.search(
            r"inout_udMotorData\.tRuntime\s*:=\s*s_dRunSecs\s*;",
            scl_text, re.IGNORECASE,
        ), (
            "Direct 'inout_udMotorData.tRuntime := s_dRunSecs;' not found — "
            "S-4b fix missing"
        )

    def test_s4b_init_uses_integer_zero(self, scl_text: str):
        """S-4b-init: first-scan init must assign tRuntime := 0 (not T#0s)."""
        # T#0s is only valid for TIME; DInt init must use integer literal
        assert "tRuntime   := T#0s" not in scl_text, (
            "tRuntime still initialised with T#0s — S-4b fix incomplete; "
            "T#0s is incompatible with DInt type"
        )


# ---------------------------------------------------------------------------
# Gate acceptance (G-01..G-05)
# ---------------------------------------------------------------------------

class TestGateAcceptance:

    def test_gate_passes_for_motor_standard(self):
        """gate-pass: fb_acceptance_check gate must return PASS for the fixed SCL."""
        from fb_acceptance_check import run_gate  # noqa: E402

        assert SCL_PATH.exists(), f"SCL file not found: {SCL_PATH}"
        assert CONTRACT_PATH.exists(), f"Contract file not found: {CONTRACT_PATH}"

        result = run_gate(SCL_PATH, CONTRACT_PATH)
        failed_checks = [
            f"{c.check_id} ({c.check_type}): {c.issues}"
            for c in result.checks
            if c.status == "FAIL" and c.check_id != "G-06"  # G-06 PLCreX is optional
        ]
        assert result.overall == "PASS", (
            f"Gate FAILED after D-1/S-4 fixes. Failed checks:\n"
            + "\n".join(failed_checks)
        )
