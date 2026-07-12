"""GUI New Project produces the canonical folder skeleton.

2026-07-07 restructure (E2E measurement): a full retrofit run left every
numbered template folder (01_DOCS…06_REPORTS, 99_FACTORY_REFS) EMPTY — the
product writes to _raw/_input/_output/metadata/REPORTS/_delivery. A new
project therefore creates ONLY the living structure, and the never-used
folders must NOT come back (two parallel worlds confused the workbench).
"""

import importlib
import tempfile
from pathlib import Path

import pytest

pm_mod = importlib.import_module("workbench.core.project_manager")
ProjectManager = pm_mod.ProjectManager
PROJECT_FOLDERS = pm_mod.PROJECT_FOLDERS


# The living data homes — every one has a real producer/consumer in the flow.
REQUIRED = [
    "_raw/legacy_code",  # customer legacy PLC sources (AWL/SEQ/S5D)
    "_raw/drawings",
    "_raw/photos",
    "_raw/docs",
    "_input",            # hardware exchange (hardware_config.xlsx, BOM)
    "_output",           # generated code (SCL in _output/scl, HMI layer)
    "metadata",          # 14-Point RD pack + decisions
    "REPORTS",           # deterministic reports (+ _ai_steps drafts)
    "_delivery",         # handover packages
]

# Dead template folders — measured empty after a full E2E run; must never
# be part of a fresh project again.
FORBIDDEN = [
    "01_DOCS", "02_HARDWARE", "03_PLC", "04_HMI", "05_TESTS", "06_REPORTS",
    "99_FACTORY_REFS",
]


@pytest.fixture()
def new_project():
    tmp = Path(tempfile.mkdtemp())
    pm = ProjectManager()
    root = pm.create_project(tmp, "kunde_test")
    assert root is not None and root.exists()
    return root


def test_canonical_folders_created(new_project):
    for folder in PROJECT_FOLDERS:
        assert (new_project / folder).is_dir(), f"missing canonical folder: {folder}"


def test_required_data_homes_exist(new_project):
    for folder in REQUIRED:
        assert (new_project / folder).is_dir(), f"missing data home: {folder}"


def test_dead_template_folders_stay_gone(new_project):
    for folder in FORBIDDEN:
        assert not (new_project / folder).exists(), \
            f"dead template folder resurrected: {folder}"


def test_rd_templates_seeded_into_metadata(new_project):
    rds = sorted(p.name for p in (new_project / "metadata").glob("RD*.md"))
    assert len(rds) == 14, f"expected 14 RD templates, got {len(rds)}: {rds}"


def test_create_refuses_existing(new_project):
    pm = ProjectManager()
    # Same path again -> None (do not clobber an existing project).
    assert pm.create_project(new_project.parent, new_project.name) is None


def test_folders_match_init_script_when_importable():
    # When script_project_init is importable, PROJECT_FOLDERS must be that exact
    # list (single source of truth), not the in-file fallback copy.
    try:
        from script_project_init import PROJECT_FOLDERS as canonical  # type: ignore
    except Exception:
        pytest.skip("script_project_init not importable in this environment")
    assert PROJECT_FOLDERS == canonical
