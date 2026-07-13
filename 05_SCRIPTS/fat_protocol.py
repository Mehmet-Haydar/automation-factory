#!/usr/bin/env python3
"""
fat_protocol.py — FAT/SAT Test Protocol Generator (Phase 31; SAT v2 Faz 1)

FAT (factory acceptance, IEC 62381) — simulation/PLCSim scope:
  1. IO validation tests (for each signal)
  2. Safety function tests (ISO 13849-2 validation scenarios, simulated)
  3. Analog boundary value tests (0 / 27648 / overflow)
  4. State machine step and transition tests
  5. Stress / stability tests

SAT (site acceptance, IEC 62381) — real-plant scope (SAT ≠ FAT copy):
  1. Loop check with real field devices (RD01 signals)
  2. Motor rotation direction check
  3. Sensor / switch alignment
  4. Real E-stop chain and guard door circuit (ISO 13849-2 / EN 60204-1)
  5. Drive parameter verification
  6. Network / HMI integration
  7. Cybersecurity (IEC 62443 / NIS2)
  8. Backup and handover (incl. restore test + handover record)

Output: Markdown always; PDF optional (pdf_common.markdown_to_pdf — on PDF
failure the MD remains and a loud warning is appended, never a silent skip).
Languages: DE (default) / EN / TR via protocol_i18n.

CLI:
  python fat_protocol.py --project PROJECT_PATH [--type FAT|SAT|BOTH]
                         [--lang de|en|tr] [--pdf] [--out FOLDER]
"""

from __future__ import annotations

import re
import sys
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

FACTORY_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from protocol_i18n import (  # noqa: E402
    DEFAULT_LANG, FAT_SAFETY_SCENARIOS, FAT_SM_PREFIXES, FAT_STRESS_PREFIXES,
    SAT_CYBER_ROWS, force_utf8_stdout, normalize_lang, t,
)


# ── Exceptions ────────────────────────────────────────────────────────────────

class Rd05BlockedError(RuntimeError):
    """Raised when RD05 (Safety Requirements) is missing or empty.

    B-P5 / S-17: FAT protocol generation is blocked if RD05 is absent,
    empty, or contains only template/heading content.  A generic-safety-
    scenario FAT must never reach the customer without project-specific
    safety requirements.

    Fail-closed: when in doubt, block.
    """
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(
            f"FAT protocol blocked — RD05 (Safety) not ready: {reason}. "
            "Add or complete the RD05_Safety*.md file under metadata/ before "
            "generating the FAT protocol."
        )


# ── RD05 readiness gate (B-P5 / S-17) ────────────────────────────────────────

# Lines that indicate an empty / template-only file.
# A file that contains ONLY headings, dividers, or these placeholder phrases
# is considered a template, not a filled safety requirements document.
_TEMPLATE_PATTERNS = re.compile(
    r"^\s*(?:#|---|> |___|TODO|FIXME|BURAYA|PLACEHOLDER|GEREKSİNİM_YAZ|"
    r"safety requirements here|fill in|to be completed|tamamlanacak|\[.*\])\s*$",
    re.IGNORECASE,
)
# Minimum number of non-trivial content lines required for RD05 to be
# considered "filled".  A real safety requirements document has at least
# this many substantive lines (table rows, numbered requirements, etc.).
_RD05_MIN_CONTENT_LINES = 3


def check_rd05_ready(project_path: Path) -> Path:
    """Assert that RD05 exists and contains substantive content.

    Returns the RD05 file path when the check passes.

    Raises ``Rd05BlockedError`` (fail-closed) when:
    - metadata/ directory is absent,
    - no RD05_Safety*.md file is found,
    - the file is empty (0 bytes),
    - the file contains fewer than ``_RD05_MIN_CONTENT_LINES`` non-trivial
      lines (template/heading-only = not ready).

    This function is the single source of truth for RD05 readiness; all
    FAT-generation entry points (fat_protocol.run_fat_protocol,
    script_protocol_generator.generate_protocol, factory_web.generate_fat)
    call it before producing any output.
    """
    metadata = project_path / "metadata"
    if not metadata.is_dir():
        # Log hygiene: the reason reaches the GUI log — no full project path.
        raise Rd05BlockedError(
            "metadata/ directory not found in the project"
        )

    candidates = sorted(metadata.glob("RD05_Safety*.md"))
    if not candidates:
        raise Rd05BlockedError(
            "no RD05_Safety*.md file found under metadata/"
        )

    rd05 = candidates[0]
    if rd05.stat().st_size == 0:
        raise Rd05BlockedError(
            f"{rd05.name} is empty (0 bytes)"
        )

    text = rd05.read_text(encoding="utf-8", errors="ignore")
    content_lines = [
        ln for ln in text.splitlines()
        if ln.strip() and not _TEMPLATE_PATTERNS.match(ln)
    ]
    if len(content_lines) < _RD05_MIN_CONTENT_LINES:
        raise Rd05BlockedError(
            f"{rd05.name} contains only {len(content_lines)} substantive line(s) "
            f"(minimum required: {_RD05_MIN_CONTENT_LINES}). "
            "Fill in the safety requirements before generating the FAT protocol."
        )

    # AUDIT-004b (E2E #3 live finding, 2026-07-10): a FRESH project carries
    # no rd_status entry yet, so the AUDIT-004 state check below never fired
    # and an unreviewed AI draft passed this gate (live-caught: DO3 run,
    # assemble_program went through on a DRAFT_UNVERIFIED RD05). The draft
    # writer stamps every AI-produced RD05 with the DRAFT_UNVERIFIED banner —
    # the banner (in the header or the filename) blocks unless the engineer
    # review is recorded in PROJECT_STATE.rd_verifications (reviewed/locked)
    # or the RD is explicitly N/A.
    if "DRAFT_UNVERIFIED" in rd05.name or "DRAFT_UNVERIFIED" in text[:4000]:
        _reviewed = False
        _sf = project_path / "PROJECT_STATE.json"
        if _sf.exists():
            try:
                import json as _json
                _rec = ((_json.loads(_sf.read_text(encoding="utf-8"))
                         .get("rd_verifications") or {}).get("RD05") or {})
                _reviewed = bool(_rec.get("reviewed") or _rec.get("locked")
                                 or _rec.get("na"))
            except Exception:
                _reviewed = False           # unreadable state = not reviewed
        if not _reviewed:
            raise Rd05BlockedError(
                f"{rd05.name} carries the DRAFT_UNVERIFIED banner and no "
                "recorded engineer review — a certified safety engineer must "
                "review/approve RD05 (Gate 3) first. (AUDIT-004b)")

    # AUDIT-004: verify RD05 is not still in DRAFT_UNVERIFIED state.
    # Content lines passing the check above is not enough — the document must
    # also be explicitly approved by a certified safety engineer.
    _state_file = project_path / "PROJECT_STATE.json"
    if _state_file.exists():
        try:
            import json as _json
            _state = _json.loads(_state_file.read_text(encoding="utf-8"))
            _rd_status = _state.get("rd_status", {})
            _rd05_info = _rd_status.get("RD05_Safety") or _rd_status.get("RD05")
            if isinstance(_rd05_info, dict):
                _rd05_doc_status = (_rd05_info.get("status") or "").upper()
                if _rd05_doc_status in ("DRAFT_UNVERIFIED", "DRAFT", ""):
                    raise Rd05BlockedError(
                        f"{rd05.name} is in '{_rd05_doc_status or 'DRAFT_UNVERIFIED'}' "
                        "state — a certified safety engineer must approve RD05 before "
                        "the FAT/SAT protocol can be generated. (AUDIT-004)"
                    )
        except Rd05BlockedError:
            raise
        except Exception:
            pass  # STATE read failure: content check already passed; proceed

    return rd05


# ── Data structures ─────────────────────────────────────────────────────────────

@dataclass
class FatResult:
    md_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    test_count: int = 0
    test_type: str = "FAT"
    lang: str = DEFAULT_LANG
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.md_path is not None


# ── RD01 signal reading ─────────────────────────────────────────────────────────

def _load_signals(project_path: Path) -> list[dict]:
    try:
        scripts = FACTORY_ROOT / "05_SCRIPTS"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from iec_tag_generator import parse_rd01_signals
        return parse_rd01_signals(project_path)
    except Exception:
        return []


# ── RD08 alarm reading (IEC 62682, Faz 5) ───────────────────────────────────────

def _load_alarms(project_path: Path) -> list[dict]:
    """Parse alarms from metadata/RD08*.md (priority / response / class).

    Reuses script_protocol_generator's RD08 parser so the GUI-facing FAT and
    the standalone generator stay consistent.  Returns [] (with the caller
    emitting a warning) when no RD08 table exists — values are never invented.
    """
    try:
        metadata = project_path / "metadata"
        if not metadata.is_dir():
            return []
        candidates = sorted(metadata.glob("RD08*.md"))
        if not candidates:
            return []
        scripts = FACTORY_ROOT / "05_SCRIPTS"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from script_protocol_generator import _parse_alarms_from_rd08
        return _parse_alarms_from_rd08(candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return []


# ── RD05 detect safety functions ───────────────────────────────────

def _discover_rd05_file(project_path: Path) -> Optional[Path]:
    """Return the first RD05_Safety*.md found under metadata/, or None.

    Uses glob so any suffix variant (DRAFT_UNVERIFIED, VERIFIED, etc.) is
    accepted.  If multiple matches exist, the lexicographically first file is
    used (deterministic).  Fail-closed: returns None when nothing is found.
    """
    metadata = project_path / "metadata"
    if not metadata.is_dir():
        return None
    candidates = sorted(metadata.glob("RD05_Safety*.md"))
    if not candidates:
        return None
    if len(candidates) > 1:
        warnings.warn(
            f"fat_protocol: multiple RD05_Safety*.md files found under "
            f"{metadata}; using {candidates[0].name}. "
            "Remove or rename the extra files to avoid ambiguity.",
            stacklevel=2,
        )
    return candidates[0]


def _load_safety_notes(project_path: Path) -> list[str]:
    """Load safety function names from the first RD05_Safety*.md found.

    Returns an empty list with a warning if no RD05 file exists (fail-closed).
    """
    rd05 = _discover_rd05_file(project_path)
    if rd05 is None:
        warnings.warn(
            f"fat_protocol: no RD05_Safety*.md found under "
            f"{project_path / 'metadata'} — safety notes section will be empty.",
            stacklevel=2,
        )
        return []
    lines = []
    for line in rd05.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("|") and re.search(r"E.?stop|door|kapı|interlock|güvenlik|safety", s, re.I):
            name_col = [c.strip() for c in s.split("|")[1:-1]]
            if name_col:
                lines.append(name_col[0])
    return lines[:20]  # Maximum 20 safety entries


# ── Test section generators ────────────────────────────────────────────────────

class _Counter:
    """Thread-safe, per-protocol test-case counter.

    Replaces the previous module-global ``_TC`` mutable integer.
    Each ``run_fat_protocol`` call creates its own ``_Counter`` instance so
    that concurrent / back-to-back runs never share state.
    """

    __slots__ = ("_n",)

    def __init__(self) -> None:
        self._n: int = 0

    def next_id(self) -> str:
        self._n += 1
        return f"T{self._n:03d}"

    @property
    def value(self) -> int:
        return self._n


def _tbl_header(lang: str, cols: list[str]) -> list[str]:
    head = " | ".join(t(c, lang) for c in cols)
    sep = "|".join(["----"] * len(cols))
    return [f"| {head} |", f"|{sep}|"]


# ---- FAT sections -------------------------------------------------------------

def _section_io(signals: list[dict], counter: _Counter, lang: str, n: int) -> str:
    lines = [
        f"\n## {n}. {t('sec.io_validation', lang)}\n",
        f"> {t('intro.io_validation', lang)}\n",
    ]
    # Empty signal table: keep the section (and its number) and print a visible
    # warning — never drop the section silently, which would renumber the doc
    # and hide the gap. Mirrors _sat_section_loop_check.
    if not signals:
        lines.append(f"> ⚠ {t('fat.io.no_signals', lang)}\n")
        return "\n".join(lines)
    lines += _tbl_header(lang, [
        "col.no", "col.tag", "col.type", "col.address", "col.method",
        "col.expected", "col.ref", "col.actual", "col.result",
    ])
    ref = t("ref.iec62381", lang)
    for sig in signals:
        name = sig.get("name", "?")
        stype = sig.get("type", "UNK")
        addr = sig.get("address", "—")
        key_suffix = stype if stype in ("DI", "DQ", "AI", "AQ") else "default"
        method = t(f"fat.io.method.{key_suffix}", lang)
        expected = t(f"fat.io.expected.{key_suffix}", lang)
        lines.append(
            f"| {counter.next_id()} | `{name}` | {stype} | {addr} "
            f"| {method} | {expected} | {ref} | | ☐ |"
        )
    return "\n".join(lines)


def _section_alarm(alarms: list[dict], counter: _Counter, lang: str, n: int) -> str:
    """IEC 62682 alarm rationalization (Faz 5) — priority / operator response /
    alarm class per alarm, source RD08.  Missing fields render as "—" with a
    fill-in instruction; values are NEVER guessed.  Empty RD08 keeps the
    section (header + warning), never drops it silently."""
    lines = [
        f"\n## {n}. {t('alarm62682.title', lang)}\n",
        f"> {t('alarm62682.intro', lang)}\n",
    ]
    if not alarms:
        lines.append(f"> ⚠ {t('alarm.no_table_warning', lang)}\n")
        return "\n".join(lines)
    lines.append(f"> {t('alarm62682.fill_instruction', lang)}\n")
    lines += _tbl_header(lang, [
        "col.no", "col.tag", "alarm62682.col_priority",
        "alarm62682.col_response", "alarm62682.col_class",
        "col.ref", "col.result",
    ])
    ref = t("ref.iec62682", lang)
    for al in alarms:
        msg = al.get("message", "") or "?"
        tag = al.get("tag", "") or "—"
        prio = al.get("priority") or "—"
        resp = al.get("response") or "—"
        acls = al.get("alarm_class") or "—"
        lines.append(
            f"| {counter.next_id()} | `{tag}` — {msg} | {prio} | {resp} "
            f"| {acls} | {ref} | ☐ |"
        )
    return "\n".join(lines)


def _section_safety(safety_notes: list[str], counter: _Counter, lang: str, n: int) -> str:
    lines = [
        f"\n## {n}. {t('sec.safety', lang)}\n",
        f"> {t('intro.safety', lang)}\n",
    ]
    lines += _tbl_header(lang, [
        "col.no", "col.scenario", "col.start_state", "col.action",
        "col.expected", "col.ref", "col.actual", "col.result",
    ])
    # Standard safety tests — attribution: IEC 62061 (SCS) and ISO 13849-2
    # (validation procedure).  Plan Faz 1.2: the safety section cites
    # 13849-2 (Validation), not -1.
    ref_std = f"{t('ref.iec62061', lang)} / {t('ref.iso13849_2', lang)}"
    for key in FAT_SAFETY_SCENARIOS:
        lines.append(
            f"| {counter.next_id()} | {t(key + '.scenario', lang)} "
            f"| {t(key + '.start', lang)} | {t(key + '.action', lang)} "
            f"| {t(key + '.expected', lang)} | {ref_std} | | ☐ |"
        )
    ref_proj = t("ref.project", lang)
    from_rd05 = t("fat.safety.rd05_from", lang)
    for note in safety_notes:
        row_label = t("fat.safety.rd05_row", lang, name=note)
        lines.append(
            f"| {counter.next_id()} | {row_label} | {from_rd05} "
            f"| {from_rd05} | {from_rd05} | {ref_proj} | | ☐ |"
        )
    return "\n".join(lines)


_ANALOG_BOUND_KEYS = (
    ("0", "fat.analog.b0"),
    ("6912", "fat.analog.b25"),
    ("13824", "fat.analog.b50"),
    ("27648", "fat.analog.b100"),
    ("27649", "fat.analog.bover"),
    ("-1", "fat.analog.bneg"),
    ("32767", "fat.analog.b32767"),
)


def _section_analog_boundary(signals: list[dict], counter: _Counter, lang: str, n: int) -> str:
    ai_signals = [s for s in signals if s.get("type") in ("AI", "AQ")]
    lines = [
        f"\n## {n}. {t('sec.analog', lang)}\n",
        f"> {t('intro.analog', lang)}\n",
    ]
    lines += _tbl_header(lang, [
        "col.no", "col.tag", "col.type", "col.test_value",
        "col.expected", "col.ref", "col.actual", "col.result",
    ])
    ref = t("ref.iec62381", lang)
    if not ai_signals:
        placeholder = t("fat.analog.no_ai_placeholder", lang)
        for val, key in _ANALOG_BOUND_KEYS:
            lines.append(
                f"| {counter.next_id()} | {placeholder} | AI | {val} "
                f"| {t(key, lang)} | {ref} | | ☐ |"
            )
    else:
        for sig in ai_signals[:10]:  # maximum 10 analog
            name = sig.get("name", "?")
            stype = sig.get("type", "AI")
            for val, key in _ANALOG_BOUND_KEYS:
                lines.append(
                    f"| {counter.next_id()} | `{name}` | {stype} | {val} "
                    f"| {t(key, lang)} | {ref} | | ☐ |"
                )
    return "\n".join(lines)


# State machine rows whose start/expected cells are state names (kept literal —
# IDLE/READY/FAULT etc. are identifiers in the SCL code, not prose).
_SM_LITERAL = {
    "fat.sm.t1": ("IDLE (0)", "HOMING (10) → READY (20)", None),
    "fat.sm.t2": ("HOMING (10)", None, "fat.sm.t2.expected"),
    "fat.sm.t3": ("CLAMPING (30)", None, "fat.sm.t3.expected"),
    "fat.sm.t4": ("MACHINING (50)", None, "fat.sm.t4.expected"),
    "fat.sm.t5": ("MACHINING (50)", "RETRACT (60)", None),
    "fat.sm.t6": ("UNCLAMPING (70)", None, "fat.sm.t6.expected"),
    "fat.sm.t7": ("FAULT (900)", "IDLE (0)", None),
    "fat.sm.t8": ("EMERGENCY (999)", "IDLE (0)", None),
    "fat.sm.t9": (None, None, "fat.sm.t9.expected"),
    "fat.sm.t10": ("APPROACH (40)", None, "fat.sm.t10.expected"),
}


def _section_state_machine(counter: _Counter, lang: str, n: int) -> str:
    lines = [
        f"\n## {n}. {t('sec.state_machine', lang)}\n",
        f"> {t('intro.state_machine', lang)}\n",
    ]
    lines += _tbl_header(lang, [
        "col.no", "col.test", "col.start_state", "col.action",
        "col.expected_state", "col.ref", "col.actual", "col.result",
    ])
    ref = t("ref.iec62381", lang)
    for prefix in FAT_SM_PREFIXES:
        start_lit, expected_lit, expected_key = _SM_LITERAL[prefix]
        start = start_lit if start_lit is not None else t(prefix + ".start", lang)
        expected = expected_lit if expected_lit is not None else t(expected_key, lang)
        lines.append(
            f"| {counter.next_id()} | {t(prefix + '.test', lang)} | {start} "
            f"| {t(prefix + '.action', lang)} | {expected} | {ref} | | ☐ |"
        )
    return "\n".join(lines)


_STRESS_REPEATS = ("10×", "100×", "5×", "3×", "3×", "5×", "1×", "1×", "3×", "5×")


def _section_stress(counter: _Counter, lang: str, n: int) -> str:
    lines = [
        f"\n## {n}. {t('sec.stress', lang)}\n",
        f"> {t('intro.stress', lang)}\n",
    ]
    lines += _tbl_header(lang, [
        "col.no", "col.scenario", "col.condition", "col.repeat",
        "col.expected", "col.ref", "col.result",
    ])
    ref = t("ref.iec62381", lang)
    for prefix, reps in zip(FAT_STRESS_PREFIXES, _STRESS_REPEATS):
        lines.append(
            f"| {counter.next_id()} | {t(prefix + '.scenario', lang)} "
            f"| {t(prefix + '.method', lang)} | {reps} "
            f"| {t(prefix + '.expected', lang)} | {ref} | ☐ |"
        )
    return "\n".join(lines)


def _section_plcsim_notes(lang: str, n: int) -> str:
    # The numbered tool steps and the API sample are tooling instructions
    # (TIA Portal / PLCSim UI terms) — kept in EN like the code itself.
    return f"""

## {n}. {t('sec.plcsim', lang)}

```
1. TIA Portal → PLCSim Advanced → New Simulation
2. Load PLC (Download to device)
3. Set CPU to RUN mode
4. Create Watch Table:
   - DB_Safety.xSafetyOK
   - DB_StateMachine.iCurrentState
   - DB_HMI.sHMI_StatusText
   - All DI/DQ addresses
5. For each test: Change value in Force Table → verify from Watch Table
6. Write result to table and take screenshot (attach to test report)
```

### PLCSim Python API (Optional Automation)

```python
# Using Siemens PLCSim Advanced Python API (v4+)
# pip install siemens-plcsim-advanced  (Siemens official package)
import siemens_plcsim_advanced as plcsim

sim = plcsim.open_or_create("Project_Test")
sim.start()

# Test T015: E-Stop
sim.write_bool("DB_Safety", "xEstopHW", False)   # NC opened
assert sim.read_bool("DB_Safety", "xSafetyOK") == False
assert sim.read_int("DB_Safety", "iSafetyFault") == 1
sim.write_bool("DB_Safety", "xEstopHW", True)    # Release

print("T015 PASSED")
```

> **Note:** PLCSim API test scripts should be saved under `REPORTS/gate_results/`.

"""


# ---- SAT sections (site acceptance — real plant, not a FAT copy) --------------

def _sat_section_loop_check(signals: list[dict], counter: _Counter, lang: str, n: int) -> str:
    lines = [
        f"\n## {n}. {t('sec.sat_loop_check', lang)}\n",
        f"> {t('intro.sat_loop_check', lang)}\n",
    ]
    if not signals:
        lines.append(f"> ⚠ {t('sat.loop.no_signals', lang)}\n")
        return "\n".join(lines)
    lines += _tbl_header(lang, [
        "col.no", "col.tag", "col.type", "col.address", "col.description",
        "col.expected", "col.ref", "col.actual", "col.result",
    ])
    ref = t("ref.iec62381", lang)
    row_key = {"DI": "sat.loop.row_di", "DQ": "sat.loop.row_do",
               "AI": "sat.loop.row_ai", "AQ": "sat.loop.row_ao"}
    exp_key = {"DI": "sat.loop.expected_di", "DQ": "sat.loop.expected_do",
               "AI": "sat.loop.expected_ai", "AQ": "sat.loop.expected_ao"}
    for sig in signals:
        name = sig.get("name", "?")
        stype = sig.get("type", "UNK")
        addr = sig.get("address", "—")
        rk = row_key.get(stype, "sat.loop.row_di")
        ek = exp_key.get(stype, "sat.loop.expected_di")
        desc = t(rk, lang, name=name)
        expected = t(ek, lang, addr=addr or name)
        lines.append(
            f"| {counter.next_id()} | `{name}` | {stype} | {addr} "
            f"| {desc} | {expected} | {ref} | | ☐ |"
        )
    return "\n".join(lines)


def _sat_rows(counter: _Counter, lang: str, rows: list[tuple[str, str, str]]) -> list[str]:
    """rows: (desc_key, expected_key, ref_key) → table lines."""
    out = []
    for desc_key, expected_key, ref_key in rows:
        out.append(
            f"| {counter.next_id()} | {t(desc_key, lang)} "
            f"| {t(expected_key, lang)} | {t(ref_key, lang)} | | ☐ |"
        )
    return out


def _sat_simple_section(counter: _Counter, lang: str, n: int, sec_key: str,
                        intro_key: str, rows: list[tuple[str, str, str]]) -> str:
    lines = [
        f"\n## {n}. {t(sec_key, lang)}\n",
        f"> {t(intro_key, lang)}\n",
    ]
    lines += _tbl_header(lang, [
        "col.no", "col.description", "col.expected", "col.ref",
        "col.actual", "col.result",
    ])
    lines += _sat_rows(counter, lang, rows)
    return "\n".join(lines)


def _sat_section_safety_chain(safety_notes: list[str], counter: _Counter,
                              lang: str, n: int) -> str:
    rows = [
        ("sat.safety.estop_real", "sat.safety.estop_real.expected", "ref.en60204_1"),
        ("sat.safety.door_real", "sat.safety.door_real.expected", "ref.iso13849_2"),
        ("sat.safety.wiring", "sat.safety.wiring.expected", "ref.iso13849_2"),
    ]
    lines = [
        f"\n## {n}. {t('sec.sat_safety_chain', lang)}\n",
        f"> {t('intro.sat_safety_chain', lang)}\n",
    ]
    lines += _tbl_header(lang, [
        "col.no", "col.description", "col.expected", "col.ref",
        "col.actual", "col.result",
    ])
    lines += _sat_rows(counter, lang, rows)
    ref_proj = t("ref.project", lang)
    from_rd05 = t("fat.safety.rd05_from", lang)
    for note in safety_notes:
        row_label = t("fat.safety.rd05_row", lang, name=note)
        lines.append(
            f"| {counter.next_id()} | {row_label} | {from_rd05} "
            f"| {ref_proj} | | ☐ |"
        )
    return "\n".join(lines)


def _sat_section_cybersecurity(counter: _Counter, lang: str, n: int) -> str:
    """IEC 62443 / NIS2 hardening checklist (Faz 3)."""
    rows = [(key, key + ".expected", "ref.iec62443") for key in SAT_CYBER_ROWS]
    return _sat_simple_section(
        counter, lang, n, "sec.sat_cybersecurity", "intro.sat_cybersecurity", rows,
    )


# ── Document assembly ─────────────────────────────────────────────────────────

def _read_platform(project_path: Path) -> str:
    state_file = project_path / "PROJECT_STATE.json"
    if state_file.exists():
        try:
            import json
            st = json.loads(state_file.read_text(encoding="utf-8"))
            return st.get("platform", "")
        except Exception:
            pass
    return ""


def _build_header(project_name: str, platform: str, test_type: str,
                  lang: str, ts_label: str) -> str:
    title = t("common.sat_title" if test_type == "SAT" else "common.fat_title", lang)
    return f"""\
# {title}
## {t('common.project', lang)}: {project_name}
**{t('common.date', lang)}:** {ts_label}
**{t('common.platform', lang)}:** {platform or "—"}
**{t('common.tested_by', lang)}:** _______________
**{t('common.facility', lang)}:** _______________

> {t('common.auto_generated', lang)}
> {t('common.fill_during_test', lang)}
> {t('common.safety_supervision', lang)}

---
"""


def _build_signature_section(counter: _Counter, lang: str, n: int,
                             test_type: str) -> str:
    handover = ""
    if test_type == "SAT":
        handover = f"""
### {t('common.handover_title', lang)}

| {t('common.subject', lang)} | {t('col.signature', lang)} / {t('col.date', lang)} |
|------|-------|
| {t('sat.backup.docs', lang)} | _______________ |
| {t('common.manufacturer_rep', lang)} | _______________ |
| {t('common.customer_rep', lang)} | _______________ |
"""
    return f"""\
## {n}. {t('common.signatures', lang)}

| {t('common.subject', lang)} | {t('common.value', lang)} |
|------|-------|
| {t('common.total_tests', lang)} | {counter.value} |
| {t('common.passed', lang)} | ___ |
| {t('common.remaining', lang)} | ___ |
| {t('common.remaining_note', lang)} | ___ |
{handover}
**{t('common.manufacturer_rep', lang)}:** _______________  {t('common.date', lang)}: ___________
**{t('common.customer_rep', lang)}:** _______________  {t('common.date', lang)}: ___________
**{t('common.tuv_rep', lang)}:** _____________  {t('common.date', lang)}: ___________

---
*AUTOMATION FACTORY v3 — fat_protocol.py | {t('common.date', lang)}: {{ts}}*
""".replace("{ts}", datetime.now().strftime("%Y-%m-%d %H:%M"))


# ── Main Function ─────────────────────────────────────────────────────────────

def run_fat_protocol(
    project_path: Path,
    output_dir: Optional[Path] = None,
    test_type: str = "FAT",
    lang: str = DEFAULT_LANG,
    pdf: bool = False,
) -> FatResult:
    """Generate one FAT *or* SAT protocol (use run_protocol_set for BOTH)."""
    test_type = (test_type or "FAT").upper()
    if test_type not in ("FAT", "SAT"):
        raise ValueError(
            f"run_fat_protocol: test_type must be FAT or SAT (got {test_type!r}); "
            "BOTH is handled by run_protocol_set."
        )
    lang = normalize_lang(lang)

    # Per-call counter — no shared mutable state, concurrent calls are isolated.
    counter = _Counter()
    result = FatResult(test_type=test_type, lang=lang)

    if not project_path.exists():
        # Log hygiene: warnings reach the GUI log — do not embed the real path.
        result.warnings.append("Project folder not found")
        return result

    # B-P5 / S-17: RD05 readiness gate — fail-closed.
    # Raises Rd05BlockedError (propagates to caller) if RD05 is absent,
    # empty, or template-only.  No FAT/SAT output is written in that case.
    check_rd05_ready(project_path)

    signals = _load_signals(project_path)
    if not signals:
        result.warnings.append("RD01 signals could not be read — IO test uses general placeholder.")

    safety_notes = _load_safety_notes(project_path)

    project_name = project_path.name
    ts_label = datetime.now().strftime("%Y-%m-%d %H:%M")
    ts_file  = datetime.now().strftime("%Y%m%d_%H%M")
    platform = _read_platform(project_path)

    body = _build_header(project_name, platform, test_type, lang, ts_label)

    # Faz 2.3 (user decision 2026-06-12: WARNING, not a blocker): RD05 defines
    # PLr values but matching sistema_records are missing → the protocol IS
    # produced, with a visible PENDING box up front.  Re-generating after the
    # engineer enters the records replaces the box with the real table.
    # Fake/placeholder report names are forbidden — the box lists function
    # names only.
    sistema_pending: list[str] = []
    try:
        from sistema_support import sistema_status
        sistema_pending = sistema_status(project_path)["pending"]
    except Exception as exc:  # status derivation must never block a protocol
        # Log hygiene: an exception message may carry the metadata/ path —
        # surface only the type, not the text.
        result.warnings.append(
            f"SISTEMA status check failed: {type(exc).__name__}")
    if sistema_pending:
        box = t("sistema.pending_box", lang)
        body += f"\n> ⚠ **{box}**\n>\n"
        for name in sistema_pending:
            body += f"> - ☐ {name}\n"
        body += "\n"
        result.warnings.append(
            f"SISTEMA verification PENDING for: {', '.join(sistema_pending)}"
        )

    if test_type == "FAT":
        alarms = _load_alarms(project_path)
        if not alarms:
            result.warnings.append(t("alarm.no_table_warning", lang))
        body += (
            _section_io(signals, counter, lang, 1)
            + _section_safety(safety_notes, counter, lang, 2)
            + _section_analog_boundary(signals, counter, lang, 3)
            + _section_state_machine(counter, lang, 4)
            + _section_stress(counter, lang, 5)
            + _section_alarm(alarms, counter, lang, 6)
            + _section_plcsim_notes(lang, 7)
        )
        sig_n = 8
    else:  # SAT — real plant scope
        body += (
            _sat_section_loop_check(signals, counter, lang, 1)
            + _sat_simple_section(
                counter, lang, 2, "sec.sat_motor_rotation",
                "intro.sat_motor_rotation", [
                    ("sat.motor.bump", "sat.motor.bump.expected", "ref.en60204_1"),
                    ("sat.motor.generic", "sat.motor.bump.expected", "ref.en60204_1"),
                ])
            + _sat_simple_section(
                counter, lang, 3, "sec.sat_sensor_alignment",
                "intro.sat_sensor_alignment", [
                    ("sat.sensor.limit", "sat.sensor.limit.expected", "ref.iec62381"),
                    ("sat.sensor.analog_cal", "sat.sensor.analog_cal.expected", "ref.iec62381"),
                ])
            + _sat_section_safety_chain(safety_notes, counter, lang, 4)
            + _sat_simple_section(
                counter, lang, 5, "sec.sat_drive_params",
                "intro.sat_drive_params", [
                    ("sat.drive.params", "sat.drive.params.expected", "ref.en60204_1"),
                    ("sat.drive.protection", "sat.drive.protection.expected", "ref.en60204_1"),
                ])
            + _sat_simple_section(
                counter, lang, 6, "sec.sat_network_hmi",
                "intro.sat_network_hmi", [
                    ("sat.net.topology", "sat.net.topology.expected", "ref.iec62381"),
                    ("sat.net.hmi_screens", "sat.net.hmi_screens.expected", "ref.iec62381"),
                    ("sat.net.interlock_chain", "sat.net.interlock_chain.expected", "ref.iec62381"),
                ])
            + _sat_section_cybersecurity(counter, lang, 7)
            + _sat_simple_section(
                counter, lang, 8, "sec.sat_backup_handover",
                "intro.sat_backup_handover", [
                    ("sat.backup.full", "sat.backup.full.expected", "ref.iec62381"),
                    ("sat.backup.restore", "sat.backup.restore.expected", "ref.iec62381"),
                    ("sat.backup.docs", "sat.backup.docs.expected", "ref.iec62381"),
                ])
        )
        sig_n = 9

    # Faz 2.4: delivery documents carry an explicit SISTEMA reference section
    # (records table, PENDING box, or "no PLr in RD05" note — never a silent
    # gap).  SAT is the delivery-facing protocol; FAT keeps the top box only.
    if test_type == "SAT":
        try:
            from sistema_support import render_sistema_section_md
            body += "\n" + render_sistema_section_md(project_path, lang) + "\n"
        except Exception as exc:
            result.warnings.append(f"SISTEMA section could not be rendered: {exc}")

    body += "\n" + _build_signature_section(counter, lang, sig_n, test_type)

    result.test_count = counter.value

    out_dir = output_dir or (project_path / "_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w\-]", "_", project_name)
    dest = out_dir / f"{test_type}_PROTOCOL_{safe_name}_{ts_file}.md"
    dest.write_text(body, encoding="utf-8")
    result.md_path = dest

    if pdf:
        try:
            from pdf_common import markdown_to_pdf
            title = t("common.sat_title" if test_type == "SAT" else "common.fat_title", lang)
            result.pdf_path = markdown_to_pdf(
                body, dest.with_suffix(".pdf"), f"{title} — {project_name}",
            )
        except Exception as exc:
            # Fail-safe: MD output remains valid; the PDF failure is loud.
            result.warnings.append(
                f"{t('status.pdf_failed', lang)} ({exc})"
            )

    if signals:
        result.warnings.append(f"IO source: RD01 ({len(signals)} signals)")
    if safety_notes:
        result.warnings.append(f"Included {len(safety_notes)} safety notes from RD05")

    return result


def run_protocol_set(
    project_path: Path,
    output_dir: Optional[Path] = None,
    test_type: str = "FAT",
    lang: str = DEFAULT_LANG,
    pdf: bool = False,
) -> list[FatResult]:
    """FAT, SAT or BOTH — BOTH produces two separate documents."""
    test_type = (test_type or "FAT").upper()
    if test_type == "BOTH":
        types = ("FAT", "SAT")
    elif test_type in ("FAT", "SAT"):
        types = (test_type,)
    else:
        raise ValueError(f"Unknown protocol type {test_type!r} — use FAT, SAT or BOTH.")
    return [
        run_fat_protocol(project_path, output_dir, tt, lang, pdf)
        for tt in types
    ]


def format_fat_summary(result: FatResult) -> str:
    lines = [f"📋 {result.test_type} Protocol Generation Summary", ""]
    if result.md_path:
        lines.append(f"  File       : {result.md_path.name}")
    if result.pdf_path:
        lines.append(f"  PDF        : {result.pdf_path.name}")
    lines.append(f"  Language   : {result.lang}")
    lines.append(f"  Total tests: {result.test_count}")
    if result.warnings:
        lines.append("")
        for w in result.warnings:
            lines.append(f"  ℹ️  {w}")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    force_utf8_stdout()
    import argparse
    p = argparse.ArgumentParser(description="FAT/SAT Test Protocol Generator")
    p.add_argument("--project", metavar="PROJECT_PATH", required=True)
    p.add_argument("--type", choices=["FAT", "SAT", "BOTH"], default="FAT")
    p.add_argument("--lang", choices=["de", "en", "tr"], default=DEFAULT_LANG)
    p.add_argument("--pdf", action="store_true", help="Also produce PDF")
    p.add_argument("--out",   metavar="FOLDER",     help="Output folder")
    args = p.parse_args()

    results = run_protocol_set(
        Path(args.project),
        output_dir=Path(args.out) if args.out else None,
        test_type=args.type,
        lang=args.lang,
        pdf=args.pdf,
    )
    for result in results:
        print(format_fat_summary(result))
        if result.md_path:
            # Log hygiene: name only, never the full customer path.
            print(f"\nProtocol: {result.md_path.name}")


if __name__ == "__main__":
    main()
