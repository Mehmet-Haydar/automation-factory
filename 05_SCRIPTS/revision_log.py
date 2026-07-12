#!/usr/bin/env python3
"""revision_log.py — baseline snapshots + the delivery REVISION_LOG (dilim ⑥).

DACH delivery culture: the customer receives not just the final documents
but the story — what the machine analysis FIRST said, what the engineer
changed, and WHY. The factory already records every "why" in its decision
files; this module joins them into one auditable page.

  baseline   metadata/_baseline/ — the FIRST version of every RD file,
             captured when a generator writes it (write_rd_draft /
             hmi_draft hooks). First-seen wins; a baseline file is NEVER
             overwritten — that is the whole point.
  log        REPORTS/REVISION_LOG.md — per-RD baseline⇄current state
             (SHA-256 proof) + every recorded engineer decision with its
             reason and name: HMI grid edits (hmi_decisions.json), dossier
             device decisions (decisions.json, with the derived verb),
             Gate-3 conscious deviations (gate3_waivers.json) and wiring
             approvals (hmi_wiring.json). Ships in the handover ZIP.

Deterministic, read-only over the project (except its own two outputs).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASELINE_DIR = "_baseline"
LOG_FILE = "REVISION_LOG.md"


def _sha(fp: Path) -> str:
    try:
        return hashlib.sha256(fp.read_bytes()).hexdigest()
    except Exception:
        return ""


# Pristine template markers (same vocabulary as hmi_draft._may_overwrite).
# B5 (E2E finding 2026-07-07): the snapshot hook fires after EVERY draft
# write and used to capture the sibling RDs too — which at that moment were
# still empty templates. The revision log then reported 13 RDs as
# "MODIFIED" although nobody had touched them. A template is NOT a
# baseline; each RD's baseline is its first REAL content.
_TEMPLATE_MARKERS = ("<PROJECT_CODE>", "filled_by: <Engineer Name>")


def snapshot_baseline(project_root: Path) -> list[str]:
    """Copy every metadata/RD*.md that has real content and no baseline yet.
    First-seen wins; existing baselines are never touched; pristine
    templates are skipped (their first draft becomes the baseline later).
    Fail-quiet per file — a snapshot problem must never block a generator."""
    root = Path(project_root)
    md = root / "metadata"
    if not md.is_dir():
        return []
    base = md / BASELINE_DIR
    captured: list[str] = []
    for fp in sorted(md.glob("RD*.md")):
        target = base / fp.name
        if target.exists():
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
            if any(m in text for m in _TEMPLATE_MARKERS):
                continue    # still a template — not a baseline
            base.mkdir(exist_ok=True)
            target.write_text(text, encoding="utf-8")
            captured.append(fp.name)
        except Exception:
            continue
    return captured


def _load_json(fp: Path) -> dict:
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def generate_revision_log(project_root: Path) -> Path | None:
    """REPORTS/REVISION_LOG.md — baseline⇄current per RD + every recorded
    decision with reason and name. Returns the path (None on failure)."""
    root = Path(project_root)
    md = root / "metadata"
    base = md / BASELINE_DIR
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    L = [
        f"# REVISION LOG — {root.name}",
        "",
        f"Generated: {now}",
        "",
        "> Delivery record: the FIRST generated version of each document "
        "(baseline, SHA-256 proven) vs the delivered version, plus every "
        "engineer decision on file with its reason and name. Generated — "
        "the decisions live in their own files and are never touched.",
        "",
        "## Document revisions (baseline ⇄ delivered)",
        "",
        "| Document | Baseline | State |",
        "|---|---|---|",
    ]
    rd_files = sorted(md.glob("RD*.md")) if md.is_dir() else []
    for fp in rd_files:
        b = base / fp.name
        if not b.exists():
            L.append(f"| {fp.name} | — | no baseline captured "
                     "(pre-dates the baseline feature) |")
            continue
        same = _sha(b) == _sha(fp)
        state = ("unchanged since first generation" if same
                 else "**MODIFIED** after first generation "
                      "(see decisions below)")
        L.append(f"| {fp.name} | `{_sha(b)[:12]}…` | {state} |")
    if not rd_files:
        L.append("| — | — | no RD documents yet |")

    # --- HMI grid edits ----------------------------------------------------
    hmi = _load_json(md / "hmi_decisions.json")
    L += ["", "## HMI worksheet edits (RD11/RD08 grids)", ""]
    if hmi:
        L += ["| Sheet | Row | Edited fields |", "|---|---|---|"]
        for kind, bucket in sorted(hmi.items()):
            for key, changes in sorted((bucket or {}).items()):
                fields = ", ".join(f"{c} = {v}" for c, v in
                                   sorted((changes or {}).items()))
                L.append(f"| {kind.upper()} | {key} | {fields} |")
    else:
        L.append("_none recorded_")

    # --- dossier device decisions -------------------------------------------
    dec = _load_json(md / "machine_dossier" / "decisions.json")
    L += ["", "## Device decisions (dossier decision table)", ""]
    if dec:
        try:
            from decision_cascade import parse_verb  # type: ignore
        except Exception:
            def parse_verb(_t):  # type: ignore
                return "?"
        L += ["| Address | Verb | Decision | Code impact |", "|---|---|---|---|"]
        for addr, d in sorted(dec.items()):
            decision = str(d.get("decision", "")).strip()
            impact = str(d.get("impact", "")).strip()
            L.append(f"| {addr} | {parse_verb(decision + ' ' + impact)} | "
                     f"{decision or '—'} | {impact or '—'} |")
    else:
        L.append("_none recorded_")

    # --- Gate-3 conscious deviations -----------------------------------------
    try:
        from gate3_consistency import load_waivers  # type: ignore
        waivers = load_waivers(root)
    except Exception:
        waivers = {}
    L += ["", "## Conscious deviations (Gate-3 waivers)", ""]
    if waivers:
        L += ["| Finding | Reason | By | Date |", "|---|---|---|---|"]
        for _fid, w in sorted(waivers.items(),
                              key=lambda kv: kv[1].get("at", "")):
            L.append(f"| {w.get('title', '—')} | {w.get('reason', '—')} | "
                     f"{w.get('by', '—')} | {w.get('at', '—')} |")
    else:
        L.append("_none — the reconciliation closed clean_")

    # --- wiring approvals -----------------------------------------------------
    try:
        from hmi_wiring import load_wiring  # type: ignore
        wiring = load_wiring(root)
    except Exception:
        wiring = {}
    L += ["", "## HMI wiring decisions", ""]
    if wiring:
        L += ["| Interface tag | Decision | By | Note | Date |",
              "|---|---|---|---|---|"]
        for tag, w in sorted(wiring.items()):
            L.append(f"| `{tag}` | "
                     f"{'APPROVED' if w.get('approved') else 'rejected'} | "
                     f"{w.get('by', '—') or '—'} | {w.get('note', '') or '—'} | "
                     f"{w.get('at', '—')} |")
    else:
        L.append("_none recorded — wiring proposal not yet decided_")

    L += [""]
    try:
        reports = root / "REPORTS"
        reports.mkdir(exist_ok=True)
        fp = reports / LOG_FILE
        fp.write_text("\n".join(L), encoding="utf-8")
        return fp
    except Exception:
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: revision_log.py <project_root>")
        raise SystemExit(2)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    print("baseline captured:", snapshot_baseline(Path(sys.argv[1])))
    print("log:", generate_revision_log(Path(sys.argv[1])))
