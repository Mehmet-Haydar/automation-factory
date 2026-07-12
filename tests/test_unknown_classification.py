"""Proof tests — #UNKNOWN classification (E2E #2, F4).

E2E #2 (mixer-line test machine) produced 295 flat "unknown" lines — unreadable. Contract
now: every unknown carries a class (operator_panel / internal_flag /
device_gap), the report groups them with device_gap FIRST (the only class
demanding action), and the summary message names the gap count. Nothing is
dropped: class counts always add up to the full unknown list.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from program_assembler import (  # noqa: E402
    AssemblyResult, UNKNOWN_CLASSES, _write_report, classify_unknown,
)


def _sig(name="", desc="", equipment="", address=""):
    return {"name": name, "desc": desc, "equipment": equipment,
            "address": address}


# ------------------------------------------------------------- classes ----

def test_operator_panel_keywords():
    assert classify_unknown(_sig("TASTER_START", "Taster Start Transport")) \
        == "operator_panel"
    assert classify_unknown(_sig("ML_1", "Meldeleuchte Stoerung")) \
        == "operator_panel"
    assert classify_unknown(_sig("X", "Wahlschalter Betriebsart")) \
        == "operator_panel", "panel wins over mode-flag when both match"
    assert classify_unknown(_sig("HUPE", "Hupe Pult")) == "operator_panel"


def test_internal_flag_keywords_and_merker_addresses():
    assert classify_unknown(_sig("BA_AUTO", "Betriebsart Automatik")) \
        == "internal_flag"
    assert classify_unknown(_sig("FREIGABE_X", "Freigabe Achse")) \
        == "internal_flag"
    assert classify_unknown(_sig("HELPER", "irgendwas", address="%M10.0")) \
        == "internal_flag", "Merker address -> internal flag"


def test_unmatched_stays_device_gap():
    """Conservative default: anything unrecognized demands review."""
    assert classify_unknown(_sig("XYZ_99", "Zentrifuge Sonderaggregat")) \
        == "device_gap"
    assert classify_unknown(_sig()) == "device_gap"


# ------------------------------------------------------------- report -----

def test_report_groups_unknowns_and_counts_add_up(tmp_path):
    res = AssemblyResult()
    res.ok = True
    res.msg = "x"
    res.unknown = [
        {"item": "TASTER_1", "reason": "r", "class": "operator_panel"},
        {"item": "BA_AUTO", "reason": "r", "class": "internal_flag"},
        {"item": "ZENTRIFUGE_9", "reason": "r", "class": "device_gap"},
        {"item": "LEGACY_NO_CLASS", "reason": "r"},   # pre-F4 dict shape
    ]
    path = _write_report(tmp_path, res)
    text = path.read_text(encoding="utf-8")
    gap_head = UNKNOWN_CLASSES["device_gap"]
    assert f"### {gap_head} (2)" in text, \
        "class'sız eski kayıt device_gap'e düşmeli (asla kaybolmaz)"
    assert f"### {UNKNOWN_CLASSES['operator_panel']} (1)" in text
    assert f"### {UNKNOWN_CLASSES['internal_flag']} (1)" in text
    assert text.index(gap_head) < text.index(UNKNOWN_CLASSES["operator_panel"]), \
        "aksiyon isteyen sınıf (device_gap) önce gelmeli"
    for item in ("TASTER_1", "BA_AUTO", "ZENTRIFUGE_9", "LEGACY_NO_CLASS"):
        assert item in text, "hiçbir unknown sessizce düşmez"


def test_loose_signals_get_classified_in_assembly():
    from program_assembler import group_devices
    sigs = [_sig("TASTER_START", "Taster Start", address="%I0.0"),
            _sig("BA_HAND", "Betriebsart Hand", address="%M2.0")]
    devices, loose = group_devices(sigs)
    assert not devices and len(loose) == 2
    assert [classify_unknown(s) for s in loose] \
        == ["operator_panel", "internal_flag"]
