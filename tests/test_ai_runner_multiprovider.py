"""M0 — per-step API key resolution + multi-step output map in AutoFlowRunner.

Bug history (2026-06-09 field-readiness plan, finding 1):
- ai_runner sent ``self.api_key`` to EVERY provider, so a mixed-provider
  workflow (Retrofit Pre-Analysis: google + anthropic) gave the Gemini key
  to Anthropic and failed mid-run.
- Templates could only reference ``{prev_output}`` — the RD01 consolidation
  step never saw the drawing analysis from step 1.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.core import ai_runner
from workbench.core.ai_runner import AutoFlowRunner, BUILTIN_WORKFLOWS, WorkflowStep


class _Gate:
    """check_ai_send stand-in: tuple-unpackable AND .allowed (both call styles)."""
    allowed = True
    reason = "ok"

    def __iter__(self):
        return iter((self.allowed, self.reason))


class _RecorderClient:
    """AIClient stand-in recording constructor args and prompts."""

    instances: list["_RecorderClient"] = []

    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.prompts: list[str] = []
        _RecorderClient.instances.append(self)

    def chat(self, system, user, max_tokens, on_chunk=None):
        self.prompts.append(user)
        return f"OUT[{self.provider}]", None

    def chat_with_files(self, system, user, files, max_tokens):
        self.prompts.append(user)
        return f"OUT[{self.provider}:mm]", None


@pytest.fixture
def runner_env(monkeypatch, tmp_path):
    """Patched ai_runner module: mock client, open guard, no audit, sync run."""
    _RecorderClient.instances = []
    monkeypatch.setattr(ai_runner, "AIClient", _RecorderClient)
    monkeypatch.setattr(ai_runner, "AI_AVAILABLE", True)
    monkeypatch.setattr(ai_runner, "AUDIT_AVAILABLE", False)
    monkeypatch.setattr(ai_runner, "check_ai_send", lambda *a, **kw: _Gate())
    src = tmp_path / "legacy.txt"
    src.write_text("L 100\nU E 1.0\n= A 2.0\n", encoding="utf-8")
    return tmp_path, src


def _mk_runner(project_root, resolver=None, **cb_overrides):
    calls = {"errors": [], "done": False}

    def _err(msg):
        calls["errors"].append(msg)

    kw = dict(
        provider="google", model="gemini-test", api_key="KEY-GOOGLE",
        project_root=project_root,
        on_step_start=lambda i, n: None,
        on_step_chunk=lambda c: None,
        on_step_done=lambda i, o, p: None,
        on_flow_done=lambda: calls.__setitem__("done", True),
        on_error=_err,
        api_key_resolver=resolver,
    )
    kw.update(cb_overrides)
    return AutoFlowRunner(**kw), calls


def _with_workflow(name, steps):
    """Context helper: temporarily register a workflow."""
    BUILTIN_WORKFLOWS[name] = steps
    return name


@pytest.fixture
def two_provider_workflow():
    name = _with_workflow("_test_mixed", [
        WorkflowStep(name="G step", prompt_template="A:{content}",
                     output_suffix="_a.md", provider="google", model="gemini-test"),
        WorkflowStep(name="C step", prompt_template="B:{prev_output}",
                     output_suffix="_b.md", provider="anthropic", model="claude-test"),
    ])
    yield name
    BUILTIN_WORKFLOWS.pop(name, None)


class TestPerStepKeyResolution:
    def test_each_provider_gets_its_own_key(self, runner_env, two_provider_workflow):
        root, src = runner_env
        keys = {"google": "KEY-GOOGLE", "anthropic": "KEY-ANTHROPIC"}
        runner, calls = _mk_runner(root, resolver=lambda p: keys.get(p))
        runner._run(two_provider_workflow, src)

        assert calls["done"], f"flow should complete; errors={calls['errors']}"
        by_provider = {c.provider: c.api_key for c in _RecorderClient.instances}
        assert by_provider["google"] == "KEY-GOOGLE"
        assert by_provider["anthropic"] == "KEY-ANTHROPIC", (
            "anthropic step must receive the anthropic key — pre-fix code sent "
            "the global (google) key to every provider"
        )

    def test_missing_step_key_stops_run_with_clear_error(self, runner_env, two_provider_workflow):
        root, src = runner_env
        runner, calls = _mk_runner(root, resolver=lambda p: {"google": "KEY-G"}.get(p))
        runner._run(two_provider_workflow, src)

        assert not calls["done"]
        assert any("anthropic" in e and "C step" in e for e in calls["errors"]), (
            f"error must name the provider and the step: {calls['errors']}"
        )
        # No anthropic client may have been created with a wrong/empty key
        assert all(c.provider != "anthropic" for c in _RecorderClient.instances)

    def test_no_resolver_no_cross_provider_leak(self, runner_env, two_provider_workflow):
        # Without a resolver, a foreign-provider step must NOT receive the
        # global key (old behavior) — it must stop with the key error.
        root, src = runner_env
        runner, calls = _mk_runner(root, resolver=None)
        runner._run(two_provider_workflow, src)

        assert not calls["done"]
        anthropic_clients = [c for c in _RecorderClient.instances if c.provider == "anthropic"]
        assert not anthropic_clients, "global key must never leak to another provider"


class TestStepOutputMap:
    def test_out_n_placeholders_inject_all_earlier_steps(self, runner_env):
        root, src = runner_env
        name = _with_workflow("_test_outmap", [
            WorkflowStep(name="s1", prompt_template="1:{content}", output_suffix="_1.md",
                         provider="google", model="gemini-test"),
            WorkflowStep(name="s2", prompt_template="2:{prev_output}", output_suffix="_2.md",
                         provider="google", model="gemini-test"),
            WorkflowStep(name="s3", prompt_template="3: A={out_1} B={out_2}",
                         output_suffix="_3.md", provider="google", model="gemini-test"),
        ])
        try:
            runner, calls = _mk_runner(root, resolver=lambda p: "KEY-GOOGLE")
            runner._run(name, src)
        finally:
            BUILTIN_WORKFLOWS.pop(name, None)

        assert calls["done"], calls["errors"]
        client = _RecorderClient.instances[0]
        step3_prompt = client.prompts[2]
        # Both earlier outputs (sanitized) must appear in step 3's prompt
        assert "OUT[google]" in step3_prompt
        assert step3_prompt.count("OUT[google]") >= 2, (
            "step 3 must receive BOTH step-1 and step-2 outputs"
        )

    def test_unknown_placeholder_fails_loud_not_silent(self, runner_env):
        root, src = runner_env
        name = _with_workflow("_test_badph", [
            WorkflowStep(name="s1", prompt_template="X:{out_99}", output_suffix="_1.md",
                         provider="google", model="gemini-test"),
        ])
        try:
            runner, calls = _mk_runner(root, resolver=lambda p: "KEY-GOOGLE")
            runner._run(name, src)
        finally:
            BUILTIN_WORKFLOWS.pop(name, None)

        assert not calls["done"]
        assert any("out_99" in e for e in calls["errors"])


class TestRetrofitWorkflowTemplate:
    def test_consolidation_step_references_both_analyses(self):
        steps = BUILTIN_WORKFLOWS["Retrofit Pre-Analysis"]
        consolidation = steps[2]
        assert "{out_1}" in consolidation.prompt_template, (
            "RD01 consolidation must inject the DRAWING analysis (step 1) — "
            "pre-fix template only saw {prev_output} (legacy analysis)"
        )
        assert "{out_2}" in consolidation.prompt_template

    def test_workflow_uses_two_providers(self):
        # Step 1 (drawing/photo analysis) is always "google" (Vision required).
        # Steps 2-6 use provider=None so they inherit the global/task-routing
        # provider and work with any key the user has configured.
        steps = BUILTIN_WORKFLOWS["Retrofit Pre-Analysis"]
        providers = {s.provider for s in steps}
        assert providers == {"google", None}
        assert steps[0].provider == "google", "Step 1 must be google (Vision)"
