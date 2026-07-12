"""
tests/test_softstarter_safety_fixes.py — Proof tests for three safety fixes

FIX 1 (D-1): Restart inhibit after enable rising edge (explicit reset to clear).
FIX 2 (S-1): in_bManualMode routes to in_bStartCmd; AUTO mode routes to in_bAutoCmd.
FIX 3 (S-2): Stop guard in RAMP UP (step 10) — aborts ramp and returns to IDLE.

Each test is PROTECTIVE: if the fix is reverted the test FAILS.
Gate acceptance check (fb_acceptance_check PASS) is also included.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
sys.path.insert(0, str(_SCRIPTS))

from fb_acceptance_check import run_gate  # noqa: E402

SCL_PATH = (
    _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "motor" / "FB_Motor_SoftStarter.scl"
)
CONTRACT_PATH = (
    _ROOT
    / "06_KNOWLEDGE_BASE"
    / "contracts"
    / "motor"
    / "FB_Motor_SoftStarter.contract.json"
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _scl() -> str:
    return SCL_PATH.read_text(encoding="utf-8")


def _extract_region(scl: str, region_name: str) -> str:
    """Return text between REGION <name> and END_REGION."""
    pattern = re.compile(
        r"REGION\s+" + re.escape(region_name) + r"\b(.*?)END_REGION",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(scl)
    return m.group(1) if m else ""


def _extract_step_block(scl: str, step_label: str) -> str:
    """Return text from step_label up to the next step label or END_CASE.
    Does NOT stop at ELSE/END_IF — captures the full step body including inner branches."""
    pattern = re.compile(
        r"(" + re.escape(step_label) + r".*?)(?=\n\s+\d+:\s*//|\bEND_CASE\b)",
        re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(scl)
    return m.group(1) if m else ""


# ===========================================================================
# FIX 1 (D-1) — Restart inhibit
# ===========================================================================

class TestFix1RestartInhibit:

    def test_static_vars_declared(self):
        """s_bRestartInhibit and s_bEnableEdgeMem must be declared in VAR block."""
        scl = _scl()
        var_block = re.search(
            r"\bVAR\b(.*?)\bEND_VAR\b", scl, re.DOTALL | re.IGNORECASE
        )
        assert var_block, "VAR block not found"
        body = var_block.group(1)
        assert re.search(r"\bs_bRestartInhibit\s*:", body, re.IGNORECASE), (
            "s_bRestartInhibit not declared in VAR block — FIX 1 reverted"
        )
        assert re.search(r"\bs_bEnableEdgeMem\s*:", body, re.IGNORECASE), (
            "s_bEnableEdgeMem not declared in VAR block — FIX 1 reverted"
        )

    def test_enable_rising_edge_sets_inhibit(self):
        """REGION 01 must detect enable rising edge and set s_bRestartInhibit := TRUE."""
        scl = _scl()
        region = _extract_region(scl, "01_INPUT_VALIDATION")
        assert region, "REGION 01_INPUT_VALIDATION not found"
        # Must contain: IF in_bEnable AND NOT s_bEnableEdgeMem THEN ... s_bRestartInhibit := TRUE
        assert re.search(
            r"IF\s+in_bEnable\s+AND\s+NOT\s+s_bEnableEdgeMem", region, re.IGNORECASE
        ), "Enable rising-edge detection missing — FIX 1 reverted"
        assert re.search(
            r"s_bRestartInhibit\s*:=\s*TRUE", region, re.IGNORECASE
        ), "s_bRestartInhibit := TRUE not found in region 01 — FIX 1 reverted"

    def test_reset_clears_inhibit(self):
        """REGION 01 must clear s_bRestartInhibit when s_bResetTrig is TRUE."""
        scl = _scl()
        region = _extract_region(scl, "01_INPUT_VALIDATION")
        assert re.search(
            r"IF\s+s_bResetTrig.*?s_bRestartInhibit\s*:=\s*FALSE",
            region,
            re.DOTALL | re.IGNORECASE,
        ), (
            "s_bRestartInhibit := FALSE on reset not found in region 01 — FIX 1 reverted"
        )

    def test_step0_transition_guarded_by_inhibit(self):
        """Step 0 start transition must include AND NOT s_bRestartInhibit."""
        scl = _scl()
        step0 = _extract_step_block(scl, "0:  // IDLE")
        assert step0, "Step 0 (IDLE) block not found"
        assert re.search(
            r"AND\s+NOT\s+s_bRestartInhibit", step0, re.IGNORECASE
        ), (
            "AND NOT s_bRestartInhibit missing from step 0 transition — FIX 1 reverted"
        )

    def test_reset_trig_computed_before_inhibit_clear(self):
        """s_bResetTrig must be assigned before the inhibit-clear IF block (correct ordering)."""
        scl = _scl()
        region = _extract_region(scl, "01_INPUT_VALIDATION")
        pos_reset_trig = re.search(
            r"s_bResetTrig\s*:=\s*in_bReset\s+AND\s+NOT", region, re.IGNORECASE
        )
        pos_inhibit_clear = re.search(
            r"IF\s+s_bResetTrig.*?s_bRestartInhibit\s*:=\s*FALSE",
            region,
            re.DOTALL | re.IGNORECASE,
        )
        assert pos_reset_trig and pos_inhibit_clear, (
            "Could not locate both reset-trig assignment and inhibit-clear block"
        )
        assert pos_reset_trig.start() < pos_inhibit_clear.start(), (
            "s_bResetTrig must be computed BEFORE the inhibit-clear block — ordering bug"
        )


# ===========================================================================
# FIX 2 (S-1) — Manual/Auto mode routing
# ===========================================================================

class TestFix2ManualAutoMode:

    def test_in_bAutoCmd_declared(self):
        """in_bAutoCmd must be declared in VAR_INPUT."""
        scl = _scl()
        input_block_m = re.search(
            r"\bVAR_INPUT\b(.*?)\bEND_VAR\b", scl, re.DOTALL | re.IGNORECASE
        )
        assert input_block_m, "VAR_INPUT block not found"
        assert re.search(
            r"\bin_bAutoCmd\s*:", input_block_m.group(1), re.IGNORECASE
        ), "in_bAutoCmd not declared in VAR_INPUT — FIX 2 reverted"

    def test_manual_mode_uses_start_cmd(self):
        """When in_bManualMode, t_bStartEnable must be derived from in_bStartCmd."""
        scl = _scl()
        region = _extract_region(scl, "02_STATE_MACHINE")
        assert region, "REGION 02_STATE_MACHINE not found"
        # Look for: IF in_bManualMode THEN ... t_bStartEnable := in_bStartCmd ...
        assert re.search(
            r"IF\s+in_bManualMode.*?t_bStartEnable\s*:=\s*in_bStartCmd",
            region,
            re.DOTALL | re.IGNORECASE,
        ), "Manual mode path (in_bStartCmd) missing — FIX 2 reverted"

    def test_auto_mode_uses_auto_cmd(self):
        """In AUTO mode (ELSE branch), t_bStartEnable must come from in_bAutoCmd."""
        scl = _scl()
        region = _extract_region(scl, "02_STATE_MACHINE")
        # Look for: ELSE ... t_bStartEnable := in_bAutoCmd ...
        assert re.search(
            r"ELSE.*?t_bStartEnable\s*:=\s*in_bAutoCmd",
            region,
            re.DOTALL | re.IGNORECASE,
        ), "Auto mode path (in_bAutoCmd) missing — FIX 2 reverted"

    def test_unconditional_assignment_removed(self):
        """The old single-statement t_bStartEnable derivation (no IF/ELSE) must be gone.

        Old pattern was a SINGLE standalone assignment before any IF/ELSE block.
        New pattern wraps BOTH assignments inside IF in_bManualMode ... ELSE ... END_IF.
        Verify: an IF in_bManualMode block exists, meaning the assignment is conditional.
        """
        scl = _scl()
        region = _extract_region(scl, "02_STATE_MACHINE")
        # Must have the conditional IF in_bManualMode wrapper
        assert re.search(
            r"IF\s+in_bManualMode\b",
            region,
            re.IGNORECASE,
        ), (
            "IF in_bManualMode conditional wrapper missing — FIX 2 reverted or not applied"
        )
        # Must NOT have a bare (top-level) t_bStartEnable assignment that uses in_bAutoCmd
        # directly without any IF wrapper (i.e. auto-cmd must only appear inside the ELSE branch)
        # Best check: in_bAutoCmd appears exactly inside the ELSE branch of in_bManualMode
        manual_block_m = re.search(
            r"IF\s+in_bManualMode\b.*?END_IF\s*;",
            region,
            re.DOTALL | re.IGNORECASE,
        )
        assert manual_block_m, "IF in_bManualMode...END_IF block not found in region 02"
        assert re.search(
            r"in_bAutoCmd",
            manual_block_m.group(0),
            re.IGNORECASE,
        ), (
            "in_bAutoCmd not found inside IF in_bManualMode block — FIX 2 ELSE branch missing"
        )


# ===========================================================================
# FIX 3 (S-2) — Stop guard in RAMP UP
# ===========================================================================

class TestFix3StopGuardRampUp:

    def test_stop_guard_present_in_step10(self):
        """Step 10 must start with an IF NOT t_bStartEnable OR NOT in_bEnable guard."""
        scl = _scl()
        step10 = _extract_step_block(scl, "10: // RAMP UP")
        assert step10, "Step 10 (RAMP UP) block not found"
        assert re.search(
            r"IF\s+NOT\s+t_bStartEnable\s+OR\s+NOT\s+in_bEnable",
            step10,
            re.IGNORECASE,
        ), "Stop guard (IF NOT t_bStartEnable OR NOT in_bEnable) missing in step 10 — FIX 3 reverted"

    def test_stop_guard_aborts_to_step0(self):
        """Stop guard in step 10 must set s_nStep := 0 in the THEN branch."""
        scl = _scl()
        step10 = _extract_step_block(scl, "10: // RAMP UP")
        # Extract THEN branch: from THEN up to ELSE
        guard_then_m = re.search(
            r"IF\s+NOT\s+t_bStartEnable\s+OR\s+NOT\s+in_bEnable\s+THEN(.*?)\bELSE\b",
            step10,
            re.DOTALL | re.IGNORECASE,
        )
        assert guard_then_m, "Stop guard IF...THEN...ELSE structure not found in step 10 — FIX 3 reverted"
        guard_body = guard_then_m.group(1)
        assert re.search(r"s_nStep\s*:=\s*0", guard_body, re.IGNORECASE), (
            "s_nStep := 0 missing inside stop guard THEN branch — FIX 3 reverted"
        )
        assert re.search(r"out_bStartCmd\s*:=\s*FALSE", guard_body, re.IGNORECASE), (
            "out_bStartCmd := FALSE missing inside stop guard THEN branch — FIX 3 reverted"
        )

    def test_ramp_logic_in_else_branch(self):
        """Normal ramp logic (out_bStartCmd := TRUE) must be in ELSE branch, not executed on abort."""
        scl = _scl()
        step10 = _extract_step_block(scl, "10: // RAMP UP")
        else_m = re.search(
            r"\bELSE\b(.*?)\bEND_IF\b",
            step10,
            re.DOTALL | re.IGNORECASE,
        )
        assert else_m, "ELSE branch not found in step 10 — FIX 3 guard structure missing"
        else_body = else_m.group(1)
        assert re.search(r"out_bStartCmd\s*:=\s*TRUE", else_body, re.IGNORECASE), (
            "out_bStartCmd := TRUE not in ELSE branch — ramp-up body restructuring broken"
        )
        assert re.search(r"s_tonRampUp", else_body, re.IGNORECASE), (
            "s_tonRampUp call not in ELSE branch — ramp-up body restructuring broken"
        )

    def test_error_code_0010_still_in_step10(self):
        """Ramp-up timeout error code 16#0010 must still be present in step 10 ELSE branch.

        Uses greedy match to capture the full ELSE branch (which contains nested END_IFs).
        """
        scl = _scl()
        step10 = _extract_step_block(scl, "10: // RAMP UP")
        # The ELSE branch ends at the final END_IF; of the outer guard — use greedy DOTALL
        else_m = re.search(
            r"\bELSE\b(.*)\bEND_IF\b",
            step10,
            re.DOTALL | re.IGNORECASE,
        )
        assert else_m, "ELSE branch not found in step 10"
        assert re.search(r"16#0010", else_m.group(1), re.IGNORECASE), (
            "16#0010 (Ramp-up timeout) missing from step 10 ELSE branch"
        )


# ===========================================================================
# Gate acceptance check (all fixes combined)
# ===========================================================================

class TestGateAcceptance:

    def test_gate_passes(self):
        """fb_acceptance_check gate must PASS for FB_Motor_SoftStarter after all fixes."""
        assert SCL_PATH.exists(), f"SCL file not found: {SCL_PATH}"
        assert CONTRACT_PATH.exists(), f"Contract file not found: {CONTRACT_PATH}"

        result = run_gate(SCL_PATH, CONTRACT_PATH)
        failed = [
            f"{c.check_id} ({c.check_type}): {c.issues}"
            for c in result.checks
            if c.status == "FAIL"
        ]
        assert result.overall == "PASS", (
            "Gate expected PASS but returned FAIL.\nFailed checks:\n"
            + "\n".join(failed)
        )
