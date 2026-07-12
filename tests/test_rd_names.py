"""W1 — RD adları kanonik kaynaktan (project_analyzer.RD_INPUT_NEEDS)."""

import importlib

fw = importlib.import_module("factory_web")
import project_analyzer


def test_rd_names_match_canonical_titles():
    expected = [
        (project_analyzer.RD_INPUT_NEEDS[f"RD{n:02d}"]["title"]).strip()
        for n in range(1, 15)
    ]
    assert fw.RD_NAMES == expected


def test_rd_names_length():
    assert len(fw.RD_NAMES) == 14


def test_known_canonical_labels():
    # The specific labels the old hard-coded list got wrong.
    assert fw.RD_NAMES[5] == "Motion"          # RD06 (was "Motors")
    assert fw.RD_NAMES[7] == "Alarm"           # RD08 (was "Sensors")
    assert fw.RD_NAMES[9] == "FBSpec"          # RD10 (was "Alarms")
    assert fw.RD_NAMES[11] == "UseCase"        # RD12 (was "Test Spec")
    assert fw.RD_NAMES[12].startswith("Annotation")     # RD13 (was "Documentation")
    assert fw.RD_NAMES[13].startswith("Modernization")  # RD14 (was "Delivery")
