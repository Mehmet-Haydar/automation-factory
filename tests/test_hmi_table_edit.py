"""Proof tests — RD11/RD08 grid-editor backbone (hmi_table_edit).

The rules that make the grid trustworthy: locked columns can never be
written, invalid values are refused with a reason, and a persisted
decision SURVIVES a full HMI-draft regeneration (the classic data-loss
moment, same guarantee as the dossier decisions.json).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from hmi_table_edit import (  # noqa: E402
    apply_edits, load_decisions, parse_table, save_decisions,
)

_RD11_MD = """# RD11
## Sheet 2: TagList

| HMI_TagID | PLC_Tag | ScreenRef | ElementType | Label_EN | Label_TR | Label_DE | ReadWrite | MinValue | MaxValue | EngUnit | Notes |
|-----------|---------|-----------|-------------|----------|----------|----------|-----------|----------|----------|---------|-------|
| HMI_BTN_START | DB_HMI.Cmd.bStart | SCR002 | Button | ST START | | ST START | Write | | | | legacy I7.5 |
| HMI_SET_ZEIT | DB_HMI.Set.iZeit | SCR020 | NumericInput | SW CODIERS | | SW CODIERS | Write | 0 | 999 | s | bits |
"""


def test_parse_table_finds_rows():
    cols, rows, lnos = parse_table(_RD11_MD, "HMI_TagID")
    assert cols[0] == "HMI_TagID" and len(rows) == 2
    assert rows[0]["Label_DE"] == "ST START"


def test_editable_edit_applies_locked_refused():
    edits = {"HMI_BTN_START": {"Label_TR": "Çevrim Başlat",
                               "Label_DE": "HACKED",       # locked!
                               "PLC_Tag": "DB_EVIL.x"}}    # locked!
    new_md, problems = apply_edits(_RD11_MD, "rd11", edits)
    assert "Çevrim Başlat" in new_md
    assert "HACKED" not in new_md and "DB_EVIL" not in new_md
    assert len(problems) == 2 and all("locked" in p for p in problems)


def test_unknown_key_and_bad_numeric_refused():
    new_md, problems = apply_edits(_RD11_MD, "rd11", {
        "HMI_NOPE": {"Label_TR": "x"},
        "HMI_SET_ZEIT": {"MaxValue": "abc"},
    })
    assert new_md == _RD11_MD, "hiçbir şey uygulanmamalı"
    assert any("not in table" in p for p in problems)
    assert any("numeric" in p for p in problems)


def test_rd08_critical_ackn_rule():
    md = """| AlarmID | AlarmName | Class | Priority | TriggerTag | TriggerCondition | LimitValue | LimitUnit | AlarmText_EN | AlarmText_TR | AlarmText_DE | AcknRequired | SuppressCondition | LinkedTimer | LinkedSF | RecommendedAction | Notes | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALM0001 | Hupe | Critical | 1 | Q5.2 | Q5.2 = TRUE | | | HUPE | | HUPE | Y | | | | | | Active |
"""
    _, problems = apply_edits(md, "rd08", {"ALM0001": {"AcknRequired": "N"}})
    assert any("ISA-18.2" in p for p in problems), \
        "Critical alarmda Ackn=N reddedilmeli"
    new_md, problems2 = apply_edits(md, "rd08", {
        "ALM0001": {"RecommendedAction": "Reset horn; check hydraulics"}})
    assert problems2 == [] and "Reset horn" in new_md


def test_decisions_survive_regeneration(tmp_path):
    """The whole point: grid edit → save decisions → hmi_draft regenerates
    from scratch → the engineer's values are still there."""
    from hmi_draft import generate_hmi_drafts

    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "sym.seq").write_text(
        "E 7.5\tST START ZYKLUS\nA 41.1\tH KETTE LAEUFT\n", encoding="utf-8")

    generate_hmi_drafts(tmp_path, "P1")
    rd11 = tmp_path / "metadata" / "RD11_HMI.md"
    _cols, rows, _ = parse_table(rd11.read_text(encoding="utf-8"),
                                 "HMI_TagID")
    tag = rows[0]["HMI_TagID"]

    save_decisions(tmp_path, "rd11", {tag: {"Label_TR": "Çevrim Başlat"}})
    text, _p = apply_edits(rd11.read_text(encoding="utf-8"), "rd11",
                           {tag: {"Label_TR": "Çevrim Başlat"}})
    rd11.write_text(text, encoding="utf-8")

    # full regeneration — the classic data-loss moment
    generate_hmi_drafts(tmp_path, "P1")
    assert "Çevrim Başlat" in rd11.read_text(encoding="utf-8"), \
        "yeniden üretim mühendisin grid kararını SİLMEMELİ"


def test_empty_value_drops_decision(tmp_path):
    (tmp_path / "metadata").mkdir(parents=True)
    save_decisions(tmp_path, "rd11", {"T1": {"Label_TR": "x"}})
    save_decisions(tmp_path, "rd11", {"T1": {"Label_TR": ""}})
    assert "T1" not in load_decisions(tmp_path).get("rd11", {})
