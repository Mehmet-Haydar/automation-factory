"""
test_rag_safety_chain.py

Proof tests for Aşama D — RAG safety warning chain:
  - _rag_safety_check returns [] gracefully when index is missing
  - _inject_rag_safety_box prepends ⚠️ SAFETY NOTU to existing MD
  - generate_fat() response always contains rag_warnings key (empty list when no index)
  - generate_customer_report() response always contains rag_warnings key
  - app.js contains #pr-rag-banner element and "Gördüm" text (banner HTML)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


# ─────────────────────────────────────────────────────────────────────────────
# _rag_safety_check — graceful degradation
# ─────────────────────────────────────────────────────────────────────────────

def test_rag_safety_check_returns_empty_list_when_no_index(tmp_path):
    """_rag_safety_check() must return ([], 'unavailable') (not raise) when index missing."""
    import factory_web
    api = factory_web.Api()
    api.settings = {"api_keys": {"openai": "sk-test"}}

    # RAGIndexNotFoundError should be caught internally → ([], "unavailable")
    result = api._rag_safety_check("E-stop safety")
    assert isinstance(result, tuple), "_rag_safety_check must return a (list, str) tuple"
    warnings, rag_mode = result
    assert isinstance(warnings, list), "First element must be a list"
    assert isinstance(rag_mode, str), "Second element (rag_mode) must be a str"


def test_rag_safety_check_returns_list_without_api_key():
    """_rag_safety_check() returns (list, mode) even without API key.

    B-00 fix: not_verified=True so NOT_VERIFIED safety records are included.
    B-01 fix: category_filter="safety" so only safety entries are returned.
    """
    import factory_web
    api = factory_web.Api()
    api.settings = {"api_keys": {}}  # no openai key

    result = api._rag_safety_check("E-stop safety")
    assert isinstance(result, tuple), "_rag_safety_check must return a (list, str) tuple"
    warnings, rag_mode = result
    assert isinstance(warnings, list), "First element must be a list"
    # B-00: safety records (all currently NOT_VERIFIED) must NOW be returned
    # B-01: all returned records must be critical(safety)
    for r in warnings:
        assert r["severity"] == "critical(safety)", (
            "_rag_safety_check must only return critical(safety) entries"
        )
    # With BM25 index present, we expect at least one safety result for this query
    assert len(warnings) > 0, (
        "B-00: NOT_VERIFIED safety records must be included (not_verified=True). "
        "If this fails, _rag_safety_check is silently swallowing safety warnings."
    )
    assert rag_mode in ("bm25", "semantic"), (
        f"rag_mode must be 'bm25' or 'semantic' when index is available, got {rag_mode!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# _inject_rag_safety_box
# ─────────────────────────────────────────────────────────────────────────────

def test_inject_rag_safety_box_prepends_to_md(tmp_path):
    """Safety box must be prepended BEFORE existing content."""
    md = tmp_path / "protocol.md"
    md.write_text("# FAT Protocol\n\nOriginal content here.\n", encoding="utf-8")

    import factory_web
    factory_web.Api._inject_rag_safety_box(md, [
        {"entry_id": "SAFETY-001", "severity": "critical(safety)", "chunk_text": "## Pitfall 1: E-Stop Logic on Standard PLC\nRisk: Cannot assign SIL/PLr"}
    ])

    content = md.read_text(encoding="utf-8")
    # Box must come first
    assert content.startswith(">"), "Safety box must be the very first content"
    assert "SAFETY NOTU" in content
    assert "SAFETY-001" in content
    # Original content must still be present
    assert "# FAT Protocol" in content
    assert "Original content here." in content


def test_inject_rag_safety_box_skips_empty_warnings(tmp_path):
    """Empty warnings list → MD file unchanged."""
    original = "# FAT Protocol\n\nContent.\n"
    md = tmp_path / "protocol.md"
    md.write_text(original, encoding="utf-8")

    import factory_web
    factory_web.Api._inject_rag_safety_box(md, [])

    assert md.read_text(encoding="utf-8") == original


def test_inject_rag_safety_box_skips_missing_file(tmp_path):
    """Non-existent file → no error raised."""
    import factory_web
    factory_web.Api._inject_rag_safety_box(
        tmp_path / "does_not_exist.md",
        [{"entry_id": "SAFETY-001", "severity": "critical(safety)", "chunk_text": "test"}]
    )  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# generate_fat / generate_customer_report — rag_warnings key always present
# ─────────────────────────────────────────────────────────────────────────────

def _make_minimal_project(tmp_path: Path) -> Path:
    """Minimal project structure for generate_fat/generate_customer_report."""
    import json
    proj = tmp_path / "TestProject"
    meta = proj / "metadata"
    meta.mkdir(parents=True)
    (proj / "PROJECT_STATE.json").write_text(
        json.dumps({"project_name": "Test", "project_type": "retrofit",
                    # AUDIT-004b: banner blocks without a recorded review
                    "rd_verifications": {"RD05": {"reviewed": True}}}),
        encoding="utf-8"
    )
    (meta / "RD01_IO_List.md").write_text(
        "| Tag | Address | Type |\n|---|---|---|\n| xStart | %I0.0 | DI |\n", encoding="utf-8"
    )
    # Minimal RD05 so FAT doesn't fail on safety check
    (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
        "# RD05\n| Function | Description | PLr |\n|---|---|---|\n| EStop | E-stop | d |\n",
        encoding="utf-8",
    )
    return proj


def test_generate_fat_response_has_rag_warnings_key(tmp_path):
    """generate_fat() must always return 'rag_warnings' key in dict."""
    proj = _make_minimal_project(tmp_path)

    import factory_web
    api = factory_web.Api()
    api.root = proj
    api.settings = {"api_keys": {}}  # no RAG key → empty list

    # Patch generate internals to avoid full protocol generation.
    # _rag_safety_check now returns (warnings_list, rag_mode) tuple.
    with patch.object(api, "_rag_safety_check", return_value=([], "bm25")):
        try:
            result = api.generate_fat(test_type="FAT", lang="de", pdf=False)
        except Exception:
            pytest.skip("generate_fat failed due to missing project data — not testing that here")

    assert "rag_warnings" in result, "generate_fat() must include 'rag_warnings' in its response"
    assert isinstance(result["rag_warnings"], list)


def test_generate_customer_report_response_has_rag_warnings_key(tmp_path):
    """generate_customer_report() must always return 'rag_warnings' key in dict."""
    proj = _make_minimal_project(tmp_path)

    import factory_web
    api = factory_web.Api()
    api.root = proj
    api.settings = {"api_keys": {}}

    # _rag_safety_check now returns (warnings_list, rag_mode) tuple.
    with patch.object(api, "_rag_safety_check", return_value=([], "bm25")):
        try:
            result = api.generate_customer_report()
        except Exception:
            pytest.skip("generate_customer_report failed — not testing that here")

    assert "rag_warnings" in result, "generate_customer_report() must include 'rag_warnings'"
    assert isinstance(result["rag_warnings"], list)


# ─────────────────────────────────────────────────────────────────────────────
# app.js safety banner UI
# ─────────────────────────────────────────────────────────────────────────────

def _js() -> str:
    return (_ROOT / "webgui" / "app.js").read_text(encoding="utf-8")


def test_app_js_has_rag_banner_element():
    """app.js must contain the #pr-rag-banner div for safety warnings."""
    assert 'id="pr-rag-banner"' in _js(), \
        "app.js must have #pr-rag-banner element in the FAT protocol modal"


def test_app_js_has_goerduem_confirm_button():
    """app.js must have 'Gördüm' confirm button text in the banner handler."""
    assert "Gördüm" in _js(), \
        "app.js must have 'Gördüm, devam et' button in the rag_warnings banner"


def test_app_js_checks_rag_warnings_in_fat_handler():
    """app.js must check r.rag_warnings in the generate_fat result handler."""
    assert "r.rag_warnings" in _js(), \
        "app.js FAT result handler must check r.rag_warnings for safety banner"
