#!/usr/bin/env python3
"""
tia_export.py — TIA Portal Import Package Builder (Phase 25-D)

Copies the SCL files in the _output/scl/ folder into the folder structure
TIA Portal expects, and produces a pre-import checklist.

TIA Portal SCL import structure:
  tia_import/
    PLC_1/
      ProgramBlocks/
        FB_xxx.scl
        FC_xxx.scl
        OB_xxx.scl
      UserDefinedTypes/
        _types.scl   <- TYPE blocks
      GlobalDB/      <- (not automatic yet, in a later phase)
  IMPORT_CHECKLIST.md

CLI:
  python tia_export.py --project PROJECT_PATH [--plc-name PLC_1]
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# R-S-1: merkezi F-CPU tespit yardımcısı
try:
    from workbench.core.safety_utils import is_f_cpu as _is_f_cpu
except ImportError:  # pragma: no cover
    def _is_f_cpu(cpu_model):  # type: ignore[misc]
        import re as _re
        return bool(_re.search(r"(?i)(\bSF\b|^SF|\bTF\b|\dF[-\s/]|\dF$|\dTF[-\s/]|\dTF$|[-\s]F[-\s]|[-\s]F$)", cpu_model or ""))


FACTORY_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# IP Classification Guard — tia_export (I-1 grep sibling, line ~200)
# ---------------------------------------------------------------------------

_RESTRICTED_EXPORT_LEVELS = {"CONFIDENTIAL", "RESTRICTED"}
_KNOWN_EXPORT_LEVELS = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"}


class TIAExportClassificationError(Exception):
    """CONFIDENTIAL/RESTRICTED proje TIA dışa aktarımına izin vermez (IP koruyucu)."""


def _check_project_classification_for_export(
    project_path: Path,
    local_transfer_consent: bool = False,
) -> None:
    """Read the classification from PROJECT_STATE.json and gate the export.

    Fail-closed: missing file, missing field or parse error → assumed CONFIDENTIAL.

    M4 policy (SAFETY_CHANGES.md 2026-06-10): TIA export/import is a LOCAL
    machine transfer, not a cloud egress. CONFIDENTIAL is therefore allowed with
    explicit engineer approval (the caller audit-logs it). RESTRICTED is always
    blocked — consent has no effect.

    Raises:
        TIAExportClassificationError: always for RESTRICTED; for CONFIDENTIAL
        only when local_transfer_consent is not given.
    """
    classification = "CONFIDENTIAL"  # fail-closed default
    try:
        state_file = project_path / "PROJECT_STATE.json"
        if state_file.is_file():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            raw = (state.get("data_classification") or "").strip().upper()
            if raw in _KNOWN_EXPORT_LEVELS:
                classification = raw
            # Unknown value → fail-closed: stays CONFIDENTIAL
    except Exception:
        pass  # Parse error → fail-closed: stays CONFIDENTIAL

    if classification == "RESTRICTED":
        raise TIAExportClassificationError(
            f"RESTRICTED proje TIA dışa aktarımı reddedildi: {project_path}. "
            "Bu seviye için consent mekanizması ÇALIŞMAZ — her zaman bloklanır."
        )
    if classification == "CONFIDENTIAL" and not local_transfer_consent:
        raise TIAExportClassificationError(
            f"CONFIDENTIAL proje TIA dışa aktarımı mühendis onayı gerektirir: "
            f"{project_path}. Lokal aktarım onayını verin (AI_DECISION_LOG'a "
            "yazılır) veya PROJECT_STATE.json sınıflandırmasını düzeltin."
        )


# -- SCL block categories -----------------------------------------------------

def _classify_scl(content: str) -> str:
    """Return the TIA Portal folder based on the SCL content."""
    upper = content.upper()
    if re.search(r"\bFUNCTION_BLOCK\b", upper):
        return "ProgramBlocks"
    if re.search(r"\bFUNCTION\b(?!_BLOCK)", upper):
        return "ProgramBlocks"
    if re.search(r"\bORGANIZATION_BLOCK\b", upper):
        return "ProgramBlocks"
    if re.search(r"\bTYPE\b", upper):
        return "UserDefinedTypes"
    if re.search(r"\bDATA_BLOCK\b", upper):
        return "GlobalDB"
    return "ProgramBlocks"  # default


# -- Checklist builder --------------------------------------------------------

@dataclass
class CheckItem:
    category: str
    text: str
    status: str = "todo"  # todo / ok / warn / skip
    note: str = ""


def _build_checklist(project_path: Path, state: dict, scl_files: list[Path]) -> list[CheckItem]:
    items: list[CheckItem] = []

    # 1. Platform / TIA compatibility
    platform = state.get("target_platform", "")
    tia_ver  = state.get("target_tia_version", "")
    cpu      = state.get("target_cpu", "")

    if platform and tia_ver:
        items.append(CheckItem("TIA Portal", f"Opened with TIA Portal {tia_ver}", "todo"))
    else:
        items.append(CheckItem("TIA Portal", "Target TIA version not defined — set it in Project Settings", "warn"))

    if cpu:
        items.append(CheckItem("Hardware", f"{cpu} added to the hardware configuration", "todo"))
    else:
        items.append(CheckItem("Hardware", "CPU not defined — select it in Project Settings", "warn"))

    # 2. PROFINET / Network
    has_profinet = False
    hw01 = project_path / "metadata" / "HW01_BOM.md"
    if hw01.exists():
        if "PROFINET" in hw01.read_text(encoding="utf-8", errors="replace").upper():
            has_profinet = True
    if has_profinet:
        items.append(CheckItem("PROFINET", "GSDML files installed (from the Device catalog)", "todo"))
        items.append(CheckItem("PROFINET", "IO Device IP addresses assigned", "todo"))
        items.append(CheckItem("PROFINET", "Telegram 1 selected on high-speed devices (STW1/ZSW1)", "todo"))

    # 3. SCL files
    if scl_files:
        items.append(CheckItem("SCL Import", f"{len(scl_files)} SCL files ready", "ok",
                               ", ".join(f.name for f in scl_files[:3]) + ("..." if len(scl_files) > 3 else "")))
        items.append(CheckItem("SCL Import", "SCL files imported into TIA Portal via drag-and-drop", "todo"))
        items.append(CheckItem("SCL Import", "No compile errors", "todo"))
    else:
        items.append(CheckItem("SCL Import", "No SCL files found — run extraction first", "warn"))

    # 4. Tag table
    hw02 = project_path / "metadata" / "HW02_IO_Adresleme.md"
    if hw02.exists():
        items.append(CheckItem("Tag Table", "HW02_IO_Adresleme.md present — IO addresses verified", "ok"))
        items.append(CheckItem("Tag Table", "TIA Portal PLC tag table matches the IO addresses", "todo"))
    else:
        items.append(CheckItem("Tag Table", "HW02_IO_Adresleme.md missing — check %I/%Q addresses", "warn"))

    # 5. Safety
    has_safety = bool(state.get("selected_devices") and
                      any("F-" in d.get("device_id", "").upper() or
                          "SAFE" in d.get("device_id", "").upper()
                          for d in state.get("selected_devices", [])))
    if has_safety or _is_f_cpu(cpu):  # R-S-1: merkezi F-CPU tespiti (eski: "F" in cpu.upper() aşırı genişti)
        items.append(CheckItem("Safety", "Safety functions are DRAFT_UNVERIFIED — certified engineer approval is mandatory", "warn"))
        items.append(CheckItem("Safety", "F-CPU PROFIsafe addresses assigned", "todo"))
        items.append(CheckItem("Safety", "SIL/PLr verification approved by a certified engineer", "todo"))

    # 6. Simulation / FAT
    items.append(CheckItem("Test", "Simulation test done with PLCSIM (optional)", "skip"))
    items.append(CheckItem("Test", "FAT test protocol ready", "todo"))
    items.append(CheckItem("Test", "Customer FAT approval obtained", "todo"))

    return items


# -- Folder structure builder -------------------------------------------------

@dataclass
class ExportResult:
    tia_dir: Path
    copied: list[tuple[Path, Path]] = field(default_factory=list)  # (src, dst)
    checklist: list[CheckItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checklist_md: Optional[Path] = None


def prepare_tia_package(
    project_path: Path,
    plc_name: str = "PLC_1",
    overwrite: bool = False,
    local_transfer_consent: bool = False,
) -> ExportResult:
    """
    Prepare the TIA Portal import folder.

    Raises TIAExportClassificationError when the classification gate refuses
    (RESTRICTED always; CONFIDENTIAL without local_transfer_consent).
    """
    # I-1 grep kardeşi fix + M4 consent policy.
    _check_project_classification_for_export(
        project_path, local_transfer_consent=local_transfer_consent)

    state = {}
    state_file = project_path / "PROJECT_STATE.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # SCL source files (+ .db instance-DB sources from the M3 assembler)
    scl_dir  = project_path / "_output" / "scl"
    scl_files = (sorted(scl_dir.glob("*.scl")) + sorted(scl_dir.glob("*.db"))
                 if scl_dir.exists() else [])

    # Also any .scl directly in _output/
    output_dir = project_path / "_output"
    if output_dir.exists():
        scl_files += [f for f in output_dir.glob("*.scl") if f not in scl_files]

    result = ExportResult(
        tia_dir=project_path / "_output" / "tia_import",
        checklist=_build_checklist(project_path, state, scl_files),
    )

    if not scl_files:
        result.warnings.append(
            "No SCL files found. Run the 'MD -> SCL Extractor' first."
        )
        # Write the checklist anyway
    else:
        # Build the TIA Portal folder structure
        plc_dir         = result.tia_dir / plc_name
        prog_dir        = plc_dir / "ProgramBlocks"
        udt_dir         = plc_dir / "UserDefinedTypes"
        gdb_dir         = plc_dir / "GlobalDB"
        for d in [prog_dir, udt_dir, gdb_dir]:
            d.mkdir(parents=True, exist_ok=True)

        for scl_path in scl_files:
            try:
                content = scl_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                content = ""
            sub_dir = _classify_scl(content)
            dst_parent = {"ProgramBlocks": prog_dir,
                          "UserDefinedTypes": udt_dir,
                          "GlobalDB": gdb_dir}.get(sub_dir, prog_dir)
            dst = dst_parent / scl_path.name

            if dst.exists() and not overwrite:
                result.warnings.append(f"Skipped (exists): {dst.relative_to(result.tia_dir)}")
                continue

            shutil.copy2(str(scl_path), str(dst))
            result.copied.append((scl_path, dst))

    # Write the checklist MD
    result.checklist_md = _write_checklist_md(result)
    return result


def _write_checklist_md(result: ExportResult) -> Path:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# TIA Portal Import Checklist",
        "",
        "```yaml",
        f"created:   {ts}",
        f"tia_folder: {result.tia_dir}",
        "```",
        "",
        "Complete the items below before and after importing into TIA Portal:",
        "",
    ]

    current_cat = ""
    for item in result.checklist:
        if item.category != current_cat:
            current_cat = item.category
            lines.append(f"### {current_cat}")
            lines.append("")

        checkbox = "- [x]" if item.status == "ok" else "- [ ]"
        warn_prefix = "(!) " if item.status == "warn" else ("~~" if item.status == "skip" else "")
        warn_suffix = "~~" if item.status == "skip" else ""
        note = f" *(note: {item.note})*" if item.note else ""
        lines.append(f"{checkbox} {warn_prefix}{item.text}{warn_suffix}{note}")

    if result.copied:
        lines.append("")
        lines.append("### Copied SCL Files")
        lines.append("")
        for src, dst in result.copied:
            rel = dst.relative_to(result.tia_dir)
            lines.append(f"- `{rel}` <- `{src.name}`")

    if result.warnings:
        lines.append("")
        lines.append("### Warnings")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- (!) {w}")

    lines.append("")
    lines.append("---")
    lines.append(f"*AUTOMATION_FACTORY tia_export.py — {ts}*")

    out = result.tia_dir / "IMPORT_CHECKLIST.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def format_export_summary(result: ExportResult) -> str:
    lines = ["TIA Portal Package Summary", ""]
    lines.append(f"  Output folder : {result.tia_dir}")
    lines.append(f"  Copied SCL    : {len(result.copied)}")
    if result.copied:
        for src, dst in result.copied:
            lines.append(f"    [OK] {dst.relative_to(result.tia_dir)}")
    if result.warnings:
        lines.append("")
        lines.append("  Warnings:")
        for w in result.warnings:
            lines.append(f"    (!) {w}")
    if result.checklist_md:
        lines.append("")
        lines.append(f"  Checklist     : {result.checklist_md}")
    return "\n".join(lines)


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="TIA Portal Import Package Builder")
    p.add_argument("project", nargs="?", help="Project path")
    p.add_argument("--plc-name", default="PLC_1", help="TIA Portal PLC name (default: PLC_1)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    args = p.parse_args()

    if not args.project:
        p.print_help()
        return

    result = prepare_tia_package(Path(args.project),
                                 plc_name=args.plc_name,
                                 overwrite=args.overwrite)
    print(format_export_summary(result))


if __name__ == "__main__":
    main()
