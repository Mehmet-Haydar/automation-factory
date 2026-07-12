"""G-05 proof — STEP 5 .ini / .seq legacy files are recognised as S5 source.

Before G-05 the platform detector ignored the two STEP 5 export formats a
retrofit engineer most often receives:
  - .ini  → symbol table / Zuordnungsliste
  - .seq  → sequence export / zone program

Each test fails if the fix is reverted (extension maps removed, role/kind
mappings dropped, or the S5 address-format content pattern deleted).
"""

from __future__ import annotations

import importlib

import platform_detector as pd


class TestExtensionMapping:
    def test_ini_and_seq_map_to_s5(self):
        assert pd.EXT_TO_PLATFORMS.get(".ini") == ["S5"]
        assert pd.EXT_TO_PLATFORMS.get(".seq") == ["S5"]

    def test_detect_from_filename(self):
        assert "S5" in pd.detect_platform_from_filename("4711Z0.SEQ")
        assert "S5" in pd.detect_platform_from_filename("symbols.ini")


class TestFileRole:
    def test_seq_is_source_code(self):
        assert pd.categorize_file_role("4711Z0.seq", ".seq") == "source_code"

    def test_ini_is_config(self):
        assert pd.categorize_file_role("symbols.ini", ".ini") == "config"


class TestContentDetection:
    def test_s5_address_format_detected(self, tmp_path):
        # A .seq body with S5 operand addresses (E 4.0 / A 28.0) must read as S5
        f = tmp_path / "zone.seq"
        f.write_bytes(
            b"\tE    4.0\tE 4.0\tMOTOR EIN\r\n"
            b"\tA   28.0\tA 28.0\tHYDR PUMPE\r\n"
            b"\tM    1.0\tM 1.0\tMERKER\r\n"
        )
        assert "S5" in pd.detect_platform_from_content(f)

    def test_program_block_reference_detected(self, tmp_path):
        f = tmp_path / "prog.seq"
        f.write_bytes(b"PB 1\r\nPB 11\r\nSPB FB 20\r\n")
        assert "S5" in pd.detect_platform_from_content(f)


class TestEditorKind:
    def test_factory_web_kind_text(self):
        fw = importlib.import_module("factory_web")
        assert fw.KIND_BY_EXT.get(".ini") == "text"
        assert fw.KIND_BY_EXT.get(".seq") == "text"
