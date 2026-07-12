"""Proof tests — the "cheap model, premium result" quality machine.

Three deterministic layers make a low-cost model field-safe:
1. device_lexicon — bilingual DE/EN classification + port vocabulary
   (compound-noun aware, umlaut folded, fail-safe None).
2. rd01_crosscheck — the AI's RD01 is mechanically verified against the
   legacy sources: omissions, hallucinations and direction errors surface
   the moment the draft is written, not weeks later in TIA.
3. rd_draft_writer outer-fence strip — a whole-draft ```markdown wrapper
   (seen live from DeepSeek) must not survive into metadata/.
"""
from __future__ import annotations

from pathlib import Path

import device_lexicon as dl
import rd01_crosscheck as cc
from rd_draft_writer import _strip_outer_fence


# ---------------------------------------------------------------------------
# 1. Lexicon — classification
# ---------------------------------------------------------------------------

class TestLexiconClassify:
    def test_german_compounds_classify(self):
        assert dl.classify_text("Kreiselpumpe Kuehlwasser") == "FB_Motor_DOL"
        assert dl.classify_text("Abluftgeblaese Halle 2") == "FB_Motor_DOL"
        assert dl.classify_text("Schneckenfoerderer Silo") == "FB_Motor_DOL"
        assert dl.classify_text("Absperrklappe Zuluft") == "FB_Valve_OnOff"

    def test_starter_variants(self):
        assert dl.classify_text(
            "Dosierpumpe Freigabe Frequenzumrichter") == "FB_Motor_VFD"
        assert dl.classify_text(
            "Ruehrwerk Stern Dreieck Anlauf") == "FB_Motor_StarDelta"
        assert dl.classify_text(
            "Kompressor mit Sanftanlauf") == "FB_Motor_SoftStarter"

    def test_valve_variants(self):
        assert dl.classify_text("3-Wege-Ventil Heizkreis") == "FB_Valve_3Way"
        assert dl.classify_text("Stellventil Dampf") == "FB_Valve_Modulating"
        assert dl.classify_text("Magnetventil Wasser") == "FB_Valve_OnOff"

    def test_umlaut_spellings_are_equivalent(self):
        for spelling in ("Gebläse", "Geblaese", "Geblase"):
            assert dl.classify_text(spelling) == "FB_Motor_DOL", spelling

    def test_unknown_stays_none(self):
        assert dl.classify_text("Lichtschranke Sender Empfaenger") is None
        assert dl.classify_text("") is None

    def test_prefix_vote(self):
        assert dl.classify_text("", prefix="Y") == "FB_Valve_OnOff"
        assert dl.classify_text("", prefix="MOT") == "FB_Motor_DOL"

    def test_valve_wins_over_motor_in_mixed_text(self):
        # "Pumpenventil" is a valve even though "pumpe" appears in the word
        assert dl.classify_text("Ventil an der Pumpe") == "FB_Valve_OnOff"


class TestLexiconPorts:
    def test_german_electrical_synonyms(self):
        assert "motorschutz" in dl.port_synonyms("overload")
        assert "schuetz" in dl.port_synonyms("run")
        assert "rueckmeldung" in dl.port_synonyms("feedback")
        assert "stoerung" in dl.port_synonyms("fault")

    def test_unknown_port_token_matches_itself_only(self):
        assert dl.port_synonyms("frobnicate") == {"frobnicate"}


# ---------------------------------------------------------------------------
# 2. RD01 cross-check
# ---------------------------------------------------------------------------

AWL = """
ORGANIZATION_BLOCK OB 1
      U    E 0.0      // NotAus
      U    E 0.1      // Start
      =    A 4.0      // K1
      L    EW 10      // Temperatur
      T    AW 96      // Sollwert
      U    M 10.0     // Merker (internal - NOT IO)
      SE   T 5        // Timer (internal)
END_ORGANIZATION_BLOCK
"""

RD01_HEAD = (
    "| Tag | Address | Type | Dir | Equipment | Description | OldTag | Status |\n"
    "|-----|---------|------|-----|-----------|-------------|--------|--------|\n"
)


def _proj(tmp_path: Path, rows: str) -> Path:
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "OB1.AWL").write_text(AWL, encoding="utf-8")
    md = tmp_path / "metadata"
    md.mkdir()
    (md / "RD01_IO_List.md").write_text(RD01_HEAD + rows, encoding="utf-8")
    return tmp_path


FULL_ROWS = (
    "| S_NotAus | %I0.0 | DI | IN | MA1 | NotAus | E 0.0 | DRAFT_UNVERIFIED |\n"
    "| S_Start | %I0.1 | DI | IN | MA1 | Start | E 0.1 | DRAFT_UNVERIFIED |\n"
    "| K1 | %Q4.0 | DQ | OUT | M1 | Schuetz | A 4.0 | DRAFT_UNVERIFIED |\n"
    "| Temp | %IW10 | AI | IN | MA1 | Temperatur | EW 10 | DRAFT_UNVERIFIED |\n"
    "| Soll | %QW96 | AO | OUT | P1 | Sollwert | AW 96 | DRAFT_UNVERIFIED |\n"
)


def test_clean_rd01_passes(tmp_path):
    r = cc.crosscheck_rd01(_proj(tmp_path, FULL_ROWS))
    assert r["ok"], r
    assert r["covered"] == 5 and r["source_io"] == 5
    assert "clean" in r["summary"]


def test_internal_operands_not_required(tmp_path):
    """M-flags and timers are internal — their absence from RD01 is correct."""
    r = cc.crosscheck_rd01(_proj(tmp_path, FULL_ROWS))
    assert not any(op.startswith(("M", "T")) for op in r["missing_in_rd01"])


def test_omission_detected(tmp_path):
    rows = "\n".join(FULL_ROWS.splitlines()[:-1]) + "\n"   # drop AW 96
    r = cc.crosscheck_rd01(_proj(tmp_path, rows))
    assert r["ok"] is False
    assert "AW96" in r["missing_in_rd01"], (
        "AI'ın atladığı sinyal yakalanmadı — ucuz modelin 1 numaralı hata "
        "modu budur (OMISSION)."
    )


def test_hallucination_detected(tmp_path):
    rows = FULL_ROWS + (
        "| Ghost | %I9.7 | DI | IN | X1 | erfunden | E 9.7 | DRAFT_UNVERIFIED |\n")
    r = cc.crosscheck_rd01(_proj(tmp_path, rows))
    assert r["ok"] is False
    assert "E9.7" in r["not_in_source"], (
        "Kaynakta olmayan RD01 satırı yakalanmadı (HALLUCINATION)."
    )


def test_direction_mismatch_detected(tmp_path):
    rows = FULL_ROWS.replace(
        "| K1 | %Q4.0 | DQ |", "| K1 | %Q4.0 | DI |")
    r = cc.crosscheck_rd01(_proj(tmp_path, rows))
    assert r["ok"] is False
    assert any("K1" in d for d in r["dir_mismatch"])


def test_no_sources_is_not_an_error(tmp_path):
    (tmp_path / "metadata").mkdir()
    (tmp_path / "metadata" / "RD01_IO_List.md").write_text(
        RD01_HEAD + FULL_ROWS, encoding="utf-8")
    r = cc.crosscheck_rd01(tmp_path)
    assert r["ok"] is True and r["source_io"] == 0


# ---------------------------------------------------------------------------
# 3. Outer-fence strip
# ---------------------------------------------------------------------------

def test_whole_document_fence_unwrapped():
    doc = "```markdown\n# RD05\n| a | b |\n```"
    out = _strip_outer_fence(doc)
    assert out.startswith("# RD05") and "```" not in out


def test_inner_fences_survive():
    doc = "```markdown\n# RD03\n```mermaid\nflowchart TD\n```\ntext\n```"
    out = _strip_outer_fence(doc)
    assert "```mermaid" in out and out.startswith("# RD03")


def test_unfenced_document_untouched():
    doc = "# RD01\n| a | b |\n"
    assert _strip_outer_fence(doc) == doc


def test_partial_fence_kept():
    """A fence that CLOSES an opening block mid-document is not an outer
    wrapper — stripping it would corrupt the draft."""
    doc = "```scl\ncode\n```\nprose after the block"
    assert _strip_outer_fence(doc) == doc
