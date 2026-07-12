"""Gate staleness: RDs edited AFTER a gate approval must surface as a visible
warning in the gate model (advisory — the gate itself must NOT regress).

Covers:
  1. advance_gate writes an rd_snapshot (gate, when, per-file SHA-256)
  2. no snapshot (legacy project)        -> stale_rds == []
  3. untouched RDs after advance        -> stale_rds == []
  4. RD modified after advance          -> reported as "modified"
  5. RD deleted after advance           -> reported as "deleted"
  6. brand-new RD added after advance   -> NOT stale (normal progress)
  7. staleness never changes the current gate (advisory only)
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw


def _bootstrap(project_root: Path, *, gate: int = 3, classification: str = "PUBLIC"):
    state = {"gate": gate, "data_classification": classification}
    (project_root / "PROJECT_STATE.json").write_text(
        json.dumps(state), encoding="utf-8",
    )
    (project_root / "PROJECT_MAESTRO.md").write_text(
        f"---\ndata_classification: {classification}\n---\n", encoding="utf-8",
    )
    md = project_root / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD01_IO_List.md").write_text("status: done\n| sig |", encoding="utf-8")
    (md / "RD03_Flowchart.md").write_text("status: done\n| S000 |", encoding="utf-8")


def _all_rds_done(monkeypatch):
    import project_analyzer

    class _Status:
        def __init__(self, s): self.status = s

    class _Analysis:
        rd_statuses = {f"RD{n:02d}": _Status("done") for n in range(1, 15)}

    monkeypatch.setattr(project_analyzer, "analyze_project", lambda root: _Analysis())


def _api(root: Path) -> fw.Api:
    api = fw.Api()
    api.root = root
    api.settings = {"username": "tester"}
    return api


def _advance(api) -> dict:
    # 3-state model: Gate 3 needs every RD with a file pre-reviewed (green).
    # The bootstrap only writes RD01 + RD03, so review just those.
    api.review_rd("RD01")
    api.review_rd("RD03")
    r = api.advance_gate(signature="Hans Becker (TÜV)")
    assert r["ok"] is True, r
    return r


# -- 1. snapshot is written on advance ---------------------------------------

def test_advance_writes_rd_snapshot(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    _advance(_api(tmp_path))

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    snap = st.get("rd_snapshot")
    assert snap, "advance_gate must write rd_snapshot"
    assert snap["gate"] == 3
    assert snap["when"]
    assert set(snap["hashes"]) == {"RD01_IO_List.md", "RD03_Flowchart.md"}
    assert all(len(h) == 64 for h in snap["hashes"].values())


# -- 2. legacy project without snapshot --------------------------------------

def test_no_snapshot_means_no_staleness(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    model = _api(tmp_path).get_gate_model()
    assert model["stale_rds"] == []


# -- 3..6. staleness detection ------------------------------------------------

def test_untouched_rds_are_not_stale(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)
    assert api.get_gate_model()["stale_rds"] == []


def test_modified_rd_is_reported(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    (tmp_path / "metadata" / "RD03_Flowchart.md").write_text(
        "status: done\n| S000 |\n| S010 |", encoding="utf-8",
    )
    stale = api.get_gate_model()["stale_rds"]
    assert len(stale) == 1
    assert stale[0]["rd_file"] == "RD03_Flowchart.md"
    assert stale[0]["change"] == "modified"
    assert stale[0]["gate"] == 3


def test_deleted_rd_is_reported(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    (tmp_path / "metadata" / "RD01_IO_List.md").unlink()
    stale = api.get_gate_model()["stale_rds"]
    assert [s["change"] for s in stale] == ["deleted"]
    assert stale[0]["rd_file"] == "RD01_IO_List.md"


def test_new_rd_after_advance_is_not_stale(tmp_path, monkeypatch):
    """Adding the next RD while working toward the next gate is normal
    progress, not a post-approval edit."""
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    (tmp_path / "metadata" / "RD04_Mode.md").write_text(
        "status: draft\n| M00 |", encoding="utf-8",
    )
    assert api.get_gate_model()["stale_rds"] == []


# -- 7. advisory only ----------------------------------------------------------

def test_staleness_does_not_regress_gate(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)
    gate_before = api.get_gate_model()["current"]

    (tmp_path / "metadata" / "RD03_Flowchart.md").write_text(
        "tampered", encoding="utf-8",
    )
    model = api.get_gate_model()
    assert model["current"] == gate_before
    assert model["stale_rds"], "warning expected, regression not"
