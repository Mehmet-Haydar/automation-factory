"""Proof tests — workbench restructure (E2E findings, 2026-07-07).

Pins the three decisions from the measured E2E blind-test run #1:
  1. Token defaults ×4 (the AI client's per-provider clamp keeps it safe).
  2. AI step copies: ONE living file per artifact (REPORTS/_ai_steps/,
     stable name, old timestamped duplicates removed on regeneration).
  3. Opening an old project prunes the dead template folders — but ONLY
     when truly empty (a folder with any file anywhere below survives).
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw
from workbench.core.ai_runner import WorkflowStep, _step_output_path


# ------------------------------------------------------------ tokens ------

def test_provider_token_defaults_are_4x():
    m = fw._PROVIDER_META
    assert m["anthropic"]["default_max_tokens"] == 32768
    assert m["google"]["default_max_tokens"] == 65536
    assert m["deepseek"]["default_max_tokens"] == 16384
    assert m["openai"]["default_max_tokens"] == 16384
    assert WorkflowStep(name="x", prompt_template="y",
                        output_suffix=".md").max_tokens == 16384


def test_ai_client_clamps_to_real_provider_ceiling():
    """The generous budgets are safe ONLY because the client clamps every
    request to the provider's real output cap — pin that the cap table
    still exists and deepseek stays at its physical 8192."""
    from ai_client import AIClient
    caps = AIClient._PROVIDER_MAX_OUTPUT
    assert caps["deepseek"] == 8192 and caps["openai"] == 16384
    assert caps["anthropic"] >= 32768 and caps["google"] >= 65536


# ------------------------------------------------------------ ai steps ----

def test_step_output_single_living_copy(tmp_path):
    reports = tmp_path / "REPORTS"
    reports.mkdir()
    # old-style timestamped duplicates from three earlier runs
    for ts in ("20260705_0900", "20260706_1200", "20260707_1318"):
        (reports / f"_concat_{ts}_RD05_draft.md").write_text("old",
                                                             encoding="utf-8")
    name, path = _step_output_path(reports, "_concat", "_RD05_draft.md")
    assert name == "_concat_RD05_draft.md"
    assert path.parent.name == "_ai_steps"
    assert not list(reports.glob("_concat_2*_RD05_draft.md")), \
        "eski zaman damgalı kopyalar silinmeli — bir tane kalsın"
    # a second regeneration reuses the SAME path (replace, not accumulate)
    path.write_text("run1", encoding="utf-8")
    name2, path2 = _step_output_path(reports, "_concat", "_RD05_draft.md")
    assert path2 == path
    path2.write_text("run2", encoding="utf-8")
    assert len(list(path.parent.glob("*_RD05_draft.md"))) == 1
    # other artifacts' files are untouched by the cleanup
    (reports / "_concat_20260707_1318_RD06_draft.md").write_text(
        "other", encoding="utf-8")
    _step_output_path(reports, "_concat", "_RD05_draft.md")
    assert (reports / "_concat_20260707_1318_RD06_draft.md").exists()


# ------------------------------------------------------------ pruning -----

def test_open_project_prunes_only_truly_empty_dead_dirs(tmp_path):
    proj = tmp_path / "proj"
    (proj / "metadata").mkdir(parents=True)
    (proj / "PROJECT_STATE.json").write_text(json.dumps({"gate": 1}),
                                             encoding="utf-8")
    (proj / "01_DOCS").mkdir()                      # empty → prune
    (proj / "05_TESTS" / "sub").mkdir(parents=True)  # only empty subdir → prune
    (proj / "03_PLC" / "SCL").mkdir(parents=True)   # has a FILE → keep
    (proj / "03_PLC" / "SCL" / "FB_X.scl").write_text("x", encoding="utf-8")
    api = fw.Api()
    api.settings = {"projects_folder": str(tmp_path),
                    "project_roots": [str(tmp_path)]}
    r = api.open_project(str(proj))
    assert r["ok"], r
    assert not (proj / "01_DOCS").exists()
    assert not (proj / "05_TESTS").exists()
    assert (proj / "03_PLC" / "SCL" / "FB_X.scl").exists(), \
        "içi dolu klasör ASLA budanmaz"
