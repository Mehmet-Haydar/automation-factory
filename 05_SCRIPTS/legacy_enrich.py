#!/usr/bin/env python3
"""
legacy_enrich.py — deterministic S5→S7 enrichment of legacy AWL exports.

WHY (A/B/C benchmark on the Beispielmaschine 4711 demo): the raw
"S5 for Windows" AWL export is bare mnemonics — no comments, no symbols,
bracket-numbered networks. Feeding it to the analysis AI yields generic
block summaries. Feeding the SAME code with the Zuordnungsliste symbols
injected inline ("AN I 6.7  // I6.7: STEUERUNG EIN") yields operand-level
correct analysis (verified against ground truth: 6/6 inferred flag meanings
matched the reference symbol list). This module does that enrichment
deterministically — no AI, offline, milliseconds:

  1. bracket networks  "[5 … ***]"  →  "NETWORK  // Segment 5"
  2. S5 flags          F 1.0 / FW 111 →  M 1.0 / MW 111
  3. S5 timer literals KT 050.0     →  S5T#500MS
  4. EVERY I/Q/M/T operand line gets its Zuordnungsliste description as an
     inline comment — the locality is what makes the AI "see" the plant.

The original files are never modified; enrichment happens in memory (see
factory_web pre-analysis) or into a sibling directory via enrich_project().
Symbols come from every *.seq/*.sdf file under _raw/legacy_code — drop the
full Zuordnungsliste (with M/T rows) next to io.seq to enrich flags too.
"""

from __future__ import annotations

import re
from pathlib import Path

_SYMBOL_EXTS = {".seq", ".sdf"}
_AWL_EXTS = {".awl", ".stl"}

# S5 timer constant: KT <value>.<base>, base 0..3 → 10ms/100ms/1s/10s
_TIMEBASE = {0: 0.01, 1: 0.1, 2: 1.0, 3: 10.0}
_KT_RE = re.compile(r"\bKT\s+(\d+)\.([0-3])\b")

# operands as they appear in international S5 exports
_IO_RE = re.compile(r"\b([IQ])\s?(\d{1,3}\.\d)\b")
_M_RE = re.compile(r"\bM\s?(\d{1,3}\.\d)\b")
_T_RE = re.compile(r"\bT\s?(\d{1,3})\b")

# symbol-table row operand cell: "I 4.0", "Q 28.4", "M 1.0", "MW 111", "T 5"
_SYMOP_RE = re.compile(r"^([EAIQMTZ]|EW|AW|IW|QW|MW)\s*(\d+(?:\.\d)?)$")

# bracket-format detection: "###PG:…" header or a "[N" network marker line
_S5_HEADER_RE = re.compile(r"^###PG", re.M)
_S5_NET_RE = re.compile(r"^\[\d+\s*$", re.M)


def _read_text(fp: Path) -> str:
    """Zuordnungsliste exports are often cp850 — fall back when utf-8 mangles."""
    raw = fp.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if text.count("�") > max(3, len(text) // 500):
        try:
            return raw.decode("cp850")
        except Exception:
            pass
    return text


def is_s5_bracket_awl(text: str) -> bool:
    """True when the text looks like a bare S5-for-Windows AWL export."""
    return bool(_S5_HEADER_RE.search(text) or _S5_NET_RE.search(text))


def load_symbols(legacy_dir: Path) -> dict[str, str]:
    """{canonical operand ('I4.0', 'Q28.4', 'M1.0', 'T5'): description}.

    Reads every symbol-table file (*.seq/*.sdf) in the directory. Both the
    international (I/Q) and German (E/A) spellings key the same description
    so lookups work from either side. RESERVE rows are skipped."""
    sym: dict[str, str] = {}
    if not legacy_dir.is_dir():
        return sym
    for fp in sorted(legacy_dir.iterdir()):
        if not fp.is_file() or fp.suffix.lower() not in _SYMBOL_EXTS:
            continue
        for line in _read_text(fp).splitlines():
            parts = [p.strip() for p in line.split("\t") if p.strip()]
            if len(parts) < 2:
                continue
            desc = parts[-1]
            if not desc or desc.upper() == "RESERVE":
                continue
            for cell in parts[:-1]:
                m = _SYMOP_RE.match(cell)
                if not m:
                    continue
                kind, addr = m.group(1).upper(), m.group(2)
                key = f"{kind}{addr}"
                sym.setdefault(key, desc)
                # cross-key the German/international twin (E↔I, A↔Q)
                twin = {"E": "I", "I": "E", "A": "Q", "Q": "A",
                        "EW": "IW", "IW": "EW", "AW": "QW", "QW": "AW"}
                if kind in twin:
                    sym.setdefault(f"{twin[kind]}{addr}", desc)
    return sym


def _kt_to_s5t(m: re.Match) -> str:
    val = int(m.group(1)) * _TIMEBASE[int(m.group(2))]
    if val >= 1 and val == int(val):
        return f"S5T#{int(val)}S"
    return f"S5T#{int(round(val * 1000))}MS"


def _enrich_line(line: str, sym: dict[str, str]) -> str:
    # F flags are S7 M memory
    line = re.sub(r"\bF\s?(\d{1,3}\.\d)\b", r"M \1", line)
    line = re.sub(r"\bFW\s?(\d{1,4})\b", r"MW \1", line)
    line = re.sub(r"\bFD\s?(\d{1,4})\b", r"MD \1", line)
    line = _KT_RE.sub(_kt_to_s5t, line)
    # one inline comment per line: physical IO first, flags/timers second
    key = None
    io = _IO_RE.search(line)
    if io:
        key = f"{io.group(1)}{io.group(2)}"
    else:
        mm = _M_RE.search(line)
        if mm:
            key = f"M{mm.group(1)}"
        else:
            tm = _T_RE.search(line)
            if tm:
                key = f"T{tm.group(1)}"
    if key:
        desc = sym.get(key)
        if desc:
            return f"{line.rstrip()}\t// {key}: {desc}"
    return line


def enrich_awl_text(text: str, sym: dict[str, str], name: str = "") -> str:
    """Convert one bare S5 bracket-format AWL export to commented S7 STL."""
    out = [f"// {name or 'legacy block'} — S5->S7 enriched by "
           "AUTOMATION_FACTORY legacy_enrich (deterministic; symbols from "
           "Zuordnungsliste)"]
    for raw in text.splitlines():
        s = raw.rstrip("\n")
        if s.startswith("###PG"):
            continue
        mnet = re.match(r"^\[(\d+)\s*$", s.strip())
        if mnet:
            out.append("")
            out.append(f"NETWORK  // Segment {mnet.group(1)}")
            continue
        stripped = s.strip()
        if stripped in ("***\t]", "***]", "***"):
            continue
        if stripped.endswith("]"):
            s = s.rstrip().rstrip("]").rstrip()
            if not s.strip():
                continue
        out.append(_enrich_line(s, sym))
    out.append("")
    return "\n".join(out)


def enrich_project(project_root: Path) -> dict:
    """Batch mode: write enriched copies next to the originals.

    _raw/legacy_code/*.AWL (bracket S5) → _raw/legacy_enriched/<stem>_S7.AWL.
    Originals untouched (audit trail). Returns {ok, enriched, skipped,
    symbols}."""
    legacy = Path(project_root) / "_raw" / "legacy_code"
    out_dir = Path(project_root) / "_raw" / "legacy_enriched"
    if not legacy.is_dir():
        return {"ok": False, "enriched": 0, "skipped": 0, "symbols": 0,
                "msg": "_raw/legacy_code not found"}
    sym = load_symbols(legacy)
    enriched = skipped = 0
    for fp in sorted(legacy.iterdir()):
        if not fp.is_file() or fp.suffix.lower() not in _AWL_EXTS:
            continue
        text = _read_text(fp)
        if not is_s5_bracket_awl(text):
            skipped += 1
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{fp.stem}_S7{fp.suffix}").write_text(
            enrich_awl_text(text, sym, fp.stem), encoding="utf-8")
        enriched += 1
    return {"ok": True, "enriched": enriched, "skipped": skipped,
            "symbols": len(sym)}


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print("usage: legacy_enrich.py <project_root>")
        raise SystemExit(2)
    print(json.dumps(enrich_project(Path(sys.argv[1])), indent=2))
