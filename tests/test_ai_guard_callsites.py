"""C-A4 regresyonu — *meta* test: factory_web.Api'nin AIClient'i instantiate
eden HER metodu, paylaşımdan önce data-classification kapısını çağırmalı.

Önceki C4 fix yalnızca run_workflow / run_ai_prompt / get_ai_suggestion'a
guard ekledi; normalize_prompt atlandı, böylece CONFIDENTIAL bir projeden
seçilen metin "+ New Prompt" diyalogundan public Anthropic endpoint'ine
sızabiliyordu. Yeni bir AI çağrı yolu eklendiğinde bu test, kapı çağrılmadan
açıkta kalmadığını yakalar.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest

import factory_web as fw


# Each entry: (method_name, callable that invokes it on an Api instance).
# The callable returns the dict the method returns to the JS bridge.
AI_METHODS: list[tuple[str, Callable[[fw.Api], dict]]] = [
    ("normalize_prompt",   lambda api: api.normalize_prompt("hello", "analyze")),
    ("run_ai_prompt",      lambda api: api.run_ai_prompt("say hi")),
    ("run_workflow",       lambda api: api.run_workflow("Analyze → Validate")),
    ("get_ai_suggestion",  lambda api: api.get_ai_suggestion("IF foo THEN", 1)),
]


@pytest.fixture
def confidential_project(tmp_path: Path) -> Path:
    """Project root flagged CONFIDENTIAL — public-tier AI providers MUST be
    refused by the data-classification guard."""
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\nproject_name: secret\ndata_classification: CONFIDENTIAL\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "PROJECT_STATE.json").write_text("{}", encoding="utf-8")
    return tmp_path


def _make_api(project_root: Path) -> fw.Api:
    api = fw.Api()
    api.root = project_root
    # Provide a non-empty API key (anthropic = public-tier) and "api" mode so
    # the early "no_api_key / clipboard" short-circuit doesn't fire — the
    # request must reach the guard.
    api.settings = {
        "ai_provider": "anthropic",
        "ai_model":    "claude-sonnet-4-6",
        "ai_mode":     "api",
        "api_keys":    {"anthropic": "sk-test-fake"},
    }
    return api


@pytest.mark.parametrize("name,invoke", AI_METHODS, ids=[m[0] for m in AI_METHODS])
def test_ai_method_calls_classification_guard(
    monkeypatch, confidential_project, name, invoke,
):
    """Each AI method must consult _ai_send_allowed and refuse on a deny."""
    calls: list[str] = []

    real_guard = fw.Api._ai_send_allowed

    def fake_guard(self, provider: str):
        calls.append(provider)
        return False, "TEST-BLOCKED"

    monkeypatch.setattr(fw.Api, "_ai_send_allowed", fake_guard)

    # If AIClient is somehow constructed despite the guard saying no, fail
    # the test loudly — that's the bug we're guarding against.
    import ai_client
    def boom(*a, **kw):
        raise AssertionError(
            f"{name}: AIClient was instantiated AFTER the classification "
            "guard returned deny — the call site is bypassing C-A4 guard."
        )
    monkeypatch.setattr(ai_client, "AIClient", boom)

    api = _make_api(confidential_project)
    result = invoke(api)

    assert calls, f"{name} never consulted _ai_send_allowed"
    assert result.get("ok") is False, f"{name} should report ok=False on deny"
    assert "TEST-BLOCKED" in str(result.get("msg", "")), (
        f"{name} did not surface the guard's reason to the UI: {result}"
    )


def test_real_guard_blocks_normalize_prompt_on_confidential(
    monkeypatch, confidential_project,
):
    """End-to-end: with the REAL guard (not mocked), normalize_prompt on a
    CONFIDENTIAL project + public-tier provider must refuse."""
    # Make sure no AI call goes out.
    import ai_client
    def boom(*a, **kw):
        raise AssertionError("AIClient instantiated despite CONFIDENTIAL guard")
    monkeypatch.setattr(ai_client, "AIClient", boom)

    api = _make_api(confidential_project)
    out = api.normalize_prompt("customer's secret IO list", "analyze")
    assert out["ok"] is False
    assert out.get("blocked") == "classification"
