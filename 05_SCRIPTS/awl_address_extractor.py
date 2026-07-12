#!/usr/bin/env python3
"""
awl_address_extractor.py — Deterministic S5 field-IO address extractor.

Reads legacy code files from _raw/legacy_code/ and backfills the
Address column of RD01_IO_List.md with real S7-format PLC addresses.

Two complementary sources (both run, AWL/SEQ wins on conflict):
  1. SEQ file  — structured IO declaration list (KE/KA lines)
  2. AWL file  — inline comments on operands
  3. Fallback  — "(old E x.y)" pattern already in RD01 descriptions (AI residue)

S5 → S7 mapping:
  E x.y  → %Ix.y   (DI)   EW x → %IWx  (AI word)
  A x.y  → %Qx.y   (DQ)   AW x → %QWx  (AO word)
  EB x   → %IBx    (AI byte)  AB x → %QBx  (AO byte)

Usage:
  python awl_address_extractor.py <project_root>
  or: from awl_address_extractor import backfill_rd01_addresses
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# S5 → S7 address conversion
# ---------------------------------------------------------------------------

_S5_PREFIX: dict[str, tuple[str, str]] = {
    "E":  ("%I",  "DI"),
    "A":  ("%Q",  "DQ"),
    "EW": ("%IW", "AI"),
    "AW": ("%QW", "AO"),
    "EB": ("%IB", "AI"),
    "AB": ("%QB", "AO"),
    "ED": ("%ID", "AI"),
    "AD": ("%QD", "AO"),
}

# Matches "E 1.4", "EW 10", "EW 10.0", "A 4.3" etc.
_S5_ADDR_RE = re.compile(
    r"\b(EW|AW|EB|AB|ED|AD|E|A)\s+(\d+)(?:\.(\d+))?",
    re.IGNORECASE,
)

# Matches "(old E 1.4)", "(old EW 10)" inside RD01 descriptions
_OLD_ADDR_RE = re.compile(
    r"\(old\s+(EW|AW|EB|AB|ED|AD|E|A)\s+(\d+)(?:\.(\d+))?\)",
    re.IGNORECASE,
)


def _convert(prefix: str, byte: str, bit: str | None) -> tuple[str, str]:
    """Return (s7_address, io_type) for a given S5 operand."""
    p = prefix.upper()
    s7_pfx, io_type = _S5_PREFIX.get(p, ("", "UNK"))
    if not s7_pfx:
        return "", "UNK"
    if p in ("EW", "AW", "EB", "AB", "ED", "AD"):
        return f"{s7_pfx}{byte}", io_type
    # bit-addressed (E/A): keep byte.bit, strip trailing .0 for words
    addr = f"{byte}.{bit}" if bit is not None else byte
    return f"{s7_pfx}{addr}", io_type


# ---------------------------------------------------------------------------
# SEQ file parser
# ---------------------------------------------------------------------------

# E    1.0 E 1.0  KE HYDR.PUMPE NETZSCHUETZ RUECKM.
# EW  10.0 EW 10  KE OELTEMPERATUR FUEHLER 4-20MA
_SEQ_RE = re.compile(
    r"^(EW|AW|EB|AB|ED|AD|E|A)\s+[\d.]+\s+"  # first type + addr (ignored)
    r"(?:EW|AW|EB|AB|ED|AD|E|A)\s+([\d.]+)\s+"  # canonical addr
    r"K[EA]\s+(.+)$",                             # comment
    re.IGNORECASE,
)


def _parse_seq(path: Path) -> dict[str, dict]:
    """Parse a .SEQ file → {s5_key: {"s7": str, "type": str, "desc": str}}"""
    result: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _SEQ_RE.match(line.strip())
        if not m:
            continue
        prefix = m.group(1).upper()
        raw_addr = m.group(2).strip()          # "1.0", "10", "10.0"
        desc = m.group(3).strip()

        # Normalise: "10.0" for word types → byte only "10"
        if prefix in ("EW", "AW", "EB", "AB", "ED", "AD"):
            byte = raw_addr.split(".")[0]
            bit = None
        else:
            parts = raw_addr.split(".")
            byte, bit = parts[0], parts[1] if len(parts) > 1 else "0"

        s7_addr, io_type = _convert(prefix, byte, bit)
        if not s7_addr:
            continue

        s5_key = f"{prefix} {byte}" + (f".{bit}" if bit else "")
        result[s5_key] = {"s7": s7_addr, "type": io_type, "desc": desc}
    return result


# ---------------------------------------------------------------------------
# AWL file parser
# ---------------------------------------------------------------------------

# Matches: "U     E    1.4          // Band Rueckmeldung"
_AWL_LINE_RE = re.compile(
    r"\b(EW|AW|EB|AB|ED|AD|E|A)\s+([\d]+)(?:\.([\d]+))?\s*(?://\s*(.+))?",
    re.IGNORECASE,
)


def _parse_awl(path: Path) -> dict[str, dict]:
    """Parse a .AWL file → {s5_key: {"s7": str, "type": str, "desc": str}}"""
    result: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        m = _AWL_LINE_RE.search(stripped)
        if not m:
            continue
        prefix = m.group(1).upper()
        if prefix not in _S5_PREFIX:
            continue
        byte = m.group(2)
        bit  = m.group(3)
        desc = (m.group(4) or "").strip()

        if prefix in ("EW", "AW", "EB", "AB", "ED", "AD"):
            bit = None

        s7_addr, io_type = _convert(prefix, byte, bit)
        if not s7_addr:
            continue

        s5_key = f"{prefix} {byte}" + (f".{bit}" if bit else "")
        if s5_key not in result or (desc and not result[s5_key]["desc"]):
            result[s5_key] = {"s7": s7_addr, "type": io_type, "desc": desc}
    return result


# ---------------------------------------------------------------------------
# Scan project legacy files
# ---------------------------------------------------------------------------

def scan_legacy_files(project_root: Path) -> dict[str, dict]:
    """Scan _raw/legacy_code/ for .seq and .awl files.

    SEQ entries take precedence (more structured); AWL fills gaps.
    Returns {s5_key → {"s7": str, "type": str, "desc": str}}.
    """
    legacy_dir = project_root / "_raw" / "legacy_code"
    addr_map: dict[str, dict] = {}

    if not legacy_dir.is_dir():
        return addr_map

    # AWL first (lower priority)
    for awl in sorted(legacy_dir.glob("*.[Aa][Ww][Ll]")):
        addr_map.update(_parse_awl(awl))

    # SEQ on top (higher priority — structured IO list)
    for seq in sorted(legacy_dir.glob("*.[Ss][Ee][Qq]")):
        addr_map.update(_parse_seq(seq))

    return addr_map


# ---------------------------------------------------------------------------
# RD01 markdown table backfill
# ---------------------------------------------------------------------------

def _col_index(header_cells: list[str], keys: list[str]) -> int:
    """Return 0-based column index for the first matching key (case-insensitive)."""
    for i, cell in enumerate(header_cells):
        if cell.strip().lower() in keys:
            return i
    return -1


def _s5_from_desc(desc: str) -> str:
    """Extract S5 address from description like '(old E 1.4)' → 'E 1.4'."""
    m = _OLD_ADDR_RE.search(desc)
    if not m:
        return ""
    prefix = m.group(1).upper()
    byte   = m.group(2)
    bit    = m.group(3)
    return f"{prefix} {byte}" + (f".{bit}" if bit else "")


def backfill_rd01_addresses(project_root: Path) -> dict:
    """Fill empty Address cells in RD01_IO_List.md.

    Strategy (in order):
      1. '(old E x.y)' pattern in description → convert directly
      2. AWL/SEQ file scan → match by same s5_key

    Returns {"updated": int, "skipped": int, "files": list[str]}
    """
    addr_map = scan_legacy_files(project_root)

    md_dir = project_root / "metadata"
    if not md_dir.is_dir():
        return {"updated": 0, "skipped": 0, "files": [], "msg": "No metadata/ dir"}

    rd01_files = sorted(md_dir.glob("RD01*.md"))
    if not rd01_files:
        return {"updated": 0, "skipped": 0, "files": [], "msg": "No RD01 file found"}

    total_updated = 0
    touched_files: list[str] = []

    for rd01_path in rd01_files:
        lines = rd01_path.read_text(encoding="utf-8").splitlines(keepends=True)
        updated = 0
        in_table = False
        addr_col = -1
        desc_col = -1
        new_lines: list[str] = []

        for line in lines:
            stripped = line.rstrip("\n\r")

            if not stripped.startswith("|"):
                in_table = False
                addr_col = -1
                desc_col = -1
                new_lines.append(line)
                continue

            cells = stripped.split("|")
            # cells[0] is empty (before first |), cells[-1] is empty (after last |)
            data = cells[1:-1]

            # Header row detection
            if not in_table:
                lower = [c.strip().lower() for c in data]
                addr_col = _col_index(data, ["address", "adres", "%i", "%q", "hw adres"])
                desc_col = _col_index(data, ["description", "açıklama", "desc", "tanım"])
                if addr_col >= 0:
                    in_table = True
                new_lines.append(line)
                continue

            # Separator row (|---|---|)
            if all(re.match(r"^[-:]+$", c.strip()) for c in data if c.strip()):
                new_lines.append(line)
                continue

            # Data row — fill Address if empty
            if addr_col < 0 or addr_col >= len(data):
                new_lines.append(line)
                continue

            current_addr = data[addr_col].strip()
            if current_addr and current_addr != "—":
                new_lines.append(line)
                continue  # already filled

            # Try to resolve
            s7_addr = ""

            # Source 1: "(old E x.y)" in description
            if desc_col >= 0 and desc_col < len(data):
                s5_key = _s5_from_desc(data[desc_col])
                if s5_key:
                    m = _S5_ADDR_RE.match(s5_key)
                    if m:
                        pfx, byte, bit = m.group(1), m.group(2), m.group(3)
                        if pfx.upper() in ("EW", "AW", "EB", "AB", "ED", "AD"):
                            bit = None
                        s7_addr, _ = _convert(pfx, byte, bit)

            # Source 2: AWL/SEQ scan — by s5_key from description
            if not s7_addr and desc_col >= 0 and desc_col < len(data):
                s5_key = _s5_from_desc(data[desc_col])
                if s5_key and s5_key in addr_map:
                    s7_addr = addr_map[s5_key]["s7"]

            if not s7_addr:
                new_lines.append(line)
                continue

            # Patch the line
            data[addr_col] = f" {s7_addr} "
            new_line = "|" + "|".join(data) + "|\n"
            new_lines.append(new_line)
            updated += 1

        if updated:
            rd01_path.write_text("".join(new_lines), encoding="utf-8")
            touched_files.append(rd01_path.name)
            total_updated += updated

    msg = (
        f"{total_updated} address(es) backfilled in {len(touched_files)} file(s)"
        if total_updated else "No empty Address cells found — nothing to do"
    )
    return {
        "updated": total_updated,
        "files": touched_files,
        "legacy_signals_found": len(addr_map),
        "msg": msg,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python awl_address_extractor.py <project_root>")
        sys.exit(1)
    root = Path(sys.argv[1])
    result = backfill_rd01_addresses(root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
