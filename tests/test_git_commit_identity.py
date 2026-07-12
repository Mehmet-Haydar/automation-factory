"""tests/test_git_commit_identity.py — O-2 git identity fix proof tests.

Tests that git_commit() forwards user_name / user_email to manual_commit:
- when settings has username/user_email  -> forwarded verbatim
- when settings is empty                 -> sentinel values used (not empty strings)
- sentinel values emit a logging.warning -> observable gap
- manual_commit is never called with ("", "") after the fix
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

for _mod in ("webview", "keyring"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import factory_web  # noqa: E402
from factory_web import Api  # noqa: E402


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_api(settings: dict | None = None, root: Path | None = None) -> Api:
    api = object.__new__(Api)
    api.settings = settings or {}
    api.root = root
    return api


def _fake_git_result(ok=True, message="Commit successful: test"):
    r = MagicMock()
    r.ok = ok
    r.message = message
    return r


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGitCommitIdentity:

    def test_user_name_and_email_forwarded_from_settings(self, tmp_path):
        """When settings has username + user_email both must reach manual_commit."""
        (tmp_path / ".git").mkdir()  # make it look like a git repo
        api = _make_api(
            settings={"username": "Mehmet Haydar", "user_email": "mehmet@example.com"},
            root=tmp_path,
        )
        fake_result = _fake_git_result()

        with patch("factory_web.Api.git_commit.__module__"):
            pass  # just ensure module loaded

        with patch.dict("sys.modules", {"project_git": MagicMock()}):
            import project_git as pg  # noqa: F811
            pg.manual_commit = MagicMock(return_value=fake_result)

            result = api.git_commit("my commit message")

        pg.manual_commit.assert_called_once()
        _, kwargs = pg.manual_commit.call_args
        assert kwargs.get("user_name") == "Mehmet Haydar", (
            f"user_name not forwarded: {kwargs}"
        )
        assert kwargs.get("user_email") == "mehmet@example.com", (
            f"user_email not forwarded: {kwargs}"
        )
        assert result["ok"] is True

    def test_missing_settings_uses_sentinel_not_empty_string(self, tmp_path):
        """When settings has no username/email, sentinel values replace empty strings.

        The OLD code passed ("", "") silently.  The NEW code must use a sentinel
        so the gap is visible in git log.
        """
        (tmp_path / ".git").mkdir()
        api = _make_api(settings={}, root=tmp_path)  # no username, no user_email
        fake_result = _fake_git_result()

        with patch.dict("sys.modules", {"project_git": MagicMock()}):
            import project_git as pg  # noqa: F811
            pg.manual_commit = MagicMock(return_value=fake_result)

            api.git_commit("update")

        _, kwargs = pg.manual_commit.call_args
        # Must NOT be empty strings — that was the pre-fix behaviour
        assert kwargs.get("user_name") != "", (
            "user_name must not be empty string after O-2 fix"
        )
        assert kwargs.get("user_email") != "", (
            "user_email must not be empty string after O-2 fix"
        )
        # Must use the sentinel values
        assert kwargs.get("user_name") == "anonymous", (
            f"Expected sentinel 'anonymous', got: {kwargs.get('user_name')!r}"
        )
        assert kwargs.get("user_email") == "anonymous@factory-web.local", (
            f"Expected sentinel email, got: {kwargs.get('user_email')!r}"
        )

    def test_missing_identity_emits_warning(self, tmp_path, caplog):
        """When identity is missing, a logging.WARNING must be emitted (O-2)."""
        (tmp_path / ".git").mkdir()
        api = _make_api(settings={}, root=tmp_path)
        fake_result = _fake_git_result()

        with patch.dict("sys.modules", {"project_git": MagicMock()}):
            import project_git as pg  # noqa: F811
            pg.manual_commit = MagicMock(return_value=fake_result)

            with caplog.at_level(logging.WARNING):
                api.git_commit("update")

        warning_texts = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("O-2" in t for t in warning_texts), (
            f"Expected a WARNING referencing O-2, got: {warning_texts}"
        )

    def test_only_missing_email_triggers_sentinel_and_warning(self, tmp_path, caplog):
        """When username is set but user_email is missing, sentinel email is used."""
        (tmp_path / ".git").mkdir()
        api = _make_api(settings={"username": "Alice"}, root=tmp_path)
        fake_result = _fake_git_result()

        with patch.dict("sys.modules", {"project_git": MagicMock()}):
            import project_git as pg  # noqa: F811
            pg.manual_commit = MagicMock(return_value=fake_result)

            with caplog.at_level(logging.WARNING):
                api.git_commit("update")

        _, kwargs = pg.manual_commit.call_args
        assert kwargs.get("user_name") == "Alice"
        assert kwargs.get("user_email") == "anonymous@factory-web.local"
        warning_texts = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("O-2" in t for t in warning_texts)

    def test_no_project_returns_error(self):
        """git_commit with no open project must return ok=False immediately."""
        api = _make_api(settings={}, root=None)
        result = api.git_commit("anything")
        assert result["ok"] is False
        assert "project" in result.get("msg", "").lower()

    def test_old_behaviour_would_fail(self, tmp_path):
        """Regression: the old code passed no user_name/user_email kwargs.

        This test verifies the fix is load-bearing: if the fix were removed and
        manual_commit received NO user_name/user_email kwargs, we would see
        them missing.  We assert that after the fix they ARE present.
        """
        (tmp_path / ".git").mkdir()
        api = _make_api(
            settings={"username": "Engineer", "user_email": "eng@corp.local"},
            root=tmp_path,
        )
        fake_result = _fake_git_result()

        with patch.dict("sys.modules", {"project_git": MagicMock()}):
            import project_git as pg  # noqa: F811
            pg.manual_commit = MagicMock(return_value=fake_result)
            api.git_commit("deploy")

        _, kwargs = pg.manual_commit.call_args
        # These kwargs were absent before the fix
        assert "user_name" in kwargs, "user_name kwarg must be passed (O-2 fix)"
        assert "user_email" in kwargs, "user_email kwarg must be passed (O-2 fix)"
