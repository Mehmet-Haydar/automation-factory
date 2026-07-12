"""C-A1 regresyonu: Api.save_io_list mevcut YAML frontmatter'ı korumalı.

Önceki davranış: GUI grid'inden "Save MD" tıklayınca sync(md_path, io_rows)
çağrısı frontmatter=None ile yapılıyordu, write_md de fm={} ile sadece
filled_at ekleyip diğer alanları (project_id, output_language, customer,
data_classification, source_platform, …) siliyordu.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from workbench.core.io_list_io import IORow, read_md, write_md


EXISTING_MD = """---
project_id: KMG-2026-001
output_language: EN
customer: Müller GmbH
data_classification: CONFIDENTIAL
source_platform: TIA
---

# RD01_IO_List — Example

> AI extraction + human review note.

## Summary

- Total signals: 1
- DI: 1 | DO: 0 | AI: 0 | AO: 0
- Safety-related: 0

## Signals

| Tag | Address | Type | Direction | Equipment | Description | NormalState | EngUnit | RangeMin | RangeMax | SafetyRelated | SourceModule | OldTag | Notes | Status |
|-----|---------|------|-----------|-----------|-------------|-------------|---------|----------|----------|---------------|--------------|--------|-------|--------|
| OLD_TAG | %I0.0 | BOOL | DI | X | desc | NO | | | | N | DI_001 | E_Old | note | Active |
"""


def _make_api_with_root(root: Path):
    """Construct a webgui Api object pointing at `root` without launching pywebview."""
    factory_web = importlib.import_module("factory_web")
    api = factory_web.Api()
    # The Api class normally learns about its project root via open_project; we
    # short-circuit that for the test so save_io_list resolves paths under tmp.
    api.root = root
    return api


def test_save_io_list_preserves_frontmatter(tmp_path: Path):
    md_path = tmp_path / "RD01_IO_List.md"
    md_path.write_text(EXISTING_MD, encoding="utf-8")

    api = _make_api_with_root(tmp_path)
    result = api.save_io_list(
        md_path.name,
        [{"tag": "NEW_TAG", "address": "%I0.1", "dtype": "BOOL", "direction": "DI"}],
    )

    assert result["ok"], result
    rows, fm = read_md(md_path)
    tags = {r.tag for r in rows}
    assert tags == {"NEW_TAG"}

    # The frontmatter must still carry every original key.
    assert fm.get("project_id") == "KMG-2026-001"
    assert fm.get("output_language") == "EN"
    assert "Müller" in str(fm.get("customer", ""))
    assert fm.get("data_classification") == "CONFIDENTIAL"
    assert fm.get("source_platform") == "TIA"

    # Sanity: language switch is preserved on disk too (English headings).
    on_disk = md_path.read_text(encoding="utf-8")
    assert "## Summary" in on_disk
    assert "## Signals" in on_disk


def test_save_io_list_fresh_file_still_writes(tmp_path: Path):
    """When there is no existing file, save still produces a valid MD."""
    md_path = tmp_path / "fresh.md"

    api = _make_api_with_root(tmp_path)
    result = api.save_io_list(
        md_path.name,
        [{"tag": "X", "address": "%I0.0", "dtype": "BOOL", "direction": "DI"}],
    )

    assert result["ok"], result
    rows, _fm = read_md(md_path)
    assert {r.tag for r in rows} == {"X"}
