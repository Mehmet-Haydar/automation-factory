#!/usr/bin/env python3
"""
iec_tag_generator.py — IEC 61131-3 / TIA Portal Tag Name Generator (Phase 26-B)

Generates TIA Portal-accepted, IEC 61131-3-compliant tag names from the raw
signal names in RD01_IO_List.md.

TIA Portal tag rules:
  - Max 24 chars (v17 and earlier), V18+ allows 128 (we keep it at 24)
  - Only A-Z, a-z, 0-9, underscore (_)
  - Cannot start with a digit
  - Case-insensitive but we prefer uppercase

Output: metadata/HW03_IEC_Tags.md

CLI:
  python iec_tag_generator.py --project PROJECT_PATH
  python iec_tag_generator.py --project PROJECT_PATH --prefix-mode full
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# -- Turkish -> ASCII mapping (intentional: legacy signal names may be Turkish) --

_TR_ASCII = str.maketrans(
    "çğıöşüÇĞİÖŞÜ",
    "cgiOsUCGIOSU",
)

# -- Signal type -> IEC prefix mapping ----------------------------------------

PREFIX_MAP: dict[tuple[str, str], str] = {
    ("digital", "input"):  "DI",
    ("digital", "output"): "DQ",
    ("analog",  "input"):  "AI",
    ("analog",  "output"): "AQ",
    ("motor",   ""):       "M",
    ("valve",   ""):       "V",
    ("sensor",  ""):       "SEN",
    ("safety",  ""):       "SF",
    ("counter", ""):       "CNT",
    ("speed",   ""):       "SPD",
    ("temp",    ""):       "TEMP",
    ("pressure",""):       "P",
    ("level",   ""):       "LVL",
    ("flow",    ""):       "FLW",
}

# Keywords for detecting signal type in the RD01 markdown table.
# Turkish keywords are kept on purpose to match legacy/Turkish RD01 data.
#
# S-1 / B-L8: Safety (F-) signal patterns MUST be checked BEFORE standard
# DI/DQ patterns because "F-DI" also contains the substring "DI".
# Recognised variants: SAFE_DI, SAFE DI, F-DI, FDI (input side)
#                      SAFE_DQ, SAFE DQ, F-DQ, FDQ (output side)
_SAFE_DI_KW = re.compile(
    r"\bsafe[_ ]?di\b|\bf[-_]?di\b|\bfdi\b", re.IGNORECASE
)
_SAFE_DQ_KW = re.compile(
    r"\bsafe[_ ]?dq\b|\bf[-_]?dq\b|\bfdq\b", re.IGNORECASE
)
_DI_KW  = re.compile(r"\bdigital\s+input|di\b|dijital\s+giri[sş]|\bDI\b", re.IGNORECASE)
_DQ_KW  = re.compile(r"\bdigital\s+output|dq\b|do\b|dijital\s+çıkı[sş]|\bDQ\b", re.IGNORECASE)
_AI_KW  = re.compile(r"\banalog\s+input|ai\b|analog\s+giri[sş]|\bAI\b", re.IGNORECASE)
_AQ_KW  = re.compile(r"\banalog\s+output|aq\b|ao\b|analog\s+çıkı[sş]|\bAQ\b", re.IGNORECASE)


# -- Data structures ----------------------------------------------------------

@dataclass
class SignalTag:
    original_name: str
    tag_name: str
    signal_type: str    # DI / DQ / AI / AQ / M / UNK
    address: str = ""   # %I0.0, %Q0.0 etc.
    description: str = ""
    source_row: str = ""


@dataclass
class TagGenResult:
    project_path: Path
    tags: list[SignalTag] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    output_path: Optional[Path] = None


# -- Core function ------------------------------------------------------------

def make_iec_tag(raw: str, prefix: str = "", max_len: int = 24) -> str:
    """Raw text -> IEC 61131-3 / TIA Portal-compatible tag name."""
    # Turkish character conversion
    text = raw.translate(_TR_ASCII)
    # Replace disallowed characters with underscore
    text = re.sub(r"[^a-zA-Z0-9_]", "_", text)
    # Collapse consecutive underscores
    text = re.sub(r"_+", "_", text).strip("_")
    # Prefix an underscore if it starts with a digit
    if text and text[0].isdigit():
        text = f"_{text}"
    # Add prefix and uppercase
    full = f"{prefix}_{text}" if prefix else text
    full = full.upper()
    # Length trim
    return full[:max_len]


def _detect_type(row_text: str, header: str = "") -> str:
    """Detect the signal type from the row text.

    S-1 / B-L8: Safety (F-) patterns are checked FIRST so that a cell value
    like "SAFE_DI" or "F-DI" is returned as "SAFE_DI"/"SAFE_DQ" rather than
    falling through to the plain "DI"/"DQ" branch (which would strip the
    safety designation and generate an unprefixed, unsafe tag name).
    """
    combined = f"{header} {row_text}"
    # --- Safety channels: check BEFORE standard DI/DQ ---
    if _SAFE_DI_KW.search(combined): return "SAFE_DI"
    if _SAFE_DQ_KW.search(combined): return "SAFE_DQ"
    # --- Standard channels ---
    if _DI_KW.search(combined):  return "DI"
    if _DQ_KW.search(combined):  return "DQ"
    if _AI_KW.search(combined):  return "AI"
    if _AQ_KW.search(combined):  return "AQ"
    return "UNK"


# -- RD01 Parser --------------------------------------------------------------

def parse_rd01_signals(project_path: Path) -> list[dict]:
    """
    Read the markdown tables in RD01_IO_List.md to produce a signal list.
    Returns: [{"name": str, "type": str, "address": str, "desc": str, "raw": str}]
    """
    rd01_files = list((project_path / "metadata").glob("RD01*.md"))
    if not rd01_files:
        return []

    signals: list[dict] = []
    header_context = ""

    for rd01 in rd01_files:
        try:
            lines = rd01.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        in_table = False
        col_names: list[str] = []

        for raw_line in lines:
            stripped = raw_line.strip()

            # Derive signal-type context from the section header
            if stripped.startswith("#"):
                header_context = stripped
                in_table = False
                col_names = []
                continue

            # Markdown table header: | Tag | Description | Address | Type |
            # Turkish column-name keywords kept to match legacy RD01 data.
            if stripped.startswith("|") and not in_table:
                parts = [c.strip() for c in stripped.split("|") if c.strip()]
                lower = [p.lower() for p in parts]
                if any(k in " ".join(lower) for k in ("tag", "sinyal", "signal", "giriş", "çıkış")):
                    col_names = lower
                    in_table = True
                    continue

            # Separator line: |---|---|
            if in_table and re.match(r"^\|[-|\s:]+\|$", stripped):
                continue

            # Table data row
            if in_table and stripped.startswith("|"):
                # Demo-project bugfix: the old filter `if c.strip() is not None`
                # was always True, so the empty cell BEFORE the leading "|"
                # stayed at index 0 and shifted every column — the tag column
                # read as "" and every row was silently skipped. Strip the
                # boundary-pipe artifacts but keep interior cells aligned
                # with col_names (whose header filter dropped the same two).
                cells = [c.strip() for c in stripped.split("|")]
                if cells and cells[0] == "":
                    cells = cells[1:]
                if cells and cells[-1] == "":
                    cells = cells[:-1]
                parts = cells
                if len(parts) < 1:
                    in_table = False
                    continue

                def _get(keys: list[str], default: str = "") -> str:
                    for k in keys:
                        for i, cn in enumerate(col_names):
                            if k in cn and i < len(parts):
                                return parts[i]
                    return parts[0] if parts else default

                def _get_opt(keys: list[str]) -> str:
                    """Like _get but returns '' when no column matches —
                    never falls back to the tag column."""
                    for k in keys:
                        for i, cn in enumerate(col_names):
                            if k in cn and i < len(parts):
                                return parts[i]
                    return ""

                name    = _get(["tag", "sinyal", "signal", "ad", "name"])
                desc    = _get(["açıklama", "desc", "description", "tanım"])
                addr    = _get(["adres", "address", "%i", "%q", "%iw", "%qw", "hw adres"])
                sig_type = _get(["tip", "type", "tür", "yön", "direction"])
                # B-03: the Equipment column carries the physical device id
                # (M1, P1, Y2 …) — the assembler's fallback grouping for
                # legacy tags that don't follow SCOPE_EQUIP_NNN naming.
                equip   = _get_opt(["equipment", "ekipman", "cihaz",
                                    "gerät", "geraet", "device"])
                # Legacy operand ("E 0.3", "AW 96") — the cross-check anchor
                # between the AI-drafted RD01 and the real legacy source.
                oldtag  = _get_opt(["oldtag", "old tag", "old_tag",
                                    "legacy", "alt", "eski"])
                # Which legacy blocks reference the operand (traceability)
                srcmod  = _get_opt(["srcmodule", "src module", "source",
                                    "kaynak"])

                if not name or name == "-":
                    continue

                # Auto-detect type from text
                detected = _detect_type(f"{sig_type} {desc} {name}", header_context)
                if detected == "UNK":
                    detected = _detect_type(addr, header_context)

                signals.append({
                    "name": name,
                    "type": detected,
                    "address": addr,
                    "desc": desc,
                    "equipment": equip,
                    "oldtag": oldtag,
                    "srcmodule": srcmod,
                    "raw": stripped,
                })
                continue

            if in_table and not stripped.startswith("|"):
                in_table = False
                col_names = []

    return signals


# -- Tag Generation -----------------------------------------------------------

def _tag_prefix_for_type(sig_type: str) -> str:
    """Return the IEC tag prefix for a given signal type.

    S-1 / B-L8: SAFE_DI and SAFE_DQ channels are required to carry the F_
    prefix (IEC 61508 / TIA Safety project convention, consistent with what
    io_validator checks).  Using the raw type string ("SAFE_DI") as a prefix
    would produce tags like SAFE_DI_ESTOP_N which are NOT recognised as safety
    tags by the validator.  Mapping to "F" produces F_ESTOP_N — matching the
    convention enforced everywhere else in the tool-chain.
    """
    _SAFETY_PREFIX_MAP = {
        "SAFE_DI": "F",
        "SAFE_DQ": "F",
    }
    if sig_type in _SAFETY_PREFIX_MAP:
        return _SAFETY_PREFIX_MAP[sig_type]
    return sig_type if sig_type != "UNK" else ""


def generate_tags(signals: list[dict]) -> TagGenResult:
    """Generate the IEC tag table from a signal list."""
    result = TagGenResult(project_path=Path("."))
    seen: dict[str, int] = {}

    for sig in signals:
        prefix = _tag_prefix_for_type(sig["type"])
        # Long German names may truncate to the same 24 chars; keep the
        # untruncated form so collisions can be resolved from the part the
        # cut threw away (E2E #2 finding: DI_UEBERLASTFOERDERSCHNE x2).
        full = make_iec_tag(sig["name"], prefix=prefix, max_len=999)
        tag = full[:24]

        # Collision check: different long names that truncate alike get a
        # stable 4-hex suffix hashed from the FULL name; identical names
        # fall through to numbering. Every issued tag is registered in
        # `seen`, so the loop guarantees table-wide uniqueness.
        base_tag = tag
        if base_tag in seen:
            seen[base_tag] += 1
            result.duplicates.append(base_tag)
            digest = hashlib.sha1(full.encode("utf-8")).hexdigest()[:4].upper()
            tag = f"{full[:19]}_{digest}"
            n = seen[base_tag]
            while tag in seen:
                tag = f"{full[:16]}_{digest}_{n:02d}"
                n += 1
            seen[tag] = 1
        else:
            seen[base_tag] = 1

        result.tags.append(SignalTag(
            original_name=sig["name"],
            tag_name=tag,
            signal_type=sig["type"],
            address=sig["address"],
            description=sig["desc"],
            source_row=sig["raw"],
        ))

    return result


def generate_tags_for_project(project_path: Path) -> TagGenResult:
    """Full pipeline: parse RD01 -> generate tags."""
    signals = parse_rd01_signals(project_path)
    result = generate_tags(signals)
    result.project_path = project_path

    if not signals:
        result.warnings.append(
            "RD01_IO_List.md not found or tables could not be read. "
            "There must be an RD01 file with markdown tables in the metadata/ folder."
        )

    return result


# -- Markdown Writer ----------------------------------------------------------

def write_tag_table(result: TagGenResult) -> Path:
    """Write the tag table as HW03_IEC_Tags.md."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# HW03 — IEC 61131-3 Tag Table",
        "",
        "```yaml",
        f"created: {ts}",
        f"source:  RD01_IO_List.md",
        f"total:   {len(result.tags)} tags",
        "```",
        "",
        "> **Note:** This table was auto-generated. Verify the address and",
        "> type information before exporting to TIA Portal.",
        "",
        "## Tag Table",
        "",
        "| IEC Tag Name | Type | Address | Original Name | Description |",
        "|---|---|---|---|---|",
    ]

    type_counts: dict[str, int] = {}
    for tag in result.tags:
        type_counts[tag.signal_type] = type_counts.get(tag.signal_type, 0) + 1
        lines.append(
            f"| `{tag.tag_name}` | {tag.signal_type} | `{tag.address or '-'}` "
            f"| {tag.original_name} | {tag.description} |"
        )

    lines += [
        "",
        "## Summary",
        "",
    ]
    for stype, cnt in sorted(type_counts.items()):
        lines.append(f"- **{stype}:** {cnt} items")

    if result.duplicates:
        lines += [
            "",
            "## Duplicate Tag Names (Numbered)",
            "",
        ]
        for d in set(result.duplicates):
            lines.append(f"- `{d}` -> numeric suffix added")

    if result.warnings:
        lines += ["", "## Warnings", ""]
        for w in result.warnings:
            lines.append(f"- {w}")

    lines += ["", "---", f"*AUTOMATION_FACTORY iec_tag_generator.py — {ts}*"]

    out = result.project_path / "metadata" / "HW03_IEC_Tags.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    result.output_path = out
    return out


def run_tag_generation(project_path: Path) -> TagGenResult:
    """Full pipeline wrapper."""
    result = generate_tags_for_project(project_path)
    write_tag_table(result)
    return result


def format_summary(result: TagGenResult) -> str:
    lines = ["IEC Tag Generation Summary", ""]
    lines.append(f"  Total tags      : {len(result.tags)}")
    if result.tags:
        type_c: dict[str, int] = {}
        for t in result.tags:
            type_c[t.signal_type] = type_c.get(t.signal_type, 0) + 1
        for k, v in sorted(type_c.items()):
            lines.append(f"    {k:<6}: {v}")
    if result.duplicates:
        lines.append(f"  Collisions (suffix added): {len(set(result.duplicates))}")
    if result.output_path:
        lines.append(f"  Output          : {result.output_path}")
    if result.warnings:
        lines.append("")
        for w in result.warnings:
            lines.append(f"  [WARN] {w}")
    return "\n".join(lines)


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="IEC 61131-3 Tag Name Generator")
    p.add_argument("--project", metavar="PROJECT_PATH", required=True)
    args = p.parse_args()

    result = run_tag_generation(Path(args.project))
    print(format_summary(result))


if __name__ == "__main__":
    main()
