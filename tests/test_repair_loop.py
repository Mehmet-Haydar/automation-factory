"""W4 — Onarim dongusu insan onayina diff sunar (auto_apply kapali varsayilan)."""

from code_verifier import repair_loop, RepairSession

BAD_SCL = """\
FUNCTION_BLOCK FB_Test
VAR_INPUT Enable : BOOL; END_VAR
BEGIN
    Running := Enable;
"""

FIXED_SCL = """\
FUNCTION_BLOCK FB_Test
VAR_INPUT Enable : BOOL; END_VAR
VAR_OUTPUT Running : BOOL; END_VAR
BEGIN
    Running := Enable;
END_FUNCTION_BLOCK
"""


def _fake_ai(system, user):
    return f"```scl\n{FIXED_SCL}```", None


def test_auto_apply_false_does_not_modify_current_scl():
    session = repair_loop(BAD_SCL, _fake_ai, max_iterations=2, auto_apply=False)
    assert session.current_scl == BAD_SCL


def test_auto_apply_false_returns_proposed_scl():
    session = repair_loop(BAD_SCL, _fake_ai, max_iterations=2, auto_apply=False)
    assert FIXED_SCL.strip() in session.proposed_scl or session.proposed_scl.strip() == FIXED_SCL.strip()


def test_auto_apply_false_returns_diff():
    session = repair_loop(BAD_SCL, _fake_ai, max_iterations=2, auto_apply=False)
    assert session.diff  # non-empty
    assert "---" in session.diff or "+++" in session.diff


def test_auto_apply_true_modifies_current_scl():
    session = repair_loop(BAD_SCL, _fake_ai, max_iterations=2, auto_apply=True)
    assert session.current_scl != BAD_SCL


def test_no_errors_skips_repair():
    """SCL with no structural errors -> repair loop terminates without calling AI."""
    # Use an OB (not FB) to avoid the END_FUNCTION_BLOCK overlap-guard edge case in the validator
    clean_scl = (
        "ORGANIZATION_BLOCK OB_Main\n"
        "VAR_TEMP x : INT; END_VAR\n"
        "BEGIN\n"
        "    x := 0;\n"
        "END_ORGANIZATION_BLOCK\n"
    )
    calls = []
    def counting_ai(s, u):
        calls.append(1)
        return "", None

    session = repair_loop(clean_scl, counting_ai, max_iterations=2, auto_apply=False)
    assert calls == []
    assert session.proposed_scl == ""
