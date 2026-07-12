"""Proof tests — deterministic S5→S7 enrichment of bare AWL exports.

A/B/C field measurement (2026-07-03): the bare "S5 for Windows" export
(bracket networks, no comments) yields generic AI analysis; the SAME code
with Zuordnungsliste symbols inline yields operand-level correct analysis.
These tests pin the enrichment: detection, symbol loading (incl. flags),
syntax conversion and the audit-safe batch mode.
"""
from __future__ import annotations

from pathlib import Path

import legacy_enrich as le


S5_AWL = (
    "###PG:82000000\n"
    "[1\t\n"
    "\t***\t]\n"
    "[5\t\n"
    "\tAN\tI 6.7\n"
    "\tAN\tF 99.0\n"
    "\t=\tF 1.0\n"
    "\t***\t]\n"
    "[7\t\n"
    "\tA\tF 3.0\n"
    "\tL\tKT 050.0\n"
    "\tSE\tT 1\n"
    "\tA\tT 1\n"
    "\t=\tQ 28.4\n"
    "\tBE\t]\n"
)

IOSEQ = (
    "\tI 6.7\tE 6.7\tSTEUERUNG EIN\n"
    "\tQ 28.4\tA 28.4\tYH VEREINZELUNG SCHLIESSEN\n"
    "\tI 5.6\tE 5.6\tReserve\n"
)

MERKER_SEQ = (
    "\tM    1.0\tM  1.0\tHM STEUERUNG EIN\n"
    "\tM   99.0\tM 99.0\tRESET AUS OB 21\n"
    "\tT    1\tT  1\tVERZOEGERUNG VEREINZELUNG\n"
)


def _legacy(tmp_path: Path) -> Path:
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "PB1.AWL").write_text(S5_AWL, encoding="utf-8")
    (legacy / "io.seq").write_text(IOSEQ, encoding="utf-8")
    (legacy / "merker.seq").write_text(MERKER_SEQ, encoding="utf-8")
    return legacy


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def test_detects_bracket_export_and_ignores_normal_stl():
    assert le.is_s5_bracket_awl(S5_AWL)
    assert le.is_s5_bracket_awl("[12\nA I 1.0")
    assert not le.is_s5_bracket_awl(
        "FUNCTION_BLOCK FB10\nNETWORK\nU E 0.1\n")


# ---------------------------------------------------------------------------
# Symbol loading
# ---------------------------------------------------------------------------

def test_load_symbols_reads_io_flags_timers_and_skips_reserve(tmp_path):
    sym = le.load_symbols(_legacy(tmp_path))
    assert sym["I6.7"] == "STEUERUNG EIN"
    assert sym["E6.7"] == "STEUERUNG EIN", "Alman/uluslararası çift anahtar"
    assert sym["Q28.4"].startswith("YH VEREINZELUNG")
    assert sym["M1.0"] == "HM STEUERUNG EIN"
    assert sym["M99.0"] == "RESET AUS OB 21"
    assert sym["T1"].startswith("VERZOEGERUNG")
    assert "I5.6" not in sym, "RESERVE satırı sembol değildir"


# ---------------------------------------------------------------------------
# Enrichment output
# ---------------------------------------------------------------------------

def test_enrich_converts_syntax_and_injects_symbols(tmp_path):
    sym = le.load_symbols(_legacy(tmp_path))
    out = le.enrich_awl_text(S5_AWL, sym, "PB1")
    assert "###PG" not in out
    assert "NETWORK  // Segment 5" in out
    # F flags became S7 M memory — with the flag's meaning inline
    assert "M 99.0" in out and "// M99.0: RESET AUS OB 21" in out
    assert "F 99.0" not in out
    # S5 timer literal converted (KT 050.0 = 50 × 10ms = 500ms)
    assert "S5T#500MS" in out and "KT 050.0" not in out
    # IO lines carry the Zuordnungsliste description
    assert "// I6.7: STEUERUNG EIN" in out
    assert "// Q28.4: YH VEREINZELUNG SCHLIESSEN" in out
    # timer line got the timer symbol
    assert "// T1: VERZOEGERUNG VEREINZELUNG" in out


def test_enrich_leaves_unknown_operands_uncommented(tmp_path):
    out = le.enrich_awl_text("\tA\tI 9.9\n", {}, "X")
    line = next(ln for ln in out.splitlines() if "I 9.9" in ln)
    assert "//" not in line, "bilinmeyen operanda yorum uydurulmaz"


# ---------------------------------------------------------------------------
# Batch mode (audit-safe)
# ---------------------------------------------------------------------------

def test_enrich_project_writes_copies_and_keeps_originals(tmp_path):
    legacy = _legacy(tmp_path)
    original = (legacy / "PB1.AWL").read_text(encoding="utf-8")
    r = le.enrich_project(tmp_path)
    assert r["ok"] and r["enriched"] == 1, r
    enriched = tmp_path / "_raw" / "legacy_enriched" / "PB1_S7.AWL"
    assert enriched.is_file()
    assert "// I6.7: STEUERUNG EIN" in enriched.read_text(encoding="utf-8")
    assert (legacy / "PB1.AWL").read_text(encoding="utf-8") == original, (
        "orijinal dosyaya dokunulmaz (denetim izi)")


def test_enrich_project_skips_non_bracket_files(tmp_path):
    legacy = _legacy(tmp_path)
    (legacy / "FB10.AWL").write_text(
        "FUNCTION_BLOCK FB10\nNETWORK\nU E 0.1\n", encoding="utf-8")
    r = le.enrich_project(tmp_path)
    assert r["enriched"] == 1 and r["skipped"] == 1
