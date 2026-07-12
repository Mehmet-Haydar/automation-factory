#!/usr/bin/env python3
"""
sistema_support.py — SISTEMA helper package

Division of labour (user decision 2026-06-12, immutable):
**the software reminds and documents; the engineer calculates and signs.**
There is NO automatic PL calculation anywhere in this module.

Provides:
1. ``parse_rd05_safety_functions`` — safety-function list from RD05
   (function name, PLr if present, RD01 signal matches).
2. ``generate_sistema_prep`` — `_output/SISTEMA_PREP_<ts>.md` (i18n DE/EN/TR):
   the engineer's input template for SISTEMA.  When RD05 has no PLr at all
   the document is still produced WITH a visible warning block (a silent
   empty list is forbidden).
3. ``load_sistema_records`` / ``add_sistema_record`` / ``delete_sistema_record``
   — engineer declarations {function, file, achieved_pl, date, engineer}
   stored in PROJECT_STATE.json under ``sistema_records`` (same declaration
   pattern as the Gate-6 "manually tested" confirmation).
4. ``sistema_status`` — which RD05 PLr functions still lack a record
   (drives the WARNING — never a blocker — in FAT/SAT generation).
5. ``render_sistema_section_md`` — the "SISTEMA calculation" reference
   section for delivery documents (records table when present, honest
   PENDING box otherwise; fake/placeholder report names are FORBIDDEN —
   only file names the engineer actually entered are ever printed).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from protocol_i18n import DEFAULT_LANG, normalize_lang, t  # noqa: E402


class SistemaInputError(RuntimeError):
    """Raised when the inputs needed for the prep list are absent entirely
    (no RD05 file) — fail-loud, never an empty document."""


# ── RD05 / RD01 parsing ───────────────────────────────────────────────────────

_PL_VALUE = re.compile(r"\bPL\s*[:=]?\s*([a-e])\b|\b([a-e])\b", re.IGNORECASE)

# Column-header keywords
_FUNC_KEYS = ("funktion", "function", "fonksiyon", "func", "işlev", "islev", "sf")
_PLR_KEYS = ("plr", "pl_r", "pl r", "performance", "pl")
_SIGNAL_HINT = re.compile(
    r"E.?stop|door|kapı|tür|interlock|güvenlik|safety|schutz|licht|light|muting",
    re.IGNORECASE,
)


def _split_row(stripped: str) -> list[str]:
    return [c.strip() for c in stripped.strip("|").split("|")]


def _extract_pl(cell: str) -> str:
    """'PL d' / 'PLd' / 'd' / 'PL=e' → 'd'/'e'; anything else → ''."""
    cell = (cell or "").strip()
    if not cell or cell == "-" or cell == "—":
        return ""
    m = re.fullmatch(r"(?:PL\s*[:=]?\s*)?([a-eA-E])", cell.replace("_", " ").strip())
    if m:
        return m.group(1).lower()
    m = re.search(r"\bPL\s*[:=]?\s*([a-eA-E])\b", cell)
    if m:
        return m.group(1).lower()
    return ""


def _discover_rd05(project_path: Path) -> Optional[Path]:
    metadata = project_path / "metadata"
    if not metadata.is_dir():
        return None
    candidates = sorted(metadata.glob("RD05_Safety*.md"))
    return candidates[0] if candidates else None


def _read_rd01_signals(project_path: Path) -> list[dict]:
    try:
        from script_protocol_generator import _parse_io_from_rd01, _read_rd
        return _parse_io_from_rd01(_read_rd(project_path, "RD01"))
    except Exception:
        return []


def _match_signals(function_name: str, signals: list[dict]) -> list[str]:
    """Token-overlap match between a safety-function name and RD01 tags.

    Heuristic on purpose (documented in the prep list as a suggestion the
    engineer must verify) — an empty result is rendered as an explicit
    "no match found" note, never silently dropped.
    """
    tokens = [tok.lower() for tok in re.split(r"[^A-Za-z0-9]+", function_name)
              if len(tok) >= 3]
    out = []
    for sig in signals:
        name = sig.get("name", "")
        lname = name.lower()
        if any(tok in lname for tok in tokens):
            out.append(name)
    return out


def parse_rd05_safety_functions(project_path: Path) -> list[dict]:
    """Return [{function, plr, signals: [tag,...]}] from RD05 table rows.

    Rows are taken from markdown tables; a row counts as a safety function
    when it matches the safety keyword hint OR the table has a PLr column.
    PLr is extracted per row when a PLr-ish column exists ('' when absent).
    """
    rd05 = _discover_rd05(project_path)
    if rd05 is None:
        # Log hygiene: message reaches the GUI log — no full project path.
        raise SistemaInputError(
            "No RD05_Safety*.md found under metadata/ — the SISTEMA "
            "preparation list needs the safety requirements document. "
            "Create RD05 first."
        )
    signals = _read_rd01_signals(project_path)

    functions: list[dict] = []
    in_table = False
    col_names: list[str] = []
    func_idx: Optional[int] = None
    plr_idx: Optional[int] = None

    for line in rd05.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and not in_table:
            cells = [c.lower() for c in _split_row(stripped)]
            in_table = True
            col_names = cells
            func_idx = next(
                (i for i, c in enumerate(cells)
                 if any(k in c for k in _FUNC_KEYS)), None)
            # exact-ish PLr column: avoid matching e.g. "plan"
            plr_idx = next(
                (i for i, c in enumerate(cells)
                 if any(k == c or k in c.split() or c.startswith(k)
                        for k in _PLR_KEYS)), None)
            continue
        if in_table and re.match(r"^\|[-|\s:]+\|$", stripped):
            continue
        if in_table and stripped.startswith("|"):
            cells = _split_row(stripped)
            if not any(cells):
                in_table = False
                continue
            name = cells[func_idx] if (func_idx is not None and func_idx < len(cells)) else cells[0]
            if not name or name == "-":
                continue
            row_is_safety = bool(_SIGNAL_HINT.search(stripped)) or plr_idx is not None
            if not row_is_safety:
                continue
            plr = ""
            if plr_idx is not None and plr_idx < len(cells):
                plr = _extract_pl(cells[plr_idx])
            functions.append({
                "function": name,
                "plr": plr,
                "signals": _match_signals(name, signals),
            })
        elif in_table and not stripped.startswith("|"):
            in_table = False
            col_names = []
            func_idx = plr_idx = None

    return functions


# ── prep document ─────────────────────────────────────────────────────────────

@dataclass
class SistemaPrepResult:
    md_path: Optional[Path] = None
    functions: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.md_path is not None


def generate_sistema_prep(project_path: Path, lang: str = DEFAULT_LANG) -> SistemaPrepResult:
    """Write `_output/SISTEMA_PREP_<ts>.md` — the engineer's SISTEMA input
    template.  RD05 without any PLr → document is still produced WITH a
    visible warning block (silent empty list forbidden)."""
    lang = normalize_lang(lang)
    result = SistemaPrepResult()
    functions = parse_rd05_safety_functions(project_path)  # raises if no RD05
    result.functions = functions

    has_any_plr = any(f["plr"] for f in functions)
    ts_label = datetime.now().strftime("%Y-%m-%d %H:%M")
    ts_file = datetime.now().strftime("%Y%m%d_%H%M")

    lines = [
        f"# {t('sistema.prep_title', lang)} — {project_path.name}",
        "",
        f"**{t('common.date', lang)}:** {ts_label}",
        "",
        f"> {t('sistema.prep_intro', lang)}",
        "",
    ]
    if not has_any_plr:
        warn = t("sistema.no_plr_warning", lang)
        lines += [f"> ⚠ **{warn}**", ""]
        result.warnings.append(warn)

    lines += [
        f"| {t('sistema.col_function', lang)} | {t('sistema.col_plr', lang)} "
        f"| {t('sistema.col_signals', lang)} | {t('sistema.col_achieved', lang)} "
        f"| {t('sistema.col_file', lang)} | {t('sistema.col_engineer', lang)} |",
        "|---|---|---|---|---|---|",
    ]
    no_match = t("sistema.no_signal_match", lang)
    for f in functions:
        signals = ", ".join(f"`{s}`" for s in f["signals"]) if f["signals"] else no_match
        plr = f["plr"] or "—"
        lines.append(
            f"| {f['function']} | {plr} | {signals} | ______ | ______ | ______ |"
        )
    if not functions:
        # No table rows recognized at all — still no silent empty doc.
        warn = t("sistema.no_plr_warning", lang)
        if warn not in result.warnings:
            lines += ["", f"> ⚠ **{warn}**"]
            result.warnings.append(warn)

    lines += ["", "---", f"*AUTOMATION FACTORY — sistema_support.py | {ts_label}*", ""]

    out_dir = project_path / "_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"SISTEMA_PREP_{ts_file}.md"
    dest.write_text("\n".join(lines), encoding="utf-8")
    result.md_path = dest
    return result


# ── engineer declaration records (PROJECT_STATE.sistema_records) ──────────────

_RECORD_FIELDS = ("function", "file", "achieved_pl", "date", "engineer")


def _state_path(project_path: Path) -> Path:
    return project_path / "PROJECT_STATE.json"


def _read_state(project_path: Path, *, strict: bool = False) -> dict:
    """Read PROJECT_STATE.json.

    Missing file → {} (a fresh project, fine). When the file EXISTS but is
    unparseable: readers (strict=False) tolerate it with {}, but writers
    (strict=True) MUST raise — silently returning {} there would make the
    caller overwrite the whole state (gate approvals, platform, TIA settings)
    with just its own key. That is irreversible data loss.
    """
    p = _state_path(project_path)
    if p.exists():
        # NB: json.JSONDecodeError IS a subclass of ValueError, so a parse
        # failure must be handled here explicitly — never let it propagate on
        # the tolerant (reader) path.
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = None
        if data is None:                 # unparseable / corrupt
            if strict:
                raise ValueError(
                    "PROJECT_STATE.json is corrupt — refusing to overwrite "
                    "(would lose gate approvals and project state)")
            return {}
        if isinstance(data, dict):
            return data
        if strict:                       # valid JSON but not an object
            raise ValueError(
                "PROJECT_STATE.json is not an object — refusing to "
                "overwrite (would lose existing project state)")
        return {}
    return {}


def load_sistema_records(project_path: Path) -> list[dict]:
    records = _read_state(project_path).get("sistema_records") or []
    return [r for r in records if isinstance(r, dict)]


def add_sistema_record(
    project_path: Path,
    function: str,
    file: str = "",
    achieved_pl: str = "",
    engineer: str = "",
) -> dict:
    """Append an engineer declaration.  function + engineer are mandatory
    (a record without a responsible name is not a declaration)."""
    function = (function or "").strip()
    engineer = (engineer or "").strip()
    if not function:
        raise ValueError("sistema record: 'function' must not be empty")
    if not engineer:
        raise ValueError(
            "sistema record: 'engineer' must not be empty — the record is an "
            "engineer declaration (same pattern as the Gate-6 manual-test "
            "confirmation)."
        )
    achieved = _extract_pl(achieved_pl) or (achieved_pl or "").strip()
    record = {
        "function": function,
        "file": (file or "").strip(),
        "achieved_pl": achieved,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "engineer": engineer,
    }
    state = _read_state(project_path, strict=True)
    records = [r for r in (state.get("sistema_records") or []) if isinstance(r, dict)]
    records.append(record)
    state["sistema_records"] = records
    _state_path(project_path).write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return record


def delete_sistema_record(project_path: Path, index: int) -> bool:
    state = _read_state(project_path, strict=True)
    records = [r for r in (state.get("sistema_records") or []) if isinstance(r, dict)]
    if not (0 <= index < len(records)):
        return False
    records.pop(index)
    state["sistema_records"] = records
    _state_path(project_path).write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


# ── status / delivery-document section ────────────────────────────────────────

def sistema_status(project_path: Path) -> dict:
    """Pending = RD05 functions WITH a PLr but WITHOUT a record.

    Returns {"functions": [...], "records": [...], "pending": [names],
    "rd05_has_plr": bool}.  Missing RD05 → empty status (the FAT generator
    has its own RD05 gate; this helper never raises for the warning path).
    """
    try:
        functions = parse_rd05_safety_functions(project_path)
    except SistemaInputError:
        functions = []
    records = load_sistema_records(project_path)
    recorded_names = {r.get("function", "").strip().lower() for r in records}
    with_plr = [f for f in functions if f["plr"]]
    pending = [
        f["function"] for f in with_plr
        if f["function"].strip().lower() not in recorded_names
    ]
    return {
        "functions": functions,
        "records": records,
        "pending": pending,
        "rd05_has_plr": bool(with_plr),
    }


def render_sistema_section_md(project_path: Path, lang: str = DEFAULT_LANG,
                              heading_level: int = 2) -> str:
    """The "SISTEMA calculation" reference block for delivery documents
    (customer report, SAT protocol).

    - records present → declaration table (only engineer-entered file names —
      placeholder/fake report names are FORBIDDEN).
    - RD05 has PLr but records missing → loud PENDING box listing the open
      functions.
    - RD05 has no PLr at all → honest note (status always explicit; a silent
      "—" is forbidden).
    """
    lang = normalize_lang(lang)
    status = sistema_status(project_path)
    h = "#" * heading_level
    lines = [f"{h} {t('sistema.section_title', lang)}", ""]

    if status["records"]:
        lines += [
            f"| {t('sistema.col_function', lang)} | {t('sistema.col_achieved', lang)} "
            f"| {t('sistema.col_file', lang)} | {t('common.date', lang)} "
            f"| {t('sistema.col_engineer', lang)} |",
            "|---|---|---|---|---|",
        ]
        for r in status["records"]:
            lines.append(
                f"| {r.get('function', '')} | {r.get('achieved_pl') or '—'} "
                f"| {r.get('file') or '—'} | {r.get('date', '')} "
                f"| {r.get('engineer', '')} |"
            )
        lines += ["", f"> {t('sistema.record_note', lang)}"]

    if status["pending"]:
        lines += ["", f"> ⚠ **{t('sistema.pending_box', lang)}**", ""]
        for name in status["pending"]:
            lines.append(f"- ☐ {name}")
    elif not status["records"]:
        if status["rd05_has_plr"]:
            # has PLr, nothing pending, no records — cannot happen by
            # construction (pending covers it), kept for completeness
            lines += ["", f"> ⚠ **{t('sistema.pending_box', lang)}**"]
        else:
            lines += ["", f"> {t('sistema.no_plr_in_rd05', lang)}"]

    lines.append("")
    return "\n".join(lines)
