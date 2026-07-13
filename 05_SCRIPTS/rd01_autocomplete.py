#!/usr/bin/env python3
"""
rd01_autocomplete.py — deterministic RD01 completion from legacy symbol tables.

WHY (Beispielmaschine 4711 demo, ~300 IO): asking an LLM to
TRANSCRIBE a 190-row IO table is architecturally wrong — cheap models cap
output at ~8k tokens, the table gets cut mid-row, and the missing signals
surface weeks later in TIA. A Zuordnungsliste (io.seq / .SDF / .SEQ) is
STRUCTURED data: the machine parses it, the AI only enriches semantics.

Flow: rd01_crosscheck finds operands missing from the AI draft → this module
looks them up in the parsed symbol table(s) and APPENDS honest rows
(Status=DRAFT_UNVERIFIED, Notes flag the deterministic origin). Device hints
in classic comments ("ROLLENBAHN 3 * 8-M10") become Equipment=M10 so the
assembler's fallback grouping still works.

No AI, offline, idempotent (appends only operands still missing).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rd01_crosscheck import (  # type: ignore
    _canon_bit, _canon_word, _BIT_RE, _WORD_RE, crosscheck_rd01,
)
from device_lexicon import equipment_from_text  # type: ignore

_TAG_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_]+")


@dataclass
class SymbolRow:
    operand: str          # canonical: E4.0 / A28.0 / EW10 / AW96
    oldtag: str           # as written in the source ("E 4.0")
    name: str             # symbol or comment-derived tag
    desc: str             # human comment
    equipment: str = ""   # device id parsed from the comment ("M10")


def _canon_operand(cell: str) -> str | None:
    v = (cell or "").strip()
    m = _BIT_RE.fullmatch(v) or _BIT_RE.search(v)
    if m and m.group(0) == v.strip():
        return _canon_bit(m.group(1), m.group(2), m.group(3))
    m = _WORD_RE.fullmatch(v)
    if m:
        return _canon_word(m.group(1), m.group(2))
    return None


def _tag_from(symbol: str, desc: str, operand: str) -> str:
    """A stable, TIA-legal tag: prefer a real symbol, else the comment."""
    base = symbol if symbol and _canon_operand(symbol) is None else ""
    if not base:
        base = desc
    base = _TAG_SANITIZE_RE.sub("_", base.strip()).strip("_")
    if not base:
        base = operand
    if base and base[0].isdigit():
        base = "T_" + base
    return base[:32].upper().strip("_") or operand


def parse_symbol_tables(project_root: Path) -> dict[str, SymbolRow]:
    """Parse every symbol-table-like file under _raw/legacy_code.

    Recognised layout (S5 Zuordnungsliste export, tab/space separated):
        <intl op> <german op | symbol> <comment...>
    Any line containing at least one parseable operand cell is used; the
    remaining text becomes the comment. Returns {canonical_op: SymbolRow}.
    """
    out: dict[str, SymbolRow] = {}
    legacy = Path(project_root) / "_raw" / "legacy_code"
    if not legacy.is_dir():
        return out
    for fp in sorted(legacy.iterdir()):
        if not fp.is_file() or fp.suffix.lower() not in (".seq", ".sdf", ".txt"):
            continue
        try:
            lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for ln in lines:
            cells = [c.strip() for c in re.split(r"\t+|\s{2,}", ln) if c.strip()]
            if len(cells) < 2:
                continue
            ops = [(i, _canon_operand(c)) for i, c in enumerate(cells)]
            ops = [(i, o) for i, o in ops if o]
            if not ops:
                continue
            idx, op = ops[0]
            # comment = everything that is not an operand cell; a leading
            # single-token identifier (F-BREMSE) counts as the symbol, a
            # prose fragment ("KE ROLLENBAHN 2") stays part of the comment.
            op_idxs = {i for i, _o in ops}
            rest = [c for i, c in enumerate(cells) if i not in op_idxs and i > 0]
            symbol = ""
            if (len(rest) > 1
                    and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.\-]{1,23}", rest[0])):
                symbol = rest[0]
                rest = rest[1:]
            desc = " ".join(rest)
            equip = equipment_from_text(ln)
            # Register EVERY distinct operand found on the line. Normally the
            # intl and German cells canon-match (I 4.0 == E 4.0 → one entry),
            # but real legacy tables contain misaligned rows ("Q 32.2 |
            # A 40.6 | RESERVE" — seen in the 4711 blind test): both
            # operands exist in the code, so both get the row's semantics.
            for i, o in ops:
                if o in out:
                    continue
                oldtag = ""
                for j, o2 in ops:
                    if o2 == o and cells[j].upper().startswith(("E", "A")):
                        oldtag = cells[j]
                out[o] = SymbolRow(operand=o, oldtag=oldtag or cells[i],
                                   name=_tag_from(symbol, desc, o),
                                   desc=desc, equipment=equip)

    # Tag uniqueness: legacy tables repeat "RESERVE"-style comments across
    # dozens of rows — identical tags would trip the IO validator (duplicate
    # tag) and TIA import. Suffix repeated names with their operand.
    seen: dict[str, int] = {}
    for row in out.values():
        seen[row.name] = seen.get(row.name, 0) + 1
    for row in out.values():
        if seen[row.name] > 1:
            sfx = "_" + row.operand.replace(".", "_")
            row.name = row.name[: 32 - len(sfx)].rstrip("_") + sfx
    return out


def _iec_address(op: str) -> str:
    if op.startswith("EW"):
        return "%IW" + op[2:]
    if op.startswith("AW"):
        return "%QW" + op[2:]
    if op.startswith("ED"):
        return "%ID" + op[2:]
    if op.startswith("AD"):
        return "%QD" + op[2:]
    if op.startswith("E"):
        return "%I" + op[1:]
    if op.startswith("A"):
        return "%Q" + op[1:]
    return ""


def _row_type_dir(op: str) -> tuple[str, str]:
    if op.startswith("EW") or op.startswith("ED"):
        return "AI", "IN"
    if op.startswith("AW") or op.startswith("AD"):
        return "AO", "OUT"
    if op.startswith("E"):
        return "DI", "IN"
    return "DQ", "OUT"


def complete_rd01(project_root: Path) -> dict:
    """Append rows for operands the AI draft missed, from the symbol tables.

    Returns {ok, appended, still_missing, crosscheck_after}. Idempotent —
    a second run appends nothing. The RD01 stays DRAFT_UNVERIFIED; every
    appended row is flagged in Notes as deterministic (engineer sees the
    provenance)."""
    root = Path(project_root)
    rd01 = next(iter(sorted((root / "metadata").glob("RD01*.md"))), None)
    if rd01 is None:
        return {"ok": False, "appended": 0, "still_missing": [],
                "msg": "RD01 file not found"}

    lines = rd01.read_text(encoding="utf-8", errors="replace").splitlines()
    # locate the table: header row + last contiguous row index
    hdr_i = next((i for i, ln in enumerate(lines)
                  if ln.strip().startswith("|") and "tag" in ln.lower()), None)
    if hdr_i is None:
        return {"ok": False, "appended": 0, "still_missing": [],
                "msg": "RD01 table header not found"}
    cols = [c.strip().lower() for c in lines[hdr_i].split("|")[1:-1]]
    last = hdr_i
    for i in range(hdr_i, len(lines)):
        if lines[i].strip().startswith("|"):
            last = i
        elif i > hdr_i + 1:
            break
    # A truncated AI draft can end mid-row. The half row may still expose a
    # parseable address, fooling the cross-check into "covered" — drop it
    # BEFORE measuring what is missing, so the operand is re-added whole.
    if not lines[last].rstrip().endswith("|"):
        lines[last] = ""
        last -= 1
        rd01.write_text("\n".join(lines) + "\n", encoding="utf-8")

    before = crosscheck_rd01(root)
    missing = list(before.get("missing_in_rd01") or [])
    if not missing:
        return {"ok": True, "appended": 0, "still_missing": [],
                "crosscheck_after": before}

    symbols = parse_symbol_tables(root)

    def make_row(sym: SymbolRow) -> str:
        t, d = _row_type_dir(sym.operand)
        vals = {
            "tag": sym.name, "address": _iec_address(sym.operand),
            "type": t, "dir": d, "equipment": sym.equipment,
            "description": sym.desc,
            "oldtag": sym.oldtag,
            "notes": "auto-added from symbol table (deterministic)",
            "status": "DRAFT_UNVERIFIED",
        }
        return "| " + " | ".join(
            vals.get(c, vals.get(c.replace(" ", ""), "")) for c in cols) + " |"

    appended, still_missing = [], []
    for op in missing:
        sym = symbols.get(op)
        if sym is None:
            still_missing.append(op)
            continue
        appended.append(make_row(sym))

    if appended:
        lines[last + 1:last + 1] = appended
        rd01.write_text("\n".join(lines) + "\n", encoding="utf-8")

    after = crosscheck_rd01(root)
    return {"ok": True, "appended": len(appended),
            "still_missing": still_missing, "crosscheck_after": after}


def _canon_from_iec(addr: str) -> str | None:
    """'%I9.4' → 'E9.4', '%QW96' → 'AW96' — canonical legacy operand."""
    v = (addr or "").strip().lstrip("%").upper()
    m = re.fullmatch(r"([IQ])(\d{1,3})\.([0-7])", v)
    if m:
        return f"{'E' if m.group(1) == 'I' else 'A'}{int(m.group(2))}.{m.group(3)}"
    m = re.fullmatch(r"([IQ])([WD])(\d{1,4})", v)
    if m:
        return f"{'E' if m.group(1) == 'I' else 'A'}{m.group(2)}{int(m.group(3))}"
    return None


_STEM_PREFIX_RE = re.compile(r"^(KE|YH|SE|ST|SW|HM|K|Y|BA|IMPM|FLM)\s+")
_STEM_DEVREF_RE = re.compile(r"\*?\s*\d+\s*-\s*[MKYFP]\d{1,3}")
_STEM_PAREN_RE = re.compile(r"\([^)]*\)")


def _desc_stem_tokens(desc: str) -> frozenset:
    """Normalized token set of a legacy description for stem matching."""
    t = (desc or "").upper()
    t = _STEM_DEVREF_RE.sub(" ", t)
    t = _STEM_PAREN_RE.sub(" ", t)
    t = _STEM_PREFIX_RE.sub("", t.strip())
    return frozenset(tok for tok in re.split(r"[^\wÄÖÜ.]+", t) if tok)


def propagate_equipment_by_stem(rows: list[dict]) -> int:
    """Second-pass fill: inherit Equipment across rows describing the SAME
    machine part ("ROLLENBAHN 1.1" input ↔ "ROLLENBAHN 1.1 SCHUETZ" output).

    Guards (fail-safe — wrong grouping is worse than no grouping):
      * the FILLED row's stem tokens must be a SUBSET of the empty row's;
      * the overlap must include at least one digit-bearing anchor token
        ("1.1", "3") — generic words alone never match;
      * exactly ONE distinct equipment id may qualify, else untouched.
    rows: [{"desc":…, "equipment":…}] mutated in place; returns fill count."""
    filled = [(r, _desc_stem_tokens(r.get("desc", ""))) for r in rows
              if (r.get("equipment") or "").strip()]
    n = 0
    for row in rows:
        if (row.get("equipment") or "").strip():
            continue
        desc = (row.get("desc") or "").strip().upper()
        # Operator controls (ST=Taster, SW=Wahlschalter, BA=Betriebsart)
        # are STATION signals — attributing them to a device re-creates
        # the button→feedback mis-bind (D-run 2026-07-03). Never inherit.
        if re.match(r"^(ST|SW|BA)[\s*]", desc):
            continue
        toks = _desc_stem_tokens(row.get("desc", ""))
        if not toks:
            continue
        candidates = set()
        for src, stoks in filled:
            if not stoks or not stoks <= toks:
                continue
            anchors = {t for t in stoks if any(c.isdigit() for c in t)}
            if not anchors or not anchors <= toks:
                continue
            candidates.add(src["equipment"].strip().upper())
        if len(candidates) == 1:
            row["equipment"] = candidates.pop()
            row["_stem_filled"] = True
            n += 1
    return n


def enrich_equipment(project_root: Path) -> dict:
    """Fill EMPTY Equipment cells of the RD01 table — deterministically.

    WHY (A/B/C field measurement 2026-07-03): the assembler groups devices by
    the Equipment column; when the AI leaves it empty (it does, depending on
    input style), wiring collapses from 15 to 5 bound ports. The device
    reference is already IN the data ('… * 7-M3 (EINLAUF)') — no AI needed.

    Sources per row, in order: (1) devref pattern in the row's own
    Description cell, (2) the symbol-table row of the operand (OldTag or
    Address). Only EMPTY cells are written; never overwrites an engineer's
    or the AI's value. Idempotent. Returns {ok, filled, rows}."""
    root = Path(project_root)
    rd01 = next(iter(sorted((root / "metadata").glob("RD01*.md"))), None)
    if rd01 is None:
        return {"ok": False, "filled": 0, "msg": "RD01 file not found"}

    lines = rd01.read_text(encoding="utf-8", errors="replace").splitlines()
    hdr_i = next((i for i, ln in enumerate(lines)
                  if ln.strip().startswith("|") and "tag" in ln.lower()), None)
    if hdr_i is None:
        return {"ok": False, "filled": 0, "msg": "RD01 table header not found"}
    cols = [c.strip().lower() for c in lines[hdr_i].split("|")[1:-1]]

    def col_idx(*keys: str) -> int | None:
        for k in keys:
            for i, c in enumerate(cols):
                if k in c:
                    return i
        return None

    i_equip = col_idx("equipment", "ekipman", "cihaz", "gerät", "geraet",
                      "device")
    i_desc = col_idx("desc", "açıklama", "tanım")
    i_addr = col_idx("address", "adres")
    i_old = col_idx("oldtag", "old tag", "legacy", "eski")
    if i_equip is None:
        return {"ok": False, "filled": 0, "msg": "no Equipment column"}

    symbols = None  # lazy — only parse the tables if a row needs them
    filled = 0
    for i in range(hdr_i + 2, len(lines)):
        ln = lines[i]
        if not ln.strip().startswith("|"):
            if ln.strip():
                break
            continue
        cells = ln.split("|")
        # cells[0] is the text before the leading pipe ('') — data starts at 1
        if len(cells) < len(cols) + 1:
            continue

        def cell(idx: int | None) -> str:
            return cells[idx + 1].strip() if idx is not None \
                and idx + 1 < len(cells) else ""

        if cell(i_equip):
            continue
        equip = equipment_from_text(cell(i_desc))
        if not equip:
            op = None
            for raw in (cell(i_old), cell(i_addr)):
                if not raw:
                    continue
                op = _canon_operand(raw) or _canon_from_iec(raw)
                if op:
                    break
            if op:
                if symbols is None:
                    symbols = parse_symbol_tables(root)
                sym = symbols.get(op)
                if sym is not None:
                    equip = sym.equipment \
                        or equipment_from_text(sym.desc)
        if not equip:
            continue
        cells[i_equip + 1] = f" {equip} "
        lines[i] = "|".join(cells)
        filled += 1

    # pass 2 — stem propagation across rows of the same machine part
    # ("ROLLENBAHN 1.1" feedback carries M3 → "ROLLENBAHN 1.1 SCHUETZ"
    # output inherits it). Guarded: unique candidate + numeric anchor.
    rows: list[dict] = []
    for i in range(hdr_i + 2, len(lines)):
        ln = lines[i]
        if not ln.strip().startswith("|"):
            if ln.strip():
                break
            continue
        cells = ln.split("|")
        if len(cells) < len(cols) + 1:
            continue
        rows.append({
            "_i": i,
            "desc": cells[i_desc + 1].strip() if i_desc is not None else "",
            "equipment": cells[i_equip + 1].strip(),
        })
    stem_filled = propagate_equipment_by_stem(rows)
    for row in rows:
        if row.get("_stem_filled"):
            cells = lines[row["_i"]].split("|")
            cells[i_equip + 1] = f" {row['equipment']} "
            lines[row["_i"]] = "|".join(cells)
    filled += stem_filled

    if filled:
        rd01.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "filled": filled, "stem_filled": stem_filled}
