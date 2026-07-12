"""Proof tests — Gate-3 "Reconciliation & Preview" (gate3_consistency).

Pins the contract: deviations are findings, consistent facts are counts;
orange deviations exit through fix OR a named permanent waiver; the RED
class (NOT-AUS / EN ISO 13850) can never be waived — not even with a
signature; the Gate-3 bulk lock refuses to close over unresolved findings;
waivers land in the traceability matrix.
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw
import gate3_consistency as g3c

_RD01_HEADER = (
    "| Tag | Address | Type | Dir | Equipment | Description | NormalState | "
    "EngUnit | RangeMin | RangeMax | Safety | SrcModule | OldTag | Notes | Status |\n"
    "|-----|---------|------|-----|-----------|-------------|-------------|"
    "---------|----------|---------|--------|----------|--------|-------|--------|\n"
)

_RD01 = (
    "---\nstatus: DRAFT_UNVERIFIED\n---\n# RD01 IO List\n\n## Signals\n"
    + _RD01_HEADER
    + "| BTN_START | %I0.0 | DI | IN | Pult | Taster Start | | | | | NO | CODE | E 0.0 | | DRAFT_UNVERIFIED |\n"
    + "| BTN_STOP | %I0.1 | DI | IN | Pult | Taster Stop | | | | | NO | CODE | E 0.1 | | DRAFT_UNVERIFIED |\n"
    + "| LMP_RUN | %Q5.0 | DQ | OUT | Pult | Meldeleuchte laeuft | | | | | NO | CODE | A 5.0 | | DRAFT_UNVERIFIED |\n"
    + "| ALM_SAMMEL | %Q5.1 | DQ | OUT | Pult | Sammelstoerung | | | | | NO | CODE | A 5.1 | | DRAFT_UNVERIFIED |\n"
    + "| MOT_A | %Q0.0 | DQ | OUT | M1 | Motorschuetz Y-Delta | | | | | NO | CODE | A 0.0 | | DRAFT_UNVERIFIED |\n"
)

_RD11_HEADER = (
    "| HMI_TagID | PLC_Tag | ScreenRef | ElementType | Label_EN | Label_TR | "
    "Label_DE | ReadWrite | MinValue | MaxValue | EngUnit | Notes |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
)


def _rd11(rows: str) -> str:
    return "# RD11_HMI\n\n## Sheet 2: TagList\n\n" + _RD11_HEADER + rows


_RD11_CLEAN = _rd11(
    "| HMI_BTN_START | DB_HMI.Cmd.bStart | SCR002 | Button | Start |  | "
    "TASTER START | Write | | | | legacy I0.0 |\n"
    "| HMI_BTN_STOP | DB_HMI.Cmd.bStop | SCR002 | Button | Stop |  | "
    "TASTER STOP | Write | | | | legacy I0.1 |\n"
    "| HMI_LMP_RUN | DB_HMI.Sts.bRun | SCR001 | Indicator | Running |  | "
    "LAEUFT | Read | | | | legacy Q5.0 · shows: I0.0 AND NOT I0.1 |\n")

_RD08_HEADER = (
    "| AlarmID | AlarmName | Class | Priority | TriggerTag | TriggerCondition | "
    "LimitValue | LimitUnit | AlarmText_EN | AlarmText_TR | AlarmText_DE | "
    "AcknRequired | SuppressCondition | LinkedTimer | LinkedSF | "
    "RecommendedAction | Notes | Status |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
)

_RD08_CLEAN = (
    "# RD08_Alarm\n\n## Alarms\n\n" + _RD08_HEADER
    + "| ALM0001 | ASammel | Critical | 1 | Q5.1 | Q5.1 = TRUE | | | Sammel |  "
    "| Sammelstoerung | Y | | | | | legacy lamp | Active |\n")


def _project(tmp_path: Path, rd11: str = _RD11_CLEAN,
             rd08: str = _RD08_CLEAN, rd01: str = _RD01) -> Path:
    md = tmp_path / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD01_IO_List.md").write_text(rd01, encoding="utf-8")
    (md / "RD11_HMI.md").write_text(rd11, encoding="utf-8")
    (md / "RD08_Alarm.md").write_text(rd08, encoding="utf-8")
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 3}), encoding="utf-8")
    return tmp_path


def _decide(root: Path, entries: dict) -> None:
    out = root / "metadata" / "machine_dossier"
    out.mkdir(parents=True, exist_ok=True)
    (out / "decisions.json").write_text(
        json.dumps(entries, ensure_ascii=False), encoding="utf-8")


def _api(root: Path) -> fw.Api:
    api = fw.Api()
    api.root = root
    api.settings = {"username": "Eng"}
    return api


# ------------------------------------------------------------ checks ------

def test_clean_project_is_lock_ready(tmp_path):
    r = g3c.run(_project(tmp_path))
    assert r["findings"] == []
    assert r["lock_ready"] is True and r["unresolved"] == 0
    # consistency is COUNTED, not listed (management by exception)
    assert r["consistent"]["orphan_hmi_ref"] >= 4


def test_orphan_hmi_ref_detected(tmp_path):
    rd11 = _rd11("| HMI_BTN_GHOST | DB_HMI.Cmd.bGhost | SCR002 | Button | "
                 "Ghost |  | GEIST | Write | | | | legacy I9.4 |\n")
    r = g3c.run(_project(tmp_path, rd11=rd11))
    kinds = {f["kind"] for f in r["findings"]}
    assert "orphan_hmi_ref" in kinds
    f = next(f for f in r["findings"] if f["kind"] == "orphan_hmi_ref")
    assert f["severity"] == "deviation" and f["waivable"] is True
    assert "E9.4" in f["detail"]
    assert r["lock_ready"] is False


def test_condition_operands_are_evidence_not_references(tmp_path):
    """Notes text after 'shows:'/'condition:' is the proof equation — its
    operands must never be treated as tag references (no fake orphans)."""
    rd11 = _rd11("| HMI_LMP_X | DB_HMI.Sts.bX | SCR001 | Indicator | X |  | "
                 "X | Read | | | | legacy Q5.0 · shows: I9.4 AND NOT I8.6 |\n")
    r = g3c.run(_project(tmp_path, rd11=rd11))
    assert not [f for f in r["findings"] if f["kind"] == "orphan_hmi_ref"]


def test_pulpit_element_without_tag(tmp_path):
    root = _project(tmp_path)
    legacy = root / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "sym.seq").write_text(
        "E 0.0\tST TASTER START\n"
        "E 0.5\tST TASTER SONDERFALL\n",   # no RD11 row references I0.5
        encoding="utf-8")
    r = g3c.run(root)
    missing = [f for f in r["findings"] if f["kind"] == "pulpit_without_tag"]
    assert len(missing) == 1 and missing[0]["subject"] == "I0.5"


def test_drop_decision_not_propagated(tmp_path):
    root = _project(tmp_path)
    _decide(root, {"%Q5.0": {"decision": "DROP — Leuchte entfällt", "impact": ""}})
    r = g3c.run(root)
    f = next(f for f in r["findings"] if f["kind"] == "decision_not_propagated")
    assert f["severity"] == "deviation" and f["fix_target"] == "dossier"
    # the tag it points at is still referenced by RD11 (legacy Q5.0)
    assert "%Q5.0" in f["subject"]


def test_semantic_change_y_delta_to_vfd(tmp_path):
    root = _project(tmp_path)
    _decide(root, {"%Q0.0": {"decision": "REPLACE — neuer FU (Frequenzumrichter) statt Y-Δ",
                             "impact": "Drehzahlsollwert kommt dazu"}})
    r = g3c.run(root)
    f = next(f for f in r["findings"] if f["kind"] == "semantic_change")
    assert f["severity"] == "deviation"
    assert "%Q0.0" in f["subject"]


# ------------------------------------------------------------ red class ---

def test_notaus_hmi_button_is_red(tmp_path):
    rd11 = _rd11("| HMI_BTN_NOTAUS | DB_HMI.Cmd.bEStop | SCR002 | Button | "
                 "E-Stop |  | NOT-AUS | Write | | | | legacy I0.0 |\n")
    r = g3c.run(_project(tmp_path, rd11=rd11))
    f = next(f for f in r["findings"] if f["kind"] == "safety_on_hmi")
    assert f["severity"] == "red" and f["waivable"] is False
    assert "13850" in f["detail"]
    assert r["red"] >= 1 and r["lock_ready"] is False


def test_red_cannot_be_waived_even_with_signature(tmp_path):
    rd11 = _rd11("| HMI_BTN_NOTAUS | DB_HMI.Cmd.bEStop | SCR002 | Button | "
                 "E-Stop |  | NOT-AUS | Write | | | | legacy I0.0 |\n")
    root = _project(tmp_path, rd11=rd11)
    f = next(f for f in g3c.run(root)["findings"] if f["severity"] == "red")
    ok, msg = g3c.save_waiver(root, f, "wir wissen was wir tun", "H. Becker, TÜV")
    assert ok is False and "13850" in msg
    # even a stale waiver record on disk never neutralizes a red finding
    g3c._waivers_path(root).parent.mkdir(exist_ok=True)
    g3c._waivers_path(root).write_text(
        json.dumps({f["id"]: {"reason": "x", "by": "y"}}), encoding="utf-8")
    r = g3c.run(root)
    assert r["red"] >= 1 and r["lock_ready"] is False


def test_estop_indication_is_orange_not_red(tmp_path):
    rd11 = _rd11("| HMI_LMP_NOTAUS | DB_HMI.Sts.bEStop | SCR001 | Indicator | "
                 "E-Stop active |  | NOT-AUS GEDRUECKT | Read | | | | legacy Q5.0 |\n")
    r = g3c.run(_project(tmp_path, rd11=rd11))
    f = next(f for f in r["findings"] if f["kind"] == "safety_indication_on_hmi")
    assert f["severity"] == "deviation" and f["waivable"] is True


def test_safety_decision_into_hmi_is_red(tmp_path):
    rd01 = _RD01 + ("| ESTOP_1 | %I0.3 | SAFE_DI | IN | Pult | NOT-AUS Pult "
                    "| | | | | YES | CODE | E 0.3 | | DRAFT_UNVERIFIED |\n")
    root = _project(tmp_path, rd01=rd01)
    _decide(root, {"%I0.3": {"decision": "auf HMI Panel verlagern", "impact": ""}})
    r = g3c.run(root)
    f = next(f for f in r["findings"] if f["kind"] == "safety_decision_to_hmi")
    assert f["severity"] == "red" and f["waivable"] is False


# ------------------------------------------------------------ waivers -----

def test_waiver_flow_permanent_and_named(tmp_path):
    rd11 = _rd11("| HMI_BTN_GHOST | DB_HMI.Cmd.bGhost | SCR002 | Button | "
                 "Ghost |  | GEIST | Write | | | | legacy I9.4 |\n")
    root = _project(tmp_path, rd11=rd11)
    f = g3c.run(root)["findings"][0]
    # reason + name are mandatory
    assert g3c.save_waiver(root, f, "", "H. Becker, IBN")[0] is False
    assert g3c.save_waiver(root, f, "bewusst: Altsignal bleibt", "")[0] is False
    ok, msg = g3c.save_waiver(root, f, "bewusst: Altsignal bleibt", "H. Becker, IBN")
    assert ok is True and msg == ""
    # permanent: the next run marks it waived and unblocks the lock
    r2 = g3c.run(root)
    assert r2["findings"][0]["waived"] is True
    assert r2["findings"][0]["waiver"]["by"] == "H. Becker, IBN"
    assert r2["unresolved"] == 0 and r2["lock_ready"] is True


def test_traceability_matrix_carries_waivers(tmp_path):
    rd11 = _rd11("| HMI_BTN_GHOST | DB_HMI.Cmd.bGhost | SCR002 | Button | "
                 "Ghost |  | GEIST | Write | | | | legacy I9.4 |\n")
    root = _project(tmp_path, rd11=rd11)
    f = g3c.run(root)["findings"][0]
    assert g3c.save_waiver(root, f, "bewusst akzeptiert", "H. Becker, IBN")[0]
    from traceability_matrix import generate_traceability_matrix
    s = generate_traceability_matrix(root)
    text = Path(s.report_path).read_text(encoding="utf-8")
    assert "Conscious deviations" in text
    assert "H. Becker, IBN" in text and "bewusst akzeptiert" in text


# ------------------------------------------------------------ gate lock ---

def test_gate3_blockers_red_and_deviation(tmp_path):
    red = {"severity": "red", "title": "NOT-AUS on HMI"}
    dev = {"severity": "deviation", "title": "orphan"}
    blockers = fw._gate_advance_blockers(
        3, {}, "H. Becker, IBN", rd_reviewed={}, gate3_unresolved=[red, dev])
    joined = " ".join(blockers)
    assert "13850" in joined                      # red named explicitly
    assert "conscious choice" in joined           # deviations point at the screen
    # resolved list (or legacy caller passing None) adds no blocker
    assert not [b for b in fw._gate_advance_blockers(
        3, {}, "H. Becker, IBN", rd_reviewed={}, gate3_unresolved=[])
        if "13850" in b or "reconciliation" in b]
    assert not [b for b in fw._gate_advance_blockers(
        3, {}, "H. Becker, IBN", rd_reviewed={}, gate3_unresolved=None)
        if "13850" in b or "reconciliation" in b]


def test_endpoint_reports_and_waives(tmp_path):
    rd11 = _rd11("| HMI_BTN_GHOST | DB_HMI.Cmd.bGhost | SCR002 | Button | "
                 "Ghost |  | GEIST | Write | | | | legacy I9.4 |\n"
                 "| HMI_BTN_NOTAUS | DB_HMI.Cmd.bEStop | SCR002 | Button | "
                 "E-Stop |  | NOT-AUS | Write | | | | legacy I0.0 |\n")
    api = _api(_project(tmp_path, rd11=rd11))
    r = api.get_gate3_consistency()
    assert r["ok"] and r["lock_ready"] is False
    sev = [f["severity"] for f in r["findings"]]
    assert sev.index("red") < sev.index("deviation"), "red sorts first"
    ghost = next(f for f in r["findings"] if f["kind"] == "orphan_hmi_ref")
    red = next(f for f in r["findings"] if f["severity"] == "red")
    # waiving the RED is refused at the endpoint too
    w = api.waive_gate3_finding(red["id"], "trotzdem", "H. Becker, IBN")
    assert w["ok"] is False
    # name must satisfy the W-A1 signature rules
    w = api.waive_gate3_finding(ghost["id"], "bewusst", "x")
    assert w["ok"] is False and w.get("needs_signature")
    w = api.waive_gate3_finding(ghost["id"], "bewusst akzeptiert", "H. Becker, IBN")
    assert w["ok"] is True
    r2 = api.get_gate3_consistency()
    g2 = next(f for f in r2["findings"] if f["id"] == ghost["id"])
    assert g2["waived"] is True     # asked once, never again
    assert r2["lock_ready"] is False  # the red still stands
