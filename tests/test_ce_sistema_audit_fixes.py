"""Proof tests for the 2026-06-13 night-audit fixes (müfettiş → dogrulayici).

Each test pins one verified finding so it cannot regress:
  BULGU-01  CE disclaimer present in ALL THREE languages, not just the chosen one
  BULGU-02  a corrupt PROJECT_STATE.json is NOT overwritten by a sistema write
  BULGU-03  nightly check FAILs a block whose compile reports errors
  BULGU-06  FAT IO section is kept (header + warning) when signals are empty
  BULGU-07  CE 'folder not found' error carries no filesystem path
  BULGU-10  protocol CLI summary prints file NAMES, not full paths
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import ce_assessment
import sistema_support
import nightly_tia_check as ntc
import fat_protocol
import script_protocol_generator as spg
from protocol_i18n import t, SUPPORTED_LANGS


# ---- BULGU-01: CE disclaimer in all three languages --------------------

def _mk_project(tmp_path: Path, ptype: str = "retrofit") -> Path:
    proj = tmp_path / "Proj"
    proj.mkdir()
    (proj / "PROJECT_STATE.json").write_text(
        json.dumps({"project_name": "X", "project_type": ptype}),
        encoding="utf-8")
    return proj


@pytest.mark.parametrize("lang", ["de", "en", "tr"])
def test_ce_disclaimer_is_trilingual_regardless_of_lang(tmp_path, lang):
    proj = _mk_project(tmp_path)
    res = ce_assessment.generate_ce_assessment(proj, lang=lang)
    body = res.md_path.read_text(encoding="utf-8")
    # The disclaimer text for every supported language must appear.
    for dl in SUPPORTED_LANGS:
        assert t("ce.disclaimer", dl) in body, f"missing {dl} disclaimer"


# ---- BULGU-07: no path leak in CE 'folder not found' -------------------

def test_ce_missing_folder_error_has_no_path(tmp_path):
    bogus = tmp_path / "customer_4711" / "secret"
    with pytest.raises(FileNotFoundError) as ei:
        ce_assessment.generate_ce_assessment(bogus)
    msg = str(ei.value)
    assert "customer_4711" not in msg and "secret" not in msg
    assert str(bogus) not in msg


# ---- BULGU-02: corrupt state must not be clobbered ---------------------

def test_corrupt_state_is_not_overwritten_on_sistema_write(tmp_path):
    proj = tmp_path / "Proj"
    proj.mkdir()
    corrupt = '{ this is not valid json '
    sp = proj / "PROJECT_STATE.json"
    sp.write_text(corrupt, encoding="utf-8")
    with pytest.raises(ValueError):
        sistema_support.add_sistema_record(
            proj, "EStop", engineer="Eng")
    # The corrupt file is untouched — no silent data loss.
    assert sp.read_text(encoding="utf-8") == corrupt


def test_valid_state_keys_survive_sistema_write(tmp_path):
    proj = tmp_path / "Proj"
    proj.mkdir()
    (proj / "PROJECT_STATE.json").write_text(
        json.dumps({"gate6_approved": True, "platform": "S7_1500"}),
        encoding="utf-8")
    sistema_support.add_sistema_record(proj, "EStop", engineer="Eng")
    state = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    assert state["gate6_approved"] is True
    assert state["platform"] == "S7_1500"
    assert len(state["sistema_records"]) == 1


def test_corrupt_state_reader_is_tolerant_not_raising(tmp_path):
    # Regression: json.JSONDecodeError IS a ValueError. The tolerant (reader)
    # path must NOT re-raise it — sistema_status/load_sistema_records would
    # otherwise crash on a corrupt PROJECT_STATE instead of degrading to empty.
    proj = tmp_path / "Proj"
    proj.mkdir()
    (proj / "PROJECT_STATE.json").write_text("{ broken json", encoding="utf-8")
    assert sistema_support._read_state(proj) == {}            # no raise
    assert sistema_support.load_sistema_records(proj) == []   # no raise
    assert sistema_support.sistema_status(proj)["records"] == []


# ---- BULGU-06: FAT IO section kept when signals empty ------------------

def test_fat_io_section_kept_when_no_signals():
    md = fat_protocol._section_io([], fat_protocol._Counter(), "en", 1)
    assert md.strip() != ""
    assert "1." in md                          # section number present
    assert t("fat.io.no_signals", "en") in md  # explicit warning, not silent


# ---- E2E gap: IEC 62682 must reach the GUI-facing FAT (fat_protocol) ----

def _mk_fat_project(tmp_path: Path, rd08: str) -> Path:
    proj = tmp_path / "ProjFAT"
    meta = proj / "metadata"
    meta.mkdir(parents=True)
    (proj / "PROJECT_STATE.json").write_text(
        json.dumps({"project_name": "P", "project_type": "retrofit",
                    # AUDIT-004b: banner blocks without a recorded review
                    "rd_verifications": {"RD05": {"reviewed": True}}}),
        encoding="utf-8")
    (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
        "# RD05\n| Func | Desc | PLr |\n|---|---|---|\n| EStop | E | d |\n",
        encoding="utf-8")
    (meta / "RD01_IO_List.md").write_text(
        "| Tag | Address | Type |\n|---|---|---|\n| xStart | %I0.0 | DI |\n",
        encoding="utf-8")
    (meta / "RD08_Alarm.md").write_text(rd08, encoding="utf-8")
    return proj


@pytest.mark.parametrize("lang", ["de", "en", "tr"])
def test_fat_carries_iec62682_alarm_section(tmp_path, lang):
    proj = _mk_fat_project(
        tmp_path,
        "| Alarm | Tag | Priority | Response | Class |\n"
        "|---|---|---|---|---|\n"
        "| Motor overload | xOvl | high | stop | safety |\n")
    res = fat_protocol.run_fat_protocol(proj, None, "FAT", lang, False)
    body = res.md_path.read_text(encoding="utf-8")
    assert "62682" in body          # GUI generator now carries Faz 5
    assert "high" in body and "safety" in body


def test_fat_alarm_missing_fields_not_invented(tmp_path):
    proj = _mk_fat_project(
        tmp_path,
        "| Alarm | Tag |\n|---|---|\n| Motor overload | xOvl |\n")
    res = fat_protocol.run_fat_protocol(proj, None, "FAT", "en", False)
    body = res.md_path.read_text(encoding="utf-8")
    assert "62682" in body
    assert "—" in body                       # missing priority/response/class
    assert t("alarm62682.fill_instruction", "en") in body


# ---- BULGU-10: CLI summaries print names, not paths --------------------

def test_protocol_summary_prints_name_not_path():
    class _R:
        test_type = "FAT"
        project_name = "X"; lang = "de"
        items = []; precheck_items = []; io_items = []
        function_items = []; alarm_items = []
        md_path = Path("/customer/secret/Proj/_output/FAT.md")
        xlsx_path = None; pdf_path = None; warnings = []
    out = spg.format_protocol_summary(_R())
    assert "FAT.md" in out
    assert "secret" not in out and "/customer/" not in out


# ---- BULGU-03: nightly fails a block with compile errors ---------------

class _FakeImport:
    def __init__(self, generated, failed):
        self.blocks_generated = generated
        self.failed = failed


class _FakeMsg:
    def __init__(self, severity, block):
        self.severity = severity; self.text = "err"; self.block = block


class _FakeCompile:
    def __init__(self, errors, messages):
        self.errors = errors; self.messages = messages


class _FakeCore:
    def __init__(self, names, bad_block):
        self._names = names; self._bad = bad_block
    def start_portal(self, with_ui=False): pass
    def open_project(self, p): return object()
    def find_plc(self, proj, name): return (object(), object())
    def import_scl_files(self, plc, blocks, skip_safety=True):
        return _FakeImport(list(self._names), [])
    def compile_plc(self, plc):
        return _FakeCompile(1, [_FakeMsg("Error", self._bad)])
    def stop_portal(self): pass


class _FakeBridge:
    def __init__(self, core): self._core = core
    def _get_core(self): return self._core


def test_nightly_fails_block_with_compile_error(tmp_path, monkeypatch):
    names = [p.stem for p in ntc.resolve_blocks()]
    bad = names[0]
    core = _FakeCore(names, bad)
    monkeypatch.setattr(ntc, "_load_tia_bridge", lambda: _FakeBridge(core))
    proj = tmp_path / "Scratch.ap19"
    proj.write_text("stub", encoding="utf-8")
    lines: list[str] = []
    rc = ntc.run_full(proj, out=lines.append)
    out = "\n".join(lines)
    assert rc == 1
    assert f"[FAIL] {bad}" in out
    assert "(compile)" in out


def test_nightly_all_pass_when_no_compile_errors(tmp_path, monkeypatch):
    names = [p.stem for p in ntc.resolve_blocks()]
    core = _FakeCore(names, bad_block="")          # no error message
    core.compile_plc = lambda plc: _FakeCompile(0, [])
    monkeypatch.setattr(ntc, "_load_tia_bridge", lambda: _FakeBridge(core))
    proj = tmp_path / "Scratch.ap19"
    proj.write_text("stub", encoding="utf-8")
    lines: list[str] = []
    rc = ntc.run_full(proj, out=lines.append)
    assert rc == 0
    assert "NIGHTLY TIA OK" in "\n".join(lines)
