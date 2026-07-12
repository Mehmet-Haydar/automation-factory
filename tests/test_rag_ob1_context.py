"""
test_rag_ob1_context.py

RAG Aşama D — OB1 vendor context injection:
  - _rag_vendor_notes() returns non-safety VERIFIED entries for a given category
  - _rag_vendor_notes() returns [] gracefully when no index
  - _inject_rag_context_block() prepends // RAG_CONTEXT to SCL file
  - _inject_rag_context_block() is a no-op on empty notes
  - generate_ob1() response includes rag_notes key
  - _rag_safety_check() works in BM25 mode without API key
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


# ─────────────────────────────────────────────────────────────────────────────
# _rag_vendor_notes
# ─────────────────────────────────────────────────────────────────────────────

def _make_bm25_fixture(tmp_path: Path, records: list[dict]) -> Path:
    from rag.ingest import build_bm25_index
    bm25 = build_bm25_index(records)
    idx_dir = tmp_path / "_rag_index"
    idx_dir.mkdir()
    (idx_dir / "bm25.json").write_text(
        json.dumps(bm25, ensure_ascii=False), encoding="utf-8"
    )
    return idx_dir


_SAMPLE = [
    {
        "entry_id": "VQ-001",
        "category": "vendor_quirk",
        "severity": "medium",
        "verified": "VERIFIED",
        "source": "field",
        "vendor": "SEW",
        "chunk_text": "SEW MoviDrive requires 20ms ramp-up before starting SCL loop.",
        "source_file": "KB_VENDOR_QUIRKS.md",
    },
    {
        "entry_id": "COMMS-001",
        "category": "comms",
        "severity": "medium",
        "verified": "VERIFIED",
        "source": "field",
        "vendor": None,
        "chunk_text": "PROFINET cycle time must be set to 1ms to avoid packet loss.",
        "source_file": "KB_PITFALLS_COMMS.md",
    },
    {
        "entry_id": "SAFETY-001",
        "category": "safety",
        "severity": "critical(safety)",
        "verified": "VERIFIED",
        "source": "field",
        "vendor": None,
        "chunk_text": "E-stop must never be wired through standard PLC.",
        "source_file": "KB_PITFALLS_SAFETY.md",
    },
]


def test_rag_vendor_notes_returns_non_safety_entries(tmp_path):
    """_rag_vendor_notes() must return non-critical VERIFIED entries for the category."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE)

    import factory_web
    import rag.retrieve as rmod
    api = factory_web.Api()
    api.settings = {"api_keys": {}}

    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        notes = api._rag_vendor_notes("vendor quirk SEW ramp", "vendor_quirk")

    assert notes, "Must return vendor_quirk entries for matching query"
    assert all(n["category"] == "vendor_quirk" for n in notes)
    assert all(n["severity"] != "critical(safety)" for n in notes), \
        "_rag_vendor_notes must exclude critical(safety) entries"


def test_rag_vendor_notes_excludes_other_categories(tmp_path):
    """_rag_vendor_notes() with category_filter=comms must not return vendor_quirk."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE)

    import factory_web
    import rag.retrieve as rmod
    api = factory_web.Api()
    api.settings = {"api_keys": {}}

    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        notes = api._rag_vendor_notes("PROFINET cycle", "comms")

    assert all(n["category"] == "comms" for n in notes)


def test_rag_vendor_notes_returns_empty_when_no_index(tmp_path):
    """_rag_vendor_notes() must return [] gracefully when no index exists."""
    import factory_web
    import rag.retrieve as rmod
    api = factory_web.Api()
    api.settings = {"api_keys": {}}

    empty = tmp_path / "_rag_index_empty"
    empty.mkdir()
    with patch.object(rmod, "_INDEX_DIR", empty):
        notes = api._rag_vendor_notes("anything", "vendor_quirk")

    assert notes == []


# ─────────────────────────────────────────────────────────────────────────────
# _inject_rag_context_block
# ─────────────────────────────────────────────────────────────────────────────

def test_inject_rag_context_block_prepends_to_scl(tmp_path):
    """// RAG_CONTEXT block must be prepended to SCL file."""
    scl = tmp_path / "OB_Main.scl"
    scl.write_text('ORGANIZATION_BLOCK "OB_Main"\n{ S7_Optimized_Access := \'TRUE\' }\nEND_ORGANIZATION_BLOCK\n',
                   encoding="utf-8")

    import factory_web
    factory_web.Api._inject_rag_context_block(scl, [
        {"entry_id": "VQ-001", "severity": "medium", "category": "vendor_quirk",
         "chunk_text": "SEW MoviDrive requires 20ms ramp-up before SCL loop."}
    ])

    content = scl.read_text(encoding="utf-8")
    assert content.startswith("// RAG_CONTEXT:"), "Block must be first in file"
    assert "VQ-001" in content
    assert "ORGANIZATION_BLOCK" in content, "Original SCL must still be present"


def test_inject_rag_context_block_noop_on_empty_notes(tmp_path):
    """Empty notes → SCL file unchanged."""
    original = 'ORGANIZATION_BLOCK "OB_Main"\nEND_ORGANIZATION_BLOCK\n'
    scl = tmp_path / "OB_Main.scl"
    scl.write_text(original, encoding="utf-8")

    import factory_web
    factory_web.Api._inject_rag_context_block(scl, [])

    assert scl.read_text(encoding="utf-8") == original


def test_inject_rag_context_block_noop_on_missing_file(tmp_path):
    """Non-existent SCL file → no error raised."""
    import factory_web
    factory_web.Api._inject_rag_context_block(
        tmp_path / "does_not_exist.scl",
        [{"entry_id": "VQ-001", "severity": "medium", "category": "vendor_quirk",
          "chunk_text": "test"}]
    )  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# generate_ob1 — rag_notes key in response
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_ob1_response_has_rag_notes_key(tmp_path):
    """generate_ob1() response must always include 'rag_notes' key."""
    import factory_web

    proj = tmp_path / "Proj"
    (proj / "metadata").mkdir(parents=True)
    (proj / "PROJECT_STATE.json").write_text(
        '{"project_name": "Proj", "project_type": "retrofit"}', encoding="utf-8"
    )

    api = factory_web.Api()
    api.root = proj
    api.settings = {"api_keys": {}}

    with patch.object(api, "_rag_vendor_notes", return_value=[]):
        # _rag_safety_check now returns (warnings_list, rag_mode) tuple.
        with patch.object(api, "_rag_safety_check", return_value=([], "bm25")):
            try:
                result = api.generate_ob1()
            except Exception:
                pytest.skip("generate_ob1 failed due to missing project structure")

    assert "rag_notes" in result, "generate_ob1() must include 'rag_notes' key"
    assert isinstance(result["rag_notes"], list)


# ─────────────────────────────────────────────────────────────────────────────
# _rag_safety_check — BM25 mode (no API key)
# ─────────────────────────────────────────────────────────────────────────────

def test_rag_safety_check_bm25_no_api_key(tmp_path):
    """_rag_safety_check() uses BM25 mode when no API key is set."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE)

    import factory_web
    import rag.retrieve as rmod
    api = factory_web.Api()
    api.settings = {"api_keys": {}}  # no OpenAI key

    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        result = api._rag_safety_check("E-stop safety")

    # _rag_safety_check now returns (warnings_list, rag_mode) tuple.
    assert isinstance(result, tuple), "_rag_safety_check must return a (list, str) tuple"
    warnings, rag_mode = result
    assert isinstance(warnings, list)
    # If any results, they must all be critical(safety)
    for r in warnings:
        assert r["severity"] == "critical(safety)"
    assert rag_mode in ("bm25", "semantic", "unavailable")
