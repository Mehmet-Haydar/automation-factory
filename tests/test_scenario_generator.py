"""Proof tests for rag.test_scenario_generator (Gate 6 test scenarios).

Locks:
  1. The module exists and is importable under its renamed path. It was
     committed late as `rag/rd13_generator.py` while factory_web.py imported it,
     so the feature silently broke on clean checkouts; renamed to
     test_scenario_generator (it is NOT the RD13 Legacy Annotation). This test
     makes a recurrence a CI failure.
  2. Output artefacts carry the NEW names (TEST_SCENARIOS.md / test_scenarios.json),
     not the old RD13_* names that collided with the annotation.
  3. No silent success on an empty project.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from rag.test_scenario_generator import generate_test_scenarios  # noqa: E402


_RD01 = """\
# RD01 IO List

| Tag | Type | Address | Description |
|-----|------|---------|-------------|
| MOT_CONV_001_FB  | DI | %I0.0 | Conveyor run feedback |
| MOT_CONV_001_OL  | DI | %I0.1 | Conveyor overload thermal relay |
| MOT_CONV_001_RUN | DQ | %Q0.0 | Conveyor motor contactor |
"""


def _make_project(tmp_path: Path) -> Path:
    md = tmp_path / "metadata"
    md.mkdir()
    (md / "RD01_IO_List.md").write_text(_RD01, encoding="utf-8")
    return tmp_path


class TestHappyPath:
    def test_generates_scenarios_with_new_filenames(self, tmp_path):
        proj = _make_project(tmp_path)
        res = generate_test_scenarios(proj)
        assert res["ok"] is True, res
        assert res["device_count"] >= 1  # conveyor motor matched FB_Motor_DOL

        # Renamed artefacts must exist...
        assert (proj / "REPORTS" / "TEST_SCENARIOS.md").is_file()
        assert (proj / "REPORTS" / "gate_results" / "test_scenarios.json").is_file()
        # ...and the old RD13-colliding names must NOT.
        assert not (proj / "REPORTS" / "RD13_test_scenarios.md").exists()
        assert not (proj / "REPORTS" / "gate_results" / "rd13_test_scenarios.json").exists()

    def test_output_has_no_turkish_left(self, tmp_path):
        proj = _make_project(tmp_path)
        generate_test_scenarios(proj)
        text = (proj / "REPORTS" / "TEST_SCENARIOS.md").read_text(encoding="utf-8")
        for tr in ("Proje:", "Cihaz", "Üretildi", "Sinyal Bağ", "Sonuç"):
            assert tr not in text, f"untranslated Turkish leaked: {tr}"


class TestNoSilentFailure:
    def test_empty_project_reports_error(self, tmp_path):
        res = generate_test_scenarios(tmp_path)
        assert res["ok"] is False
        assert res["tc_count"] == 0
        assert "RD01" in res.get("msg", "")
