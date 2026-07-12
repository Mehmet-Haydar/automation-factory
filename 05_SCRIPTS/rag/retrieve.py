#!/usr/bin/env python3
"""
retrieve.py — Query the RAG index and return top-k matching chunks.

Usage (CLI):
    python 05_SCRIPTS/rag/retrieve.py "PROFINET cycle time" --top-k 5

Usage (API):
    from rag.retrieve import retrieve
    results = retrieve("PROFINET cycle time", top_k=5)

Returns list of dicts with keys:
    entry_id, category, severity, verified, source, vendor, chunk_text, score

Only VERIFIED records are returned by default.
Pass not_verified=True to include NOT_VERIFIED records (annotated with a flag).
critical(safety) records are always returned with rag_warning=True.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

from . import RAGIndexNotFoundError

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent
_INDEX_DIR = _REPO_ROOT / "_rag_index"

EMBEDDING_MODEL_DEFAULT = "text-embedding-3-small"


# ─────────────────────────────────────────────────────────────────────────────
# Index loading
# ─────────────────────────────────────────────────────────────────────────────

# Module-level cache keyed by (path, mtime): the indexes are a few hundred KB
# of JSON parsed on EVERY retrieve call otherwise (safety-check + suggestion
# paths hit this several times per user action). mtime keying keeps a fresh
# ingest visible without an app restart.
_index_cache: dict[str, tuple[float, Any]] = {}


def _cached_load(path: Path, loader):
    key = str(path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _index_cache.pop(key, None)
        raise
    hit = _index_cache.get(key)
    if hit is not None and hit[0] == mtime:
        return hit[1]
    value = loader(path)
    _index_cache[key] = (mtime, value)
    return value


def _load_index() -> tuple[list[dict[str, Any]], Any]:
    """Load metadata list and embedding matrix. Raises RAGIndexNotFoundError if missing."""
    metadata_path = _INDEX_DIR / "metadata.json"
    embeddings_path = _INDEX_DIR / "embeddings.npy"

    if not metadata_path.exists() or not embeddings_path.exists():
        raise RAGIndexNotFoundError(
            f"RAG index not found at {_INDEX_DIR}. "
            "Run '05_SCRIPTS/rag/ingest.py' to build it."
        )

    try:
        import numpy as np
    except ImportError as exc:
        raise SystemExit("numpy required: pip install numpy") from exc

    metadata = _cached_load(
        metadata_path, lambda p: json.loads(p.read_text(encoding="utf-8")))
    embeddings = _cached_load(embeddings_path, lambda p: np.load(str(p)))
    return metadata, embeddings


# ─────────────────────────────────────────────────────────────────────────────
# BM25 keyword index
# ─────────────────────────────────────────────────────────────────────────────

def _load_bm25_index() -> dict[str, Any]:
    """Load bm25.json. Raises RAGIndexNotFoundError if missing."""
    path = _INDEX_DIR / "bm25.json"
    if not path.exists():
        raise RAGIndexNotFoundError(
            f"BM25 index not found at {path}. "
            "Run '05_SCRIPTS/rag/ingest.py --offline' to build it."
        )
    return _cached_load(
        path, lambda p: json.loads(p.read_text(encoding="utf-8")))


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def _bm25_search(
    query: str,
    bm25: dict[str, Any],
    top_k: int,
    not_verified: bool,
    category_filter: str | None,
) -> list[dict[str, Any]]:
    """Score all records with BM25 and return top-k filtered results."""
    tokens = _tokenize(query)
    idf: dict[str, float] = bm25["idf"]
    tf_docs: list[dict[str, float]] = bm25["tf_docs"]
    records: list[dict[str, Any]] = bm25["records"]
    k1: float = bm25["k1"]

    scores: list[tuple[int, float]] = []
    for idx, tf in enumerate(tf_docs):
        score = sum(idf.get(t, 0.0) * tf.get(t, 0.0) for t in tokens)
        scores.append((idx, score))

    scores.sort(key=lambda x: x[1], reverse=True)

    results: list[dict[str, Any]] = []
    for idx, score in scores:
        if score <= 0:
            break
        rec = records[idx]

        is_not_verified = rec.get("verified", "NOT_VERIFIED") == "NOT_VERIFIED"
        if is_not_verified and not not_verified:
            continue

        if category_filter and rec.get("category") != category_filter:
            continue

        results.append({
            **rec,
            "score": score,
            "rag_warning": rec.get("severity") == "critical(safety)",
            "not_verified": is_not_verified,
        })

        if len(results) >= top_k:
            break

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Embedding
# ─────────────────────────────────────────────────────────────────────────────

def _embed_query(text: str, api_key: str, model: str) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("openai package required: pip install openai>=1.50.0") from exc

    import numpy as np

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(input=[text], model=model)
    return np.array(response.data[0].embedding, dtype="float32")


# ─────────────────────────────────────────────────────────────────────────────
# Similarity
# ─────────────────────────────────────────────────────────────────────────────

def _cosine_similarity(query_vec: Any, matrix: Any) -> Any:
    import numpy as np

    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
    normed = matrix / norms
    return normed @ query_norm


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    top_k: int = 5,
    not_verified: bool = False,
    category_filter: str | None = None,
    api_key: str | None = None,
    model: str = EMBEDDING_MODEL_DEFAULT,
) -> list[dict[str, Any]]:
    """Return top-k matching KB chunks for the given query.

    Mode selection (automatic):
      - If embeddings.npy exists → semantic search (requires OpenAI key).
      - If only bm25.json exists → BM25 keyword search (no API key needed).

    Args:
        query: Natural language search query.
        top_k: Number of results to return.
        not_verified: Include NOT_VERIFIED entries (annotated with not_verified=True).
        category_filter: Restrict to a specific category (e.g. "safety", "comms").
        api_key: OpenAI API key; only needed for semantic mode.
        model: Embedding model name.

    Returns:
        List of dicts: {entry_id, category, severity, verified, source, vendor,
                        chunk_text, score, rag_warning, not_verified,
                        _rag_mode ("semantic"|"bm25"),
                        _rag_fallback_reason ("no_embeddings"|"no_api_key") — only present in BM25 mode}

    Raises:
        RAGIndexNotFoundError: If neither semantic nor BM25 index exists.
    """
    embeddings_path = _INDEX_DIR / "embeddings.npy"
    bm25_path = _INDEX_DIR / "bm25.json"

    if not embeddings_path.exists() and not bm25_path.exists():
        raise RAGIndexNotFoundError(
            f"RAG index not found at {_INDEX_DIR}. "
            "Run 'python 05_SCRIPTS/rag/ingest.py --offline' to build the BM25 index."
        )

    # BM25 mode: no embeddings.npy but bm25.json present
    if not embeddings_path.exists() and bm25_path.exists():
        bm25 = _load_bm25_index()
        hits = _bm25_search(query, bm25, top_k, not_verified, category_filter)
        for h in hits:
            h["_rag_mode"] = "bm25"
            h["_rag_fallback_reason"] = "no_embeddings"
        return hits

    # Semantic mode: requires embeddings.npy (and API key)
    import numpy as np

    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        # B-06: both indexes present but no API key → fall back to BM25
        if bm25_path.exists():
            bm25 = _load_bm25_index()
            hits = _bm25_search(query, bm25, top_k, not_verified, category_filter)
            for h in hits:
                h["_rag_mode"] = "bm25"
                h["_rag_fallback_reason"] = "no_api_key"
            return hits
        raise ValueError("OPENAI_API_KEY not set. Pass api_key= or set the environment variable.")

    metadata, embeddings = _load_index()

    query_vec = _embed_query(query, key, model)
    scores = _cosine_similarity(query_vec, embeddings)

    # Build candidate list
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

    results: list[dict[str, Any]] = []
    for idx, score in indexed:
        rec = metadata[idx]

        # Verified filter
        is_not_verified = rec.get("verified", "NOT_VERIFIED") == "NOT_VERIFIED"
        if is_not_verified and not not_verified:
            continue

        # Category filter
        if category_filter and rec.get("category") != category_filter:
            continue

        entry = {
            **rec,
            "score": float(score),
            "rag_warning": rec.get("severity") == "critical(safety)",
            "not_verified": is_not_verified,
            "_rag_mode": "semantic",
        }
        results.append(entry)

        if len(results) >= top_k:
            break

    return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query RAG index")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--not-verified", action="store_true")
    parser.add_argument("--category", default=None)
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--model", default=EMBEDDING_MODEL_DEFAULT)
    args = parser.parse_args(argv)

    bm25_only = not args.api_key and (_INDEX_DIR / "bm25.json").exists()
    if not args.api_key and not bm25_only:
        print("ERROR: OPENAI_API_KEY not set and no BM25 index found.")
        return 1

    try:
        results = retrieve(
            args.query,
            top_k=args.top_k,
            not_verified=args.not_verified,
            category_filter=args.category,
            api_key=args.api_key,
            model=args.model,
        )
    except RAGIndexNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    for r in results:
        warning = " ⚠️  SAFETY WARNING" if r["rag_warning"] else ""
        nv = " [NOT_VERIFIED]" if r["not_verified"] else ""
        print(f"\n[{r['entry_id']}] score={r['score']:.3f} {r['category']} / {r['severity']}{warning}{nv}")
        print(r["chunk_text"][:300].strip())

    if not results:
        print("No results found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
