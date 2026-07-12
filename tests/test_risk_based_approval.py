"""Proof tests — Vites-2: risk-based approval (14 approvals → RD01/RD03/RD05).

Field-audit B-04: mandatory review of all 14 RDs cost half a working day
before the first line of SCL. New rule: only the CRITICAL set — RD01 (IO
list), RD03 (flowchart), RD05 (safety, named sign-off) — blocks the gates.
The other produced RDs are stamped "auto-accepted" by the Gate-3 lock with
an honest audit record; editing a file still breaks its seal (staleness).
"""
from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw


def _bootstrap(root: Path, *, gate: int = 3):
    (root / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": gate, "data_classification": "PUBLIC"}), encoding="utf-8")
    (root / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: PUBLIC\n---\n", encoding="utf-8")
    md = root / "metadata"
    md.mkdir(exist_ok=True)
    for n in range(1, 15):
        rd = f"RD{n:02d}"
        (md / f"{rd}_x.md").write_text(
            f"status: DRAFT_UNVERIFIED\n# {rd}\noriginal", encoding="utf-8")


def _all_done(monkeypatch):
    import project_analyzer

    class _S:
        def __init__(self, s): self.status = s

    class _A:
        rd_statuses = {f"RD{n:02d}": _S("done") for n in range(1, 15)}

    monkeypatch.setattr(project_analyzer, "analyze_project", lambda root: _A())


def _api(root: Path) -> fw.Api:
    api = fw.Api()
    api.root = root
    api.settings = {"username": "M. Yilmaz"}
    return api


def _state(root: Path) -> dict:
    return json.loads((root / "PROJECT_STATE.json").read_text(encoding="utf-8"))


_RD05_SIG = "H. Becker, TÜV"


# ---------------------------------------------------------------------------
# Pure blocker logic
# ---------------------------------------------------------------------------

def test_critical_set_is_exactly_io_flow_safety():
    assert fw.CRITICAL_RDS == {"RD01", "RD03", "RD05"}


def test_gate1_blocks_only_on_critical_rds():
    rds = {f"RD{n:02d}": "done" for n in range(1, 15)}
    # Nothing reviewed → only RD01/RD03 block gate 1 (its own critical RDs).
    reviewed = {f"RD{n:02d}": False for n in range(1, 15)}
    blockers = fw._gate_advance_blockers(1, rds, rd_reviewed=reviewed)
    joined = " ".join(blockers)
    assert "RD01" in joined and "RD03" in joined
    assert "RD02" not in joined and "RD13" not in joined, (
        "Kritik olmayan RD'ler gate-1'i bloklamamalı (Vites-2 regresyonu)"
    )
    # Critical reviewed → gate 1 free.
    reviewed.update({"RD01": True, "RD03": True})
    assert fw._gate_advance_blockers(1, rds, rd_reviewed=reviewed) == []


def test_gate3_lock_waits_only_for_critical(monkeypatch):
    rds = {f"RD{n:02d}": "done" for n in range(1, 15)}
    reviewed = {f"RD{n:02d}": False for n in range(1, 15)}
    reviewed.update({"RD01": True, "RD03": True, "RD05": True})
    blockers = fw._gate_advance_blockers(
        3, rds, signature=_RD05_SIG, rd_reviewed=reviewed)
    assert blockers == [], (
        f"Kritik set yeşilken gate-3 kilidi bloklanmamalı: {blockers}"
    )


def test_rd05_still_hard_blocks_gate3():
    """Safety never rides the fast lane — W-A2 stays intact."""
    rds = {f"RD{n:02d}": "done" for n in range(1, 15)}
    rds["RD05"] = "draft_unverified"
    reviewed = {f"RD{n:02d}": True for n in range(1, 15)}
    reviewed["RD05"] = False
    blockers = fw._gate_advance_blockers(
        3, rds, signature=_RD05_SIG, rd_reviewed=reviewed)
    assert any("RD05" in b for b in blockers)


# ---------------------------------------------------------------------------
# Lock stamps auto-accepted (honest audit trail)
# ---------------------------------------------------------------------------

def test_gate3_lock_auto_accepts_unreviewed_noncritical(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_done(monkeypatch)
    api = _api(tmp_path)
    # Only the critical set gets a human review.
    api.review_rd("RD01")
    api.review_rd("RD03")
    api.review_rd("RD05", _RD05_SIG)

    r = api.advance_gate(signature=_RD05_SIG)
    assert r["ok"] is True, r

    vers = _state(tmp_path)["rd_verifications"]
    # Everything is locked…
    assert all(vers[f"RD{n:02d}"]["locked"] for n in range(1, 15))
    # …human reviews stay attributed to the human…
    assert vers["RD01"]["reviewed_by"] == "M. Yilmaz"
    assert not vers["RD01"].get("auto_accepted")
    # …and the rest carries an HONEST machine-accept record.
    for rd in ("RD02", "RD04", "RD11", "RD14"):
        assert vers[rd].get("auto_accepted") is True, rd
        assert "auto-accepted" in vers[rd].get("reviewed_by", ""), rd


def test_gate_model_exposes_lock_ready_and_auto_list(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_done(monkeypatch)
    api = _api(tmp_path)
    rs0 = api.get_gate_model()["review_summary"]
    assert rs0["lock_ready"] is False
    assert set(rs0["critical_pending"]) == {"RD01", "RD03", "RD05"}

    api.review_rd("RD01"); api.review_rd("RD03"); api.review_rd("RD05", _RD05_SIG)
    rs1 = api.get_gate_model()["review_summary"]
    assert rs1["lock_ready"] is True
    assert "RD02" in rs1["auto_accept_on_lock"]
    # Docs carry the critical flag for the GUI.
    g1 = next(g for g in api.get_gate_model()["gates"] if g["n"] == 1)
    crit = {d["rd"] for d in g1["docs"] if d.get("critical")}
    assert crit == {"RD01", "RD03"}


def test_editing_auto_accepted_rd_breaks_its_seal(tmp_path, monkeypatch):
    """Auto-accept is not a free pass: an edit after the lock demotes the RD
    to stale/draft exactly like a human-reviewed one (auto-unsign chain)."""
    _bootstrap(tmp_path, gate=3)
    _all_done(monkeypatch)
    api = _api(tmp_path)
    api.review_rd("RD01"); api.review_rd("RD03"); api.review_rd("RD05", _RD05_SIG)
    assert api.advance_gate(signature=_RD05_SIG)["ok"] is True

    (tmp_path / "metadata" / "RD04_x.md").write_text(
        "status: DRAFT_UNVERIFIED\n# RD04\nEDITED", encoding="utf-8")
    st = _state(tmp_path)
    states = fw._rd_review_states(tmp_path, st,
                                  {f"RD{n:02d}": "done" for n in range(1, 15)})
    assert states["RD04"]["ui_state"] == "draft"
    assert states["RD04"]["stale"] is True
