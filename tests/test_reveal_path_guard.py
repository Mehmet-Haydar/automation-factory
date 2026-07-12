"""I-A3 regresyonu — reveal_path absolute path veya '..' iceren path'i
reddetmeli; sadece project root altina izin verilmeli.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import factory_web as fw


def _api_with_root(tmp_path: Path) -> fw.Api:
    api = fw.Api()
    api.root = tmp_path
    return api


def _no_explorer(monkeypatch):
    """Stub subprocess.Popen so the test never launches Explorer."""
    import subprocess

    calls = []

    def fake_popen(args, *a, **kw):
        calls.append(args)
        return types.SimpleNamespace(pid=12345)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    return calls


def test_absolute_path_refused(tmp_path, monkeypatch):
    api = _api_with_root(tmp_path)
    calls = _no_explorer(monkeypatch)

    # Pick a path that always exists on Windows so the old code branch
    # would have opened it.
    target = "C:\\Windows" if sys.platform == "win32" else "/etc"
    r = api.reveal_path(target)

    assert r["ok"] is False
    assert "absolute" in r["msg"].lower()
    assert calls == []  # Explorer must not have been launched.


def test_traversal_path_refused(tmp_path, monkeypatch):
    api = _api_with_root(tmp_path)
    calls = _no_explorer(monkeypatch)

    # Use both separator styles — guard must catch either on any OS
    for bad_path in ["../../etc", "..\\..\\Windows"]:
        r = api.reveal_path(bad_path)
        assert r["ok"] is False, f"Expected traversal to be refused: {bad_path!r}"
    assert calls == []


def test_relative_inside_project_allowed(tmp_path, monkeypatch):
    sub = tmp_path / "REPORTS"
    sub.mkdir()
    api = _api_with_root(tmp_path)
    calls = _no_explorer(monkeypatch)

    r = api.reveal_path("REPORTS")
    assert r["ok"] is True
    # Explorer was invoked with the resolved sub-folder.
    assert calls and str(sub) in str(calls[0][1])
