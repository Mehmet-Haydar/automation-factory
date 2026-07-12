"""Proof tests — task routing output-ceiling guard (E2E #2, F5).

RD05/09/10 drafts were silently cut mid-table when a long-output task was
routed to deepseek (hard 8192-token output cap). The user's routing choice
is still respected — but get_provider_for_task must say the risk out loud
so the consent modal can show it BEFORE tokens are spent.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import factory_web  # noqa: E402


def _api(routing):
    api = factory_web.Api()
    api.settings = {"task_routing": routing,
                    "api_keys": {"deepseek": "x", "anthropic": "x",
                                 "google": "x", "openai": "x"}}
    api._resolve_api_key = lambda p: "x"
    return api


def test_long_output_task_on_capped_provider_warns():
    api = _api({"default": "anthropic", "preanalysis": "deepseek",
                "scl_generation": "deepseek"})
    for task in ("preanalysis", "scl_generation"):
        r = api.get_provider_for_task(task)
        assert r["provider"] == "deepseek", "user's routing stays respected"
        assert "8192" in r.get("warning", ""), \
            f"{task}: truncation risk must be stated"
        assert "Settings" in r["warning"]


def test_high_cap_providers_stay_silent():
    api = _api({"default": "anthropic", "preanalysis": "google",
                "scl_generation": "anthropic"})
    for task in ("default", "preanalysis", "scl_generation"):
        assert "warning" not in api.get_provider_for_task(task)


def test_short_output_task_never_warns():
    api = _api({"default": "anthropic", "translation": "deepseek"})
    assert "warning" not in api.get_provider_for_task("translation"), \
        "translation fits in 8k — warning would be noise"


def test_gui_surfaces_the_warning():
    app_js = (Path(factory_web.__file__).resolve().parent.parent
              / "webgui" / "app.js").read_text(encoding="utf-8")
    assert "provInfo.warning" in app_js, "consent modal must receive it"
    assert "Output-ceiling risk" in app_js
