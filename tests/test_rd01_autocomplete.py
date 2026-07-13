"""Proof tests — deterministic RD01 completion from symbol tables.

Benchmark (Beispielmaschine 4711 demo, ~300 IO): a cheap model's output
window (~8k tokens) cannot hold a 190-row IO table — the draft truncated
mid-row. The fix: a Zuordnungsliste is STRUCTURED data; missing operands are
appended mechanically, flagged as deterministic, and the cross-check goes
clean without a second AI call.
"""
from __future__ import annotations

from pathlib import Path

import rd01_autocomplete as ac


IOSEQ = (
    "\tI 4.0\tE 4.0\tKE HYDR.MOTOR NETZSCHUETZ\n"
    "\tI 5.2\tE 5.2\tKE ROLLENBAHN 2   * 7-M5  (STAT. I)\n"
    "\tI 6.4\tF-BREMSE\tKE SICHERUNG BZW. MOTORSCHUTZ BREMSEN\n"
    "\tQ 28.0\tA 28.0\tHYDRAULIKMOTOR SCHUETZ\n"
)

AWL = (
    "###PG:82000000\n"
    "\tA\tI 4.0\n"
    "\tA\tI 5.2\n"
    "\tA\tI 6.4\n"
    "\t=\tQ 28.0\n"
)

RD01_TRUNCATED = (
    "| Tag | Address | Type | Dir | Equipment | Description | OldTag | Notes | Status |\n"
    "|-----|---------|------|-----|-----------|-------------|--------|-------|--------|\n"
    "| HydrNetz | %I4.0 | DI | IN | M1 | KE Netzschuetz | E 4.0 | | DRAFT_UNVERIFIED |\n"
    "| Rollenb2 | %I5.2 | DI | IN | M5 | KE Rollenbahn 2 | E 5\n"   # ← cut mid-row
)


def _proj(tmp_path: Path) -> Path:
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "io.seq").write_text(IOSEQ, encoding="utf-8")
    (legacy / "OB1.AWL").write_text(AWL, encoding="utf-8")
    (tmp_path / "metadata").mkdir()
    (tmp_path / "metadata" / "RD01_IO_List.md").write_text(
        RD01_TRUNCATED, encoding="utf-8")
    return tmp_path


def test_symbol_table_parses_devrefs_and_symbols(tmp_path):
    _proj(tmp_path)
    syms = ac.parse_symbol_tables(tmp_path)
    assert set(syms) == {"E4.0", "E5.2", "E6.4", "A28.0"}
    assert syms["E5.2"].equipment == "M5", "yorumdaki '7-M5' cihaz referansı"
    assert "ROLLENBAHN" in syms["E5.2"].desc
    assert syms["E6.4"].name.startswith("F_BREMSE"), "gerçek sembol korunmalı"


def test_completion_appends_missing_and_goes_clean(tmp_path):
    root = _proj(tmp_path)
    r = ac.complete_rd01(root)
    assert r["ok"], r
    # E5.2 half-row was unusable; E5.2 + E6.4 + A28.0 must be appended
    assert r["appended"] == 3
    cc = r["crosscheck_after"]
    assert cc["ok"], cc
    text = (root / "metadata" / "RD01_IO_List.md").read_text(encoding="utf-8")
    assert "auto-added from symbol table (deterministic)" in text
    assert "%Q28.0" in text and "HYDRAULIKMOTOR" in text
    # Equipment survived into the appended row
    assert "| M5 |" in text


def test_completion_is_idempotent(tmp_path):
    root = _proj(tmp_path)
    ac.complete_rd01(root)
    r2 = ac.complete_rd01(root)
    assert r2["appended"] == 0, "ikinci koşu satır eklememeli"


def test_unresolvable_operand_stays_reported(tmp_path):
    root = _proj(tmp_path)
    # add an operand to the CODE that no symbol table covers
    ob1 = root / "_raw" / "legacy_code" / "OB1.AWL"
    ob1.write_text(ob1.read_text(encoding="utf-8") + "\tA\tI 20.3\n",
                   encoding="utf-8")
    r = ac.complete_rd01(root)
    assert "E20.3" in r["still_missing"], (
        "Sembol tablosunda olmayan operand sessizce kaybolmamalı"
    )
    assert r["crosscheck_after"]["ok"] is False
