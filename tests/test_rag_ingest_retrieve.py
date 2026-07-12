"""
test_rag_ingest_retrieve.py

Verify the ingest → retrieve round-trip without hitting the OpenAI API.

Strategy:
 1. parse_kb_file() is pure Python — no API needed; test it directly.
 2. For retrieve round-trip, build a minimal fake index (JSON + npy) and
    mock the embedding call so the top-k result is deterministic.
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


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_KB_FIXTURE = """\
---
title: KB Test
version: 1.0.0
status: ACTIVE
---

# KB_TEST.md — Test File

> Test fixture.

---

## metadata

```yaml
rag_category: comms
rag_severity_default: medium
rag_verified_default: VERIFIED
rag_source_pattern: field_experience_anon
rag_entry_id_prefix: TEST
rag_entry_split_heading_level: 2
rag_entry_split_prefix: "Pitfall"
```

---

## Pitfall 1: Widget Timeout

**Symptom:** Widget times out after 3 seconds.

**Solution:** Increase timeout to 10 seconds.

---

## Pitfall 2: Widget Overflow

**Symptom:** Widget buffer overflows on large payloads.

**Solution:** Chunk payload into 1 kB segments.
"""


def _make_kb_file(tmp_path: Path) -> Path:
    kb = tmp_path / "KB_TEST.md"
    kb.write_text(_KB_FIXTURE, encoding="utf-8")
    return kb


def _make_fake_index(tmp_path: Path) -> Path:
    """Create a minimal _rag_index/ with 2 records and fake embeddings."""
    index_dir = tmp_path / "_rag_index"
    index_dir.mkdir()

    records = [
        {
            "entry_id": "TEST-001",
            "category": "comms",
            "severity": "medium",
            "verified": "VERIFIED",
            "source": "field_experience_anon",
            "vendor": None,
            "chunk_text": "## Pitfall 1: Widget Timeout\n**Symptom:** Widget times out.\n**Solution:** Increase timeout.",
            "source_file": "06_KNOWLEDGE_BASE/KB_TEST.md",
        },
        {
            "entry_id": "TEST-002",
            "category": "comms",
            "severity": "medium",
            "verified": "VERIFIED",
            "source": "field_experience_anon",
            "vendor": None,
            "chunk_text": "## Pitfall 2: Widget Overflow\n**Symptom:** Buffer overflows.\n**Solution:** Chunk payload.",
            "source_file": "06_KNOWLEDGE_BASE/KB_TEST.md",
        },
    ]
    (index_dir / "metadata.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Fake embeddings: record 0 matches query (dot product = 1), record 1 doesn't
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype="float32")
    np.save(str(index_dir / "embeddings.npy"), embeddings)
    return index_dir


# ─────────────────────────────────────────────────────────────────────────────
# parse_kb_file tests (pure, no API)
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_kb_file_returns_two_entries(tmp_path):
    kb = _make_kb_file(tmp_path)
    from rag.ingest import parse_kb_file
    with patch("rag.ingest._REPO_ROOT", tmp_path):
        records = parse_kb_file(kb)
    assert len(records) == 2, f"Expected 2 entries, got {len(records)}"


def test_parse_kb_file_entry_ids(tmp_path):
    kb = _make_kb_file(tmp_path)
    from rag.ingest import parse_kb_file
    with patch("rag.ingest._REPO_ROOT", tmp_path):
        records = parse_kb_file(kb)
    ids = [r["entry_id"] for r in records]
    assert ids == ["TEST-001", "TEST-002"], f"Unexpected IDs: {ids}"


def test_parse_kb_file_category(tmp_path):
    kb = _make_kb_file(tmp_path)
    from rag.ingest import parse_kb_file
    with patch("rag.ingest._REPO_ROOT", tmp_path):
        records = parse_kb_file(kb)
    assert all(r["category"] == "comms" for r in records)


def test_parse_kb_file_verified_default(tmp_path):
    kb = _make_kb_file(tmp_path)
    from rag.ingest import parse_kb_file
    with patch("rag.ingest._REPO_ROOT", tmp_path):
        records = parse_kb_file(kb)
    assert all(r["verified"] == "VERIFIED" for r in records)


def test_parse_kb_file_chunk_text_contains_symptom(tmp_path):
    kb = _make_kb_file(tmp_path)
    from rag.ingest import parse_kb_file
    with patch("rag.ingest._REPO_ROOT", tmp_path):
        records = parse_kb_file(kb)
    assert all("Symptom" in r["chunk_text"] for r in records)


# ─────────────────────────────────────────────────────────────────────────────
# retrieve round-trip tests (mocked embedding)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_retrieve_returns_best_match(tmp_path):
    """Top result must be TEST-001 when query embedding is [1, 0]."""
    from rag import retrieve as rag_retrieve

    index_dir = _make_fake_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve("widget timeout", top_k=1, api_key="fake-key")

    assert len(results) == 1
    assert results[0]["entry_id"] == "TEST-001"


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_retrieve_score_between_zero_and_one(tmp_path):
    from rag import retrieve as rag_retrieve

    index_dir = _make_fake_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve("widget", top_k=2, api_key="fake-key")

    for r in results:
        assert 0.0 <= r["score"] <= 1.0, f"Score out of range: {r['score']}"


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
def test_retrieve_chunk_text_present(tmp_path):
    from rag import retrieve as rag_retrieve

    index_dir = _make_fake_index(tmp_path)
    query_vec = np.array([1.0, 0.0], dtype="float32")

    with patch("rag.retrieve._INDEX_DIR", index_dir):
        with patch("rag.retrieve._embed_query", return_value=query_vec):
            results = rag_retrieve.retrieve("widget", top_k=1, api_key="fake-key")

    assert "chunk_text" in results[0]
    assert len(results[0]["chunk_text"]) > 0


# ---------------------------------------------------------------------------
# RAG index missing error guard — taşındı: test_rag_index_missing_error.py
# ---------------------------------------------------------------------------

class TestRagIndexMissing:
    """RAGIndexNotFoundError fresh-clone guard: retrieve() boş liste değil exception fırlatmalı."""

    def test_missing_index_raises_not_empty_list(self, tmp_path):
        from rag import RAGIndexNotFoundError
        from rag import retrieve as rag_retrieve
        fake_index = tmp_path / "_rag_index_does_not_exist"
        with patch("rag.retrieve._INDEX_DIR", fake_index):
            with pytest.raises(RAGIndexNotFoundError) as exc_info:
                rag_retrieve.retrieve("PROFINET cycle time", api_key="fake-key")
        assert "ingest" in str(exc_info.value).lower()

    def test_missing_index_error_message_mentions_ingest(self, tmp_path):
        from rag import RAGIndexNotFoundError
        from rag import retrieve as rag_retrieve
        fake_index = tmp_path / "no_index_here"
        with patch("rag.retrieve._INDEX_DIR", fake_index):
            try:
                rag_retrieve.retrieve("test query", api_key="fake-key")
            except RAGIndexNotFoundError as exc:
                assert "ingest" in str(exc).lower(), (
                    f"Error message must mention 'ingest.py'. Got: {exc}"
                )
            except Exception as exc:
                pytest.fail(f"Expected RAGIndexNotFoundError but got {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# RAG mode metadata (BM25 fallback / semantic) — taşındı: test_rag_mode_metadata.py
# ---------------------------------------------------------------------------

import os as _os  # noqa: E402

_RAG_RECORDS = [
    {
        "entry_id": "COMMS-001", "category": "comms", "severity": "medium",
        "verified": "VERIFIED", "source": "field", "vendor": None,
        "chunk_text": "PROFINET cycle time must be configured correctly.",
        "source_file": "KB_PITFALLS_COMMS.md",
    },
    {
        "entry_id": "SAFETY-001", "category": "safety", "severity": "critical(safety)",
        "verified": "VERIFIED", "source": "field", "vendor": None,
        "chunk_text": "E-stop must never route through standard PLC output.",
        "source_file": "KB_PITFALLS_SAFETY.md",
    },
]


def _make_bm25_dir(tmp_path: Path, records: list) -> Path:
    from rag.ingest import build_bm25_index
    bm25 = build_bm25_index(records)
    idx_dir = tmp_path / "_rag_index"
    idx_dir.mkdir()
    (idx_dir / "bm25.json").write_text(
        json.dumps(bm25, ensure_ascii=False), encoding="utf-8"
    )
    return idx_dir


class TestBM25NoEmbeddingsMode:
    """embeddings.npy yokken BM25 fallback metadata."""

    def test_rag_mode_is_bm25(self, tmp_path):
        idx_dir = _make_bm25_dir(tmp_path, _RAG_RECORDS)
        import rag.retrieve as rmod
        with patch.object(rmod, "_INDEX_DIR", idx_dir):
            results = rmod.retrieve("PROFINET", top_k=5, not_verified=True)
        assert results, "En az bir sonuç bekleniyor"
        for r in results:
            assert r["_rag_mode"] == "bm25", f"_rag_mode 'bm25' olmalı, {r['_rag_mode']!r} geldi"

    def test_fallback_reason_is_no_embeddings(self, tmp_path):
        idx_dir = _make_bm25_dir(tmp_path, _RAG_RECORDS)
        import rag.retrieve as rmod
        with patch.object(rmod, "_INDEX_DIR", idx_dir):
            results = rmod.retrieve("PROFINET", top_k=5, not_verified=True)
        for r in results:
            assert r.get("_rag_fallback_reason") == "no_embeddings", (
                f"_rag_fallback_reason 'no_embeddings' olmalı, {r.get('_rag_fallback_reason')!r} geldi"
            )

    def test_rag_mode_field_present(self, tmp_path):
        idx_dir = _make_bm25_dir(tmp_path, _RAG_RECORDS)
        import rag.retrieve as rmod
        with patch.object(rmod, "_INDEX_DIR", idx_dir):
            results = rmod.retrieve("PROFINET", top_k=5, not_verified=True)
        assert all("_rag_mode" in r for r in results), (
            "Fix eksik: '_rag_mode' alanı retrieve() sonuçlarında bulunmuyor"
        )


class TestBM25NoApiKeyMode:
    """embeddings.npy var, API key yok → BM25 fallback, reason=no_api_key."""

    def _make_both_indexes(self, tmp_path: Path) -> Path:
        idx_dir = _make_bm25_dir(tmp_path, _RAG_RECORDS)
        try:
            arr = np.zeros((len(_RAG_RECORDS), 4), dtype="float32")
            np.save(str(idx_dir / "embeddings.npy"), arr)
        except (ImportError, NameError):
            (idx_dir / "embeddings.npy").write_bytes(b"\x93NUMPY")
        return idx_dir

    def test_rag_mode_is_bm25_when_no_key(self, tmp_path):
        idx_dir = self._make_both_indexes(tmp_path)
        import rag.retrieve as rmod
        env_copy = {k: v for k, v in _os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.object(rmod, "_INDEX_DIR", idx_dir):
            with patch.dict(_os.environ, env_copy, clear=True):
                results = rmod.retrieve("PROFINET", top_k=5, not_verified=True, api_key=None)
        assert results, "BM25 fallback en az bir sonuç döndürmeli"
        for r in results:
            assert r["_rag_mode"] == "bm25"

    def test_fallback_reason_is_no_api_key(self, tmp_path):
        idx_dir = self._make_both_indexes(tmp_path)
        import rag.retrieve as rmod
        env_copy = {k: v for k, v in _os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.object(rmod, "_INDEX_DIR", idx_dir):
            with patch.dict(_os.environ, env_copy, clear=True):
                results = rmod.retrieve("PROFINET", top_k=5, not_verified=True, api_key=None)
        for r in results:
            assert r.get("_rag_fallback_reason") == "no_api_key"


class TestSemanticMode:
    """API key varken semantic mod _rag_mode='semantic' döndürmeli."""

    @pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
    def test_rag_mode_is_semantic(self, tmp_path):
        import rag.retrieve as rmod

        idx_dir = tmp_path / "_rag_index"
        idx_dir.mkdir()
        metadata = [
            {
                "entry_id": "COMMS-001", "category": "comms", "severity": "medium",
                "verified": "VERIFIED", "source": "field", "vendor": None,
                "chunk_text": "PROFINET timing.",
            }
        ]
        (idx_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        emb = np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32")
        np.save(str(idx_dir / "embeddings.npy"), emb)
        fake_vec = np.array([1.0, 0.0, 0.0, 0.0], dtype="float32")

        with patch.object(rmod, "_INDEX_DIR", idx_dir):
            with patch.object(rmod, "_embed_query", return_value=fake_vec):
                results = rmod.retrieve("PROFINET", top_k=5, not_verified=True, api_key="fake-key")

        assert results, "Semantic mod en az bir sonuç döndürmeli"
        for r in results:
            assert r["_rag_mode"] == "semantic", (
                f"_rag_mode 'semantic' olmalı, {r['_rag_mode']!r} geldi"
            )
            assert "_rag_fallback_reason" not in r or r.get("_rag_fallback_reason") is None


class TestRagSafetyCheckTuple:
    """_rag_safety_check BM25 modunda (warnings, rag_mode) tuple döndürmeli."""

    def _build_api(self, tmp_path: Path):
        import factory_web as _fw
        api = _fw.Api.__new__(_fw.Api)
        api.root = tmp_path / "proj"
        api.root.mkdir()
        api.settings = {}
        return api

    def test_returns_tuple_bm25_mode(self, tmp_path):
        idx_dir = _make_bm25_dir(tmp_path, _RAG_RECORDS)
        import rag.retrieve as rmod
        api = self._build_api(tmp_path)
        env_copy = {k: v for k, v in _os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.object(rmod, "_INDEX_DIR", idx_dir):
            with patch.dict(_os.environ, env_copy, clear=True):
                result = api._rag_safety_check("E-stop safety interlock")
        assert isinstance(result, tuple), "_rag_safety_check tuple döndürmeli (list, str)"
        warnings, rag_mode = result
        assert isinstance(warnings, list)
        assert rag_mode in ("bm25", "semantic", "unavailable")

    def test_rag_mode_field_in_warnings(self, tmp_path):
        idx_dir = _make_bm25_dir(tmp_path, _RAG_RECORDS)
        import rag.retrieve as rmod
        api = self._build_api(tmp_path)
        env_copy = {k: v for k, v in _os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.object(rmod, "_INDEX_DIR", idx_dir):
            with patch.dict(_os.environ, env_copy, clear=True):
                warnings, rag_mode = api._rag_safety_check("E-stop safety critical")
        for w in warnings:
            assert "_rag_mode" in w, f"Uyarı kaydında '_rag_mode' yok: {w}"

    def test_rag_mode_propagated_to_caller_bm25(self, tmp_path):
        """BM25 modda rag_mode 'bm25' string'i olmalı; 'unavailable' olmamalı."""
        idx_dir = _make_bm25_dir(tmp_path, _RAG_RECORDS)
        import rag.retrieve as rmod
        api = self._build_api(tmp_path)
        env_copy = {k: v for k, v in _os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.object(rmod, "_INDEX_DIR", idx_dir):
            with patch.dict(_os.environ, env_copy, clear=True):
                _warnings, rag_mode = api._rag_safety_check("E-stop safety critical")
        assert rag_mode != "unavailable", (
            "İndeks mevcutken rag_mode 'unavailable' olmamalı"
        )

    def test_error_returns_unavailable(self, tmp_path):
        import factory_web as _fw
        api = _fw.Api.__new__(_fw.Api)
        api.root = tmp_path / "proj"
        api.root.mkdir()
        api.settings = {}
        import rag.retrieve as rmod
        bad_dir = tmp_path / "noexist"
        with patch.object(rmod, "_INDEX_DIR", bad_dir):
            warnings, rag_mode = api._rag_safety_check("herhangi bir sorgu")
        assert warnings == []
        assert rag_mode == "unavailable"
