#!/usr/bin/env python3
"""
script_factory_audit.py
=========================
Audits every .md file in the factory:
- Is the last_validated frontmatter field older than 6 months?
- Are TODO/FIXME markers still present?
- Are there empty files?

USAGE:
    python script_factory_audit.py [--max-age-months 6] [--format text|json]

OUTPUT:
    Audit report as a table.
    Exit code: 0 = clean, 1 = has issues.
"""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# This script lives in 05_SCRIPTS/dev/, so the repo root is three levels up.
FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent
SKIP_DIRS = {".venv", "venv", ".git", "node_modules", "__pycache__", "_archive",
             ".pytest_cache", ".mypy_cache", ".ruff_cache", "site-packages"}
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
LAST_VALIDATED_RE = re.compile(r"^last_validated\s*:\s*(.+)$", re.MULTILINE)
TODO_RE = re.compile(r"\b(TODO|FIXME|XXX)\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--max-age-months", type=int, default=6,
                   help="Max age before flagging (default: 6)")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--include-todos", action="store_true",
                   help="Flag files containing TODO/FIXME")
    return p.parse_args()


def parse_validated_date(raw: str) -> Optional[date]:
    """Parse the date from frontmatter. Format: YYYY-MM or YYYY-MM-DD."""
    raw = raw.strip().strip("'\"")
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def months_between(a: date, b: date) -> int:
    return (a.year - b.year) * 12 + (a.month - b.month)


def audit_file(path: Path, max_age_months: int, check_todos: bool) -> dict:
    """Audit a single .md file."""
    result = {
        "path": str(path.relative_to(FACTORY_ROOT)),
        "issues": [],
        "last_validated": None,
        "age_months": None,
        "size_bytes": path.stat().st_size,
    }

    if result["size_bytes"] == 0:
        result["issues"].append("EMPTY_FILE")
        return result

    text = path.read_text(encoding="utf-8", errors="replace")

    # Frontmatter
    m = FRONTMATTER_RE.match(text)
    if not m:
        result["issues"].append("NO_FRONTMATTER")
    else:
        front = m.group(1)
        lv_match = LAST_VALIDATED_RE.search(front)
        if not lv_match:
            result["issues"].append("NO_LAST_VALIDATED")
        else:
            d = parse_validated_date(lv_match.group(1))
            if d is None:
                result["issues"].append("INVALID_LAST_VALIDATED")
            else:
                result["last_validated"] = d.isoformat()
                age = months_between(date.today(), d)
                result["age_months"] = age
                if age >= max_age_months:
                    result["issues"].append(f"STALE_{age}MONTHS")

    # TODO check
    if check_todos and TODO_RE.search(text):
        result["issues"].append("HAS_TODO")

    return result


# Repo meta files (incl. README translations), no frontmatter expected
SKIP_FILES = {"README.md", "README_TR.md", "README_DE.md", "CHANGELOG.md"}


def find_md_files() -> list[Path]:
    """Find every .md file in the factory that should be audited."""
    files = []
    for md in FACTORY_ROOT.rglob("*.md"):
        # Skip third-party / build / archive folders
        if any(part in SKIP_DIRS for part in md.parts):
            continue
        # 07_PROJECT_TEMPLATE is copied into customer projects
        if "07_PROJECT_TEMPLATE" in md.parts:
            continue
        # Repo meta files
        if md.name in SKIP_FILES and md.parent == FACTORY_ROOT:
            continue
        files.append(md)
    return sorted(files)


def print_text_report(results: list[dict]) -> int:
    """Human-readable report."""
    issue_count = sum(1 for r in results if r["issues"])
    clean_count = len(results) - issue_count

    print(f"\nAutomation Factory Audit Report")
    print(f"   Scanned: {len(results)} files")
    print(f"   Clean:   {clean_count}")
    print(f"   Issues:  {issue_count}\n")

    if issue_count == 0:
        print("All files clean.")
        return 0

    print(f"{'File':<60} {'Age':<8} {'Issues'}")
    print("-" * 100)
    for r in results:
        if not r["issues"]:
            continue
        age = f"{r['age_months']}mo" if r["age_months"] is not None else "-"
        issues = ", ".join(r["issues"])
        print(f"{r['path']:<60} {age:<8} {issues}")

    return 1


def main() -> int:
    args = parse_args()

    files = find_md_files()
    results = [audit_file(f, args.max_age_months, args.include_todos) for f in files]

    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0 if all(not r["issues"] for r in results) else 1

    return print_text_report(results)


if __name__ == "__main__":
    sys.exit(main())
