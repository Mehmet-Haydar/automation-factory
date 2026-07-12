#!/usr/bin/env python3
"""
rd_table_schema.py — mechanical schema gate for AI-drafted RD01 tables.

WHY (A/B/C/D field measurement 2026-07-03): every deterministic consumer
(cross-check, autocomplete, Equipment enrichment, program assembler) reads
the RD01 markdown table positionally. The AI reshapes that table freely —
one run drops the % address prefix, the next drops the Equipment column,
a third emits half a row at the token limit. Prompt wording cannot pin a
format; a WRITE-TIME gate can. This module validates and — only where the
repair is unambiguous — repairs the draft BEFORE it lands in metadata/:

  repaired mechanically (safe, deterministic):
    * short rows padded with empty cells (truncation artifacts)
    * Address normalized to IEC ("I4.0" → "%I4.0", "QW 96" → "%QW96")
    * Dir derived from Type when empty (DI/AI → IN, DQ/AO → OUT)
    * empty Status → DRAFT_UNVERIFIED

  rejected loudly (never guessed, never silently dropped):
    * rows with MORE cells than the header (cell boundaries ambiguous)
    * rows whose Type is not a known IO type
  Rejected rows go to metadata/_history/<ts>_RD01_rejected.txt with their
  operands DEFUSED (I4.0 → I4_0) so the cross-check counts them as missing
  and the deterministic autocomplete re-adds them from the symbol table —
  the gate and the self-healing loop close together.

No AI, offline, idempotent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_VALID_TYPES = {"DI", "DQ", "AI", "AO", "SAFE_DI", "SAFE_DQ"}
_DIR_FOR_TYPE = {"DI": "IN", "AI": "IN", "SAFE_DI": "IN",
                 "DQ": "OUT", "AO": "OUT", "SAFE_DQ": "OUT"}

_ADDR_BIT_RE = re.compile(r"^%?\s*([IQ])\s*(\d{1,3})\.(\d)$")
_ADDR_WORD_RE = re.compile(r"^%?\s*([IQ])([WD])\s*(\d{1,4})$")
_OPERAND_DEFUSE_RE = re.compile(r"\b([EAIQ]W?\s?\d{1,4})\.(\d)\b")


@dataclass
class SchemaGateReport:
    ok: bool = True
    checked_rows: int = 0
    repaired_cells: int = 0
    rejected_rows: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = [f"{self.checked_rows} rows checked"]
        if self.repaired_cells:
            parts.append(f"{self.repaired_cells} cell(s) repaired")
        if self.rejected_rows:
            parts.append(f"{len(self.rejected_rows)} row(s) REJECTED")
        return "RD01 schema gate: " + ", ".join(parts)


def _norm_address(cell: str) -> tuple[str, bool]:
    """IEC-normalize an address cell; returns (value, changed)."""
    v = cell.strip()
    if not v:
        return cell, False
    m = _ADDR_BIT_RE.match(v)
    if m:
        norm = f"%{m.group(1)}{int(m.group(2))}.{m.group(3)}"
        return norm, norm != v
    m = _ADDR_WORD_RE.match(v)
    if m:
        norm = f"%{m.group(1)}{m.group(2)}{int(m.group(3))}"
        return norm, norm != v
    return cell, False


def _defuse(text: str) -> str:
    """Make operands unparseable so the cross-check counts them missing."""
    return _OPERAND_DEFUSE_RE.sub(lambda m: f"{m.group(1)}_{m.group(2)}",
                                  text)


def validate_and_repair_rd01(content: str) -> tuple[str, SchemaGateReport]:
    """Gate an RD01 draft. Returns (possibly repaired content, report).

    Conservative by contract: acts only on the first table whose header
    contains both 'tag' and 'address'; anything else passes through
    untouched with a note."""
    rep = SchemaGateReport()
    lines = content.splitlines()
    hdr_i = None
    for i, ln in enumerate(lines):
        low = ln.lower()
        if ln.strip().startswith("|") and "tag" in low and "address" in low:
            hdr_i = i
            break
    if hdr_i is None:
        rep.notes.append("no Tag/Address table found — gate skipped")
        return content, rep

    cols = [c.strip() for c in lines[hdr_i].split("|")[1:-1]]
    ncols = len(cols)
    low_cols = [c.lower() for c in cols]

    def idx(*keys: str) -> int | None:
        for k in keys:
            for j, c in enumerate(low_cols):
                if k in c:
                    return j
        return None

    i_addr = idx("address")
    i_type = idx("type")
    i_dir = idx("dir")
    i_status = idx("status")

    out = lines[: hdr_i + 2]  # header + separator unchanged
    i = hdr_i + 2
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s.startswith("|"):
            break
        i += 1
        # half row at the token limit: no closing pipe → defuse + reject
        if not s.endswith("|"):
            rep.rejected_rows.append(_defuse(s) + "   [reason: truncated row]")
            continue
        cells = [c for c in s.split("|")][1:-1]
        rep.checked_rows += 1
        if len(cells) > ncols:
            rep.rejected_rows.append(
                _defuse(s) + f"   [reason: {len(cells)} cells > "
                f"{ncols} columns — boundaries ambiguous]")
            continue
        if len(cells) < ncols:
            rep.repaired_cells += ncols - len(cells)
            cells += [" "] * (ncols - len(cells))

        def cell(j: int | None) -> str:
            return cells[j].strip() if j is not None else ""

        if i_type is not None:
            t = cell(i_type).upper()
            if t and t not in _VALID_TYPES:
                rep.rejected_rows.append(
                    _defuse(s) + f"   [reason: unknown Type '{cell(i_type)}']")
                rep.checked_rows -= 0
                continue
            if t and t != cells[i_type].strip():
                cells[i_type] = f" {t} "
                rep.repaired_cells += 1
        if i_addr is not None:
            norm, changed = _norm_address(cell(i_addr))
            if changed:
                cells[i_addr] = f" {norm} "
                rep.repaired_cells += 1
        if i_dir is not None and i_type is not None and not cell(i_dir):
            derived = _DIR_FOR_TYPE.get(cell(i_type).upper(), "")
            if derived:
                cells[i_dir] = f" {derived} "
                rep.repaired_cells += 1
        if i_status is not None and not cell(i_status):
            cells[i_status] = " DRAFT_UNVERIFIED "
            rep.repaired_cells += 1

        out.append("|" + "|".join(cells) + "|")

    out.extend(lines[i:])
    rep.ok = not rep.rejected_rows
    return "\n".join(out), rep


_PLC_TAG_OK_RE = re.compile(r"^DB_HMI\.(Cmd|Set|Sts)\.\w+$")


def validate_and_repair_rd11(content: str) -> tuple[str, SchemaGateReport]:
    """Gate an RD11 draft: enforce the DB_HMI interface contract on PLC_Tag.

    B1 (E2E finding 2026-07-07): the AI wrote bare tag names
    ('Automatik_Ein') into PLC_Tag, so hmi_codegen refused 22/22 rows and
    the whole HMI chain (interface → wiring approval → FC generation) was
    dead on arrival. The repair is DETERMINISTIC — area from
    ElementType/ReadWrite, member slug from the existing cell — and every
    repaired cell is counted in the report (never silent).

      Button/ModeSelector or Write → DB_HMI.Cmd.b<Slug>
      NumericInput                 → DB_HMI.Set.i<Slug>
      Indicator or Read            → DB_HMI.Sts.b<Slug>
    """
    rep = SchemaGateReport()
    lines = content.splitlines()
    hdr_i = None
    for i, ln in enumerate(lines):
        low = ln.lower()
        if ln.strip().startswith("|") and "hmi_tagid" in low and "plc_tag" in low:
            hdr_i = i
            break
    if hdr_i is None:
        rep.notes.append("no HMI_TagID/PLC_Tag table found — gate skipped")
        return content, rep

    cols = [c.strip() for c in lines[hdr_i].split("|")[1:-1]]
    ncols = len(cols)
    low_cols = [c.lower() for c in cols]

    def idx(*keys: str) -> int | None:
        for k in keys:
            for j, c in enumerate(low_cols):
                if k in c:
                    return j
        return None

    i_plc = idx("plc_tag")
    i_etype = idx("elementtype")
    i_rw = idx("readwrite")
    i_tagid = idx("hmi_tagid")
    if i_plc is None:
        rep.notes.append("PLC_Tag column not found — gate skipped")
        return content, rep

    def _slug(raw: str) -> str:
        s = re.sub(r"^(HMI|BTN|LMP|SEL|SET)_", "", raw.strip(), flags=re.I)
        s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
        return "".join(w.capitalize() for w in s.split("_"))[:24]

    out = lines[: hdr_i + 2]
    i = hdr_i + 2
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not (s.startswith("|") and s.endswith("|")):
            break
        i += 1
        cells = [c for c in s.split("|")][1:-1]
        rep.checked_rows += 1
        if len(cells) < ncols:
            cells += [" "] * (ncols - len(cells))
        plc = cells[i_plc].strip() if i_plc < len(cells) else ""
        if plc and not _PLC_TAG_OK_RE.match(plc):
            etype = (cells[i_etype].strip().upper()
                     if i_etype is not None and i_etype < len(cells) else "")
            rw = (cells[i_rw].strip().upper()
                  if i_rw is not None and i_rw < len(cells) else "")
            base = _slug(plc) or _slug(
                cells[i_tagid].strip() if i_tagid is not None else "")
            if not base:
                rep.rejected_rows.append(
                    _defuse(s) + "   [reason: PLC_Tag not derivable]")
                continue
            if "NUMERIC" in etype:
                fixed = f"DB_HMI.Set.i{base}"
            elif "INDICATOR" in etype or rw.startswith("R"):
                fixed = f"DB_HMI.Sts.b{base}"
            else:                    # Button / ModeSelector / Write default
                fixed = f"DB_HMI.Cmd.b{base}"
            cells[i_plc] = f" {fixed} "
            rep.repaired_cells += 1
        out.append("|" + "|".join(cells) + "|")

    out.extend(lines[i:])
    rep.ok = not rep.rejected_rows
    if rep.repaired_cells:
        rep.notes.append(
            f"PLC_Tag contract repair: {rep.repaired_cells} cell(s) rewritten "
            "to DB_HMI.<Cmd|Set|Sts>.<member> (deterministic, from "
            "ElementType/ReadWrite)")
    return "\n".join(out), rep


def gate_rd11_draft(project_root: Path, content: str) -> tuple[str, SchemaGateReport]:
    """validate_and_repair_rd11 + a visible banner when anything was repaired
    — the engineer must know the AI's tag paths were rewritten to the
    interface contract (traceable, never silent)."""
    repaired, rep = validate_and_repair_rd11(content)
    if rep.repaired_cells:
        banner = (
            f"> ⚠ **Schema gate:** {rep.repaired_cells} PLC_Tag cell(s) did "
            "not follow the `DB_HMI.<Cmd|Set|Sts>.<member>` interface "
            "contract and were rewritten deterministically "
            "(ElementType/ReadWrite → area). Review before approval.\n\n")
        repaired = banner + repaired
    return repaired, rep


def gate_rd01_draft(project_root: Path, content: str) -> tuple[str, SchemaGateReport]:
    """validate_and_repair + persist rejected rows to metadata/_history and
    stamp a visible banner into the draft when anything was rejected."""
    repaired, rep = validate_and_repair_rd01(content)
    if rep.rejected_rows:
        history = Path(project_root) / "metadata" / "_history"
        history.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rej = history / f"{ts}_RD01_rejected.txt"
        rej.write_text(
            "Rows rejected by the RD01 schema gate (operands defused so the\n"
            "cross-check re-adds them deterministically):\n\n"
            + "\n".join(rep.rejected_rows) + "\n",
            encoding="utf-8")
        banner = (
            f"> ⚠ **Schema gate:** {len(rep.rejected_rows)} malformed row(s) "
            f"moved to `_history/{rej.name}` — their operands will be "
            "re-added from the symbol table (deterministic).\n\n")
        repaired = banner + repaired
        rep.notes.append(f"rejected rows saved to {rej.name}")
    return repaired, rep
