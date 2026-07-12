"""Proof tests — approved HMI wiring → generated code (dilim ⑤).

Pins the contract: NOTHING is auto-applied — an HMI→PLC command generates
code only with a NAMED engineer approval; Sts lamps/alarms are driven from
PROVEN legacy equations with operands translated via RD01; anything the
engine cannot prove or translate becomes an honest TODO inside the file —
never a guessed assignment.
"""

from __future__ import annotations

import json
from pathlib import Path

import hmi_wiring as hw
from hmi_codegen import generate_hmi_interface
from hmi_draft import generate_hmi_drafts

_RD01 = (
    "---\nstatus: DRAFT_UNVERIFIED\n---\n# RD01 IO List\n\n## Signals\n"
    "| Tag | Address | Type | Dir | Equipment | Description | Safety | "
    "SrcModule | OldTag | Status |\n"
    "|---|---|---|---|---|---|---|---|---|---|\n"
    "| BTN_START | %I0.0 | DI | IN | Pult | Taster Start | NO | PB9 | E 0.0 | DRAFT |\n"
    "| BTN_STOP | %I0.1 | DI | IN | Pult | Taster Stop | NO | PB9 | E 0.1 | DRAFT |\n"
)


def _mk_project(tmp_path: Path) -> Path:
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "sym.seq").write_text(
        "E 0.0\tST TASTER START TRANSPORT\n"
        "E 0.1\tST TASTER STOP TRANSPORT\n"
        "E 0.2\tSW WAHLSCHALTER BA AUTOMATIK\n"
        "A 5.0\tML MELDELEUCHTE TRANSPORT LAEUFT\n"
        "A 5.1\tLM STOERUNG SAMMELSTOERUNG\n",
        encoding="utf-8")
    (legacy / "PB9.AWL").write_text(
        "###PG:82000000\n"
        "[1\t\n\tA\tI 0.0\n\tAN\tI 0.1\n\t=\tQ 5.0\n\tBE\t]\n",
        encoding="utf-8")
    md = tmp_path / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD01_IO_List.md").write_text(_RD01, encoding="utf-8")
    generate_hmi_drafts(tmp_path, "WIRETEST")
    generate_hmi_interface(tmp_path)
    return tmp_path


def _cmd_tag(root: Path, legacy: str) -> str:
    return next(r["tag"] for r in hw.wiring_rows(root)
                if r["area"] == "Cmd" and r["legacy"] == legacy)


# ------------------------------------------------------------ decisions ---

def test_approval_needs_a_name(tmp_path):
    root = _mk_project(tmp_path)
    tag = _cmd_tag(root, "I0.0")
    ok, msg = hw.save_wiring_decision(root, tag, True, "x")
    assert ok is False and "name" in msg
    ok, _ = hw.save_wiring_decision(root, tag, True, "H. Becker, IBN")
    assert ok is True
    # rejection may be anonymous
    ok, _ = hw.save_wiring_decision(root, _cmd_tag(root, "I0.1"), False, "")
    assert ok is True
    rows = {r["tag"]: r for r in hw.wiring_rows(root)}
    assert rows[tag]["approved"] is True
    assert rows[_cmd_tag(root, "I0.1")]["approved"] is False


def test_unknown_tag_refused(tmp_path):
    root = _mk_project(tmp_path)
    ok, msg = hw.save_wiring_decision(root, "DB_Other.Cmd.x", True, "H. B, IBN")
    assert ok is False and "Unknown" in msg


# ------------------------------------------------------------ codegen -----

def test_sts_lamp_driven_from_proven_equation(tmp_path):
    root = _mk_project(tmp_path)
    r = hw.generate_wiring_code(root)
    assert r["ok"] and r["sts_driven"] == 1
    fc = (root / "_output" / hw.FC_FILE).read_text(encoding="utf-8")
    # proven Q5.0 = I0.0 AND NOT I0.1, translated to the NEW IEC tags
    assert '"BTN_START" AND NOT "BTN_STOP"' in fc
    assert '"DB_HMI".Sts.' in fc


def test_unproven_alarm_becomes_todo_not_guess(tmp_path):
    root = _mk_project(tmp_path)
    r = hw.generate_wiring_code(root)
    # the Sammelstoerung lamp (Q5.1) has NO proven equation in PB9
    assert any("DB_Alarm" in t and "no proven equation" in t
               for t in r["todo"])
    fc = (root / "_output" / hw.FC_FILE).read_text(encoding="utf-8")
    assert "TODO" in fc
    assert r["alarms_driven"] == 0


def test_cmd_generates_only_with_named_approval(tmp_path):
    root = _mk_project(tmp_path)
    r = hw.generate_wiring_code(root)
    fc = (root / "_output" / hw.FC_FILE).read_text(encoding="utf-8")
    assert r["cmd_merged"] == 0 and ".Mrg." not in fc, \
        "onaysız komut ASLA kod üretmez"
    tag = _cmd_tag(root, "I0.0")
    assert hw.save_wiring_decision(root, tag, True, "H. Becker, IBN")[0]
    r2 = hw.generate_wiring_code(root)
    fc2 = (root / "_output" / hw.FC_FILE).read_text(encoding="utf-8")
    assert r2["cmd_merged"] == 1
    member = tag.split(".")[-1]
    assert f'"DB_HMI".Mrg.{member} := "BTN_START" OR "DB_HMI".Cmd.{member};' in fc2
    assert "H. Becker, IBN" in fc2, "onay ismi kodda izlenebilir"
    # DB_HMI now carries the Mrg struct for the approved member only
    db = (root / "_output" / "DB_HMI.scl").read_text(encoding="utf-8")
    assert "Mrg : STRUCT" in db and db.count("approved merge") == 1


def test_rejected_cmd_stays_out(tmp_path):
    root = _mk_project(tmp_path)
    tag = _cmd_tag(root, "I0.0")
    assert hw.save_wiring_decision(root, tag, False, "", "HMI'dan start yok")[0]
    r = hw.generate_wiring_code(root)
    fc = (root / "_output" / hw.FC_FILE).read_text(encoding="utf-8")
    assert r["cmd_merged"] == 0 and ".Mrg." not in fc


# ------------------------------------------- F3: legacy operand fallback --
# E2E #2 finding: AI-produced RD11 rows sometimes omit "legacy E 0.0" from
# Notes; the wiring merge then dropped the row as "no physical twin". The
# fallback recovers the operand from RD01 deterministically (cited RD01 tag
# name first, then a UNIQUE HMI_TagID/member stem match). Ambiguity -> "".

def test_missing_legacy_note_recovered_from_rd01_citation(tmp_path):
    import re
    root = _mk_project(tmp_path)
    tag = _cmd_tag(root, "I0.0")
    from hmi_table_edit import KINDS
    fp = root / "metadata" / KINDS["rd11"]["file"]
    text = fp.read_text(encoding="utf-8")
    member = tag.split(".")[-1]
    fixed = []
    for line in text.splitlines():
        if f"DB_HMI.Cmd.{member}" in line:
            line = re.sub(r"legacy\s+[EI]\s?0\.0", "maps BTN_START", line)
            assert "legacy" not in line
        fixed.append(line)
    fp.write_text("\n".join(fixed), encoding="utf-8")

    rows = {r["tag"]: r for r in hw.wiring_rows(root)}
    assert hw._canon_s5(rows[tag]["legacy"]) == "I0.0", \
        "Notes'ta RD01 adı anılıyorsa operand oradan geri kazanılmalı"
    # and the recovered row still merges into generated code after approval
    assert hw.save_wiring_decision(root, tag, True, "H. Becker, IBN")[0]
    r = hw.generate_wiring_code(root)
    assert r["cmd_merged"] == 1


def test_legacy_fallback_stem_and_ambiguity():
    by_name = {"BTN_START": "I0.0", "BTN_STOP": "I0.1",
               "DI_MOTOR_EIN": "I2.0"}
    # unique stem match, type prefix stripped
    assert hw._legacy_fallback("HMI_MOTOR_EIN", "bMotor", "", by_name) == "I2.0"
    # exact name match via member (hungarian prefix stripped)
    assert hw._legacy_fallback("", "bBTN_START", "", by_name) == "I0.0"
    # ambiguous stem must NOT guess
    amb = {"DI_START": "I0.0", "DQ_START": "Q0.0"}
    assert hw._legacy_fallback("HMI_START", "bStart", "", amb) == ""
    # nothing known -> honest empty
    assert hw._legacy_fallback("HMI_X", "bX", "irrelevant note", by_name) == ""


# --------------------------------------------- S-5: no silent row drops --
# Audit M-02: an RD11 row whose PLC_Tag breaks the DB_HMI contract vanished
# with a silent `continue` — the engineer saw "0 open items" while a
# button was never wired. Contract now: such rows land in `problems`,
# the endpoint reports them and the GUI shows a dropped badge.

def test_contract_breaking_rd11_row_is_reported_not_dropped(tmp_path):
    root = _mk_project(tmp_path)
    from hmi_table_edit import KINDS
    fp = root / "metadata" / KINDS["rd11"]["file"]
    rogue = ("| HMI_ROGUE | MOT_PUMP_01_OUT | SCR001 | Indicator | "
             "Rogue | | | Read | | | | |")
    lines = fp.read_text(encoding="utf-8").splitlines()
    at = next(i for i, ln in enumerate(lines) if "DB_HMI.Cmd" in ln)
    lines.insert(at + 1, rogue)
    fp.write_text("\n".join(lines), encoding="utf-8")
    rows, problems = hw.wiring_rows_with_problems(root)
    assert rows, "geçerli satırlar etkilenmez"
    assert len(problems) == 1 and "HMI_ROGUE" in problems[0]
    assert "DB_HMI" in problems[0], "sebep sözleşmeyi adıyla anmalı"

    import factory_web as fw
    api = fw.Api()
    api.root = root
    g = api.get_hmi_wiring()
    assert g["ok"] and g["dropped"] == 1 and g["problems"]
    app_js = (Path(fw.__file__).resolve().parent.parent
              / "webgui" / "app.js").read_text(encoding="utf-8")
    assert "w.dropped" in app_js and "w.problems" in app_js, \
        "GUI düşürülen satırları göstermeli"


def test_wiring_endpoints(tmp_path):
    import factory_web as fw
    root = _mk_project(tmp_path)
    (root / "PROJECT_STATE.json").write_text(json.dumps({"gate": 4}),
                                             encoding="utf-8")
    api = fw.Api()
    api.root = root
    api.settings = {"username": "Eng"}
    g = api.get_hmi_wiring()
    assert g["ok"] and g["open"] > 0 and g["approved"] == 0
    tag = _cmd_tag(root, "I0.0")
    assert api.set_hmi_wiring(tag, True, "", "")["ok"] is False, \
        "endpoint da isimsiz onayı reddeder"
    assert api.set_hmi_wiring(tag, True, "H. Becker, IBN", "")["ok"] is True
    r = api.generate_hmi_wiring_code()
    assert r["ok"] and r["cmd_merged"] == 1 and "FC_HMI_Wiring" in r["msg"]
    # GUI wiring: proposal file opens as the approval grid
    app_js = (Path(fw.__file__).resolve().parent.parent
              / "webgui" / "app.js").read_text(encoding="utf-8")
    assert "HMI_WIRING_PROPOSAL.MD" in app_js
    assert "renderHmiWiringView" in app_js and "generate_hmi_wiring_code" in app_js
