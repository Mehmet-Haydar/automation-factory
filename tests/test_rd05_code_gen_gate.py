"""Proof tests — RD05 safety gate on the code-generation chain (S-1/M-01).

2026-07-10 audit: the RD05 gate existed for the FAT protocol and the
customer report, but assemble_program / delta assembly / generate_scl /
send_to_tia never called it — a Gate-1 project could be assembled and
pushed into a real TIA project with the safety analysis unreviewed.
Contract now: all four entry points share fat_protocol.check_rd05_ready
(fail-closed) and answer with the precondition_error response shape the
GUI already renders. An approved RD05 lets them through unchanged.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import factory_web  # noqa: E402


def _api(root: Path):
    api = factory_web.Api()
    api.root = root
    api.settings = {}
    return api


def _bare_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "PROJECT_STATE.json").write_text(
        json.dumps({"allowed_tia_versions": ["V19"]}), encoding="utf-8")
    return proj


def _approve_rd05(proj: Path) -> None:
    md = proj / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD05_Safety.md").write_text(
        "# RD05 Safety\n| SF | Function | PLr |\n|---|---|---|\n"
        "| SF-01 | E-stop | d |\n| SF-02 | Guard | c |\n", encoding="utf-8")
    st = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    st["rd_status"] = {"RD05_Safety": {"status": "REVIEWED"}}
    (proj / "PROJECT_STATE.json").write_text(json.dumps(st), encoding="utf-8")


def test_assemble_blocked_without_rd05(tmp_path):
    api = _api(_bare_project(tmp_path))
    for call in (api.assemble_program, api.run_delta_assembly):
        r = call()
        assert r["ok"] is False and r.get("precondition_error") is True
        assert "RD05" in r["msg"], r


def test_generate_scl_action_blocked_without_rd05(tmp_path):
    api = _api(_bare_project(tmp_path))
    r = api.run_pipeline("generate_scl")
    assert r["ok"] is False and r.get("precondition_error") is True
    assert "RD05" in str(r.get("msg") or r.get("output")), r


class _Mgr:
    """Minimal enabled bridge manager (mirrors test_tia_fix_assist)."""
    def tia_settings(self):
        return {"default_plc_name": "PLC_1", "fix_assist_mode": "hints"}

    def is_enabled(self, bid):
        return True

    def get(self, bid):
        class _B:
            display_name = "TIA V19 (fake)"
        return _B()


def test_send_to_tia_blocked_without_rd05(tmp_path):
    proj = _bare_project(tmp_path)
    api = _api(proj)
    api._bridge_mgr = _Mgr()
    out = proj / "_output" / "scl"
    out.mkdir(parents=True)
    (out / "x.scl").write_text("// code", encoding="utf-8")
    ap = tmp_path / "plant.ap19"
    ap.write_text("", encoding="utf-8")
    api._tia_consent_gate = lambda consent, op: None
    r = api.send_to_tia({"project_path": str(ap)})
    assert r["ok"] is False and r.get("precondition_error") is True
    assert "RD05" in r["msg"], r
    assert not getattr(api, "_tia_job", None), "job must never start"


def test_draft_unverified_rd05_still_blocks(tmp_path):
    """Content present but not approved -> still blocked (3-state model)."""
    proj = _bare_project(tmp_path)
    _approve_rd05(proj)
    st = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    st["rd_status"] = {"RD05_Safety": {"status": "DRAFT_UNVERIFIED"}}
    (proj / "PROJECT_STATE.json").write_text(json.dumps(st), encoding="utf-8")
    r = _api(proj).assemble_program()
    assert r["ok"] is False and "RD05" in r["msg"]


def test_fresh_ai_draft_banner_blocks_without_review_record(tmp_path):
    """E2E #3 live finding (AUDIT-004b): a fresh project has NO rd_status
    entry, so the old state check never fired and an unreviewed AI draft
    (always stamped DRAFT_UNVERIFIED by the draft writer) passed the gate.
    The banner itself must block until rd_verifications records a review."""
    proj = _bare_project(tmp_path)
    md = proj / "metadata"
    md.mkdir()
    (md / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
        "---\nstatus: DRAFT_UNVERIFIED\n---\n# RD05 Safety\n"
        "| SF | Function | PLr |\n|---|---|---|\n"
        "| SF-01 | E-stop | d |\n| SF-02 | Guard | c |\n", encoding="utf-8")
    r = _api(proj).assemble_program()
    assert r["ok"] is False and r.get("precondition_error") is True
    assert "AUDIT-004b" in r["msg"] or "banner" in r["msg"], r

    # recorded engineer review lifts the block
    st = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    st["rd_verifications"] = {"RD05": {"reviewed": True,
                                       "who": "H. Becker (TUV)"}}
    (proj / "PROJECT_STATE.json").write_text(json.dumps(st), encoding="utf-8")
    r2 = _api(proj).assemble_program()
    assert r2.get("precondition_error") is None, r2


def test_approved_rd05_passes_gate(tmp_path):
    """With RD05 reviewed, the gate steps aside — the assembler answers
    (about the missing RD01), NOT the safety gate."""
    proj = _bare_project(tmp_path)
    _approve_rd05(proj)
    r = _api(proj).assemble_program()
    assert r.get("precondition_error") is None
    assert "RD05" not in str(r.get("output", "")), r
