#!/usr/bin/env python3
"""
customer_report.py — Customer Delivery Report PDF Generator (Phase 28-B)

Creates a professional PDF report from the project data:
  - Cover page (project name, customer, date, platform)
  - Project summary table
  - IO list (from RD01)
  - SCL block list (_output/scl/)
  - Test status (if a FAT/SAT protocol exists)
  - Delivery checklist
  - Signature / approval page

Dependency: reportlab  (pip install reportlab)
Fallback:   if reportlab is missing, a Markdown report is produced.

CLI:
  python customer_report.py --project PROJECT_PATH [--out FOLDER]
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# -- PDF infrastructure now lives in pdf_common (Faz 1.4) ----------------------
# Style values, palette and table styling are byte-identical to the former
# in-file definitions; customer_report output is unchanged.
import sys as _sys
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SCRIPTS_DIR))

from pdf_common import HAS_REPORTLAB  # noqa: E402

if HAS_REPORTLAB:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )
    from pdf_common import (
        NAVY as _NAVY, STEEL as _STEEL, LIGHT as _LIGHT, GREEN as _GREEN,
        ORANGE as _ORANGE, GRAY as _GRAY, LGRAY as _LGRAY,
    )

FACTORY_ROOT = Path(__file__).resolve().parent.parent


# -- Exceptions ---------------------------------------------------------------

class ReportPreconditionError(RuntimeError):
    """Raised when the project does not meet the preconditions for report generation.

    Fail-closed: if any required gate or safety check is missing or unverified,
    the report is NOT produced.  The caller receives a clear reason string.
    """
    def __init__(self, reasons: List[str]) -> None:
        self.reasons = reasons
        super().__init__(
            "Report preconditions not met: " + "; ".join(reasons)
        )


# -- Precondition helpers -----------------------------------------------------

# R-C-1 — Gate History Hash Chain Verification
# Hash computation is byte-identical to advance_gate(): sort_keys=True, ensure_ascii=False,
# payload field order: gate, when, who, signature, note, prev_hash.
_CHAIN_PAYLOAD_FIELDS = ("gate", "when", "who", "signature", "note", "prev_hash")


def verify_gate_chain(gate_history: list) -> list[str]:
    """Verify the SHA-256 prev_hash → hash chain of gate_history records.

    Returns a list of violation strings (empty list → chain is valid).

    SCOPE (M-07, documented 2026-07-10): this verifies INTERNAL consistency
    — it catches accidental/partial edits of PROJECT_STATE.json. It cannot
    detect a chain rebuilt wholesale with recomputed hashes; for that, each
    record written since 2026-07-10 is cross-anchored into the hash-chained
    AI decision log (record["audit_anchor"], AI_DECISION_LOG.jsonl entry
    "gate_advance:<n>" carrying the record hash) — forging a signature then
    requires rewriting both files consistently.

    Rules (R-C-1):
    - Records are iterated in gate-number order.
    - Genesis record (first in sorted order): prev_hash == "" or "GENESIS" or absent — accepted.
    - Each subsequent record: its prev_hash must equal the previous record's hash.
    - Hash recomputation uses the same canonical payload as advance_gate():
        json.dumps({field: entry[field] for field in _CHAIN_PAYLOAD_FIELDS},
                   ensure_ascii=False, sort_keys=True).encode("utf-8")
      → sha256 hexdigest.
    - Legacy record (hash field absent): WARN, skip verification for that record (backwards-compat).
    - Hash field present but incorrect: VIOLATION (counted as tampering).

    This function never raises; all errors are returned as violation strings.
    """
    violations: list[str] = []
    history = list(gate_history or [])

    # Sort by gate number for deterministic traversal; ties keep original order (stable).
    try:
        history_sorted = sorted(history, key=lambda e: int(e.get("gate", 0)))
    except Exception as exc:
        violations.append(f"Gate chain ordering failed: {exc}")
        return violations

    prev_hash: str | None = None  # None = first record not processed yet

    for idx, entry in enumerate(history_sorted):
        gate_n = entry.get("gate", "?")
        stored_hash: str | None = entry.get("hash")

        # --- Legacy record: hash field absent entirely → warn, skip verification ---
        if stored_hash is None:
            violations.append(
                f"WARNING (legacy): Gate {gate_n} record has no 'hash' field — "
                "chain verification skipped for this record"
            )
            # We cannot advance the prev_hash chain; reset it so the next record
            # is not linked to this "unknown" hash → since we do not know the
            # next record's prev_hash, we will skip that one too.
            prev_hash = None
            continue

        # --- prev_hash consistency ---
        entry_prev = entry.get("prev_hash", "")
        if idx == 0:
            # Genesis: prev_hash == "" or "GENESIS" is accepted.
            if entry_prev not in ("", "GENESIS"):
                violations.append(
                    f"Chain violation: Gate {gate_n} genesis record — "
                    f"prev_hash='{entry_prev}' expected '' or 'GENESIS'"
                )
        else:
            if prev_hash is None:
                # Previous record was legacy; this record's prev_hash cannot be verified.
                pass
            elif entry_prev != prev_hash:
                violations.append(
                    f"Chain violation: Gate {gate_n} record — "
                    f"prev_hash='{entry_prev[:12]}…' ≠ previous hash='{prev_hash[:12]}…'"
                )

        # --- Hash verification: does stored_hash actually represent this payload? ---
        try:
            payload_dict = {k: entry[k] for k in _CHAIN_PAYLOAD_FIELDS if k in entry}
            # advance_gate() writes all fields; if any are missing, fail-closed:
            missing = [k for k in _CHAIN_PAYLOAD_FIELDS if k not in entry]
            if missing:
                violations.append(
                    f"Chain violation: Gate {gate_n} record is missing payload fields: "
                    f"{missing} — hash cannot be verified"
                )
                prev_hash = stored_hash  # advance the chain (violation already recorded)
                continue
            payload = json.dumps(
                payload_dict, ensure_ascii=False, sort_keys=True
            ).encode("utf-8")
            computed = hashlib.sha256(payload).hexdigest()
            if computed != stored_hash:
                violations.append(
                    f"Chain violation: Gate {gate_n} record SHA-256 mismatch — "
                    f"computed='{computed[:12]}…' stored='{stored_hash[:12]}…' "
                    "(record has been tampered with)"
                )
        except Exception as exc:
            violations.append(
                f"Gate {gate_n} hash computation failed: {exc}"
            )

        prev_hash = stored_hash  # update for the next iteration

    return violations


def _gate7_approved(gate_history: list) -> bool:
    """Return True only when Gate 7 (FAT/SAT) has an *approved* record in the
    hash-chained gate_history list stored inside PROJECT_STATE.json.

    The gate_history record written by advance_gate() carries:
      {"gate": 7, "note": "approved", "who": ..., "hash": ..., ...}
    We do NOT trust the bare ``status`` field of PROJECT_STATE.json because
    that field can be written without going through the gate API.

    R-C-1: Also verifies the hash chain; returns False when chain violations
    are found (tampered records cannot yield a trusted gate-7 approval).
    """
    chain_violations = verify_gate_chain(gate_history or [])
    # Legacy-only warnings (WARNING prefix) do not block; hard violations do.
    hard_violations = [v for v in chain_violations if not v.startswith("WARNING")]
    if hard_violations:
        return False
    # R-C-3: null-hash gate-7 records are untrusted — a spoofed approval can be
    # injected by writing {"gate": 7, "note": "approved", "hash": null} which
    # verify_gate_chain treats as a legacy WARNING (not hard violation).
    return any(
        int(entry.get("gate", 0)) == 7
        and entry.get("note") == "approved"
        and entry.get("hash") is not None
        for entry in (gate_history or [])
    )


def _rd05_verified(state: dict) -> bool:
    """Return True when RD05 Safety carries a certified engineer's approval.

    Two equally valid signals (B6, E2E finding 2026-07-07 — the gate engine
    accepted the 3-state review while this check only read the file status,
    blocking a report on a properly reviewed project):
      1. 3-state review model: PROJECT_STATE.rd_verifications.RD05 is
         reviewed/locked (named sign-off, W-A2) or explicitly N/A with a
         named justification.
      2. Legacy file status: rd_status.RD05 not DRAFT_UNVERIFIED/DRAFT.
    Fail-closed when neither says approved.
    """
    rd05_ver = (state.get("rd_verifications") or {}).get("RD05") or {}
    if rd05_ver.get("na"):
        return True
    if rd05_ver.get("reviewed") or rd05_ver.get("locked"):
        # Staleness guard (same discipline as the gate engine): a review is
        # only trusted while the recorded content hash still matches the
        # RD05 file on disk — an edit after sign-off demotes it. If we can't
        # locate the file, fall through to the legacy status check
        # (fail-closed there).
        rec_hash = rd05_ver.get("content_hash") or ""
        proot = state.get("_project_path")
        if rec_hash and proot:
            import hashlib as _hl
            for fp in sorted(Path(proot).glob("metadata/RD05*.md")):
                if _hl.sha256(fp.read_bytes()).hexdigest() == rec_hash:
                    return True
        elif rec_hash:
            # no path available to re-verify — accept the named review record
            return True
    rd_status = state.get("rd_status", {})
    rd05 = rd_status.get("RD05_Safety") or rd_status.get("RD05", {})
    if not rd05:
        # RD05 entry missing entirely — treat as unverified (fail-closed).
        return False
    status = (rd05.get("status") or "").upper()
    return status not in ("DRAFT_UNVERIFIED", "", "DRAFT")


def _determine_status_badge(state: dict) -> str:
    """Derive the project status badge from the gate_history hash chain.

    Returns ``"COMPLETED"`` only when Gate 7 has an approved record.
    Returns ``"IN PROGRESS"`` in every other case (fail-closed).

    This intentionally does NOT read ``state["status"]`` to prevent a
    simple JSON edit from promoting an incomplete project to COMPLETED.
    """
    gate_history = state.get("gate_history") or []
    return "COMPLETED" if _gate7_approved(gate_history) else "IN PROGRESS"


def _check_report_preconditions(project_path: Path, state: dict) -> None:  # noqa: ARG001
    """Raise ReportPreconditionError if the project is not ready for customer delivery.

    Checks (fail-closed — ALL must pass):
    1. Gate history hash chain must be intact (R-C-1: no hard violations).
    2. Gate 7 (FAT/SAT) must have an approved record in gate_history.
    3. RD05 Safety document must NOT be in DRAFT_UNVERIFIED state.

    ``project_path`` is accepted for future extension (e.g. reading separate
    gate_history files), but gate_history is currently read from ``state``.
    """
    reasons: List[str] = []

    # B6: give the RD05 staleness guard a way to re-verify the review hash
    # against the file on disk (state alone has no filesystem anchor).
    state = {**state, "_project_path": str(project_path)}

    gate_history = state.get("gate_history") or []

    # R-C-1 — Chain integrity: hard violations block the report.
    chain_violations = verify_gate_chain(gate_history)
    hard_violations = [v for v in chain_violations if not v.startswith("WARNING")]
    if hard_violations:
        reasons.append(
            "Gate history hash chain integrity is broken — "
            "suspected unauthorized modification (violations: "
            + "; ".join(hard_violations) + ")"
        )

    # Gate 7 approval: _gate7_approved() also runs the chain check, but we have
    # already evaluated chain_violations here; if there is a hard violation we
    # reject anyway. Direct check here to avoid running the chain a second time.
    # R-C-3: also require non-null hash — null-hash records are untrusted (spoofable).
    gate7_ok = any(
        int(entry.get("gate", 0)) == 7
        and entry.get("note") == "approved"
        and entry.get("hash") is not None
        for entry in gate_history
    )
    if not gate7_ok:
        reasons.append(
            "Gate 7 (FAT/SAT) has not been approved — advance through the gate "
            "with a valid signature before generating a customer report"
        )

    if not _rd05_verified(state):
        reasons.append(
            "RD05 Safety configuration is DRAFT_UNVERIFIED — a certified safety "
            "engineer must approve RD05 before the report can be generated"
        )

    if reasons:
        raise ReportPreconditionError(reasons)


# -- Data structures ----------------------------------------------------------

@dataclass
class ReportResult:
    pdf_path: Optional[Path] = None
    md_path: Optional[Path] = None
    warnings: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.pdf_path is not None or self.md_path is not None

    @property
    def output_path(self) -> Optional[Path]:
        return self.pdf_path or self.md_path


# -- Data collection ----------------------------------------------------------

def _load_state(project_path: Path) -> dict:
    state_file = project_path / "PROJECT_STATE.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _parse_io_table(project_path: Path) -> list[list[str]]:
    """Return IO table rows from RD01: [header_row, *data_rows]"""
    rd01 = project_path / "metadata" / "RD01_IO_List.md"
    if not rd01.exists():
        return []

    text = rd01.read_text(encoding="utf-8", errors="ignore")
    rows: list[list[str]] = []
    in_table = False

    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            if re.match(r"^\|[-:\s|]+\|$", s):
                continue
            cells = [c.strip() for c in s.split("|")[1:-1]]
            if cells:
                rows.append(cells)
                in_table = True
        elif in_table and not s:
            break

    return rows


def _list_scl_blocks(project_path: Path) -> list[dict]:
    """List the SCL files under _output/scl/."""
    scl_dir = project_path / "_output" / "scl"
    if not scl_dir.exists():
        return []

    blocks = []
    for f in sorted(scl_dir.glob("*.scl")):
        size_kb = f.stat().st_size / 1024
        block_type = ""
        try:
            head = f.read_text(encoding="utf-8", errors="ignore")[:500]
            m = re.search(r"\b(FUNCTION_BLOCK|FUNCTION|ORGANIZATION_BLOCK)\b", head)
            if m:
                block_type = m.group(1)
        except Exception:
            pass
        blocks.append({"name": f.stem, "type": block_type or "SCL", "size_kb": size_kb})
    return blocks


def _pipeline_stats(state: dict) -> tuple[int, int]:
    steps = state.get("pipeline_steps", {})
    if not steps:
        return 0, 0
    done = sum(1 for s in steps.values() if s.get("status") == "done")
    return done, len(steps)


def _find_test_protocol(project_path: Path) -> Optional[Path]:
    out = project_path / "_output"
    for pattern in ("FAT_*.md", "SAT_*.md", "TEST_*.md"):
        found = sorted(out.glob(pattern))
        if found:
            return found[-1]
    return None


# -- PDF Generator ------------------------------------------------------------
# Style construction and table styling moved verbatim to pdf_common (Faz 1.4);
# the aliases keep this module's call sites and output unchanged.

if HAS_REPORTLAB:
    from pdf_common import (
        build_styles as _build_styles,
        hr as _hr,
        section as _section,
        table as _table,
    )


def _generate_pdf(project_path: Path, state: dict, dest: Path) -> list[str]:
    styles  = _build_styles()
    page_w, _ = A4
    fw = page_w - 4.0 * cm  # usable width

    doc = SimpleDocTemplate(
        str(dest), pagesize=A4,
        rightMargin=2.0 * cm, leftMargin=2.0 * cm,
        topMargin=2.0 * cm,   bottomMargin=2.0 * cm,
        title=f"Delivery Report — {project_path.name}",
        author="AUTOMATION FACTORY",
    )

    ts_display = datetime.now().strftime("%d.%m.%Y")
    proj_name  = state.get("project_name", project_path.name)
    customer   = state.get("customer", "—")
    platform   = state.get("target_platform", "—")
    cpu        = state.get("target_cpu", "—")
    tia_ver    = state.get("target_tia_version", "—")
    done, total = _pipeline_stats(state)
    # C-2 fix: derive badge from gate_history, not from the mutable status field.
    status_txt  = _determine_status_badge(state)
    s_color     = _GREEN if status_txt == "COMPLETED" else _ORANGE

    story = []
    sections: list[str] = []

    # -- COVER ----------------------------------------------------------------
    story += [
        Spacer(1, 2.5 * cm),
        Paragraph("AUTOMATION FACTORY", styles["small"]),
        Paragraph("Customer Delivery Report", styles["cover_title"]),
        Spacer(1, 0.6 * cm),
        Paragraph(proj_name, styles["cover_sub"]),
        Spacer(1, 1.0 * cm),
        Paragraph(f"Customer / Company: {customer}", styles["cover_info"]),
        Paragraph(f"Platform: {platform} — {cpu}", styles["cover_info"]),
        Paragraph(f"TIA Portal: {tia_ver}", styles["cover_info"]),
        Paragraph(f"Date: {ts_display}", styles["cover_info"]),
        Spacer(1, 1.5 * cm),
    ]
    badge = Table([[status_txt]], colWidths=[5 * cm])
    badge.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), s_color),
        ("TEXTCOLOR",     (0, 0), (-1, -1), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 11),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [badge, PageBreak()]
    sections.append("Cover")

    # -- PROJECT SUMMARY ------------------------------------------------------
    story += _section(styles, "1. Project Summary")
    meta = [
        ["Field", "Value"],
        ["Project Name", proj_name],
        ["Customer", customer],
        ["Platform", platform],
        ["CPU Model", cpu],
        ["TIA Portal", tia_ver],
        ["Status", status_txt],
        ["Pipeline Progress", f"{done} / {total} steps completed"],
        ["Report Date", ts_display],
    ]
    story.append(_table(meta, [5 * cm, fw - 5 * cm]))
    sections.append("Project Summary")

    # -- IO LIST --------------------------------------------------------------
    story += _section(styles, "2. IO List")
    io_rows = _parse_io_table(project_path)
    MAX_IO = 60
    if io_rows:
        display = io_rows[: MAX_IO + 1]
        n = len(display[0])
        story.append(_table(display, [fw / n] * n))
        if len(io_rows) > MAX_IO + 1:
            story.append(Paragraph(
                f"* {len(io_rows)-1} IO total. First {MAX_IO} rows shown. "
                "Full list: metadata/RD01_IO_List.md",
                styles["small"],
            ))
        sections.append("IO List")
    else:
        story.append(Paragraph("RD01_IO_List.md not found or empty.", styles["body"]))

    # -- SCL BLOCK LIST -------------------------------------------------------
    story += _section(styles, "3. SCL Block List")
    scl = _list_scl_blocks(project_path)
    if scl:
        blk_data = [["Block Name", "Type", "Size"]]
        blk_data += [[b["name"], b["type"], f"{b['size_kb']:.1f} KB"] for b in scl]
        story.append(_table(blk_data, [fw * 0.55, fw * 0.25, fw * 0.20]))
        story.append(Paragraph(f"Total: {len(scl)} blocks", styles["small"]))
        sections.append("SCL Block List")
    else:
        story.append(Paragraph("No SCL files found in the _output/scl/ folder.", styles["body"]))

    # -- TEST STATUS ----------------------------------------------------------
    story += _section(styles, "4. Test Status")
    proto = _find_test_protocol(project_path)
    if proto:
        story.append(Paragraph(f"Protocol present: <b>{proto.name}</b>", styles["body"]))
        try:
            snippet = "\n".join(
                proto.read_text(encoding="utf-8", errors="ignore").splitlines()[:18]
            )
            safe = snippet.replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>")
            story.append(Paragraph(safe, styles["small"]))
        except Exception:
            pass
        sections.append("Test Status")
    else:
        story.append(Paragraph(
            "FAT/SAT protocol not generated yet. "
            "Use the 'Generate FAT Protocol' button on the Delivery Package screen.",
            styles["body"],
        ))

    # -- SISTEMA CALCULATION (Faz 2.4) -----------------------------------------
    # Records table when present, loud PENDING list otherwise — the SISTEMA
    # status is always explicit in delivery documents, never a silent gap.
    story += _section(styles, "5. SISTEMA Calculation (Performance Level Evidence)")
    try:
        from sistema_support import sistema_status
        _sist = sistema_status(project_path)
        if _sist["records"]:
            rec_data = [["Safety Function", "Achieved PL", "SISTEMA File", "Date", "Engineer"]]
            for r in _sist["records"]:
                rec_data.append([
                    r.get("function", ""), r.get("achieved_pl") or "—",
                    r.get("file") or "—", r.get("date", ""), r.get("engineer", ""),
                ])
            story.append(_table(
                rec_data, [fw * 0.28, fw * 0.12, fw * 0.25, fw * 0.13, fw * 0.22]))
            story.append(Paragraph(
                "Entries are engineer declarations (date + name); the SISTEMA "
                "file stays with the project.", styles["small"]))
        if _sist["pending"]:
            story.append(Paragraph(
                "<b>SISTEMA verification: PENDING — to be completed before "
                "delivery.</b> No SISTEMA evidence (achieved PL) yet for:",
                styles["body"]))
            for name in _sist["pending"]:
                story.append(Paragraph(f"[ ]  {name}", styles["check"]))
        elif not _sist["records"]:
            story.append(Paragraph(
                "Note: RD05 contains no PLr information — the SISTEMA evidence "
                "status cannot be derived. Add PLr to RD05.", styles["body"]))
    except Exception as _exc:
        story.append(Paragraph(
            f"SISTEMA status could not be derived: {_exc}", styles["body"]))
    sections.append("SISTEMA Calculation")

    # -- DELIVERY CHECKLIST ---------------------------------------------------
    story += _section(styles, "6. Delivery Checklist")
    for item in [
        "[ ]  SCL code imported into TIA Portal and compiles without errors",
        "[ ]  IO addresses matched against physical wiring",
        "[ ]  Safety functions verified by a certified engineer",
        "[ ]  SISTEMA evidence complete for all PLr safety functions",
        "[ ]  FAT (Factory Acceptance Test) completed and signed",
        "[ ]  SAT (Site Acceptance Test) completed and signed",
        "[ ]  Customer training completed",
        "[ ]  All documents delivered to the customer",
        "[ ]  Backup parameter files saved",
    ]:
        story.append(Paragraph(item, styles["check"]))
    sections.append("Delivery Checklist")

    # -- SIGNATURE PAGE -------------------------------------------------------
    story += [PageBreak()] + _section(styles, "7. Approval and Signatures")
    sig_data = [
        ["Role", "Full Name", "Date", "Signature"],
        ["Project Eng.", "", "", ""],
        ["Customer Rep.", "", "", ""],
        ["Quality Mgr.", "", "", ""],
    ]
    cw = [fw * 0.25, fw * 0.30, fw * 0.20, fw * 0.25]
    sig = Table(sig_data, colWidths=cw, rowHeights=[None, 1.5 * cm, 1.5 * cm, 1.5 * cm])
    sig.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  _NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("GRID",          (0, 0), (-1, -1), 0.5, _GRAY),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [sig, Spacer(1, 0.5 * cm)]
    story.append(Paragraph(
        f"*This report was generated automatically by AUTOMATION FACTORY v3.0 "
        f"on {ts_display}.*",
        styles["small"],
    ))
    sections.append("Signature Page")

    doc.build(story)
    return sections


# -- Markdown Fallback --------------------------------------------------------

def _generate_md(project_path: Path, state: dict, dest: Path) -> list[str]:
    ts = datetime.now().strftime("%d.%m.%Y %H:%M")
    proj_name = state.get("project_name", project_path.name)
    customer  = state.get("customer", "—")
    platform  = state.get("target_platform", "—")
    cpu       = state.get("target_cpu", "—")
    tia_ver   = state.get("target_tia_version", "—")
    done, total = _pipeline_stats(state)

    lines = [
        f"# Delivery Report — {proj_name}",
        f"> {ts} | AUTOMATION FACTORY",
        "",
        "## 1. Project Summary",
        "| Field | Value |",
        "|-------|-------|",
        f"| Project Name | {proj_name} |",
        f"| Customer | {customer} |",
        f"| Platform | {platform} — {cpu} |",
        f"| TIA Portal | {tia_ver} |",
        f"| Pipeline | {done}/{total} steps |",
        f"| Date | {ts} |",
        "",
        "## 2. IO List",
        "",
    ]
    io_rows = _parse_io_table(project_path)
    if io_rows:
        for i, row in enumerate(io_rows[:61]):
            lines.append("| " + " | ".join(row) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * len(row)) + " |")
    else:
        lines.append("*RD01_IO_List.md not found.*")

    lines += ["", "## 3. SCL Block List", ""]
    scl = _list_scl_blocks(project_path)
    if scl:
        lines += ["| Block | Type | Size |", "|-------|------|------|"]
        lines += [f"| {b['name']} | {b['type']} | {b['size_kb']:.1f} KB |" for b in scl]
    else:
        lines.append("*No SCL files found.*")

    # Faz 2.4: SISTEMA status is explicit in the MD fallback too.
    lines += [""]
    try:
        from sistema_support import render_sistema_section_md
        lines.append(render_sistema_section_md(project_path, lang="en"))
    except Exception as _exc:
        lines.append(f"*SISTEMA status could not be derived: {_exc}*")

    lines += [
        "",
        "## 5. Delivery Checklist",
        "",
        "- [ ] SCL code imported into TIA Portal",
        "- [ ] IO addresses verified",
        "- [ ] SISTEMA evidence complete for all PLr safety functions",
        "- [ ] FAT completed",
        "- [ ] SAT completed",
        "- [ ] Documents delivered",
        "",
        "---",
        f"*AUTOMATION_FACTORY customer_report.py — {ts}*",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    return ["Project Summary", "IO List", "SCL Block List",
            "SISTEMA Calculation", "Delivery Checklist"]


# -- Main function ------------------------------------------------------------

def run_report(
    project_path: Path,
    output_dir: Optional[Path] = None,
    *,
    skip_preconditions: bool = False,
) -> ReportResult:
    """Generate the customer delivery report.

    Parameters
    ----------
    project_path:
        Root of the project folder.
    output_dir:
        Where to write the output file.  Defaults to ``<project>/_output/``.
    skip_preconditions:
        TEST-ONLY flag — bypasses the gate/safety checks.  Do NOT pass True
        in production code; it exists solely for unit tests that verify the
        report layout with a minimal project fixture.
    """
    result = ReportResult()

    if not project_path.exists():
        result.warnings.append(f"Project folder not found: {project_path}")
        return result

    state = _load_state(project_path)

    # C-2 fix: gate and safety precondition check — fail-closed.
    # ReportPreconditionError propagates to the caller; no report is written.
    if not skip_preconditions:
        _check_report_preconditions(project_path, state)

    ts    = datetime.now().strftime("%Y%m%d_%H%M")
    safe  = re.sub(r"[^\w\-]", "_", project_path.name)

    out_dir = output_dir or (project_path / "_output")
    out_dir.mkdir(parents=True, exist_ok=True)

    if HAS_REPORTLAB:
        pdf_dest = out_dir / f"CUSTOMER_REPORT_{safe}_{ts}.pdf"
        try:
            secs = _generate_pdf(project_path, state, pdf_dest)
            result.pdf_path = pdf_dest
            result.sections = secs
        except Exception as exc:
            result.warnings.append(f"PDF generation error: {exc}")
            md_dest = out_dir / f"CUSTOMER_REPORT_{safe}_{ts}.md"
            result.sections = _generate_md(project_path, state, md_dest)
            result.md_path  = md_dest
            result.warnings.append("Markdown report produced due to the PDF error.")
    else:
        result.warnings.append("reportlab not installed — producing a Markdown report (pip install reportlab).")
        md_dest = out_dir / f"CUSTOMER_REPORT_{safe}_{ts}.md"
        result.sections = _generate_md(project_path, state, md_dest)
        result.md_path  = md_dest

    return result


def format_report_summary(result: ReportResult) -> str:
    lines = ["Customer Report Summary", ""]
    if result.pdf_path:
        lines += [f"  Format       : PDF", f"  File         : {result.pdf_path.name}"]
    elif result.md_path:
        lines += [f"  Format       : Markdown (fallback)", f"  File         : {result.md_path.name}"]
    if result.sections:
        lines.append(f"  Sections     : {', '.join(result.sections)}")
    if result.warnings:
        lines.append("")
        for w in result.warnings:
            lines.append(f"  {w}")
    return "\n".join(lines)


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="Customer Delivery Report PDF Generator")
    p.add_argument("--project", metavar="PROJECT_PATH", required=True)
    p.add_argument("--out", metavar="FOLDER", help="Output folder (default: _output/)")
    args = p.parse_args()

    result = run_report(
        Path(args.project),
        output_dir=Path(args.out) if args.out else None,
    )
    print(format_report_summary(result))
    if result.output_path:
        print(f"\nReport: {result.output_path}")


if __name__ == "__main__":
    main()
