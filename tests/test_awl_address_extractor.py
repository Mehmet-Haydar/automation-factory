"""Proof tests for awl_address_extractor.

Locks two things:
  1. The module exists and is importable (it was committed late — a caller in
     factory_web.py imported it while the file itself stayed untracked, so the
     address-backfill feature silently broke on clean checkouts; this test makes
     that recurrence a CI failure).
  2. Deterministic S5 -> S7 address conversion + RD01 backfill behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import awl_address_extractor as ax  # noqa: E402


class TestConvert:
    def test_bit_inputs_outputs(self):
        assert ax._convert("E", "1", "4") == ("%I1.4", "DI")
        assert ax._convert("A", "4", "0") == ("%Q4.0", "DQ")

    def test_word_types_drop_bit(self):
        assert ax._convert("EW", "10", None) == ("%IW10", "AI")
        assert ax._convert("AW", "2", None) == ("%QW2", "AO")

    def test_unknown_prefix_is_unk_not_crash(self):
        assert ax._convert("ZZ", "1", "0") == ("", "UNK")


class TestScanLegacy:
    def test_parses_awl_operands(self, tmp_path):
        legacy = tmp_path / "_raw" / "legacy_code"
        legacy.mkdir(parents=True)
        (legacy / "OB1.awl").write_text(
            "      U     E    1.4          // Band Rueckmeldung\n"
            "      =     A    4.3          // Bandschuetz\n",
            encoding="utf-8",
        )
        addr_map = ax.scan_legacy_files(tmp_path)
        assert addr_map.get("E 1.4", {}).get("s7") == "%I1.4"
        assert addr_map.get("A 4.3", {}).get("s7") == "%Q4.3"

    def test_no_legacy_dir_returns_empty_not_crash(self, tmp_path):
        assert ax.scan_legacy_files(tmp_path) == {}


class TestBackfill:
    def test_fills_empty_address_from_old_pattern(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        (md / "RD01_IO_List.md").write_text(
            "# RD01 IO List\n\n"
            "| Tag | Type | Address | Description |\n"
            "|-----|------|---------|-------------|\n"
            "| StartBtn | DI |  | Start button (old E 0.0) |\n"
            "| OilTemp  | AI |  | Oil temperature (old EW 10) |\n",
            encoding="utf-8",
        )
        res = ax.backfill_rd01_addresses(tmp_path)
        assert res["updated"] == 2
        filled = (md / "RD01_IO_List.md").read_text(encoding="utf-8")
        assert "%I0.0" in filled
        assert "%IW10" in filled

    def test_already_filled_addresses_untouched(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        (md / "RD01_IO_List.md").write_text(
            "# RD01 IO List\n\n"
            "| Tag | Type | Address | Description |\n"
            "|-----|------|---------|-------------|\n"
            "| StartBtn | DI | %I0.0 | Start button (old E 9.9) |\n",
            encoding="utf-8",
        )
        res = ax.backfill_rd01_addresses(tmp_path)
        assert res["updated"] == 0  # existing %I0.0 must NOT be overwritten by E9.9

    def test_missing_metadata_returns_clean_not_crash(self, tmp_path):
        res = ax.backfill_rd01_addresses(tmp_path)
        assert res["updated"] == 0
        assert "msg" in res
