#!/usr/bin/env python3
"""
rd01_crosscheck.py — deterministic verification of the AI-drafted RD01
against the real legacy sources.

WHY: the whole "cheap model, premium result" strategy stands on catching a
cheap model's two failure modes mechanically — OMISSION (a signal in the
legacy code that never reached RD01) and HALLUCINATION (an RD01 row whose
legacy operand does not exist in any source). Both are invisible to a human
skimming a 200-row table and fatal weeks later in TIA. No AI here: pure
parsing, runs offline in milliseconds, right after the RD01 draft is
written.

Scope: S5/S7-classic operand syntax (E/A/M x.y, EW/AW/ED/AD/PEW/PAW n,
T n, Z n) and IEC syntax (%I0.0, %QW96) in .awl/.stl/.seq/.txt/.src files
under _raw/legacy_code/. Timers/counters/flags are inventoried but NOT
required in RD01 (they are internal, not IO).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# --- operand grammar --------------------------------------------------------

# Classic S5/S7: "E 0.0" / "E0.0" / "A 4.1" — bit addressed IO
_BIT_RE = re.compile(r"\b([EAI]|Q)\s?(\d{1,3})\.([0-7])\b")
# Word/analog: "EW 10", "AW 96", "PEW 288", "PAW 288"
_WORD_RE = re.compile(r"\b(EW|AW|IW|QW|PEW|PAW|ED|AD|ID|QD)\s?(\d{1,4})\b")
# IEC style in newer exports: %I0.0 / %Q4.1 / %IW10 / %QW96
_IEC_BIT_RE = re.compile(r"%([IQ])\s?(\d{1,3})\.([0-7])\b")
_IEC_WORD_RE = re.compile(r"%([IQ])W\s?(\d{1,4})\b")

# German→canonical direction letters (S5/S7 German mnemonics: E=input,
# A=output; international: I / Q)
_DIR_IN = {"E", "I"}
_DIR_OUT = {"A", "Q"}

_SOURCE_EXTS = {".awl", ".stl", ".seq", ".txt", ".src", ".scl", ".db"}

# Comment / string noise that produces false operands ("// siehe E 2.0"
# stays — comments legitimately document IO; but block headers repeating
# addresses in prose are acceptable inventory noise: cross-check treats the
# UNION of code+comments as ground truth of "mentioned in the source").


def _canon_bit(direction: str, byte: str, bit: str) -> str:
    d = "E" if direction.upper() in _DIR_IN else "A"
    return f"{d}{int(byte)}.{bit}"


def _canon_word(kind: str, addr: str) -> str:
    k = kind.upper().lstrip("P")           # PEW→EW, PAW→AW
    k = {"IW": "EW", "QW": "AW", "ID": "ED", "QD": "AD"}.get(k, k)
    return f"{k}{int(addr)}"


@dataclass
class SourceInventory:
    bit_inputs: set = field(default_factory=set)     # E0.0 …
    bit_outputs: set = field(default_factory=set)    # A4.1 …
    words: set = field(default_factory=set)          # EW10 / AW96 …
    files: list = field(default_factory=list)

    @property
    def all_io(self) -> set:
        return self.bit_inputs | self.bit_outputs | self.words


def scan_legacy_sources(project_root: Path) -> SourceInventory:
    """Inventory every IO operand mentioned in _raw/legacy_code text files."""
    inv = SourceInventory()
    legacy = Path(project_root) / "_raw" / "legacy_code"
    if not legacy.is_dir():
        return inv
    for fp in sorted(legacy.iterdir()):
        if not fp.is_file() or fp.suffix.lower() not in _SOURCE_EXTS:
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        inv.files.append(fp.name)
        for m in _BIT_RE.finditer(text):
            tgt = inv.bit_inputs if m.group(1).upper() in _DIR_IN else inv.bit_outputs
            tgt.add(_canon_bit(m.group(1), m.group(2), m.group(3)))
        for m in _IEC_BIT_RE.finditer(text):
            tgt = inv.bit_inputs if m.group(1).upper() == "I" else inv.bit_outputs
            tgt.add(_canon_bit(m.group(1), m.group(2), m.group(3)))
        for m in _WORD_RE.finditer(text):
            inv.words.add(_canon_word(m.group(1), m.group(2)))
        for m in _IEC_WORD_RE.finditer(text):
            inv.words.add(_canon_word(m.group(1) + "W", m.group(2)))
    return inv


def _canon_rd01_operand(value: str) -> str | None:
    """Normalize an RD01 OldTag/Address cell to the canonical operand form."""
    v = (value or "").strip()
    if not v:
        return None
    m = _BIT_RE.search(v) or _IEC_BIT_RE.search(v)
    if m:
        return _canon_bit(m.group(1), m.group(2), m.group(3))
    m = _WORD_RE.search(v)
    if m:
        return _canon_word(m.group(1), m.group(2))
    m = _IEC_WORD_RE.search(v)
    if m:
        return _canon_word(m.group(1) + "W", m.group(2))
    return None


def crosscheck_rd01(project_root: Path) -> dict:
    """Compare the RD01 table against the legacy-source inventory.

    Returns {ok, source_io, rd01_rows, covered, missing_in_rd01,
    not_in_source, dir_mismatch, summary} — `ok` is True when there is
    nothing to flag. Missing timers/flags are NOT flagged (internal, not IO).
    """
    from iec_tag_generator import parse_rd01_signals  # type: ignore

    inv = scan_legacy_sources(project_root)
    rows = parse_rd01_signals(Path(project_root))

    rd01_ops: dict[str, dict] = {}
    for r in rows:
        op = _canon_rd01_operand(r.get("oldtag", "")) or \
             _canon_rd01_operand(r.get("address", ""))
        if op:
            rd01_ops[op] = r

    src = inv.all_io
    covered = sorted(src & set(rd01_ops))
    missing = sorted(src - set(rd01_ops))
    invented = sorted(set(rd01_ops) - src) if src else []

    # Direction sanity: an E-operand typed as an output (or A as input)
    dir_mismatch = []
    for op, r in rd01_ops.items():
        t = (r.get("type") or "").upper()
        if op.startswith("E") and t in ("DQ", "AO"):
            dir_mismatch.append(f"{r.get('name', '?')} ({op}) typed {t} but is a legacy INPUT")
        if op.startswith("A") and t in ("DI",):
            dir_mismatch.append(f"{r.get('name', '?')} ({op}) typed {t} but is a legacy OUTPUT")

    n_src = len(src)
    summary = (
        f"RD01 cross-check: {len(covered)}/{n_src} legacy IO operands covered"
        + (f", {len(missing)} MISSING from RD01" if missing else "")
        + (f", {len(invented)} rows have NO legacy source (hallucination?)"
           if invented else "")
        + (f", {len(dir_mismatch)} direction mismatch(es)" if dir_mismatch else "")
        + (" — clean." if not (missing or invented or dir_mismatch) else "")
    ) if n_src else "RD01 cross-check: no legacy sources to check against."

    return {
        "ok": not (missing or invented or dir_mismatch),
        "source_io": n_src,
        "rd01_rows": len(rows),
        "covered": len(covered),
        "missing_in_rd01": missing,
        "not_in_source": invented,
        "dir_mismatch": dir_mismatch,
        "files_scanned": inv.files,
        "summary": summary,
    }
