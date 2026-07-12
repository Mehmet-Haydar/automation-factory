"""
test_fb_template_error_counter.py
Regression guard for the audit finding: GLOBAL_FB_TEMPLATE.scl error counter
incremented on EVERY scan while an error was active (gated by the unrelated
s_bResetEdgeMem), instead of once per error onset.

The fix:
  - declares a dedicated error-edge memory (s_bErrorEdgeMem),
  - guards the increment with `out_bError/t_bAnyError AND NOT s_bErrorEdgeMem`,
  - assigns the edge memory after the check.

These tests are STRUCTURAL (static analysis of the SCL text):
  - PASS with the fix applied.
  - BREAK if the every-scan increment (or the s_bResetEdgeMem guard) returns.
"""

from __future__ import annotations

import re
from pathlib import Path

SCL_PATH = (
    Path(__file__).parent.parent
    / "01_GLOBAL_STANDARDS"
    / "templates"
    / "GLOBAL_FB_TEMPLATE.scl"
)


def _scl() -> str:
    return SCL_PATH.read_text(encoding="utf-8")


def _diagnostics_region(scl: str) -> str:
    """Return the 04_DIAGNOSTICS REGION body."""
    m = re.search(
        r"REGION\s+04_DIAGNOSTICS(.*?)END_REGION",
        scl,
        re.DOTALL | re.IGNORECASE,
    )
    assert m, "04_DIAGNOSTICS region not found"
    return m.group(1)


def test_error_edge_memory_declared():
    """A dedicated error-edge memory must be declared (not reuse the reset one)."""
    assert re.search(
        r"s_bErrorEdgeMem\s*:\s*Bool",
        _scl(),
        re.IGNORECASE,
    ), "s_bErrorEdgeMem : Bool not declared — counter cannot be edge-guarded"


def test_counter_increment_is_edge_guarded():
    """The s_nErrorCount increment must be gated by NOT s_bErrorEdgeMem
    (rising edge), NOT by the unrelated s_bResetEdgeMem (every-scan bug)."""
    region = _diagnostics_region(_scl())

    # The increment must exist...
    assert re.search(r"s_nErrorCount\s*:=\s*#?\s*s_nErrorCount\s*\+\s*1", region), (
        "error counter increment missing from DIAGNOSTICS"
    )

    # ...and be guarded by the ERROR edge memory.
    assert re.search(
        r"AND\s+NOT\s+#?s_bErrorEdgeMem\s+THEN(?:[^E]|E(?!ND_IF))*?"
        r"s_nErrorCount\s*:=\s*#?\s*s_nErrorCount\s*\+\s*1",
        region,
        re.DOTALL | re.IGNORECASE,
    ), "error counter increment is not guarded by 'AND NOT s_bErrorEdgeMem' (every-scan bug?)"


def test_counter_not_guarded_by_reset_memory():
    """ANTI-PATTERN: increment guarded by s_bResetEdgeMem == every-scan increment."""
    region = _diagnostics_region(_scl())
    bug = re.search(
        r"AND\s+NOT\s+#?s_bResetEdgeMem\s+THEN(?:[^E]|E(?!ND_IF))*?"
        r"s_nErrorCount\s*:=",
        region,
        re.DOTALL | re.IGNORECASE,
    )
    assert bug is None, (
        "error counter is gated by s_bResetEdgeMem — increments every scan "
        "while the error persists (audit regression)"
    )


def test_error_edge_memory_assigned_after_check():
    """The edge memory must be updated to the current error state each scan."""
    region = _diagnostics_region(_scl())
    assert re.search(
        r"s_bErrorEdgeMem\s*:=\s*#?\s*(t_bAnyError|out_bError)",
        region,
        re.IGNORECASE,
    ), "s_bErrorEdgeMem must be assigned the current error state (edge tracking)"
