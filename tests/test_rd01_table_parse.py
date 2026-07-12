"""RD01 markdown-table parser — boundary-pipe regression.

Found via the Demo_Beispielmaschine_4711 example: the data-row filter
`if c.strip() is not None` was always True, so the empty cell before the
leading "|" shifted every column — the tag read as "" and EVERY row was
silently skipped. parse_rd01_signals returned [] for any standard
markdown table, which starved generate_iec_tags and the assembler.
"""

from __future__ import annotations

from pathlib import Path

from iec_tag_generator import parse_rd01_signals

RD01 = """---
status: done
---

# RD01 — IO List

## Signals

| Tag | Description | IO_Type | Address | SafetyRelated | Status |
|-----|-------------|---------|---------|---------------|--------|
| MOT_HYD_001_FBM | Pump main contactor feedback | DI | %I1.0 | N | done |
| MOT_HYD_001_MAIN | Pump main contactor | DQ | %Q4.0 | N | done |
| SEN_TEMP_001_VAL | Oil temperature 4-20mA | AI | %IW10 | N | done |
"""


def _project(tmp_path: Path) -> Path:
    md = tmp_path / "metadata"
    md.mkdir()
    (md / "RD01_IO_List.md").write_text(RD01, encoding="utf-8")
    return tmp_path


class TestBoundaryPipeParsing:
    def test_standard_markdown_table_yields_all_rows(self, tmp_path):
        signals = parse_rd01_signals(_project(tmp_path))
        assert len(signals) == 3, (
            "every data row of a standard |-delimited table must parse — "
            "pre-fix the leading boundary pipe shifted columns and ALL rows "
            "were silently dropped"
        )

    def test_columns_correctly_aligned(self, tmp_path):
        signals = parse_rd01_signals(_project(tmp_path))
        by_name = {s["name"]: s for s in signals}
        assert "MOT_HYD_001_FBM" in by_name, "tag column must not read empty"
        fbm = by_name["MOT_HYD_001_FBM"]
        assert fbm["address"] == "%I1.0"
        assert fbm["type"] == "DI"
        assert by_name["MOT_HYD_001_MAIN"]["type"] == "DQ"
        assert by_name["SEN_TEMP_001_VAL"]["type"] == "AI"

    def test_demo_example_project_parses(self):
        demo = (Path(__file__).resolve().parent.parent
                / "examples" / "Demo_Beispielmaschine_4711")
        signals = parse_rd01_signals(demo)
        names = {s["name"] for s in signals}
        assert "MOT_HYD_001_STAR" in names
        assert len(signals) >= 14
