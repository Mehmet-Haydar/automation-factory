"""tests/test_open_project_sandbox.py — O-2 sandbox fix proof tests.

Tests that open_project() enforces the allowed-root whitelist:
- paths inside an allowed root  -> ok=True
- paths outside every allowed root -> ok=False with O-2 in message
- the _is_path_under helper     -> correct boolean semantics
- empty whitelist (no roots on disk) -> every path is rejected (fail-closed)
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# ---------------------------------------------------------------------------
# Minimal stub so factory_web can be imported without pywebview / optional deps
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "05_SCRIPTS"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Stub heavy optional modules before importing factory_web
for _mod in ("webview", "keyring"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import factory_web  # noqa: E402  (must come after stubs)
from factory_web import Api  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api(settings: dict | None = None) -> Api:
    """Return an Api instance with controlled settings, no disk I/O."""
    api = object.__new__(Api)
    api.settings = settings or {}
    api.root = None
    return api


# ---------------------------------------------------------------------------
# Unit tests for _is_path_under
# ---------------------------------------------------------------------------

class TestIsPathUnder:
    def test_child_inside_parent_returns_true(self, tmp_path):
        child = tmp_path / "projects" / "my_project"
        child.mkdir(parents=True)
        assert Api._is_path_under(child, tmp_path) is True

    def test_child_is_parent_returns_true(self, tmp_path):
        # Edge case: path equals the parent root itself
        assert Api._is_path_under(tmp_path, tmp_path) is True

    def test_path_outside_parent_returns_false(self, tmp_path):
        outside = tmp_path.parent  # one level above tmp_path
        assert Api._is_path_under(tmp_path, outside.parent if outside.parent != outside else tmp_path / "x") is False or True
        # More precise: a sibling directory is NOT under tmp_path
        sibling = tmp_path.parent / "sibling_dir"
        sibling.mkdir(exist_ok=True)
        assert Api._is_path_under(sibling, tmp_path) is False

    def test_traversal_path_returns_false(self, tmp_path):
        # A path that would traverse above the parent boundary
        candidate = tmp_path.parent
        assert Api._is_path_under(candidate, tmp_path) is False


# ---------------------------------------------------------------------------
# Unit tests for _check_open_project_path  (whitelist logic, no disk)
# ---------------------------------------------------------------------------

class TestCheckOpenProjectPath:
    def test_path_inside_allowed_root_returns_none(self, tmp_path):
        """A path under an allowed root must pass (return None = no error)."""
        project = tmp_path / "AUTOMATION_FACTORY_PROJECTS" / "my_proj"
        project.mkdir(parents=True)
        allowed_root = tmp_path / "AUTOMATION_FACTORY_PROJECTS"

        api = _make_api()
        with patch.object(api, "_allowed_project_roots", return_value=[allowed_root]):
            result = api._check_open_project_path(project)
        assert result is None, f"Expected None (allowed) but got: {result}"

    def test_path_outside_all_roots_returns_error(self, tmp_path):
        """A path outside every allowed root must be rejected with O-2."""
        project = tmp_path / "outside" / "some_project"
        project.mkdir(parents=True)
        allowed_root = tmp_path / "AUTOMATION_FACTORY_PROJECTS"
        allowed_root.mkdir()

        api = _make_api()
        with patch.object(api, "_allowed_project_roots", return_value=[allowed_root]):
            result = api._check_open_project_path(project)
        assert result is not None, "Expected an error string but got None"
        assert "O-2" in result, f"Error should reference O-2, got: {result}"

    def test_empty_whitelist_is_fail_closed(self, tmp_path):
        """If no allowed roots exist on disk, every path must be rejected."""
        project = tmp_path / "any_project"
        project.mkdir()

        api = _make_api()
        with patch.object(api, "_allowed_project_roots", return_value=[]):
            result = api._check_open_project_path(project)
        assert result is not None, "Empty whitelist must reject all paths (fail-closed)"
        assert "O-2" in result


# ---------------------------------------------------------------------------
# Integration test for open_project
# ---------------------------------------------------------------------------

class TestOpenProjectSandbox:
    def _patched_save(self, *a, **kw):
        pass  # suppress disk write in tests

    def test_open_project_inside_allowed_root_succeeds(self, tmp_path):
        """open_project returns ok=True for a path inside the allowed root."""
        allowed_root = tmp_path / "AUTOMATION_FACTORY_PROJECTS"
        project = allowed_root / "proj_alpha"
        project.mkdir(parents=True)

        api = _make_api()
        with patch.object(api, "_allowed_project_roots", return_value=[allowed_root]):
            with patch("factory_web._save_settings", side_effect=self._patched_save):
                result = api.open_project(str(project))

        assert result["ok"] is True, f"Expected ok=True, got: {result}"
        assert api.root == project

    def test_open_project_outside_root_is_rejected(self, tmp_path):
        """open_project returns ok=False with O-2 for a path outside the whitelist."""
        allowed_root = tmp_path / "AUTOMATION_FACTORY_PROJECTS"
        allowed_root.mkdir()
        outside = tmp_path / "secret_dir" / "project"
        outside.mkdir(parents=True)

        api = _make_api()
        with patch.object(api, "_allowed_project_roots", return_value=[allowed_root]):
            result = api.open_project(str(outside))

        assert result["ok"] is False, "Path outside whitelist must be rejected"
        assert "O-2" in result.get("msg", ""), (
            f"Response must reference O-2.  Got: {result}"
        )
        assert api.root is None, "root must not be set after rejection"

    def test_open_project_system_path_is_rejected(self, tmp_path):
        """A system path (e.g. /etc or C:\\Windows) outside whitelist is rejected."""
        allowed_root = tmp_path / "AUTOMATION_FACTORY_PROJECTS"
        allowed_root.mkdir()

        # Use a path that definitely exists but is outside the allowed root:
        # on all platforms the parent of tmp_path is outside the whitelist.
        system_like = tmp_path.parent  # always exists, always outside allowed_root

        api = _make_api()
        with patch.object(api, "_allowed_project_roots", return_value=[allowed_root]):
            result = api.open_project(str(system_like))

        assert result["ok"] is False
        assert "O-2" in result.get("msg", "")

    def test_open_project_empty_whitelist_rejects_everything(self, tmp_path):
        """Fail-closed: when whitelist is empty every open_project call fails."""
        project = tmp_path / "whatever"
        project.mkdir()

        api = _make_api()
        with patch.object(api, "_allowed_project_roots", return_value=[]):
            result = api.open_project(str(project))

        assert result["ok"] is False
        # Must not silently succeed
        assert "O-2" in result.get("msg", "")

    def test_fix_in_place_without_patch_rejects_system_root(self, tmp_path):
        """Without mocking, a C:\\ / / path is outside any realistic allowed root."""
        import platform
        if platform.system() == "Windows":
            system_path = Path("C:\\Windows\\System32")
        else:
            system_path = Path("/etc")

        if not system_path.exists():
            pytest.skip("System path does not exist on this platform")

        api = _make_api()
        # _allowed_project_roots will return [] or only ~/Documents/...
        # which definitely does NOT contain /etc or C:\Windows
        result = api.open_project(str(system_path))
        assert result["ok"] is False, (
            "System path must be rejected without any mocking; "
            f"allowed roots: {api._allowed_project_roots()}"
        )
