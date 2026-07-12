"""M2 — RD draft writer + extended pre-analysis chain.

The pre-analysis chain used to dead-end in REPORTS/ (engineer had to
copy-paste into metadata/RD01 by hand). These tests pin the closure of
that gap: drafts land in metadata/ with DRAFT_UNVERIFIED status, approved
files are never overwritten, and the workflow carries RD02/RD03/RD13 too.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import project_analyzer
from rd_draft_writer import (
    DraftWriteResult, find_rd_target, has_markdown_table, write_rd_draft,
)
from workbench.core import ai_runner
from workbench.core.ai_runner import AutoFlowRunner, BUILTIN_WORKFLOWS, WorkflowStep

fw = importlib.import_module("factory_web")


TABLE_CONTENT = (
    "## IO List\n\n"
    "| Tag | Description | IO_Type | Address | SafetyRelated | Status |\n"
    "|-----|-------------|---------|---------|---------------|--------|\n"
    "| MOT_CONV_001_RUN | Conveyor run | DQ | %Q0.0 | N | DRAFT_UNVERIFIED |\n"
    "| BTN_ESTOP_001 | E-Stop chain | DI | %I0.0 | Y | DRAFT_UNVERIFIED |\n"
)


class TestWriteRdDraft:
    def test_fresh_project_creates_canonical_file(self, tmp_path):
        res = write_rd_draft(tmp_path, "RD01", TABLE_CONTENT,
                             source_step="t", model_id="m")
        assert res.action == "written"
        assert res.path.name == "RD01_IO_List.md"
        text = res.path.read_text(encoding="utf-8")
        assert "status: DRAFT_UNVERIFIED" in text
        assert "Status: DRAFT_UNVERIFIED" in text  # visible banner
        assert "MOT_CONV_001_RUN" in text
        assert not res.backed_up

    def test_existing_variant_name_updated_with_backup(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        existing = md / "RD01_Signal_List_ProjektX.md"   # project-specific variant name
        existing.write_text("status: draft\nold content here", encoding="utf-8")

        res = write_rd_draft(tmp_path, "RD01", TABLE_CONTENT)
        assert res.path == existing, "must update the project's own RD01 file"
        assert res.backed_up
        backups = list((md / "_history").iterdir())
        assert len(backups) == 1
        assert "old content here" in backups[0].read_text(encoding="utf-8")

    def test_approved_rd_never_overwritten(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        approved = md / "RD01_IO_List.md"
        approved_body = "---\nstatus: approved\n---\nengineer-verified content"
        approved.write_text(approved_body, encoding="utf-8")

        res = write_rd_draft(tmp_path, "RD01", TABLE_CONTENT)
        assert res.action == "sidecar"
        assert res.warning
        assert approved.read_text(encoding="utf-8") == approved_body, (
            "approved RD content must be untouched"
        )
        assert res.path.name == "RD01_IO_List.ai_draft.md"
        assert "MOT_CONV_001_RUN" in res.path.read_text(encoding="utf-8")

    def test_ai_frontmatter_replaced_by_ours(self, tmp_path):
        content = "---\nstatus: done\nauthor: AI\n---\n" + TABLE_CONTENT
        res = write_rd_draft(tmp_path, "RD01", content)
        text = res.path.read_text(encoding="utf-8")
        assert "status: done" not in text, (
            "model-invented 'status: done' would silently pass the gate"
        )
        assert "status: DRAFT_UNVERIFIED" in text

    def test_tableless_draft_warns(self, tmp_path):
        res = write_rd_draft(tmp_path, "RD02", "Just prose, no table.")
        assert res.action == "written"
        assert "table" in res.warning.lower()

    def test_rd05_safety_draft_is_forced_to_draft_unverified(self, tmp_path):
        # Even if the model returns 'status: done', RD05 lands as DRAFT_UNVERIFIED
        # under the canonical safety filename — the writer never lets AI mark
        # safety as approved.
        content = "---\nstatus: done\n---\n" + TABLE_CONTENT
        res = write_rd_draft(tmp_path, "RD05", content)
        assert res.path.name == "RD05_Safety.md"
        text = res.path.read_text(encoding="utf-8")
        assert "status: DRAFT_UNVERIFIED" in text
        assert "status: done" not in text

    def test_status_recognised_by_both_classifiers(self, tmp_path):
        res = write_rd_draft(tmp_path, "RD01", TABLE_CONTENT)
        # factory_web gate vocabulary → draft (NOT ok/approved)
        assert fw._rd_status(res.path) == "draft"
        # project_analyzer vocabulary → draft_unverified
        status, _size = project_analyzer.detect_rd_file_status(res.path)
        assert status == "draft_unverified"


class TestFindRdTarget:
    def test_skips_ai_draft_sidecars(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        (md / "RD01_IO_List.ai_draft.md").write_text("x", encoding="utf-8")
        target = find_rd_target(md, "RD01")
        assert target.name == "RD01_IO_List.md"


class TestHasMarkdownTable:
    def test_detects_table(self):
        assert has_markdown_table(TABLE_CONTENT)

    def test_rejects_prose(self):
        assert not has_markdown_table("no pipes here\njust text\n")


class TestWorkflowDefinition:
    def test_gate1_chain_covers_rd01_02_03_13(self):
        # Gate 1 "Retrofit Pre-Analysis" hand-writes only the discovery RDs.
        steps = BUILTIN_WORKFLOWS["Retrofit Pre-Analysis"]
        targets = [s.metadata_target for s in steps if s.metadata_target]
        assert targets == ["RD01", "RD02", "RD03", "RD13"]

    def test_gate2_topic_extraction_covers_remaining_rds(self):
        # Gate 2 "Topic Extraction" produces the rest (RD04-12, 14 + RD05),
        # using the approved Gate-1 outputs (separate, gated generation).
        steps = BUILTIN_WORKFLOWS["Topic Extraction"]
        targets = [s.metadata_target for s in steps if s.metadata_target]
        assert targets == [
            "RD04", "RD05", "RD06", "RD07", "RD08",
            "RD09", "RD10", "RD11", "RD12", "RD14",
        ]

    def test_rd05_safety_is_drafted_but_stays_unverified(self):
        # Policy (2026-06-29): the AI assists on safety too — RD05 IS auto-drafted
        # (in the Gate-2 Topic Extraction), but every row is DRAFT_UNVERIFIED and
        # the gate engine (W-A2) + FAT/report preconditions block every approval
        # gate until a certified safety engineer signs RD05 off.
        steps = BUILTIN_WORKFLOWS["Topic Extraction"]
        rd05 = [s for s in steps if s.metadata_target == "RD05"]
        assert len(rd05) == 1, "RD05 safety extractor must be wired into Topic Extraction"
        assert "DRAFT_UNVERIFIED" in rd05[0].prompt_template
        # The system prompt must forbid guessing SIL/PLr.
        assert "SIL" in rd05[0].system_prompt or "PLr" in rd05[0].system_prompt

    def test_every_draft_step_demands_draft_unverified_rows(self):
        for wf in ("Retrofit Pre-Analysis", "Topic Extraction"):
            for s in BUILTIN_WORKFLOWS[wf]:
                if s.metadata_target:
                    assert "DRAFT_UNVERIFIED" in s.prompt_template, f"{wf}:{s.name}"


class _Gate:
    allowed = True
    reason = "ok"
    def __iter__(self):
        return iter((True, "ok"))


class _StubClient:
    def __init__(self, provider, api_key, model):
        self.provider = provider
    def chat(self, system, user, max_tokens, on_chunk=None):
        return TABLE_CONTENT, None
    def chat_with_files(self, system, user, files, max_tokens):
        return TABLE_CONTENT, None


class TestRunnerDraftWriterHook:
    @pytest.fixture
    def env(self, monkeypatch, tmp_path):
        monkeypatch.setattr(ai_runner, "AIClient", _StubClient)
        monkeypatch.setattr(ai_runner, "AI_AVAILABLE", True)
        monkeypatch.setattr(ai_runner, "AUDIT_AVAILABLE", False)
        monkeypatch.setattr(ai_runner, "check_ai_send", lambda *a, **kw: _Gate())
        src = tmp_path / "legacy.txt"
        src.write_text("U E 1.0\n", encoding="utf-8")
        return tmp_path, src

    def _run(self, root, src, writer, on_warn=None):
        name = "_test_draft_hook"
        BUILTIN_WORKFLOWS[name] = [
            WorkflowStep(name="plain", prompt_template="{content}",
                         output_suffix="_p.md"),
            WorkflowStep(name="rd step", prompt_template="{prev_output}",
                         output_suffix="_rd.md", metadata_target="RD01"),
        ]
        flow_done = {"v": False}
        try:
            runner = AutoFlowRunner(
                provider="google", model="m", api_key="k", project_root=root,
                on_step_start=lambda i, n: None, on_step_chunk=lambda c: None,
                on_step_done=lambda i, o, p: None,
                on_flow_done=lambda: flow_done.__setitem__("v", True),
                on_error=lambda m: None, on_warn=on_warn,
                draft_writer=writer,
            )
            runner._run(name, src)
        finally:
            BUILTIN_WORKFLOWS.pop(name, None)
        return flow_done["v"]

    def test_writer_called_only_for_metadata_steps(self, env):
        root, src = env
        calls = []
        done = self._run(root, src, lambda step, content: calls.append(
            (step.metadata_target, content)))
        assert done
        assert len(calls) == 1
        assert calls[0][0] == "RD01"
        assert "MOT_CONV_001_RUN" in calls[0][1]

    def test_writer_failure_warns_but_flow_survives(self, env):
        root, src = env
        warns = []
        def _boom(step, content):
            raise RuntimeError("disk full")
        done = self._run(root, src, _boom, on_warn=warns.append)
        assert done, "draft-writer failure must not kill the flow"
        assert any("disk full" in w for w in warns)
        # REPORTS/ copy still exists as the fallback audit trail
        # (2026-07-07: single living copy under REPORTS/_ai_steps/)
        assert list((root / "REPORTS").rglob("*_rd.md"))
