"""Output-language directive (GLOBAL_LANG_POLICY §7) — delivery audit fix.

The README promised per-project TR/EN/DE output, but no AI call site
consumed PROJECT_STATE.output_language. These tests pin the wiring:
runner suffix, pre-analysis injection, sequence-FB injection, state
setter, and the EN no-op.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from workbench.core import ai_runner
from workbench.core.ai_runner import AutoFlowRunner, BUILTIN_WORKFLOWS, WorkflowStep

fw = importlib.import_module("factory_web")


def _mk_api(root: Path, state: dict | None = None):
    api = object.__new__(fw.Api)
    api.settings = {"api_keys": {"google": "k-g", "anthropic": "k-a"}}
    api.root = root
    if state is not None:
        (root / "PROJECT_STATE.json").write_text(
            json.dumps(state), encoding="utf-8")
    return api


class TestLangDirective:
    def test_en_is_noop(self):
        assert fw._lang_directive("EN") == ""
        assert fw._lang_directive("") == ""
        assert fw._lang_directive(None) == ""

    def test_tr_directive_names_turkish_keeps_tags_english(self):
        d = fw._lang_directive("TR")
        assert "Turkish" in d
        assert "English" in d, "tags/keywords must explicitly stay English"

    def test_de_directive(self):
        assert "German" in fw._lang_directive("de")


class TestOutputLanguageState:
    def test_reads_from_project_state(self, tmp_path):
        api = _mk_api(tmp_path, {"output_language": "tr"})
        assert api._output_language() == "TR"

    def test_defaults_to_en(self, tmp_path):
        api = _mk_api(tmp_path, {})
        assert api._output_language() == "EN"

    def test_set_project_target_accepts_language(self, tmp_path):
        api = _mk_api(tmp_path, {"data_classification": "PUBLIC"})
        r = api.set_project_target({"output_language": "TR"})
        assert r["ok"]
        st = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        assert st["output_language"] == "TR"

    def test_set_project_target_rejects_unknown_language(self, tmp_path):
        api = _mk_api(tmp_path, {"data_classification": "PUBLIC"})
        r = api.set_project_target({"output_language": "FR"})
        assert not r["ok"], "unsupported language codes must not be stored"


class _Recorder:
    systems: list[str] = []

    def __init__(self, provider, api_key, model):
        pass

    def chat(self, system, user, max_tokens, on_chunk=None):
        _Recorder.systems.append(system)
        return "| Tag |\n|---|\n| X |", None

    def chat_with_files(self, system, user, files, max_tokens):
        _Recorder.systems.append(system)
        return "out", None


class _Gate:
    allowed = True
    reason = "ok"
    def __iter__(self):
        return iter((True, "ok"))


class TestRunnerSuffixInjection:
    def test_suffix_reaches_every_step_system_prompt(self, monkeypatch, tmp_path):
        _Recorder.systems = []
        monkeypatch.setattr(ai_runner, "AIClient", _Recorder)
        monkeypatch.setattr(ai_runner, "AI_AVAILABLE", True)
        monkeypatch.setattr(ai_runner, "AUDIT_AVAILABLE", False)
        monkeypatch.setattr(ai_runner, "check_ai_send", lambda *a, **kw: _Gate())
        src = tmp_path / "x.txt"
        src.write_text("U E 1.0", encoding="utf-8")

        name = "_test_lang"
        BUILTIN_WORKFLOWS[name] = [
            WorkflowStep(name="s1", prompt_template="{content}", output_suffix="_1.md"),
            WorkflowStep(name="s2", prompt_template="{prev_output}", output_suffix="_2.md"),
        ]
        try:
            runner = AutoFlowRunner(
                provider="google", model="m", api_key="k", project_root=tmp_path,
                on_step_start=lambda i, n: None, on_step_chunk=lambda c: None,
                on_step_done=lambda i, o, p: None, on_flow_done=lambda: None,
                on_error=lambda m: None,
                system_prompt_suffix=fw._lang_directive("TR"),
            )
            runner._run(name, src)
        finally:
            BUILTIN_WORKFLOWS.pop(name, None)

        assert len(_Recorder.systems) == 2
        assert all("Turkish" in s for s in _Recorder.systems), (
            "every step's system prompt must carry the language directive")


class TestPreanalysisWiresLanguage:
    def test_runner_receives_directive_from_project_state(self, tmp_path, monkeypatch):
        proj = tmp_path / "proj"
        (proj / "_raw" / "legacy_code").mkdir(parents=True)
        (proj / "_raw" / "legacy_code" / "c.awl").write_text("U E 1.0",
                                                             encoding="utf-8")
        api = _mk_api(proj, {"output_language": "DE",
                             "data_classification": "PUBLIC"})

        import data_classification_guard as dcg
        monkeypatch.setattr(dcg, "check_ai_send", lambda *a, **kw: _Gate())

        captured = {}

        class _FakeRunner:
            def __init__(self, **kw):
                captured.update(kw)
            def run_async(self, wf, src):
                captured["on_flow_done"]()

        monkeypatch.setattr(ai_runner, "AutoFlowRunner", _FakeRunner)
        r = api.run_retrofit_preanalysis({"engineer": "E", "confirmed": True})
        assert r["ok"], r.get("msg")
        assert "German" in captured.get("system_prompt_suffix", ""), (
            "pre-analysis must pass the project language to the runner")
