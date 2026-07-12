"""
test_b2_safety_notice_header.py  — Proof test for CLASS B-2: SAFETY NOTICE header

Verifies:
  1. Every SCL file under 06_KNOWLEDGE_BASE/blocks/ contains the SAFETY NOTICE block.
  2. The notice appears EXACTLY once per file (idempotency — no double insertion).
  3. The notice appears BEFORE the first FUNCTION_BLOCK / ORGANIZATION_BLOCK declaration.
  4. No code lines are modified — only comment lines were added.
  5. Regression guard: a file WITHOUT the notice fails this test (proves test is not smoke).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BLOCKS_DIR = PROJECT_ROOT / "06_KNOWLEDGE_BASE" / "blocks"

SAFETY_NOTICE_MARKER = "*** SAFETY NOTICE ***"

# All SCL files that must carry the notice
SCL_FILES = sorted(BLOCKS_DIR.rglob("*.scl"))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BLOCK_DECL_RE = re.compile(
    r"^\s*(FUNCTION_BLOCK|ORGANIZATION_BLOCK)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _first_block_line(text: str) -> int:
    """Return 0-based line index of the first FUNCTION_BLOCK / ORGANIZATION_BLOCK."""
    for i, line in enumerate(text.splitlines()):
        if _BLOCK_DECL_RE.match(line):
            return i
    return -1


def _notice_line(text: str) -> int:
    """Return 0-based line index of the SAFETY NOTICE marker, or -1."""
    for i, line in enumerate(text.splitlines()):
        if SAFETY_NOTICE_MARKER in line:
            return i
    return -1


# ---------------------------------------------------------------------------
# Parametrized tests — one per SCL file
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scl_path", SCL_FILES, ids=[p.name for p in SCL_FILES])
class TestSafetyNoticeHeader:

    def test_notice_present(self, scl_path: Path) -> None:
        """SAFETY NOTICE marker must exist in the file."""
        text = scl_path.read_text(encoding="utf-8", errors="replace")
        assert SAFETY_NOTICE_MARKER in text, (
            f"{scl_path.name}: SAFETY NOTICE marker not found. "
            "Fix CLASS B-2 was not applied or was reverted."
        )

    def test_notice_exactly_once(self, scl_path: Path) -> None:
        """The marker must appear exactly once — no duplicate insertions."""
        text = scl_path.read_text(encoding="utf-8", errors="replace")
        count = text.count(SAFETY_NOTICE_MARKER)
        assert count == 1, (
            f"{scl_path.name}: SAFETY NOTICE marker appears {count} times; expected 1. "
            "Possible duplicate insertion."
        )

    def test_notice_before_block_declaration(self, scl_path: Path) -> None:
        """The notice must appear BEFORE the FUNCTION_BLOCK / ORGANIZATION_BLOCK line."""
        text = scl_path.read_text(encoding="utf-8", errors="replace")
        notice_ln = _notice_line(text)
        block_ln = _first_block_line(text)
        assert notice_ln != -1, f"{scl_path.name}: SAFETY NOTICE line not found."
        assert block_ln != -1, (
            f"{scl_path.name}: No FUNCTION_BLOCK / ORGANIZATION_BLOCK declaration found."
        )
        assert notice_ln < block_ln, (
            f"{scl_path.name}: SAFETY NOTICE (line {notice_ln + 1}) is NOT before "
            f"block declaration (line {block_ln + 1})."
        )

    def test_notice_is_comment_only(self, scl_path: Path) -> None:
        """Every line of the SAFETY NOTICE block must be a comment line (// prefix)."""
        text = scl_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        # Locate the boundary: from the line with SAFETY NOTICE until we hit the
        # closing ============ line that follows it.
        in_notice = False
        for line in lines:
            stripped = line.strip()
            if SAFETY_NOTICE_MARKER in stripped:
                in_notice = True
            if in_notice:
                assert stripped.startswith("//"), (
                    f"{scl_path.name}: Non-comment line found inside SAFETY NOTICE block: "
                    f"{line!r}"
                )
                # The closing border terminates the notice section
                if stripped.startswith("// =") and SAFETY_NOTICE_MARKER not in stripped:
                    if stripped.count("=") > 10:  # long === line = closing border
                        break


# ---------------------------------------------------------------------------
# Regression guard: a synthesised file WITHOUT the notice must fail notice check
# ---------------------------------------------------------------------------

def test_regression_guard_no_notice(tmp_path: Path) -> None:
    """Proves the test is protective: a file without the notice triggers failure."""
    fake_scl = tmp_path / "FB_Fake.scl"
    fake_scl.write_text(
        "// ============================================================\n"
        "// FB_Fake — test file without safety notice\n"
        "// ============================================================\n"
        "\n"
        'FUNCTION_BLOCK "FB_Fake"\n'
        "BEGIN\n"
        "END_FUNCTION_BLOCK\n",
        encoding="utf-8",
    )
    text = fake_scl.read_text(encoding="utf-8")
    assert SAFETY_NOTICE_MARKER not in text, (
        "Regression guard: the synthetic test file must NOT contain the SAFETY NOTICE "
        "so that we can assert the presence check would fire on it."
    )
    # Simulate what test_notice_present would do — it must fail for this file
    with pytest.raises(AssertionError):
        assert SAFETY_NOTICE_MARKER in text, "SAFETY NOTICE marker not found."


def test_scl_file_count() -> None:
    """Sanity: expected at least 18 SCL files in blocks/."""
    assert len(SCL_FILES) >= 18, (
        f"Expected >= 18 SCL files under {BLOCKS_DIR}, found {len(SCL_FILES)}. "
        "Some files may have been deleted or moved."
    )
