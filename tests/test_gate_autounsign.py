"""S-18 / B-P8 — Gate auto-unsign when approval-gate RDs change after signing.

Proof tests:  fix varken GECMELİ, fix geri alınırsa (auto-unsign mantığı
yoksa) KIRILMALI.  Smoke testi değil; koruyucu davranışı assert eder.

Kapsam:
  1.  advance_gate writes gate_rd_snapshots for approval gates
  2.  unmodified RDs → no auto-unsign
  3.  modified RD after signing → auto-unsign record in gate_history
  4.  deleted RD after signing → auto-unsign ("deleted")
  5.  legacy gate (no snapshot) → WARNING log only, no auto-unsign
  6.  gate_history chain NOT broken by auto-unsign (verify_gate_chain OK)
  7.  get_gate_model surfaces auto_unsign_warnings
  8.  non-approval gate RD changes → no auto-unsign (only approval gates)
  9.  re-sign after auto-unsign writes fresh snapshot
 10.  _check_and_apply_autounsign: root=None → no crash, no events
 11.  auto-unsign note contains RD name and S-18 reference
 12.  advance_gate: if prior approval gate was auto-unsigned, chain remains
      intact (prev_hash links correctly)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import factory_web as fw
from factory_web import (
    APPROVAL_GATES,
    _check_and_apply_autounsign,
    _effective_gate_rds,
    _gate_rd_hashes_for_gate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAYLOAD_FIELDS = ("gate", "when", "who", "signature", "note", "prev_hash")


def _make_record(gate: int, *, who: str = "A. Tester", note: str = "approved",
                 prev_hash: str = "", when: str = "2026-01-01",
                 signature: str = "A. Tester") -> dict:
    record = {
        "gate": gate, "when": when, "who": who,
        "signature": signature, "note": note, "prev_hash": prev_hash,
    }
    payload = json.dumps(
        {k: record[k] for k in _PAYLOAD_FIELDS},
        ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")
    record["hash"] = hashlib.sha256(payload).hexdigest()
    return record


def _bootstrap(project_root: Path, *, gate: int = 3):
    """Create minimal project structure for integration tests."""
    state = {"gate": gate, "data_classification": "PUBLIC"}
    (project_root / "PROJECT_STATE.json").write_text(
        json.dumps(state), encoding="utf-8",
    )
    (project_root / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: PUBLIC\n---\n", encoding="utf-8",
    )
    md = project_root / "metadata"
    md.mkdir(exist_ok=True)
    # Phase model: approval gates own no RDs of their own; their sign-off
    # certifies the upstream analysis (all gate 1-2 RDs, i.e. RD01-RD14). Create
    # every RD file so the effective snapshot set is populated regardless of
    # which gate is under test.
    for n in range(1, 15):
        rd_id = f"RD{n:02d}"
        (md / f"{rd_id}_placeholder.md").write_text(
            f"status: done\n# {rd_id}\noriginal content", encoding="utf-8",
        )


def _all_rds_done(monkeypatch):
    import project_analyzer

    class _Status:
        def __init__(self, s):
            self.status = s

    class _Analysis:
        rd_statuses = {f"RD{n:02d}": _Status("done") for n in range(1, 15)}

    monkeypatch.setattr(project_analyzer, "analyze_project", lambda root: _Analysis())


def _api(root: Path) -> fw.Api:
    api = fw.Api()
    api.root = root
    api.settings = {"username": "tester"}
    return api


def _review_all(api, sig: str = "Hans Becker (TÜV)") -> None:
    """3-state model: Gate 3 (the approval gate these tests exercise) now needs
    every produced RD pre-reviewed (green). RD05 requires a named sign-off.
    Re-reviewing is idempotent and re-stamps the current file hash, which is
    what the re-sign tests need after they edit an RD."""
    for n in range(1, 15):
        rd = f"RD{n:02d}"
        api.review_rd(rd, signature=(sig if rd == "RD05" else ""))


def _advance(api, sig: str = "Hans Becker (TÜV)") -> dict:
    _review_all(api, sig)
    r = api.advance_gate(signature=sig)
    assert r["ok"] is True, r
    return r


# ---------------------------------------------------------------------------
# TEST 1: advance_gate writes gate_rd_snapshots for approval gates
# ---------------------------------------------------------------------------

def test_advance_writes_gate_rd_snapshots_for_approval_gate(tmp_path, monkeypatch):
    """Fix varken: advance_gate (approval gate) → gate_rd_snapshots[str(gate)] yazılır.
    Fix geri alınırsa (snapshot yazılmazsa): state anahtarı yoktur → test kırılır.
    """
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    _advance(_api(tmp_path))

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    snaps = st.get("gate_rd_snapshots") or {}
    assert "3" in snaps, "gate_rd_snapshots must contain entry for gate 3 (approval gate)"
    snap3 = snaps["3"]
    assert snap3["gate"] == 3
    assert snap3["when"]
    # Hashes must include the RDs gate 3 certifies (the cumulative upstream
    # analysis — all gate 1-2 RDs, since gate 3 owns none of its own).
    hashes = snap3["hashes"]
    eff = _effective_gate_rds(3)
    assert eff, "Gate 3 effective RD set must not be empty (certifies upstream analysis)"
    for rd_id in eff:
        assert rd_id in hashes, f"{rd_id} must be in gate_rd_snapshots[3].hashes"
    assert all(len(h) == 64 for h in hashes.values() if not h.startswith("__"))


def test_non_approval_gate_does_not_write_gate_rd_snapshots(tmp_path, monkeypatch):
    """Gate 1 (non-approval) → gate_rd_snapshots yok veya boş."""
    _bootstrap(tmp_path, gate=1)
    _all_rds_done(monkeypatch)
    _advance(_api(tmp_path))

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    snaps = st.get("gate_rd_snapshots") or {}
    assert "1" not in snaps, "Non-approval gate must not write gate_rd_snapshots"


# ---------------------------------------------------------------------------
# TEST 2: unmodified RDs → no auto-unsign
# ---------------------------------------------------------------------------

def test_no_autounsign_when_rds_unchanged(tmp_path, monkeypatch):
    """Fix varken: RD değişmemişse auto-unsign olmamalı.
    Fix geri alınırsa (her zaman unsign etseydi) bu test kırılır.
    """
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    hist_before = len(st.get("gate_history") or [])

    # Call check without modifying any RD
    st2, events = _check_and_apply_autounsign(tmp_path, st)
    assert events == [], "No events when RDs are unchanged"
    assert len(st2.get("gate_history") or []) == hist_before


# ---------------------------------------------------------------------------
# TEST 3: modified RD after signing → auto-unsign record
# ---------------------------------------------------------------------------

def test_autounsign_on_rd_modification(tmp_path, monkeypatch):
    """Fix varken: RD değişince auto-unsign kaydı zincire eklenir.
    Fix geri alınırsa (check_and_apply çalışmasaydı): events boş → test kırılır.
    """
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    # Modify an RD that belongs to gate 3
    rd_file = next((tmp_path / "metadata").glob("RD06_*.md"))
    rd_file.write_text("status: done\n# RD06\nMODIFIED CONTENT", encoding="utf-8")

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    st2, events = _check_and_apply_autounsign(tmp_path, st)

    assert len(events) == 1, f"Expected 1 auto-unsign event; got {events}"
    assert events[0]["gate"] == 3
    assert any(c["rd"] == "RD06" and c["change"] == "modified"
               for c in events[0]["changed_rds"])

    # The auto-unsign record must appear in gate_history
    hist = st2.get("gate_history") or []
    unsign_record = next(
        (r for r in hist if r.get("who") == "system" and r.get("gate") == 3), None
    )
    assert unsign_record is not None, "Auto-unsign system record missing from gate_history"
    assert "auto-unsigned" in unsign_record["note"]
    assert unsign_record["signature"] == ""


# ---------------------------------------------------------------------------
# TEST 4: deleted RD after signing → auto-unsign with change="deleted"
# ---------------------------------------------------------------------------

def test_autounsign_on_rd_deletion(tmp_path, monkeypatch):
    """Fix varken: RD silinince auto-unsign "deleted" olarak işaretlenir.
    Fix geri alınırsa: deletion sentinel (__MISSING__) eşit sayılırdı → test kırılır.
    """
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    rd_file = next((tmp_path / "metadata").glob("RD06_*.md"))
    rd_file.unlink()

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    st2, events = _check_and_apply_autounsign(tmp_path, st)

    assert events, "Deleted RD must trigger auto-unsign"
    changed = events[0]["changed_rds"]
    assert any(c["rd"] == "RD06" and c["change"] == "deleted" for c in changed), \
        f"Expected RD06 deleted; got {changed}"


# ---------------------------------------------------------------------------
# TEST 5: legacy gate (no snapshot) → no auto-unsign, no crash
# ---------------------------------------------------------------------------

def test_legacy_gate_no_snapshot_no_autounsign(tmp_path):
    """Fix varken: snapshot'sız legacy gate → event üretilmez, crash olmaz.
    Fix geri alınırsa (legacy gate'ı da unsign etseydi): test kırılır.
    """
    _bootstrap(tmp_path, gate=3)
    # Manualy sign gate 3 WITHOUT any gate_rd_snapshots (legacy state)
    signed_record = _make_record(3, note="approved")
    st = {
        "gate": 4,
        "gate_history": [signed_record],
        # gate_rd_snapshots intentionally absent (legacy)
    }
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps(st), encoding="utf-8",
    )

    st2, events = _check_and_apply_autounsign(tmp_path, st)
    assert events == [], "Legacy gate without snapshot must not be auto-unsigned"


def test_legacy_snapshot_entry_empty_hashes_no_autounsign(tmp_path):
    """Snapshot anahtarı var ama hashes boş → uyarı loglanır, unsign yapılmaz."""
    _bootstrap(tmp_path, gate=3)
    signed_record = _make_record(3, note="approved")
    st = {
        "gate": 4,
        "gate_history": [signed_record],
        "gate_rd_snapshots": {"3": {"gate": 3, "when": "2026-01-01", "hashes": {}}},
    }
    (tmp_path / "PROJECT_STATE.json").write_text(json.dumps(st), encoding="utf-8")

    st2, events = _check_and_apply_autounsign(tmp_path, st)
    assert events == [], "Empty hashes in snapshot → warn only, no auto-unsign"


# ---------------------------------------------------------------------------
# TEST 6: gate_history chain NOT broken by auto-unsign (verify_gate_chain OK)
# ---------------------------------------------------------------------------

def test_autounsign_record_preserves_chain_integrity(tmp_path, monkeypatch):
    """Fix varken: auto-unsign kaydı zinciri bozmaz (verify_gate_chain hard ihlal vermez).
    Fix geri alınırsa (prev_hash yanlış hesaplansaydı): zincir kırılır → test kırılır.
    """
    from customer_report import verify_gate_chain

    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    # Modify RD to trigger auto-unsign
    rd_file = next((tmp_path / "metadata").glob("RD06_*.md"))
    rd_file.write_text("CHANGED", encoding="utf-8")

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    st2, events = _check_and_apply_autounsign(tmp_path, st)
    assert events, "Must have unsign event for this test to be meaningful"

    hist = st2.get("gate_history") or []
    violations = verify_gate_chain(hist)
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert not hard, f"Chain must not have hard violations after auto-unsign; hard={hard}"


# ---------------------------------------------------------------------------
# TEST 7: get_gate_model surfaces auto_unsign_warnings
# ---------------------------------------------------------------------------

def test_get_gate_model_exposes_auto_unsign_warnings(tmp_path, monkeypatch):
    """Fix varken: get_gate_model → auto_unsign_warnings listesi dolu.
    Fix geri alınırsa (alan yoksa veya boşsa): test kırılır.
    """
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    # Modify RD to trigger auto-unsign on next get_gate_model call
    rd_file = next((tmp_path / "metadata").glob("RD06_*.md"))
    rd_file.write_text("CHANGED FOR MODEL TEST", encoding="utf-8")

    model = api.get_gate_model()
    warnings = model.get("auto_unsign_warnings", [])
    assert warnings, (
        "get_gate_model must expose auto_unsign_warnings when an RD changed. "
        "Fix geri alınırsa bu alan boş kalır."
    )
    assert any("Gate 3" in w or "RD06" in w for w in warnings), \
        f"Warning must mention gate/RD; got {warnings}"


# ---------------------------------------------------------------------------
# TEST 8: non-approval gate RD changes → no auto-unsign
# ---------------------------------------------------------------------------

def test_non_approval_gate_rd_change_does_not_trigger_autounsign(tmp_path, monkeypatch):
    """Fix varken: gate 1 (non-approval) RD değişse de auto-unsign olmaz.
    Fix geri alınırsa (tüm gate'leri unsign etseydi): test kırılır.
    """
    _bootstrap(tmp_path, gate=1)
    _all_rds_done(monkeypatch)

    # Manually create a (non-approval gate) snapshot to simulate an edge case
    gate1_snap_hashes = _gate_rd_hashes_for_gate(tmp_path, 1)
    st = {
        "gate": 2,
        "gate_history": [_make_record(1, note="completed")],
        "gate_rd_snapshots": {
            "1": {"gate": 1, "when": "2026-01-01", "hashes": gate1_snap_hashes},
        },
    }
    (tmp_path / "PROJECT_STATE.json").write_text(json.dumps(st), encoding="utf-8")

    # Modify gate-1 RD
    rd_file = next((tmp_path / "metadata").glob("RD01_*.md"), None)
    if rd_file:
        rd_file.write_text("CHANGED", encoding="utf-8")

    st2, events = _check_and_apply_autounsign(tmp_path, st)
    assert events == [], (
        "Non-approval gate (gate 1) changes must NOT trigger auto-unsign. "
        "Only APPROVAL_GATES are monitored."
    )


# ---------------------------------------------------------------------------
# TEST 9: re-sign after auto-unsign writes fresh snapshot
# ---------------------------------------------------------------------------

def test_resign_after_autounsign_writes_fresh_snapshot(tmp_path, monkeypatch):
    """Fix varken: auto-unsign sonrası advance_gate yeniden imzalarsa
    taze snapshot yazılır.
    Fix geri alınırsa (snapshot silinmeseydi): eski hash kalır → test kırılır.
    """
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    # Read original hash
    st_before = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    original_hash = st_before["gate_rd_snapshots"]["3"]["hashes"].get("RD06", "")

    # Modify RD and apply auto-unsign
    rd_file = next((tmp_path / "metadata").glob("RD06_*.md"))
    rd_file.write_text("CHANGED CONTENT", encoding="utf-8")

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    st2, events = _check_and_apply_autounsign(tmp_path, st)
    assert events, "Must auto-unsign before re-sign test"

    # Persist the auto-unsign
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps(st2, indent=2, ensure_ascii=False), encoding="utf-8",
    )

    # Re-advance with gate back at 3 so we can re-sign
    st2["gate"] = 3
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps(st2, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    _advance(api, sig="Hans Becker (TÜV)")

    st_after = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    new_hash = st_after.get("gate_rd_snapshots", {}).get("3", {}).get("hashes", {}).get("RD06", "")
    assert new_hash, "Fresh snapshot must exist after re-sign"
    assert new_hash != original_hash, "Re-sign must store updated (new file content) hash"


# ---------------------------------------------------------------------------
# TEST 10: _check_and_apply_autounsign: root=None → no crash
# ---------------------------------------------------------------------------

def test_autounsign_root_none_no_crash():
    """Fix varken: root=None → (st, []) döner, exception fırlatmaz."""
    st = {"gate": 4, "gate_history": [], "gate_rd_snapshots": {"3": {"hashes": {"RD06": "abc"}}}}
    st2, events = _check_and_apply_autounsign(None, st)
    assert events == []
    # State unchanged
    assert st2 is st


# ---------------------------------------------------------------------------
# TEST 11: auto-unsign note contains RD name and S-18/B-P8 reference
# ---------------------------------------------------------------------------

def test_autounsign_note_contains_rd_name_and_policy_ref(tmp_path, monkeypatch):
    """Fix varken: auto-unsign kaydının note alanında RD adı ve S-18/B-P8 var.
    Fix geri alınırsa (farklı note yazılsaydı): assert kırılır.
    """
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    rd_file = next((tmp_path / "metadata").glob("RD06_*.md"))
    rd_file.write_text("CHANGED", encoding="utf-8")

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    st2, events = _check_and_apply_autounsign(tmp_path, st)
    assert events

    hist = st2.get("gate_history") or []
    sys_record = next(r for r in hist if r.get("who") == "system" and r.get("gate") == 3)
    note = sys_record["note"]
    assert "RD06" in note, f"Note must mention RD06; got: {note!r}"
    assert "S-18" in note, f"Note must reference S-18; got: {note!r}"
    assert "B-P8" in note, f"Note must reference B-P8; got: {note!r}"
    assert "auto-unsigned" in note, f"Note must start with 'auto-unsigned'; got: {note!r}"


# ---------------------------------------------------------------------------
# TEST 12: chain prev_hash integrity after auto-unsign + new advance
# ---------------------------------------------------------------------------

def test_chain_prev_hash_links_after_autounsign_and_readvance(tmp_path, monkeypatch):
    """Fix varken: auto-unsign + yeniden imzalama sonrası prev_hash zinciri doğru.
    Fix geri alınırsa (prev_hash yanlış hesaplansaydı): verify_gate_chain kırılır.
    """
    from customer_report import verify_gate_chain

    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    _advance(api)

    # Trigger auto-unsign
    rd_file = next((tmp_path / "metadata").glob("RD06_*.md"))
    rd_file.write_text("CHANGED", encoding="utf-8")

    st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    st2, events = _check_and_apply_autounsign(tmp_path, st)
    assert events

    # Persist; reset gate to 3 for re-advance
    st2["gate"] = 3
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps(st2, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    _advance(api, sig="Hans Becker (TÜV)")

    final_st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    violations = verify_gate_chain(final_st.get("gate_history") or [])
    hard = [v for v in violations if not v.startswith("WARNING")]
    assert not hard, f"Chain must be intact after auto-unsign + re-advance; hard={hard}"
