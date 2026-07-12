"""Proof tests — RD01 schema gate (AI format drift stops at write time).

D-run 2026-07-03: the AI dropped the % address prefix and reshaped rows;
every deterministic consumer downstream reads the table positionally.
The gate repairs what is unambiguous and loudly rejects what is not."""
from __future__ import annotations

from pathlib import Path

from rd_table_schema import gate_rd01_draft, validate_and_repair_rd01


HDR = ("| Tag | Address | Type | Dir | Equipment | Description | OldTag "
       "| Notes | Status |\n"
       "|-----|---------|------|-----|-----------|-------------|--------"
       "|-------|--------|\n")


def test_address_normalized_to_iec():
    content = HDR + ("| HydrNetz | I4.0 | DI | IN | M1 | KE NETZ | I 4.0 "
                     "| | DRAFT_UNVERIFIED |\n")
    out, rep = validate_and_repair_rd01(content)
    assert "| %I4.0 |" in out, "D-koşusu kusuru: % öneki mekanik eklenmeli"
    assert rep.ok and rep.repaired_cells >= 1


def test_short_row_padded_and_dir_status_derived():
    content = HDR + "| X | %Q28.4 | DQ | | Y1 | VENTIL |\n"
    out, rep = validate_and_repair_rd01(content)
    row = next(ln for ln in out.splitlines() if ln.startswith("| X"))
    cells = [c.strip() for c in row.split("|")[1:-1]]
    assert len(cells) == 9, "kısa satır kolon sayısına tamamlanmalı"
    assert cells[3] == "OUT", "Dir, Type'tan türetilmeli (DQ→OUT)"
    assert cells[8] == "DRAFT_UNVERIFIED", "boş Status doldurulmalı"
    assert rep.ok


def test_oversized_row_rejected_never_guessed(tmp_path):
    bad = ("| A | %I1.0 | DI | IN | M1 | desc | with | extra | pipes "
           "| overflow | DRAFT_UNVERIFIED |")
    content = HDR + bad + "\n"
    (tmp_path / "metadata").mkdir()
    out, rep = gate_rd01_draft(tmp_path, content)
    assert not rep.ok and len(rep.rejected_rows) == 1
    assert "| A |" not in out.split("Schema gate")[-1].splitlines()[0], \
        "reddedilen satır tabloda kalmamalı"
    rej_files = list((tmp_path / "metadata" / "_history").glob("*rejected*"))
    assert rej_files, "reddedilenler kalıcı dosyaya yazılmalı"
    rej_text = rej_files[0].read_text(encoding="utf-8")
    assert "I1_0" in rej_text and "I1.0" not in rej_text, (
        "operand etkisizleştirilmeli ki crosscheck onu 'eksik' sayıp "
        "autocomplete deterministik geri eklesin")
    assert "Schema gate" in out, "görünür banner şart"


def test_unknown_type_rejected():
    content = HDR + ("| B | %I2.0 | BOOL | IN | | x | | | DRAFT_UNVERIFIED |\n")
    out, rep = validate_and_repair_rd01(content)
    assert len(rep.rejected_rows) == 1
    assert "unknown Type" in rep.rejected_rows[0]


def test_truncated_half_row_rejected():
    content = HDR + "| C | %I3.0 | DI | IN | M2 | KESIK SAT\n"
    out, rep = validate_and_repair_rd01(content)
    assert len(rep.rejected_rows) == 1
    assert "truncated" in rep.rejected_rows[0]


def test_gate_is_idempotent_and_skips_foreign_content():
    content = HDR + ("| HydrNetz | %I4.0 | DI | IN | M1 | KE NETZ | I 4.0 "
                     "| | DRAFT_UNVERIFIED |\n")
    once, rep1 = validate_and_repair_rd01(content)
    twice, rep2 = validate_and_repair_rd01(once)
    assert once == twice and rep2.repaired_cells == 0
    prose = "# Not a table\nJust text.\n"
    out, rep = validate_and_repair_rd01(prose)
    assert out == prose and "skipped" in rep.notes[0]
