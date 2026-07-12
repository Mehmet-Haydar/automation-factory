"""W-A6 regresyonu — save_file kontrol dosyalarini (PROJECT_STATE.json,
PROJECT_MAESTRO.md) reddetmeli; aksi halde JS bridge gate'i 7'ye, classification'i
PUBLIC'e zorlayabilir ve daha onceki tum guard'lar bypass edilir.
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw


def _api(root: Path) -> fw.Api:
    api = fw.Api()
    api.root = root
    api.settings = {}
    return api


def test_save_file_refuses_project_state_json(tmp_path: Path):
    state = {"gate": 2, "data_classification": "CONFIDENTIAL"}
    (tmp_path / "PROJECT_STATE.json").write_text(json.dumps(state), encoding="utf-8")

    api = _api(tmp_path)
    payload = json.dumps({"gate": 7, "data_classification": "PUBLIC",
                          "last_validation": {"errors": 0}})
    r = api.save_file("PROJECT_STATE.json", payload)

    assert r["ok"] is False
    assert "control" in r["msg"].lower()
    # File on disk MUST remain untouched.
    on_disk = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    assert on_disk == state


def test_save_file_refuses_project_maestro_md(tmp_path: Path):
    original = "---\ndata_classification: CONFIDENTIAL\n---\n# Original\n"
    (tmp_path / "PROJECT_MAESTRO.md").write_text(original, encoding="utf-8")

    api = _api(tmp_path)
    r = api.save_file("PROJECT_MAESTRO.md",
                      "---\ndata_classification: PUBLIC\n---\n# Hacked\n")

    assert r["ok"] is False
    assert (tmp_path / "PROJECT_MAESTRO.md").read_text(encoding="utf-8") == original


def test_save_file_still_writes_ordinary_markdown(tmp_path: Path):
    api = _api(tmp_path)
    r = api.save_file("notes.md", "# notes\nhello\n")
    assert r["ok"] is True
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "# notes\nhello\n"
