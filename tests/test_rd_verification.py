"""3-state per-RD verification model (draft 🟡 → reviewed 🟢 → locked 🔒).

Pins the verified UX behaviour:
  1.  review_rd is one-click for normal RDs (verified_by = settings username)
  2.  RD05 (Safety) demands a named sign-off; empty/short signatures are rejected
  3.  review records the file hash → editing the file demotes it (stale)
  4.  get_gate_model surfaces per-RD ui_state + a review_summary
  5.  Gate 3 (Human Review) cannot lock until every produced RD is reviewed
  6.  locking Gate 3 stamps every produced RD as locked
  7.  a named RD05 review satisfies the W-A2 safety gate
  8.  unreview_rd reverts a pre-approval
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
# review_rd
# ---------------------------------------------------------------------------

def test_review_one_click_uses_username(tmp_path):
    _bootstrap(tmp_path)
    r = _api(tmp_path).review_rd("RD04")
    assert r["ok"] is True
    assert r["reviewed_by"] == "M. Yilmaz"
    rec = _state(tmp_path)["rd_verifications"]["RD04"]
    assert rec["reviewed"] is True and rec["locked"] is False
    assert rec["content_hash"] and len(rec["content_hash"]) == 64


def test_review_rd05_requires_named_signature(tmp_path):
    _bootstrap(tmp_path)
    api = _api(tmp_path)
    r = api.review_rd("RD05", "")
    assert r["ok"] is False and r.get("needs_signature")
    assert "RD05" not in (_state(tmp_path).get("rd_verifications") or {})
    # single word / too short is rejected too
    assert api.review_rd("RD05", "ok")["ok"] is False
    # name + role is accepted
    r2 = api.review_rd("RD05", _RD05_SIG)
    assert r2["ok"] is True and r2["reviewed_by"] == _RD05_SIG


def test_review_missing_file_fails(tmp_path):
    _bootstrap(tmp_path)
    # RD99 has no file
    assert _api(tmp_path).review_rd("RD99")["ok"] is False


def test_edit_after_review_demotes_to_draft(tmp_path, monkeypatch):
    _bootstrap(tmp_path)
    _all_done(monkeypatch)
    api = _api(tmp_path)
    api.review_rd("RD04")
    # Edit the file → hash changes → stale, ui_state back to draft
    f = next((tmp_path / "metadata").glob("RD04_*.md"))
    f.write_text("status: DRAFT_UNVERIFIED\n# RD04\nEDITED", encoding="utf-8")
    states = fw._rd_review_states(tmp_path, _state(tmp_path),
                                  {f"RD{n:02d}": "done" for n in range(1, 15)})
    assert states["RD04"]["ui_state"] == "draft"
    assert states["RD04"]["stale"] is True
    assert states["RD04"]["reviewed"] is False


def test_unreview_reverts(tmp_path):
    _bootstrap(tmp_path)
    api = _api(tmp_path)
    api.review_rd("RD04")
    r = api.unreview_rd("RD04")
    assert r["ok"] is True
    assert "RD04" not in (_state(tmp_path).get("rd_verifications") or {})


# ---------------------------------------------------------------------------
# get_gate_model surface
# ---------------------------------------------------------------------------

def test_gate_model_exposes_ui_state_and_summary(tmp_path, monkeypatch):
    _bootstrap(tmp_path)
    _all_done(monkeypatch)
    api = _api(tmp_path)
    api.review_rd("RD01")
    model = api.get_gate_model()
    rs = model["review_summary"]
    assert rs["produced"] == 14
    assert rs["reviewed"] == 1
    assert "RD02" in rs["unreviewed"] and "RD01" not in rs["unreviewed"]
    assert rs["all_reviewed"] is False
    # gate-1 docs carry the per-RD ui_state
    g1 = next(g for g in model["gates"] if g["n"] == 1)
    rd01 = next(d for d in g1["docs"] if d["rd"] == "RD01")
    assert rd01["ui_state"] == "reviewed"
    rd02 = next(d for d in g1["docs"] if d["rd"] == "RD02")
    assert rd02["ui_state"] == "draft"


# ---------------------------------------------------------------------------
# Gate-3 lock
# ---------------------------------------------------------------------------

def _review_all(api):
    for n in range(1, 15):
        rd = f"RD{n:02d}"
        api.review_rd(rd, _RD05_SIG if rd == "RD05" else "")


def test_mark_na_requires_reason_and_excludes_from_gates(tmp_path):
    _bootstrap(tmp_path)
    api = _api(tmp_path)
    # reason required for a normal RD
    assert api.mark_rd_na("RD11")["ok"] is False
    r = api.mark_rd_na("RD11", "no HMI on this machine")
    assert r["ok"] is True and r["na"] is True
    st = _state(tmp_path)["rd_verifications"]["RD11"]
    assert st["na"] is True and st["na_reason"]
    # ui_state reflects N/A and it drops out of the review summary "produced"
    model = api.get_gate_model()
    assert "RD11" in model["review_summary"]["na"]
    assert "RD11" not in model["review_summary"]["unreviewed"]
    g2 = next(g for g in model["gates"] if g["n"] == 2)
    assert next(d for d in g2["docs"] if d["rd"] == "RD11")["ui_state"] == "na"


def test_rd05_na_requires_named_justification(tmp_path):
    _bootstrap(tmp_path)
    api = _api(tmp_path)
    assert api.mark_rd_na("RD05", "none")["ok"] is False        # not a named sign-off
    r = api.mark_rd_na("RD05", "No safety functions in scope — H. Becker, TÜV")
    assert r["ok"] is True


def test_mark_na_clears_stale_reviewer_fields(tmp_path):
    # Audit hygiene: marking N/A after a review must not leave a 'reviewed_by'
    # on the record (it would read as 'reviewed' in the audit trail).
    _bootstrap(tmp_path)
    api = _api(tmp_path)
    api.review_rd("RD11")
    api.mark_rd_na("RD11", "no HMI on this machine")
    rec = _state(tmp_path)["rd_verifications"]["RD11"]
    assert rec["na"] is True
    assert "reviewed_by" not in rec and "content_hash" not in rec
    assert rec.get("reviewed") is False and rec.get("locked") is False


def test_unmark_na_reverts(tmp_path):
    _bootstrap(tmp_path)
    api = _api(tmp_path)
    api.mark_rd_na("RD11", "no HMI")
    assert api.unmark_rd_na("RD11")["ok"] is True
    assert "RD11" not in (_state(tmp_path).get("rd_verifications") or {})


def test_na_rd_does_not_block_gate_advance(tmp_path):
    # Pure blocker check: a gate-2 RD that is empty but N/A must not block.
    rd = {f"RD{n:02d}": "done" for n in range(1, 15)}
    rd["RD11"] = "empty"
    b = fw._gate_advance_blockers(2, rd, "Hans Becker (TÜV)",
                                  rd_reviewed={}, rd_na={"RD11"})
    assert not any("RD11" in x for x in b), b
    # Without the N/A mark, RD11 empty DOES block.
    b2 = fw._gate_advance_blockers(2, rd, "Hans Becker (TÜV)", rd_reviewed={})
    assert any("RD11" in x for x in b2)


def test_gate1_advance_blocked_until_own_rds_reviewed(tmp_path, monkeypatch):
    # Rule (A): a gate's own produced RDs must be approved before leaving it.
    # Gate 1 owns RD01/02/03/13 — advancing 1->2 needs them green first.
    _bootstrap(tmp_path, gate=1)
    _all_done(monkeypatch)
    api = _api(tmp_path)
    r = api.advance_gate(signature="Hans Becker (TÜV)")
    assert r["ok"] is False
    assert any("not yet reviewed" in b and "Gate 1" in b for b in r["blockers"])
    # Approve the four discovery RDs → gate 1 advances.
    for rd in ("RD01", "RD02", "RD03", "RD13"):
        api.review_rd(rd)
    r2 = api.advance_gate(signature="Hans Becker (TÜV)")
    assert r2["ok"] is True, r2
    assert r2["gate"] == 2


def test_gate3_blocked_until_all_reviewed(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_done(monkeypatch)
    api = _api(tmp_path)
    # No reviews yet → blocked with a "not yet reviewed" reason.
    r = api.advance_gate(signature=_RD05_SIG)
    assert r["ok"] is False
    assert any("not yet reviewed" in b for b in r["blockers"])


def test_gate3_locks_all_rds_when_reviewed(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_done(monkeypatch)
    api = _api(tmp_path)
    _review_all(api)
    r = api.advance_gate(signature=_RD05_SIG)
    assert r["ok"] is True, r
    assert r["gate"] == 4
    vers = _state(tmp_path)["rd_verifications"]
    assert all(vers[f"RD{n:02d}"]["locked"] for n in range(1, 15)), vers


def test_topic_extraction_blocked_until_gate1_critical_approved(tmp_path):
    # Vites-2 (risk-based approval): Gate-2 generation waits only for the
    # CRITICAL Gate-1 outputs — RD01 (IO list) + RD03 (flowchart). RD02/RD13
    # join as drafts. Hits the precondition before provider/key machinery.
    _bootstrap(tmp_path, gate=2)
    api = _api(tmp_path)
    r = api.run_topic_extraction({"engineer": "M. Yilmaz", "confirmed": True})
    assert r["ok"] is False
    assert "Gate-1" in r["msg"] and "approve" in r["msg"].lower()
    assert "RD01" in r["msg"] and "RD03" in r["msg"]
    # Non-critical Gate-1 RDs must NOT be demanded any more.
    assert "RD02" not in r["msg"] and "RD13" not in r["msg"]
    # Approving only RD01 still blocks on RD03…
    api.review_rd("RD01")
    r2 = api.run_topic_extraction({"engineer": "M. Yilmaz", "confirmed": True})
    assert r2["ok"] is False and "RD03" in r2["msg"]
    # …and RD01+RD03 clears the precondition (later failures are key/provider,
    # never the Gate-1 review prereq).
    api.review_rd("RD03")
    r3 = api.run_topic_extraction({"engineer": "M. Yilmaz", "confirmed": True})
    assert "needs the Gate-1 analysis approved" not in (r3.get("msg") or "")


def test_rd05_named_review_satisfies_w_a2(tmp_path, monkeypatch):
    # RD05 reported as draft_unverified by analyze; a named review must let the
    # approval gate pass (W-A2) without RD05 ever being file-status 'approved'.
    _bootstrap(tmp_path, gate=3)

    import project_analyzer

    class _S:
        def __init__(self, s): self.status = s

    class _A:
        rd_statuses = {f"RD{n:02d}": _S("done") for n in range(1, 15)}
        rd_statuses["RD05"] = _S("draft_unverified")

    monkeypatch.setattr(project_analyzer, "analyze_project", lambda root: _A())

    api = _api(tmp_path)
    _review_all(api)  # RD05 gets the named sign-off
    r = api.advance_gate(signature=_RD05_SIG)
    assert r["ok"] is True, r
