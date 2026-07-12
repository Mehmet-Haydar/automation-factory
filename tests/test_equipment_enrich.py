"""Proof tests — deterministic RD01 Equipment column guarantee.

A/B/C benchmark (Schleifmaschine 4711 demo): the assembler
groups devices by the Equipment column; an AI draft that leaves it empty
collapses the wiring from 15 to 5 bound ports. The device reference is
already in the legacy data ("… * 7-M3 (EINLAUF)") — these tests pin the
deterministic extraction at all three layers: lexicon, RD01 file pass,
assembly-time fallback.
"""
from __future__ import annotations

from pathlib import Path

from device_lexicon import equipment_from_text
import rd01_autocomplete as ac
from program_assembler import group_devices


# ---------------------------------------------------------------------------
# Layer 1: lexicon extraction
# ---------------------------------------------------------------------------

def test_equipment_from_text_devref_patterns():
    assert equipment_from_text("KE ROLLENBAHN 1.1 * 7-M3  (EINLAUF)") == "M3"
    assert equipment_from_text("MOTORSCHUTZUEBERW. HYDRM. 5-M1") == "M1"
    assert equipment_from_text("ROLLENBAHN 3   * 8-M10 (STAT. II)") == "M10"


def test_equipment_from_text_rejects_prose():
    # a bare device letter in prose is ambiguous — never guessed
    assert equipment_from_text("MOTOR M3 EIN") == ""
    assert equipment_from_text("STATION II BEREIT") == ""
    assert equipment_from_text("") == ""
    assert equipment_from_text(None) == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Layer 2: RD01 file pass (enrich_equipment)
# ---------------------------------------------------------------------------

IOSEQ = (
    "\tI 5.0\tE 5.0\tKE ROLLENBAHN 1.1 * 7-M3  (EINLAUF)\n"
    "\tI 6.5\tE 6.5\tKE MOTORSCHUTZ SCHLEIFSPINDEL 5-M1\n"
    "\tQ 28.4\tA 28.4\tYH VEREINZELUNG SCHLIESSEN\n"
)

RD01 = (
    "| Tag | Address | Type | Dir | Equipment | Description | OldTag | Notes | Status |\n"
    "|-----|---------|------|-----|-----------|-------------|--------|-------|--------|\n"
    "| Rollenbahn11 | %I5.0 | DI | IN | | KE ROLLENBAHN 1.1 * 7-M3 (EINLAUF) | I 5.0 | | DRAFT_UNVERIFIED |\n"
    "| MotorschutzSpindel | %I6.5 | DI | IN | | KE MOTORSCHUTZ SPINDEL | I 6.5 | | DRAFT_UNVERIFIED |\n"
    "| VereinzelungZu | %Q28.4 | DQ | OUT | Y1 | YH VEREINZELUNG SCHLIESSEN | Q 28.4 | | DRAFT_UNVERIFIED |\n"
    "| StationBereit | %I7.0 | DI | IN | | STATION BEREIT LAMPE | | | DRAFT_UNVERIFIED |\n"
)


def _proj(tmp_path: Path) -> Path:
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "io.seq").write_text(IOSEQ, encoding="utf-8")
    (tmp_path / "metadata").mkdir()
    (tmp_path / "metadata" / "RD01_IO_List.md").write_text(RD01,
                                                           encoding="utf-8")
    return tmp_path


def test_enrich_fills_from_own_description(tmp_path):
    root = _proj(tmp_path)
    r = ac.enrich_equipment(root)
    assert r["ok"], r
    text = (root / "metadata" / "RD01_IO_List.md").read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if "Rollenbahn11" in ln)
    assert "| M3 |" in row, "kendi açıklamasındaki '7-M3' Equipment'a inmeli"


def test_enrich_fills_from_symbol_table_when_desc_has_no_ref(tmp_path):
    root = _proj(tmp_path)
    ac.enrich_equipment(root)
    text = (root / "metadata" / "RD01_IO_List.md").read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if "MotorschutzSpindel" in ln)
    # RD01 desc was shortened by the AI — the io.seq row still carries "5-M1"
    assert "| M1 |" in row


def test_enrich_never_overwrites_and_is_idempotent(tmp_path):
    root = _proj(tmp_path)
    r1 = ac.enrich_equipment(root)
    text1 = (root / "metadata" / "RD01_IO_List.md").read_text(encoding="utf-8")
    row = next(ln for ln in text1.splitlines() if "VereinzelungZu" in ln)
    assert "| Y1 |" in row, "AI'nın verdiği Y1 dokunulmaz kalmalı"
    r2 = ac.enrich_equipment(root)
    text2 = (root / "metadata" / "RD01_IO_List.md").read_text(encoding="utf-8")
    assert r1["filled"] == 2 and r2["filled"] == 0
    assert text1 == text2, "ikinci koşu dosyayı değiştirmemeli"


def test_enrich_leaves_unidentifiable_rows_empty(tmp_path):
    root = _proj(tmp_path)
    ac.enrich_equipment(root)
    text = (root / "metadata" / "RD01_IO_List.md").read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if "StationBereit" in ln)
    cells = [c.strip() for c in row.split("|")]
    assert cells[5] == "", "cihazsız satır uydurulmamalı (fail-safe)"


# ---------------------------------------------------------------------------
# Layer 3: assembly-time fallback (group_devices)
# ---------------------------------------------------------------------------

def test_group_devices_falls_back_to_desc_devref():
    signals = [
        {"name": "Rollenbahn11Ein", "type": "DI", "address": "%I5.0",
         "desc": "KE ROLLENBAHN 1.1 * 7-M3 (EINLAUF)", "equipment": ""},
        {"name": "Rollenbahn11Schuetz", "type": "DQ", "address": "%Q39.0",
         "desc": "ROLLENBAHN 1.1 SCHUETZ * 7-M3", "equipment": ""},
    ]
    devices, loose = group_devices(signals)
    assert len(devices) == 1 and not loose
    assert devices[0].device_id == "M3"
    assert len(devices[0].signals) == 2


def test_group_devices_explicit_equipment_still_wins():
    signals = [
        {"name": "X", "type": "DI", "address": "%I1.0",
         "desc": "irrelevant * 7-M3", "equipment": "Y9"},
    ]
    devices, _ = group_devices(signals)
    assert devices[0].device_id == "Y9", "dolu Equipment kolonu üstündür"


# ---------------------------------------------------------------------------
# Layer 4: port binding on real DACH vocabulary (D-run regressions)
# ---------------------------------------------------------------------------

def _m1_signals():
    return [
        {"name": "HydrMotorNetzschuetz", "type": "DI", "address": "I4.0",
         "desc": "KE HYDR.MOTOR NETZSCHUETZ", "equipment": "M1"},
        {"name": "HydrMotorDreiecks", "type": "DI", "address": "I4.1",
         "desc": "KE HYDR.MOTOR DREIECKS.", "equipment": "M1"},
        {"name": "HydrMotorSternschuetz", "type": "DI", "address": "I4.2",
         "desc": "KE HYDR.MOTOR STERNSCHUETZ", "equipment": "M1"},
        {"name": "HydrMotorUeberlast", "type": "DI", "address": "I4.6",
         "desc": "KE MOTORSCHUTZUEBERW. HYDRM. 5-M1", "equipment": "M1"},
    ]


def test_star_delta_compound_words_classify_star_delta():
    from device_lexicon import classify_text
    text = ("KE HYDR.MOTOR NETZSCHUETZ KE HYDR.MOTOR DREIECKS. "
            "KE HYDR.MOTOR STERNSCHUETZ")
    assert classify_text(text, prefix="M") == "FB_Motor_StarDelta", (
        "STERNSCHUETZ/DREIECKS bileşikleri yıldız-üçgen demektir")


def test_score_compound_and_abbreviation_hits():
    from program_assembler import _score
    # compound: overload synonym inside MOTORSCHUTZUEBERW.
    assert _score("in_bFeedbackOverload", _m1_signals()[3]) > 0
    # abbreviation: CamelCase tag token 'Rueckm'
    sig = {"name": "Rollenbahn11Rueckm", "type": "DI",
           "desc": "KE ROLLENBAHN 1.1 * 7-M3 (EINLAUF)", "equipment": "M3"}
    assert _score("in_bFeedbackRun", sig) > 0


def test_generic_token_never_triggers_longer_synonym():
    from program_assembler import _score
    # 'motor' alone must NOT hit the 'motorschutz' overload synonym
    sig = {"name": "HydrMotorNetzschuetz", "type": "DI",
           "desc": "KE HYDR.MOTOR NETZSCHUETZ", "equipment": "M1"}
    assert _score("in_bFeedbackOverload", sig) == 0, (
        "jenerik 'motor' token'ı overload'u tetiklememeli (yanlış kablolama)")


def test_analog_raw_input_binds_single_ai_and_refuses_ambiguity():
    from program_assembler import (
        Device, DeviceMatch, bind_device, load_contracts,
    )
    contracts = load_contracts()
    entry = contracts.get("FB_AnalogScale")
    if entry is None:
        import pytest
        pytest.skip("FB_AnalogScale contract not found")

    def make(dev_signals):
        dev = Device(device_id="B1", prefix="B", description="FUELLSTAND")
        dev.signals = dev_signals
        m = DeviceMatch(device=dev, contract_stem="FB_AnalogScale",
                        scl_path=entry["scl_path"],
                        contract_path=entry["contract_path"])
        bind_device(m)
        return m

    one = make([{"name": "FuellstandB1", "type": "AI", "address": "%IW96",
                 "desc": "FUELLSTAND TANK B1", "equipment": "B1",
                 "suffix": "FUELLSTANDB1"}])
    assert one.in_bindings.get("in_iRawValue") == "FuellstandB1", (
        "tek AI sinyali raw-value portuna bağlanmalı")

    two = make([
        {"name": "FuellstandB1", "type": "AI", "address": "%IW96",
         "desc": "FUELLSTAND TANK B1", "equipment": "B1", "suffix": "A"},
        {"name": "DruckB1", "type": "AI", "address": "%IW98",
         "desc": "DRUCK TANK B1", "equipment": "B1", "suffix": "B"},
    ])
    assert "in_iRawValue" not in two.in_bindings, (
        "iki eşit aday → belirsiz, bağlanmaz")
    assert any("ambiguous" in t for t in two.todos)


def test_status_outputs_never_take_field_signals():
    from program_assembler import (
        Device, DeviceMatch, bind_device, load_contracts,
    )
    contracts = load_contracts()
    entry = contracts.get("FB_Valve_OnOff")
    if entry is None:  # library layout changed — this test needs the block
        import pytest
        pytest.skip("FB_Valve_OnOff contract not found")
    dev = Device(device_id="Y2", prefix="Y", description="VEREINZELUNG")
    dev.signals = [
        {"name": "VereinzelungSchliessen", "type": "DQ", "address": "Q28.4",
         "desc": "YH VEREINZELUNG SCHLIESSEN", "equipment": "Y2",
         "suffix": "VEREINZELUNGSCHLIESSEN"},
        {"name": "VereinzelungOeffnen", "type": "DQ", "address": "Q28.5",
         "desc": "YH VEREINZELUNG OEFFNEN", "equipment": "Y2",
         "suffix": "VEREINZELUNGOEFFNEN"},
    ]
    m = DeviceMatch(device=dev, contract_stem="FB_Valve_OnOff",
                    scl_path=entry["scl_path"],
                    contract_path=entry["contract_path"])
    bind_device(m)
    assert m.out_bindings.get("out_bOpenOutput") == "VereinzelungOeffnen"
    assert "out_bReadyClosed" not in m.out_bindings, (
        "saha çıkışı durum-lambası portuna bağlanamaz (fail-safe)")
    assert "out_bReadyOpen" not in m.out_bindings
