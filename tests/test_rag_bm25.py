"""
test_rag_bm25.py

BM25 offline keyword search mode:
  - retrieve() uses bm25.json when embeddings.npy is absent
  - BM25 score > 0 for a term that appears in at least one record
  - NOT_VERIFIED filter respected in BM25 mode
  - category_filter respected in BM25 mode
  - RAGIndexNotFoundError when neither index file exists
  - rag_warning=True for critical(safety) records in BM25 results
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _make_bm25_fixture(tmp_path: Path, records: list[dict]) -> Path:
    """Build a minimal bm25.json from records and return the index dir."""
    from rag.ingest import build_bm25_index
    bm25 = build_bm25_index(records)
    idx_dir = tmp_path / "_rag_index"
    idx_dir.mkdir()
    (idx_dir / "bm25.json").write_text(
        json.dumps(bm25, ensure_ascii=False), encoding="utf-8"
    )
    return idx_dir


_SAMPLE_RECORDS = [
    {
        "entry_id": "COMMS-001",
        "category": "comms",
        "severity": "medium",
        "verified": "VERIFIED",
        "source": "field",
        "vendor": None,
        "chunk_text": "PROFINET cycle time must be set correctly to avoid packet loss.",
        "source_file": "KB_PITFALLS_COMMS.md",
    },
    {
        "entry_id": "SAFETY-001",
        "category": "safety",
        "severity": "critical(safety)",
        "verified": "VERIFIED",
        "source": "field",
        "vendor": None,
        "chunk_text": "E-stop must never be wired through standard PLC. Use safety relay.",
        "source_file": "KB_PITFALLS_SAFETY.md",
    },
    {
        "entry_id": "HMI-NV-001",
        "category": "hmi",
        "severity": "medium",
        "verified": "NOT_VERIFIED",
        "source": "field",
        "vendor": None,
        "chunk_text": "HMI screen flicker caused by refresh rate mismatch.",
        "source_file": "KB_PITFALLS_HMI.md",
    },
]


def test_bm25_returns_results_for_matching_term(tmp_path):
    """BM25 mode returns results for a term present in the corpus."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE_RECORDS)

    import rag.retrieve as rmod
    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        # embeddings.npy does NOT exist → BM25 mode
        results = rmod.retrieve("PROFINET", top_k=5, not_verified=True)

    assert results, "Must return at least one result for 'PROFINET'"
    assert results[0]["entry_id"] == "COMMS-001"
    assert results[0]["score"] > 0


def test_bm25_score_zero_for_no_match(tmp_path):
    """BM25 returns empty list when no record contains the query terms."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE_RECORDS)

    import rag.retrieve as rmod
    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        results = rmod.retrieve("xyzzy_nonexistent_token_abc", top_k=5, not_verified=True)

    assert results == []


def test_bm25_not_verified_filter(tmp_path):
    """not_verified=False must exclude NOT_VERIFIED records from BM25 results."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE_RECORDS)

    import rag.retrieve as rmod
    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        results = rmod.retrieve("HMI flicker", top_k=5, not_verified=False)

    ids = [r["entry_id"] for r in results]
    assert "HMI-NV-001" not in ids, "NOT_VERIFIED record must be excluded by default"


def test_bm25_not_verified_included_when_flag_set(tmp_path):
    """not_verified=True includes NOT_VERIFIED records with not_verified=True annotation."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE_RECORDS)

    import rag.retrieve as rmod
    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        results = rmod.retrieve("HMI screen refresh", top_k=5, not_verified=True)

    ids = [r["entry_id"] for r in results]
    assert "HMI-NV-001" in ids
    nv_result = next(r for r in results if r["entry_id"] == "HMI-NV-001")
    assert nv_result["not_verified"] is True


def test_bm25_category_filter(tmp_path):
    """category_filter restricts BM25 results to matching category."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE_RECORDS)

    import rag.retrieve as rmod
    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        results = rmod.retrieve("safety stop relay", top_k=5,
                                not_verified=True, category_filter="safety")

    assert all(r["category"] == "safety" for r in results)


def test_bm25_rag_warning_on_critical_safety(tmp_path):
    """critical(safety) records must have rag_warning=True in BM25 results."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE_RECORDS)

    import rag.retrieve as rmod
    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        results = rmod.retrieve("E-stop safety", top_k=5, not_verified=True)

    safety = next((r for r in results if r["entry_id"] == "SAFETY-001"), None)
    assert safety is not None, "SAFETY-001 must be in results"
    assert safety["rag_warning"] is True


def test_bm25_top_k_respected(tmp_path):
    """BM25 must not return more than top_k results."""
    idx_dir = _make_bm25_fixture(tmp_path, _SAMPLE_RECORDS)

    import rag.retrieve as rmod
    with patch.object(rmod, "_INDEX_DIR", idx_dir):
        results = rmod.retrieve("stop relay cycle time", top_k=1, not_verified=True)

    assert len(results) <= 1


def test_ragindex_not_found_when_no_index(tmp_path):
    """RAGIndexNotFoundError raised when neither embeddings.npy nor bm25.json exist."""
    from rag import RAGIndexNotFoundError
    import rag.retrieve as rmod

    empty_dir = tmp_path / "_rag_index_empty"
    empty_dir.mkdir()

    with patch.object(rmod, "_INDEX_DIR", empty_dir):
        with pytest.raises(RAGIndexNotFoundError):
            rmod.retrieve("anything", not_verified=True)
