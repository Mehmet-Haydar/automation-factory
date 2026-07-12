"""W2 — SCL dizin sözleşmesi: extract -> _output/scl/; metadata taranır."""

import importlib
from pathlib import Path

scl_ext = importlib.import_module("scl_extractor")
extract_all_from_project = scl_ext.extract_all_from_project
write_blocks = scl_ext.write_blocks

SCL_BLOCK = """\
FUNCTION_BLOCK FB_ConveyorDrive
VAR_INPUT
    Enable : BOOL;
END_VAR
VAR_OUTPUT
    Running : BOOL;
END_VAR
BEGIN
    Running := Enable;
END_FUNCTION_BLOCK
"""

MD_CONTENT = f"# RD06\n\n```scl\n{SCL_BLOCK}```\n"


def test_extract_from_output_dir(tmp_path):
    (tmp_path / "_output").mkdir()
    (tmp_path / "_output" / "RD06_output.md").write_text(MD_CONTENT, encoding="utf-8")
    results = extract_all_from_project(tmp_path)
    assert len(results) == 1
    assert results[0].extracted_count == 1


def test_extract_from_metadata_dir(tmp_path):
    (tmp_path / "metadata").mkdir()
    (tmp_path / "metadata" / "RD06_Motion.md").write_text(MD_CONTENT, encoding="utf-8")
    results = extract_all_from_project(tmp_path)
    assert len(results) == 1
    assert results[0].extracted_count == 1


def test_write_goes_to_output_scl(tmp_path):
    (tmp_path / "metadata").mkdir()
    (tmp_path / "metadata" / "RD06_Motion.md").write_text(MD_CONTENT, encoding="utf-8")
    results = extract_all_from_project(tmp_path)
    out_dir = tmp_path / "_output" / "scl"
    written = write_blocks(results, out_dir, overwrite=False)
    assert out_dir.exists()
    assert len(written) == 1
    assert written[0].output_path.parent == out_dir


def test_empty_project_returns_empty_list(tmp_path):
    results = extract_all_from_project(tmp_path)
    assert results == []


def test_no_duplicate_when_same_file_in_both_dirs(tmp_path):
    """Even if somehow the same content appears in both dirs, dedup by path."""
    (tmp_path / "_output").mkdir()
    (tmp_path / "metadata").mkdir()
    (tmp_path / "_output" / "RD06.md").write_text(MD_CONTENT, encoding="utf-8")
    (tmp_path / "metadata" / "RD06.md").write_text(MD_CONTENT, encoding="utf-8")
    results = extract_all_from_project(tmp_path)
    # Both files are different paths — both scanned (2 results expected)
    assert len(results) == 2
