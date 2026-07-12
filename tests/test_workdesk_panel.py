"""Proof tests — 3-part sidebar: Çalışma Masası + İnceleme (2026-07-07).

User decision: the passive Reports list is retired; the sidebar shows
① the tree, ② the engineer's DESK (every surface they EDIT or SIGN, with
honest status chips), ③ the read-only REVIEW list (reference RDs in
reading mode + deterministic reports).
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw


def _api(tmp_path: Path) -> fw.Api:
    md = tmp_path / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD01_IO_List.md").write_text("# rd01\n| Tag | Address |\n",
                                        encoding="utf-8")
    (md / "RD03_Flowchart.md").write_text("# rd03\n", encoding="utf-8")
    (tmp_path / "PROJECT_STATE.json").write_text(json.dumps({
        "gate": 2,
        "rd_verifications": {"RD09": {"na": True, "na_reason": "no comms"}},
    }), encoding="utf-8")
    (tmp_path / "REPORTS").mkdir()
    (tmp_path / "REPORTS" / "ASSEMBLY_REPORT.md").write_text("# rep\n",
                                                             encoding="utf-8")
    api = fw.Api()
    api.root = tmp_path
    api.settings = {"username": "Eng"}
    return api


def test_desk_lists_every_editable_surface_with_honest_state(tmp_path):
    r = _api(tmp_path).get_workdesk()
    assert r["ok"]
    by_kind = {d["kind"]: d for d in r["desk"]}
    # the five surfaces + the safety sign-off are ALWAYS on the desk
    for kind in ("rd:RD01", "rd:RD11", "rd:RD08", "decisions", "wiring",
                 "rd:RD05"):
        assert kind in by_kind, f"masa yüzeyi eksik: {kind}"
    assert by_kind["rd:RD01"]["state"] == "draft"       # file exists, no review
    assert by_kind["rd:RD11"]["state"] == "missing"     # honest: not produced
    assert by_kind["rd:RD05"]["state"] == "missing"


def test_reading_list_is_reference_rds_plus_reports(tmp_path):
    r = _api(tmp_path).get_workdesk()
    kinds = {(it["kind"], it.get("label")) for it in r["reading"]}
    assert ("rdread:RD03", "Logic Flow") in kinds       # produced ref RD
    assert ("report", "ASSEMBLY_REPORT") in kinds       # deterministic report
    labels = [it["label"] for it in r["reading"]]
    assert "Data Dictionary" not in labels, "üretilmemiş RD listelenmez"
    assert "Communications" not in labels, "N/A RD incelemeye düşmez"
    # desk surfaces never leak into the read-only list
    assert not any(it["kind"].startswith("rdread:RD01") for it in r["reading"])


def test_gui_wiring_three_part_sidebar():
    root = Path(fw.__file__).resolve().parent.parent
    html = (root / "webgui" / "index.html").read_text(encoding="utf-8")
    assert 'id="workdesk-panel"' in html and 'id="reading-panel"' in html
    assert 'id="reports-list"' not in html, "eski pasif rapor listesi emekli"
    assert 'id="btn-handover"' in html, "teslim düğmesi masada kalır"
    app_js = (root / "webgui" / "app.js").read_text(encoding="utf-8")
    assert "get_workdesk" in app_js
    assert "openRdReadingView" in app_js and "read-row" in app_js
    i18n = (root / "webgui" / "i18n.js").read_text(encoding="utf-8")
    assert "side.workdesk" in i18n and "side.reading" in i18n
