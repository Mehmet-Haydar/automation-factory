"""
test_stardelta_safety_fixes.py
Proof tests for three safety fixes applied to FB_Motor_StarDelta.scl.

FIX 1 (B-1)  : Star contactor feedback — step 15 STAR_OPENING inserted between step 10 and 20.
FIX 2 (S-2)  : Stop guard in STAR (step 10) and DEAD TIME (step 20).
FIX 3 (S-5)  : Welded delta detection — step 35 DELTA_STOPPING + 16#0012 error code.

These tests are STRUCTURAL (static analysis of the SCL text). They:
  - PASS with the fix applied.
  - BREAK (fail) if the fix is reverted, acting as regression guards.
"""

from __future__ import annotations

import re
from pathlib import Path

SCL_PATH = (
    Path(__file__).parent.parent
    / "06_KNOWLEDGE_BASE"
    / "blocks"
    / "motor"
    / "FB_Motor_StarDelta.scl"
)


def _scl() -> str:
    return SCL_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# FIX 1 — B-1: Star contactor feedback input + step 15 STAR_OPENING
# ---------------------------------------------------------------------------

class TestFix1StarFeedbackInput:
    """in_bFeedbackStar must be declared as a Bool input."""

    def test_input_declared(self):
        scl = _scl()
        # Must appear inside VAR_INPUT block
        var_input_block = re.search(
            r"VAR_INPUT(.*?)END_VAR", scl, re.DOTALL | re.IGNORECASE
        ).group(1)
        assert re.search(
            r"in_bFeedbackStar\s*:\s*Bool", var_input_block, re.IGNORECASE
        ), "in_bFeedbackStar : Bool not declared in VAR_INPUT"

    def test_input_comment_mentions_star(self):
        scl = _scl()
        # Comment must mention STAR to prevent accidental copypaste without semantics
        match = re.search(
            r"in_bFeedbackStar\s*:\s*Bool[^\n]*//[^\n]*STAR", scl, re.IGNORECASE
        )
        assert match, "in_bFeedbackStar declaration must have a STAR-related comment"


class TestFix1Step15Inserted:
    """Step 10 must redirect to step 15; step 15 must exist with timeout to step 99."""

    def test_step10_transitions_to_15_not_20(self):
        scl = _scl()
        # After s_tonStarDur.Q the assignment must go to 15.
        # The two statements may be on the same line separated by ';', so use DOTALL
        # and allow any characters (including ';') between .Q and s_nStep := 15.
        assert re.search(
            r"s_tonStarDur\.Q.*?s_nStep\s*:=\s*15", scl, re.DOTALL
        ), "Step 10: s_tonStarDur.Q must transition to step 15 (not 20)"

    def test_step15_label_exists(self):
        scl = _scl()
        assert re.search(r"^\s*15\s*:", scl, re.MULTILINE), (
            "Step 15 case label not found in state machine"
        )

    def test_step15_uses_feedback_star(self):
        scl = _scl()
        # Step 15 block must reference in_bFeedbackStar
        step15_match = re.search(
            r"15\s*:.*?(?=\n\s*\d+\s*:|END_CASE)", scl, re.DOTALL
        )
        assert step15_match, "Cannot locate step 15 block"
        step15_text = step15_match.group(0)
        assert "in_bFeedbackStar" in step15_text, (
            "Step 15 must reference in_bFeedbackStar"
        )

    def test_step15_has_fault_path_to_99(self):
        scl = _scl()
        step15_match = re.search(
            r"15\s*:.*?(?=\n\s*\d+\s*:|END_CASE)", scl, re.DOTALL
        )
        assert step15_match, "Cannot locate step 15 block"
        step15_text = step15_match.group(0)
        # Must escalate to step 99 on timeout (stuck-star fault)
        assert re.search(r"s_nStep\s*:=\s*99", step15_text), (
            "Step 15 must have a fault path (s_nStep := 99) for stuck-star timeout"
        )

    def test_step15_error_code_0020(self):
        scl = _scl()
        step15_match = re.search(
            r"15\s*:.*?(?=\n\s*\d+\s*:|END_CASE)", scl, re.DOTALL
        )
        assert step15_match, "Cannot locate step 15 block"
        step15_text = step15_match.group(0)
        assert re.search(r"16#0020", step15_text, re.IGNORECASE), (
            "Step 15 must set error code 16#0020 (star contactor stuck closed)"
        )

    def test_step15_transitions_to_20_on_open(self):
        scl = _scl()
        step15_match = re.search(
            r"15\s*:.*?(?=\n\s*\d+\s*:|END_CASE)", scl, re.DOTALL
        )
        assert step15_match, "Cannot locate step 15 block"
        step15_text = step15_match.group(0)
        assert re.search(r"s_nStep\s*:=\s*20", step15_text), (
            "Step 15 must transition to step 20 when star is confirmed open"
        )

    def test_step10_no_longer_directly_jumps_to_20(self):
        """Regression: step 10 must NOT have s_nStep := 20 after s_tonStarDur.Q."""
        scl = _scl()
        step10_match = re.search(
            r"10\s*:.*?(?=\n\s*15\s*:)", scl, re.DOTALL
        )
        assert step10_match, "Cannot locate step 10 block (expected to end at step 15)"
        step10_text = step10_match.group(0)
        # After tonStarDur.Q the next step must be 15, not 20
        assert not re.search(
            r"s_tonStarDur\.Q\b[^;]*s_nStep\s*:=\s*20", step10_text, re.DOTALL
        ), "Step 10 must not transition directly to step 20 (regression of fix B-1)"


# ---------------------------------------------------------------------------
# FIX 2 — S-2: Stop guard in STAR (step 10) and DEAD TIME (step 20)
# ---------------------------------------------------------------------------

class TestFix2StopGuards:
    """Both step 10 and step 20 must contain the stop guard."""

    def _extract_step(self, scl: str, step_num: int, next_step: int) -> str:
        pattern = rf"{step_num}\s*:.*?(?=\n\s*{next_step}\s*:)"
        m = re.search(pattern, scl, re.DOTALL)
        assert m, f"Cannot locate step {step_num} block"
        return m.group(0)

    def test_step10_has_stop_guard(self):
        scl = _scl()
        step10 = self._extract_step(scl, 10, 15)
        # Must have both t_bStartEnable check and in_bEnable check
        assert re.search(r"NOT\s+t_bStartEnable", step10), (
            "Step 10 missing stop guard: NOT t_bStartEnable"
        )
        assert re.search(r"NOT\s+in_bEnable", step10), (
            "Step 10 missing stop guard: NOT in_bEnable"
        )

    def test_step10_stop_guard_goes_to_0(self):
        scl = _scl()
        step10 = self._extract_step(scl, 10, 15)
        # Guard must set step to 0
        guard_match = re.search(
            r"NOT\s+t_bStartEnable.*?s_nStep\s*:=\s*0", step10, re.DOTALL
        )
        assert guard_match, (
            "Step 10 stop guard must set s_nStep := 0"
        )

    def test_step10_stop_guard_clears_outputs(self):
        scl = _scl()
        step10 = self._extract_step(scl, 10, 15)
        guard_block = re.search(
            r"NOT\s+t_bStartEnable.*?END_IF", step10, re.DOTALL
        )
        assert guard_block, "Cannot find stop guard IF block in step 10"
        guard_text = guard_block.group(0)
        for out in ("out_bMain", "out_bStar", "out_bDelta"):
            assert out in guard_text, (
                f"Step 10 stop guard must clear {out}"
            )

    def test_step20_has_stop_guard(self):
        scl = _scl()
        step20 = self._extract_step(scl, 20, 30)
        assert re.search(r"NOT\s+t_bStartEnable", step20), (
            "Step 20 missing stop guard: NOT t_bStartEnable"
        )
        assert re.search(r"NOT\s+in_bEnable", step20), (
            "Step 20 missing stop guard: NOT in_bEnable"
        )

    def test_step20_stop_guard_goes_to_0(self):
        scl = _scl()
        step20 = self._extract_step(scl, 20, 30)
        guard_match = re.search(
            r"NOT\s+t_bStartEnable.*?s_nStep\s*:=\s*0", step20, re.DOTALL
        )
        assert guard_match, "Step 20 stop guard must set s_nStep := 0"

    def test_step20_stop_guard_clears_outputs(self):
        scl = _scl()
        step20 = self._extract_step(scl, 20, 30)
        guard_block = re.search(
            r"NOT\s+t_bStartEnable.*?END_IF", step20, re.DOTALL
        )
        assert guard_block, "Cannot find stop guard IF block in step 20"
        guard_text = guard_block.group(0)
        for out in ("out_bMain", "out_bStar", "out_bDelta"):
            assert out in guard_text, (
                f"Step 20 stop guard must clear {out}"
            )


# ---------------------------------------------------------------------------
# FIX 3 — S-5: Welded delta detection — step 35 + s_tonStopTO
# ---------------------------------------------------------------------------

class TestFix3WeldedDelta:
    """Step 30 must route stop to step 35; step 35 must detect welded delta."""

    def test_stoptimeout_var_declared(self):
        scl = _scl()
        var_block = re.search(
            r"\bVAR\b(.*?)END_VAR", scl, re.DOTALL | re.IGNORECASE
        ).group(1)
        assert re.search(r"s_tonStopTO\s*:\s*TON", var_block, re.IGNORECASE), (
            "s_tonStopTO : TON not declared in VAR section"
        )

    def test_step30_stop_transition_goes_to_35(self):
        scl = _scl()
        step30_match = re.search(
            r"30\s*:.*?(?=\n\s*35\s*:)", scl, re.DOTALL
        )
        assert step30_match, "Cannot locate step 30 block (expected to end at step 35)"
        step30_text = step30_match.group(0)
        # The stop transition must go to 35, not 0
        assert re.search(r"s_nStep\s*:=\s*35", step30_text), (
            "Step 30 stop transition must set s_nStep := 35 (not 0)"
        )

    def test_step30_does_not_directly_go_to_0_on_stop(self):
        """Regression: step 30 must not set s_nStep := 0 on NOT t_bStartEnable."""
        scl = _scl()
        step30_match = re.search(
            r"30\s*:.*?(?=\n\s*35\s*:)", scl, re.DOTALL
        )
        assert step30_match, "Cannot locate step 30 block"
        step30_text = step30_match.group(0)
        # Any guard that checks NOT t_bStartEnable must NOT immediately go to 0
        guard_blocks = re.findall(
            r"NOT\s+t_bStartEnable[^E]+END_IF", step30_text, re.DOTALL
        )
        for block in guard_blocks:
            assert not re.search(r"s_nStep\s*:=\s*0", block), (
                "Step 30 stop guard must route to step 35, not directly to step 0 (regression)"
            )

    def test_step35_label_exists(self):
        scl = _scl()
        assert re.search(r"^\s*35\s*:", scl, re.MULTILINE), (
            "Step 35 case label not found in state machine"
        )

    def test_step35_uses_stop_timer(self):
        scl = _scl()
        step35_match = re.search(
            r"35\s*:.*?(?=\n\s*99\s*:)", scl, re.DOTALL
        )
        assert step35_match, "Cannot locate step 35 block"
        step35_text = step35_match.group(0)
        assert "s_tonStopTO" in step35_text, (
            "Step 35 must use s_tonStopTO timer"
        )

    def test_step35_monitors_feedback_delta(self):
        scl = _scl()
        step35_match = re.search(
            r"35\s*:.*?(?=\n\s*99\s*:)", scl, re.DOTALL
        )
        assert step35_match, "Cannot locate step 35 block"
        step35_text = step35_match.group(0)
        assert "in_bFeedbackDelta" in step35_text, (
            "Step 35 must reference in_bFeedbackDelta to detect welded contactor"
        )

    def test_step35_fault_path_error_code_0012(self):
        scl = _scl()
        step35_match = re.search(
            r"35\s*:.*?(?=\n\s*99\s*:)", scl, re.DOTALL
        )
        assert step35_match, "Cannot locate step 35 block"
        step35_text = step35_match.group(0)
        assert re.search(r"16#0012", step35_text, re.IGNORECASE), (
            "Step 35 must set error code 16#0012 (delta contactor welded)"
        )

    def test_step35_fault_path_goes_to_99(self):
        scl = _scl()
        step35_match = re.search(
            r"35\s*:.*?(?=\n\s*99\s*:)", scl, re.DOTALL
        )
        assert step35_match, "Cannot locate step 35 block"
        step35_text = step35_match.group(0)
        assert re.search(r"s_nStep\s*:=\s*99", step35_text), (
            "Step 35 must escalate to step 99 on welded-delta timeout"
        )

    def test_step35_happy_path_goes_to_0(self):
        scl = _scl()
        step35_match = re.search(
            r"35\s*:.*?(?=\n\s*99\s*:)", scl, re.DOTALL
        )
        assert step35_match, "Cannot locate step 35 block"
        step35_text = step35_match.group(0)
        assert re.search(r"s_nStep\s*:=\s*0", step35_text), (
            "Step 35 must return to step 0 when delta is confirmed open"
        )

    def test_step35_clears_main_and_delta(self):
        scl = _scl()
        step35_match = re.search(
            r"35\s*:.*?(?=\n\s*99\s*:)", scl, re.DOTALL
        )
        assert step35_match, "Cannot locate step 35 block"
        step35_text = step35_match.group(0)
        for out in ("out_bMain", "out_bDelta"):
            assert re.search(rf"{out}\s*:=\s*FALSE", step35_text), (
                f"Step 35 must de-energise {out} := FALSE"
            )


# ---------------------------------------------------------------------------
# Cross-cutting: gate-level structural checks still pass after fixes
# ---------------------------------------------------------------------------

class TestGateCriticalPatternsStillPresent:
    """Key contract patterns must not have been accidentally removed."""

    def test_reset_edge_pattern(self):
        scl = _scl()
        assert re.search(
            r"s_bResetTrig\s*:=.*in_bReset.*AND\s*NOT.*s_bResetEdgeMem",
            scl, re.IGNORECASE
        ), "B-SD-001: Reset rising-edge detection removed"

    def test_star_dur_timer_present(self):
        assert "s_tonStarDur" in _scl(), "B-SD-002: s_tonStarDur removed"

    def test_dead_time_timer_present(self):
        assert "s_tonDeadTime" in _scl(), "B-SD-003: s_tonDeadTime removed"

    def test_mutual_exclusion_pattern(self):
        scl = _scl()
        assert re.search(
            r"out_bStar\s+AND\s+out_bDelta", scl
        ), "B-SD-004: STAR/DELTA mutual exclusion check removed"

    def test_error_0001_present(self):
        assert "16#0001" in _scl(), "B-SD-005: error code 16#0001 removed"

    def test_error_0003_present(self):
        assert "16#0003" in _scl(), "B-SD-006: error code 16#0003 removed"

    def test_error_0010_present(self):
        assert "16#0010" in _scl(), "B-SD-007: error code 16#0010 removed"

    def test_fb_name_intact(self):
        scl = _scl()
        assert re.search(
            r'FUNCTION_BLOCK\s+"?FB_Motor_StarDelta"?', scl
        ), "B-SD-008: FB name changed"

    def test_optimized_access_declared(self):
        scl = _scl()
        assert re.search(
            r"S7_Optimized_Access\s*:=\s*'TRUE'", scl
        ), "B-SD-009: S7_Optimized_Access removed"

    def test_all_four_regions_present(self):
        scl = _scl()
        for region in ("01_INPUT_VALIDATION", "02_STATE_MACHINE",
                       "03_OUTPUT_LOGIC", "04_DIAGNOSTICS"):
            assert re.search(rf"REGION\s+{re.escape(region)}", scl, re.IGNORECASE), (
                f"Mandatory REGION {region} removed"
            )


# ---------------------------------------------------------------------------
# FIX 2 (S-2) — DEEPER: stop-guard must not be overwritten in the same scan.
#
# Regression guard for the audit finding (step-10 overwrite bug): the stop
# guard set the outputs FALSE, but an UNCONDITIONAL `out_bMain := TRUE` below
# the END_IF re-energised them in the same scan (no RETURN/ELSE). The fix moves
# the normal-run assignments inside an ELSE branch. These tests fail if anyone
# reintroduces the unconditional overwrite.
# ---------------------------------------------------------------------------

class TestStopGuardNotOverwritten:
    """Steps 10 (STAR) and 20 (DEAD TIME): the energising assignment must live
    inside the stop-guard ELSE, never as an unconditional sibling after END_IF."""

    @staticmethod
    def _step_arm(scl: str, step: int) -> str:
        """Return the source text of CASE arm `step` up to the next numeric step label."""
        m = re.search(
            rf"\n\s*{step}:\s*//.*?(?=\n\s*\d+:\s*//|\n\s*END_CASE)",
            scl,
            re.DOTALL,
        )
        assert m, f"CASE arm for step {step} not found"
        return m.group(0)

    def _assert_guarded(self, step: int) -> None:
        arm = self._step_arm(_scl(), step)
        # The stop/disable guard must be present in this arm.
        assert re.search(
            r"IF\s+NOT\s+t_bStartEnable\s+OR\s+NOT\s+in_bEnable\s+THEN",
            arm,
            re.IGNORECASE,
        ), f"step {step}: stop/disable guard missing"
        # ANTI-PATTERN: `END_IF;` immediately followed by an unconditional
        # `out_bMain := TRUE` (the overwrite bug). Must NOT be present.
        overwrite = re.search(
            r"END_IF\s*;\s*out_bMain\s*:=\s*TRUE",
            arm,
            re.IGNORECASE,
        )
        assert overwrite is None, (
            f"step {step}: unconditional 'out_bMain := TRUE' right after the stop "
            f"guard END_IF — guard is overwritten in the same scan (S-2 regression)"
        )
        # POSITIVE: the guard must use ELSE so the run path is unreachable on stop.
        assert re.search(
            r"IF\s+NOT\s+t_bStartEnable\s+OR\s+NOT\s+in_bEnable\s+THEN"
            r".*?\bELSE\b.*?out_bMain\s*:=\s*TRUE",
            arm,
            re.DOTALL | re.IGNORECASE,
        ), f"step {step}: energising assignment must be inside the stop-guard ELSE"

    def test_step10_star_guard_not_overwritten(self):
        self._assert_guarded(10)

    def test_step20_deadtime_guard_not_overwritten(self):
        self._assert_guarded(20)
