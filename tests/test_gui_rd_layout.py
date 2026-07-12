"""Proof tests — role-based RD layout support + in-GUI xlsx preview
(2026-07-07 GUI reorganization)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_xlsx_preview_returns_capped_grid(tmp_path):
    import openpyxl

    import factory_web

    fp = tmp_path / "sample.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "HMI_Tags"
    ws.append(["Tag", "Type", "Value"])
    for i in range(400):                       # forces the honest cap
        ws.append([f"T{i}", "Bool", i])
    wb.save(fp)

    r = factory_web.Api._read_xlsx_preview(fp)
    assert r["kind"] == "xlsx" and r["sheet"] == "HMI_Tags"
    assert r["rows"][0] == ["Tag", "Type", "Value"]
    assert len(r["rows"]) == 300 and r["truncated"] is True, \
        "önizleme dürüstçe sınırlanmalı ve bunu SÖYLEMELİ"


def test_xlsx_preview_fails_readably(tmp_path):
    import factory_web

    fp = tmp_path / "broken.xlsx"
    fp.write_bytes(b"not a real xlsx")
    r = factory_web.Api._read_xlsx_preview(fp)
    assert r["kind"] == "text" and "open externally" in r["text"]


def test_rd_role_map_in_frontend_covers_all_14():
    """The GUI role map must classify every RD; an unmapped RD silently
    falling into 'ref' is fine ONLY for analysis docs — worksheets and
    safety must be pinned explicitly."""
    app_js = (_ROOT / "webgui" / "app.js").read_text(encoding="utf-8")
    assert 'RD01:"work"' in app_js and 'RD11:"work"' in app_js \
        and 'RD08:"work"' in app_js, "çalışma tabloları sabitlenmiş olmalı"
    assert 'RD05:"sign"' in app_js, "Safety imza bölümünde olmalı"
    for rd in ("RD01", "RD02", "RD03", "RD04", "RD05", "RD06", "RD07",
               "RD08", "RD09", "RD10", "RD11", "RD12", "RD13", "RD14"):
        assert f"{rd}:" in app_js.split("const RD_HUMAN")[1].split("};")[0], \
            f"{rd} insan adı eksik"
