#!/usr/bin/env python3
"""
traceability_matrix.py — old↔new signal traceability in one table.

Auditors (TÜV, customer FAT) ask ONE question about a retrofit: "where did
this old signal go?" The data already exists across RD01, the assembly
manifest and the legacy sources — this module joins it into
REPORTS/TRACEABILITY_MATRIX.md:

  legacy operand | legacy symbol/description | source blocks | new tag |
  new address | device | library FB | bound port

Deterministic, offline. Unmapped signals stay visible ("—") — a row never
disappears just because nothing references it yet.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class TraceSummary:
    rows: int = 0
    bound: int = 0
    with_device: int = 0
    report_path: Path | None = None


def _bound_ports_from_ob1(root: Path) -> dict[str, tuple[str, str]]:
    """{signal tag: (instance, port)} parsed from the generated OB_Main."""
    ob = root / "_output" / "scl" / "OB_Main.scl"
    out: dict[str, tuple[str, str]] = {}
    if not ob.is_file():
        return out
    inst = ""
    for ln in ob.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r'\s*"(iDB_\w+)"\(', ln)
        if m:
            inst = m.group(1)
        m = re.match(r'\s*(\w+)\s*(?::=|=>)\s*"([^"]+)"', ln)
        if m and inst:
            out[m.group(2)] = (inst, m.group(1))
    return out


def _fb_by_device(root: Path) -> dict[str, str]:
    mp = root / "_output" / "scl" / "_assembly_manifest.json"
    if not mp.is_file():
        return {}
    try:
        man = json.loads(mp.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {d: (v or {}).get("fb") or "—"
            for d, v in (man.get("devices") or {}).items()}


def generate_traceability_matrix(project_root: Path) -> TraceSummary:
    root = Path(project_root)
    from iec_tag_generator import parse_rd01_signals  # type: ignore

    signals = parse_rd01_signals(root)
    bound = _bound_ports_from_ob1(root)
    fbs = _fb_by_device(root)
    summ = TraceSummary(rows=len(signals))

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    L = [
        "# TRACEABILITY MATRIX — legacy signal → new program",
        "",
        f"Generated: {now}",
        f"Signals: {len(signals)}",
        "",
        "| Legacy operand | Legacy description | Source blocks | New tag | "
        "New address | Device | Library FB | Bound port |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for sig in signals:
        name = sig.get("name", "")
        old = (sig.get("oldtag") or "—").strip() or "—"
        desc = (sig.get("desc") or "").strip()[:60] or "—"
        src = (sig.get("src") or sig.get("srcmodule") or "").strip()
        addr = (sig.get("address") or "—").strip() or "—"
        dev = (sig.get("equipment") or "").strip()
        fb = fbs.get(dev.upper(), "—") if dev else "—"
        port = "—"
        if name in bound:
            inst, pname = bound[name]
            port = f"`{inst}.{pname}`"
            summ.bound += 1
        if dev:
            summ.with_device += 1
        L.append(f"| {old} | {desc} | {src or '—'} | {name} | {addr} | "
                 f"{dev or '—'} | {fb} | {port} |")

    L += [
        "",
        f"Bound to a library port: {summ.bound}/{summ.rows} · "
        f"attributed to a device: {summ.with_device}/{summ.rows}",
        "",
        "> Rows with `—` in Device/Port are NOT lost — they are the "
        "engineer's wiring worklist (see ASSUMPTION_LEDGER.md).",
    ]

    # Gate-3 conscious choices: reconciliation deviations the engineer
    # waived by name. Auditors get the SAME list the lock saw — a waiver
    # is a documented decision, never a silent skip.
    try:
        from gate3_consistency import load_waivers  # type: ignore
        waivers = load_waivers(root)
    except Exception:
        waivers = {}
    if waivers:
        L += [
            "",
            "## Conscious deviations (Gate-3 reconciliation waivers)",
            "",
            "| Finding | Subject | Reason | Waived by | Date |",
            "|---|---|---|---|---|",
        ]
        for _fid, w in sorted(waivers.items(), key=lambda kv: kv[1].get("at", "")):
            L.append(
                f"| {w.get('title', '—')} | {w.get('subject', '—')} | "
                f"{w.get('reason', '—')} | {w.get('by', '—')} | "
                f"{w.get('at', '—')} |")

    reports = root / "REPORTS"
    reports.mkdir(exist_ok=True)
    path = reports / "TRACEABILITY_MATRIX.md"
    path.write_text("\n".join(L), encoding="utf-8")
    summ.report_path = path
    return summ


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: traceability_matrix.py <project_root>")
        raise SystemExit(2)
    s = generate_traceability_matrix(Path(sys.argv[1]))
    print(f"rows={s.rows} bound={s.bound} with_device={s.with_device} "
          f"-> {s.report_path}")
