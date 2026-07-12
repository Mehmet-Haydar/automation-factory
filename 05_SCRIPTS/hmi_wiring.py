#!/usr/bin/env python3
"""hmi_wiring.py — approved HMI wiring → generated PLC code (dilim ⑤).

hmi_codegen produces HMI_WIRING_PROPOSAL.md and stops there on purpose:
binding an HMI command into the program changes machine semantics, so
NOTHING is auto-applied. This module is the second half of that contract:

  decisions   metadata/hmi_wiring.json — per interface tag the engineer's
              named approval (or explicit rejection). Persisted like every
              other decision file: regeneration can never erase it.
  code gen    _output/FC_HMI_Wiring.scl — deterministic wiring code from
              the APPROVED lines only:
                Sts   lamp members driven from the PROVEN legacy lamp
                      equation, operands translated to the new IEC tags
                      via RD01 (OldTag ↔ Tag). An equation with an
                      untranslatable operand becomes an honest TODO
                      comment — never a guessed assignment.
                Alarm DB_Alarm bools driven the same way (RD08 TriggerTag
                      = the legacy lamp/horn output).
                Cmd   approved commands become a Mrg (merged) member:
                      Mrg.x := physical input OR HMI command — the OR is
                      exactly what the engineer approved; FB inputs are
                      then re-pointed at Mrg by the engineer/assembler.
                      Unapproved commands generate NOTHING.

Fail-honest throughout: every skipped line says why, in the file itself.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

WIRING_FILE = "hmi_wiring.json"
FC_FILE = "FC_HMI_Wiring.scl"

_LEGACY_IN_NOTES = re.compile(r"legacy\s+([A-Z]+\s?\d+(?:\.\d+)?)")


# ---------------------------------------------------------------------------
# decisions (persisted, regeneration-proof)
# ---------------------------------------------------------------------------

def _wiring_path(root: Path) -> Path:
    return Path(root) / "metadata" / WIRING_FILE


def load_wiring(root: Path) -> dict:
    fp = _wiring_path(root)
    if not fp.exists():
        return {}
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_wiring_decision(root: Path, tag: str, approved: bool,
                         by: str, note: str = "") -> tuple[bool, str]:
    """Record the engineer's decision for ONE interface tag. Approval needs
    a name (wiring changes program semantics — same W-A1 discipline as
    every other sign-off); rejection may be anonymous."""
    tag = (tag or "").strip()
    if not tag.startswith("DB_HMI."):
        return False, f"Unknown interface tag: {tag!r}"
    by = (by or "").strip()
    if approved and (len([t for t in by.split() if t]) < 2
                     or not any(c.isalpha() for c in by)):
        return False, ("Approving a wiring line needs a name "
                       "(name-surname or name-role).")
    w = load_wiring(root)
    w[tag] = {
        "approved": bool(approved),
        "by": by,
        "note": (note or "").strip(),
        "at": date.today().isoformat(),
    }
    fp = _wiring_path(root)
    fp.parent.mkdir(exist_ok=True)
    fp.write_text(json.dumps(w, ensure_ascii=False, indent=2),
                  encoding="utf-8")
    return True, ""


# ---------------------------------------------------------------------------
# proposal rows (single source: RD11/RD08, same parse as hmi_codegen)
# ---------------------------------------------------------------------------

def wiring_rows(root: Path) -> list[dict]:
    """The wiring proposal joined with the persisted decisions.
    [{tag, area, member, legacy, direction, label, approved(None|bool),
      by, note}]"""
    return wiring_rows_with_problems(root)[0]


def wiring_rows_with_problems(root: Path) -> tuple[list[dict], list[str]]:
    """wiring_rows plus the rows it could NOT use (S-5, audit M-02).

    An RD11 row whose PLC_Tag does not follow DB_HMI.<Cmd|Set|Sts>.<member>
    used to vanish with a silent `continue` — the engineer saw "0 open
    items" while a button/lamp was never wired. Same fail-honest discipline
    as hmi_codegen's `problems` list."""
    from hmi_table_edit import KINDS, parse_table  # type: ignore
    root = Path(root)
    decisions = load_wiring(root)
    rows: list[dict] = []
    problems: list[str] = []
    by_name: dict[str, str] | None = None       # lazy — RD01 parse is not free
    fp = root / "metadata" / KINDS["rd11"]["file"]
    if fp.is_file():
        _c, trows, _l = parse_table(
            fp.read_text(encoding="utf-8", errors="replace"), "HMI_TagID")
        for r in trows:
            plc = r.get("PLC_Tag", "")
            parts = plc.split(".")
            if len(parts) != 3 or parts[0] != "DB_HMI":
                tid = r.get("HMI_TagID", "") or "?"
                problems.append(
                    f"{tid}: PLC_Tag '{plc or '(empty)'}' does not follow "
                    "DB_HMI.<Cmd|Set|Sts>.<member> — row NOT in the wiring "
                    "proposal; fix RD11 or it will never be wired")
                continue
            area, member = parts[1], parts[2]
            m = _LEGACY_IN_NOTES.search(r.get("Notes", ""))
            legacy = m.group(1).replace(" ", "") if m else ""
            if not legacy:
                # F3 fallback: AI drafts sometimes omit "legacy E 0.0" from
                # Notes; without it the wiring merge drops the row as "no
                # physical twin". Recover the operand deterministically
                # from RD01 before giving up.
                if by_name is None:
                    by_name = _operand_by_name(root)
                legacy = _legacy_fallback(
                    r.get("HMI_TagID", ""), member, r.get("Notes", ""),
                    by_name)
            d = decisions.get(plc, {})
            rows.append({
                "tag": plc, "area": area, "member": member,
                "legacy": legacy,
                "direction": "PLC → HMI" if area == "Sts" else "HMI → PLC",
                "label": r.get("Label_DE") or r.get("Label_EN")
                         or r.get("HMI_TagID", ""),
                "approved": d.get("approved") if d else None,
                "by": d.get("by", ""), "note": d.get("note", ""),
                "at": d.get("at", ""),
            })
    return rows, problems


# ---------------------------------------------------------------------------
# operand translation (legacy proven equation → new IEC tags)
# ---------------------------------------------------------------------------

def _canon_s5(operand: str) -> str:
    """'E 0.0'/'I0.0'/'%I0.0' → s5_logic_extract canonical 'I0.0';
    'A 5.1'/'Q5.1' → 'Q5.1'. '' when not a bit operand."""
    v = (operand or "").strip().upper().lstrip("%").replace(" ", "")
    m = re.match(r"^([EAIQ])(\d{1,3})\.(\d)$", v)
    if not m:
        return ""
    d = {"E": "I", "A": "Q"}.get(m.group(1), m.group(1))
    return f"{d}{int(m.group(2))}.{m.group(3)}"


def _tagmap(root: Path) -> dict[str, str]:
    """{canonical legacy operand: new IEC tag name} from RD01."""
    try:
        from iec_tag_generator import parse_rd01_signals  # type: ignore
        signals = parse_rd01_signals(Path(root))
    except Exception:
        return {}
    out: dict[str, str] = {}
    for s in signals:
        name = (s.get("name") or "").strip()
        if not name:
            continue
        for cell in (s.get("oldtag", ""), s.get("address", "")):
            c = _canon_s5(cell)
            if c:
                out.setdefault(c, name)
    return out


def _operand_by_name(root: Path) -> dict[str, str]:
    """{RD01 tag name (upper): canonical legacy operand} — reverse of
    _tagmap; feeds the F3 fallback when RD11 Notes lack 'legacy E 0.0'."""
    try:
        from iec_tag_generator import parse_rd01_signals  # type: ignore
        signals = parse_rd01_signals(Path(root))
    except Exception:
        return {}
    out: dict[str, str] = {}
    for s in signals:
        name = (s.get("name") or "").strip().upper()
        if not name:
            continue
        for cell in (s.get("oldtag", ""), s.get("address", "")):
            c = _canon_s5(cell)
            if c:
                out.setdefault(name, c)
                break
    return out


_TYPE_PREFIX = re.compile(r"^(?:F|DI|DQ|AI|AQ)_")
_HUNGARIAN = re.compile(r"^[BIR]_?")


def _legacy_fallback(hmi_tagid: str, member: str, notes: str,
                     by_name: dict[str, str]) -> str:
    """Derive the legacy operand from RD01 when Notes lack 'legacy E 0.0'.
    Deterministic and conservative: an RD01 tag name cited in Notes wins;
    otherwise the HMI_TagID / member stem must match exactly ONE RD01 name
    (with or without its DI_/DQ_/... type prefix). Ambiguity returns ''."""
    up_notes = (notes or "").upper()
    if up_notes:
        cited = [opd for name, opd in by_name.items()
                 if name and re.search(rf"(?<![A-Z0-9_]){re.escape(name)}"
                                       rf"(?![A-Z0-9_])", up_notes)]
        if len(set(cited)) == 1:
            return cited[0]
    stems: list[str] = []
    tid = (hmi_tagid or "").strip().upper()
    if tid.startswith("HMI_"):
        stems.append(tid[4:])
    mem = _HUNGARIAN.sub("", (member or "").strip().upper())
    if mem and mem not in stems:
        stems.append(mem)
    for stem in stems:
        hits = {opd for name, opd in by_name.items()
                if name == stem or _TYPE_PREFIX.sub("", name) == stem}
        if len(hits) == 1:
            return next(iter(hits))
    return ""


def _render_scl(expr, tagmap: dict) -> tuple[str, set]:
    """Render an s5_logic_extract Expr with new tags. Returns
    (scl_text, missing_operands). Unmapped operands render as-is AND are
    reported — the caller decides comment-vs-code."""
    from s5_logic_extract import And, Not, Or, Var  # type: ignore
    missing: set[str] = set()

    def walk(e) -> str:
        if isinstance(e, Var):
            tag = tagmap.get(e.operand)
            if tag:
                return f'"{tag}"'
            missing.add(e.operand)
            return e.operand
        if isinstance(e, Not):
            inner = walk(e.a)
            if isinstance(e.a, (And, Or)):
                inner = f"({inner})"
            return f"NOT {inner}"
        if isinstance(e, And):
            parts = []
            for x in (e.a, e.b):
                s = walk(x)
                if isinstance(x, Or):
                    s = f"({s})"
                parts.append(s)
            return " AND ".join(parts)
        if isinstance(e, Or):
            return f"{walk(e.a)} OR {walk(e.b)}"
        missing.add(str(e))
        return str(e)

    return walk(expr), missing


def _proven_equations(root: Path) -> dict[str, object]:
    """{canonical Q operand: Expr} — the '=' coils proven from legacy AWL."""
    try:
        from s5_logic_extract import extract_project_logic  # type: ignore
        nets = extract_project_logic(Path(root))
    except Exception:
        return {}
    out: dict[str, object] = {}
    for nl in nets:
        if not nl.parsed:
            continue
        for addr, coil in nl.coils.items():
            if addr.startswith("Q") and coil.assign is not None:
                out[addr] = coil.assign
    return out


# ---------------------------------------------------------------------------
# code generation
# ---------------------------------------------------------------------------

def generate_wiring_code(root: Path) -> dict:
    """FC_HMI_Wiring.scl from the approved wiring + proven lamp logic.
    Also regenerates DB_HMI (via hmi_codegen) so the Mrg struct exists for
    every approved command."""
    root = Path(root)
    rows = wiring_rows(root)
    if not rows:
        return {"ok": False,
                "msg": "No wiring rows — generate the HMI interface first "
                       "(RD11 with DB_HMI tags)."}
    tagmap = _tagmap(root)
    equations = _proven_equations(root)

    sts_lines: list[str] = []
    mrg_lines: list[str] = []
    todo: list[str] = []
    driven = merged = 0

    for r in rows:
        legacy_c = _canon_s5(r["legacy"])
        if r["area"] == "Sts":
            # Display only — semantics-safe, always generated when provable.
            expr = equations.get(legacy_c) if legacy_c else None
            if expr is None:
                todo.append(f"Sts.{r['member']}: no proven equation for "
                            f"legacy {r['legacy'] or '?'} — drive from the "
                            "new FB status manually")
                continue
            scl, missing = _render_scl(expr, tagmap)
            if missing:
                todo.append(
                    f"Sts.{r['member']}: operands not in RD01 "
                    f"({', '.join(sorted(missing))}) — proven legacy logic: "
                    f"{scl}")
                continue
            sts_lines.append(f'    "DB_HMI".Sts.{r["member"]} := {scl};'
                             f'   // {r["label"]} (proven, ex {r["legacy"]})')
            driven += 1
        elif r["area"] == "Set":
            # Setpoint binding is assembler work (FB input re-point) — an
            # approval here is recorded and surfaced, never silently lost.
            if r["approved"] is True:
                todo.append(f"Set.{r['member']}: approved by {r['by']} — "
                            "bind at the FB input (assembler/engineer work; "
                            "replaces the BCD thumbwheel)")
        elif r["area"] == "Cmd":
            # Semantics-changing — ONLY the engineer's named approval
            # generates code; everything else stays a proposal.
            if r["approved"] is not True:
                continue
            phys = tagmap.get(legacy_c, "") if legacy_c else ""
            if phys:
                mrg_lines.append(
                    f'    "DB_HMI".Mrg.{r["member"]} := "{phys}" OR '
                    f'"DB_HMI".Cmd.{r["member"]};'
                    f'   // approved: {r["by"]} {r["at"]}')
            else:
                mrg_lines.append(
                    f'    "DB_HMI".Mrg.{r["member"]} := '
                    f'"DB_HMI".Cmd.{r["member"]};'
                    f'   // approved: {r["by"]} {r["at"]} — no physical twin')
            merged += 1

    # Alarms: TriggerTag = legacy lamp/horn output; same proof discipline.
    alarms = 0
    alarm_lines: list[str] = []
    rd08 = root / "metadata" / "RD08_Alarm.md"
    if rd08.is_file():
        from hmi_table_edit import parse_table  # type: ignore
        _c, arows, _l = parse_table(
            rd08.read_text(encoding="utf-8", errors="replace"), "AlarmID")
        for a in arows:
            member = f"{a.get('AlarmID', '')}_{a.get('AlarmName', '')}"
            trig_c = _canon_s5(a.get("TriggerTag", ""))
            expr = equations.get(trig_c) if trig_c else None
            if expr is None:
                todo.append(f"DB_Alarm.{member}: no proven equation for "
                            f"trigger {a.get('TriggerTag', '?')}")
                continue
            scl, missing = _render_scl(expr, tagmap)
            if missing:
                todo.append(f"DB_Alarm.{member}: operands not in RD01 "
                            f"({', '.join(sorted(missing))})")
                continue
            alarm_lines.append(f'    "DB_Alarm".{member} := {scl};'
                               f'   // {a.get("AlarmText_DE") or a.get("AlarmText_EN") or member}')
            alarms += 1

    body = [
        'FUNCTION "FC_HMI_Wiring" : Void',
        "{ S7_Optimized_Access := 'TRUE' }",
        "VERSION : 0.1",
        "// Generated HMI wiring — call at the END of OB1 (after the FBs).",
        "// Sts/alarm drives come from PROVEN legacy lamp equations with",
        "// operands translated via RD01; Mrg merges are the engineer's",
        "// APPROVED command bindings (hmi_wiring.json). Regenerate after",
        "// wiring decisions change; do not edit by hand.",
        "BEGIN",
    ]
    if mrg_lines:
        body += ["    // --- approved command merges (point FB inputs at "
                 "Mrg.*) ---"] + mrg_lines
    if sts_lines:
        body += ["    // --- lamp status drives (display only) ---"] + sts_lines
    if alarm_lines:
        body += ["    // --- alarm drives (ISA-18.2 list subscribes to "
                 "DB_Alarm) ---"] + alarm_lines
    if todo:
        body += ["    // --- NOT generated (honest gaps — engineer work) ---"]
        body += [f"    // TODO {t}" for t in todo]
    if not (mrg_lines or sts_lines or alarm_lines):
        body += ["    // nothing approved/provable yet — see TODO list above"]
    body += ["END_FUNCTION", ""]

    out = root / "_output"
    out.mkdir(exist_ok=True)
    (out / FC_FILE).write_text("\n".join(body), encoding="utf-8")

    # DB_HMI must carry the Mrg struct for the merged commands.
    try:
        from hmi_codegen import generate_hmi_interface  # type: ignore
        generate_hmi_interface(root)
    except Exception:
        pass

    return {"ok": True, "file": FC_FILE, "sts_driven": driven,
            "cmd_merged": merged, "alarms_driven": alarms,
            "todo": todo}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: hmi_wiring.py <project_root>")
        raise SystemExit(2)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    print(json.dumps(generate_wiring_code(Path(sys.argv[1])),
                     ensure_ascii=False, indent=2))
