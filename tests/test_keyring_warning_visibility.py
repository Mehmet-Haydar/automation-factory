"""S-9 (B-G9) — plaintext API-key fallback must be visible in the GUI.

When ``keyring`` is unavailable, keys land in .gui_settings.json in
plaintext. The old code wrote ONE stderr line at first save — invisible
to a GUI user who just typed their key in the Settings dialog. The
warning now also enters the ``_warn`` queue (category="security"), which
``_attach_warnings`` delivers with the save response.
"""

from __future__ import annotations

import importlib

fw = importlib.import_module("factory_web")


class TestPlaintextFallbackWarns:
    def _save_with_broken_keyring(self, monkeypatch, tmp_path):
        monkeypatch.setattr(fw, "GUI_SETTINGS", tmp_path / ".gui_settings.json")
        monkeypatch.setattr(fw, "_kr_set", lambda prov, key: False)  # keyring dead
        fw._flush_warnings()  # drain anything pending
        fw._save_settings({"api_keys": {"anthropic": "sk-test-123"}})
        return fw._flush_warnings()

    def test_warning_enters_gui_queue(self, monkeypatch, tmp_path):
        warnings = self._save_with_broken_keyring(monkeypatch, tmp_path)
        sec = [w for w in warnings if w.get("category") == "security"]
        assert sec, "plaintext fallback GUI uyarı kuyruğuna girmedi (yalnız stderr)"
        assert "PLAINTEXT" in sec[0]["msg"] and "anthropic" in sec[0]["msg"]

    def test_warning_repeats_on_every_save(self, monkeypatch, tmp_path):
        # The stderr line is once-only; the GUI warning must NOT be — the
        # user can open Settings again tomorrow.
        self._save_with_broken_keyring(monkeypatch, tmp_path)
        warnings = self._save_with_broken_keyring(monkeypatch, tmp_path)
        assert any(w.get("category") == "security" for w in warnings), (
            "ikinci kayıtta uyarı yutuldu — _KEYRING_WARN_EMITTED GUI yolunu "
            "kapatmamalı")

    def test_no_warning_when_keyring_works(self, monkeypatch, tmp_path):
        monkeypatch.setattr(fw, "GUI_SETTINGS", tmp_path / ".gui_settings.json")
        monkeypatch.setattr(fw, "_kr_set", lambda prov, key: True)
        fw._flush_warnings()
        fw._save_settings({"api_keys": {"anthropic": "sk-test-123"}})
        warnings = fw._flush_warnings()
        assert not any(w.get("category") == "security" for w in warnings)
