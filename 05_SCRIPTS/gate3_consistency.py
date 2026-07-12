#!/usr/bin/env python3
"""gate3_consistency.py — the Gate-3 "Reconciliation & Preview" validator.

Human Review (Gate 3) is where the engineer signs the whole analysis pack.
This module gives that screen its substance: it cross-checks the artifacts
that were edited in DIFFERENT places (RD01 IO list, RD11/RD08 HMI grids,
the dossier decision table) and reports every DEVIATION as a finding.
Consistent facts are counted, not listed — management by exception.

Finding classes:
  red        NOT-AUS / safety baseline violations (EN ISO 13850: the
             emergency-stop function stays physical). CANNOT be waived —
             not even with a signature. The only exit is "go back & fix".
  deviation  orphan references (HMI tag whose IO row is gone, pulpit
             element without an HMI tag), un-propagated dossier decisions
             (DROP decided but the tag remains), semantic device-class
             changes (Y-Δ starter → VFD). Waivable as a "conscious choice"
             with a mandatory reason + name; the waiver is persisted in
             metadata/gate3_waivers.json, never asked again, and lands in
             the TRACEABILITY matrix.

Fail-honest rules: a check whose source data is absent (no RD01 rows, no
RD11 table, no legacy sources) is reported in `skipped` — it neither
invents findings nor silently claims consistency.

Pure text/JSON layer — no GUI, no AI; fully unit-tested.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from rd01_crosscheck import _canon_rd01_operand  # type: ignore

WAIVERS_FILE = "gate3_waivers.json"

# Emergency-stop vocabulary (DE/EN/TR) — the red-class anchor.
_SAFETY_RE = re.compile(
    r"NOT\s*-?\s*AUS|NOTAUS|E\s*-?\s*STOP|EMERGENCY\s*STOP|ACIL\s*STOP",
    re.IGNORECASE)
# Decision text that moves a function into software/HMI territory.
_TO_HMI_RE = re.compile(r"\bHMI\b|\bPANEL\b|\bSOFTWARE\b|\bTOUCH\b|\bSCADA\b",
                        re.IGNORECASE)
# Decision verbs (KEEP/REPLACE/DROP) live in decision_cascade.parse_verb —
# ONE vocabulary, so this validator and the cascade engine can never
# disagree about what a decision says. Imported lazily in collect_findings.
# Device classes whose arrival CHANGES THE MEANING of the signal set
# (a Y-Δ starter migrating to a VFD re-defines contactor outputs, adds
# speed setpoints, changes the fault vocabulary).
_DRIVE_RE = re.compile(
    r"\bVFD\b|\bFU\b|FREQUENZUMRICHTER|UMRICHTER|\bSERVO\b|SOFT\s*START|"
    r"SANFTANL|\bDRIVE\b|SÜRÜCÜ", re.IGNORECASE)

# Operand pattern for scanning free-text cells (Notes: "legacy I0.0",
# "replaces BCD thumbwheel bits I2.0, I2.1"; TriggerTag: "Q5.1").
_OPERAND_RE = re.compile(r"\b(?:[EAIQ]\s?\d{1,3}\.\d|%[IQ]W?\s?\d{1,4}(?:\.\d)?|"
                         r"[EAIQ][WD]\s?\d{1,4})\b")


def _canon(value: str) -> str | None:
    return _canon_rd01_operand(value or "")


def _canon_all(text: str) -> set[str]:
    """Every canonical operand mentioned in a free-text cell."""
    out: set[str] = set()
    for m in _OPERAND_RE.finditer(text or ""):
        c = _canon(m.group(0))
        if c:
            out.add(c)
    return out


def _finding_id(kind: str, subject: str) -> str:
    """Stable across runs — the waiver key."""
    return hashlib.sha256(f"{kind}|{subject}".encode("utf-8")).hexdigest()[:16]


def _mk(kind: str, severity: str, subject: str, title: str, detail: str,
        fix_target: str) -> dict:
    return {
        "id": _finding_id(kind, subject),
        "kind": kind,
        "severity": severity,           # red | deviation
        "subject": subject,
        "title": title,
        "detail": detail,
        "fix_target": fix_target,       # rd11 | rd08 | rd01 | dossier
        "waivable": severity != "red",
    }


# ---------------------------------------------------------------------------
# source loading
# ---------------------------------------------------------------------------

def _rd01_operands(root: Path) -> set[str]:
    """Canonical operands RD01 carries (Address + OldTag columns)."""
    try:
        from iec_tag_generator import parse_rd01_signals  # type: ignore
        signals = parse_rd01_signals(Path(root))
    except Exception:
        return set()
    ops: set[str] = set()
    for s in signals:
        for cell in (s.get("address", ""), s.get("oldtag", "")):
            c = _canon(cell)
            if c:
                ops.add(c)
    return ops


def _rd01_signal_by_operand(root: Path) -> dict[str, dict]:
    try:
        from iec_tag_generator import parse_rd01_signals  # type: ignore
        signals = parse_rd01_signals(Path(root))
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for s in signals:
        for cell in (s.get("address", ""), s.get("oldtag", "")):
            c = _canon(cell)
            if c:
                out.setdefault(c, s)
    return out


def _hmi_rows(root: Path) -> tuple[list[dict], list[dict], bool, bool]:
    """(rd11_rows, rd08_rows, rd11_exists, rd08_exists) — parsed grids."""
    from hmi_table_edit import KINDS, parse_table  # type: ignore
    meta = Path(root) / "metadata"
    out: dict[str, list[dict]] = {"rd11": [], "rd08": []}
    exists = {"rd11": False, "rd08": False}
    for kind, spec in KINDS.items():
        fp = meta / spec["file"]
        if not fp.is_file():
            continue
        exists[kind] = True
        try:
            _cols, rows, _lnos = parse_table(
                fp.read_text(encoding="utf-8", errors="replace"), spec["key"])
            out[kind] = rows
        except Exception:
            continue
    return out["rd11"], out["rd08"], exists["rd11"], exists["rd08"]


# hmi_draft Notes carry PROOF text after "shows:" / "condition:" — the lamp's
# input equation. Those operands are evidence, not references; scanning them
# would fabricate orphan findings for every input in the equation.
_COND_SPLIT_RE = re.compile(r"shows:|condition:", re.IGNORECASE)


def _row_operands(row: dict) -> set[str]:
    """Legacy operands a RD11/RD08 row references (Notes, TriggerTag)."""
    notes = _COND_SPLIT_RE.split(row.get("Notes", ""))[0]
    ops = _canon_all(notes)
    trig = _canon(row.get("TriggerTag", ""))
    if trig:
        ops.add(trig)
    return ops


def _row_label(row: dict) -> str:
    return (row.get("Label_DE") or row.get("Label_EN") or
            row.get("AlarmText_DE") or row.get("AlarmText_EN") or
            row.get("HMI_TagID") or row.get("AlarmID") or "")


# ---------------------------------------------------------------------------
# the checks
# ---------------------------------------------------------------------------

def collect_findings(project_root: Path) -> dict:
    """Run every consistency check. Returns
    {"findings": [...], "consistent": {check: count}, "skipped": [reason...]}
    — waivers NOT applied here (see apply_waivers)."""
    root = Path(project_root)
    findings: list[dict] = []
    consistent: dict[str, int] = {}
    skipped: list[str] = []

    rd11_rows, rd08_rows, rd11_exists, rd08_exists = _hmi_rows(root)
    rd01_ops = _rd01_operands(root)
    rd01_by_op = _rd01_signal_by_operand(root)

    hmi_refs: set[str] = set()
    for row in rd11_rows + rd08_rows:
        hmi_refs |= _row_operands(row)

    # -- A. orphan HMI reference: tag points at an IO row that is gone ------
    if (rd11_rows or rd08_rows) and rd01_ops:
        ok = 0
        for kind, rows, keycol in (("rd11", rd11_rows, "HMI_TagID"),
                                   ("rd08", rd08_rows, "AlarmID")):
            for row in rows:
                refs = _row_operands(row)
                if not refs:
                    continue
                missing = sorted(refs - rd01_ops)
                if missing:
                    key = row.get(keycol, "?")
                    findings.append(_mk(
                        "orphan_hmi_ref", "deviation", f"{key}:{','.join(missing)}",
                        f"{key} references IO that is not in RD01",
                        f"HMI row '{_row_label(row)}' references legacy operand(s) "
                        f"{', '.join(missing)} — no RD01 row carries them "
                        "(deleted or renamed after the HMI draft).",
                        kind))
                else:
                    ok += 1
        consistent["orphan_hmi_ref"] = ok
    else:
        skipped.append("orphan_hmi_ref: RD01 and/or RD11-RD08 tables not available")

    # -- B. pulpit element without an HMI tag -------------------------------
    legacy_dir = root / "_raw" / "legacy_code"
    if legacy_dir.is_dir() and (rd11_exists or rd08_exists):
        try:
            from hmi_draft import classify_pulpit  # type: ignore
            inv = classify_pulpit(root)
        except Exception:
            inv = None
            skipped.append("pulpit_without_tag: pulpit classification failed")
        if inv is not None:
            expected: list[tuple[str, str]] = (
                [(a, n) for a, n in inv.buttons]
                + [(a, n) for a, n in inv.selectors]
                + [(a, n, ) for a, n, *_ in inv.indicators]
                + [(a, n) for a, n, *_ in inv.alarms]
                + [(m[0][0], stem) for stem, m in inv.numeric_groups])
            ok = 0
            for addr, name in expected:
                c = _canon(addr)
                if c and c in hmi_refs:
                    ok += 1
                else:
                    findings.append(_mk(
                        "pulpit_without_tag", "deviation", addr,
                        f"Pulpit element {addr} has no HMI tag",
                        f"'{name}' ({addr}) classifies as an operator-panel "
                        "element but no RD11/RD08 row references it — "
                        "regenerate the HMI draft or add the tag.",
                        "rd11"))
            consistent["pulpit_without_tag"] = ok
    else:
        skipped.append("pulpit_without_tag: no legacy sources or no HMI tables")

    # -- C/D. dossier decisions: DROP propagation + semantic change ---------
    try:
        from machine_dossier import load_decisions  # type: ignore
        decisions = load_decisions(root)
    except Exception:
        decisions = {}
    if decisions:
        from decision_cascade import parse_verb  # lazy — avoids import cycle
        ok_drop = ok_sem = 0
        for addr, d in sorted(decisions.items()):
            text = f"{d.get('decision', '')} {d.get('impact', '')}"
            c = _canon(addr)
            sig = rd01_by_op.get(c or "", {})
            sig_text = f"{sig.get('name', '')} {sig.get('desc', '')}"
            is_safety = bool(_SAFETY_RE.search(sig_text))
            # C. DROP decided but the HMI tag still stands
            if parse_verb(text) == "DROP":
                if c and c in hmi_refs:
                    findings.append(_mk(
                        "decision_not_propagated",
                        "red" if is_safety else "deviation", addr,
                        f"Decision says DROP for {addr} but its HMI tag remains",
                        f"The dossier decision for {addr} ('{d.get('decision', '')}') "
                        "drops the device, yet RD11/RD08 still reference it. "
                        + ("A safety device may never be dropped this way "
                           "(EN ISO 13850)." if is_safety
                           else "Remove the tag or revise the decision."),
                        "dossier"))
                else:
                    ok_drop += 1
            # D. device-class change (Y-Δ → VFD family)
            if _DRIVE_RE.search(text) and not _DRIVE_RE.search(sig_text):
                findings.append(_mk(
                    "semantic_change", "deviation", addr,
                    f"Device class changes at {addr} (→ drive/VFD family)",
                    f"The decision for {addr} introduces a drive "
                    f"('{d.get('decision', '')}') while the signal itself "
                    f"('{sig.get('name', '') or addr}') is not one — a Y-Δ→VFD "
                    "style meaning change. Verify FB selection, HMI tags, "
                    "setpoints and the alarm vocabulary follow.",
                    "dossier"))
            else:
                ok_sem += 1
            # RED: a safety device being decided into software/HMI
            if is_safety and _TO_HMI_RE.search(text):
                findings.append(_mk(
                    "safety_decision_to_hmi", "red", addr,
                    f"Safety device {addr} decided into HMI/software",
                    f"The dossier decision for {addr} moves an emergency-stop "
                    "class device toward HMI/software — EN ISO 13850 requires "
                    "the E-stop function to stay physical. This cannot be "
                    "waived; revise the decision.",
                    "dossier"))
        consistent["decision_not_propagated"] = ok_drop
        consistent["semantic_change"] = ok_sem
    else:
        skipped.append("decisions: no dossier decisions recorded yet")

    # -- E. NOT-AUS as an HMI tag (red baseline) -----------------------------
    if rd11_rows:
        ok = 0
        for row in rd11_rows:
            label = " ".join((row.get("HMI_TagID", ""), row.get("Label_EN", ""),
                              row.get("Label_TR", ""), row.get("Label_DE", "")))
            if _SAFETY_RE.search(label):
                writable = "W" in (row.get("ReadWrite", "") or "").upper()
                is_button = "BUTTON" in (row.get("ElementType", "") or "").upper()
                key = row.get("HMI_TagID", "?")
                if writable or is_button:
                    findings.append(_mk(
                        "safety_on_hmi", "red", key,
                        f"{key}: emergency-stop function on the HMI",
                        f"'{_row_label(row)}' is an E-stop class element wired "
                        "as a writable/button HMI tag. EN ISO 13850: the "
                        "emergency-stop function must remain a physical device "
                        "— it can never move to a touchscreen. Remove the tag.",
                        "rd11"))
                else:
                    findings.append(_mk(
                        "safety_indication_on_hmi", "deviation", key,
                        f"{key}: E-stop status shown on the HMI",
                        f"'{_row_label(row)}' displays an emergency-stop state. "
                        "Indication is permissible (the function stays "
                        "physical) — confirm this tag is read-only display.",
                        "rd11"))
            else:
                ok += 1
        consistent["safety_on_hmi"] = ok

    return {"findings": findings, "consistent": consistent, "skipped": skipped}


# ---------------------------------------------------------------------------
# waivers — conscious, named, permanent, traceable
# ---------------------------------------------------------------------------

def _waivers_path(project_root: Path) -> Path:
    return Path(project_root) / "metadata" / WAIVERS_FILE


def load_waivers(project_root: Path) -> dict:
    fp = _waivers_path(project_root)
    if not fp.exists():
        return {}
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_waiver(project_root: Path, finding: dict, reason: str,
                name: str) -> tuple[bool, str]:
    """Persist a conscious-choice waiver. Refused for red findings (EN ISO
    13850 baseline — a signature cannot bend it) and for empty reason/name."""
    if finding.get("severity") == "red" or not finding.get("waivable", False):
        return False, ("This finding is in the red class (safety baseline, "
                       "EN ISO 13850) — it cannot be waived. Go back and fix it.")
    reason = (reason or "").strip()
    name = (name or "").strip()
    if len(reason) < 6:
        return False, "A substantive reason is required (at least 6 characters)."
    if len([t for t in name.split() if t]) < 2 or not any(c.isalpha() for c in name):
        return False, ("A name is required (name-surname or name-role, "
                       "e.g. 'H. Becker, Inbetriebnahme').")
    from datetime import datetime as _dt
    waivers = load_waivers(project_root)
    waivers[finding["id"]] = {
        "kind": finding.get("kind", ""),
        "subject": finding.get("subject", ""),
        "title": finding.get("title", ""),
        "reason": reason,
        "by": name,
        "at": _dt.now().strftime("%Y-%m-%d"),
    }
    fp = _waivers_path(project_root)
    fp.parent.mkdir(exist_ok=True)
    fp.write_text(json.dumps(waivers, ensure_ascii=False, indent=2),
                  encoding="utf-8")
    return True, ""


def apply_waivers(project_root: Path, result: dict) -> dict:
    """Mark waived findings; red findings NEVER count as waived even if a
    stale waiver record exists for their id (fail-safe)."""
    waivers = load_waivers(project_root)
    for f in result.get("findings", []):
        w = waivers.get(f["id"])
        f["waived"] = bool(w) and f.get("severity") != "red"
        if f["waived"]:
            f["waiver"] = w
    return result


def unresolved(result: dict) -> list[dict]:
    """Findings still blocking the Gate-3 lock (red, or not yet waived)."""
    return [f for f in result.get("findings", [])
            if not f.get("waived", False)]


def run(project_root: Path) -> dict:
    """collect + waivers + lock verdict, in one call."""
    result = apply_waivers(project_root, collect_findings(project_root))
    un = unresolved(result)
    result["unresolved"] = len(un)
    result["red"] = sum(1 for f in un if f.get("severity") == "red")
    result["lock_ready"] = not un
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: gate3_consistency.py <project_root>")
        raise SystemExit(2)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    r = run(Path(sys.argv[1]))
    print(json.dumps(r, ensure_ascii=False, indent=2))
