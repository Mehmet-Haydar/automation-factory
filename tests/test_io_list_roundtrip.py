"""C3 + I1 — IO listesi round-trip: #UNKNOWNS korunur; dil baslikları."""

from pathlib import Path

from workbench.core.io_list_io import IORow, write_md, read_md


EXISTING = """---
project_id: KMG-2026-001
output_language: TR
status: DRAFT
---

# RD01_IO_List — Örnek

> AI extraction + insan inceleme notu.

## Özet

- Toplam sinyal: 1
- DI: 1 | DO: 0 | AI: 0 | AO: 0
- Safety-related: 0

## Sinyaller

| Tag | Address | Type | Direction | Equipment | Description | NormalState | EngUnit | RangeMin | RangeMax | SafetyRelated | SourceModule | OldTag | Notes | Status |
|-----|---------|------|-----------|-----------|-------------|-------------|---------|----------|----------|---------------|--------------|--------|-------|--------|
| OLD_TAG | %I0.0 | BOOL | DI | X | desc | NO | | | | N | DI_001 | E_Old | note | Active |

## #UNKNOWNS (Gate 3 — insan dolduracak)

| Eski Tag | Sebep |
|----------|-------|
| MW100..MW150 | Sembol tablosunda yok — operatör interview gerek |
| EW_Druck | Range belirsiz — datasheet gerek |

## ⚠️ KRİTİK BULGULAR

1. E-Stop standart PLC üzerinde — FND001 SAFETY CRITICAL
"""


def _write_existing(tmp_path: Path) -> Path:
    p = tmp_path / "RD01_IO.md"
    p.write_text(EXISTING, encoding="utf-8")
    return p


def test_unknowns_preserved_on_save(tmp_path):
    p = _write_existing(tmp_path)
    new_rows = [IORow(tag="NEW_TAG", address="%I0.1", dtype="BOOL", direction="DI")]
    write_md(p, new_rows, frontmatter={"project_id": "KMG-2026-001"})
    out = p.read_text(encoding="utf-8")
    # The populated #UNKNOWNS rows must survive.
    assert "MW100..MW150" in out
    assert "EW_Druck" in out
    # The post-table critical-findings section must survive.
    assert "FND001 SAFETY CRITICAL" in out
    # The new signal row is written.
    assert "NEW_TAG" in out
    # The old row was replaced (not appended).
    assert "OLD_TAG" not in out


def test_intro_and_extra_head_preserved(tmp_path):
    p = _write_existing(tmp_path)
    write_md(p, [IORow(tag="T", direction="DI")])
    out = p.read_text(encoding="utf-8")
    assert "AI extraction + insan inceleme notu." in out


def test_fresh_write_emits_default_unknowns(tmp_path):
    p = tmp_path / "fresh.md"
    write_md(p, [IORow(tag="T1", direction="DI")])
    out = p.read_text(encoding="utf-8")
    assert "#UNKNOWNS" in out
    assert "T1" in out


def test_roundtrip_rows_readable(tmp_path):
    # write -> read returns the rows we wrote.
    p = tmp_path / "rt.md"
    rows = [
        IORow(tag="A", address="%I0.0", dtype="BOOL", direction="DI"),
        IORow(tag="B", address="%Q0.0", dtype="BOOL", direction="DO"),
    ]
    write_md(p, rows)
    back, _fm = read_md(p)
    tags = {r.tag for r in back}
    assert {"A", "B"} <= tags


def test_save_twice_keeps_unknowns(tmp_path):
    # Idempotency: saving again must not wipe the preserved tail.
    p = _write_existing(tmp_path)
    write_md(p, [IORow(tag="N1", direction="DI")])
    write_md(p, [IORow(tag="N2", direction="DI")])
    out = p.read_text(encoding="utf-8")
    assert "MW100..MW150" in out
    assert "N2" in out


# -- I1: output_language headings --

def test_english_headings_used(tmp_path):
    p = tmp_path / "en.md"
    write_md(p, [IORow(tag="X", direction="DI")], frontmatter={"output_language": "EN"})
    out = p.read_text(encoding="utf-8")
    assert "## Summary" in out
    assert "## Signals" in out
    assert "Total signals" in out
    assert "## #UNKNOWNS" in out
    assert "human to fill" in out


def test_german_headings_used(tmp_path):
    p = tmp_path / "de.md"
    write_md(p, [IORow(tag="Y", direction="DI")], frontmatter={"output_language": "DE"})
    out = p.read_text(encoding="utf-8")
    assert "## Zusammenfassung" in out
    assert "## Signale" in out
    assert "Signale gesamt" in out


def test_default_turkish_headings(tmp_path):
    p = tmp_path / "tr.md"
    write_md(p, [IORow(tag="Z", direction="DI")], frontmatter={})
    out = p.read_text(encoding="utf-8")
    assert "## Özet" in out
    assert "## Sinyaller" in out
