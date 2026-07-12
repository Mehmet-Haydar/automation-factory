"""CE essential-modification assessment proof tests (Faz 4).

- generation (retrofit + greenfield), disclaimer ALWAYS present (3 langs),
- greenfield → visible non-blocking warning,
- the tool never pre-answers a question or pre-ticks the result,
- PDF smoke.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ce_assessment import generate_ce_assessment


def _mk_project(tmp_path: Path, ptype: str = "retrofit") -> Path:
    proj = tmp_path / "Proj_CE"
    proj.mkdir(parents=True)
    (proj / "PROJECT_STATE.json").write_text(json.dumps({
        "project_name": "Schleifmaschine_4711",
        "project_type": ptype,
        "customer": "ACME",
        "target_platform": "S7_1500",
    }), encoding="utf-8")
    return proj


_DISCLAIMER_MARKERS = {
    "de": "ersetzt KEINE rechtliche Bewertung",
    "en": "does NOT replace a legal assessment",
    "tr": "hukuki değerlendirmenin YERİNE GEÇMEZ",
}


class TestCeAssessment:
    @pytest.mark.parametrize("lang", ["de", "en", "tr"])
    def test_disclaimer_always_present(self, tmp_path, lang):
        proj = _mk_project(tmp_path)
        r = generate_ce_assessment(proj, lang=lang)
        text = r.md_path.read_text(encoding="utf-8")
        assert _DISCLAIMER_MARKERS[lang] in text, f"{lang}: disclaimer missing"
        # disclaimer must be near the top (before section 1)
        assert text.index(_DISCLAIMER_MARKERS[lang]) < text.index("## 1.")

    def test_retrofit_no_warning(self, tmp_path):
        proj = _mk_project(tmp_path, "retrofit")
        r = generate_ce_assessment(proj, lang="en")
        assert r.is_retrofit is True
        assert r.warnings == []
        assert "not set up as a retrofit" not in r.md_path.read_text(encoding="utf-8")

    def test_greenfield_warns_but_produces(self, tmp_path):
        """User decision: warn, don't block."""
        proj = _mk_project(tmp_path, "greenfield")
        r = generate_ce_assessment(proj, lang="en")
        assert r.ok, "document must still be produced for greenfield"
        assert r.is_retrofit is False
        assert any("not set up as a retrofit" in w for w in r.warnings)
        assert "not set up as a retrofit" in r.md_path.read_text(encoding="utf-8")

    def test_questions_and_result_present_unanswered(self, tmp_path):
        """The tool must never pre-answer: every answer cell is the blank
        checkbox pair, and the result line carries both empty boxes."""
        proj = _mk_project(tmp_path)
        text = generate_ce_assessment(proj, lang="en").md_path.read_text(
            encoding="utf-8")
        assert "performance increase or functional change" in text
        assert "NEW hazard" in text
        assert "still sufficient" in text
        assert "SIMPLE protective devices" in text
        assert text.count("☐ / ☐") == 4, "all 4 answers must be blank"
        assert "☐ YES  ☐ NO" in text, "result must be un-ticked"
        assert "☑" not in text and "[x]" not in text.lower()

    def test_machine_identity_from_state(self, tmp_path):
        proj = _mk_project(tmp_path)
        text = generate_ce_assessment(proj, lang="en").md_path.read_text(
            encoding="utf-8")
        assert "Schleifmaschine_4711" in text
        assert "ACME" in text
        assert "S7_1500" in text

    def test_pdf_smoke(self, tmp_path):
        pytest.importorskip("reportlab")
        proj = _mk_project(tmp_path)
        r = generate_ce_assessment(proj, lang="de", pdf=True)
        assert r.pdf_path is not None, f"PDF missing — {r.warnings}"
        assert r.pdf_path.stat().st_size > 0

    def test_missing_project_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            generate_ce_assessment(tmp_path / "nope")
