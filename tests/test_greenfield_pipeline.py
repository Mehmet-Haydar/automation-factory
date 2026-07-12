"""Greenfield = the unified pipeline in DESIGN mode (not a parallel pipeline).

Same engine (Vision + text + RD draft writer + 3-state review + gates); the
prompts DESIGN from the new machine's documents instead of EXTRACTing from
legacy code. RD13/RD14 are retrofit-only → auto-N/A for greenfield.
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw
from workbench.core.ai_runner import BUILTIN_WORKFLOWS


# ---------------------------------------------------------------------------
# Workflow definitions (prompt families kept strictly separate)
# ---------------------------------------------------------------------------

def test_greenfield_discovery_designs_rd01_02_03():
    steps = BUILTIN_WORKFLOWS["Greenfield Discovery"]
    targets = [s.metadata_target for s in steps if s.metadata_target]
    assert targets == ["RD01", "RD02", "RD03"]          # no RD13 (retrofit-only)
    # Step 1 is the Vision pass over the design documents.
    assert steps[0].provider == "google" and steps[0].use_multimodal is True


def test_greenfield_topic_design_covers_rd04_12_no_rd14():
    steps = BUILTIN_WORKFLOWS["Greenfield Topic Design"]
    targets = [s.metadata_target for s in steps if s.metadata_target]
    assert targets == ["RD04", "RD05", "RD06", "RD07", "RD08",
                       "RD09", "RD10", "RD11", "RD12"]   # no RD14 (retrofit-only)
    assert "DRAFT_UNVERIFIED" in steps[0].prompt_template


def test_design_and_extract_prompts_do_not_mix():
    # A greenfield step must read as DESIGN; a retrofit step as EXTRACT. Guard
    # against accidentally wiring the wrong prompt family.
    gf = " ".join(s.system_prompt for s in BUILTIN_WORKFLOWS["Greenfield Topic Design"])
    rf = " ".join(s.system_prompt for s in BUILTIN_WORKFLOWS["Topic Extraction"])
    assert "DESIGN" in gf and "legacy" not in gf.lower()
    assert "legacy" in rf.lower()


# ---------------------------------------------------------------------------
# Routing + auto-N/A
# ---------------------------------------------------------------------------

def _api(root: Path, project_type: str) -> fw.Api:
    (root / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 1, "project_type": project_type,
                    "data_classification": "PUBLIC"}), encoding="utf-8")
    (root / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: PUBLIC\n---\n", encoding="utf-8")
    md = root / "metadata"
    md.mkdir(exist_ok=True)
    for n in range(1, 15):
        (md / f"RD{n:02d}_x.md").write_text(
            f"status: DRAFT_UNVERIFIED\n# RD{n:02d}\nbody", encoding="utf-8")
    api = fw.Api()
    api.root = root
    api.settings = {"username": "Eng"}
    return api


def test_project_type_default_is_retrofit(tmp_path):
    (tmp_path / "PROJECT_STATE.json").write_text(json.dumps({"gate": 1}), encoding="utf-8")
    api = fw.Api(); api.root = tmp_path; api.settings = {}
    assert api._project_type() == "retrofit"


def test_greenfield_auto_na_rd13_rd14(tmp_path, monkeypatch):
    import project_analyzer

    class _S:
        def __init__(self, s): self.status = s

    class _A:
        rd_statuses = {f"RD{n:02d}": _S("done") for n in range(1, 15)}

    monkeypatch.setattr(project_analyzer, "analyze_project", lambda root: _A())

    api = _api(tmp_path, "greenfield")
    model = api.get_gate_model()
    na = model["review_summary"]["na"]
    assert "RD13" in na and "RD14" in na
    # And they no longer count as produced-needing-review.
    assert "RD13" not in model["review_summary"]["unreviewed"]


def test_na_does_not_freeze_gate_progression():
    # Regression for the audit's CRITICAL finding: N/A RDs must not freeze
    # _completed_gate_count / _effective_gate (greenfield RD13/14, or any N/A
    # topic RD) — otherwise gates 3-7 become unreachable.
    gf = {f"RD{n:02d}": "done" for n in range(1, 15)}
    gf["RD13"] = "empty"; gf["RD14"] = "empty"
    assert fw._completed_gate_count(gf) == 0                       # the bug (no na)
    assert fw._completed_gate_count(gf, {"RD13", "RD14"}) == 7      # fixed
    assert fw._effective_gate(3, gf, {"RD13", "RD14"}) == 3         # was 1 before
    # Retrofit with an N/A topic RD (no file) must also progress past gate 2.
    rf = {f"RD{n:02d}": "done" for n in range(1, 15)}
    rf["RD11"] = "empty"
    assert fw._effective_gate(3, rf, set()) == 2                    # frozen without na
    assert fw._effective_gate(3, rf, {"RD11"}) == 3                 # na-aware


def test_greenfield_get_gate_model_not_frozen(tmp_path, monkeypatch):
    import project_analyzer

    class _S:
        def __init__(self, s): self.status = s

    class _A:
        rd_statuses = {f"RD{n:02d}": _S("done") for n in range(1, 13)}
        rd_statuses["RD13"] = _S("empty")
        rd_statuses["RD14"] = _S("empty")

    monkeypatch.setattr(project_analyzer, "analyze_project", lambda root: _A())

    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 3, "project_type": "greenfield"}), encoding="utf-8")
    md = tmp_path / "metadata"; md.mkdir()
    for n in range(1, 13):
        (md / f"RD{n:02d}_x.md").write_text(
            f"status: DRAFT_UNVERIFIED\n# RD{n:02d}\nbody", encoding="utf-8")
    api = fw.Api(); api.root = tmp_path; api.settings = {"username": "Eng"}
    # stored gate 3 must be reachable (not clamped to 1 by absent RD13/14).
    assert api.get_gate_model()["current"] == 3
    # RD13/RD14 are auto-N/A and excluded from the gate-3 snapshot.
    assert set(fw._effective_gate_rds(3, {"RD13", "RD14"})).isdisjoint({"RD13", "RD14"})


def test_greenfield_topic_routing_and_prereq(tmp_path):
    api = _api(tmp_path, "greenfield")
    # No reviews yet → greenfield topic design refuses, naming the greenfield wf.
    r = api.run_topic_generation({"engineer": "Eng", "confirmed": True})
    assert r["ok"] is False
    assert "Greenfield Topic Design" in r["msg"] and "RD01" in r["msg"]
    # Approving RD01/02/03 satisfies the Gate-1 precondition (RD13 is auto-N/A);
    # the run then proceeds past the prereq (and stops later on the missing key).
    for rd in ("RD01", "RD02", "RD03"):
        api.review_rd(rd)
    r2 = api.run_topic_generation({"engineer": "Eng", "confirmed": True})
    assert "needs the Gate-1 analysis approved" not in (r2.get("msg") or "")
