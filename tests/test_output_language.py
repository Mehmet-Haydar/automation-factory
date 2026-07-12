"""Analysis/output language selection (TR / EN / DE).

Generation prose follows PROJECT_STATE.output_language via _lang_directive;
tag names / SCL keywords stay English. These pin the get/set endpoints + the
directive wiring.
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw


def _api(root: Path) -> fw.Api:
    (root / "PROJECT_STATE.json").write_text(json.dumps({"gate": 1}), encoding="utf-8")
    api = fw.Api()
    api.root = root
    api.settings = {}
    return api


def _state(root: Path) -> dict:
    return json.loads((root / "PROJECT_STATE.json").read_text(encoding="utf-8"))


def test_default_language_is_en(tmp_path):
    api = _api(tmp_path)
    r = api.get_output_language()
    assert r["ok"] and r["language"] == "EN"
    assert set(r["supported"]) == {"TR", "EN", "DE"}


def test_set_language_persists(tmp_path):
    api = _api(tmp_path)
    assert api.set_output_language("tr")["language"] == "TR"   # case-insensitive
    assert _state(tmp_path)["output_language"] == "TR"
    assert api.get_output_language()["language"] == "TR"
    assert api._output_language() == "TR"


def test_invalid_language_rejected(tmp_path):
    api = _api(tmp_path)
    r = api.set_output_language("FR")
    assert r["ok"] is False
    assert "output_language" not in _state(tmp_path)


def test_directive_reflects_language(tmp_path):
    api = _api(tmp_path)
    api.set_output_language("DE")
    assert "German" in fw._lang_directive(api._output_language())
    api.set_output_language("TR")
    assert "Turkish" in fw._lang_directive(api._output_language())
    # EN → no directive (English is the base language)
    api.set_output_language("EN")
    assert fw._lang_directive(api._output_language()) == ""


def test_set_language_no_project():
    api = fw.Api()
    api.root = None
    assert api.set_output_language("TR")["ok"] is False
