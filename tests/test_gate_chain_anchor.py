"""Proof tests — gate record hash cross-anchored in the audit log (M-07).

The gate_history hash chain proves internal consistency only: a forger
rewriting PROJECT_STATE.json wholesale with recomputed hashes passes
verify_gate_chain. Contract now: every new gate record's hash is ALSO
written into the hash-chained AI decision log (gate_advance:<n> entry),
so hiding a forged signature requires rewriting both files consistently.
Anchor failure never blocks the (already approved) advance but must be
visible through the compliance warnings channel.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import factory_web as fw  # noqa: E402


def _bootstrap(project_root: Path, gate: int = 3):
    (project_root / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": gate, "data_classification": "PUBLIC"}),
        encoding="utf-8")
    (project_root / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: PUBLIC\n---\n", encoding="utf-8")


def _all_rds_done(monkeypatch):
    import project_analyzer

    class _Status:
        def __init__(self, s): self.status = s

    class _Analysis:
        rd_statuses = {f"RD{n:02d}": _Status("done") for n in range(1, 15)}

    monkeypatch.setattr(project_analyzer, "analyze_project",
                        lambda root: _Analysis())


def _api(root: Path) -> "fw.Api":
    api = fw.Api()
    api.root = root
    api.settings = {"username": "tester"}
    return api


def test_gate_advance_anchors_record_hash_in_audit_log(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)
    api = _api(tmp_path)
    r = api.advance_gate(signature="Hans Becker (TUV)")
    assert r["ok"] is True

    rec = json.loads((tmp_path / "PROJECT_STATE.json")
                     .read_text(encoding="utf-8"))["gate_history"][-1]
    assert rec.get("audit_anchor") is True
    log = (tmp_path / "AI_DECISION_LOG.jsonl").read_text(encoding="utf-8")
    assert rec["hash"] in log, "record hash must sit in the audit chain"
    assert "gate_advance:3" in log

    # the anchor field sits OUTSIDE the hash payload: chain still verifies
    from customer_report import verify_gate_chain
    violations = [v for v in verify_gate_chain([rec])
                  if not v.startswith("WARNING")]
    assert not violations, violations


def test_anchor_failure_is_visible_not_silent(tmp_path, monkeypatch):
    _bootstrap(tmp_path, gate=3)
    _all_rds_done(monkeypatch)

    def _boom(*a, **kw):
        raise RuntimeError("log disk full")

    monkeypatch.setattr(fw, "_audit_log", _boom)
    fw._flush_warnings()
    api = _api(tmp_path)
    r = api.advance_gate(signature="Hans Becker (TUV)")
    assert r["ok"] is True, "approved advance must not be hostage to the log"

    rec = json.loads((tmp_path / "PROJECT_STATE.json")
                     .read_text(encoding="utf-8"))["gate_history"][-1]
    assert rec.get("audit_anchor") is False
    warns = (r.get("_warnings") or []) + fw._flush_warnings()
    assert any("anchored" in str(w.get("msg", w)) for w in warns), \
        "çapa hatası sessiz kalamaz"
