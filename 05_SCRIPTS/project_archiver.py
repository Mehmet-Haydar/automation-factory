#!/usr/bin/env python3
"""
project_archiver.py — Project Archiving and Delivery Zip (Phase 27-D)

Selectively zips a customer project into a delivery package.

Package types:
  FULL     : Whole project (metadata + _output, excluding _input raw data)
  DELIVERY : Deliverables only (_output + metadata)
  SCL_ONLY : SCL code only (_output/scl/)
  REPORT   : Reports only (_output/*.md, _output/*.xlsx)

Automatically EXCLUDED (safety):
  - _input/ (raw customer data)
  - *.log, *.tmp
  - __pycache__/, *.pyc
  - .backup_* files
  - .gui_settings.json (may contain API keys)

CLI:
  python project_archiver.py --project PROJECT_PATH [--type DELIVERY] [--out FOLDER]
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


FACTORY_ROOT = Path(__file__).resolve().parent.parent

# Always-excluded patterns
_EXCLUDE_PATTERNS = {
    "_input",           # Raw customer data
    ".gui_settings",    # API keys
    "__pycache__",
    ".backup_",
    ".git",
}
_EXCLUDE_SUFFIXES = {".pyc", ".log", ".tmp", ".bak"}


# -- Data structures ----------------------------------------------------------

@dataclass
class ArchiveResult:
    archive_path: Optional[Path] = None
    included: list[Path] = field(default_factory=list)
    excluded: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    size_bytes: int = 0
    package_type: str = "DELIVERY"

    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


# -- File filters -------------------------------------------------------------

def _should_exclude(rel_path: Path) -> bool:
    """Should the file be excluded from the archive?"""
    parts_lower = {p.lower() for p in rel_path.parts}

    for excl in _EXCLUDE_PATTERNS:
        if any(excl in p for p in parts_lower):
            return True

    if rel_path.suffix.lower() in _EXCLUDE_SUFFIXES:
        return True

    return False


def _collect_files(project_path: Path, package_type: str) -> tuple[list[Path], list[Path]]:
    """
    Return the included/excluded file list per package type.
    Returns: (included, excluded)
    """
    included: list[Path] = []
    excluded: list[Path] = []

    for f in project_path.rglob("*"):
        if not f.is_file():
            continue

        rel = f.relative_to(project_path)

        # Universal exclusions
        if _should_exclude(rel):
            excluded.append(f)
            continue

        # Filter by package type
        keep = False
        top = rel.parts[0].lower() if rel.parts else ""

        if package_type == "FULL":
            keep = True

        elif package_type == "DELIVERY":
            # metadata/ + _output/ + PROJECT_STATE + PROJECT_MAESTRO
            if top in ("metadata", "_output"):
                keep = True
            elif f.name in ("PROJECT_STATE.json", "PROJECT_MAESTRO.md"):
                keep = True

        elif package_type == "SCL_ONLY":
            # _output/scl/*.scl
            if top == "_output" and "scl" in rel.parts and f.suffix.lower() == ".scl":
                keep = True

        elif package_type == "REPORT":
            # _output/*.md and _output/*.xlsx (excluding the scl/ subfolder)
            if top == "_output" and len(rel.parts) == 2:
                if f.suffix.lower() in (".md", ".xlsx", ".pdf"):
                    keep = True

        if keep:
            included.append(f)
        else:
            excluded.append(f)

    return included, excluded


# -- Archive builder ----------------------------------------------------------

def create_archive(
    project_path: Path,
    package_type: str = "DELIVERY",
    output_dir: Optional[Path] = None,
    include_manifest: bool = True,
) -> ArchiveResult:
    """
    Create the project archive.

    package_type: FULL / DELIVERY / SCL_ONLY / REPORT
    output_dir:   folder to save the zip in (None = parent of project)
    """
    result = ArchiveResult(package_type=package_type)

    if not project_path.exists():
        result.warnings.append(f"Project folder not found: {project_path}")
        return result

    # Project info from the STATE file
    state: dict = {}
    state_file = project_path / "PROJECT_STATE.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    zip_name = f"{project_path.name}_{package_type}_{ts}.zip"

    dest_dir = output_dir or project_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    archive_path = dest_dir / zip_name

    included, excluded = _collect_files(project_path, package_type)
    result.included = included
    result.excluded = excluded

    if not included:
        result.warnings.append(f"No files to include for package type ({package_type}).")
        return result

    # Write ZIP
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in included:
            arcname = f.relative_to(project_path)
            zf.write(f, arcname)

        # Manifest file
        if include_manifest:
            manifest = _build_manifest(project_path, state, included, excluded, package_type)
            zf.writestr("ARCHIVE_MANIFEST.md", manifest)

    result.archive_path = archive_path
    result.size_bytes = archive_path.stat().st_size
    return result


def _build_manifest(
    project_path: Path,
    state: dict,
    included: list[Path],
    excluded: list[Path],
    package_type: str,
) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    platform = state.get("target_platform", "-")
    cpu      = state.get("target_cpu", "-")
    tia_ver  = state.get("target_tia_version", "-")

    lines = [
        "# Archive Manifest",
        "",
        "```yaml",
        f"project:     {project_path.name}",
        f"package_type:{package_type}",
        f"created:     {ts}",
        f"platform:    {platform}",
        f"cpu:         {cpu}",
        f"tia_version: {tia_ver}",
        f"file_count:  {len(included)}",
        "```",
        "",
        "## Included Files",
        "",
    ]
    for f in sorted(included, key=lambda x: str(x)):
        rel = f.relative_to(project_path)
        size = f.stat().st_size
        lines.append(f"- `{rel}` ({size:,} bytes)")

    lines += [
        "",
        "## Excluded Categories",
        "",
        "- `_input/` — raw customer data (CONFIDENTIAL)",
        "- `.gui_settings.json` — API keys",
        "- `__pycache__/`, `*.pyc`",
        "- `.backup_*` — backup files",
        "",
        "---",
        f"*AUTOMATION_FACTORY project_archiver.py — {ts}*",
    ]
    return "\n".join(lines)


def format_archive_summary(result: ArchiveResult) -> str:
    lines = ["Project Archive Summary", ""]
    lines.append(f"  Package type : {result.package_type}")
    if result.archive_path:
        lines.append(f"  Zip file     : {result.archive_path.name}")
        if result.size_mb >= 1:
            lines.append(f"  Size         : {result.size_mb:.1f} MB")
        else:
            lines.append(f"  Size         : {result.size_kb:.1f} KB")
    lines.append(f"  Included     : {len(result.included)} files")
    lines.append(f"  Excluded     : {len(result.excluded)} files")
    if result.warnings:
        lines.append("")
        for w in result.warnings:
            lines.append(f"  [WARN] {w}")
    return "\n".join(lines)


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="Project Archiving and Delivery Zip")
    p.add_argument("--project", metavar="PROJECT_PATH", required=True)
    p.add_argument(
        "--type", choices=["FULL", "DELIVERY", "SCL_ONLY", "REPORT"],
        default="DELIVERY",
        help="Package type (default: DELIVERY)",
    )
    p.add_argument("--out", metavar="FOLDER", help="Zip output folder")
    args = p.parse_args()

    result = create_archive(
        Path(args.project),
        package_type=args.type,
        output_dir=Path(args.out) if args.out else None,
    )
    print(format_archive_summary(result))
    if result.archive_path:
        print(f"\nZip: {result.archive_path}")


if __name__ == "__main__":
    main()
