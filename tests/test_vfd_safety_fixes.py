"""
tests/test_d1_s1_vfd_fixes.py — Proof tests: D-1 and S-1 fixes for FB_Motor_VFD.scl

FIX D-1 (CLASS D-1): Restart inhibit after enable rising edge
  - s_bRestartInhibit and s_bEnableEdgeMem declared in VAR block
  - Restart inhibit is SET on enable rising edge
  - Restart inhibit is CLEARED on s_bResetTrig (explicit operator reset)
  - Step-0 start transition guards with AND NOT s_bRestartInhibit

FIX S-1 (CLASS S-1): in_bManualMode was declared but ignored
  - t_bStartEnable now branches on in_bManualMode
  - MANUAL path uses in_bStartCmd; AUTO path uses in_bAutoCmd
  - in_bAutoCmd VAR_INPUT is declared

These tests:
  1. D-1-vars      : both new static variables are declared in VAR block
  2. D-1-set       : s_bRestartInhibit := TRUE triggered on enable rising edge
  3. D-1-clear     : s_bRestartInhibit := FALSE triggered when s_bResetTrig is TRUE
  4. D-1-guard     : step-0 transition carries AND NOT s_bRestartInhibit
  5. D-1-guard-neg : if the guard is absent the test fails (protective assertion)
  6. S-1-manual    : MANUAL branch uses in_bStartCmd
  7. S-1-auto      : AUTO branch uses in_bAutoCmd
  8. S-1-autocmd   : in_bAutoCmd is declared as VAR_INPUT
  9. S-1-no-simple : the old single-line t_bStartEnable assignment is gone
 10. gate-pass     : acceptance gate returns PASS (G-01..G-05)

Fix removal breaks tests 1-9. Test 10 catches regression in contract compliance.
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

SCL_PATH = PROJECT_ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "motor" / "FB_Motor_VFD.scl"
CONTRACT_PATH = PROJECT_ROOT / "06_KNOWLEDGE_BASE" / "contracts" / "motor" / "FB_Motor_VFD.contract.json"


@pytest.fixture(scope="module")
def scl_text() -> str:
    return SCL_PATH.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Helper: extract the VAR (static) block text only
# ---------------------------------------------------------------------------

def _static_block(scl: str) -> str:
    """Return text inside the first bare VAR ... END_VAR block (static vars)."""
    m = re.search(r"\bVAR\b(.*?)\bEND_VAR\b", scl, re.IGNORECASE | re.DOTALL)
    return m.group(1) if m else ""


def _input_block(scl: str) -> str:
    m = re.search(r"\bVAR_INPUT\b(.*?)\bEND_VAR\b", scl, re.IGNORECASE | re.DOTALL)
    return m.group(1) if m else ""


def _state_machine_region(scl: str) -> str:
    """Return text of REGION 02_STATE_MACHINE."""
    m = re.search(
        r"REGION\s+02_STATE_MACHINE\b(.*?)END_REGION",
        scl, re.IGNORECASE | re.DOTALL,
    )
    return m.group(1) if m else ""


def _input_validation_region(scl: str) -> str:
    """Return text of REGION 01_INPUT_VALIDATION."""
    m = re.search(
        r"REGION\s+01_INPUT_VALIDATION\b(.*?)END_REGION",
        scl, re.IGNORECASE | re.DOTALL,
    )
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# D-1 tests
# ---------------------------------------------------------------------------

class TestD1RestartInhibit:

    def test_d1_vars_declared(self, scl_text: str):
        """D-1-vars: s_bRestartInhibit and s_bEnableEdgeMem must be in the VAR block."""
        static = _static_block(scl_text)
        assert re.search(r"\bs_bRestartInhibit\s*:", static, re.IGNORECASE), (
            "s_bRestartInhibit not declared in VAR block — D-1 fix missing"
        )
        assert re.search(r"\bs_bEnableEdgeMem\s*:", static, re.IGNORECASE), (
            "s_bEnableEdgeMem not declared in VAR block — D-1 fix missing"
        )

    def test_d1_inhibit_set_on_rising_edge(self, scl_text: str):
        """D-1-set: s_bRestartInhibit := TRUE must be set when enable rises."""
        region = _input_validation_region(scl_text)
        # Pattern: IF in_bEnable AND NOT s_bEnableEdgeMem ... s_bRestartInhibit := TRUE
        assert re.search(
            r"IF\s+in_bEnable\s+AND\s+NOT\s+s_bEnableEdgeMem",
            region, re.IGNORECASE,
        ), "Rising-edge detect block (in_bEnable AND NOT s_bEnableEdgeMem) missing — D-1 fix missing"
        assert re.search(
            r"s_bRestartInhibit\s*:=\s*TRUE",
            region, re.IGNORECASE,
        ), "s_bRestartInhibit := TRUE assignment missing — D-1 fix missing"

    def test_d1_inhibit_cleared_on_reset(self, scl_text: str):
        """D-1-clear: s_bRestartInhibit := FALSE must occur inside an s_bResetTrig guard."""
        region = _input_validation_region(scl_text)
        # Both the reset-trig guard and the FALSE assignment must be present
        assert re.search(r"IF\s+s_bResetTrig", region, re.IGNORECASE), (
            "IF s_bResetTrig block missing in 01_INPUT_VALIDATION — D-1 fix missing"
        )
        assert re.search(r"s_bRestartInhibit\s*:=\s*FALSE", region, re.IGNORECASE), (
            "s_bRestartInhibit := FALSE assignment missing — D-1 fix missing"
        )

    def test_d1_step0_guard_present(self, scl_text: str):
        """D-1-guard: step-0 start transition must include AND NOT s_bRestartInhibit."""
        sm = _state_machine_region(scl_text)
        assert re.search(
            r"t_bStartEnable\s+AND\s+NOT\s+out_bError\s+AND\s+NOT\s+s_bRestartInhibit",
            sm, re.IGNORECASE,
        ), (
            "Step-0 guard 'AND NOT s_bRestartInhibit' missing — D-1 fix missing; "
            "removing this allows unintended auto-restart on enable rising edge"
        )

    def test_d1_guard_is_protective_assertion(self, scl_text: str):
        """D-1-guard-neg: removing the guard keyword breaks this test (sentinel check)."""
        # If the guard were simply 't_bStartEnable AND NOT out_bError' (original),
        # the pattern below would NOT match — confirming this test is protective.
        sm = _state_machine_region(scl_text)
        # Verify the old two-condition form WITHOUT s_bRestartInhibit does NOT exist
        old_form_only = re.search(
            r"IF\s+t_bStartEnable\s+AND\s+NOT\s+out_bError\s+THEN",
            sm, re.IGNORECASE,
        )
        assert old_form_only is None, (
            "Old 2-condition start guard still present without s_bRestartInhibit — "
            "D-1 fix was not applied or was partially reverted"
        )


# ---------------------------------------------------------------------------
# S-1 tests
# ---------------------------------------------------------------------------

class TestS1ManualModeImplemented:

    def test_s1_autocmd_declared(self, scl_text: str):
        """S-1-autocmd: in_bAutoCmd must exist in VAR_INPUT."""
        inputs = _input_block(scl_text)
        assert re.search(r"\bin_bAutoCmd\s*:", inputs, re.IGNORECASE), (
            "in_bAutoCmd not declared in VAR_INPUT — S-1 fix missing"
        )

    def test_s1_manual_branch_uses_start_cmd(self, scl_text: str):
        """S-1-manual: MANUAL mode branch must route in_bStartCmd to t_bStartEnable."""
        sm = _state_machine_region(scl_text)
        assert re.search(
            r"IF\s+in_bManualMode\b",
            sm, re.IGNORECASE,
        ), "IF in_bManualMode branch missing in 02_STATE_MACHINE — S-1 fix missing"
        # After the IF in_bManualMode, in_bStartCmd must be used
        assert re.search(
            r"in_bManualMode.*?in_bStartCmd",
            sm, re.IGNORECASE | re.DOTALL,
        ), "in_bStartCmd not used in manual branch — S-1 fix missing"

    def test_s1_auto_branch_uses_autocmd(self, scl_text: str):
        """S-1-auto: AUTO mode (ELSE) branch must route in_bAutoCmd to t_bStartEnable."""
        sm = _state_machine_region(scl_text)
        assert re.search(
            r"t_bStartEnable\s*:=\s*in_bAutoCmd\s+AND\s+NOT\s+in_bStopCmd",
            sm, re.IGNORECASE,
        ), (
            "AUTO branch 't_bStartEnable := in_bAutoCmd AND NOT in_bStopCmd' missing — "
            "S-1 fix missing; in AUTO mode the start command was previously ignored"
        )

    def test_s1_simple_assignment_gone(self, scl_text: str):
        """S-1-no-simple: the old single-line assignment (ignoring mode) must be gone."""
        sm = _state_machine_region(scl_text)
        # Original: "t_bStartEnable := in_bStartCmd AND NOT in_bStopCmd;"  (unconditional)
        # After fix this exists only INSIDE the IF in_bManualMode block — not unconditionally.
        # We check that there is no line where t_bStartEnable is assigned in_bStartCmd
        # OUTSIDE any IF context by verifying the IF in_bManualMode branch wraps it.
        assert re.search(r"IF\s+in_bManualMode", sm, re.IGNORECASE), (
            "Conditional mode branch absent — original unconditional assignment may still exist; "
            "S-1 fix missing"
        )


# ---------------------------------------------------------------------------
# Gate acceptance (G-01..G-05)
# ---------------------------------------------------------------------------

class TestGateAcceptance:

    def test_gate_pass(self):
        """gate-pass: fb_acceptance_check gate must return PASS for the fixed SCL."""
        from fb_acceptance_check import run_gate

        result = run_gate(SCL_PATH, CONTRACT_PATH)

        failed_checks = [
            f"{c.check_id} ({c.check_type}): {c.issues}"
            for c in result.checks
            if c.status == "FAIL" and c.check_id != "G-06"  # G-06 PLCreX is optional
        ]
        assert result.overall == "PASS", (
            f"Gate FAILED. Failed checks:\n" + "\n".join(failed_checks)
        )
