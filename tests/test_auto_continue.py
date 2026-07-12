"""Proof tests — Vites-1: one-click full analysis (auto-continue).

Design: the consent modal offers "continue with topic generation
automatically". A discovery run then chains straight into the topic workflow
inside the SAME background job — the engineer clicks once and gets all 14 RD
drafts. The review requirement moves to the Gate-3 lock; the fact that topic
RDs were generated from UNREVIEWED Gate-1 drafts is recorded loudly.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import factory_web as fw
from workbench.core import ai_runner as ar


def _api(root: Path) -> fw.Api:
    (root / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 1, "project_type": "retrofit",
                    "data_classification": "PUBLIC"}), encoding="utf-8")
    (root / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: PUBLIC\n---\n", encoding="utf-8")
    (root / "metadata").mkdir(exist_ok=True)
    legacy = root / "_raw" / "legacy_code"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "OB1.awl").write_text("CALL FB 10;", encoding="utf-8")
    api = fw.Api()
    api.root = root
    api.settings = {"username": "Eng"}
    return api


class _FakeRunner:
    """Captures AutoFlowRunner construction; never touches an AI API."""
    instances: list = []

    def __init__(self, **kw):
        self.kw = kw
        self.workflow = None
        _FakeRunner.instances.append(self)

    def run_async(self, workflow_name, src):
        self.workflow = workflow_name
        self.src = src


@pytest.fixture
def patched(monkeypatch, tmp_path):
    _FakeRunner.instances = []
    monkeypatch.setattr(ar, "AutoFlowRunner", _FakeRunner)
    api = _api(tmp_path)
    monkeypatch.setattr(api, "_resolve_api_key", lambda p=None: "test-key")
    return api


def test_chain_skips_reviewed_check(patched):
    """The internal continuation hop must NOT be blocked by the Gate-1
    reviewed requirement — that is the whole point of auto-continue."""
    job = {"running": True, "done": False, "ok": None, "msg": "", "lines": [],
           "current_step": "", "drafts": [], "warnings": [], "step_index": -1}
    r = patched.run_retrofit_preanalysis(
        {"engineer": "Eng", "confirmed": True},
        workflow_name="Topic Extraction",
        _chain={"job": job, "offset": 6},
    )
    assert r.get("ok"), r
    assert "needs the Gate-1 analysis approved" not in (r.get("msg") or "")


def test_manual_topic_still_requires_review(patched):
    """Without _chain the review gate stays hard (two-stage flow intact)."""
    r = patched.run_topic_extraction({"engineer": "Eng", "confirmed": True})
    assert r["ok"] is False
    assert "needs the Gate-1 analysis approved" in r["msg"]


def test_auto_continue_full_chain(patched):
    disc = [s.name for s in ar.BUILTIN_WORKFLOWS["Retrofit Pre-Analysis"]]
    topic = [s.name for s in ar.BUILTIN_WORKFLOWS["Topic Extraction"]]

    r = patched.run_discovery(
        {"engineer": "Eng", "confirmed": True, "auto_continue": True})
    assert r.get("ok"), r

    job = patched._preanalysis_job
    # One continuous tracker: full combined step list from the start.
    assert job["step_names"] == disc + topic
    assert job["step_total"] == len(disc) + len(topic)

    # Phase 1 finishes → the chain must start phase 2 in the SAME job.
    p1 = _FakeRunner.instances[0]
    assert p1.workflow == "Retrofit Pre-Analysis"
    p1.kw["on_flow_done"]()
    assert len(_FakeRunner.instances) == 2, "auto-continue ikinci fazı başlatmadı"
    p2 = _FakeRunner.instances[1]
    assert p2.workflow == "Topic Extraction"
    assert job["running"] is True and job["done"] is False
    # The unreviewed-drafts gap is recorded loudly.
    assert any("UNREVIEWED" in w for w in job["warnings"])

    # Phase-2 step indices continue after phase 1 (no progress-bar reset).
    p2.kw["on_step_start"](0, "X")
    assert job["step_index"] == len(disc)

    # Phase 2 finishes → job done with the honest completion message.
    p2.kw["on_flow_done"]()
    assert job["done"] is True and job["ok"] is True
    assert "UNREVIEWED" in job["msg"]


def test_auto_continue_off_keeps_two_stage(patched):
    disc = [s.name for s in ar.BUILTIN_WORKFLOWS["Retrofit Pre-Analysis"]]
    r = patched.run_discovery({"engineer": "Eng", "confirmed": True})
    assert r.get("ok"), r
    job = patched._preanalysis_job
    assert job["step_names"] == disc, "auto_continue kapalıyken adımlar genişlememeli"
    _FakeRunner.instances[0].kw["on_flow_done"]()
    assert job["done"] is True and len(_FakeRunner.instances) == 1


def test_auto_continue_failure_reports_manual_fallback(patched, monkeypatch):
    r = patched.run_discovery(
        {"engineer": "Eng", "confirmed": True, "auto_continue": True})
    assert r.get("ok"), r
    job = patched._preanalysis_job
    # Second hop fails (e.g. key revoked mid-run) → job fails HONESTLY with
    # a pointer to the manual Gate-2 path, not a silent half-result.
    monkeypatch.setattr(
        patched, "run_retrofit_preanalysis",
        lambda *a, **k: {"ok": False, "msg": "boom"})
    _FakeRunner.instances[0].kw["on_flow_done"]()
    assert job["done"] is True and job["ok"] is False
    assert "boom" in job["msg"] and "Gate 2" in job["msg"]
