"""Proof tests — baseline snapshots + REVISION_LOG (dilim ⑥).

Pins the contract: the baseline captures the FIRST version of every RD file
and is never overwritten; the revision log tells the delivery story
honestly (unchanged vs MODIFIED with SHA proof, plus every named decision:
grid edits, device decisions, waivers, wiring); the handover ZIP carries it.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import revision_log as rl

_RD01 = (
    "---\nstatus: DRAFT_UNVERIFIED\n---\n# RD01 IO List\n\n"
    "| Tag | Address | Type | Dir | Equipment | Description | Safety | "
    "SrcModule | OldTag | Status |\n"
    "|---|---|---|---|---|---|---|---|---|---|\n"
    "| BTN_START | %I0.0 | DI | IN | Pult | Taster Start | NO | PB9 | E 0.0 | DRAFT |\n"
)


def _project(tmp_path: Path) -> Path:
    md = tmp_path / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD01_IO_List.md").write_text(_RD01, encoding="utf-8")
    (md / "RD11_HMI.md").write_text("# RD11 draft v1\n", encoding="utf-8")
    (tmp_path / "PROJECT_STATE.json").write_text(json.dumps({"gate": 2}),
                                                 encoding="utf-8")
    return tmp_path


# ------------------------------------------------------------ baseline ----

def test_baseline_first_seen_wins(tmp_path):
    root = _project(tmp_path)
    captured = rl.snapshot_baseline(root)
    assert set(captured) == {"RD01_IO_List.md", "RD11_HMI.md"}
    base = root / "metadata" / rl.BASELINE_DIR / "RD11_HMI.md"
    assert base.read_text(encoding="utf-8") == "# RD11 draft v1\n"
    # engineer edits the working copy — the baseline must NOT follow
    (root / "metadata" / "RD11_HMI.md").write_text("# edited v2\n",
                                                   encoding="utf-8")
    assert rl.snapshot_baseline(root) == []          # nothing new
    assert base.read_text(encoding="utf-8") == "# RD11 draft v1\n", \
        "baseline ASLA üzerine yazılmaz — bütün mesele bu"


def test_generator_hooks_capture_baseline(tmp_path):
    # write_rd_draft (AI drafts) hook
    from rd_draft_writer import write_rd_draft
    md = tmp_path / "metadata"
    md.mkdir(exist_ok=True)
    write_rd_draft(tmp_path, "RD04", "# RD04\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    assert (md / rl.BASELINE_DIR / "RD04_Mode.md").exists() or \
           list((md / rl.BASELINE_DIR).glob("RD04*.md")), \
        "AI taslağı yazılınca baseline otomatik alınmalı"
    # hmi_draft hook
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "sym.seq").write_text("E 0.0\tST TASTER START\n", encoding="utf-8")
    from hmi_draft import generate_hmi_drafts
    generate_hmi_drafts(tmp_path, "T")
    assert list((md / rl.BASELINE_DIR).glob("RD11*.md"))


# ------------------------------------------------------------ the log -----

def test_revision_log_tells_the_story(tmp_path):
    root = _project(tmp_path)
    rl.snapshot_baseline(root)
    # engineer work: edit RD11, record a device decision + a wiring approval
    (root / "metadata" / "RD11_HMI.md").write_text("# edited v2\n",
                                                   encoding="utf-8")
    (root / "metadata" / "hmi_decisions.json").write_text(json.dumps(
        {"rd11": {"HMI_BTN_START": {"Label_EN": "Start"}}}), encoding="utf-8")
    dossier = root / "metadata" / "machine_dossier"
    dossier.mkdir(parents=True)
    (dossier / "decisions.json").write_text(json.dumps(
        {"%Q0.0": {"decision": "Ersatz durch FU", "impact": "Sollwert neu"}}),
        encoding="utf-8")
    (root / "metadata" / "gate3_waivers.json").write_text(json.dumps(
        {"abc123": {"title": "orphan ref", "reason": "bewusst",
                    "by": "H. Becker, IBN", "at": "2026-07-07"}}),
        encoding="utf-8")
    (root / "metadata" / "hmi_wiring.json").write_text(json.dumps(
        {"DB_HMI.Cmd.bStart": {"approved": True, "by": "H. Becker, IBN",
                               "note": "", "at": "2026-07-07"}}),
        encoding="utf-8")
    fp = rl.generate_revision_log(root)
    text = fp.read_text(encoding="utf-8")
    assert "**MODIFIED**" in text and "RD11_HMI.md" in text
    assert "unchanged since first generation" in text        # RD01
    assert "HMI_BTN_START" in text and "Label_EN = Start" in text
    assert "REPLACE" in text and "Ersatz durch FU" in text   # derived verb
    assert "bewusst" in text and "H. Becker, IBN" in text
    assert "APPROVED" in text and "DB_HMI.Cmd.bStart" in text


def test_log_is_honest_when_empty(tmp_path):
    root = _project(tmp_path)
    fp = rl.generate_revision_log(root)
    text = fp.read_text(encoding="utf-8")
    assert "no baseline captured" in text
    assert "_none recorded_" in text


def test_handover_zip_carries_revision_log(tmp_path):
    import factory_web as fw
    root = _project(tmp_path)
    rl.snapshot_baseline(root)
    api = fw.Api()
    api.root = root
    api.settings = {"username": "Eng"}
    r = api.export_handover_package()
    assert r["ok"]
    with zipfile.ZipFile(r["path"]) as zf:
        names = zf.namelist()
    assert "REPORTS/REVISION_LOG.md" in names, \
        "teslim zip'i revizyon hikâyesini taşımalı"
