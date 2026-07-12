"""
test_rag_critical_safety_banner.py

Verify that retrieve() sets rag_warning=True for every record with
severity "critical(safety)", regardless of verified status.

The safety banner (rag_warning flag) is the first line of the production
safety chain (retrieve → factory_web → app.js ⚠️ banner).
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


def _make_safety_index(tmp_path: Path) -> Path:
    """Index with one critical(safety) entry and one normal entry."""
    index_dir = tmp_path / "_rag_index"
    index_dir.mkdir()

    records = [
        {
            "entry_id": "SAFETY-001",
            "category": "safety",
            "severity": "critical(safety)",
            "verified": "VERIFIED",
            "source": "field_experience_anon",
            "vendor": None,
            "chunk_text": (
                "## Pitfall 1: E-Stop Logic on Standard PLC\n"
                "**Symptom:** Old machine has no F-CPU.\n"
                "**Solution:** Add F-CPU. TÜV review required."
            ),
            "source_file": "06_KNOWLEDGE_BASE/KB_PITFALLS_SAFETY.md",
        },
        {
            "entry_id": "COMMS-001",
            "category": "comms",
            "severity": "medium",
            "verified": "VERIFIED",
            "source": "field_experience_anon",
            "vendor": None,
            "chunk_text": (
                "## Pitfall 1: PROFINET Cycle Time Too Short\n"
                "**Symptom:** PROFINET IO cycle 1ms.\n"
                "**Solution:** Standard switch minimum 4ms."
            ),
            "source_file": "06_KNOWLEDGE_BASE/KB_PITFALLS_COMMS.md",
        },
    ]
    (index_dir / "metadata.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Both records get equal similarity scores → top-k returns both
    embeddings = np.array([[1.0, 0.0], [1.0, 0.0]], dtype="float32")
    np.save(str(index_dir / "embeddings.npy"), embeddings)
    return index_dir


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_critical_safety_record_has_rag_warning(tmp_path):
    """critical(safety) entry must carry rag_warning=True."""
    from rag import retrieve as rag_retrieve

    index_dir = _make_safety_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve("e-stop safety", top_k=5, api_key="fake-key")

    safety_results = [r for r in results if r["entry_id"] == "SAFETY-001"]
    assert safety_results, "SAFETY-001 should be in results"
    assert safety_results[0]["rag_warning"] is True, (
        f"critical(safety) entry must have rag_warning=True, got: {safety_results[0]}"
    )


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_non_critical_record_has_no_rag_warning(tmp_path):
    """Non-safety entries must NOT have rag_warning=True."""
    from rag import retrieve as rag_retrieve

    index_dir = _make_safety_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve("profinet timeout", top_k=5, api_key="fake-key")

    comms_results = [r for r in results if r["entry_id"] == "COMMS-001"]
    assert comms_results, "COMMS-001 should be in results"
    assert comms_results[0]["rag_warning"] is False, (
        f"Non-critical entry must have rag_warning=False, got: {comms_results[0]}"
    )


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_rag_warning_field_always_present(tmp_path):
    """Every returned record must carry the rag_warning key (bool)."""
    from rag import retrieve as rag_retrieve

    index_dir = _make_safety_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve("query", top_k=10, api_key="fake-key")

    for r in results:
        assert "rag_warning" in r, f"Missing rag_warning key in record {r.get('entry_id')}"
        assert isinstance(r["rag_warning"], bool), (
            f"rag_warning must be bool, got {type(r['rag_warning'])}"
        )
