"""C1 — TIA güvenlik bloğu tespiti fail-closed + RD05 kaynaklı.

Bu testler yalnızca saf yardımcı fonksiyonları doğrular (pythonnet/TIA gerekmez).
Gerçek provider.Download/import çağrısı bu ortamda test EDİLEMEZ (kod-incelemesi).
"""

from pathlib import Path

from bridges.tia.openness_core import (
    _safety_classification,
    _looks_like_safety,
    _read_rd05_safety_names,
    _discover_rd05_names,
)


def _scl(tmp_path: Path, name: str, body: str = "FUNCTION_BLOCK x\nEND_FUNCTION_BLOCK\n") -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_f_prefix_is_safety(tmp_path):
    # F_ prefix is the project's safety convention — must NOT slip through.
    f = _scl(tmp_path, "F_ESTOP1.scl")
    assert _safety_classification(f) == "safety"
    assert _looks_like_safety(f) is True


def test_emergency_name_is_safety(tmp_path):
    # The old heuristic missed this name entirely.
    f = _scl(tmp_path, "FB_EmergencyStop.scl")
    assert _safety_classification(f) == "safety"


def test_content_signature_is_safety(tmp_path):
    # Name looks neutral, but body declares F_TRIG / safety.
    body = "// SAFETY block\nFUNCTION_BLOCK Guard\nVAR x : F_TRIG; END_VAR\nEND_FUNCTION_BLOCK\n"
    f = _scl(tmp_path, "Guard.scl", body)
    assert _safety_classification(f) == "safety"


def test_standard_block_passes(tmp_path):
    f = _scl(tmp_path, "FB_ConveyorRun.scl",
             "FUNCTION_BLOCK FB_ConveyorRun\nVAR run : BOOL; END_VAR\nEND_FUNCTION_BLOCK\n")
    assert _safety_classification(f) == "standard"
    assert _looks_like_safety(f) is False


def test_unreadable_file_is_uncertain(tmp_path):
    # Fail-closed: a path we cannot read must not be assumed standard.
    missing = tmp_path / "does_not_exist.scl"
    assert _safety_classification(missing) == "uncertain"
    assert _looks_like_safety(missing) is True


def test_rd05_declared_name_is_safety(tmp_path):
    # A block whose name is declared in RD05 is safety even without other hints.
    declared = {"ConveyorGuard"}
    f = _scl(tmp_path, "ConveyorGuard.scl",
             "FUNCTION_BLOCK ConveyorGuard\nEND_FUNCTION_BLOCK\n")
    assert _safety_classification(f, declared) == "safety"
    # ...but standard without the RD05 list.
    assert _safety_classification(f) == "standard"


def test_read_rd05_names_from_metadata(tmp_path):
    meta = tmp_path / "metadata"
    meta.mkdir()
    (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
        "# RD05\n\n"
        "| FunctionID | FunctionName | F_InputTag | F_FB |\n"
        "|---|---|---|---|\n"
        "| SF001 | EStop_North_Panel | F_I_EStop_North | FB_F_EStop |\n",
        encoding="utf-8",
    )
    names = _read_rd05_safety_names(tmp_path)
    assert "EStop_North_Panel" in names
    assert "F_I_EStop_North" in names
    assert "FB_F_EStop" in names


def test_read_rd05_names_missing_returns_empty(tmp_path):
    assert _read_rd05_safety_names(tmp_path) == set()


# -- M-A2: declared-name match must be word-bounded, not substring --

def test_short_declared_name_does_not_match_unrelated_file(tmp_path):
    """A 2-3 char declared name (e.g. 'fb') must NOT mark every block as
    safety. Old substring match did exactly that and DOS'd the whole
    standard import pipeline."""
    declared = {"fb"}
    f = _scl(tmp_path, "FB_ConveyorRun.scl",
             "FUNCTION_BLOCK FB_ConveyorRun\nEND_FUNCTION_BLOCK\n")
    # Without F_ prefix or content hints, this must remain 'standard'.
    assert _safety_classification(f, declared) == "standard"


def test_substring_of_longer_name_not_treated_as_match(tmp_path):
    """Declared name 'stop' must not mark 'FB_LocalStop' / 'FB_LocalStopper'
    as safety on substring alone — semantics differ."""
    declared = {"stop"}
    f = _scl(tmp_path, "FB_LocalStopper.scl",
             "FUNCTION_BLOCK FB_LocalStopper\nEND_FUNCTION_BLOCK\n")
    # 'stop' is < 5 chars; per M-A2 it does NOT trigger the rule by itself.
    # The block stays standard because there are no other safety signals.
    assert _safety_classification(f, declared) == "standard"


def test_word_bounded_declared_name_still_matches(tmp_path):
    """A genuinely-declared safety block name remains detected: as exact
    token in the underscore-split filename."""
    declared = {"EmergencyStop"}
    f = _scl(tmp_path, "FB_EmergencyStop_Pilot.scl")
    # "FB_EmergencyStop_Pilot" splits to {"fb", "emergencystop", "pilot"};
    # 'emergencystop' is a token match (>=5 chars) -> safety.
    assert _safety_classification(f, declared) == "safety"


def test_exact_match_still_detected(tmp_path):
    """Exact filename match (case-insensitive) is always safety regardless
    of length."""
    declared = {"AB"}
    f = _scl(tmp_path, "ab.scl")
    assert _safety_classification(f, declared) == "safety"


def test_discover_rd05_from_scl_location(tmp_path):
    # SCL lives under <root>/_output/scl/, RD05 under <root>/metadata/.
    root = tmp_path / "proj"
    (root / "metadata").mkdir(parents=True)
    (root / "metadata" / "RD05_Safety.md").write_text(
        "| FunctionName | F_FB |\n|---|---|\n| WidgetGuard | FB_WidgetGuard |\n",
        encoding="utf-8",
    )
    scl_dir = root / "_output" / "scl"
    scl_dir.mkdir(parents=True)
    scl = scl_dir / "FB_WidgetGuard.scl"
    scl.write_text("FUNCTION_BLOCK FB_WidgetGuard\nEND_FUNCTION_BLOCK\n", encoding="utf-8")
    names = _discover_rd05_names([scl])
    assert "FB_WidgetGuard" in names or "WidgetGuard" in names
