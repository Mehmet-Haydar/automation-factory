#!/usr/bin/env python3
"""
assumption_ledger.py — the engineer's single page of everything uncertain.

The factory says "I don't know" in many places — #UNKNOWN devices, ambiguous
port bindings, ASSUMPTION sections, DRAFT_UNVERIFIED rows, UNPARSED
networks, NOT_VERIFIED safety fields. That honesty is only USABLE if it is
in ONE place: before a gate signature the engineer must be able to scan the
open questions in ten minutes, not grep 14 documents.

This module collects every uncertainty marker from metadata/ and REPORTS/
into REPORTS/ASSUMPTION_LEDGER.md, grouped by severity:

  BLOCKER — safety-relevant unknowns (RD05, Safety=YES rows)
  REVIEW  — wiring/logic uncertainty (ambiguous binds, #UNKNOWN devices,
            UNPARSED networks, rejected RD01 rows)
  INFO    — bulk draft status counts (DRAFT_UNVERIFIED row totals)

Deterministic, offline, idempotent — regenerated after every assembly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class LedgerSummary:
    blockers: int = 0
    reviews: int = 0
    info: int = 0
    report_path: Path | None = None


_ASSUMPTION_LINE = re.compile(
    r"^\s*(?:[-*]|\d+\.)?\s*(.*(?:ASSUMPTION|assumption)[:\s].*)$", re.M)


def _rd_files(root: Path):
    md = root / "metadata"
    if md.is_dir():
        yield from sorted(md.glob("RD*.md"))


def generate_assumption_ledger(project_root: Path) -> LedgerSummary:
    root = Path(project_root)
    summ = LedgerSummary()
    blockers: list[str] = []
    reviews: list[str] = []
    info: list[str] = []

    # --- RD documents -----------------------------------------------------
    for fp in _rd_files(root):
        text = fp.read_text(encoding="utf-8", errors="replace")
        rd = fp.name.split("_")[0]
        n_draft = text.count("DRAFT_UNVERIFIED")
        if n_draft:
            info.append(f"{rd}: {n_draft} row(s)/field(s) DRAFT_UNVERIFIED "
                        f"({fp.name})")
        n_nv = len(re.findall(r"NOT_VERIFIED", text))
        if n_nv:
            (blockers if rd == "RD05" else reviews).append(
                f"{rd}: {n_nv} NOT_VERIFIED field(s) ({fp.name})")
        if rd == "RD05":
            n_safety = len(re.findall(r"^\|.*\|\s*(?:YES|SIL|PL[a-e])\s*\|",
                                      text, re.M | re.I))
            blockers.append(
                f"RD05 safety draft requires a NAMED certified-engineer "
                f"sign-off before any gate lock ({fp.name})")
            _ = n_safety
        for m in _ASSUMPTION_LINE.finditer(text):
            line = m.group(1).strip()
            if len(line) > 15 and "assumption" in line.lower():
                reviews.append(f"{rd}: {line[:180]}")

    # --- assembly report ---------------------------------------------------
    asm = root / "REPORTS" / "ASSEMBLY_REPORT.md"
    if asm.is_file():
        text = asm.read_text(encoding="utf-8", errors="replace")
        for ln in text.splitlines():
            s = ln.strip()
            if s.startswith("- **") and ("ambiguous" in s
                                         or "not wired" in s
                                         or "not bound" in s):
                reviews.append(f"assembly: {s[2:].strip()[:180]}")
        m = re.search(r"(\d+) unknown item", text)
        if m and int(m.group(1)):
            reviews.append(f"assembly: {m.group(1)} #UNKNOWN item(s) — "
                           "see ASSEMBLY_REPORT.md")

    # --- flowchart cross-check ----------------------------------------------
    fc = root / "REPORTS" / "FLOWCHART_CROSSCHECK.md"
    if fc.is_file():
        text = fc.read_text(encoding="utf-8", errors="replace")
        for ln in text.splitlines():
            if ln.startswith("- ") and ("NOT a proven" in ln
                                        or "not found" in ln):
                reviews.append(f"flowchart: {ln[2:][:180]}")

    # --- interlock / sequence drafts ---------------------------------------
    il = root / "REPORTS" / "INTERLOCK_DRAFT.md"
    if il.is_file():
        text = il.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"refused \(honest\): (\d+)", text)
        if m and int(m.group(1)):
            reviews.append(
                f"interlock extraction: {m.group(1)} network(s) UNPARSED — "
                "see INTERLOCK_DRAFT.md § UNPARSED")

    # --- schema-gate rejections --------------------------------------------
    hist = root / "metadata" / "_history"
    if hist.is_dir():
        for rj in sorted(hist.glob("*RD01_rejected*")):
            n = sum(1 for ln in rj.read_text(
                encoding="utf-8", errors="replace").splitlines()
                if ln.strip().startswith("|"))
            reviews.append(f"schema gate: {n} RD01 row(s) rejected "
                           f"({rj.name}) — operands re-added "
                           "deterministically, verify the rest")

    summ.blockers, summ.reviews, summ.info = (
        len(blockers), len(reviews), len(info))

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    L = [
        "# ASSUMPTION LEDGER — everything the factory does NOT know",
        "",
        f"Generated: {now}",
        f"Open items: {summ.blockers} blocker(s) · {summ.reviews} "
        f"review item(s) · {summ.info} bulk-draft note(s)",
        "",
        "> One page, zero hunting: scan this BEFORE signing a gate. "
        "Every line links back to its source document.",
        "",
        "## 🟥 BLOCKER — safety-relevant, needs a certified engineer",
        "",
    ]
    L += [f"- {b}" for b in blockers] or ["- none"]
    L += ["", "## 🟨 REVIEW — wiring/logic uncertainty", ""]
    L += [f"- {r}" for r in reviews] or ["- none"]
    L += ["", "## ⬜ INFO — bulk draft status", ""]
    L += [f"- {i}" for i in info] or ["- none"]

    reports = root / "REPORTS"
    reports.mkdir(exist_ok=True)
    path = reports / "ASSUMPTION_LEDGER.md"
    path.write_text("\n".join(L), encoding="utf-8")
    summ.report_path = path
    return summ


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: assumption_ledger.py <project_root>")
        raise SystemExit(2)
    s = generate_assumption_ledger(Path(sys.argv[1]))
    print(f"blockers={s.blockers} reviews={s.reviews} info={s.info} "
          f"-> {s.report_path}")
