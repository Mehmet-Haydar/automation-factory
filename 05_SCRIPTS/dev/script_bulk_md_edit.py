#!/usr/bin/env python3
"""
script_bulk_md_edit.py
========================
Makes mechanical edits across all MD files deterministically, without AI.

USAGE EXAMPLES:

# 1. Add a frontmatter field (if missing)
python script_bulk_md_edit.py \\
    --add-frontmatter "watchdog: required" \\
    --target "04_AI_PROMPTS/code_gen/motor/*.md"

# 2. Update a frontmatter field (replace if present)
python script_bulk_md_edit.py \\
    --update-field "last_validated" \\
    --new-value "2026-05-06" \\
    --target "**/*.md"

# 3. Remove a frontmatter field
python script_bulk_md_edit.py \\
    --remove-field "deprecated_field" \\
    --target "**/*.md"

# 4. Find-and-replace
python script_bulk_md_edit.py \\
    --replace "TIA Portal V18" \\
    --with "TIA Portal V19" \\
    --target "**/*.md"

# 5. Add a line after a specific section
python script_bulk_md_edit.py \\
    --add-after-section "## 7. Typical AI Errors" \\
    --content "- Watchdog error: after feedback timeout..." \\
    --target "04_AI_PROMPTS/code_gen/motor/*.md"

# 6. Version bumping (semver)
python script_bulk_md_edit.py \\
    --bump-version minor \\
    --target "04_AI_PROMPTS/code_gen/motor/*.md"

# 7. Dry-run (show what would happen without actually changing)
python script_bulk_md_edit.py \\
    --replace "foo" --with "bar" \\
    --target "**/*.md" \\
    --dry-run

SAFETY:
- Every command can be tested first with --dry-run
- With --backup, the original is kept with a .bak extension
- No command breaks the frontmatter (it works through a parser)
"""

import argparse
import re
import shutil
import sys
from pathlib import Path
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# This script lives in 05_SCRIPTS/dev/, so the repo root is three levels up.
FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent

FRONTMATTER_RE = re.compile(r"^(---\s*\n)(.*?)(\n---\s*\n)", re.DOTALL)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Bulk MD editor - mechanical editing without AI.",
        epilog=__doc__,
    )

    # Target
    p.add_argument("--target", required=True,
                   help="Glob pattern (e.g. '**/*.md', 'motor/*.md')")

    # Operation flags (one is chosen; they cannot be combined)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--add-frontmatter", metavar="KEY: VALUE",
                       help="Add a line to the frontmatter (skip if present)")
    group.add_argument("--update-field", metavar="KEY",
                       help="Update a frontmatter field (--new-value required)")
    group.add_argument("--remove-field", metavar="KEY",
                       help="Remove a frontmatter field")
    group.add_argument("--replace", metavar="OLD",
                       help="Find-and-replace (--with required)")
    group.add_argument("--add-after-section", metavar="SECTION_HEADER",
                       help="Add a line after a specific header (--content required)")
    group.add_argument("--bump-version", choices=["major", "minor", "patch"],
                       help="Bump the frontmatter version")
    group.add_argument("--list-targets", action="store_true",
                       help="Only list the matching files")

    # Helper arguments
    p.add_argument("--new-value", help="New value for --update-field")
    p.add_argument("--with", dest="replacement", help="New text for --replace")
    p.add_argument("--content", help="Content for --add-after-section")

    # Mode
    p.add_argument("--dry-run", action="store_true",
                   help="Do not change anything, just show what would happen")
    p.add_argument("--backup", action="store_true",
                   help="Back up the original as .bak")
    p.add_argument("--verbose", "-v", action="store_true")

    return p.parse_args()


def find_targets(pattern: str) -> list[Path]:
    """Find the files matching the glob pattern."""
    files = list(FACTORY_ROOT.glob(pattern))
    # Only operate on .md files
    files = [f for f in files if f.suffix == ".md" and f.is_file()]
    # Exclude 07_PROJECT_TEMPLATE
    files = [f for f in files if "07_PROJECT_TEMPLATE" not in f.parts]
    return sorted(files)


def split_frontmatter(text: str) -> tuple[str | None, str | None, str]:
    """Split the frontmatter. (delim_open, content, rest_with_close) or (None, None, full_text)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, None, text
    return m.group(1), m.group(2), m.group(3) + text[m.end():]


def reassemble(open_delim: str, frontmatter_content: str, rest: str) -> str:
    """Combine frontmatter + rest."""
    return f"{open_delim}{frontmatter_content}{rest}"


# ===== Operations =====

def op_add_frontmatter(text: str, line: str) -> tuple[str, bool]:
    """Add a line to the frontmatter (skip if key already present)."""
    open_delim, fm, rest = split_frontmatter(text)
    if fm is None:
        return text, False  # No frontmatter

    key = line.split(":", 1)[0].strip()
    # Already present?
    if re.search(rf"^{re.escape(key)}\s*:", fm, re.MULTILINE):
        return text, False  # Already present

    # Add (at the end)
    new_fm = fm.rstrip() + "\n" + line.strip()
    return reassemble(open_delim, new_fm, rest), True


def op_update_field(text: str, key: str, value: str) -> tuple[str, bool]:
    """Update a frontmatter field."""
    open_delim, fm, rest = split_frontmatter(text)
    if fm is None:
        return text, False

    pattern = rf"^({re.escape(key)}\s*:\s*).*$"
    new_fm, n = re.subn(pattern, rf"\g<1>{value}", fm, count=1, flags=re.MULTILINE)
    if n == 0:
        return text, False  # Not found

    return reassemble(open_delim, new_fm, rest), True


def op_remove_field(text: str, key: str) -> tuple[str, bool]:
    """Remove a frontmatter field."""
    open_delim, fm, rest = split_frontmatter(text)
    if fm is None:
        return text, False

    pattern = rf"^{re.escape(key)}\s*:.*\n?"
    new_fm, n = re.subn(pattern, "", fm, count=1, flags=re.MULTILINE)
    if n == 0:
        return text, False

    return reassemble(open_delim, new_fm, rest), True


def op_replace(text: str, old: str, new: str) -> tuple[str, bool]:
    """Find-and-replace (literal, not regex)."""
    if old not in text:
        return text, False
    return text.replace(old, new), True


def op_add_after_section(text: str, header: str, content: str) -> tuple[str, bool]:
    """Add a line after a specific header."""
    pattern = rf"^({re.escape(header)}\s*\n)"
    new_text, n = re.subn(
        pattern,
        rf"\g<1>\n{content}\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n == 0:
        return text, False
    return new_text, True


def op_bump_version(text: str, level: str) -> tuple[str, bool]:
    """Bump the frontmatter version per semver."""
    open_delim, fm, rest = split_frontmatter(text)
    if fm is None:
        return text, False

    m = re.search(r"^version\s*:\s*(\d+)\.(\d+)\.(\d+)\s*$", fm, re.MULTILINE)
    if not m:
        return text, False

    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if level == "major":
        major, minor, patch = major + 1, 0, 0
    elif level == "minor":
        minor, patch = minor + 1, 0
    elif level == "patch":
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    new_fm = re.sub(
        r"^(version\s*:\s*).*$",
        rf"\g<1>{new_version}",
        fm,
        count=1,
        flags=re.MULTILINE,
    )
    return reassemble(open_delim, new_fm, rest), True


# ===== Main =====

def main() -> int:
    args = parse_args()
    targets = find_targets(args.target)

    if args.list_targets:
        print(f"{len(targets)} files matched:\n")
        for t in targets:
            print(f"  - {t.relative_to(FACTORY_ROOT)}")
        return 0

    if not targets:
        print(f"Pattern matched nothing: {args.target}")
        return 1

    # Operation selection and validation
    op = None
    op_args = ()
    op_name = ""

    if args.add_frontmatter:
        op = op_add_frontmatter
        op_args = (args.add_frontmatter,)
        op_name = f"add-frontmatter '{args.add_frontmatter}'"
    elif args.update_field:
        if not args.new_value:
            print("--update-field requires --new-value")
            return 1
        op = op_update_field
        op_args = (args.update_field, args.new_value)
        op_name = f"update-field {args.update_field} -> '{args.new_value}'"
    elif args.remove_field:
        op = op_remove_field
        op_args = (args.remove_field,)
        op_name = f"remove-field {args.remove_field}"
    elif args.replace is not None:
        if args.replacement is None:
            print("--replace requires --with")
            return 1
        op = op_replace
        op_args = (args.replace, args.replacement)
        op_name = f"replace '{args.replace}' -> '{args.replacement}'"
    elif args.add_after_section:
        if not args.content:
            print("--add-after-section requires --content")
            return 1
        op = op_add_after_section
        op_args = (args.add_after_section, args.content)
        op_name = f"add-after-section '{args.add_after_section}'"
    elif args.bump_version:
        op = op_bump_version
        op_args = (args.bump_version,)
        op_name = f"bump-version {args.bump_version}"

    print(f"Operation: {op_name}")
    print(f"Target: {args.target} ({len(targets)} files)")
    if args.dry_run:
        print("DRY-RUN mode — changes are not saved")
    print()

    changed_count = 0
    skipped_count = 0

    for path in targets:
        try:
            original = path.read_text(encoding="utf-8")
            modified, did_change = op(original, *op_args)

            if not did_change:
                skipped_count += 1
                if args.verbose:
                    print(f"  - {path.relative_to(FACTORY_ROOT)} (no change)")
                continue

            changed_count += 1
            rel = path.relative_to(FACTORY_ROOT)

            if args.dry_run:
                print(f"  + [DRY] {rel}")
            else:
                if args.backup:
                    shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
                path.write_text(modified, encoding="utf-8")
                print(f"  + {rel}")

        except Exception as e:
            print(f"  [FAIL] {path.relative_to(FACTORY_ROOT)}: {e}")

    print()
    print(f"Result: {changed_count} changed, {skipped_count} skipped")

    if args.dry_run and changed_count > 0:
        print()
        print("Tip: drop --dry-run to apply the changes for real.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
