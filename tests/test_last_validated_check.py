"""Proof tests — last_validated staleness check (S-7 automation).

Pins the comparison semantics (month granularity, frontmatter-only parse)
and that the checker actually runs against this repo without crashing.
"""

from __future__ import annotations

import sys
from pathlib import Path

_DEV = Path(__file__).resolve().parent.parent / "05_SCRIPTS" / "dev"
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from script_last_validated_check import (  # noqa: E402
    is_stale, parse_last_validated,
)


def test_parse_frontmatter_variants():
    assert parse_last_validated("---\nlast_validated: 2026-05\n---\n") == (2026, 5)
    assert parse_last_validated('---\nlast_validated: "2026-07"\n---\n') == (2026, 7)
    assert parse_last_validated("---\nlast_validated: 2026-06-14\n---\n") == (2026, 6)
    assert parse_last_validated("# No frontmatter\n") is None


def test_staleness_is_month_granular():
    assert is_stale((2026, 5), (2026, 7)) is True
    assert is_stale((2026, 7), (2026, 7)) is False, \
        "aynı ay içinde değişiklik bayat sayılmaz"
    assert is_stale((2026, 7), (2026, 6)) is False
    assert is_stale((2025, 12), (2026, 1)) is True


def test_checker_runs_on_this_repo():
    import subprocess
    r = subprocess.run(
        [sys.executable, str(_DEV / "script_last_validated_check.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "last_validated check:" in r.stdout
