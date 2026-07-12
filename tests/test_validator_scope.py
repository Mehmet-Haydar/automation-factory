"""W3 — Validate ciktisi yapisal-only olarak etiketlendi."""

from scl_validator import validate_scl, validate_scl_file, FileResult, SCOPE_WARNING


VALID_SCL = """\
FUNCTION_BLOCK FB_Test
VAR_INPUT Enable : BOOL; END_VAR
VAR_OUTPUT Running : BOOL; END_VAR
BEGIN
    Running := Enable;
END_FUNCTION_BLOCK
"""


def test_file_result_has_scope():
    res = validate_scl(VALID_SCL)
    assert res.scope == "structural_only"


def test_file_result_has_scope_warning():
    res = validate_scl(VALID_SCL)
    assert res.scope_warning
    assert "semantik" in res.scope_warning.lower() or "DOGRULANMADI" in res.scope_warning


def test_scope_warning_constant_exists():
    assert SCOPE_WARNING
    assert len(SCOPE_WARNING) > 20


def test_scope_not_cleared_on_errors():
    bad_scl = "FUNCTION_BLOCK FB_Test\nVAR_INPUT Enable : BOOL; END_VAR\nBEGIN\n    x := 1;\n"
    res = validate_scl(bad_scl)
    assert res.scope == "structural_only"
    assert res.scope_warning


def test_validate_scl_file_scope(tmp_path):
    f = tmp_path / "test.scl"
    f.write_text(VALID_SCL, encoding="utf-8")
    res = validate_scl_file(f)
    assert res.scope == "structural_only"
    assert res.scope_warning
