"""S-1 proof tests — scl_validator: N-W5 (string literal masking) + N-W6 (stack nesting).

These tests verify the protective behaviour added for S-1:
  N-W5: Keywords embedded in SCL string literals must NOT be counted.
  N-W6: Wrong-order nesting (IF..FOR..END_IF..END_FOR) must be an error.

Each test is written so that removing the corresponding fix causes the assertion
to fail — i.e. they are NOT smoke tests; they assert the protective behaviour.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from scl_validator import (
    strip_comments,
    validate_scl,
    validate_scl_file,
    _balanced_stack,
    FileResult,
    ValidationIssue,
)


# ---------------------------------------------------------------------------
# N-W5 — string literal masking in strip_comments
# ---------------------------------------------------------------------------

class TestStripCommentsStringLiterals:
    """strip_comments must mask the content of SCL string literals so that
    keywords inside them are invisible to the keyword-balance checks."""

    def test_keyword_inside_string_is_masked(self):
        src = "myVar := 'END_IF';"
        result = strip_comments(src)
        # The string literal content must NOT contain 'END_IF' verbatim.
        assert "END_IF" not in result.upper(), (
            "keyword inside string literal leaked through strip_comments"
        )

    def test_keyword_outside_string_is_kept(self):
        src = "IF x THEN\nEND_IF\n"
        result = strip_comments(src)
        assert "IF" in result.upper()
        assert "END_IF" in result.upper()

    def test_block_comment_keyword_masked(self):
        src = "(* END_IF comment *)\nIF x THEN\nEND_IF\n"
        result = strip_comments(src)
        # Count: exactly one IF and one END_IF (from real code, not comment)
        import re
        ifs = len(re.findall(r"\bIF\b", result, re.IGNORECASE))
        end_ifs = len(re.findall(r"\bEND_IF\b", result, re.IGNORECASE))
        assert ifs == 1, f"expected 1 IF, got {ifs}"
        assert end_ifs == 1, f"expected 1 END_IF, got {end_ifs}"

    def test_line_comment_keyword_masked(self):
        src = "// END_IF in comment\nIF x THEN\nEND_IF\n"
        result = strip_comments(src)
        import re
        end_ifs = len(re.findall(r"\bEND_IF\b", result, re.IGNORECASE))
        assert end_ifs == 1, f"expected 1 END_IF from code, got {end_ifs}"

    def test_doubled_quote_does_not_end_string(self):
        # '' is an escaped single-quote inside the literal; string continues.
        src = "myVar := 'it''s END_IF here'; realEnd := 0;"
        result = strip_comments(src)
        assert "END_IF" not in result.upper(), (
            "doubled-quote escape not handled — keyword inside string leaked"
        )

    def test_string_literal_with_endfor_keyword(self):
        src = "label := 'END_FOR loop'; FOR i := 1 TO 10 DO\nEND_FOR\n"
        result = strip_comments(src)
        import re
        end_fors = len(re.findall(r"\bEND_FOR\b", result, re.IGNORECASE))
        # Only the real END_FOR should survive; the one inside the string must be masked.
        assert end_fors == 1, (
            f"expected 1 END_FOR (the real one), got {end_fors} — "
            "string literal content leaked into keyword count"
        )


# ---------------------------------------------------------------------------
# N-W5 integration: validate_scl must not raise false balance errors
# ---------------------------------------------------------------------------

class TestValidateSclStringLiteralIntegration:
    """validate_scl (which calls strip_comments) must not flag false errors
    when keywords appear only inside string literals."""

    def test_no_false_error_when_keyword_only_in_string(self):
        # IF/END_IF only in string — block is otherwise structurally valid.
        scl = (
            "FUNCTION_BLOCK FB_Test\n"
            "VAR\n"
            "  msg : STRING;\n"
            "END_VAR\n"
            "  msg := 'value is END_IF irrelevant';\n"
            "END_FUNCTION_BLOCK\n"
        )
        res = validate_scl(scl)
        if_errors = [i for i in res.issues
                     if i.severity == "error" and "IF" in i.message.upper()]
        assert not if_errors, (
            f"False balance error triggered by keyword inside string: {if_errors}"
        )

    def test_real_missing_end_if_still_detected(self):
        # A genuine unclosed IF must still be caught.
        scl = (
            "FUNCTION_BLOCK FB_Test\n"
            "VAR x : BOOL; END_VAR\n"
            "  IF x THEN\n"
            "    x := FALSE;\n"
            "  (* END_IF is in comment, not code *)\n"
            "END_FUNCTION_BLOCK\n"
        )
        res = validate_scl(scl)
        errors = [i for i in res.issues if i.severity == "error"]
        assert errors, "A real unclosed IF was not detected"


# ---------------------------------------------------------------------------
# N-W6 — stack-based nesting
# ---------------------------------------------------------------------------

class TestBalancedStack:
    """_balanced_stack must reject wrong-order nesting and accept valid nesting."""

    def test_valid_nested_if_for_passes(self):
        # Correct nesting: IF..FOR..END_FOR..END_IF
        code = "IF x THEN FOR i := 1 TO 10 DO END_FOR END_IF"
        errors = _balanced_stack(code)
        assert errors == [], f"Valid nesting reported errors: {errors}"

    def test_swapped_closers_detected(self):
        # Wrong order: IF..FOR..END_IF..END_FOR
        code = "IF x THEN FOR i := 1 TO 10 DO END_IF END_FOR"
        errors = _balanced_stack(code)
        assert errors, (
            "Wrong-order nesting IF..FOR..END_IF..END_FOR was NOT detected — "
            "count-based check would miss this; stack check must catch it"
        )

    def test_unclosed_if_detected(self):
        code = "IF x THEN\n  y := 1;\n"  # missing END_IF
        errors = _balanced_stack(code)
        assert errors, "Unclosed IF was not detected"
        assert any("IF" in e.upper() for e in errors)

    def test_extra_end_for_detected(self):
        code = "FOR i := 1 TO 10 DO END_FOR END_FOR"
        errors = _balanced_stack(code)
        assert errors, "Extra END_FOR was not detected"

    def test_function_block_and_function_not_confused(self):
        # FUNCTION_BLOCK must close with END_FUNCTION_BLOCK, not END_FUNCTION.
        code = "FUNCTION_BLOCK FB_X\nVAR x: BOOL; END_VAR\nEND_FUNCTION"
        errors = _balanced_stack(code)
        assert errors, (
            "FUNCTION_BLOCK closed with END_FUNCTION should be an error "
            "but no error was reported"
        )

    def test_correct_function_block_passes(self):
        code = "FUNCTION_BLOCK FB_X\nVAR x: BOOL; END_VAR\nEND_FUNCTION_BLOCK"
        errors = _balanced_stack(code)
        assert errors == [], f"Correct FUNCTION_BLOCK reported errors: {errors}"

    def test_correct_function_passes(self):
        code = "FUNCTION FC_Calc : BOOL\nVAR_INPUT v : INT; END_VAR\nEND_FUNCTION"
        errors = _balanced_stack(code)
        assert errors == [], f"Correct FUNCTION reported errors: {errors}"

    def test_deeply_nested_valid(self):
        code = (
            "FUNCTION_BLOCK FB_Deep\n"
            "VAR x: BOOL; END_VAR\n"
            "IF x THEN\n"
            "  FOR i := 0 TO 5 DO\n"
            "    WHILE x DO\n"
            "      x := FALSE;\n"
            "    END_WHILE\n"
            "  END_FOR\n"
            "END_IF\n"
            "END_FUNCTION_BLOCK\n"
        )
        errors = _balanced_stack(code)
        assert errors == [], f"Valid deeply-nested code reported errors: {errors}"

    def test_deeply_nested_wrong_order(self):
        # WHILE closes before FOR
        code = (
            "IF x THEN\n"
            "  FOR i := 0 TO 5 DO\n"
            "    WHILE x DO\n"
            "    END_FOR\n"    # wrong — should be END_WHILE
            "  END_WHILE\n"
            "END_IF\n"
        )
        errors = _balanced_stack(code)
        assert errors, "Wrong-order deep nesting was not detected"


# ---------------------------------------------------------------------------
# N-W6 integration: validate_scl must report nesting errors
# ---------------------------------------------------------------------------

class TestValidateSclNestingIntegration:
    """validate_scl must surface _balanced_stack errors as 'error' severity issues."""

    def test_swapped_if_for_raises_error(self):
        scl = (
            "FUNCTION_BLOCK FB_Bad\n"
            "VAR x: BOOL; i: INT; END_VAR\n"
            "IF x THEN\n"
            "  FOR i := 1 TO 10 DO\n"
            "  END_IF\n"        # wrong — should be END_FOR
            "END_FOR\n"
            "END_FUNCTION_BLOCK\n"
        )
        res = validate_scl(scl)
        nesting_errors = [i for i in res.issues
                          if i.severity == "error" and "nesting" in i.message.lower()]
        assert nesting_errors, (
            "Wrong-order IF..FOR..END_IF..END_FOR was not flagged in validate_scl"
        )

    def test_valid_scl_has_no_nesting_error(self):
        scl = (
            "FUNCTION_BLOCK FB_Good\n"
            "VAR x: BOOL; i: INT; END_VAR\n"
            "IF x THEN\n"
            "  FOR i := 1 TO 10 DO\n"
            "  END_FOR\n"
            "END_IF\n"
            "END_FUNCTION_BLOCK\n"
        )
        res = validate_scl(scl)
        nesting_errors = [i for i in res.issues
                          if i.severity == "error" and "nesting" in i.message.lower()]
        assert not nesting_errors, (
            f"Valid SCL falsely reported nesting errors: {nesting_errors}"
        )


# ---------------------------------------------------------------------------
# BLOCK_COMMENT — (* *) hazard rules (2026-06-10 TIA V19 import test)
# ---------------------------------------------------------------------------

class TestBlockCommentHazard:
    """Generated SCL must use // comments only. A (* *) comment whose text
    contains "*)" (e.g. "(iDB_*)") is closed early by TIA and the rest is
    parsed as code — exactly what broke OB_Main in the V19 import test."""

    def test_block_comment_is_warned(self):
        src = (
            "FUNCTION_BLOCK \"FB_X\"\n"
            "(* header comment *)\n"
            "BEGIN\n;\nEND_FUNCTION_BLOCK\n"
        )
        result = validate_scl(src)
        assert any(i.keyword == "BLOCK_COMMENT" and i.severity == "warning"
                   for i in result.issues), "(* *) usage must raise a warning"

    def test_early_closed_comment_is_error(self):
        # "(iDB_*)" closes the comment at "*)" — the trailing text leaks
        # into code and the final "*)" becomes a stray closer.
        src = (
            "ORGANIZATION_BLOCK \"OB_X\"\n"
            "(* DBs are called via single-instance DBs (iDB_*).\n"
            "   WARNING: DRAFT *)\n"
            "BEGIN\n;\nEND_ORGANIZATION_BLOCK\n"
        )
        result = validate_scl(src)
        assert any(i.keyword == "BLOCK_COMMENT" and i.severity == "error"
                   for i in result.issues), (
            "early-closed (* *) comment must raise a stray-'*)' error"
        )

    def test_line_comments_are_clean(self):
        src = (
            "FUNCTION_BLOCK \"FB_X\"\n"
            "// header comment with (iDB_*) text — safe in a line comment\n"
            "BEGIN\n;\nEND_FUNCTION_BLOCK\n"
        )
        result = validate_scl(src)
        assert not any(i.keyword == "BLOCK_COMMENT" for i in result.issues), (
            "// comments must not trigger the block-comment rules"
        )


# ---------------------------------------------------------------------------
# EMPTY_BODY — statement-free IF/ELSE/loop bodies (2026-06-10 live compile)
# ---------------------------------------------------------------------------

class TestEmptyBodyHazard:
    """TIA's external-source compiler refuses an IF body that holds no
    statement (comments do not count): 'Compound part of instruction
    expected', reported far from the culprit — FB_Watchdog's comment-only
    placeholder IF cost a 6-variant live bisect to find."""

    def _wrap(self, body: str) -> str:
        return ("FUNCTION_BLOCK \"FB_X\"\n"
                "VAR_INPUT\n   x : Bool;\nEND_VAR\n"
                "BEGIN\n" + body + "\nEND_FUNCTION_BLOCK\n")

    def test_comment_only_if_body_is_error(self):
        # The exact FB_Watchdog pattern that failed the live V19 compile.
        result = validate_scl(self._wrap(
            "IF x THEN\n"
            "   // placeholder — wire the comms check here\n"
            "   // out_bFault := TRUE;\n"
            "END_IF;"))
        assert any(i.keyword == "EMPTY_BODY" and i.severity == "error"
                   for i in result.issues)

    def test_truly_empty_if_body_is_error(self):
        result = validate_scl(self._wrap("IF x THEN\nEND_IF;"))
        assert any(i.keyword == "EMPTY_BODY" and i.severity == "error"
                   for i in result.issues)

    def test_empty_then_before_else_is_error(self):
        result = validate_scl(self._wrap(
            "IF x THEN\n   // nothing yet\nELSE\n   ;\nEND_IF;"))
        assert any(i.keyword == "EMPTY_BODY" and i.severity == "error"
                   for i in result.issues)

    def test_empty_else_is_warning(self):
        result = validate_scl(self._wrap(
            "IF x THEN\n   ;\nELSE\n   // nothing\nEND_IF;"))
        assert any(i.keyword == "EMPTY_BODY" and i.severity == "warning"
                   for i in result.issues)

    def test_noop_semicolon_body_is_clean(self):
        # The fix shipped in FB_Watchdog: a bare ';' makes the body legal.
        result = validate_scl(self._wrap(
            "IF x THEN\n"
            "   // placeholder comment\n"
            "   ;\n"
            "END_IF;"))
        assert not any(i.keyword == "EMPTY_BODY" for i in result.issues)

    def test_fixed_library_watchdog_is_clean(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "06_KNOWLEDGE_BASE"
               / "blocks" / "system" / "FB_Watchdog.scl")
        result = validate_scl(src.read_text(encoding="utf-8"))
        assert not any(i.keyword == "EMPTY_BODY" for i in result.issues), (
            "the shipped FB_Watchdog must stay EMPTY_BODY-clean")


# ---------------------------------------------------------------------------
# _ELSE_RE regex fix (B4/S-4) — taşındı: test_else_re_fix.py
# ---------------------------------------------------------------------------

class TestElseReRegex:
    """_ELSE_RE'nin doğrudan davranışını doğrular.

    Fix geri alınırsa (yani r"\\bELS(E|IF)\\b" kullanılırsa) bu testler kırılır.
    """

    def _get_else_re(self):
        import scl_validator as sv
        return sv._ELSE_RE

    def test_else_eslesiyor(self):
        pat = self._get_else_re()
        assert pat.search("         ELSE")

    def test_else_satirsonu_eslesiyor(self):
        pat = self._get_else_re()
        assert pat.search("ELSE")

    def test_elsif_eslesmemeli(self):
        pat = self._get_else_re()
        assert not pat.search("ELSIF Req_Auto AND Allow_Auto THEN"), (
            "_ELSE_RE 'ELSIF' eşlememelidir — negative lookahead eksikse kırılır")

    def test_elsif_kucuk_harf(self):
        pat = self._get_else_re()
        assert not pat.search("elsif cond THEN")

    def test_else_boslukla_devam_eden(self):
        pat = self._get_else_re()
        assert pat.search("         ELSE\n")


def _wrap_fb(case_body: str) -> str:
    return f"""FUNCTION_BLOCK "FB_Test"
{{ S7_Optimized_Access := 'TRUE' }}
VAR_INPUT
   in_bEnable : Bool;
   Req_Auto   : Bool;
   Allow_Auto : Bool;
   Req_Manual : Bool;
   Req_Stop   : Bool;
END_VAR
VAR
   s_nStep : Int;
END_VAR
BEGIN
   CASE s_nStep OF
{case_body}
   END_CASE;
END_FUNCTION_BLOCK
"""


def _structural_bugs(result):
    return [i for i in result.issues if i.keyword == "STRUCTURAL_BUG"]


_ELSIF_GUARD_WITH_OVERWRITE = """
      10:
         IF NOT in_bEnable THEN
            out_bMain := FALSE;
            out_bStar := FALSE;
            s_nStep := 0;
         ELSIF Req_Auto AND Allow_Auto THEN
            out_bMain := TRUE;
         ELSIF Req_Manual THEN
            out_bMain := TRUE;
         ELSIF Req_Stop THEN
            out_bMain := FALSE;
            s_nStep := 0;
         END_IF;
         out_bMain := TRUE;
"""

_ELSE_GUARD_CLEAN = """
      10:
         IF NOT in_bEnable THEN
            out_bMain := FALSE;
            out_bStar := FALSE;
            s_nStep := 0;
         ELSE
            out_bMain := TRUE;
            out_bStar := TRUE;
         END_IF;
"""

_NO_ELSE_GUARD_WITH_OVERWRITE = """
      10:
         IF NOT in_bEnable THEN
            out_bMain := FALSE;
            out_bStar := FALSE;
            s_nStep := 0;
         END_IF;
         out_bMain := TRUE;
"""


class TestGuardOverwriteElsif:
    """has_top_else flag'i ELSIF'den etkilenmemeli."""

    def test_elsif_olan_blokta_guard_overwrite_TESPIT_EDILMELI(self):
        result = validate_scl(_wrap_fb(_ELSIF_GUARD_WITH_OVERWRITE))
        bugs = _structural_bugs(result)
        assert bugs, (
            "ELSIF içeren IF-blokta gerçek guard-overwrite varsa STRUCTURAL_BUG bekleniyor. "
            "Fix geri alınırsa ELSIF has_top_else=True yapıp tespiti engeller.")

    def test_else_olan_blok_temiz(self):
        result = validate_scl(_wrap_fb(_ELSE_GUARD_CLEAN))
        assert not _structural_bugs(result)

    def test_else_olmayan_sade_overwrite_tespit_edilmeli(self):
        result = validate_scl(_wrap_fb(_NO_ELSE_GUARD_WITH_OVERWRITE))
        assert _structural_bugs(result)


# ---------------------------------------------------------------------------
# Guard-overwrite linter rule — 2026-06-09 audit (test_scl_validator_guard_overwrite.py)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BLOCKS_DIR = _PROJECT_ROOT / "06_KNOWLEDGE_BASE" / "blocks"


def _wrap_guard(case_body: str) -> str:
    """Minimal FB skeleton for guard-overwrite tests (only in_bEnable)."""
    return f"""FUNCTION_BLOCK "FB_Test"
{{ S7_Optimized_Access := 'TRUE' }}
VAR_INPUT
   in_bEnable : Bool;
END_VAR
VAR
   s_nStep : Int;
END_VAR
BEGIN
   CASE s_nStep OF
{case_body}
   END_CASE;
END_FUNCTION_BLOCK
"""


_PRE_FIX_STEP10 = """
      10:
         IF NOT t_bStartEnable OR NOT in_bEnable THEN
            out_bMain := FALSE; out_bStar := FALSE; out_bDelta := FALSE;
            s_nStep := 0;
         END_IF;
         out_bMain := TRUE; out_bStar := TRUE; out_bDelta := FALSE;
"""

_POST_FIX_STEP10 = """
      10:
         IF NOT t_bStartEnable OR NOT in_bEnable THEN
            out_bMain := FALSE; out_bStar := FALSE; out_bDelta := FALSE;
            s_nStep := 0;
         ELSE
            out_bMain := TRUE; out_bStar := TRUE; out_bDelta := FALSE;
         END_IF;
"""


class TestRuleCatchesPreFixBug:
    def test_pre_fix_stardelta_pattern_flagged(self):
        result = validate_scl(_wrap_guard(_PRE_FIX_STEP10))
        bugs = _structural_bugs(result)
        assert bugs, (
            "The pre-fix StarDelta step-10 guard-overwrite pattern must be "
            "flagged as STRUCTURAL_BUG — this is the exact bug the 2026-06-09 "
            "audit found and the old tests missed"
        )
        assert any("out_bMain" in b.message or "out_bmain" in b.message
                   for b in bugs)
        assert all(b.severity == "error" for b in bugs)

    def test_flag_points_at_overwriting_line(self):
        result = validate_scl(_wrap_guard(_PRE_FIX_STEP10))
        bug = _structural_bugs(result)[0]
        src_lines = _wrap_guard(_PRE_FIX_STEP10).splitlines()
        flagged = src_lines[bug.line - 1]
        assert ":= TRUE" in flagged

    def test_comments_cannot_hide_the_bug(self):
        body = _PRE_FIX_STEP10.replace(
            "         out_bMain := TRUE;",
            "         // safe: guard above handles stop\n"
            "         out_bMain := TRUE;",
        )
        assert _structural_bugs(validate_scl(_wrap_guard(body)))


class TestRuleAcceptsCorrectCode:
    def test_post_fix_else_pattern_clean(self):
        result = validate_scl(_wrap_guard(_POST_FIX_STEP10))
        assert not _structural_bugs(result), (
            "ELSE-wrapped guard (the applied fix) must NOT be flagged"
        )

    def test_guard_without_false_assignments_not_flagged(self):
        body = """
      0:
         out_bReady := FALSE;
         IF t_bStartEnable AND NOT out_bError THEN
            s_nStep := 10;
         END_IF;
         out_bReady := TRUE;
"""
        assert not _structural_bugs(validate_scl(_wrap_guard(body)))

    def test_reassignment_of_other_variable_not_flagged(self):
        body = """
      10:
         IF NOT in_bEnable THEN
            out_bMain := FALSE;
            s_nStep := 0;
         END_IF;
         out_bLamp := TRUE;
"""
        assert not _structural_bugs(validate_scl(_wrap_guard(body)))


class TestCuratedLibraryStaysClean:
    def test_all_library_blocks_pass(self):
        scl_files = sorted(_BLOCKS_DIR.rglob("*.scl"))
        assert len(scl_files) >= 18, f"expected >=18 blocks, found {len(scl_files)}"
        offenders = {}
        for f in scl_files:
            bugs = _structural_bugs(validate_scl_file(f))
            if bugs:
                offenders[f.name] = [b.message for b in bugs]
        assert not offenders, (
            "curated library must be free of guard-overwrite bugs; "
            f"offenders: {offenders}"
        )
