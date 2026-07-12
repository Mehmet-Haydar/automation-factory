#!/usr/bin/env python3
"""decision_cascade.py — structured decision vocabulary + old⇄target delta.

The dossier decision table is engineer-owned FREE TEXT (that stays — a
retrofit decision is an engineering sentence, not a dropdown). This module
derives the STRUCTURED reading of each decision:

  verb      KEEP / REPLACE / DROP / UNCLASSIFIED (deterministic keyword
            parse over DE/EN/TR vocabulary; DROP > REPLACE > KEEP priority
            so "bleibt nicht — ersatzlos entfällt" reads as DROP)
  cascade   which downstream artifacts the decision touches (HMI tags &
            alarms referencing the operand, the library-FB binding of the
            device, the RD01 row) and whether the propagation already
            HAPPENED — proven against the same sources the Gate-3
            reconciliation reads, so the two screens can never disagree.

Read-only by design: the engine never edits an artifact (the FB library is
untouchable, RDs carry approval state). It reports; the engineer or the
affected generator acts. Its byproduct is the dossier's Old⇄Target page
(05_old_target_delta.md) — the customer-facing answer to "what happens to
this device in the retrofit?".
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from gate3_consistency import (  # type: ignore
    _DRIVE_RE, _SAFETY_RE, _canon, _hmi_rows, _row_operands,
)

DELTA_FILE = "05_old_target_delta.md"

# Decision vocabulary (DE/EN/TR). Word-level, case-insensitive.
_DROP_RE = re.compile(
    r"\bDROP\b|\bENTF(?:AE|Ä)LLT\b|\bERSATZLOS\b|\bWEGFALL\b|\bREMOVE\b|"
    r"\bDELETE\b|\bENTFERNEN\b|\bKALDIR|\bIPTAL\b|\bİPTAL\b", re.IGNORECASE)
_REPLACE_RE = re.compile(
    r"\bREPLACE\b|\bERSATZ\b|\bERSETZ\w*|\bTAUSCH\w*|\bNEU\b|\bSTATT\b|"
    r"\bMIGRATE\b|\bUPGRADE\b|\bYER(?:I|İ)NE\b|→|->|=>", re.IGNORECASE)
_KEEP_RE = re.compile(
    r"\bKEEP\b|\bBLEIBT\b|\bUNVER(?:AE|Ä)NDERT\b|\b1\s*:\s*1\b|"
    r"\bWIE BISHER\b|\bKALIR\b|\bKALACAK\b|\bRETAIN\b|\bBEHALTEN\b",
    re.IGNORECASE)

VERBS = ("KEEP", "REPLACE", "DROP", "UNCLASSIFIED")


def parse_verb(text: str) -> str:
    """Deterministic verb of a free-text decision. Priority DROP > REPLACE >
    KEEP: a sentence that both denies keeping and names removal is a DROP;
    "ersetzt" beats a courtesy "bleibt" fragment. Empty/unmatched text is
    honestly UNCLASSIFIED — never guessed."""
    t = (text or "").strip()
    if not t:
        return "UNCLASSIFIED"
    if _DROP_RE.search(t):
        return "DROP"
    if _REPLACE_RE.search(t):
        return "REPLACE"
    if _KEEP_RE.search(t):
        return "KEEP"
    return "UNCLASSIFIED"


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

def _signals_by_addr(root: Path) -> dict[str, dict]:
    try:
        from iec_tag_generator import parse_rd01_signals  # type: ignore
        return {s.get("address", ""): s for s in parse_rd01_signals(Path(root))
                if s.get("address")}
    except Exception:
        return {}


def _fb_bindings(root: Path) -> dict[str, str]:
    """{EQUIPMENT: FB name} from the assembly manifest (if any)."""
    try:
        from traceability_matrix import _fb_by_device  # type: ignore
        return _fb_by_device(Path(root))
    except Exception:
        return {}


def _hmi_refs_by_row(root: Path) -> list[tuple[str, str, set]]:
    """[(kind, row key, canonical operands)] for every RD11/RD08 row."""
    rd11, rd08, _e11, _e08 = _hmi_rows(Path(root))
    out: list[tuple[str, str, set]] = []
    for row in rd11:
        out.append(("RD11", row.get("HMI_TagID", "?"), _row_operands(row)))
    for row in rd08:
        out.append(("RD08", row.get("AlarmID", "?"), _row_operands(row)))
    return out


# ---------------------------------------------------------------------------
# the cascade
# ---------------------------------------------------------------------------

def compute_cascade(project_root: Path) -> dict:
    """Old⇄target delta for every decided device.

    Returns {"devices": [...], "summary": {...}}. Device entry:
      addr, name, equipment, function, old (current solution), verb,
      target (decision text), impact, safety (bool),
      affected: [{artifact, key, action, status}]  status: pending|propagated|review
      pending: bool  (any affected item still waiting)
    """
    root = Path(project_root)
    try:
        from machine_dossier import load_decisions  # type: ignore
        decisions = load_decisions(root)
    except Exception:
        decisions = {}
    signals = _signals_by_addr(root)
    fbs = _fb_bindings(root)
    hmi = _hmi_refs_by_row(root)

    devices: list[dict] = []
    summary = {v: 0 for v in VERBS}
    summary["pending"] = 0

    for addr, d in sorted(decisions.items()):
        decision = str(d.get("decision", "")).strip()
        impact = str(d.get("impact", "")).strip()
        verb = parse_verb(f"{decision} {impact}")
        sig = signals.get(addr, {})
        c = _canon(addr)
        refs = [(kind, key) for kind, key, ops in hmi if c and c in ops]
        equip = (sig.get("equipment") or "").strip()
        fb = fbs.get(equip.upper(), "") if equip else ""
        safety = bool(_SAFETY_RE.search(
            f"{sig.get('name', '')} {sig.get('desc', '')}"))

        affected: list[dict] = []
        if verb == "DROP":
            for kind, key in refs:
                affected.append({
                    "artifact": kind, "key": key,
                    "action": "remove tag/alarm (device is dropped)",
                    "status": "pending"})
            if not refs:
                affected.append({
                    "artifact": "HMI", "key": "—",
                    "action": "no HMI reference remains",
                    "status": "propagated"})
            if fb:
                affected.append({
                    "artifact": "FB", "key": fb,
                    "action": f"unbind {equip} from {fb} at the next assembly",
                    "status": "pending"})
        elif verb == "REPLACE":
            drive = bool(_DRIVE_RE.search(f"{decision} {impact}"))
            for kind, key in refs:
                affected.append({
                    "artifact": kind, "key": key,
                    "action": ("review label/setpoints/alarm vocabulary "
                               "(device class changes)" if drive
                               else "review tag against the new device"),
                    "status": "review"})
            if fb:
                affected.append({
                    "artifact": "FB", "key": fb,
                    "action": f"re-select library FB for {equip or addr} "
                              "(bound to the OLD device class)",
                    "status": "pending" if drive else "review"})
        # KEEP / UNCLASSIFIED cascade nothing; UNCLASSIFIED is itself the
        # engineer's worklist (the verb could not be derived).

        pending = any(a["status"] == "pending" for a in affected)
        summary[verb] += 1
        if pending:
            summary["pending"] += 1
        devices.append({
            "addr": addr,
            "name": sig.get("name", ""),
            "equipment": equip,
            "function": sig.get("desc", ""),
            "old": sig.get("srcmodule", "") or "",
            "verb": verb,
            "target": decision,
            "impact": impact,
            "safety": safety,
            "affected": affected,
            "pending": pending,
        })

    return {"devices": devices, "summary": summary}


# ---------------------------------------------------------------------------
# dossier page (byproduct)
# ---------------------------------------------------------------------------

def render_delta_md(cascade: dict, project_id: str = "") -> str:
    devices = cascade.get("devices", [])
    s = cascade.get("summary", {})
    lines = [
        f"# OLD ⇄ TARGET — device delta{(' — ' + project_id) if project_id else ''}",
        "",
        "> DRAFT_UNVERIFIED — derived from the ENGINEER's decision table "
        "(04_decision_table): the structured reading of each free-text "
        "decision. Generated; the decisions themselves live in "
        "decisions.json and are never touched.",
        "",
        f"Decisions: {len(devices)} · KEEP {s.get('KEEP', 0)} · "
        f"REPLACE {s.get('REPLACE', 0)} · DROP {s.get('DROP', 0)} · "
        f"unclassified {s.get('UNCLASSIFIED', 0)} · "
        f"pending propagation {s.get('pending', 0)}",
        "",
        "| Address | Device (old) | Function | Verb | Target (decision) | "
        "Impact | Cascade |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in devices:
        casc = "; ".join(
            f"{a['artifact']} {a['key']}: {a['action']} [{a['status']}]"
            for a in d.get("affected", [])) or "—"
        flag = " ⚠️SAFETY" if d.get("safety") else ""
        lines.append(
            f"| {d['addr']}{flag} | {d.get('name', '') or '—'} | "
            f"{(d.get('function', '') or '—')[:60]} | {d['verb']} | "
            f"{(d.get('target', '') or '—')} | {(d.get('impact', '') or '—')} | "
            f"{casc} |".replace("\n", " "))
    lines += [
        "",
        "> Verb is derived (DROP > REPLACE > KEEP keyword priority, DE/EN/TR); "
        "UNCLASSIFIED rows need a clearer decision sentence. [pending] items "
        "are also enforced by the Gate-3 reconciliation — they cannot be "
        "locked away silently.",
        "",
    ]
    return "\n".join(lines)


def write_delta_file(project_root: Path, project_id: str = "") -> Path | None:
    """(Re)generate the dossier's Old⇄Target page. Fail-quiet: a delta-page
    failure must never break a decisions save."""
    root = Path(project_root)
    try:
        cascade = compute_cascade(root)
        out = root / "metadata" / "machine_dossier"
        out.mkdir(parents=True, exist_ok=True)
        fp = out / DELTA_FILE
        fp.write_text(render_delta_md(cascade, project_id or root.name),
                      encoding="utf-8")
        return fp
    except Exception:
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: decision_cascade.py <project_root>")
        raise SystemExit(2)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    c = compute_cascade(Path(sys.argv[1]))
    print(json.dumps(c, ensure_ascii=False, indent=2))
    p = write_delta_file(Path(sys.argv[1]))
    print(f"delta page: {p}")
