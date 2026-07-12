"""Proof tests — E2E finding fixes B1/B5/B6/B7/B8 (E2E blind-test run #1, 2026-07-07).

B1a  hmi_draft may replace an AI topic-extraction draft (it is NOT engineer
     content) — but never a reviewed/locked RD.
B1b  RD11 schema gate rewrites bare PLC_Tag cells to the DB_HMI contract,
     deterministically and with a visible banner.
B5   baseline snapshots skip pristine templates (no fake "MODIFIED").
B6   customer report accepts the 3-state RD05 review (named sign-off) and
     still rejects a stale one (file edited after review).
B7   run_pipeline knows generate_hmi_interface / hmi_draft.
B8   AI spend accumulates into settings.total_cost_usd.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import factory_web as fw

_AI_HEADER = (
    "---\nstatus: DRAFT_UNVERIFIED\nsource: ai_preanalysis\nrd: RD11\n---\n\n")


# ------------------------------------------------------------ B1a ---------

def _pulpit(tmp_path: Path) -> Path:
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "sym.seq").write_text("E 0.0\tST TASTER START\n", encoding="utf-8")
    return tmp_path


def test_hmi_draft_keeps_richer_ai_draft_and_backs_up(tmp_path):
    """E2E #2 (mixer-line test machine): the AI extracts alarms from CODE — on a big machine
    far richer than the pulpit lamp list. hmi_draft must (1) never replace a
    richer draft, (2) back up whatever it does replace to _history."""
    from hmi_draft import generate_hmi_drafts
    root = _pulpit(tmp_path)
    md = root / "metadata"
    md.mkdir(exist_ok=True)
    rows = "\n".join(
        f"| ALM{i:04d} | A{i} | Warning | {i} | Q{i}.0 | x | | | t |  | t | N "
        "| | | | | | Active |" for i in range(1, 25))
    (md / "RD08_Alarm.md").write_text(
        _AI_HEADER.replace("RD11", "RD08")
        + "| AlarmID | AlarmName | Class | Priority | TriggerTag | c | l | u "
          "| en | tr | de | a | s | lt | ls | ra | n | st |\n"
        + "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        + rows + "\n", encoding="utf-8")
    (root / "PROJECT_STATE.json").write_text("{}", encoding="utf-8")
    r = generate_hmi_drafts(root, "T")
    assert "RD08_Alarm.md" not in r["written"], \
        "24 alarmlık AI taslağı 0-1 alarmlık pulpit taslağına EZDIRILMEZ"
    assert any("richer" in x for x in r["refused"])
    # RD11 (AI'sız) yazıldı ve analizci onu TASLAK okur (template değil —
    # Gate-2 donması E2E #2'nin köküydü)
    from project_analyzer import detect_rd_file_status
    status, _ = detect_rd_file_status(md / "RD11_HMI.md")
    assert status == "draft_unverified", status
    # replaced files are backed up: overwrite own draft → history entry
    r2 = generate_hmi_drafts(root, "T")
    assert "RD11_HMI.md" in r2["written"]
    assert list((md / "_history").glob("*_RD11_HMI.md")), \
        "değiştirilen taslak _history'ye yedeklenmeli — veri kaybı yok"


def test_hmi_draft_replaces_ai_draft_but_not_reviewed(tmp_path):
    from hmi_draft import generate_hmi_drafts
    root = _pulpit(tmp_path)
    md = root / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD11_HMI.md").write_text(_AI_HEADER + "| bare | table |\n",
                                    encoding="utf-8")
    (root / "PROJECT_STATE.json").write_text("{}", encoding="utf-8")
    r = generate_hmi_drafts(root, "T")
    assert "RD11_HMI.md" in r["written"], \
        "AI taslağı mühendis içeriği DEĞİL — deterministik taslak yerine geçebilmeli"
    # now mark RD11 as reviewed → the draft becomes signed work, hands off
    (md / "RD11_HMI.md").write_text(_AI_HEADER + "| reviewed | content |\n",
                                    encoding="utf-8")
    (root / "PROJECT_STATE.json").write_text(json.dumps(
        {"rd_verifications": {"RD11": {"reviewed": True}}}), encoding="utf-8")
    r2 = generate_hmi_drafts(root, "T")
    assert "RD11_HMI.md" not in r2["written"]
    assert any("RD11" in x for x in r2["refused"])


# ------------------------------------------------------------ B1b ---------

_RD11_AI_TABLE = (
    "# RD11\n\n"
    "| HMI_TagID | PLC_Tag | ScreenRef | ElementType | Label_EN | Label_TR | "
    "Label_DE | ReadWrite | MinValue | MaxValue | EngUnit | Notes |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    "| HMI_AUTOMATIK_EIN | Automatik_Ein | SCR001 | Button | Auto on |  | "
    "Automatik ein | Write | | | | legacy E 0.0 |\n"
    "| HMI_SOLL_TEMP | Soll_Temp | SCR002 | NumericInput | Setpoint |  | "
    "Solltemperatur | Write | 0 | 99 | °C | |\n"
    "| HMI_LED_STOERUNG | LED_Stoerung | SCR001 | Indicator | Fault |  | "
    "Störung | Read | | | | legacy A 5.1 |\n"
    "| HMI_OK | DB_HMI.Cmd.bOk | SCR001 | Button | OK |  | OK | Write | | | | |\n")


def test_rd11_schema_gate_repairs_plc_tag_contract(tmp_path):
    from rd_table_schema import gate_rd11_draft
    fixed, rep = gate_rd11_draft(tmp_path, _RD11_AI_TABLE)
    assert rep.repaired_cells == 3          # the compliant row is untouched
    assert "DB_HMI.Cmd.bAutomatikEin" in fixed
    assert "DB_HMI.Set.iSollTemp" in fixed
    assert "DB_HMI.Sts.bLedStoerung" in fixed
    assert "DB_HMI.Cmd.bOk" in fixed
    assert "Schema gate" in fixed, "onarım görünür banner ister — sessiz olmaz"
    # the repaired file now feeds hmi_codegen without refusals
    md = tmp_path / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD11_HMI.md").write_text(fixed, encoding="utf-8")
    from hmi_codegen import generate_hmi_interface
    r = generate_hmi_interface(tmp_path)
    assert r["ok"] and r["problems"] == []
    assert r["counts"]["cmd"] == 2 and r["counts"]["set"] == 1 \
        and r["counts"]["sts"] == 1


def test_rd11_gate_wired_into_draft_writer(tmp_path):
    from rd_draft_writer import write_rd_draft
    (tmp_path / "metadata").mkdir()
    res = write_rd_draft(tmp_path, "RD11", _RD11_AI_TABLE)
    text = res.path.read_text(encoding="utf-8")
    assert "DB_HMI.Cmd.bAutomatikEin" in text
    assert res.warning and "repair" in res.warning.lower()


# ------------------------------------------------------------ B5 ----------

def test_baseline_skips_pristine_templates(tmp_path):
    import revision_log as rl
    md = tmp_path / "metadata"
    md.mkdir()
    (md / "RD01_IO_List.md").write_text("# real content\n| T | A |\n",
                                        encoding="utf-8")
    (md / "RD04_Mode.md").write_text(
        "project_id: <PROJECT_CODE>\n# template\n", encoding="utf-8")
    captured = rl.snapshot_baseline(tmp_path)
    assert captured == ["RD01_IO_List.md"], \
        "şablon baseline DEĞİLDİR — sahte MODIFIED'ın kökü buydu"
    # when RD04 later gets real content, THAT becomes its baseline
    (md / "RD04_Mode.md").write_text("# real RD04 draft\n", encoding="utf-8")
    assert rl.snapshot_baseline(tmp_path) == ["RD04_Mode.md"]


# ------------------------------------------------------------ B6 ----------

def test_customer_report_accepts_3state_rd05_review(tmp_path):
    from customer_report import _check_report_preconditions, \
        ReportPreconditionError
    md = tmp_path / "metadata"
    md.mkdir()
    rd05 = md / "RD05_Safety_DRAFT_UNVERIFIED.md"
    rd05.write_text("# RD05\nstatus: DRAFT_UNVERIFIED\n", encoding="utf-8")
    h = hashlib.sha256(rd05.read_bytes()).hexdigest()
    gate7 = [{"gate": 7, "note": "approved", "hash": "abc"}]
    # named 3-state review with matching hash → RD05 reason must be gone
    state = {"gate_history": gate7,
             "rd_verifications": {"RD05": {"reviewed": True,
                                           "reviewed_by": "H. Becker, TÜV",
                                           "content_hash": h}}}
    try:
        _check_report_preconditions(tmp_path, state)
        reasons = []
    except ReportPreconditionError as e:
        reasons = e.reasons
    assert not any("RD05" in r for r in reasons), reasons
    # stale review (file edited after sign-off) → blocked again (fail-closed)
    rd05.write_text("# RD05 edited after sign-off\n", encoding="utf-8")
    try:
        _check_report_preconditions(tmp_path, state)
        reasons = []
    except ReportPreconditionError as e:
        reasons = e.reasons
    assert any("RD05" in r for r in reasons), \
        "imzadan sonra düzenlenen RD05'e rapor açılmaz"


# ------------------------------------------------------------ B7 ----------

def test_run_pipeline_knows_hmi_actions(tmp_path):
    api = fw.Api()
    api.root = tmp_path
    api.settings = {"username": "Eng"}
    r = api.run_pipeline("generate_hmi_interface")
    assert "Unknown action" not in str(r.get("output", "")), \
        "GATE_CONFIG aksiyonu dispatcher'da tanınmalı"
    r2 = api.run_pipeline("hmi_draft")
    assert "Unknown action" not in str(r2.get("output", ""))


# ------------------------------------------------------------ B8 ----------

def test_ai_spend_accumulates(tmp_path):
    class _U:
        cost_usd = 0.0123
    api = fw.Api()
    api.settings = {"total_cost_usd": 0.0}
    api._add_cost(_U())
    api._add_cost(_U())
    assert api.settings["total_cost_usd"] == 0.0246
    # runner exposes the hook
    from workbench.core.ai_runner import AutoFlowRunner
    import inspect
    assert "on_usage" in inspect.signature(AutoFlowRunner.__init__).parameters
