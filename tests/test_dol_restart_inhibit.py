"""
tests/test_d1_dol_restart_inhibit.py  —  Class D-1 Proof Tests
                                          Restart Inhibit After Enable Rising Edge

Fix target: FB_Motor_DOL.scl
  - s_bRestartInhibit / s_bEnableEdgeMem added to VAR block
  - Enable rising-edge inhibit block inserted at start of REGION 01_INPUT_VALIDATION
  - Step-0 start transition: AND NOT s_bRestartInhibit added

Test design (fail-closed):
  - PASS when fix is present.
  - BREAK when fix is removed (proof, not smoke).
  - Acceptance gate must still report PASS (no gate regression).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT     = Path(__file__).parent.parent
_DOL_SCL  = _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "motor" / "FB_Motor_DOL.scl"
_CONTRACT = _ROOT / "06_KNOWLEDGE_BASE" / "contracts" / "motor" / "FB_Motor_DOL.contract.json"
_SCRIPTS  = _ROOT / "05_SCRIPTS"


def _read_dol() -> str:
    return _DOL_SCL.read_text(encoding="utf-8")


def _var_block(scl: str) -> str:
    """Return text of the static VAR ... END_VAR block."""
    m = re.search(r"\bVAR\b(?!_)(.*?)\bEND_VAR\b", scl, re.DOTALL | re.IGNORECASE)
    assert m, "VAR block not found — file structure broken"
    return m.group(1)


def _code_lines(scl: str) -> str:
    """Strip full-line comments; return joined code."""
    return "\n".join(
        line for line in scl.splitlines()
        if not line.strip().startswith("//")
    )


# ---------------------------------------------------------------------------
# VAR block — new variables declared
# ---------------------------------------------------------------------------

class TestNewVarsDeclared:
    """Both new static variables must appear in the VAR block."""

    def test_s_bRestartInhibit_declared(self):
        """
        s_bRestartInhibit : Bool must be in the VAR block.
        BREAKS if the declaration is removed (fix reverted).
        """
        var_text = _var_block(_read_dol())
        assert re.search(r"\bs_bRestartInhibit\s*:", var_text, re.IGNORECASE), (
            "D-1 FIX REVERTED: s_bRestartInhibit not found in VAR block. "
            "Restart-inhibit feature requires this static variable."
        )

    def test_s_bEnableEdgeMem_declared(self):
        """
        s_bEnableEdgeMem : Bool must be in the VAR block.
        BREAKS if the declaration is removed (fix reverted).
        """
        var_text = _var_block(_read_dol())
        assert re.search(r"\bs_bEnableEdgeMem\s*:", var_text, re.IGNORECASE), (
            "D-1 FIX REVERTED: s_bEnableEdgeMem not found in VAR block. "
            "Enable-edge detection requires this static variable."
        )

    def test_both_vars_are_bool_type(self):
        """Both new variables must be declared as Bool."""
        var_text = _var_block(_read_dol())
        for var_name in ("s_bRestartInhibit", "s_bEnableEdgeMem"):
            m = re.search(
                rf"\b{var_name}\s*:\s*(\w+)", var_text, re.IGNORECASE
            )
            assert m, f"{var_name} declaration not found in VAR block"
            assert m.group(1).lower() == "bool", (
                f"{var_name} must be declared as Bool, found: {m.group(1)!r}"
            )


# ---------------------------------------------------------------------------
# REGION 01_INPUT_VALIDATION — inhibit logic present
# ---------------------------------------------------------------------------

class TestInhibitLogicInRegion01:
    """
    The enable rising-edge detection and inhibit block must appear inside
    REGION 01_INPUT_VALIDATION, before (or alongside) the reset-trig logic.
    """

    def _region01_text(self) -> str:
        scl = _read_dol()
        m = re.search(
            r"\bREGION\s+01_INPUT_VALIDATION\b(.*?)\bEND_REGION\b",
            scl, re.DOTALL | re.IGNORECASE,
        )
        assert m, "REGION 01_INPUT_VALIDATION not found"
        return m.group(1)

    def test_enable_rising_edge_detection_present(self):
        """
        'IF in_bEnable AND NOT s_bEnableEdgeMem' must appear in REGION 01.
        BREAKS if the enable-edge detection block is removed.
        """
        region = self._region01_text()
        assert re.search(
            r"IF\s+in_bEnable\s+AND\s+NOT\s+s_bEnableEdgeMem",
            region, re.IGNORECASE,
        ), (
            "D-1 FIX REVERTED: Enable rising-edge detection "
            "'IF in_bEnable AND NOT s_bEnableEdgeMem' not found in REGION 01_INPUT_VALIDATION."
        )

    def test_inhibit_set_on_enable_edge(self):
        """
        s_bRestartInhibit := TRUE must appear inside the enable-edge IF block.
        BREAKS if the inhibit-set assignment is removed.
        """
        region = self._region01_text()
        assert re.search(
            r"s_bRestartInhibit\s*:=\s*TRUE",
            region, re.IGNORECASE,
        ), (
            "D-1 FIX REVERTED: 's_bRestartInhibit := TRUE' not found in REGION 01. "
            "Inhibit must be set when enable rises."
        )

    def test_enable_edge_memory_updated(self):
        """
        s_bEnableEdgeMem := in_bEnable must appear in REGION 01.
        BREAKS if the edge-memory update is removed.
        """
        region = self._region01_text()
        assert re.search(
            r"s_bEnableEdgeMem\s*:=\s*in_bEnable",
            region, re.IGNORECASE,
        ), (
            "D-1 FIX REVERTED: 's_bEnableEdgeMem := in_bEnable' not found in REGION 01. "
            "Edge memory must be updated every scan."
        )

    def test_inhibit_cleared_on_reset_trig(self):
        """
        s_bRestartInhibit := FALSE inside an IF s_bResetTrig block in REGION 01.
        BREAKS if the inhibit-clear is removed.
        """
        region = self._region01_text()
        assert re.search(
            r"s_bRestartInhibit\s*:=\s*FALSE",
            region, re.IGNORECASE,
        ), (
            "D-1 FIX REVERTED: 's_bRestartInhibit := FALSE' not found in REGION 01. "
            "Inhibit must be cleared on operator reset."
        )

    def test_inhibit_cleared_guarded_by_reset_trig(self):
        """
        The FALSE assignment must be guarded by 'IF s_bResetTrig'.
        BREAKS if the guard condition is removed.
        """
        region = self._region01_text()
        # Find IF s_bResetTrig ... s_bRestartInhibit := FALSE pattern
        assert re.search(
            r"IF\s+s_bResetTrig\b.*?s_bRestartInhibit\s*:=\s*FALSE",
            region, re.IGNORECASE | re.DOTALL,
        ), (
            "D-1 FIX REVERTED: inhibit clear is not guarded by 'IF s_bResetTrig'. "
            "Inhibit must only clear on a rising-edge reset, not unconditionally."
        )


# ---------------------------------------------------------------------------
# Step 0 (IDLE) — start transition guarded by inhibit
# ---------------------------------------------------------------------------

class TestStep0StartTransitionGuarded:
    """
    The IDLE -> STARTING transition (step 0) must include AND NOT s_bRestartInhibit.
    """

    def test_step0_transition_has_inhibit_guard(self):
        """
        't_bStartEnable AND NOT out_bError AND NOT s_bRestartInhibit' in step 0.
        BREAKS if AND NOT s_bRestartInhibit is removed from the transition.
        """
        code = _code_lines(_read_dol())
        assert re.search(
            r"t_bStartEnable\s+AND\s+NOT\s+out_bError\s+AND\s+NOT\s+s_bRestartInhibit",
            code, re.IGNORECASE,
        ), (
            "D-1 FIX REVERTED: step-0 start transition does not include "
            "'AND NOT s_bRestartInhibit'. Motor can restart without operator reset."
        )

    def test_step0_transition_blocked_without_inhibit_flag_in_scl(self):
        """
        Negative: if s_bRestartInhibit is removed from the transition condition
        entirely, a plain 't_bStartEnable AND NOT out_bError' without inhibit guard
        must NOT exist in the IDLE case block.

        This test is the 'break-if-reverted' twin of the positive test above.
        It passes when the inhibit guard IS present; it would fail (as expected)
        if someone only kept 't_bStartEnable AND NOT out_bError' without the extra guard.
        """
        code = _code_lines(_read_dol())
        # The FULL condition with the guard must exist — we already tested that.
        # Here we additionally confirm there is no rogue bare condition without the guard.
        bare_condition = re.search(
            r"IF\s+t_bStartEnable\s+AND\s+NOT\s+out_bError\s*THEN",
            code, re.IGNORECASE,
        )
        assert not bare_condition, (
            "D-1 FIX PARTIALLY REVERTED: found 'IF t_bStartEnable AND NOT out_bError THEN' "
            "without the restart-inhibit guard. The transition must include "
            "'AND NOT s_bRestartInhibit'."
        )


# ---------------------------------------------------------------------------
# Acceptance gate — no regression
# ---------------------------------------------------------------------------

class TestAcceptanceGateStillPasses:
    """
    After D-1 fix, FB_Motor_DOL.scl must still pass the full acceptance gate.
    Any gate regression (missing required port, broken region, etc.) is caught here.
    """

    def _gate_result(self):
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import run_gate
        return run_gate(_DOL_SCL, _CONTRACT)

    def test_overall_pass(self):
        """G-01..G-05 must all PASS after D-1 changes."""
        result = self._gate_result()
        failures = [c for c in result.checks if c.status == "FAIL" and c.check_id != "G-06"]
        assert result.overall == "PASS", (
            "FB_Motor_DOL acceptance gate FAIL after D-1 fix.\n"
            + "\n".join(f"  {c.check_id}: {c.issues}" for c in failures)
        )

    def test_label_auto_verified(self):
        """Gate label must contain AUTO_VERIFIED."""
        result = self._gate_result()
        assert "AUTO_VERIFIED" in result.label, (
            f"Expected 'AUTO_VERIFIED' in gate label, found: {result.label!r}"
        )

    def test_interface_check_passes(self):
        """G-02: All required ports still present with correct IEC types."""
        import json
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import check_interface
        scl = _DOL_SCL.read_text(encoding="utf-8")
        contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
        cr = check_interface(scl, contract)
        assert cr.status == "PASS", f"Interface check failed after D-1: {cr.issues}"

    def test_behaviors_pass(self):
        """G-03: All MUST behavioral patterns still present."""
        import json
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import check_behaviors
        scl = _DOL_SCL.read_text(encoding="utf-8")
        contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
        cr = check_behaviors(scl, contract)
        must_fails = [i for i in cr.issues if not i.startswith("[SHOULD]")]
        assert not must_fails, f"Behavior MUST failures after D-1: {must_fails}"

    def test_structural_check_passes(self):
        """G-01: SCL structural balance (IF/END_IF, VAR/END_VAR, etc.) must pass."""
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import check_structural
        scl = _DOL_SCL.read_text(encoding="utf-8")
        cr = check_structural(scl)
        assert cr.status in ("PASS", "WARN"), (
            f"Structural check FAIL after D-1: {cr.issues}"
        )
