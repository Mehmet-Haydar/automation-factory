"""SAT v2 Proof Tests.

Covers:
- protocol_i18n: unknown key fails LOUD, missing lang falls back to EN with a
  warning, unsupported language code raises (silent empty strings forbidden).
- fat_protocol: 3-language output, SAT genuinely differs from FAT, Ref. column
  present, ISO 13849-2 attribution, IEC 62443 cyber section in SAT (Faz 3),
  RD05 gate (S-17) preserved for SAT too, BOTH produces two documents,
  PDF smoke (file exists + size > 0).
- script_protocol_generator: SAT loop-check wording differs from FAT, Ref.
  column, IEC 62682 alarm rationalization table (Faz 5) — missing RD08 fields
  render as "—" + fill-in instruction, never invented values.

Fix-revert contract: reverting the SAT v2 feature must fail these tests.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from protocol_i18n import (
    ProtocolI18nKeyError, SUPPORTED_LANGS, normalize_lang, t,
)
from fat_protocol import Rd05BlockedError, run_fat_protocol, run_protocol_set
import script_protocol_generator as spg


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _mk_project(tmp_path: Path, rd08_extra_cols: bool = False) -> Path:
    proj = tmp_path / "Proj_SATV2"
    meta = proj / "metadata"
    meta.mkdir(parents=True)
    (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
        "# RD05\n| Func | Desc | PLr |\n|---|---|---|\n"
        "| EStop_Main | Emergency stop | d |\n"
        "| DoorInterlock | Door circuit | d |\n",
        encoding="utf-8",
    )
    # AUDIT-004b: the DRAFT_UNVERIFIED banner/filename now blocks unless the
    # engineer review is recorded — these tests exercise protocol generation,
    # so the fixture ships a reviewed RD05.
    import json as _json
    (proj / "PROJECT_STATE.json").write_text(_json.dumps({
        "rd_verifications": {"RD05": {"reviewed": True,
                                      "who": "H. Becker (TUV)"}}}),
        encoding="utf-8")
    (meta / "RD01_IO_List.md").write_text(
        "| Tag | Address | Type |\n|---|---|---|\n"
        "| xStart | %I0.0 | DI |\n"
        "| qMotor | %Q0.0 | DQ |\n"
        "| iTemp | %IW64 | AI |\n",
        encoding="utf-8",
    )
    if rd08_extra_cols:
        (meta / "RD08_Alarm.md").write_text(
            "| Alarm | Tag | Priority | Response | Class |\n"
            "|---|---|---|---|---|\n"
            "| Motor overload | xOvl | high | stop and inspect | safety |\n",
            encoding="utf-8",
        )
    else:
        (meta / "RD08_Alarm.md").write_text(
            "| Alarm | Tag |\n|---|---|\n| Motor overload | xOvl |\n",
            encoding="utf-8",
        )
    return proj


# ===========================================================================
# Group A — protocol_i18n contract
# ===========================================================================


class TestI18n:
    def test_unknown_key_raises_loud(self):
        with pytest.raises(ProtocolI18nKeyError):
            t("no.such.key.ever", "de")

    def test_missing_lang_falls_back_to_en_with_warning(self, monkeypatch):
        import protocol_i18n
        monkeypatch.setitem(
            protocol_i18n.STRINGS, "_test.only_en", {"en": "english only"})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            out = t("_test.only_en", "tr")
        assert out == "english only"
        assert any("fallback" in str(w.message).lower() for w in caught), (
            "EN fallback must warn loudly — silent fallback forbidden"
        )

    def test_unsupported_lang_raises(self):
        with pytest.raises(ValueError):
            normalize_lang("fr")

    def test_every_key_has_all_three_languages(self):
        """The whole table must be complete — a missing translation would
        surface as a runtime warning in a customer document."""
        import protocol_i18n
        incomplete = [
            key for key, entry in protocol_i18n.STRINGS.items()
            if not key.startswith("_test.")
            and any(lang not in entry for lang in SUPPORTED_LANGS)
        ]
        assert incomplete == [], f"keys missing translations: {incomplete}"


# ===========================================================================
# Group B — fat_protocol: languages, SAT≠FAT, Ref. column, RD05 gate
# ===========================================================================


_DE_FAT_MARKERS = ("Sicherheitsfunktionstests", "IO-Validierungstests")
_EN_FAT_MARKERS = ("Safety Function Tests", "IO Validation Tests")
_TR_FAT_MARKERS = ("Güvenlik Fonksiyon Testleri", "IO Doğrulama Testleri")


class TestFatProtocolSatV2:
    @pytest.mark.parametrize("lang,markers", [
        ("de", _DE_FAT_MARKERS), ("en", _EN_FAT_MARKERS), ("tr", _TR_FAT_MARKERS),
    ])
    def test_fat_language_output(self, tmp_path, lang, markers):
        proj = _mk_project(tmp_path)
        r = run_fat_protocol(proj, tmp_path / "out", lang=lang)
        text = r.md_path.read_text(encoding="utf-8")
        for m in markers:
            assert m in text, f"{lang}: FAT marker {m!r} missing"

    def test_default_language_is_de(self, tmp_path):
        proj = _mk_project(tmp_path)
        r = run_fat_protocol(proj, tmp_path / "out")
        assert r.lang == "de"
        assert "Sicherheitsfunktionstests" in r.md_path.read_text(encoding="utf-8")

    def test_sat_differs_from_fat(self, tmp_path):
        """SAT is no longer a re-labelled FAT copy."""
        proj = _mk_project(tmp_path)
        fat = run_fat_protocol(proj, tmp_path / "o1", test_type="FAT", lang="en")
        sat = run_fat_protocol(proj, tmp_path / "o2", test_type="SAT", lang="en")
        fat_text = fat.md_path.read_text(encoding="utf-8")
        sat_text = sat.md_path.read_text(encoding="utf-8")
        # SAT-only content
        assert "Loop Check with Real Field Devices" in sat_text
        assert "Motor Rotation Direction Check" in sat_text
        assert "Backup and Handover" in sat_text
        assert "Loop Check with Real Field Devices" not in fat_text
        # FAT-only content
        assert "Stress / Stability Tests" in fat_text
        assert "PLCSim" in fat_text
        assert "Stress / Stability Tests" not in sat_text

    def test_ref_column_present_with_standards(self, tmp_path):
        proj = _mk_project(tmp_path)
        fat_text = run_fat_protocol(
            proj, tmp_path / "o1", lang="en").md_path.read_text(encoding="utf-8")
        assert "Ref." in fat_text
        assert "IEC 62381" in fat_text
        assert "IEC 62061" in fat_text
        # Faz 1.2: safety section cites 13849-2 (Validation), not -1
        assert "ISO 13849-2" in fat_text
        assert "ISO 13849-1" not in fat_text

    def test_sat_contains_iec62443_cyber_section(self, tmp_path):
        """Faz 3 — cyber section with IEC 62443/NIS2 refs, all 3 languages."""
        proj = _mk_project(tmp_path)
        for lang, title in [
            ("de", "Cybersicherheit (IEC 62443)"),
            ("en", "Cybersecurity (IEC 62443)"),
            ("tr", "Siber Güvenlik (IEC 62443)"),
        ]:
            text = run_fat_protocol(
                proj, tmp_path / f"o_{lang}", test_type="SAT", lang=lang,
            ).md_path.read_text(encoding="utf-8")
            assert title in text, f"{lang}: cyber section title missing"
            assert "IEC 62443 / NIS2" in text
            assert text.count("62443") >= 2

    def test_sat_rd05_gate_preserved(self, tmp_path):
        """S-17 must block SAT exactly like FAT (fail-closed)."""
        proj = tmp_path / "empty_proj"
        (proj / "metadata").mkdir(parents=True)
        with pytest.raises(Rd05BlockedError):
            run_fat_protocol(proj, tmp_path / "out", test_type="SAT")

    def test_both_produces_two_documents(self, tmp_path):
        proj = _mk_project(tmp_path)
        results = run_protocol_set(proj, tmp_path / "out", test_type="BOTH", lang="en")
        assert [r.test_type for r in results] == ["FAT", "SAT"]
        names = [r.md_path.name for r in results]
        assert any(n.startswith("FAT_PROTOCOL_") for n in names)
        assert any(n.startswith("SAT_PROTOCOL_") for n in names)

    def test_invalid_type_raises(self, tmp_path):
        proj = _mk_project(tmp_path)
        with pytest.raises(ValueError):
            run_fat_protocol(proj, tmp_path / "out", test_type="BOTH")
        with pytest.raises(ValueError):
            run_protocol_set(proj, tmp_path / "out", test_type="XAT")

    def test_invalid_lang_raises(self, tmp_path):
        proj = _mk_project(tmp_path)
        with pytest.raises(ValueError):
            run_fat_protocol(proj, tmp_path / "out", lang="fr")

    def test_pdf_smoke(self, tmp_path):
        pytest.importorskip("reportlab")
        proj = _mk_project(tmp_path)
        for tt in ("FAT", "SAT"):
            r = run_fat_protocol(proj, tmp_path / "out", test_type=tt,
                                 lang="de", pdf=True)
            assert r.pdf_path is not None, f"{tt}: PDF missing — {r.warnings}"
            assert r.pdf_path.exists() and r.pdf_path.stat().st_size > 0


# ===========================================================================
# Group C — script_protocol_generator: SAT wording, Ref., IEC 62682 (Faz 5)
# ===========================================================================


class TestScriptProtocolGeneratorSatV2:
    def test_sat_loop_check_wording_differs(self, tmp_path):
        proj = _mk_project(tmp_path)
        fat = spg.run_protocol(proj, test_type="FAT", lang="en")
        sat = spg.run_protocol(proj, test_type="SAT", lang="en")
        fat_text = fat.md_path.read_text(encoding="utf-8")
        sat_text = sat.md_path.read_text(encoding="utf-8")
        assert "Loop check" in sat_text
        assert "Loop check" not in fat_text
        # SAT site prechecks
        assert "field devices" in sat_text.lower()
        assert "as-built" in sat_text.lower()

    def test_ref_column_in_md(self, tmp_path):
        proj = _mk_project(tmp_path)
        text = spg.run_protocol(proj, lang="en").md_path.read_text(encoding="utf-8")
        assert "| Ref. |" in text
        assert "IEC 62381" in text

    def test_alarm_62682_missing_fields_render_dash_and_instruction(self, tmp_path):
        """Faz 5: RD08 without priority/response/class → '—' + fill-in note,
        never invented values."""
        proj = _mk_project(tmp_path, rd08_extra_cols=False)
        text = spg.run_protocol(proj, lang="en").md_path.read_text(encoding="utf-8")
        assert "Alarm Rationalization (IEC 62682)" in text
        assert "—" in text
        assert "NOT guessed automatically" in text

    def test_alarm_62682_full_fields_no_instruction(self, tmp_path):
        proj = _mk_project(tmp_path, rd08_extra_cols=True)
        text = spg.run_protocol(proj, lang="en").md_path.read_text(encoding="utf-8")
        assert "Alarm Rationalization (IEC 62682)" in text
        assert "stop and inspect" in text
        assert "safety" in text
        assert "NOT guessed automatically" not in text

    def test_three_languages(self, tmp_path):
        proj = _mk_project(tmp_path)
        for lang, marker in [
            ("de", "Vorprüfungen"), ("en", "Pre-Checks"), ("tr", "Ön Kontroller"),
        ]:
            text = spg.run_protocol(proj, lang=lang).md_path.read_text(encoding="utf-8")
            assert marker in text, f"{lang}: precheck title missing"

    def test_both_produces_two_documents(self, tmp_path):
        proj = _mk_project(tmp_path)
        results = spg.run_protocol_set(proj, test_type="BOTH", lang="en")
        assert [r.test_type for r in results] == ["FAT", "SAT"]

    def test_rd05_gate_preserved(self, tmp_path):
        proj = tmp_path / "empty_proj"
        (proj / "metadata").mkdir(parents=True)
        with pytest.raises(Rd05BlockedError):
            spg.generate_protocol(proj, test_type="SAT")

    def test_pdf_smoke(self, tmp_path):
        pytest.importorskip("reportlab")
        proj = _mk_project(tmp_path)
        r = spg.run_protocol(proj, test_type="SAT", lang="de", pdf=True)
        assert r.pdf_path is not None, f"PDF missing — {r.warnings}"
        assert r.pdf_path.exists() and r.pdf_path.stat().st_size > 0
