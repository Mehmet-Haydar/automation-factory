"""I-A2 regresyonu — ProjectManager.get_api_settings, .gui_settings.json'da
'__keyring__' placeholder gordugunde gercek key'i OS keystore'dan cekmeli,
literal string'i dondurmemeli.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

import workbench.core.project_manager as pm


def _install_mock_keyring(monkeypatch, password: str):
    mod = types.ModuleType("keyring")

    def get_password(service, username):
        if service == "AUTOMATION_FACTORY_webgui" and username == "anthropic":
            return password
        return None

    mod.get_password = get_password
    monkeypatch.setitem(sys.modules, "keyring", mod)


def test_placeholder_resolved_from_keystore(monkeypatch, tmp_path):
    # Pretend the factory root contains a .gui_settings.json with sentinel key.
    fake_root = tmp_path
    (fake_root / ".gui_settings.json").write_text(
        json.dumps({
            "ai_provider": "anthropic",
            "ai_model":    "claude-sonnet-4-6",
            "api_keys":    {"anthropic": "__keyring__"},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(pm, "FACTORY_ROOT", fake_root)
    _install_mock_keyring(monkeypatch, "sk-ant-real-secret")

    mgr = pm.ProjectManager()
    out = mgr.get_api_settings()
    assert out["api_key"] == "sk-ant-real-secret"
    # Crucially, the literal sentinel is never propagated.
    assert out["api_key"] != "__keyring__"


def test_placeholder_with_no_keyring_returns_empty(monkeypatch, tmp_path):
    fake_root = tmp_path
    (fake_root / ".gui_settings.json").write_text(
        json.dumps({
            "ai_provider": "anthropic",
            "api_keys":    {"anthropic": "__keyring__"},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(pm, "FACTORY_ROOT", fake_root)
    # Force "no keyring": pop module + make import raise.
    monkeypatch.delitem(sys.modules, "keyring", raising=False)
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fail_import(name, *args, **kwargs):
        if name == "keyring":
            raise ImportError("no keyring in this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fail_import)

    mgr = pm.ProjectManager()
    out = mgr.get_api_settings()
    # Sentinel must NOT be returned as a fake API key.
    assert out["api_key"] == ""


def test_plaintext_legacy_key_still_passes_through(monkeypatch, tmp_path):
    """A pre-W7 .gui_settings.json may still hold a plaintext key — keep
    returning it (the user has not yet migrated)."""
    fake_root = tmp_path
    (fake_root / ".gui_settings.json").write_text(
        json.dumps({
            "ai_provider": "anthropic",
            "api_keys":    {"anthropic": "sk-legacy-plain"},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(pm, "FACTORY_ROOT", fake_root)

    mgr = pm.ProjectManager()
    out = mgr.get_api_settings()
    assert out["api_key"] == "sk-legacy-plain"
