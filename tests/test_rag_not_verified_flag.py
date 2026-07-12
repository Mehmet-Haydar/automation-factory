"""
test_rag_not_verified_flag.py

Verify retrieve() filtering behaviour for NOT_VERIFIED records:
 - Default call: NOT_VERIFIED records are excluded from results.
 - not_verified=True call: NOT_VERIFIED records ARE included and
   carry not_verified=True in the returned dict.

This enforces the "human in the loop" contract — unverified KB entries
must not silently appear in production outputs.
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

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def _make_mixed_index(tmp_path: Path) -> Path:
    """Index with one VERIFIED and one NOT_VERIFIED record."""
    index_dir = tmp_path / "_rag_index"
    index_dir.mkdir()

    records = [
        {
            "entry_id": "RETRO-001",
            "category": "retrofit_io",
            "severity": "medium",
            "verified": "VERIFIED",
            "source": "field_experience_anon",
            "vendor": None,
            "chunk_text": "## Pitfall 1: Verified retrofit issue.",
            "source_file": "06_KNOWLEDGE_BASE/KB_PITFALLS_RETROFIT_IO.md",
        },
        {
            "entry_id": "RETRO-002",
            "category": "retrofit_io",
            "severity": "high",
            "verified": "NOT_VERIFIED",
            "source": "field_experience_anon",
            "vendor": None,
            "chunk_text": "## Pitfall 2: Unverified retrofit issue.",
            "source_file": "06_KNOWLEDGE_BASE/KB_PITFALLS_RETROFIT_IO.md",
        },
    ]
    (index_dir / "metadata.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Equal scores so both would appear if not filtered
    embeddings = np.array([[1.0, 0.0], [1.0, 0.0]], dtype="float32")
    np.save(str(index_dir / "embeddings.npy"), embeddings)
    return index_dir


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_not_verified_excluded_by_default(tmp_path):
    """Default retrieve() must exclude NOT_VERIFIED records."""
    from rag import retrieve as rag_retrieve

    index_dir = _make_mixed_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve("retrofit", top_k=10, api_key="fake-key")

    ids = [r["entry_id"] for r in results]
    assert "RETRO-002" not in ids, (
        "NOT_VERIFIED record RETRO-002 must not appear in default results"
    )
    assert "RETRO-001" in ids, "VERIFIED record RETRO-001 must appear"


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_not_verified_included_when_flag_set(tmp_path):
    """retrieve(not_verified=True) must include NOT_VERIFIED records."""
    from rag import retrieve as rag_retrieve

    index_dir = _make_mixed_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve(
                "retrofit", top_k=10, not_verified=True, api_key="fake-key"
            )

    ids = [r["entry_id"] for r in results]
    assert "RETRO-002" in ids, (
        "NOT_VERIFIED record RETRO-002 must appear when not_verified=True"
    )


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_not_verified_record_carries_flag(tmp_path):
    """NOT_VERIFIED records returned with not_verified=True must carry not_verified=True."""
    from rag import retrieve as rag_retrieve

    index_dir = _make_mixed_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve(
                "retrofit", top_k=10, not_verified=True, api_key="fake-key"
            )

    nv_results = [r for r in results if r["entry_id"] == "RETRO-002"]
    assert nv_results, "RETRO-002 should be in results"
    assert nv_results[0]["not_verified"] is True, (
        "NOT_VERIFIED record must have not_verified=True in output"
    )


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_verified_record_carries_not_verified_false(tmp_path):
    """VERIFIED records must carry not_verified=False."""
    from rag import retrieve as rag_retrieve

    index_dir = _make_mixed_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve("retrofit", top_k=10, api_key="fake-key")

    verified_results = [r for r in results if r["entry_id"] == "RETRO-001"]
    assert verified_results, "RETRO-001 should be in results"
    assert verified_results[0]["not_verified"] is False, (
        "VERIFIED record must have not_verified=False in output"
    )
