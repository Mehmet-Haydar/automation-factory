"""W5 — show_standards gercek standart dosyalarina yonlendirildi."""

import importlib

fw = importlib.import_module("factory_web")


def test_show_standards_returns_content(tmp_path):
    api = fw.Api()
    api.root = tmp_path  # isolated settings: no ambient last_project anymore
    # Point FACTORY_ROOT to tmp_path so we control the files
    import factory_web as _fw
    original = _fw.FACTORY_ROOT
    try:
        rules = tmp_path / "01_GLOBAL_STANDARDS" / "rules"
        rules.mkdir(parents=True)
        (rules / "GLOBAL_NAMING_STANDARD.md").write_text(
            "# Naming Standard\n\nUse FB_ prefix for function blocks.\n",
            encoding="utf-8",
        )
        _fw.FACTORY_ROOT = tmp_path
        result = api.run_pipeline("show_standards")
        assert result["ok"] is True
        assert "not found" not in result["output"].lower()
        assert len(result["output"]) > 10
    finally:
        _fw.FACTORY_ROOT = original


def test_show_standards_lists_all_rules(tmp_path):
    import factory_web as _fw
    original = _fw.FACTORY_ROOT
    try:
        rules = tmp_path / "01_GLOBAL_STANDARDS" / "rules"
        rules.mkdir(parents=True)
        (rules / "GLOBAL_NAMING_STANDARD.md").write_text("# Naming\ncontent\n", encoding="utf-8")
        (rules / "GLOBAL_PLATFORM_MATRIX.md").write_text("# Platform\ncontent\n", encoding="utf-8")
        (rules / "GLOBAL_OTHER.md").write_text("# Other\ncontent\n", encoding="utf-8")
        _fw.FACTORY_ROOT = tmp_path
        api = _fw.Api()
        api.root = tmp_path  # isolated settings: no ambient last_project anymore
        result = api.run_pipeline("show_standards")
        assert "GLOBAL_NAMING_STANDARD.md" in result["output"]
        assert "GLOBAL_OTHER.md" in result["output"]
    finally:
        _fw.FACTORY_ROOT = original


def test_show_standards_no_rules_dir(tmp_path):
    import factory_web as _fw
    original = _fw.FACTORY_ROOT
    try:
        _fw.FACTORY_ROOT = tmp_path  # no 01_GLOBAL_STANDARDS/rules/
        api = _fw.Api()
        api.root = tmp_path  # isolated settings: no ambient last_project anymore
        result = api.run_pipeline("show_standards")
        assert result["ok"] is False
        assert "not found" in result["output"].lower()
    finally:
        _fw.FACTORY_ROOT = original
