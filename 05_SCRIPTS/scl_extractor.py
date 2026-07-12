#!/usr/bin/env python3
"""
scl_extractor.py — Markdown -> SCL Extractor (Phase 25-B)

Extracts SCL code blocks from .md files saved as AI output and writes them
as TIA Portal-compatible .scl files into the _output/scl/ folder.

Supported code-fence tags: ```scl, ```iec, ```st, ```iec61131
Block-type detection:
  FUNCTION_BLOCK <name>   -> FB_<name>.scl
  FUNCTION <name>         -> FC_<name>.scl
  ORGANIZATION_BLOCK <name> -> OB_<name>.scl
  If not detected          -> BLOCK_<file>_<n>.scl

CLI:
  python scl_extractor.py --project PROJECT_PATH
  python scl_extractor.py FILE.md [FILE2.md ...]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Code-fence tags (case-insensitive)
SCL_FENCE_TAGS = {"scl", "iec", "iec61131", "st", "structured text"}


@dataclass
class ExtractedBlock:
    source_md: Path
    block_index: int       # Sequence number within the file (starts at 1)
    block_type: str        # FB / FC / OB / UNKNOWN
    block_name: str        # FUNCTION_BLOCK name, else ""
    content: str
    output_path: Optional[Path] = None
    skipped: bool = False
    skip_reason: str = ""

    @property
    def suggested_filename(self) -> str:
        if self.block_type != "UNKNOWN" and self.block_name:
            return f"{self.block_type}_{self.block_name}.scl"
        stem = re.sub(r"[^\w]", "_", self.source_md.stem)
        return f"BLOCK_{stem}_{self.block_index}.scl"


@dataclass
class ExtractionResult:
    source_md: Path
    blocks: list[ExtractedBlock] = field(default_factory=list)

    @property
    def extracted_count(self) -> int:
        return sum(1 for b in self.blocks if not b.skipped)

    @property
    def skipped_count(self) -> int:
        return sum(1 for b in self.blocks if b.skipped)


# -- Extraction ---------------------------------------------------------------

def _detect_block_type(scl_content: str) -> tuple[str, str]:
    """Find the first block declaration -> (type, name)."""
    patterns = [
        (r"^\s*FUNCTION_BLOCK\s+(\S+)", "FB"),
        (r"^\s*FUNCTION\s+(\S+)", "FC"),
        (r"^\s*ORGANIZATION_BLOCK\s+(\S+)", "OB"),
    ]
    for pat, btype in patterns:
        m = re.search(pat, scl_content, re.IGNORECASE | re.MULTILINE)
        if m:
            name = m.group(1).strip()
            # Trim anything after a semicolon or space
            name = re.split(r"[\s;]", name)[0]
            return btype, name
    return "UNKNOWN", ""


def extract_from_md(md_path: Path) -> ExtractionResult:
    """Extract SCL blocks from a single .md file."""
    result = ExtractionResult(source_md=md_path)
    try:
        content = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return result

    # Find all ``` blocks
    fence_pattern = re.compile(
        r"```[ \t]*(\w[\w\s]*?)[ \t]*\n(.*?)```",
        re.DOTALL | re.IGNORECASE,
    )

    block_index = 0
    for match in fence_pattern.finditer(content):
        lang_tag = match.group(1).strip().lower()
        code_body = match.group(2)

        if lang_tag not in SCL_FENCE_TAGS:
            continue

        block_index += 1
        stripped = code_body.strip()

        if len(stripped) < 20:
            result.blocks.append(ExtractedBlock(
                source_md=md_path, block_index=block_index,
                block_type="UNKNOWN", block_name="",
                content=stripped, skipped=True,
                skip_reason="Block too short (<20 chars)",
            ))
            continue

        btype, bname = _detect_block_type(stripped)
        result.blocks.append(ExtractedBlock(
            source_md=md_path, block_index=block_index,
            block_type=btype, block_name=bname,
            content=stripped,
        ))

    return result


def extract_all_from_project(project_path: Path) -> list[ExtractionResult]:
    """Scan .md files in _output/ and metadata/ for SCL code blocks."""
    results = []
    seen: set[Path] = set()
    scan_dirs = [project_path / "_output", project_path / "metadata"]
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for md_file in sorted(scan_dir.glob("*.md")):
            if md_file in seen:
                continue
            seen.add(md_file)
            res = extract_from_md(md_file)
            if res.blocks:
                results.append(res)
    return results


# -- Writing ------------------------------------------------------------------

def write_blocks(
    results: list[ExtractionResult],
    output_dir: Path,
    overwrite: bool = False,
) -> list[ExtractedBlock]:
    """Write extracted blocks as .scl files. Returns the list of written blocks."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[ExtractedBlock] = []

    # Counter to avoid name collisions
    name_counts: dict[str, int] = {}

    for res in results:
        for block in res.blocks:
            if block.skipped:
                continue

            fname = block.suggested_filename
            # Collision check
            key = fname.lower()
            if key in name_counts:
                name_counts[key] += 1
                stem, ext = fname.rsplit(".", 1)
                fname = f"{stem}_{name_counts[key]}.{ext}"
            else:
                name_counts[key] = 1

            out_path = output_dir / fname
            if out_path.exists() and not overwrite:
                block.skipped = True
                block.skip_reason = f"File already exists: {fname} (use --overwrite)"
                continue

            out_path.write_text(block.content + "\n", encoding="utf-8")
            block.output_path = out_path
            written.append(block)

    return written


def run_extraction(
    project_path: Path,
    overwrite: bool = False,
    auto_validate: bool = True,
) -> dict:
    """
    Full pipeline: extract -> write -> (validate).
    Returns: {results, written, validation, scl_dir}
    """
    results = extract_all_from_project(project_path)
    scl_dir = project_path / "_output" / "scl"
    written = write_blocks(results, scl_dir, overwrite=overwrite)

    validation = None
    if auto_validate and written:
        try:
            from scl_validator import validate_scl_file
            validation = [validate_scl_file(b.output_path) for b in written if b.output_path]
        except ImportError:
            pass

    return {
        "results": results,
        "written": written,
        "validation": validation,
        "scl_dir": scl_dir,
    }


def format_extraction_summary(run_result: dict) -> str:
    lines = []
    results  = run_result["results"]
    written  = run_result["written"]
    val_list = run_result.get("validation") or []
    scl_dir  = run_result["scl_dir"]

    total_found   = sum(len(r.blocks) for r in results)
    total_written = len(written)
    total_skipped = total_found - total_written

    lines.append(f"SCL Extraction Summary")
    lines.append(f"   Scanned .md files : {len(results)}")
    lines.append(f"   SCL blocks found  : {total_found}")
    lines.append(f"   .scl files written: {total_written}")
    if total_skipped:
        lines.append(f"   Skipped           : {total_skipped}")
    lines.append(f"   Output folder     : {scl_dir}")
    lines.append("")

    if written:
        lines.append("Written files:")
        for b in written:
            fname = b.output_path.name if b.output_path else "?"
            binfo = f"  {b.block_type}" + (f": {b.block_name}" if b.block_name else "")
            lines.append(f"  [OK] {fname}{binfo}")

    # Skipped
    all_blocks = [b for r in results for b in r.blocks if b.skipped]
    if all_blocks:
        lines.append("\nSkipped:")
        for b in all_blocks:
            lines.append(f"  [SKIP] {b.source_md.name}[{b.block_index}]: {b.skip_reason}")

    # Validation
    if val_list:
        lines.append("\nValidation Results:")
        total_errors = sum(r.error_count for r in val_list)
        if total_errors == 0:
            lines.append(f"  [OK] {len(val_list)} files — no errors")
        else:
            for vr in val_list:
                icon = "[FAIL]" if vr.has_errors else ("[WARN]" if vr.warning_count else "[OK]")
                lines.append(f"  {icon} {vr.path.name} — {vr.error_count} errors, {vr.warning_count} warnings")
                for iss in vr.issues:
                    if iss.severity == "error":
                        lines.append(f"      x {iss.message}")

    return "\n".join(lines)


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="Markdown -> SCL Extractor")
    p.add_argument("files", nargs="*", metavar="MD_FILE", help=".md files")
    p.add_argument("--project", metavar="PROJECT_PATH", help="Scan the project _output/ folder")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing .scl files")
    p.add_argument("--no-validate", action="store_true", help="Skip the validation step")
    args = p.parse_args()

    if args.project:
        run = run_extraction(
            Path(args.project),
            overwrite=args.overwrite,
            auto_validate=not args.no_validate,
        )
        print(format_extraction_summary(run))
        sys.exit(0 if run["written"] else 1)

    if args.files:
        results = [extract_from_md(Path(f)) for f in args.files]
        out_dir = Path(args.files[0]).parent / "scl"
        written = write_blocks(results, out_dir, overwrite=args.overwrite)
        run = {"results": results, "written": written, "validation": None, "scl_dir": out_dir}
        if not args.no_validate:
            try:
                from scl_validator import validate_scl_file
                run["validation"] = [validate_scl_file(b.output_path) for b in written if b.output_path]
            except ImportError:
                pass
        print(format_extraction_summary(run))
        sys.exit(0 if written else 1)

    p.print_help()


if __name__ == "__main__":
    main()
