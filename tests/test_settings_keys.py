"""W7 + C-A2 — API anahtarlari OS keystore'da saklanir, JSON'da duz metin yok,
ve Api objesi/JS bridge plaintext anahtari ne bellekte tutar ne de gonderir.
"""

import io
import json
import sys
import types
import factory_web as fw


def _make_mock_keyring():
    """Minimal in-memory keyring mock."""
    store: dict[tuple, str] = {}

    mod = types.ModuleType("keyring_mock")

    def set_password(service, username, password):
        store[(service, username)] = password

    def get_password(service, username):
        return store.get((service, username))

    mod.set_password = set_password
    mod.get_password = get_password
    mod._store = store
    return mod


def test_api_key_not_stored_plaintext(tmp_path):
    mock_kr = _make_mock_keyring()
    settings_file = tmp_path / ".gui_settings.json"

    original_kr = fw._keyring
    original_kr_ok = fw._KEYRING_OK
    original_settings = fw.GUI_SETTINGS
    try:
        fw._keyring = mock_kr
        fw._KEYRING_OK = True
        fw.GUI_SETTINGS = settings_file

        data = {"api_keys": {"anthropic": "sk-ant-secret123"}}
        fw._save_settings(data)

        on_disk = json.loads(settings_file.read_text(encoding="utf-8"))
        assert on_disk["api_keys"]["anthropic"] != "sk-ant-secret123"
        assert on_disk["api_keys"]["anthropic"] == fw._KEYRING_PLACEHOLDER
    finally:
        fw._keyring = original_kr
        fw._KEYRING_OK = original_kr_ok
        fw.GUI_SETTINGS = original_settings


def test_api_key_resolved_on_demand_not_on_load(tmp_path):
    """C-A2: _load_settings MUST NOT decrypt placeholders into plaintext —
    that would let the Api object hold plaintext keys in memory and ship
    them across the JS bridge. Resolution happens only on demand via
    Api._resolve_api_key()."""
    mock_kr = _make_mock_keyring()
    mock_kr._store[(fw._KEYRING_SERVICE, "openai")] = "sk-openai-secret"

    settings_file = tmp_path / ".gui_settings.json"
    settings_file.write_text(
        json.dumps({"api_keys": {"openai": fw._KEYRING_PLACEHOLDER}}),
        encoding="utf-8",
    )

    original_kr = fw._keyring
    original_kr_ok = fw._KEYRING_OK
    original_settings = fw.GUI_SETTINGS
    try:
        fw._keyring = mock_kr
        fw._KEYRING_OK = True
        fw.GUI_SETTINGS = settings_file

        loaded = fw._load_settings()
        # Plaintext NEVER materializes during load.
        assert loaded["api_keys"]["openai"] == fw._KEYRING_PLACEHOLDER

        # The Api class resolves it lazily when an AI call needs it.
        api = fw.Api()
        api.settings = loaded
        assert api._resolve_api_key("openai") == "sk-openai-secret"
        assert api._resolve_api_key("missing") == ""
    finally:
        fw._keyring = original_kr
        fw._KEYRING_OK = original_kr_ok
        fw.GUI_SETTINGS = original_settings


def test_get_settings_does_not_leak_plaintext_keys(tmp_path):
    """C-A2: the JS bridge response must NEVER include plaintext API keys.
    Only a non-secret status flag may be exposed."""
    mock_kr = _make_mock_keyring()
    mock_kr._store[(fw._KEYRING_SERVICE, "anthropic")] = "sk-ant-very-secret"

    settings_file = tmp_path / ".gui_settings.json"
    settings_file.write_text(
        json.dumps({
            "api_keys": {
                "anthropic": fw._KEYRING_PLACEHOLDER,
                "openai":    "sk-legacy-plaintext",
            },
        }),
        encoding="utf-8",
    )

    original_kr = fw._keyring
    original_kr_ok = fw._KEYRING_OK
    original_settings = fw.GUI_SETTINGS
    try:
        fw._keyring = mock_kr
        fw._KEYRING_OK = True
        fw.GUI_SETTINGS = settings_file

        api = fw.Api()
        s = api.get_settings()

        # No plaintext keys anywhere in the bridge payload.
        assert "api_keys" not in s
        text = json.dumps(s)
        assert "sk-ant-very-secret" not in text
        assert "sk-legacy-plaintext" not in text

        # Status is exposed instead.
        status = s["api_keys_status"]
        assert status["anthropic"] == "set"
        assert status["openai"]    == "unsafe"  # legacy plaintext on disk
        assert s["keyring_available"] is True
    finally:
        fw._keyring = original_kr
        fw._KEYRING_OK = original_kr_ok
        fw.GUI_SETTINGS = original_settings


def test_save_settings_does_not_wipe_keystore_on_empty(tmp_path):
    """C-A2: an empty value from the JS UI MUST mean 'leave as-is', not
    'delete the keystore entry'. Otherwise a benign Save click clears every
    provider that wasn't retyped."""
    mock_kr = _make_mock_keyring()
    mock_kr._store[(fw._KEYRING_SERVICE, "anthropic")] = "sk-existing"

    settings_file = tmp_path / ".gui_settings.json"
    settings_file.write_text(
        json.dumps({"api_keys": {"anthropic": fw._KEYRING_PLACEHOLDER}}),
        encoding="utf-8",
    )

    original_kr = fw._keyring
    original_kr_ok = fw._KEYRING_OK
    original_settings = fw.GUI_SETTINGS
    try:
        fw._keyring = mock_kr
        fw._KEYRING_OK = True
        fw.GUI_SETTINGS = settings_file

        api = fw.Api()
        # JS sends empty api_keys (user just changed theme, didn't touch keys).
        api.save_settings_data({"theme": "light", "api_keys": {"anthropic": ""}})

        # Keystore entry must still be intact.
        assert mock_kr._store[(fw._KEYRING_SERVICE, "anthropic")] == "sk-existing"
        # Disk still has the sentinel.
        on_disk = json.loads(settings_file.read_text(encoding="utf-8"))
        assert on_disk["api_keys"]["anthropic"] == fw._KEYRING_PLACEHOLDER
    finally:
        fw._keyring = original_kr
        fw._KEYRING_OK = original_kr_ok
        fw.GUI_SETTINGS = original_settings


def test_keyring_unavailable_emits_visible_warning(tmp_path, capsys):
    """C-A2: when keyring is missing, the user MUST see a stderr warning so
    they understand the key is being persisted in plaintext."""
    settings_file = tmp_path / ".gui_settings.json"

    original_kr = fw._keyring
    original_kr_ok = fw._KEYRING_OK
    original_settings = fw.GUI_SETTINGS
    original_warn = fw._KEYRING_WARN_EMITTED
    try:
        fw._keyring = None
        fw._KEYRING_OK = False
        fw.GUI_SETTINGS = settings_file
        fw._KEYRING_WARN_EMITTED = False  # reset so this test can observe it

        fw._save_settings({"api_keys": {"anthropic": "sk-fallback"}})

        captured = capsys.readouterr()
        assert "keyring" in captured.err.lower()
        assert "plaintext" in captured.err.lower()
    finally:
        fw._keyring = original_kr
        fw._KEYRING_OK = original_kr_ok
        fw.GUI_SETTINGS = original_settings
        fw._KEYRING_WARN_EMITTED = original_warn


def test_keyring_unavailable_falls_back_to_plaintext(tmp_path):
    settings_file = tmp_path / ".gui_settings.json"

    original_kr = fw._keyring
    original_kr_ok = fw._KEYRING_OK
    original_settings = fw.GUI_SETTINGS
    try:
        fw._keyring = None
        fw._KEYRING_OK = False
        fw.GUI_SETTINGS = settings_file

        data = {"api_keys": {"anthropic": "sk-fallback"}}
        fw._save_settings(data)

        on_disk = json.loads(settings_file.read_text(encoding="utf-8"))
        # With no keyring, key is stored as-is (graceful fallback)
        assert on_disk["api_keys"]["anthropic"] == "sk-fallback"
    finally:
        fw._keyring = original_kr
        fw._KEYRING_OK = original_kr_ok
        fw.GUI_SETTINGS = original_settings
