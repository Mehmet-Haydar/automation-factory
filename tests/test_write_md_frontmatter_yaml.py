"""M-A3 regresyonu — write_md, ':' icermesi gibi YAML-tehlikeli karakterleri
bozmadan frontmatter'i yazip geri okumalı.
"""

from __future__ import annotations

from pathlib import Path

from workbench.core.io_list_io import IORow, read_md, write_md


def test_value_with_colon_round_trips(tmp_path: Path):
    p = tmp_path / "rd01.md"
    fm = {
        "project_id": "KMG-2026-001",
        "customer":   "Bosch: Bonnenfant GmbH",  # colon inside value
        "output_language": "EN",
    }
    write_md(p, [IORow(tag="T", direction="DI")], frontmatter=fm)
    _rows, back = read_md(p)
    assert back["customer"] == "Bosch: Bonnenfant GmbH"
    assert back["project_id"] == "KMG-2026-001"
    assert back["output_language"] == "EN"


def test_value_with_hash_round_trips(tmp_path: Path):
    p = tmp_path / "rd01.md"
    fm = {"description": "tag #5 spare slot"}
    write_md(p, [IORow(tag="T", direction="DI")], frontmatter=fm)
    _rows, back = read_md(p)
    assert back["description"] == "tag #5 spare slot"


def test_value_with_quotes_round_trips(tmp_path: Path):
    p = tmp_path / "rd01.md"
    fm = {"note": 'the "north" panel'}
    write_md(p, [IORow(tag="T", direction="DI")], frontmatter=fm)
    _rows, back = read_md(p)
    assert back["note"] == 'the "north" panel'


def test_list_value_preserved_as_list(tmp_path: Path):
    p = tmp_path / "rd01.md"
    fm = {"hw_modules": ["ET200SP DI 16", "ET200SP DQ 8"]}
    write_md(p, [IORow(tag="T", direction="DI")], frontmatter=fm)
    _rows, back = read_md(p)
    assert back["hw_modules"] == ["ET200SP DI 16", "ET200SP DQ 8"]


def test_unicode_round_trip(tmp_path: Path):
    p = tmp_path / "rd01.md"
    fm = {"customer": "Müller GmbH — Türkiye şubesi"}
    write_md(p, [IORow(tag="T", direction="DI")], frontmatter=fm)
    _rows, back = read_md(p)
    assert back["customer"] == "Müller GmbH — Türkiye şubesi"
