"""Shared pytest fixtures + import-path setup for the test suite.

The project mixes two import styles:
  * `05_SCRIPTS/*.py` modules are imported by bare name (e.g. `import project_analyzer`).
  * `workbench.core.*` is imported as a package from the project root.

Both roots are placed on sys.path here so tests can import either style.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "05_SCRIPTS"

for p in (PROJECT_ROOT, SCRIPTS_DIR):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)


EXAMPLE_PROJECT = PROJECT_ROOT / "examples" / "Kunde_Mueller_Conveyor_Retrofit"


@pytest.fixture(autouse=True)
def _isolate_gui_settings(tmp_path_factory, monkeypatch):
    """No test may ever touch the REAL .gui_settings.json.

    2026-07-07 incident: a test built a real Api and called open_project(),
    which persisted the test's minimal settings dict over the user's live
    settings file (API-key sentinels, task routing, project roots — gone).
    Every test now reads/writes a throwaway settings file instead; tests
    that exercise the settings machinery keep working, against the copy.
    """
    try:
        import factory_web as fw
    except Exception:
        yield
        return
    tmp = tmp_path_factory.mktemp("gui_settings") / ".gui_settings.json"
    monkeypatch.setattr(fw, "GUI_SETTINGS", tmp, raising=False)
    if hasattr(fw, "WB_SETTINGS"):
        monkeypatch.setattr(fw, "WB_SETTINGS",
                            tmp.with_name(".workbench_settings.json"),
                            raising=False)
    try:  # ProjectManager persists last_project to its own settings file
        from workbench.core import project_manager as _pm
        monkeypatch.setattr(_pm, "SETTINGS_FILE",
                            tmp.with_name(".workbench_settings.json"),
                            raising=False)
    except Exception:
        pass
    yield


@pytest.fixture
def example_project(tmp_path) -> Path:
    """A writable copy of the bundled example project."""
    dst = tmp_path / "example_project"
    shutil.copytree(EXAMPLE_PROJECT, dst)
    return dst
