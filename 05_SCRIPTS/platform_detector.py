#!/usr/bin/env python3
"""
platform_detector.py — Auto-detect legacy PLC platform

Scans the _input/ folder, detects the platform via file extension + content analysis.

Supported platforms:
- Siemens S5 (.s5d, OCR'd AWL PDF)
- Siemens S7-300/400 Classic (.awl, .scl)
- Siemens S7-1500 TIA Portal (.xml Openness, .scl)

NOTE on project archives (.s7p, .zap*, .ap*): these are DETECTED so the
platform badge is right, but their CONTENT is never extracted — the pipeline
reads text sources only. The engineer must export AWL/SCL sources from
SIMATIC Manager / TIA Portal first (the GUI shows format-specific steps).
- Allen-Bradley (.L5X, .L5K, .ACD)
- Beckhoff TwinCAT (.tsproj, .tmc, PLCopen XML)
- CODESYS V3 (.project, .library, PLCopen XML)
- Schneider EcoStruxure (.stproject)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Extension -> platform candidates
EXT_TO_PLATFORMS = {
    ".s5d": ["S5"],
    ".ini": ["S5"],   # STEP 5 symbol table / Zuordnungsliste zone file
    ".seq": ["S5"],   # STEP 5 sequence export / zone program file
    ".s7p": ["S7_300", "S7_400"],
    ".awl": ["S5", "S7_300", "S7_400"],
    ".scl": ["S7_300", "S7_400", "S7_1500", "CODESYS"],
    ".gr7": ["S7_300", "S7_400"],
    ".l5x": ["AB_L5X"],
    ".l5k": ["AB_L5X"],
    ".acd": ["AB_L5X"],
    ".tsproj": ["BECKHOFF"],
    ".tmc": ["BECKHOFF"],
    ".project": ["CODESYS"],
    ".library": ["CODESYS"],
    ".stproject": ["SCHNEIDER"],
    ".zap25": ["S7_300", "S7_400"],
    ".zap14": ["S7_300", "S7_400"],
    ".zap18": ["S7_1500"],
    ".zap19": ["S7_1500"],
    ".ap18": ["S7_1500"],
    ".ap19": ["S7_1500"],
    ".xml": ["S7_1500", "BECKHOFF", "CODESYS", "AB_L5X"],
}

# Platform -> AI prompt (analyze)
PLATFORM_TO_PROMPT = {
    "S5": "analyze/PROMPT_ANALYZE_S5_AWL.md",
    "S7_300": "analyze/PROMPT_ANALYZE_S7_300_STL.md",
    "S7_400": "analyze/PROMPT_ANALYZE_S7_400_STL.md",  # B-L6 / S-21: dedicated S7-400 parser
    "S7_1500": "analyze/PROMPT_ANALYZE_S7_1500_OPENNESS.md",
    "AB_L5X": "analyze/PROMPT_ANALYZE_AB_L5X.md",
    "BECKHOFF": "analyze/PROMPT_ANALYZE_CODESYS.md",
    "CODESYS": "analyze/PROMPT_ANALYZE_CODESYS.md",
    "SCHNEIDER": "analyze/PROMPT_ANALYZE_CODESYS.md",
}

# Content patterns (matched when reading the file body)
CONTENT_PATTERNS = {
    "S5": [
        rb"STEP 5",
        rb"FB \d+\s+NAME",
        rb"\bSPB\b|\bSPA\b|\bBE\b\s",  # S5 AWL mnemonics
        rb"[EAM]\s{1,4}\d+\.\d+",       # S5 address format: E 4.0 / A 28.0 / M 1.0
        rb"\bPB\s+\d+\b",               # Program Block reference (PB 1, PB 11 …)
    ],
    "S7_300": [
        rb"STEP 7",
        rb"SIMATIC\s+S7-300",
        rb"\bCALL FB\b|\bCALL FC\b",
        rb"VERSION\s*:\s*5\.",  # STEP 7 V5
    ],
    "S7_400": [
        rb"SIMATIC\s+S7-400",
        rb"\bCPU\s*41[2467]\b",        # CPU 412/414/416/417 family
        rb"\b6ES7\s*41[2467]-",        # CPU 41x order numbers
        rb"S7[-_ ]?400H|41[2467]-\d+H",  # H-system (redundant)
    ],
    "S7_1500": [
        rb"TIA Portal V1[4-9]",
        rb"S7-1500",
        rb"<Engineering version=\"V1[4-9]",
        rb"Optimized_Access\s*:=\s*'TRUE'",
    ],
    "AB_L5X": [
        rb"<RSLogix5000Content",
        rb"<Controller Use=\"Target\"",
        rb"<AddOnInstructionDefinition",
        rb"ControlLogix|CompactLogix|GuardLogix",
    ],
    "BECKHOFF": [
        rb"TcSmProject",
        rb"<TcModuleClass",
        rb"<NcAxis",
        rb"TwinCAT",
    ],
    "CODESYS": [
        rb"CODESYS Development System",
        rb"<plcopenxml",
        rb"VAR_GLOBAL\s+PERSISTENT",
    ],
    "SCHNEIDER": [
        rb"EcoStruxure|Schneider Electric",
        rb"Modicon\s+M\d+",
    ],
}

PLATFORM_DISPLAY = {
    "S5": "Siemens S5 (legacy)",
    "S7_300": "Siemens S7-300 Classic",
    "S7_400": "Siemens S7-400 Classic",
    "S7_1500": "Siemens S7-1500 (TIA Portal)",
    "AB_L5X": "Allen-Bradley (Studio 5000)",
    "BECKHOFF": "Beckhoff TwinCAT 3",
    "CODESYS": "CODESYS V3",
    "SCHNEIDER": "Schneider EcoStruxure",
}


@dataclass
class FileInfo:
    """A single detected file."""
    path: Path
    size_bytes: int
    extension: str
    platforms: list[str] = field(default_factory=list)  # platforms indicated by this file
    role: str = ""  # "source_code" / "config" / "documentation" / "data"
    notes: str = ""


@dataclass
class ProjectScan:
    """Scan of one _input/ folder."""
    input_path: Path
    files: list[FileInfo] = field(default_factory=list)
    detected_platforms: dict[str, int] = field(default_factory=dict)  # platform -> confidence score
    primary_platform: str = ""
    confidence: str = "low"  # low / medium / high
    total_size_mb: float = 0.0


def detect_platform_from_filename(filename: str) -> list[str]:
    """Return possible platforms based on file extension."""
    ext = Path(filename).suffix.lower()
    return EXT_TO_PLATFORMS.get(ext, [])


def detect_platform_from_content(file_path: Path, max_bytes: int = 50_000) -> list[str]:
    """Read file body and detect platform via pattern matching."""
    try:
        with open(file_path, "rb") as f:
            data = f.read(max_bytes)
    except Exception:
        return []

    matches = []
    for platform, patterns in CONTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, data, re.IGNORECASE):
                matches.append(platform)
                break
    return matches


def categorize_file_role(filename: str, ext: str) -> str:
    """Guess the file's role."""
    name = filename.lower()
    if ext in [".awl", ".scl", ".st", ".gr7", ".sfc", ".l5x", ".l5k", ".xml", ".seq"]:
        return "source_code"
    if ext in [".ini"]:
        return "config"   # STEP 5 symbol table (Zuordnungsliste)
    if ext in [".s5d", ".acd", ".tsproj", ".project", ".s7p", ".ap18", ".ap19", ".zap18", ".zap19"]:
        return "project_archive"
    if ext in [".pdf", ".doc", ".docx"]:
        return "documentation"
    if ext in [".xlsx", ".xls", ".csv"]:
        return "data"
    if ext in [".jpg", ".jpeg", ".png", ".bmp"]:
        return "image"  # scan/screenshot
    if "config" in name or "hw" in name:
        return "config"
    if "manual" in name or "operating" in name:
        return "documentation"
    return "other"


def scan_input_folder(input_path: Path,
                      extra_dirs: Optional[list] = None) -> ProjectScan:
    """Recursively scan the _input/ folder, analyze platforms + files.

    S-8 (B-L10): *extra_dirs* lets the caller include further source roots —
    project_analyzer passes ``_raw/legacy_code`` so the platform badge and
    the pre-analysis pipeline read the SAME files instead of two diverging
    truths (_input/ vs _raw/).
    """
    scan = ProjectScan(input_path=input_path)

    roots = [d for d in [input_path, *(extra_dirs or [])]
             if d is not None and Path(d).exists() and Path(d).is_dir()]
    if not roots:
        return scan

    total_bytes = 0

    # Recursive scan over every root (deduplicated)
    seen: set = set()
    candidates = []
    for root in roots:
        for file_path in Path(root).rglob("*"):
            if file_path in seen:
                continue
            seen.add(file_path)
            candidates.append(file_path)

    for file_path in candidates:
        if not file_path.is_file():
            continue
        # Skip backups and hidden files
        if file_path.name.startswith(".") or file_path.name.startswith("_parsed"):
            continue
        if file_path.suffix.lower() in [".bak", ".tmp"]:
            continue

        try:
            size = file_path.stat().st_size
        except Exception:
            size = 0
        total_bytes += size

        ext = file_path.suffix.lower()
        ext_platforms = detect_platform_from_filename(file_path.name)

        # Content scan — text/xml/awl/scl and S5-specific formats
        content_platforms = []
        if ext in [".xml", ".awl", ".scl", ".st", ".l5x", ".l5k", ".gr7", ".tsproj", ".project", ".tmc", ".txt",
                   ".ini", ".seq"]:
            if size < 5 * 1024 * 1024:  # max 5MB to scan
                content_platforms = detect_platform_from_content(file_path)

        # Merge (content > extension)
        all_platforms = list(set(ext_platforms + content_platforms))

        file_info = FileInfo(
            path=file_path,
            size_bytes=size,
            extension=ext,
            platforms=all_platforms,
            role=categorize_file_role(file_path.name, ext),
        )
        if content_platforms:
            file_info.notes = "(confirmed via content analysis)"
        elif file_info.role == "project_archive":
            file_info.notes = "(archive — content NOT read; export AWL/SCL sources)"
        scan.files.append(file_info)

    scan.total_size_mb = total_bytes / (1024 * 1024)

    # Platform votes — 1 point per platform indicated by each file
    # Content-matched ones get 2 points (archive note must NOT double-count)
    votes: dict[str, int] = {}
    for fi in scan.files:
        for plat in fi.platforms:
            weight = 2 if "confirmed" in fi.notes else 1
            votes[plat] = votes.get(plat, 0) + weight

    scan.detected_platforms = dict(sorted(votes.items(), key=lambda x: -x[1]))

    # Primary platform = highest vote + single-platform-wide lead
    if scan.detected_platforms:
        top_items = list(scan.detected_platforms.items())
        scan.primary_platform = top_items[0][0]
        top_score = top_items[0][1]
        # Confidence
        if top_score >= 5 and (len(top_items) < 2 or top_items[1][1] < top_score / 2):
            scan.confidence = "high"
        elif top_score >= 3:
            scan.confidence = "medium"
        else:
            scan.confidence = "low"

    return scan


def get_recommended_prompt(platform: str) -> str:
    """Return the recommended AI analyze prompt for the platform."""
    return PLATFORM_TO_PROMPT.get(platform, "analyze/PROMPT_ANALYZE_S7_1500_OPENNESS.md")


def format_scan_report(scan: ProjectScan) -> str:
    """Return the scan report as human-readable text."""
    lines = []
    lines.append(f"FOLDER: {scan.input_path}")
    lines.append(f"TOTAL:  {len(scan.files)} files, {scan.total_size_mb:.2f} MB")
    lines.append("")

    if not scan.files:
        lines.append("WARNING: _input/ folder is EMPTY or not found.")
        lines.append("Put the customer's legacy PLC code in this folder first.")
        return "\n".join(lines)

    # Platform detection
    lines.append("PLATFORM DETECTION:")
    if scan.primary_platform:
        display = PLATFORM_DISPLAY.get(scan.primary_platform, scan.primary_platform)
        lines.append(f"   Primary:   {display}")
        lines.append(f"   Confidence:{scan.confidence.upper()}")
        lines.append(f"   Recommended AI prompt: {get_recommended_prompt(scan.primary_platform)}")
    else:
        lines.append("   WARNING: Platform could not be detected (unknown file types)")

    if len(scan.detected_platforms) > 1:
        lines.append("\n   Other candidates:")
        for plat, score in list(scan.detected_platforms.items())[1:5]:
            lines.append(f"     - {PLATFORM_DISPLAY.get(plat, plat)} (score: {score})")

    # File inventory (by role)
    lines.append("\nFILE INVENTORY (by role):")
    by_role: dict[str, list[FileInfo]] = {}
    for f in scan.files:
        by_role.setdefault(f.role, []).append(f)

    role_order = ["source_code", "project_archive", "config", "documentation", "data", "image", "other"]
    role_names = {
        "source_code": "Source code",
        "project_archive": "Project archive",
        "config": "Configuration",
        "documentation": "Documentation",
        "data": "Data",
        "image": "Image/Scan",
        "other": "Other",
    }

    for role in role_order:
        files = by_role.get(role, [])
        if not files:
            continue
        lines.append(f"\n   {role_names[role]} ({len(files)} files):")
        for fi in files[:8]:
            try:
                rel = fi.path.relative_to(scan.input_path)
            except ValueError:
                rel = fi.path.name
            mb = fi.size_bytes / (1024 * 1024)
            size_str = f"{fi.size_bytes:,} B" if fi.size_bytes < 1024 * 1024 else f"{mb:.2f} MB"
            plats = ", ".join(fi.platforms[:2]) if fi.platforms else "(unknown)"
            lines.append(f"     - {rel}  ({size_str})  -> {plats}  {fi.notes}")
        if len(files) > 8:
            lines.append(f"     ... +{len(files) - 8} more files")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        scan = scan_input_folder(Path(sys.argv[1]))
        print(format_scan_report(scan))
    else:
        print("Usage: python platform_detector.py <_input folder path>")
