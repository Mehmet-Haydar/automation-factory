#!/usr/bin/env python3
"""
ob1_generator.py — OB1 Auto Integrator (Phase 26-C)

Scans all FB and FC blocks in the _output/scl/ folder and generates an
OB1 (Organization Block) SCL file that calls them.

Generated OB1:
  - Adds all FBs as static instances in the VAR block
  - Calls all FBs and FCs in order
  - Siemens S7-1500 compatible (S7_Optimized_Access := 'TRUE')

CLI:
  python ob1_generator.py --project PROJECT_PATH [--ob-name OB_Main] [--overwrite]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


FACTORY_ROOT = Path(__file__).resolve().parent.parent


# -- Data structures ----------------------------------------------------------

@dataclass
class BlockInfo:
    block_type: str   # FB / FC / OB
    block_name: str
    source_file: Path
    has_input_vars: bool = False


@dataclass
class OB1GenResult:
    ob_name: str
    fb_blocks: list[BlockInfo] = field(default_factory=list)
    fc_blocks: list[BlockInfo] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    output_path: Optional[Path] = None
    warnings: list[str] = field(default_factory=list)


# -- SCL Scanner --------------------------------------------------------------

_BLOCK_PATTERNS = [
    (re.compile(r"^\s*FUNCTION_BLOCK\s+[\"']?(\w+)[\"']?", re.IGNORECASE | re.MULTILINE), "FB"),
    (re.compile(r"^\s*FUNCTION\s+[\"']?(\w+)[\"']?",       re.IGNORECASE | re.MULTILINE), "FC"),
    (re.compile(r"^\s*ORGANIZATION_BLOCK\s+[\"']?(\w+)[\"']?", re.IGNORECASE | re.MULTILINE), "OB"),
]

_VAR_INPUT_RE = re.compile(r"\bVAR_INPUT\b", re.IGNORECASE)


def scan_scl_blocks(scl_dir: Path) -> OB1GenResult:
    """Scan all blocks in the _output/scl/ folder."""
    result = OB1GenResult(ob_name="OB_Main")
    seen_names: set[str] = set()

    if not scl_dir.exists():
        result.warnings.append(f"SCL folder not found: {scl_dir}")
        return result

    for scl_file in sorted(scl_dir.glob("*.scl")):
        try:
            content = scl_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            result.skipped.append(f"{scl_file.name}: {e}")
            continue

        detected = False
        for pat, btype in _BLOCK_PATTERNS:
            m = pat.search(content)
            if not m:
                continue
            bname = m.group(1).strip().strip('"\'')

            # Do not list OB files as sources (except our own OB1)
            if btype == "OB":
                result.skipped.append(f"{scl_file.name}: OB block skipped (OBs are not included)")
                detected = True
                break

            if bname in seen_names:
                result.skipped.append(f"{scl_file.name}: '{bname}' already added, duplicate skipped")
                detected = True
                break

            seen_names.add(bname)
            has_input = bool(_VAR_INPUT_RE.search(content))
            block = BlockInfo(
                block_type=btype,
                block_name=bname,
                source_file=scl_file,
                has_input_vars=has_input,
            )
            if btype == "FB":
                result.fb_blocks.append(block)
            else:
                result.fc_blocks.append(block)
            detected = True
            break

        if not detected:
            result.skipped.append(f"{scl_file.name}: no known block type found")

    return result


# -- OB1 SCL Generator --------------------------------------------------------

def generate_ob1_scl(scan: OB1GenResult, ob_name: str = "OB_Main") -> str:
    """Generate OB1 SCL code from the scan result."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = []

    lines += [
        f"ORGANIZATION_BLOCK \"{ob_name}\"",
        "{ S7_Optimized_Access := 'TRUE' }",
        "AUTHOR : AUTOMATION_FACTORY",
        f"VERSION : 0.1",
        "",
        # // comments only: text inside a (* *) block (e.g. "(iDB_*)")
        # can contain "*)" and close the comment early — TIA then parses
        # the rest as code (seen in the 2026-06-10 V19 import test).
        "// OB1 — Auto-generated: AUTOMATION_FACTORY ob1_generator.py",
        f"// Date     : {ts}",
        f"// FB count : {len(scan.fb_blocks)}",
        f"// FC count : {len(scan.fc_blocks)}",
        "// WARNING: This code is DRAFT. Manual review is required.",
        "",
    ]

    # VAR block — FB static instances
    lines.append("VAR")
    if scan.fb_blocks:
        for fb in scan.fb_blocks:
            inst = _make_instance_name(fb.block_name)
            lines.append(f"    {inst} : \"{fb.block_name}\";")
    else:
        lines.append("    // No FB found")
    lines += ["END_VAR", ""]

    # VAR_TEMP — if needed
    lines += [
        "VAR_TEMP",
        "    // Temporary variables can be added here",
        "END_VAR",
        "",
        "BEGIN",
        "",
    ]

    # FB calls
    if scan.fb_blocks:
        lines.append("    // -- Function Block calls --")
        for fb in scan.fb_blocks:
            inst = _make_instance_name(fb.block_name)
            lines += [
                f"    // {fb.block_name}",
                f"    \"{inst}\"(",
            ]
            if fb.has_input_vars:
                lines.append("        // Bind input parameters")
            lines += ["    );", ""]

    # FC calls
    if scan.fc_blocks:
        lines.append("    // -- Function calls --")
        for fc in scan.fc_blocks:
            lines += [
                f"    // {fc.block_name}",
                f"    \"{fc.block_name}\"();",
                "",
            ]

    if not scan.fb_blocks and not scan.fc_blocks:
        lines += [
            "    // No FB/FC to call found.",
            "    // Add SCL files to the _output/scl/ folder.",
        ]

    lines += [
        f"END_ORGANIZATION_BLOCK",
    ]

    return "\n".join(lines)


def _make_instance_name(block_name: str) -> str:
    """Generate an instance variable name from an FB name (prefix 'inst_')."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", block_name)
    return f"inst_{clean}"


# -- M3: device-map based OB1 (library-first assembler) ------------------------
#
# The legacy scan mode above declares FB instances in an OB VAR block — TIA
# Portal rejects that (OBs have no instance memory). The assembler path below
# calls single-instance DBs ("iDB_X"(...)) with real parameter bindings, which
# compiles cleanly as an external source.

@dataclass
class InstanceCall:
    """One FB instance call inside OB1, fed by program_assembler."""
    instance_db: str                  # e.g. iDB_MOT_CONV_001
    fb_name: str                      # FUNCTION_BLOCK name as declared in SCL
    comment: str = ""                 # human context (device + description)
    in_bindings: dict = field(default_factory=dict)    # port -> IEC tag name
    out_bindings: dict = field(default_factory=dict)   # port -> IEC tag name
    todos: list = field(default_factory=list)          # unwired ports etc.


def generate_ob1_from_instances(
    calls: list[InstanceCall],
    ob_name: str = "OB_Main",
) -> str:
    """OB1 SCL from explicit instance calls — no OB-static VAR block."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        f"ORGANIZATION_BLOCK \"{ob_name}\"",
        "{ S7_Optimized_Access := 'TRUE' }",
        "AUTHOR : AUTOMATION_FACTORY",
        "VERSION : 0.1",
        "",
        # // comments only — "(iDB_*)" inside a (* *) block closes the
        # comment at "*)" and TIA parses the rest as code (2026-06-10
        # V19 import test: "Syntax error: '.'", "'DRAFT' invalid").
        "// OB1 — assembled by AUTOMATION_FACTORY program_assembler",
        f"// Date      : {ts}",
        f"// Instances : {len(calls)}",
        "// Library FBs are called via single-instance DBs (iDB_*).",
        "// WARNING: DRAFT — engineer review + TIA compile required.",
        "",
        "VAR_TEMP",
        "    // Temporary variables can be added here",
        "END_VAR",
        "",
        "BEGIN",
        "",
    ]

    if not calls:
        lines.append("    // No instances — assembler produced an empty map.")

    for c in calls:
        if c.comment:
            lines.append(f"    // {c.comment}")
        params: list[str] = []
        for port, tag in c.in_bindings.items():
            params.append(f"        {port} := \"{tag}\"")
        for port, tag in c.out_bindings.items():
            params.append(f"        {port} => \"{tag}\"")
        if params:
            lines.append(f"    \"{c.instance_db}\"(")
            lines.append(",\n".join(params))
            lines.append("    );")
        else:
            lines.append(f"    \"{c.instance_db}\"();")
        for todo in c.todos:
            lines.append(f"    // TODO(#UNKNOWN): {todo}")
        lines.append("")

    lines.append("END_ORGANIZATION_BLOCK")
    return "\n".join(lines)


def generate_instance_db(instance_db: str, fb_name: str) -> str:
    """Single-instance DB source (TIA external source, .db file)."""
    return "\n".join([
        f"DATA_BLOCK \"{instance_db}\"",
        "{ S7_Optimized_Access := 'TRUE' }",
        f"\"{fb_name}\"",
        "",
        "BEGIN",
        "",
        "END_DATA_BLOCK",
        "",
    ])


# -- Writer -------------------------------------------------------------------

def write_ob1(
    project_path: Path,
    ob_name: str = "OB_Main",
    overwrite: bool = False,
) -> OB1GenResult:
    """Full pipeline: scan -> generate -> write."""
    scl_dir = project_path / "_output" / "scl"
    scan = scan_scl_blocks(scl_dir)
    scan.ob_name = ob_name

    # Warn if a FB/FC collides with the OB1's own name
    all_names = [b.block_name for b in scan.fb_blocks + scan.fc_blocks]
    if ob_name in all_names:
        scan.warnings.append(f"A FB/FC named '{ob_name}' exists — OB name may collide")

    scl_content = generate_ob1_scl(scan, ob_name)
    out_path = scl_dir / f"{ob_name}.scl"

    if out_path.exists() and not overwrite:
        scan.warnings.append(
            f"{out_path.name} already exists (not overwritten without --overwrite)"
        )
        scan.output_path = out_path
        return scan

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(scl_content, encoding="utf-8")
    scan.output_path = out_path
    return scan


def format_ob1_summary(result: OB1GenResult) -> str:
    lines = ["OB1 Integrator Summary", ""]
    lines.append(f"  OB name     : {result.ob_name}")
    lines.append(f"  FB blocks   : {len(result.fb_blocks)}")
    for fb in result.fb_blocks:
        lines.append(f"    [OK] {fb.block_name} ({fb.source_file.name})")
    lines.append(f"  FC blocks   : {len(result.fc_blocks)}")
    for fc in result.fc_blocks:
        lines.append(f"    [OK] {fc.block_name} ({fc.source_file.name})")
    if result.skipped:
        lines.append(f"  Skipped     : {len(result.skipped)}")
        for s in result.skipped:
            lines.append(f"    [SKIP] {s}")
    if result.output_path:
        lines.append(f"  Output      : {result.output_path}")
    if result.warnings:
        lines.append("")
        for w in result.warnings:
            lines.append(f"  [WARN] {w}")
    return "\n".join(lines)


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="OB1 Auto Integrator")
    p.add_argument("--project", metavar="PROJECT_PATH", required=True)
    p.add_argument("--ob-name", default="OB_Main", help="OB block name (default: OB_Main)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite an existing OB1 file")
    args = p.parse_args()

    result = write_ob1(Path(args.project), ob_name=args.ob_name, overwrite=args.overwrite)
    print(format_ob1_summary(result))


if __name__ == "__main__":
    main()
