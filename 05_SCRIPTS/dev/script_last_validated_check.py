#!/usr/bin/env python3
"""last_validated staleness check (S-7, 2026-07-10 audit).

~150 public MD files carry a `last_validated:` frontmatter date that nobody
maintains by hand. Instead of mass-editing dates (which would make the
field meaningless), this check compares each file's LAST GIT COMMIT month
against its `last_validated:` month and reports files whose content moved
on after the recorded validation.

Usage:
    python 05_SCRIPTS/dev/script_last_validated_check.py [--strict] [--gha]

    --strict   exit 1 when stale files exist (default: report + exit 0)
    --gha      emit GitHub Actions ::warning annotations

Requires git history (CI: actions/checkout with fetch-depth: 0).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_LV_RE = re.compile(r"^last_validated:\s*[\"']?(\d{4})-(\d{2})", re.MULTILINE)


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


def parse_last_validated(text: str) -> tuple[int, int] | None:
    """(year, month) from the first frontmatter block, or None."""
    head = text[:2000]
    m = _LV_RE.search(head)
    return (int(m.group(1)), int(m.group(2))) if m else None


def is_stale(validated: tuple[int, int], committed: tuple[int, int]) -> bool:
    """Content committed in a LATER month than it was last validated."""
    return committed > validated


def collect() -> list[tuple[str, str, str]]:
    """[(relpath, validated 'YYYY-MM', last commit 'YYYY-MM')] stale files."""
    stale: list[tuple[str, str, str]] = []
    files = _git("ls-files", "*.md").splitlines()
    for rel in files:
        p = REPO / rel
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lv = parse_last_validated(text)
        if lv is None:
            continue
        commit_date = _git("log", "-1", "--format=%cs", "--", rel)
        m = re.match(r"^(\d{4})-(\d{2})", commit_date)
        if not m:
            continue
        cm = (int(m.group(1)), int(m.group(2)))
        if is_stale(lv, cm):
            stale.append((rel, f"{lv[0]:04d}-{lv[1]:02d}",
                          f"{cm[0]:04d}-{cm[1]:02d}"))
    return stale


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--gha", action="store_true")
    args = ap.parse_args()

    stale = collect()
    if not stale:
        print("last_validated check: all validated dates cover the latest "
              "content changes.")
        return 0
    print(f"last_validated check: {len(stale)} file(s) changed AFTER their "
          "recorded validation month:")
    for rel, lv, cm in stale:
        print(f"  {rel}: validated {lv}, last commit {cm}")
        if args.gha:
            print(f"::warning file={rel}::content changed {cm} but "
                  f"last_validated is {lv} — revalidate or bump the date")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
