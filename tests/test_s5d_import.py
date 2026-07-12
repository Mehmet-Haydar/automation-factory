"""Proof tests — s5d_import pure rendering layer (no .NET required).

Pins the conversion rules proven by the 2026-07-06 parity spike:
German→English mnemonics (incl. the treacherous SV→SE / SE→SD timer
pair), operand-area mapping, KT recovery from row MC5 bytes (0x3002,
BCD — refused when not BCD), KM binary formatting, S5W network framing,
and the fail-honest handling of unknown mnemonics.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from s5d_import import (  # noqa: E402
    S5Row, decode_kt, render_block, render_parameter, render_row,
)


# ------------------------------------------------------------------ KT ----

def test_decode_kt_known_values():
    assert decode_kt(bytes.fromhex("30020050")) == "050.0"
    assert decode_kt(bytes.fromhex("30021020")) == "020.1"
    assert decode_kt(bytes.fromhex("30020800")) == "800.0"
    assert decode_kt(bytes.fromhex("30021005")) == "005.1"


def test_decode_kt_refuses_non_bcd_and_wrong_opcode():
    assert decode_kt(bytes.fromhex("30020ABC")) is None, "BCD dışı → red"
    assert decode_kt(bytes.fromhex("31020050")) is None, "yanlış opcode"
    assert decode_kt(b"\x30\x02") is None, "eksik operand"


def test_bare_kt_without_bytes_keeps_bare_and_warns():
    lines, warn = render_row(S5Row("L", "KT"))
    assert lines == ["\tL\tKT"] and "not recoverable" in warn


def test_kt_filled_from_row_bytes():
    lines, warn = render_row(S5Row("L", "KT", mc5=bytes.fromhex("30020050")))
    assert lines == ["\tL\tKT 050.0"] and warn == ""


# ------------------------------------------------------- dialect mapping --

def test_timer_mnemonic_pair_sv_se_sd():
    """German SV == English SE; German SE == English SD — swapping these
    would silently change timer semantics in the imported program."""
    assert render_row(S5Row("SV", "T 1"))[0] == ["\tSE\tT 1"]
    assert render_row(S5Row("SE", "T 2"))[0] == ["\tSD\tT 2"]


def test_operand_area_letters():
    assert render_parameter("E 6.7") == "I 6.7"
    assert render_parameter("A 29.2") == "Q 29.2"
    assert render_parameter("M 1.0") == "F 1.0"
    assert render_parameter("Z 1") == "C 1"
    assert render_parameter("MW 111") == "FW 111"
    assert render_parameter("PW 13") == "PW 13"      # unchanged
    assert render_parameter("PB 53") == "PB 53"      # call target unchanged


def test_km_constant_binary_format():
    assert render_parameter("KM -256") == "KM 11111111 00000000"
    assert render_parameter("KM 5") == "KM 00000000 00000101"


def test_unknown_mnemonic_stays_visible():
    lines, warn = render_row(S5Row("XYZ", "M 1.0"))
    assert lines == ["\t?XYZ?\tM 1.0"] and "unknown mnemonic" in warn


def test_bld_rows_dropped():
    assert render_row(S5Row("BLD", "255")) == ([], "")


# ------------------------------------------------------------- framing ----

def test_render_block_s5w_framing():
    nets = [
        [S5Row("BLD", "255")],                          # empty network
        [S5Row("U", "E 0.0"), S5Row("S", "M 1.0"),
         S5Row("NOP0", "")],
        [S5Row("U", "M 1.0", label="M001"),
         S5Row("=", "A 2.0"), S5Row("BE", "")],
    ]
    text, warns = render_block("PB9", nets)
    assert warns == []
    assert text == (
        "###PG:82000000\n"
        "[1\t\n"
        "\t***\t]\n"
        "[2\t\n"
        "\tA\tI 0.0\n"
        "\tS\tF 1.0\n"
        "\tNOP\t0\n"
        "\t***\t]\n"
        "[3\t\n"
        "M001:\tA\tF 1.0\n"
        "\t=\tQ 2.0\n"
        "\tBE\t]\n"
    )


def test_rendered_block_parses_in_existing_extractor():
    """The whole point: the extractor must consume the rendered dialect
    without any changes — proven S/R extraction on a rendered latch."""
    from s5_logic_extract import extract_project_logic

    nets = [
        [S5Row("U", "E 0.0"), S5Row("U", "M 8.0"), S5Row("S", "M 1.0"),
         S5Row("U", "M 1.1"), S5Row("R", "M 1.0"), S5Row("BE", "")],
    ]
    text, _ = render_block("PB9", nets)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        legacy = Path(td) / "_raw" / "legacy_code"
        legacy.mkdir(parents=True)
        (legacy / "PB9.AWL").write_text(text, encoding="utf-8")
        parsed = extract_project_logic(Path(td))
    assert len(parsed) == 1 and parsed[0].parsed, \
        "render edilen AWL mevcut extractor'da kanıtlı çözülmeli"
    assert "M1.0" in parsed[0].coils


# ------------------------------------------------------- backend endpoint --

def test_endpoint_requires_project_and_valid_file(tmp_path, monkeypatch):
    import factory_web
    api = factory_web.Api()
    api.root = None
    assert not api.import_s5d(str(tmp_path / "x.s5d"))["ok"]

    api.root = tmp_path
    r = api.import_s5d(str(tmp_path / "missing.s5d"))
    assert not r["ok"] and ".s5d" in r["msg"]


def test_import_refuses_clearly_when_toolbox_missing(tmp_path, monkeypatch):
    """DLL'ler yoksa kullanıcıya eyleme dönüştürülebilir mesaj: fetch script."""
    import s5d_import
    monkeypatch.setattr(s5d_import, "TOOLBOX_DIR", tmp_path / "nope")
    fake = tmp_path / "m.s5d"
    fake.write_bytes(b"\x00" * 16)
    import pytest
    with pytest.raises(RuntimeError, match="fetch_s5d_toolbox"):
        s5d_import.import_s5d(fake, tmp_path / "out")


# ------------------------------------------- duplicate block versions ----
# E2E #2 finding (mixer-line test machine): the .s5d carried FB6 four times and the
# importer silently let the LAST version win. Contract now: richest version
# (most networks; tie -> last seen) is kept, a warning names the discard,
# blocks_written stays unique and the network counter counts kept blocks only.

class _FakeRow:
    def __init__(self, cmd, par):
        self.Command, self.Parameter, self.Label, self.MC5 = cmd, par, "", None


class _FakeNet:
    def __init__(self, rows):
        self.AWLCode = rows


class _FakeBlock:
    def __init__(self, nets):
        self.Networks = nets


class _FakeInfo:
    def __init__(self, name):
        self.BlockName = name


def _fake_net(operand):
    return _FakeNet([_FakeRow("U", operand), _FakeRow("=", "A 0.0"),
                     _FakeRow("BE", "")])


def _make_fake_projects(blocks):
    """blocks: list of (name, FakeBlock) in BlockInfos order."""
    infos = [_FakeInfo(n) for n, _ in blocks]

    class _Folder:
        BlockInfos = infos
        _by_info = dict(zip(infos, (b for _, b in blocks)))

        def GetBlock(self, info):
            return self._by_info[info]

    class _Structure:
        BlocksFolder = _Folder()

    class _Project:
        ProjectStructure = _Structure()

    class _Projects:
        @staticmethod
        def LoadProject(path, flag):
            return _Project()

    return _Projects


def test_duplicate_block_versions_keep_richest_and_warn(tmp_path, monkeypatch):
    import s5d_import
    monkeypatch.setattr(s5d_import, "toolbox_available", lambda: True)
    blocks = [
        ("FB6", _FakeBlock([_fake_net("E 1.0"), _fake_net("E 1.1")])),  # 2 nets
        ("PB1", _FakeBlock([_fake_net("E 5.0")])),
        ("FB6", _FakeBlock([_fake_net("E 2.0")])),                      # poorer
        ("FB6", _FakeBlock([_fake_net("E 3.0"), _fake_net("E 3.1")])),  # tie->last
    ]
    monkeypatch.setattr(s5d_import, "_load_projects_class",
                        lambda: _make_fake_projects(blocks))
    src = tmp_path / "m.s5d"
    src.write_bytes(b"\x00" * 16)
    summ = s5d_import.import_s5d(src, tmp_path / "out")

    assert summ.blocks_written == ["FB6", "PB1"], "unique, first-seen order"
    assert summ.networks == 3, "kept blocks only: FB6(2) + PB1(1)"
    dup_warns = [w for w in summ.warnings if "versions inside" in w]
    assert dup_warns == ["FB6: 3 versions inside the .s5d — kept the richest "
                         "(2 networks), discarded the rest"]
    text = (tmp_path / "out" / "FB6.AWL").read_text(encoding="utf-8")
    assert "I 3.0" in text and "I 1.0" not in text, \
        "tie between equal-richness versions must keep the LAST one"
    assert "I 2.0" not in text, "poorer version must never overwrite"
