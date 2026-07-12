"""W-A1 regresyonu: advance_gate kabul edilen imzayı hash-zincirli, append-only
bir history kaydına yazmalı; eski kayıtları silmemeli.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import factory_web as fw


def _bootstrap(project_root: Path, *, gate: int = 3, classification: str = "PUBLIC"):
    """Set up a minimal project that can advance gate `gate` without RDs
    blocking, by claiming all RDs are 'done' via a fake project_analyzer."""
    state = {"gate": gate, "data_classification": classification}
    (project_root / "PROJECT_STATE.json").write_text(
        json.dumps(state), encoding="utf-8",
    )
    # MAESTRO is needed so the classification guard doesn't reject the project.
    (project_root / "PROJECT_MAESTRO.md").write_text(
        f"---\ndata_classification: {classification}\n---\n", encoding="utf-8",
    )


def _all_rds_done(monkeypatch):
    """Make project_analyzer.analyze_project pretend every RD is done."""
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


def test_advance_with_invalid_signature_is_blocked(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)

    api = _api(tmp_path)
    result = api.advance_gate(signature="x")
    assert result["ok"] is False
    joined = " ".join(result["blockers"])
    assert "signature" in joined.lower() or "invalid" in joined.lower() or "short" in joined.lower()

    # PROJECT_STATE.json gate must NOT have advanced.
    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    assert st["gate"] == 3


def test_advance_with_valid_signature_appends_hashed_record(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)

    api = _api(tmp_path)
    r1 = api.advance_gate(signature="Hans Becker (TÜV)")
    assert r1["ok"] is True
    assert r1["gate"] == 4

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    hist = st["gate_history"]
    assert len(hist) == 1
    rec = hist[0]
    assert rec["gate"] == 3
    assert rec["signature"] == "Hans Becker (TÜV)"
    assert rec["prev_hash"] == ""
    # The hash must match a SHA-256 of the canonical record payload.
    payload = json.dumps(
        {k: rec[k] for k in ("gate", "when", "who", "signature", "note", "prev_hash")},
        ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")
    assert rec["hash"] == hashlib.sha256(payload).hexdigest()


def test_history_is_append_only_across_multiple_advances(tmp_path, monkeypatch):
    """W-A1: re-approving must NOT silently overwrite the prior record. The
    audit trail must keep every sign-off."""
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)

    api = _api(tmp_path)
    api.advance_gate(signature="Hans Becker (TÜV)")           # gate 3 -> 4
    api.advance_gate(signature="QA sign-off")                  # gate 4 (non-approval) -> 5
    api.advance_gate(signature="Maria Lopez (SIL eng)")        # gate 5 -> 6

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    hist = st["gate_history"]
    assert [h["gate"] for h in hist] == [3, 4, 5]
    # Hash chain integrity: each record's prev_hash matches the previous hash.
    for i in range(1, len(hist)):
        assert hist[i]["prev_hash"] == hist[i - 1]["hash"]
    # Final gate state landed where we expect.
    assert st["gate"] == 6
