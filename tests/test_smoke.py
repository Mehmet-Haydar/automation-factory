"""Import sanity — confirms the path setup in conftest works."""


def test_workbench_imports():
    from workbench.core import io_list_io  # noqa: F401
    assert hasattr(io_list_io, "write_md")


def test_scripts_import():
    import project_analyzer  # noqa: F401
    assert hasattr(project_analyzer, "RD_INPUT_NEEDS") or hasattr(
        project_analyzer, "analyze_project"
    )


def test_example_project_fixture(example_project):
    assert (example_project / "metadata").is_dir()
