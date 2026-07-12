"""Proof tests — HMI package (hmi_draft + hmi_codegen).

Pins the honesty rules: verbatim symbols (nothing invented/translated),
NOT-AUS never becomes an HMI tag, BCD thumbwheel bits collapse into ONE
NumericInput, engineer-edited RDs are never overwritten, and the wiring
proposal is a proposal — DB code contains no bindings.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from hmi_codegen import generate_hmi_interface  # noqa: E402
from hmi_draft import (  # noqa: E402
    GENERATED_MARKER, classify_pulpit, generate_hmi_drafts,
)


def _mk_pulpit_project(tmp_path: Path) -> Path:
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "sym.seq").write_text(
        "E 0.0\tST TASTER START TRANSPORT\n"
        "E 0.1\tST TASTER STOP TRANSPORT\n"
        "E 0.2\tSW WAHLSCHALTER BA AUTOMATIK\n"
        "E 0.3\tNOT-AUS PULT\n"
        "E 12.7\tST LAMPENTEST\n"
        "E 2.0\tSW CODIERS. 1/10 SEKUNDEN 2^0\n"
        "E 2.1\tSW CODIERS. 1/10 SEKUNDEN 2^1\n"
        "E 2.2\tSW CODIERS. 1/10 SEKUNDEN 2^2\n"
        "E 3.0\tSE ENDSCHALTER BAND VORNE\n"
        "A 5.0\tML MELDELEUCHTE TRANSPORT LAEUFT\n"
        "A 5.1\tLM STOERUNG SAMMELSTOERUNG\n"
        "A 5.2\tHUPE STOERMELDUNG\n"
        "A 5.3\tK SCHUETZ BAND 1\n",
        encoding="utf-8")
    # one proven lamp network so the indicator carries a real condition
    (legacy / "PB9.AWL").write_text(
        "###PG:82000000\n"
        "[1\t\n\tA\tI 0.0\n\tAN\tI 0.1\n\t=\tQ 5.0\n\tBE\t]\n",
        encoding="utf-8")
    return tmp_path


# ------------------------------------------------------------ classify ----

def test_pulpit_classification(tmp_path):
    inv = classify_pulpit(_mk_pulpit_project(tmp_path))
    assert [a for a, _ in inv.buttons] == ["I0.0", "I0.1"]
    assert [a for a, _ in inv.selectors] == ["I0.2"]
    assert len(inv.numeric_groups) == 1, "3 BCD biti TEK setpoint olmalı"
    stem, members = inv.numeric_groups[0]
    assert "SEKUNDEN" in stem and len(members) == 3
    assert [a for a, *_ in inv.indicators] == ["Q5.0"]
    assert {a for a, *_ in inv.alarms} == {"Q5.1", "Q5.2"}
    # honesty rules
    assert [a for a, *_ in inv.hardwired] == ["I0.3"], "NOT-AUS fiziksel kalır"
    assert any("LAMPENTEST" in n for _a, n, _r in inv.dropped)
    # field devices (Endschalter, Schütz) are NOT HMI material
    all_hmi = {a for a, *_ in inv.buttons} | {a for a, *_ in inv.indicators}
    assert "I3.0" not in all_hmi and "Q5.3" not in all_hmi


def test_indicator_carries_proven_condition(tmp_path):
    inv = classify_pulpit(_mk_pulpit_project(tmp_path))
    _addr, _name, cond = inv.indicators[0]
    assert "I0.0" in cond and "NOT" in cond, \
        "lamba koşulu kanıtlı denklemden gelmeli"


# ------------------------------------------------------------- drafts -----

def test_drafts_written_with_marker_and_verbatim_labels(tmp_path):
    root = _mk_pulpit_project(tmp_path)
    r = generate_hmi_drafts(root, "TESTPROJ")
    assert set(r["written"]) == {"RD11_HMI.md", "RD08_Alarm.md"}
    rd11 = (root / "metadata" / "RD11_HMI.md").read_text(encoding="utf-8")
    assert GENERATED_MARKER in rd11 and "status: DRAFT" in rd11
    assert "ST TASTER START TRANSPORT" in rd11, "etiket birebir sembol"
    assert "NOT-AUS PULT" in rd11 and "stays physical" in rd11
    rd08 = (root / "metadata" / "RD08_Alarm.md").read_text(encoding="utf-8")
    assert "ALM0001" in rd08 and "HUPE" in rd08
    # horn → Critical → AcknRequired Y (validator rule respected)
    horn_row = next(l for l in rd08.splitlines() if "HUPE" in l)
    assert "| Critical |" in horn_row and "| Y |" in horn_row


def test_engineer_rd_is_never_overwritten(tmp_path):
    root = _mk_pulpit_project(tmp_path)
    meta = root / "metadata"
    meta.mkdir(exist_ok=True)
    engineer_text = ("# RD11_HMI\n```yaml\nfilled_by: Ing. Mueller\n"
                     "status: REVIEWED\n```\nhand-tuned content\n")
    (meta / "RD11_HMI.md").write_text(engineer_text, encoding="utf-8")
    r = generate_hmi_drafts(root, "TESTPROJ")
    assert "RD11_HMI.md" not in r["written"]
    assert any("RD11" in x for x in r["refused"])
    assert (meta / "RD11_HMI.md").read_text(
        encoding="utf-8") == engineer_text, "mühendis içeriği DOKUNULMAZ"


# ------------------------------------------------------------- codegen ----

def test_interface_generation_from_drafts(tmp_path):
    root = _mk_pulpit_project(tmp_path)
    generate_hmi_drafts(root, "TESTPROJ")
    r = generate_hmi_interface(root)
    assert r["ok"] and r["problems"] == []
    db = (root / "_output" / "DB_HMI.scl").read_text(encoding="utf-8")
    assert 'DATA_BLOCK "DB_HMI"' in db
    assert db.count(": Bool;") == 4, "2 buton + 1 selektör (Cmd) + 1 lamba (Sts)"
    assert ": Int;" in db and "[0..999]" in db, "BCD → sınırlı Int setpoint"
    alarm = (root / "_output" / "DB_Alarm.scl").read_text(encoding="utf-8")
    assert "ALM0001" in alarm and "ALM0002" in alarm
    wp = (root / "_output" / "HMI_WIRING_PROPOSAL.md").read_text(
        encoding="utf-8")
    assert "NOT auto-applied" in wp and "engineer" in wp
    # the DB itself must not contain any binding to program logic
    assert "FB_" not in db and ":=" not in db.split("STRUCT", 1)[1].split(
        "BEGIN")[0].replace("S7_Optimized_Access := 'TRUE'", "")


def test_interface_requires_rd11(tmp_path):
    r = generate_hmi_interface(tmp_path)
    assert not r["ok"] and "RD11" in r["msg"]


def test_prefix_code_symbols_classify(tmp_path):
    """Legacy-plant symbols use device-class PREFIX codes, not words —
    "ST START ZYKLUS" is a button even though TASTER never appears
    (live finding: word-matching found 0/43 buttons on the test machine).
    RESERVE entries never become tags."""
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "sym.seq").write_text(
        "E 7.4\tST ANGEWAEHLTE BETRIEBSART EIN\n"
        "E 7.0\tSW EINRICHTBETRIEB\n"
        "E 7.3\tRESERVE\n"
        "A 41.0\tH STOERUNG HYDRAULIK\n"
        "A 41.1\tH KETTE 1N LAEUFT\n"
        "A 41.2\tHU HUPE STOERMELDUNG\n"
        "A 41.3\tReserve\n",
        encoding="utf-8")
    inv = classify_pulpit(tmp_path)
    assert [a for a, _ in inv.buttons] == ["I7.4"]
    assert [a for a, _ in inv.selectors] == ["I7.0"]
    assert [a for a, *_ in inv.indicators] == ["Q41.1"]
    assert {a for a, *_ in inv.alarms} == {"Q41.0", "Q41.2"}
    everything = ([a for a, *_ in inv.buttons] + [a for a, *_ in inv.selectors]
                  + [a for a, *_ in inv.indicators]
                  + [a for a, *_ in inv.alarms])
    assert "I7.3" not in everything and "Q41.3" not in everything
