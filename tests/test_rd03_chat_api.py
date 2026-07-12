"""Flowchart panel backend: rd03_get / rd03_regen_mermaid /
rd03_chat_propose (mocked AI) / rd03_chat_apply.

Core safety property under test: the AI only ever supplies the Flow Steps
TABLE — the mermaid diagram and the impact findings are derived
deterministically, an apply demotes RD03 to DRAFT and keeps a _history
backup, and structurally broken proposals cannot be applied at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw

RD03_DOC = """---
project_id: TEST
filled_by: Tester
status: APPROVED
---

# RD03_Flowchart — Test

## Flow Steps

| StepID | StepName | StepType | Description | EntryCondition | ExitCondition | Actions | NextStep | ErrorStep | TimerRef | ModeReq | ISA88Level | Notes | Status |
|--------|----------|----------|-------------|----------------|---------------|---------|----------|-----------|----------|---------|------------|-------|--------|
| S000 | Initial | Initial | Initial state | TRUE | Start_Cmd | All outputs := FALSE | S010 | | | ALL | Phase | | Active |
| S010 | Run | Normal | Running | S000 done | Stop_Cmd | Start motor | (end) | | | ALL | Phase | | Active |

## Mermaid Diagram

```mermaid
stateDiagram-v2
    [*] --> STALE_OLD_DIAGRAM
```
"""

PROPOSAL_TABLE = """| StepID | StepName | StepType | Description | EntryCondition | ExitCondition | Actions | NextStep | ErrorStep | TimerRef | ModeReq | ISA88Level | Notes | Status |
|--------|----------|----------|-------------|----------------|---------------|---------|----------|-----------|----------|---------|------------|-------|--------|
| S000 | Initial | Initial | Initial state | TRUE | Start_Cmd | All outputs := FALSE | S010 | | | ALL | Phase | | Active |
| S010 | Run | Normal | Running | S000 done | Pause_Sensor = TRUE | Start motor | S020 | | | ALL | Phase | | Active |
| S020 | Paused | Normal | Paused on sensor | S010 done | Resume_Cmd | Stop motor | (end) | | | ALL | Phase | SAFETY — engineer review required | Draft |"""


def _project(tmp_path: Path) -> Path:
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 2, "data_classification": "PUBLIC"}), encoding="utf-8")
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: PUBLIC\n---\n", encoding="utf-8")
    md = tmp_path / "metadata"
    md.mkdir()
    (md / "RD03_Flowchart.md").write_text(RD03_DOC, encoding="utf-8")
    # RD01/RD02 give the impact check a vocabulary, so unknown references
    # (Pause_Sensor) are detectable instead of skipped.
    (md / "RD01_IO_List.md").write_text(
        "| Tag | Address |\n|---|---|\n| Motor_Out | %Q0.0 |\n",
        encoding="utf-8")
    (md / "RD02_DataDict.md").write_text(
        "| VarName | Scope |\n|---|---|\n| Start_Cmd | GlobalDB |\n"
        "| Stop_Cmd | GlobalDB |\n| Resume_Cmd | GlobalDB |\n",
        encoding="utf-8")
    return tmp_path


def _api(root: Path) -> fw.Api:
    api = fw.Api()
    api.root = root
    api.settings = {"username": "tester",
                    "api_keys": {"anthropic": "test-key-1234"}}
    return api


class _FakeAIClient:
    """Stands in for ai_client.AIClient; returns a canned reply."""
    reply = ""

    def __init__(self, provider=None, api_key=None, model=None):
        pass

    def chat(self, system="", user="", max_tokens=0):
        return self.__class__.reply, {"in": 1, "out": 1}


# ── rd03_get ────────────────────────────────────────────────────────────────

def test_rd03_get_derives_diagram_and_findings(tmp_path):
    api = _api(_project(tmp_path))
    r = api.rd03_get()
    assert r["ok"] is True
    assert r["step_count"] == 2
    assert r["mermaid"].startswith("flowchart TD")
    assert "STALE_OLD_DIAGRAM" not in r["mermaid"]   # derived, not read
    assert isinstance(r["findings"], list)


def test_rd03_get_without_file(tmp_path):
    (tmp_path / "metadata").mkdir()
    api = _api(tmp_path)
    r = api.rd03_get()
    assert r["ok"] is False


# ── rd03_regen_mermaid ──────────────────────────────────────────────────────

def test_regen_mermaid_overwrites_stale_block_and_backs_up(tmp_path):
    root = _project(tmp_path)
    api = _api(root)
    r = api.rd03_regen_mermaid()
    assert r["ok"] is True
    text = (root / "metadata" / "RD03_Flowchart.md").read_text(encoding="utf-8")
    assert "STALE_OLD_DIAGRAM" not in text
    assert "_s --> S000" in text
    assert "| S010 | Run" in text                      # table untouched
    backups = list((root / "metadata" / "_history").glob("*RD03*"))
    assert backups, "previous version must be backed up"


# ── rd03_chat_propose (AI mocked) ───────────────────────────────────────────

def test_chat_propose_returns_derived_preview(tmp_path, monkeypatch):
    import ai_client
    _FakeAIClient.reply = (
        "I added a pause step after S010 triggered by Pause_Sensor.\n\n"
        + PROPOSAL_TABLE)
    monkeypatch.setattr(ai_client, "AIClient", _FakeAIClient)

    api = _api(_project(tmp_path))
    r = api.rd03_chat_propose(
        [{"role": "user", "content": "Pause the belt when the sensor trips"}])
    assert r["ok"] is True and r["has_proposal"] is True
    assert r["step_count"] == 3
    assert "S020" in r["proposed_table"]
    assert any("S010" in l and "S020" in l for l in r["mermaid"].split("\n"))  # S010→S020 edge
    # Pause_Sensor is not in any RD -> deterministic impact check flags it
    assert any(f["code"] == "UNKNOWN_REF" and "Pause_Sensor" in f["msg"]
               for f in r["findings"])
    assert r["label"] == "DRAFT_UNVERIFIED"


def test_chat_propose_conversational_reply_has_no_proposal(tmp_path, monkeypatch):
    import ai_client
    _FakeAIClient.reply = "Should the pause also stop the upstream conveyor?"
    monkeypatch.setattr(ai_client, "AIClient", _FakeAIClient)

    api = _api(_project(tmp_path))
    r = api.rd03_chat_propose([{"role": "user", "content": "pause it"}])
    assert r["ok"] is True and r["has_proposal"] is False
    assert "upstream" in r["reply"]


def test_chat_propose_without_key_refuses(tmp_path):
    api = _api(_project(tmp_path))
    api.settings["api_keys"] = {}
    r = api.rd03_chat_propose([{"role": "user", "content": "x"}])
    assert r["ok"] is False
    assert "API key" in r["msg"]


# ── rd03_chat_apply ─────────────────────────────────────────────────────────

def test_apply_swaps_table_regenerates_diagram_demotes_status(tmp_path):
    root = _project(tmp_path)
    api = _api(root)
    r = api.rd03_chat_apply(PROPOSAL_TABLE)
    assert r["ok"] is True, r

    text = (root / "metadata" / "RD03_Flowchart.md").read_text(encoding="utf-8")
    assert "| S020 | Paused" in text                   # new table applied
    assert any("S010" in l and "S020" in l for l in text.split("\n"))  # S010→S020 in diagram
    assert "STALE_OLD_DIAGRAM" not in text
    assert "status: DRAFT" in text                     # demoted from APPROVED
    assert "project_id: TEST" in text                  # frontmatter preserved
    backups = list((root / "metadata" / "_history").glob("*RD03*"))
    assert backups


def test_apply_blocks_structurally_broken_proposal(tmp_path):
    root = _project(tmp_path)
    api = _api(root)
    # S010 now points at a step that does not exist -> MISSING_TARGET (error)
    broken = PROPOSAL_TABLE.replace("Start motor | S020", "Start motor | S777")
    r = api.rd03_chat_apply(broken)
    assert r["ok"] is False
    assert "structural" in r["msg"].lower()
    # file untouched
    text = (root / "metadata" / "RD03_Flowchart.md").read_text(encoding="utf-8")
    assert "STALE_OLD_DIAGRAM" in text


def test_apply_rejects_empty_proposal(tmp_path):
    api = _api(_project(tmp_path))
    r = api.rd03_chat_apply("no table here")
    assert r["ok"] is False


# ---------------------------------------------------------------------------
# rd03 audit logging (S-2) — taşındı: test_rd03_audit.py
# ---------------------------------------------------------------------------

from unittest.mock import patch as _patch  # noqa: E402

import pathlib as _pathlib  # noqa: E402

_AUDIT_RD03_DOC = """\
---
project_id: AUDIT_TEST
filled_by: Tester
status: APPROVED
---

# RD03_Flowchart — Audit Test

## Flow Steps

| StepID | StepName | StepType | Description | EntryCondition | ExitCondition | Actions | NextStep | ErrorStep | TimerRef | ModeReq | ISA88Level | Notes | Status |
|--------|----------|----------|-------------|----------------|---------------|---------|----------|-----------|----------|---------|------------|-------|--------|
| S000 | Initial | Initial | Start | TRUE | Go | Reset | S010 | | | ALL | Phase | | Active |
| S010 | Run | Normal | Run | S000 done | Stop | Start | (end) | | | ALL | Phase | | Active |
"""

_AUDIT_PROPOSAL_TABLE = """\
| StepID | StepName | StepType | Description | EntryCondition | ExitCondition | Actions | NextStep | ErrorStep | TimerRef | ModeReq | ISA88Level | Notes | Status |
|--------|----------|----------|-------------|----------------|---------------|---------|----------|-----------|----------|---------|------------|-------|--------|
| S000 | Initial | Initial | Start | TRUE | Go | Reset | S010 | | | ALL | Phase | | Active |
| S010 | Run | Normal | Run | S000 done | Stop | Start | S020 | | | ALL | Phase | | Active |
| S020 | Done | Normal | Finish | S010 done | TRUE | Park | (end) | | | ALL | Phase | | Draft |
"""


def _audit_project(tmp_path):
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"gate": 2, "data_classification": "PUBLIC"}', encoding="utf-8"
    )
    meta = tmp_path / "metadata"
    meta.mkdir()
    (meta / "RD03_Flowchart.md").write_text(_AUDIT_RD03_DOC, encoding="utf-8")
    return tmp_path


def _audit_api(root) -> fw.Api:
    api = fw.Api()
    api.root = root
    api.settings = {"username": "tester", "api_keys": {}}
    return api


class TestRd03AuditLog:
    """S-2 proof: rd03_chat_apply + rd03_regen_mermaid çağrıları _audit_log çağırır."""

    def test_chat_apply_calls_audit_log(self, tmp_path):
        root = _audit_project(tmp_path)
        api = _audit_api(root)
        call_log: list = []

        def spy_audit(project_root, step_label, *args, **kwargs):
            call_log.append(step_label)

        with _patch.object(fw, "_audit_log", side_effect=spy_audit):
            r = api.rd03_chat_apply(_AUDIT_PROPOSAL_TABLE)

        assert r["ok"] is True, r.get("msg")
        assert "rd03_chat_apply" in call_log, (
            "FAIL: _audit_log 'rd03_chat_apply' etiketi ile çağrılmadı. S-2 fix eksik."
        )

    def test_chat_apply_audit_precedes_write(self, tmp_path):
        root = _audit_project(tmp_path)
        api = _audit_api(root)
        call_order: list = []

        def spy_audit(project_root, step_label, *args, **kwargs):
            call_order.append(f"audit:{step_label}")

        original_write = _pathlib.Path.write_text

        def spy_write(self, data, **kwargs):
            if "RD03" in str(self):
                call_order.append("write_text:RD03")
            return original_write(self, data, **kwargs)

        with _patch.object(fw, "_audit_log", side_effect=spy_audit):
            with _patch.object(_pathlib.Path, "write_text", spy_write):
                r = api.rd03_chat_apply(_AUDIT_PROPOSAL_TABLE)

        assert r["ok"] is True, r.get("msg")
        audit_idx = next((i for i, e in enumerate(call_order) if e == "audit:rd03_chat_apply"), None)
        write_idx = next((i for i, e in enumerate(call_order) if e == "write_text:RD03"), None)
        assert audit_idx is not None, f"audit çağrısı yok. Sıra: {call_order}"
        assert write_idx is not None, f"write_text:RD03 yok. Sıra: {call_order}"
        assert audit_idx < write_idx, (
            f"audit (idx={audit_idx}) write_text'ten (idx={write_idx}) SONRA çağrılmış."
        )

    def test_chat_apply_file_written_even_if_audit_fails(self, tmp_path):
        root = _audit_project(tmp_path)
        api = _audit_api(root)

        def failing_audit(*args, **kwargs):
            raise fw.AuditLogError("Simulated audit failure")

        with _patch.object(fw, "_audit_log", side_effect=failing_audit):
            r = api.rd03_chat_apply(_AUDIT_PROPOSAL_TABLE)

        assert r["ok"] is True, f"Audit hatası dosya yazımını engelledi. msg={r.get('msg')}"
        text = (root / "metadata" / "RD03_Flowchart.md").read_text(encoding="utf-8")
        assert "S020" in text

    def test_regen_mermaid_calls_audit_log(self, tmp_path):
        root = _audit_project(tmp_path)
        api = _audit_api(root)
        call_log: list = []

        def spy_audit(project_root, step_label, *args, **kwargs):
            call_log.append(step_label)

        with _patch.object(fw, "_audit_log", side_effect=spy_audit):
            r = api.rd03_regen_mermaid()

        assert r["ok"] is True, r.get("msg")
        assert "rd03_regen_mermaid" in call_log, (
            "FAIL: _audit_log 'rd03_regen_mermaid' etiketi ile çağrılmadı. S-2 sibling fix eksik."
        )

    def test_regen_mermaid_file_written_even_if_audit_fails(self, tmp_path):
        root = _audit_project(tmp_path)
        api = _audit_api(root)

        def failing_audit(*args, **kwargs):
            raise fw.AuditLogError("Simulated audit failure")

        with _patch.object(fw, "_audit_log", side_effect=failing_audit):
            r = api.rd03_regen_mermaid()

        assert r["ok"] is True, f"Audit hatası rd03_regen_mermaid'i engelledi. msg={r.get('msg')}"

    def test_chat_apply_content_correctness(self, tmp_path):
        root = _audit_project(tmp_path)
        api = _audit_api(root)
        with _patch.object(fw, "_audit_log", return_value=None):
            r = api.rd03_chat_apply(_AUDIT_PROPOSAL_TABLE)
        assert r["ok"] is True
        text = (root / "metadata" / "RD03_Flowchart.md").read_text(encoding="utf-8")
        assert "S020" in text
        assert "status: DRAFT" in text
        assert "project_id: AUDIT_TEST" in text
        backups = list((root / "metadata" / "_history").glob("*RD03*"))
        assert backups, "_history yedeği oluşturulmalıydı"
