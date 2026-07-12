"""SISTEMA support proof tests.

Principle under test: the software reminds and documents; the engineer
calculates and signs.  NO automatic PL calculation.

- prep list: produced from RD05 (with PLr → values shown; without PLr →
  document STILL produced with a visible warning — silent empty forbidden);
  no RD05 at all → loud SistemaInputError.
- records: engineer declarations in PROJECT_STATE.sistema_records
  (function+engineer mandatory), add/load/delete round-trip.
- status: pending = PLr functions without a record.
- FAT/SAT integration: pending → visible PENDING box, protocol still
  produced (WARNING, not a blocker — user decision 2026-06-12); after the
  record is entered the box disappears and the SAT carries the records
  table.  No fake/placeholder report names anywhere.
- customer_report MD fallback carries the SISTEMA section (regression).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from sistema_support import (
    SistemaInputError, add_sistema_record, delete_sistema_record,
    generate_sistema_prep, load_sistema_records, parse_rd05_safety_functions,
    render_sistema_section_md, sistema_status,
)
from fat_protocol import run_fat_protocol


RD05_WITH_PLR = (
    "# RD05\n"
    "| Funktion | Beschreibung | PLr |\n"
    "|---|---|---|\n"
    "| EStop_Main | Emergency stop chain | d |\n"
    "| DoorInterlock | Guard door circuit | PL c |\n"
)

RD05_WITHOUT_PLR = (
    "# RD05\n"
    "| Func | Desc |\n"
    "|---|---|\n"
    "| EStop_Main | Emergency stop |\n"
    "| DoorInterlock | Door circuit |\n"
)


def _mk_project(tmp_path: Path, rd05_text: str = RD05_WITH_PLR) -> Path:
    proj = tmp_path / "Proj_SISTEMA"
    meta = proj / "metadata"
    meta.mkdir(parents=True)
    (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(rd05_text, encoding="utf-8")
    # AUDIT-004b: the banner now blocks without a recorded engineer review
    import json as _json
    (proj / "PROJECT_STATE.json").write_text(_json.dumps({
        "rd_verifications": {"RD05": {"reviewed": True}}}), encoding="utf-8")
    (meta / "RD01_IO_List.md").write_text(
        "| Tag | Address | Type |\n|---|---|---|\n"
        "| xEstopMain | %I0.0 | DI |\n"
        "| xDoorClosed | %I0.1 | DI |\n",
        encoding="utf-8",
    )
    return proj


# ===========================================================================
# Group A — RD05 parsing
# ===========================================================================


class TestParseRd05:
    def test_functions_with_plr_extracted(self, tmp_path):
        proj = _mk_project(tmp_path)
        funcs = parse_rd05_safety_functions(proj)
        by_name = {f["function"]: f for f in funcs}
        assert by_name["EStop_Main"]["plr"] == "d"
        assert by_name["DoorInterlock"]["plr"] == "c"

    def test_signal_matching_from_rd01(self, tmp_path):
        proj = _mk_project(tmp_path)
        funcs = parse_rd05_safety_functions(proj)
        estop = next(f for f in funcs if f["function"] == "EStop_Main")
        assert "xEstopMain" in estop["signals"]

    def test_no_rd05_raises_loud(self, tmp_path):
        proj = tmp_path / "empty"
        (proj / "metadata").mkdir(parents=True)
        with pytest.raises(SistemaInputError):
            parse_rd05_safety_functions(proj)


# ===========================================================================
# Group B — prep document
# ===========================================================================


class TestPrepDocument:
    def test_prep_with_plr(self, tmp_path):
        proj = _mk_project(tmp_path)
        r = generate_sistema_prep(proj, lang="de")
        assert r.ok
        text = r.md_path.read_text(encoding="utf-8")
        assert "SISTEMA-Vorbereitungsliste" in text
        assert "EStop_Main" in text and "| d |" in text
        # no-PLr warning must NOT appear when PLr is present
        assert "KEINE PLr-Angabe" not in text

    def test_prep_without_plr_still_produced_with_warning(self, tmp_path):
        """Silent empty list forbidden — doc produced WITH warning block."""
        proj = _mk_project(tmp_path, RD05_WITHOUT_PLR)
        r = generate_sistema_prep(proj, lang="en")
        assert r.ok, "document must still be produced"
        text = r.md_path.read_text(encoding="utf-8")
        assert "NO PLr information was found in RD05" in text
        assert r.warnings, "warning must also be returned to the caller"

    def test_prep_three_languages(self, tmp_path):
        proj = _mk_project(tmp_path)
        for lang, marker in [
            ("de", "Aufgabe des"), ("en", "engineer's"), ("tr", "mühendisinin"),
        ]:
            r = generate_sistema_prep(proj, lang=lang)
            assert marker in r.md_path.read_text(encoding="utf-8"), lang

    def test_no_automatic_pl_calculation(self, tmp_path):
        """The achieved-PL column must be an empty fill-in field — the
        software must never compute or prefill it."""
        proj = _mk_project(tmp_path)
        text = generate_sistema_prep(proj, lang="en").md_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("| EStop_Main"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                assert cells[3] == "______", "achieved PL must be a fill-in blank"


# ===========================================================================
# Group C — records CRUD (engineer declarations)
# ===========================================================================


class TestRecords:
    def test_add_load_delete_roundtrip(self, tmp_path):
        proj = _mk_project(tmp_path)
        rec = add_sistema_record(
            proj, "EStop_Main", file="estop_main.ssm",
            achieved_pl="PL d", engineer="M. Engineer",
        )
        assert rec["achieved_pl"] == "d"
        assert rec["date"]
        records = load_sistema_records(proj)
        assert len(records) == 1
        assert records[0]["function"] == "EStop_Main"
        # persisted in PROJECT_STATE.json
        st = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        assert st["sistema_records"][0]["engineer"] == "M. Engineer"
        assert delete_sistema_record(proj, 0) is True
        assert load_sistema_records(proj) == []

    def test_engineer_mandatory(self, tmp_path):
        proj = _mk_project(tmp_path)
        with pytest.raises(ValueError):
            add_sistema_record(proj, "EStop_Main", engineer="")

    def test_function_mandatory(self, tmp_path):
        proj = _mk_project(tmp_path)
        with pytest.raises(ValueError):
            add_sistema_record(proj, "", engineer="M. Engineer")

    def test_delete_out_of_range_returns_false(self, tmp_path):
        proj = _mk_project(tmp_path)
        assert delete_sistema_record(proj, 5) is False


# ===========================================================================
# Group D — status + FAT/SAT integration (WARNING, not blocker)
# ===========================================================================


class TestProtocolIntegration:
    def test_pending_detected(self, tmp_path):
        proj = _mk_project(tmp_path)
        status = sistema_status(proj)
        assert status["rd05_has_plr"] is True
        assert set(status["pending"]) == {"EStop_Main", "DoorInterlock"}

    def test_record_clears_pending(self, tmp_path):
        proj = _mk_project(tmp_path)
        add_sistema_record(proj, "EStop_Main", engineer="M. Engineer",
                           achieved_pl="d", file="estop.ssm")
        status = sistema_status(proj)
        assert status["pending"] == ["DoorInterlock"]

    def test_fat_produced_with_pending_box(self, tmp_path):
        """User decision 2026-06-12: WARNING, not a blocker — the protocol
        IS produced, with a visible PENDING box."""
        proj = _mk_project(tmp_path)
        r = run_fat_protocol(proj, tmp_path / "out", lang="en")
        assert r.ok, "protocol must be produced despite pending SISTEMA"
        text = r.md_path.read_text(encoding="utf-8")
        assert "SISTEMA verification: PENDING" in text
        assert "EStop_Main" in text
        assert any("SISTEMA" in w for w in r.warnings)

    def test_no_fake_report_names(self, tmp_path):
        """A file name must never be invented — pending box lists function
        names only; the records table shows only engineer-entered names."""
        proj = _mk_project(tmp_path)
        text = run_fat_protocol(proj, tmp_path / "out", lang="en").md_path.read_text(
            encoding="utf-8")
        assert ".ssm" not in text and ".pdf" not in text.split("```")[0].replace(
            "PDF", ""), "no placeholder SISTEMA file names may appear"

    def test_sat_carries_records_table_after_entry(self, tmp_path):
        proj = _mk_project(tmp_path)
        add_sistema_record(proj, "EStop_Main", engineer="M. Engineer",
                           achieved_pl="d", file="estop_main.ssm")
        add_sistema_record(proj, "DoorInterlock", engineer="M. Engineer",
                           achieved_pl="c", file="door.ssm")
        r = run_fat_protocol(proj, tmp_path / "out", test_type="SAT", lang="en")
        text = r.md_path.read_text(encoding="utf-8")
        assert "SISTEMA verification: PENDING" not in text, (
            "pending box must disappear once records exist")
        assert "SISTEMA Calculation (Performance Level Evidence)" in text
        assert "estop_main.ssm" in text
        assert "M. Engineer" in text

    def test_no_plr_rd05_keeps_protocol_clean_but_honest(self, tmp_path):
        proj = _mk_project(tmp_path, RD05_WITHOUT_PLR)
        r = run_fat_protocol(proj, tmp_path / "out", test_type="SAT", lang="en")
        text = r.md_path.read_text(encoding="utf-8")
        assert "SISTEMA verification: PENDING" not in text
        assert "RD05 contains no PLr information" in text, (
            "status must be explicit — silent gap forbidden")

    def test_render_section_pending_box(self, tmp_path):
        proj = _mk_project(tmp_path)
        md = render_sistema_section_md(proj, lang="en")
        assert "PENDING" in md
        assert "EStop_Main" in md


# ===========================================================================
# Group E — customer_report MD fallback regression
# ===========================================================================


class TestCustomerReportSection:
    def test_md_fallback_contains_sistema_section(self, tmp_path):
        import customer_report as cr
        proj = _mk_project(tmp_path)
        dest = tmp_path / "report.md"
        sections = cr._generate_md(proj, {}, dest)
        assert "SISTEMA Calculation" in sections
        text = dest.read_text(encoding="utf-8")
        assert "SISTEMA Calculation (Performance Level Evidence)" in text
        assert "PENDING" in text  # both functions still open


# ---------------------------------------------------------------------------
# factory_web._state_lock race condition fix (B5) — taşındı: test_sistema_lock.py
# ---------------------------------------------------------------------------

import ast as _ast
import threading as _threading
from unittest.mock import MagicMock as _MagicMock

import factory_web as _fw_lock
from factory_web import Api as _LockApi

_LOCK_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "05_SCRIPTS"

_LOCK_RD05 = (
    "# RD05\n"
    "| Funktion | Beschreibung | PLr |\n"
    "|---|---|---|\n"
    "| EStop_Main | Emergency stop chain | d |\n"
    "| DoorInterlock | Guard door circuit | PL c |\n"
)


def _mk_lock_project(tmp_path: Path) -> Path:
    proj = tmp_path / "Proj_Lock"
    meta = proj / "metadata"
    meta.mkdir(parents=True)
    (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(_LOCK_RD05, encoding="utf-8")
    import json as _json
    (proj / "PROJECT_STATE.json").write_text(_json.dumps({
        "rd_verifications": {"RD05": {"reviewed": True}}}), encoding="utf-8")
    (meta / "RD01_IO_List.md").write_text(
        "| Tag | Address | Type |\n|---|---|---|\n| xEstopMain | %I0.0 | DI |\n",
        encoding="utf-8",
    )
    return proj


def _mk_lock_api(root: Path) -> _LockApi:
    api = object.__new__(_LockApi)
    api.settings = {}
    api.root = root
    return api


class TestStaticLockPresence:
    """factory_web.py kaynak kodunda add/delete_sistema_record'un _state_lock ile
    korunduğunu statik AST taramasıyla doğrular (B5 fix proof)."""

    FACTORY_WEB = _LOCK_SCRIPTS_DIR / "factory_web.py"

    def _get_method_body_lines(self, method_name: str) -> list:
        source = self.FACTORY_WEB.read_text(encoding="utf-8")
        lines = source.splitlines()
        in_method = False
        method_lines: list = []
        indent_level = None
        for line in lines:
            stripped = line.lstrip()
            if not in_method:
                if f"def {method_name}(" in line and "self" in line:
                    in_method = True
                    indent_level = len(line) - len(stripped)
                    method_lines.append(line)
            else:
                current_indent = len(line) - len(line.lstrip())
                if stripped and current_indent <= indent_level:
                    break
                method_lines.append(line)
        return method_lines

    def test_add_sistema_record_uses_state_lock(self):
        body = "\n".join(self._get_method_body_lines("add_sistema_record"))
        assert "with self._state_lock" in body, (
            "Api.add_sistema_record must wrap the call in 'with self._state_lock' — "
            "B5 fix geri alınmış."
        )

    def test_delete_sistema_record_uses_state_lock(self):
        body = "\n".join(self._get_method_body_lines("delete_sistema_record"))
        assert "with self._state_lock" in body, (
            "Api.delete_sistema_record must wrap the call in 'with self._state_lock' — "
            "B5 fix geri alınmış."
        )

    def test_no_separate_module_level_lock_in_sistema_support(self):
        source = (_LOCK_SCRIPTS_DIR / "sistema_support.py").read_text(encoding="utf-8")
        has_lock_import = "import threading" in source
        has_lock_instance = "threading.Lock()" in source
        assert not (has_lock_import and has_lock_instance), (
            "sistema_support.py must NOT have its own threading.Lock — "
            "factory_web._state_lock is the single serialisation point."
        )


class TestConcurrentSistemaWrites:
    """Eşzamanlı add_sistema_record çağrıları veri kaybetmemeli (B5 proof)."""

    def test_concurrent_add_no_data_loss(self, tmp_path):
        proj = _mk_lock_project(tmp_path)
        api = _mk_lock_api(proj)
        N_THREADS, M_PER_THREAD = 4, 3
        errors: list = []

        def worker(tid: int) -> None:
            for i in range(M_PER_THREAD):
                r = api.add_sistema_record(
                    function=f"SF_{tid}_{i}", file=f"t{tid}_{i}.ssm",
                    achieved_pl="d", engineer=f"Eng_{tid}",
                )
                if not r.get("ok"):
                    errors.append(f"thread={tid} i={i}: {r.get('msg')}")

        threads = [_threading.Thread(target=worker, args=(t,)) for t in range(N_THREADS)]
        for th in threads: th.start()
        for th in threads: th.join()

        assert not errors, f"Bazı çağrılar başarısız: {errors}"
        import json as _json
        state = _json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        records = state.get("sistema_records", [])
        assert len(records) == N_THREADS * M_PER_THREAD, (
            f"Beklenen {N_THREADS * M_PER_THREAD} kayıt, bulunan {len(records)} — race condition."
        )

    def test_concurrent_add_then_delete_consistent(self, tmp_path):
        import json as _json
        proj = _mk_lock_project(tmp_path)
        api = _mk_lock_api(proj)
        for i in range(6):
            api.add_sistema_record(function=f"SF_{i}", engineer="Setup_Eng",
                                   achieved_pl="c", file=f"sf_{i}.ssm")
        errors: list = []

        def adder() -> None:
            for i in range(3):
                r = api.add_sistema_record(function=f"NewSF_{i}", engineer="Adder_Eng")
                if not r.get("ok"): errors.append(f"add {i}: {r.get('msg')}")

        def deleter() -> None:
            for _ in range(2): api.delete_sistema_record(0)

        t1 = _threading.Thread(target=adder)
        t2 = _threading.Thread(target=deleter)
        t1.start(); t2.start()
        t1.join(); t2.join()

        raw = (proj / "PROJECT_STATE.json").read_text(encoding="utf-8")
        try:
            state = _json.loads(raw)
        except _json.JSONDecodeError as exc:
            pytest.fail(f"PROJECT_STATE.json corrupt oldu: {exc}")
        records = state.get("sistema_records", [])
        assert all(isinstance(r, dict) for r in records), (
            "sistema_records içinde geçersiz eleman var — race condition."
        )
