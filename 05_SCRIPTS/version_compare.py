#!/usr/bin/env python3
"""
version_compare.py — deterministic diff engine for legacy project versions.

Old machine projects ship as version folders (`_Versionen/2018-08-18/`,
`_aktiv/`, …) full of STEP5/STEP7 artefacts: .SEQ symbol tables, .INI
editor state, binary .s5d MC5 code, print exports. This module answers
"what changed between two versions?" WITHOUT any AI: file-level scan
(hash/size/mtime) plus content diffs — symbol-aware for .SEQ, unified
diff for text, an honest note for binary.

Everything here is stdlib-only and side-effect free; the GUI layer
(factory_web.py) and the optional AI-hypothesis layer build on top of it.
All entry points return ``{"ok": False, "msg": ...}`` style results
instead of raising — the GUI surfaces messages to the engineer.

Encoding: STEP5-era files are cp437; decoded with errors="replace" so
umlauts may degrade in descriptions, but operands stay ASCII and match.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from datetime import datetime
from pathlib import Path

# Scan guard rails — version folders are engineer-picked, but a wrong
# click (e.g. C:\) must not freeze the GUI.
MAX_SCAN_DEPTH = 3
MAX_SCAN_FILES = 500

# Beyond this size a content diff is refused (file-level status still works).
MAX_DIFF_BYTES = 4 * 1024 * 1024

# unified_diff output cap — keeps the GUI and the AI summary bounded.
MAX_DIFF_LINES = 4000

BINARY_NOTE_S5D = (
    "Binary MC5 program code (.s5d) — content diff is not possible. "
    "Export the block list as an AWL/text listing from 'S5/S7 for Windows' "
    "to compare program logic."
)


def _looks_binary(data: bytes, sample: int = 2048) -> bool:
    """Same heuristic as factory_web._looks_binary, on bytes."""
    head = data[:sample]
    if not head:
        return False
    printable = sum(1 for b in head if 32 <= b <= 126 or b in (9, 10, 13))
    return printable / len(head) < 0.60


# ---------------------------------------------------------------------------
# .SEQ symbol tables
# ---------------------------------------------------------------------------

# Two field-separator dialects exist in real archives:
#   * \x1a record start + \x00 field separators (older exports)
#   * \t separators, one record per \r\n line (S5/S7 for Windows)
_SEQ_FIELD_SEP = re.compile(rb"[\x00\t]")

# Operand shapes that mark a field as "this is the address column":
# E 4.0 / A 33.6 / M 10.1 / T 5 / Z 3 / MW 100 / DB 20 / FB 1 …
_OPERAND_SHAPE = re.compile(
    r"^(E|A|I|Q|M|F|T|Z|C)\s*\d+(\.\d)?$"
    r"|^(EW|AW|IW|QW|MW|MB|MD|PEW|PAW|EB|AB|DW)\s*\d+$"
    r"|^(DB|FB|FC|OB|SB|PB|BB)\s*\d+$",
    re.IGNORECASE,
)


def _norm_operand(raw: str) -> str:
    """'E    4.0' and 'E 4.0' are the same address → collapse whitespace."""
    return " ".join(raw.split())


def parse_seq(data: bytes) -> tuple[dict[str, str], int]:
    """Parse a STEP5 .SEQ symbol table.

    Returns ``(symbols, parse_errors)`` where *symbols* maps the
    normalised operand (e.g. ``"E 4.0"``) to its description and
    *parse_errors* counts records that had content but no recognisable
    operand column. 0 symbols means "this is not a symbol table" —
    callers then fall back to text/binary handling.
    """
    symbols: dict[str, str] = {}
    errors = 0
    for line in data.split(b"\r\n"):
        line = line.strip(b"\n").lstrip(b"\x1a\t")
        # \x1a padding at EOF / empty lines are structure, not records
        if not line.strip(b"\x00 \t\x1a"):
            continue
        fields = [
            f.decode("cp437", errors="replace").strip()
            for f in _SEQ_FIELD_SEP.split(line)
        ]
        fields = [f for f in fields if f]
        if len(fields) < 2:
            errors += 1
            continue
        operand = _norm_operand(fields[0])
        if not _OPERAND_SHAPE.match(operand):
            errors += 1
            continue
        # field layout: long operand, [short operand,] description…
        rest = fields[1:]
        if rest and _norm_operand(rest[0]) == operand:
            rest = rest[1:]
        symbols[operand] = " ".join(rest).strip()
    return symbols, errors


def diff_seq(old_data: bytes, new_data: bytes) -> dict:
    """Symbol-level diff of two .SEQ tables (added/removed/changed)."""
    old_syms, old_err = parse_seq(old_data)
    new_syms, new_err = parse_seq(new_data)
    added = [
        {"operand": op, "desc": new_syms[op]}
        for op in new_syms if op not in old_syms
    ]
    removed = [
        {"operand": op, "desc": old_syms[op]}
        for op in old_syms if op not in new_syms
    ]
    changed = [
        {"operand": op, "old_desc": old_syms[op], "new_desc": new_syms[op]}
        for op in old_syms
        if op in new_syms and old_syms[op] != new_syms[op]
    ]
    unchanged = sum(
        1 for op in old_syms if op in new_syms and old_syms[op] == new_syms[op]
    )
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "parse_errors_old": old_err,
        "parse_errors_new": new_err,
    }


# ---------------------------------------------------------------------------
# Text + file-pair diffs
# ---------------------------------------------------------------------------

def diff_text(old_data: bytes, new_data: bytes,
              old_label: str = "old", new_label: str = "new") -> dict:
    """Unified diff of two text payloads (cp437, replace)."""
    old_lines = old_data.decode("cp437", errors="replace").splitlines()
    new_lines = new_data.decode("cp437", errors="replace").splitlines()
    lines = list(difflib.unified_diff(
        old_lines, new_lines, fromfile=old_label, tofile=new_label, lineterm=""
    ))
    truncated = len(lines) > MAX_DIFF_LINES
    if truncated:
        lines = lines[:MAX_DIFF_LINES] + ["… diff truncated …"]
    return {"lines": lines, "truncated": truncated}


def diff_file(a: str | None, b: str | None, relname: str) -> dict:
    """Content diff for one file across two versions.

    *a*/*b* are absolute paths (None = absent in that version). Returns a
    dict with ``mode`` in: seq | text | binary | too_large | added_only |
    removed_only — plus mode-specific payload. Never raises.
    """
    try:
        if a is None and b is None:
            return {"ok": False, "msg": f"'{relname}': absent in both versions"}
        if a is None:
            return {"ok": True, "mode": "added_only", "relname": relname,
                    "msg": "File exists only in the newer version."}
        if b is None:
            return {"ok": True, "mode": "removed_only", "relname": relname,
                    "msg": "File exists only in the older version."}

        pa, pb = Path(a), Path(b)
        if pa.stat().st_size > MAX_DIFF_BYTES or pb.stat().st_size > MAX_DIFF_BYTES:
            return {"ok": True, "mode": "too_large", "relname": relname,
                    "msg": f"File larger than {MAX_DIFF_BYTES // (1024*1024)} MB — "
                           "content diff skipped."}
        da, db = pa.read_bytes(), pb.read_bytes()

        suffix = Path(relname).suffix.casefold()
        if suffix == ".seq":
            # .SEQ files trip the binary heuristic (\x00/\x1a bytes) but ARE
            # parseable symbol tables — try the parser FIRST.
            seq = diff_seq(da, db)
            old_n = len(parse_seq(da)[0])
            new_n = len(parse_seq(db)[0])
            if old_n or new_n:
                return {"ok": True, "mode": "seq", "relname": relname,
                        "old_symbols": old_n, "new_symbols": new_n, **seq}
        if suffix == ".s5d":
            return {"ok": True, "mode": "binary", "relname": relname,
                    "msg": BINARY_NOTE_S5D,
                    "identical": hashlib.sha256(da).hexdigest()
                                 == hashlib.sha256(db).hexdigest()}
        if _looks_binary(da) or _looks_binary(db):
            return {"ok": True, "mode": "binary", "relname": relname,
                    "msg": "Binary content — no text diff available.",
                    "identical": hashlib.sha256(da).hexdigest()
                                 == hashlib.sha256(db).hexdigest()}
        return {"ok": True, "mode": "text", "relname": relname,
                **diff_text(da, db, f"a/{relname}", f"b/{relname}")}
    except Exception as exc:
        return {"ok": False, "msg": f"Diff failed for '{relname}': {exc}"}


# ---------------------------------------------------------------------------
# Folder scan + multi-version comparison
# ---------------------------------------------------------------------------

def scan_version_dir(path: str) -> dict:
    """Inventory one version folder (≤3 levels, ≤500 files).

    Keys in ``files`` are casefolded relative names — DOS-era tooling
    flips case freely (104711Z0.SEQ vs 104711zt.seq), and the same file
    must line up across versions.
    """
    root = Path(path)
    if not root.is_dir():
        return {"ok": False, "msg": f"Not a folder: {path}"}
    files: dict[str, dict] = {}
    truncated = False
    try:
        for fp in sorted(root.rglob("*")):
            if not fp.is_file():
                continue
            rel = fp.relative_to(root)
            if len(rel.parts) > MAX_SCAN_DEPTH:
                continue
            if len(files) >= MAX_SCAN_FILES:
                truncated = True
                break
            data = fp.read_bytes()
            st = fp.stat()
            files[str(rel).casefold()] = {
                "name": str(rel),
                "size": st.st_size,
                "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(
                    timespec="seconds"),
                "sha256": hashlib.sha256(data).hexdigest(),
                "binary": _looks_binary(data),
            }
    except Exception as exc:
        return {"ok": False, "msg": f"Scan failed for '{path}': {exc}"}
    return {"ok": True, "path": str(root), "name": root.name,
            "files": files, "truncated": truncated}


def _file_status(per_version: list[dict | None], hashes: list[str | None]) -> str:
    """added | removed | modified | unchanged | mixed across N versions."""
    present = [p is not None for p in per_version]
    real_hashes = {h for h in hashes if h is not None}
    if all(present):
        return "unchanged" if len(real_hashes) == 1 else "modified"
    if not present[0] and present[-1]:
        # absent at the start, there at the end — but holes in the middle
        # of a ≥3-version chain are "mixed", not a clean add
        return "added" if present == sorted(present) else "mixed"
    if present[0] and not present[-1]:
        return "removed" if present == sorted(present, reverse=True) else "mixed"
    return "mixed"


def compare_versions(folders: list[str]) -> dict:
    """File-level comparison across ≥2 version folders.

    Version identity = folder name (order = selection order). Returns a
    JSON-safe dict: versions[], files[] (with per-version presence and a
    status badge) and summary counts. Errors come back as ok:False.
    """
    if not folders or len(folders) < 2:
        return {"ok": False, "msg": "Select at least two version folders."}
    scans = []
    for f in folders:
        s = scan_version_dir(f)
        if not s["ok"]:
            return s
        scans.append(s)

    names = []
    for s in scans:
        # duplicate folder names (e.g. two _aktiv) must stay distinguishable
        n, base, i = s["name"], s["name"], 2
        while n in names:
            n = f"{base} ({i})"
            i += 1
        names.append(n)

    all_keys = sorted({k for s in scans for k in s["files"]})
    files = []
    summary = {"added": 0, "removed": 0, "modified": 0,
               "unchanged": 0, "mixed": 0}
    for key in all_keys:
        per_version = [s["files"].get(key) for s in scans]
        display = next(p["name"] for p in per_version if p)
        hashes = [p["sha256"] if p else None for p in per_version]
        status = _file_status(per_version, hashes)
        summary[status] += 1
        files.append({
            "key": key,
            "name": display,
            "kind": Path(display).suffix.casefold().lstrip("."),
            "binary": any(p["binary"] for p in per_version if p),
            "per_version": per_version,
            "status": status,
        })
    return {
        "ok": True,
        "versions": [{"name": n, "path": s["path"],
                      "file_count": len(s["files"]),
                      "truncated": s["truncated"]}
                     for n, s in zip(names, scans)],
        "files": files,
        "summary": {**summary, "total": len(files)},
    }


# ---------------------------------------------------------------------------
# AI summary input (Faz C) — binary content NEVER enters this string
# ---------------------------------------------------------------------------

def summarize_for_ai(result: dict, diffs: list[dict] | None = None,
                     max_chars: int = 12000) -> str:
    """Compact, text-only summary of a comparison for the AI prompt.

    *result* is a compare_versions() dict; *diffs* optional diff_file()
    results. Binary files contribute status lines only — never content.
    """
    out: list[str] = []
    out.append("Versions (oldest → newest, selection order):")
    for v in result.get("versions", []):
        out.append(f"  - {v['name']} ({v['file_count']} files)")
    s = result.get("summary", {})
    out.append(
        "File summary: "
        f"{s.get('modified', 0)} modified, {s.get('added', 0)} added, "
        f"{s.get('removed', 0)} removed, {s.get('unchanged', 0)} unchanged, "
        f"{s.get('mixed', 0)} mixed."
    )
    for f in result.get("files", []):
        if f["status"] == "unchanged":
            continue
        out.append(f"  {f['status'].upper():9s} {f['name']}"
                   + (" [binary]" if f["binary"] else ""))
    for d in diffs or []:
        if not d.get("ok"):
            continue
        mode = d.get("mode")
        out.append(f"\n## {d.get('relname', '?')} ({mode})")
        if mode == "seq":
            for e in d.get("added", []):
                out.append(f"  + {e['operand']}: {e['desc']}")
            for e in d.get("removed", []):
                out.append(f"  - {e['operand']}: {e['desc']}")
            for e in d.get("changed", []):
                out.append(f"  ~ {e['operand']}: '{e['old_desc']}'"
                           f" → '{e['new_desc']}'")
        elif mode == "text":
            out.extend(f"  {ln}" for ln in d.get("lines", []))
        else:
            # binary / too_large / added_only / removed_only → note only
            out.append(f"  {d.get('msg', '')}")
    text = "\n".join(out)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n… summary truncated …"
    return text
