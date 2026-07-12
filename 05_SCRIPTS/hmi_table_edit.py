#!/usr/bin/env python3
"""hmi_table_edit.py — grid-editor backbone for the RD11/RD08 worksheets.

Same discipline as the dossier decision grid: deterministic columns are
LOCKED (source: symbol file + proven equations), engineer columns are
editable, and every edit is persisted to metadata/hmi_decisions.json so a
dossier/HMI-draft regeneration can NEVER erase engineer work (the draft
generator re-applies the decisions after rendering).

Pure text/JSON layer — no GUI, no .NET; fully unit-tested.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RD11_KEY = "HMI_TagID"
RD11_EDITABLE = ("Label_EN", "Label_TR", "MinValue", "MaxValue", "ScreenRef")
RD08_KEY = "AlarmID"
RD08_EDITABLE = ("Class", "Priority", "AlarmText_EN", "AlarmText_TR",
                 "AcknRequired", "RecommendedAction")
_RD08_CLASS_ENUM = {"Critical", "Warning", "Info"}

KINDS = {
    "rd11": {"file": "RD11_HMI.md", "key": RD11_KEY,
             "editable": RD11_EDITABLE},
    "rd08": {"file": "RD08_Alarm.md", "key": RD08_KEY,
             "editable": RD08_EDITABLE},
}

_ROW_RE = re.compile(r"^\|(.+)\|\s*$")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_table(md_text: str, key_col: str):
    """(columns, rows, line_numbers) of the pipe table keyed by key_col.
    line_numbers[i] is the 0-based line index of rows[i] in md_text."""
    lines = md_text.splitlines()
    cols: list[str] = []
    rows: list[dict] = []
    lnos: list[int] = []
    in_table = seen_sep = False
    for i, line in enumerate(lines):
        if not _ROW_RE.match(line.strip()):
            in_table = seen_sep = False
            continue
        if not in_table:
            hdr = _cells(line)
            if key_col in hdr:
                cols, in_table, seen_sep = hdr, True, False
            continue
        if not seen_sep:
            seen_sep = True
            continue
        vals = _cells(line)
        if len(vals) < len(cols):
            vals += [""] * (len(cols) - len(vals))
        row = dict(zip(cols, vals[:len(cols)]))
        if row.get(key_col):
            rows.append(row)
            lnos.append(i)
    return cols, rows, lnos


def _validate(kind: str, col: str, value: str, row: dict) -> str:
    """'' if OK, else a human-readable refusal."""
    if kind == "rd08":
        if col == "Class" and value and value not in _RD08_CLASS_ENUM:
            return f"Class must be one of {sorted(_RD08_CLASS_ENUM)}"
        if col == "AcknRequired":
            cls = row.get("Class", "")
            if cls == "Critical" and value.upper() != "Y":
                return "Critical alarms require AcknRequired=Y (ISA-18.2 rule)"
            if value and value.upper() not in ("Y", "N"):
                return "AcknRequired must be Y or N"
        if col == "Priority" and value and not value.isdigit():
            return "Priority must be a number (1-999)"
    if kind == "rd11":
        if col in ("MinValue", "MaxValue") and value and not re.match(
                r"^-?\d+(\.\d+)?$", value):
            return f"{col} must be numeric"
    return ""


def apply_edits(md_text: str, kind: str, edits: dict) -> tuple[str, list]:
    """Apply {key: {col: value}} to the table. Locked columns and unknown
    keys are REFUSED (returned in problems), never silently applied."""
    spec = KINDS[kind]
    cols, rows, lnos = parse_table(md_text, spec["key"])
    problems: list[str] = []
    if not cols:
        return md_text, [f"{spec['file']}: table with {spec['key']} not found"]
    lines = md_text.splitlines()
    by_key = {r[spec["key"]]: (r, ln) for r, ln in zip(rows, lnos)}
    for key, changes in (edits or {}).items():
        if key not in by_key:
            problems.append(f"{key}: not in table — refused")
            continue
        row, lno = by_key[key]
        touched = False
        for col, value in (changes or {}).items():
            if col not in spec["editable"]:
                problems.append(f"{key}.{col}: locked column — refused")
                continue
            err = _validate(kind, col, str(value).strip(), row)
            if err:
                problems.append(f"{key}.{col}: {err}")
                continue
            row[col] = str(value).strip()
            touched = True
        if touched:   # refused-only rows keep their original formatting
            lines[lno] = "| " + " | ".join(row.get(c, "")
                                           for c in cols) + " |"
    return "\n".join(lines) + ("\n" if md_text.endswith("\n") else ""), problems


# ---------------------------------------------------------------------------
# decisions persistence (regeneration can never erase engineer work)
# ---------------------------------------------------------------------------

def _decisions_path(project_root: Path) -> Path:
    return Path(project_root) / "metadata" / "hmi_decisions.json"


def load_decisions(project_root: Path) -> dict:
    fp = _decisions_path(project_root)
    if not fp.exists():
        return {}
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_decisions(project_root: Path, kind: str, edits: dict) -> None:
    """Merge edits into the persistent decisions file; empty values drop
    the entry (same convention as the dossier decisions.json)."""
    all_d = load_decisions(project_root)
    bucket = all_d.setdefault(kind, {})
    for key, changes in (edits or {}).items():
        cur = bucket.setdefault(key, {})
        for col, value in (changes or {}).items():
            v = str(value).strip()
            if v:
                cur[col] = v
            else:
                cur.pop(col, None)
        if not cur:
            bucket.pop(key, None)
    fp = _decisions_path(project_root)
    fp.parent.mkdir(exist_ok=True)
    fp.write_text(json.dumps(all_d, ensure_ascii=False, indent=2),
                  encoding="utf-8")


def apply_saved_decisions(project_root: Path, kind: str,
                          md_text: str) -> str:
    """Re-apply persisted engineer decisions after a draft regeneration."""
    edits = load_decisions(project_root).get(kind, {})
    if not edits:
        return md_text
    new_text, _problems = apply_edits(md_text, kind, edits)
    return new_text
