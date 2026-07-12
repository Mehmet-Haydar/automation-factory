"""Proof tests — RAG index cache (performance audit finding).

bm25.json (~274 KB) and metadata.json were re-parsed on EVERY retrieve call.
The cache is keyed by (path, mtime): repeated loads reuse the parsed object,
while a re-ingest (mtime change) is picked up without an app restart.
"""
from __future__ import annotations

import json
import os

import pytest

from rag import retrieve as rv


@pytest.fixture
def fake_index(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "_INDEX_DIR", tmp_path)
    rv._index_cache.clear()
    bm25 = tmp_path / "bm25.json"
    bm25.write_text(json.dumps({"idf": {"motor": 1.0}, "tf_docs": [],
                                "doc_len": [], "avgdl": 1.0, "records": []}),
                    encoding="utf-8")
    return bm25


def test_second_load_skips_parsing(fake_index, monkeypatch):
    first = rv._load_bm25_index()
    calls = {"n": 0}
    real_loads = json.loads

    def counting(s, *a, **k):
        calls["n"] += 1
        return real_loads(s, *a, **k)

    monkeypatch.setattr(json, "loads", counting)
    second = rv._load_bm25_index()
    assert calls["n"] == 0, "Aynı mtime ile ikinci yükleme json.loads çağırdı — cache yok"
    assert second is first, "Cache aynı nesneyi döndürmeli"


def test_reingest_invalidates_cache(fake_index):
    first = rv._load_bm25_index()
    new_content = {"idf": {"valve": 2.0}, "tf_docs": [], "doc_len": [],
                   "avgdl": 1.0, "records": []}
    fake_index.write_text(json.dumps(new_content), encoding="utf-8")
    # Force a different mtime even on coarse-resolution filesystems.
    st = fake_index.stat()
    os.utime(fake_index, (st.st_atime, st.st_mtime + 5))
    second = rv._load_bm25_index()
    assert second is not first
    assert "valve" in second["idf"], "Yeni ingest cache'e yansımadı"


def test_missing_index_still_raises(fake_index):
    fake_index.unlink()
    rv._index_cache.clear()
    with pytest.raises(Exception) as ei:
        rv._load_bm25_index()
    assert "BM25 index not found" in str(ei.value)
