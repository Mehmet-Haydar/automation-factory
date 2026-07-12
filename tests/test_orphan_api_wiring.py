"""Proof tests — orphan APIs wired into the GUI (G-03, 2026-07-10 audit).

generate_sequence_fb (the ONLY AI code artifact), rd03_chat_propose/apply
and get_rd01_crosscheck were fully functional backend endpoints with no
GUI reach. Contract now: the first two are gate actions dispatched by
run_pipeline, the chat pair drives the flowchart view's chat panel.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import factory_web as fw  # noqa: E402


def _api(root: Path):
    api = fw.Api()
    api.root = root
    api.settings = {}
    return api


def _proj(tmp_path: Path) -> Path:
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "PROJECT_STATE.json").write_text(json.dumps({"gate": 3}),
                                             encoding="utf-8")
    return proj


def test_gate_config_lists_the_new_actions():
    acts3 = fw.GATE_CONFIG[2]["actions"]
    acts4 = fw.GATE_CONFIG[3]["actions"]
    assert "rd01_crosscheck" in acts3
    assert "generate_sequence_fb" in acts4


def test_run_pipeline_dispatches_rd01_crosscheck(tmp_path):
    api = _api(_proj(tmp_path))
    r = api.run_pipeline("rd01_crosscheck")
    assert "Unknown" not in str(r.get("output", "")), r
    assert r.get("ok") is True
    assert "cross-check" in r["output"].lower()


def test_run_pipeline_dispatches_generate_sequence_fb(tmp_path):
    api = _api(_proj(tmp_path))
    r = api.run_pipeline("generate_sequence_fb")
    # no RD03/API key in the fixture — must answer with the endpoint's own
    # refusal, never "Unknown action"
    assert r.get("ok") is False
    assert "Unknown" not in str(r.get("output", "")), r
    assert r.get("output"), "endpoint message must reach the action log"


def test_gui_carries_labels_and_chat_panel():
    app_js = (Path(fw.__file__).resolve().parent.parent
              / "webgui" / "app.js").read_text(encoding="utf-8")
    for token in ("generate_sequence_fb", "rd01_crosscheck",
                  "rd03_chat_propose", "rd03_chat_apply",
                  "fc-chat-apply", "fc-chat-discard"):
        assert token in app_js, f"GUI wiring missing: {token}"
    assert "DRAFT" in app_js.split("fc-chat-apply")[0].split("fc-chat")[-2] \
        or "demotes" in app_js, "apply button must state the DRAFT demotion"
