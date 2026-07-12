"""
io_validator.py — Platform-aware validation for IO list rows.

Errors:
  - missing required field (tag, address, type)
  - duplicate tag
  - duplicate address
  - address syntax mismatch for the platform

Warnings:
  - Direction ↔ address class mismatch (e.g. DI on %Q)
  - Type ↔ address width mismatch (e.g. REAL on a bit address)
  - SafetyRelated=Y without F_ prefix in the tag
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Optional

from .io_list_io import IORow


_S7_BIT     = r"%?[IQM]\d+\.[0-7]"          # %I0.0 .. %Q9999.7
_S7_BYTE    = r"%?[IQ]B\d+"
_S7_WORD    = r"%?[IQ]W\d+"
_S7_DWORD   = r"%?[IQ]D\d+"
# M-A1: S7 peripheral (process-image-bypass) addresses used by analog and
# F-DI/F-DQ modules: PIB256, PIW256, PID768, PQB100, PQW100, PQD100.
# The leading % is optional, matching the rest of the S7 patterns.
_S7_PERIPHERAL = r"%?P[IQ][BWD]\d+"
_S7_DB_BIT  = r"DB\d+\.DBX\d+\.[0-7]"
_S7_DB_BYTE = r"DB\d+\.DBB\d+"
_S7_DB_WORD = r"DB\d+\.DBW\d+"
_S7_DB_DWORD = r"DB\d+\.(DBD|DBR|DBL)\d+"

_S7_PATTERN = re.compile(
    r"^(?:" + "|".join((
        _S7_BIT, _S7_BYTE, _S7_WORD, _S7_DWORD, _S7_PERIPHERAL,
        _S7_DB_BIT, _S7_DB_BYTE, _S7_DB_WORD, _S7_DB_DWORD,
    )) + r")$"
)

_CODESYS_PATTERN = re.compile(r"^%?[IQM][XBWD]\d+(\.[0-7])?$")
_AB_PATTERN = re.compile(
    r"^Local:\d+:[IO]\.Data(\.\d+)?$"
    r"|^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*\.\d+$"
)

PLATFORM_ADDR_PATTERNS = {
    "S7_1500": _S7_PATTERN,
    "S7_300":  _S7_PATTERN,
    "S7_1200": _S7_PATTERN,
    "S7_400":  _S7_PATTERN,
    "AB":      _AB_PATTERN,
    "ALLEN_BRADLEY": _AB_PATTERN,
    "CODESYS": _CODESYS_PATTERN,
    "TWINCAT": _CODESYS_PATTERN,
}

BIT_TYPES   = {"BOOL"}
BYTE_TYPES  = {"BYTE", "SINT", "USINT", "CHAR"}
WORD_TYPES  = {"WORD", "INT", "UINT"}
DWORD_TYPES = {"DWORD", "DINT", "UDINT", "REAL", "TIME", "DATE"}


@dataclass
class Issue:
    row_index: int          # 0-based row index
    column: str             # IORow attribute name; "" for row-level issues
    severity: str           # "error" | "warning"
    message: str


def validate_rows(rows: Iterable[IORow], platform: str = "") -> list[Issue]:
    rows_list = list(rows)
    issues: list[Issue] = []

    plat = (platform or "").strip().upper().replace("-", "_")
    pattern = PLATFORM_ADDR_PATTERNS.get(plat)

    # Per-row checks
    for i, row in enumerate(rows_list):
        if not row.tag:
            issues.append(Issue(i, "tag", "error", "Tag is required"))
        if not row.address:
            issues.append(Issue(i, "address", "error", "Address is required"))
        if not row.dtype:
            issues.append(Issue(i, "dtype", "error", "Type is required"))

        if row.address and pattern is not None and not pattern.match(row.address):
            issues.append(Issue(
                i, "address", "error",
                f"Address {row.address!r} does not match {plat} syntax",
            ))

        # Direction ↔ address class
        if row.address and row.direction:
            cls = _address_class(row.address)
            d = row.direction.upper()
            if cls == "I" and d in ("DO", "AO"):
                issues.append(Issue(
                    i, "address", "warning",
                    f"Input address {row.address!r} but direction is {d}",
                ))
            if cls == "Q" and d in ("DI", "AI"):
                issues.append(Issue(
                    i, "address", "warning",
                    f"Output address {row.address!r} but direction is {d}",
                ))

        # Type ↔ address width
        if row.address and row.dtype:
            t = row.dtype.upper()
            width = _address_width(row.address)
            if width == "bit" and t not in BIT_TYPES:
                issues.append(Issue(
                    i, "dtype", "warning",
                    f"Type {t} on bit address {row.address!r}",
                ))
            if width == "word" and t not in WORD_TYPES | BIT_TYPES:
                issues.append(Issue(
                    i, "dtype", "warning",
                    f"Type {t} on word address {row.address!r}",
                ))
            if width == "dword" and t not in DWORD_TYPES:
                issues.append(Issue(
                    i, "dtype", "warning",
                    f"Type {t} on dword address {row.address!r}",
                ))

        # N-M2: Direction ↔ Type semantic mismatch
        # A digital/analog direction combined with a numeric/string type indicates
        # a likely engineering mistake in the IO list.
        if row.direction and row.dtype:
            d_up = row.direction.upper()
            t_up = row.dtype.upper()
            _DIGITAL_DIRS = {"DI", "DO", "DQ"}
            _INCOMPATIBLE_WITH_DIGITAL = {"REAL", "INT", "UINT", "DINT", "UDINT",
                                           "WORD", "DWORD", "STRING", "BYTE"}
            if d_up in _DIGITAL_DIRS and t_up in _INCOMPATIBLE_WITH_DIGITAL:
                issues.append(Issue(
                    i, "dtype", "warning",
                    f"Direction {d_up} is digital but Type {t_up} is a numeric/string type — "
                    "expected BOOL for digital IO",
                ))

        # S-1 / B-L8: SafetyRelated=Y but Type is not a recognised safety type.
        # engineer review required: warning→error escalation per IEC 61508 spirit — fail-closed
        # A non-safety Type on a safety-related row means the channel will reach
        # the BOM / PLC project with incorrect module assignment (standard DI
        # instead of F-DI).  This is a gate-blocking defect, not a hint.
        _SAFETY_TYPES = {"F-DI", "FDI", "SAFE_DI", "F_DI",
                         "F-DQ", "FDQ", "SAFE_DQ", "F_DQ", "SAFE"}
        if row.safety_related.upper() == "Y" and row.dtype:
            t_up = row.dtype.upper()
            if t_up not in _SAFETY_TYPES:
                issues.append(Issue(
                    i, "dtype", "error",
                    f"SafetyRelated=Y but Type {t_up!r} is not a safety type (expected F-DI / F-DQ). "
                    "Correct the Type column or remove the SafetyRelated flag. "
                    "[S-1/B-L8 fail-closed: was warning, promoted to error per IEC 61508 spirit]",
                ))

        # S-1 / B-L8: Safety convention — F_ prefix is mandatory.
        # engineer review required: warning→error escalation per IEC 61508 spirit — fail-closed
        # A safety-related tag without the F_ prefix is indistinguishable from a
        # standard tag in the TIA Safety project and in generated SCL code.
        if row.safety_related.upper() == "Y" and row.tag and not row.tag.upper().startswith("F_"):
            issues.append(Issue(
                i, "safety_related", "error",
                "SafetyRelated=Y but tag is missing the F_ prefix — rename tag to F_<name>. "
                "[S-1/B-L8 fail-closed: was warning, promoted to error per IEC 61508 spirit]",
            ))

    # Cross-row checks
    tag_counts = Counter(r.tag for r in rows_list if r.tag)
    addr_counts = Counter(r.address for r in rows_list if r.address)
    for i, row in enumerate(rows_list):
        if row.tag and tag_counts[row.tag] > 1:
            issues.append(Issue(i, "tag", "error", f"Duplicate tag {row.tag!r}"))
        if row.address and addr_counts[row.address] > 1:
            issues.append(Issue(
                i, "address", "error", f"Duplicate address {row.address!r}",
            ))

    return issues


def _address_class(addr: str) -> Optional[str]:
    """Return 'I' (input), 'Q' (output), 'M' (marker) or None.

    M-A1: peripheral addresses (PIW, PQW, PID, …) also carry an I/Q class
    based on the second character.
    """
    m = re.match(r"^%?P([IQ])", addr)
    if m:
        return m.group(1)
    m = re.match(r"^%?([IQM])", addr)
    return m.group(1) if m else None


def _address_width(addr: str) -> Optional[str]:
    """Return 'bit', 'byte', 'word', 'dword' or None."""
    if re.match(r"^%?[IQM]\d+\.[0-7]$", addr):  # bit 0-7 only, consistent with _S7_BIT
        return "bit"
    if re.match(r"^%?[IQ]B\d+$", addr):
        return "byte"
    if re.match(r"^%?[IQ]W\d+$", addr):
        return "word"
    if re.match(r"^%?[IQ]D\d+$", addr):
        return "dword"
    # M-A1: peripheral addresses.
    if re.match(r"^%?P[IQ]B\d+$", addr):
        return "byte"
    if re.match(r"^%?P[IQ]W\d+$", addr):
        return "word"
    if re.match(r"^%?P[IQ]D\d+$", addr):
        return "dword"
    if re.match(r"^DB\d+\.DBX\d+\.[0-7]$", addr):  # bit 0-7 only, consistent with _S7_DB_BIT
        return "bit"
    if re.match(r"^DB\d+\.DBB\d+$", addr):
        return "byte"
    if re.match(r"^DB\d+\.DBW\d+$", addr):
        return "word"
    if re.match(r"^DB\d+\.(DBD|DBR|DBL)\d+$", addr):
        return "dword"
    return None
