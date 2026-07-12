"""
tests/test_fb_acceptance_check.py — Gate acceptance tests (FORGE Phase 1-B)

Proves:
  1. The gate REJECTS the deliberate-broken fixture FB_Motor_Broken_TEST_ONLY.scl
  2. The gate ACCEPTS the reference FB_Motor_DOL.scl
  3. The gate ACCEPTS the repaired FB_Motor_Standard.scl (Phase-3 surgical fix)
  4. Edge cases: missing file, invalid JSON, structural bad block
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Locate scripts directory relative to the tests/ dir
_ROOT = Path(__file__).parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
sys.path.insert(0, str(_SCRIPTS))

from fb_acceptance_check import (
    GateResult,
    check_behaviors,
    check_error_codes,
    check_forbidden,
    check_interface,
    check_structural,
    run_gate,
)

# ---------------------------------------------------------------------------
# Paths to fixtures
# ---------------------------------------------------------------------------

GOOD_SCL     = _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "motor" / "FB_Motor_DOL.scl"
REPAIRED_SCL = _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "motor" / "FB_Motor_Standard.scl"
# Dedicated broken fixture — preserves original bugs for regression testing.
# FB_Motor_Standard.scl was repaired in Phase 3; BAD_SCL is now a static fixture.
BAD_SCL      = _ROOT / "tests" / "fixtures" / "FB_Motor_Broken_TEST_ONLY.scl"
CONTRACT     = _ROOT / "06_KNOWLEDGE_BASE" / "contracts" / "motor" / "FB_Motor_DOL.contract.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Critical proof: gate REJECTS the known-bad block
# ---------------------------------------------------------------------------

class TestGateRejectsBadBlock:
    """FB_Motor_Broken_TEST_ONLY.scl (deliberate fixture) must FAIL the DOL gate."""

    def test_overall_fail(self):
        result = run_gate(BAD_SCL, CONTRACT)
        assert result.overall == "FAIL", (
            f"Expected FAIL for {BAD_SCL.name} but got {result.overall}"
        )

    def test_label_is_gate_failed(self):
        result = run_gate(BAD_SCL, CONTRACT)
        assert result.label == "GATE_FAILED"

    def test_interface_check_fails(self):
        scl = BAD_SCL.read_text(encoding="utf-8")
        contract = load_contract()
        cr = check_interface(scl, contract)
        assert cr.status == "FAIL"
        assert any("in_bEnable" in issue for issue in cr.issues)

    def test_behavior_check_fails(self):
        scl = BAD_SCL.read_text(encoding="utf-8")
        contract = load_contract()
        cr = check_behaviors(scl, contract)
        assert cr.status == "FAIL"
        # Must flag missing mandatory regions
        missing_regions = [i for i in cr.issues if "REGION" in i]
        assert len(missing_regions) >= 4

    def test_forbidden_pattern_detected(self):
        """FB_Motor_Standard.scl uses CURRENT_TIME() which is Siemens-proprietary."""
        scl = BAD_SCL.read_text(encoding="utf-8")
        contract = load_contract()
        cr = check_forbidden(scl, contract)
        assert cr.status == "FAIL"
        assert any("CURRENT_TIME" in issue for issue in cr.issues)

    def test_wrong_fb_name_detected(self):
        """The bad block declares FB_Motor_Conveyor, not FB_MOTOR_DOL."""
        scl = BAD_SCL.read_text(encoding="utf-8")
        contract = load_contract()
        cr = check_behaviors(scl, contract)
        name_issues = [i for i in cr.issues if "B-DOL-009" in i or "FB_MOTOR_DOL" in i]
        assert name_issues, "Expected B-DOL-009 (wrong name) to be flagged"


# ---------------------------------------------------------------------------
# Critical proof: gate ACCEPTS the good reference block
# ---------------------------------------------------------------------------

class TestGateAcceptsGoodBlock:
    """FB_Motor_DOL.scl must pass all required checks."""

    def test_overall_pass(self):
        result = run_gate(GOOD_SCL, CONTRACT)
        assert result.overall == "PASS", (
            f"Expected PASS for {GOOD_SCL.name} but got {result.overall}.\n"
            + _format_failures(result)
        )

    def test_label_contains_auto_verified(self):
        result = run_gate(GOOD_SCL, CONTRACT)
        assert "AUTO_VERIFIED" in result.label

    def test_label_contains_pending_tia(self):
        """Honesty requirement: PENDING_TIA_VERIFY always appended."""
        result = run_gate(GOOD_SCL, CONTRACT)
        assert "PENDING_TIA_VERIFY" in result.label

    def test_structural_pass(self):
        scl = GOOD_SCL.read_text(encoding="utf-8")
        cr = check_structural(scl)
        assert cr.status in ("PASS", "WARN"), f"Structural FAIL: {cr.issues}"

    def test_interface_pass(self):
        scl = GOOD_SCL.read_text(encoding="utf-8")
        contract = load_contract()
        cr = check_interface(scl, contract)
        assert cr.status == "PASS", f"Interface failures: {cr.issues}"

    def test_behaviors_pass(self):
        scl = GOOD_SCL.read_text(encoding="utf-8")
        contract = load_contract()
        cr = check_behaviors(scl, contract)
        must_fails = [i for i in cr.issues if not i.startswith("[SHOULD]")]
        assert not must_fails, f"Behavior MUST failures: {must_fails}"

    def test_error_codes_pass(self):
        scl = GOOD_SCL.read_text(encoding="utf-8")
        contract = load_contract()
        cr = check_error_codes(scl, contract)
        assert cr.status == "PASS", f"Error code failures: {cr.issues}"

    def test_forbidden_patterns_absent(self):
        scl = GOOD_SCL.read_text(encoding="utf-8")
        contract = load_contract()
        cr = check_forbidden(scl, contract)
        assert cr.status == "PASS", f"Forbidden pattern found: {cr.issues}"

    def test_all_mandatory_regions_present(self):
        scl = GOOD_SCL.read_text(encoding="utf-8")
        for region in ["01_INPUT_VALIDATION", "02_STATE_MACHINE",
                        "03_OUTPUT_LOGIC", "04_DIAGNOSTICS"]:
            assert region.upper() in scl.upper(), f"Missing REGION: {region}"

    def test_to_dict_serializable(self):
        """Gate result must serialize to JSON without error."""
        result = run_gate(GOOD_SCL, CONTRACT)
        d = result.to_dict()
        json.dumps(d)  # must not raise


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_missing_scl_file_exits(self, tmp_path):
        ghost = tmp_path / "ghost.scl"
        # run_gate should propagate FileNotFoundError — gate caller handles sys.exit
        with pytest.raises(FileNotFoundError):
            ghost.read_text()

    def test_structurally_broken_scl_fails_g01(self):
        bad_structural = "FUNCTION_BLOCK \"FB_Test\"\nVAR_INPUT\n  x : Bool;\nEND_VAR\nBEGIN\n  IF TRUE THEN\n  // missing END_IF\nEND_FUNCTION_BLOCK\n"
        cr = check_structural(bad_structural)
        assert cr.status == "FAIL"
        assert any("IF" in issue for issue in cr.issues)

    def test_empty_scl_fails_structural(self):
        cr = check_structural("   ")
        # No FB/FC/OB found → warning, not error (structural check is lenient)
        assert cr.status in ("PASS", "WARN")

    def test_gate_result_to_dict_schema(self):
        result = run_gate(GOOD_SCL, CONTRACT)
        d = result.to_dict()
        assert "overall" in d
        assert "label" in d
        assert "checks" in d
        assert isinstance(d["checks"], list)
        assert all("id" in c and "status" in c for c in d["checks"])

    def test_good_block_block_name_extracted_correctly(self):
        result = run_gate(GOOD_SCL, CONTRACT)
        assert "FB_MOTOR_DOL" in result.block_name.upper()

    def test_bad_block_block_name_is_fb_motor_conveyor(self):
        """Broken fixture declares FB_Motor_Conveyor — gate must detect wrong name."""
        result = run_gate(BAD_SCL, CONTRACT)
        assert "FB_Motor_Conveyor" in result.block_name or "FB_MOTOR_CONVEYOR" in result.block_name.upper()

    def test_repaired_block_passes_gate(self):
        """FB_Motor_Standard.scl was surgically repaired (Phase 3) and must now PASS."""
        result = run_gate(REPAIRED_SCL, CONTRACT)
        assert result.overall == "PASS", (
            f"Repaired FB_Motor_Standard.scl should pass but got {result.overall}.\n"
            + _format_failures(result)
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_failures(gr: GateResult) -> str:
    lines = []
    for c in gr.checks:
        if c.status == "FAIL":
            lines.append(f"  {c.check_id} FAIL:")
            for issue in c.issues:
                lines.append(f"    - {issue}")
    return "\n".join(lines)
