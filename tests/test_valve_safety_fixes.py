"""
tests/test_valve_safety_fixes.py — Proof tests for two safety fixes on both valve FBs

FIX 1 (CLASS C): in_bSpringReturn parameter
  - Added to VAR_INPUT of FB_Valve_OnOff and FB_Valve_3Way.
  - Step 0 (IDLE) and step 99 (FAULT) output-deassert is wrapped with:
      IF in_bSpringReturn THEN ... END_IF
  - Bistable valves (in_bSpringReturn=FALSE) retain last state on idle/fault.

FIX 2 (CLASS S-1): in_bManualMode implemented
  - Added in_bAutoOpenCmd / in_bAutoCloseCmd (OnOff) and
    in_bAutoPositionACmd / in_bAutoPositionBCmd (3Way) to VAR_INPUT.
  - Manual/auto routing block in REGION 02 routes effective commands through
    temp vars; CASE transitions use routed temps, not raw inputs.

Each test is PROTECTIVE: if the fix is reverted the test FAILS.
Gate acceptance check (fb_acceptance_check PASS) is also included for each FB.
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

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

ONOFF_SCL = (
    _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "valve" / "FB_Valve_OnOff.scl"
)
ONOFF_CONTRACT = (
    _ROOT / "06_KNOWLEDGE_BASE" / "contracts" / "valve" / "FB_Valve_OnOff.contract.json"
)

THREEWAY_SCL = (
    _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "valve" / "FB_Valve_3Way.scl"
)
THREEWAY_CONTRACT = (
    _ROOT / "06_KNOWLEDGE_BASE" / "contracts" / "valve" / "FB_Valve_3Way.contract.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scl(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_var_block(scl: str, section: str) -> str:
    """Return text inside the first matching VAR_xxx ... END_VAR block."""
    m = re.search(
        r"\b" + re.escape(section) + r"\b(.*?)\bEND_VAR\b",
        scl,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1) if m else ""


def _extract_region(scl: str, region_name: str) -> str:
    """Return text between REGION <name> and END_REGION."""
    m = re.search(
        r"REGION\s+" + re.escape(region_name) + r"\b(.*?)END_REGION",
        scl,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1) if m else ""


def _extract_step_block(scl: str, step_label: str) -> str:
    """Return text from step_label up to the next step label or END_CASE."""
    m = re.search(
        r"(" + re.escape(step_label) + r".*?)(?=\n\s+\d+:\s*//|\bEND_CASE\b)",
        scl,
        re.DOTALL | re.IGNORECASE,
    )
    return m.group(1) if m else ""


# ===========================================================================
# FB_Valve_OnOff — FIX 1 (CLASS C): in_bSpringReturn
# ===========================================================================

class TestOnOffFix1SpringReturn:

    def test_spring_return_declared_in_input(self):
        """in_bSpringReturn must be declared in VAR_INPUT with default TRUE."""
        scl = _scl(ONOFF_SCL)
        block = _extract_var_block(scl, "VAR_INPUT")
        assert block, "VAR_INPUT block not found in FB_Valve_OnOff"
        assert re.search(r"\bin_bSpringReturn\s*:", block, re.IGNORECASE), (
            "in_bSpringReturn not declared in VAR_INPUT — FIX 1 reverted"
        )
        assert re.search(
            r"\bin_bSpringReturn\s*:.*:=\s*TRUE", block, re.IGNORECASE
        ), "in_bSpringReturn default must be TRUE — safe default for spring-return valves"

    def test_step0_outputs_wrapped_with_spring_guard(self):
        """Step 0 (IDLE): output deassert must be inside IF in_bSpringReturn ... END_IF."""
        scl = _scl(ONOFF_SCL)
        step0 = _extract_step_block(scl, "0:  // IDLE")
        assert step0, "Step 0 (IDLE) block not found in FB_Valve_OnOff"
        guard_m = re.search(
            r"IF\s+in_bSpringReturn\b(.*?)END_IF",
            step0,
            re.DOTALL | re.IGNORECASE,
        )
        assert guard_m, (
            "IF in_bSpringReturn guard not found in step 0 — FIX 1 reverted"
        )
        guard_body = guard_m.group(1)
        assert re.search(r"out_bOpenOutput\s*:=\s*FALSE", guard_body, re.IGNORECASE), (
            "out_bOpenOutput := FALSE not inside spring-return guard in step 0"
        )
        assert re.search(r"out_bCloseOutput\s*:=\s*FALSE", guard_body, re.IGNORECASE), (
            "out_bCloseOutput := FALSE not inside spring-return guard in step 0"
        )

    def test_step99_outputs_wrapped_with_spring_guard(self):
        """Step 99 (FAULT): output deassert must be inside IF in_bSpringReturn ... END_IF."""
        scl = _scl(ONOFF_SCL)
        step99 = _extract_step_block(scl, "99: // FAULT")
        assert step99, "Step 99 (FAULT) block not found in FB_Valve_OnOff"
        guard_m = re.search(
            r"IF\s+in_bSpringReturn\b(.*?)END_IF",
            step99,
            re.DOTALL | re.IGNORECASE,
        )
        assert guard_m, (
            "IF in_bSpringReturn guard not found in step 99 — FIX 1 reverted"
        )
        guard_body = guard_m.group(1)
        assert re.search(r"out_bOpenOutput\s*:=\s*FALSE", guard_body, re.IGNORECASE), (
            "out_bOpenOutput := FALSE not inside spring-return guard in step 99"
        )
        assert re.search(r"out_bCloseOutput\s*:=\s*FALSE", guard_body, re.IGNORECASE), (
            "out_bCloseOutput := FALSE not inside spring-return guard in step 99"
        )

    def test_bistable_comment_present(self):
        """A comment acknowledging bistable (retain) behavior must exist in step 0 and step 99."""
        scl = _scl(ONOFF_SCL)
        region = _extract_region(scl, "02_STATE_MACHINE")
        assert re.search(r"bistable", region, re.IGNORECASE), (
            "Bistable comment not found in REGION 02 — intent documentation missing"
        )


# ===========================================================================
# FB_Valve_OnOff — FIX 2 (CLASS S-1): in_bManualMode routing
# ===========================================================================

class TestOnOffFix2ManualAutoMode:

    def test_auto_cmd_inputs_declared(self):
        """in_bAutoOpenCmd and in_bAutoCloseCmd must be declared in VAR_INPUT."""
        scl = _scl(ONOFF_SCL)
        block = _extract_var_block(scl, "VAR_INPUT")
        assert re.search(r"\bin_bAutoOpenCmd\s*:", block, re.IGNORECASE), (
            "in_bAutoOpenCmd not declared in VAR_INPUT — FIX 2 reverted"
        )
        assert re.search(r"\bin_bAutoCloseCmd\s*:", block, re.IGNORECASE), (
            "in_bAutoCloseCmd not declared in VAR_INPUT — FIX 2 reverted"
        )

    def test_temp_vars_declared(self):
        """t_bOpenCmd and t_bCloseCmd must be declared in VAR_TEMP."""
        scl = _scl(ONOFF_SCL)
        block = _extract_var_block(scl, "VAR_TEMP")
        assert re.search(r"\bt_bOpenCmd\s*:", block, re.IGNORECASE), (
            "t_bOpenCmd not declared in VAR_TEMP — FIX 2 reverted"
        )
        assert re.search(r"\bt_bCloseCmd\s*:", block, re.IGNORECASE), (
            "t_bCloseCmd not declared in VAR_TEMP — FIX 2 reverted"
        )

    def test_manual_mode_routes_to_manual_cmds(self):
        """In manual mode, t_bOpenCmd/t_bCloseCmd must come from in_bOpenCmd/in_bCloseCmd."""
        scl = _scl(ONOFF_SCL)
        region = _extract_region(scl, "02_STATE_MACHINE")
        assert region, "REGION 02_STATE_MACHINE not found"
        manual_m = re.search(
            r"IF\s+in_bManualMode\b(.*?)ELSE",
            region,
            re.DOTALL | re.IGNORECASE,
        )
        assert manual_m, "IF in_bManualMode ... ELSE block not found in region 02 — FIX 2 reverted"
        then_body = manual_m.group(1)
        assert re.search(r"t_bOpenCmd\s*:=\s*in_bOpenCmd", then_body, re.IGNORECASE), (
            "Manual path: t_bOpenCmd := in_bOpenCmd missing — FIX 2 reverted"
        )
        assert re.search(r"t_bCloseCmd\s*:=\s*in_bCloseCmd", then_body, re.IGNORECASE), (
            "Manual path: t_bCloseCmd := in_bCloseCmd missing — FIX 2 reverted"
        )

    def test_auto_mode_routes_to_auto_cmds(self):
        """In auto mode (ELSE branch), t_bOpenCmd/t_bCloseCmd must come from auto inputs."""
        scl = _scl(ONOFF_SCL)
        region = _extract_region(scl, "02_STATE_MACHINE")
        else_m = re.search(
            r"\bELSE\b(.*?)\bEND_IF\b",
            region,
            re.DOTALL | re.IGNORECASE,
        )
        assert else_m, "ELSE branch of manual/auto routing not found — FIX 2 reverted"
        else_body = else_m.group(1)
        assert re.search(r"t_bOpenCmd\s*:=\s*in_bAutoOpenCmd", else_body, re.IGNORECASE), (
            "Auto path: t_bOpenCmd := in_bAutoOpenCmd missing — FIX 2 reverted"
        )
        assert re.search(r"t_bCloseCmd\s*:=\s*in_bAutoCloseCmd", else_body, re.IGNORECASE), (
            "Auto path: t_bCloseCmd := in_bAutoCloseCmd missing — FIX 2 reverted"
        )

    def test_step0_transitions_use_routed_cmds(self):
        """Step 0 transitions must use t_bOpenCmd / t_bCloseCmd, not raw in_bOpenCmd / in_bCloseCmd."""
        scl = _scl(ONOFF_SCL)
        step0 = _extract_step_block(scl, "0:  // IDLE")
        assert step0, "Step 0 (IDLE) block not found"
        # Transitions must reference routed temp vars
        assert re.search(r"\bt_bOpenCmd\b.*s_nStep\s*:=\s*10", step0, re.DOTALL | re.IGNORECASE), (
            "Step 0 open-transition must use t_bOpenCmd, not in_bOpenCmd — FIX 2 reverted"
        )
        assert re.search(r"\bt_bCloseCmd\b.*s_nStep\s*:=\s*20", step0, re.DOTALL | re.IGNORECASE), (
            "Step 0 close-transition must use t_bCloseCmd, not in_bCloseCmd — FIX 2 reverted"
        )


# ===========================================================================
# FB_Valve_3Way — FIX 1 (CLASS C): in_bSpringReturn
# ===========================================================================

class TestThreeWayFix1SpringReturn:

    def test_spring_return_declared_in_input(self):
        """in_bSpringReturn must be declared in VAR_INPUT with default TRUE."""
        scl = _scl(THREEWAY_SCL)
        block = _extract_var_block(scl, "VAR_INPUT")
        assert block, "VAR_INPUT block not found in FB_Valve_3Way"
        assert re.search(r"\bin_bSpringReturn\s*:", block, re.IGNORECASE), (
            "in_bSpringReturn not declared in VAR_INPUT — FIX 1 reverted"
        )
        assert re.search(
            r"\bin_bSpringReturn\s*:.*:=\s*TRUE", block, re.IGNORECASE
        ), "in_bSpringReturn default must be TRUE"

    def test_step0_outputs_wrapped_with_spring_guard(self):
        """Step 0 (IDLE): output deassert must be inside IF in_bSpringReturn ... END_IF."""
        scl = _scl(THREEWAY_SCL)
        step0 = _extract_step_block(scl, "0:  // IDLE")
        assert step0, "Step 0 (IDLE) block not found in FB_Valve_3Way"
        guard_m = re.search(
            r"IF\s+in_bSpringReturn\b(.*?)END_IF",
            step0,
            re.DOTALL | re.IGNORECASE,
        )
        assert guard_m, (
            "IF in_bSpringReturn guard not found in step 0 — FIX 1 reverted"
        )
        guard_body = guard_m.group(1)
        assert re.search(r"out_bOutputA\s*:=\s*FALSE", guard_body, re.IGNORECASE), (
            "out_bOutputA := FALSE not inside spring-return guard in step 0"
        )
        assert re.search(r"out_bOutputB\s*:=\s*FALSE", guard_body, re.IGNORECASE), (
            "out_bOutputB := FALSE not inside spring-return guard in step 0"
        )

    def test_step99_outputs_wrapped_with_spring_guard(self):
        """Step 99 (FAULT): output deassert must be inside IF in_bSpringReturn ... END_IF."""
        scl = _scl(THREEWAY_SCL)
        step99 = _extract_step_block(scl, "99: // FAULT")
        assert step99, "Step 99 (FAULT) block not found in FB_Valve_3Way"
        guard_m = re.search(
            r"IF\s+in_bSpringReturn\b(.*?)END_IF",
            step99,
            re.DOTALL | re.IGNORECASE,
        )
        assert guard_m, (
            "IF in_bSpringReturn guard not found in step 99 — FIX 1 reverted"
        )
        guard_body = guard_m.group(1)
        assert re.search(r"out_bOutputA\s*:=\s*FALSE", guard_body, re.IGNORECASE), (
            "out_bOutputA := FALSE not inside spring-return guard in step 99"
        )
        assert re.search(r"out_bOutputB\s*:=\s*FALSE", guard_body, re.IGNORECASE), (
            "out_bOutputB := FALSE not inside spring-return guard in step 99"
        )

    def test_bistable_comment_present(self):
        """A comment acknowledging bistable retain behavior must exist in REGION 02."""
        scl = _scl(THREEWAY_SCL)
        region = _extract_region(scl, "02_STATE_MACHINE")
        assert re.search(r"bistable", region, re.IGNORECASE), (
            "Bistable comment not found in REGION 02 — intent documentation missing"
        )


# ===========================================================================
# FB_Valve_3Way — FIX 2 (CLASS S-1): in_bManualMode routing
# ===========================================================================

class TestThreeWayFix2ManualAutoMode:

    def test_auto_cmd_inputs_declared(self):
        """in_bAutoPositionACmd and in_bAutoPositionBCmd must be declared in VAR_INPUT."""
        scl = _scl(THREEWAY_SCL)
        block = _extract_var_block(scl, "VAR_INPUT")
        assert re.search(r"\bin_bAutoPositionACmd\s*:", block, re.IGNORECASE), (
            "in_bAutoPositionACmd not declared in VAR_INPUT — FIX 2 reverted"
        )
        assert re.search(r"\bin_bAutoPositionBCmd\s*:", block, re.IGNORECASE), (
            "in_bAutoPositionBCmd not declared in VAR_INPUT — FIX 2 reverted"
        )

    def test_temp_vars_declared(self):
        """t_bPositionACmd and t_bPositionBCmd must be declared in VAR_TEMP."""
        scl = _scl(THREEWAY_SCL)
        block = _extract_var_block(scl, "VAR_TEMP")
        assert re.search(r"\bt_bPositionACmd\s*:", block, re.IGNORECASE), (
            "t_bPositionACmd not declared in VAR_TEMP — FIX 2 reverted"
        )
        assert re.search(r"\bt_bPositionBCmd\s*:", block, re.IGNORECASE), (
            "t_bPositionBCmd not declared in VAR_TEMP — FIX 2 reverted"
        )

    def test_manual_mode_routes_to_manual_cmds(self):
        """In manual mode, t_bPositionACmd/B must come from in_bPositionACmd/B."""
        scl = _scl(THREEWAY_SCL)
        region = _extract_region(scl, "02_STATE_MACHINE")
        assert region, "REGION 02_STATE_MACHINE not found"
        manual_m = re.search(
            r"IF\s+in_bManualMode\b(.*?)ELSE",
            region,
            re.DOTALL | re.IGNORECASE,
        )
        assert manual_m, "IF in_bManualMode ... ELSE block not found in region 02 — FIX 2 reverted"
        then_body = manual_m.group(1)
        assert re.search(r"t_bPositionACmd\s*:=\s*in_bPositionACmd", then_body, re.IGNORECASE), (
            "Manual path: t_bPositionACmd := in_bPositionACmd missing — FIX 2 reverted"
        )
        assert re.search(r"t_bPositionBCmd\s*:=\s*in_bPositionBCmd", then_body, re.IGNORECASE), (
            "Manual path: t_bPositionBCmd := in_bPositionBCmd missing — FIX 2 reverted"
        )

    def test_auto_mode_routes_to_auto_cmds(self):
        """In auto mode (ELSE branch), t_bPositionACmd/B must come from auto inputs."""
        scl = _scl(THREEWAY_SCL)
        region = _extract_region(scl, "02_STATE_MACHINE")
        else_m = re.search(
            r"\bELSE\b(.*?)\bEND_IF\b",
            region,
            re.DOTALL | re.IGNORECASE,
        )
        assert else_m, "ELSE branch of manual/auto routing not found — FIX 2 reverted"
        else_body = else_m.group(1)
        assert re.search(r"t_bPositionACmd\s*:=\s*in_bAutoPositionACmd", else_body, re.IGNORECASE), (
            "Auto path: t_bPositionACmd := in_bAutoPositionACmd missing — FIX 2 reverted"
        )
        assert re.search(r"t_bPositionBCmd\s*:=\s*in_bAutoPositionBCmd", else_body, re.IGNORECASE), (
            "Auto path: t_bPositionBCmd := in_bAutoPositionBCmd missing — FIX 2 reverted"
        )

    def test_step0_transitions_use_routed_cmds(self):
        """Step 0 transitions must use t_bPositionACmd/B, not raw in_bPositionACmd/B."""
        scl = _scl(THREEWAY_SCL)
        step0 = _extract_step_block(scl, "0:  // IDLE")
        assert step0, "Step 0 (IDLE) block not found"
        assert re.search(r"\bt_bPositionACmd\b", step0, re.IGNORECASE), (
            "Step 0 A-transition must use t_bPositionACmd — FIX 2 reverted"
        )
        assert re.search(r"\bt_bPositionBCmd\b", step0, re.IGNORECASE), (
            "Step 0 B-transition must use t_bPositionBCmd — FIX 2 reverted"
        )
        # Raw inputs must NOT appear in the transition guard conditions (they may appear in
        # the routing block above CASE, but NOT as the direct condition triggering step change)
        # Check: s_nStep := 10 transition uses routed temp
        assert re.search(
            r"\bt_bPositionACmd\b.*s_nStep\s*:=\s*10", step0, re.DOTALL | re.IGNORECASE
        ), "Step 0 -> step 10 transition must reference t_bPositionACmd"
        assert re.search(
            r"\bt_bPositionBCmd\b.*s_nStep\s*:=\s*20", step0, re.DOTALL | re.IGNORECASE
        ), "Step 0 -> step 20 transition must reference t_bPositionBCmd"


# ===========================================================================
# Gate acceptance checks
# ===========================================================================

class TestGateAcceptance:

    def test_onoff_gate_passes(self):
        """fb_acceptance_check gate must PASS for FB_Valve_OnOff after all fixes."""
        assert ONOFF_SCL.exists(), f"SCL file not found: {ONOFF_SCL}"
        assert ONOFF_CONTRACT.exists(), f"Contract file not found: {ONOFF_CONTRACT}"
        result = run_gate(ONOFF_SCL, ONOFF_CONTRACT)
        failed = [
            f"{c.check_id} ({c.check_type}): {c.issues}"
            for c in result.checks
            if c.status == "FAIL"
        ]
        assert result.overall == "PASS", (
            "FB_Valve_OnOff gate expected PASS but returned FAIL.\nFailed checks:\n"
            + "\n".join(failed)
        )

    def test_threeway_gate_passes(self):
        """fb_acceptance_check gate must PASS for FB_Valve_3Way after all fixes."""
        assert THREEWAY_SCL.exists(), f"SCL file not found: {THREEWAY_SCL}"
        assert THREEWAY_CONTRACT.exists(), f"Contract file not found: {THREEWAY_CONTRACT}"
        result = run_gate(THREEWAY_SCL, THREEWAY_CONTRACT)
        failed = [
            f"{c.check_id} ({c.check_type}): {c.issues}"
            for c in result.checks
            if c.status == "FAIL"
        ]
        assert result.overall == "PASS", (
            "FB_Valve_3Way gate expected PASS but returned FAIL.\nFailed checks:\n"
            + "\n".join(failed)
        )
