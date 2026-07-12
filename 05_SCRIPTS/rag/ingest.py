#!/usr/bin/env python3
"""
ingest.py — Build RAG index from KB_*.md and 09_HARDWARE_LIBRARY/**/*.md.

Parses file-level ## metadata blocks, splits KB files into per-entry chunks,
calls OpenAI embedding API, saves index to _rag_index/ at repo root.

Usage:
    python 05_SCRIPTS/rag/ingest.py [--api-key KEY] [--model MODEL] [--dry-run]

Environment:
    OPENAI_API_KEY — used when --api-key is not supplied

Output:
    <repo_root>/_rag_index/metadata.json  — list of chunk records
    <repo_root>/_rag_index/embeddings.npy — numpy float32 array (N × D)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent  # 05_SCRIPTS/rag/ → repo root
_KB_DIR = _REPO_ROOT / "06_KNOWLEDGE_BASE"
_HW_DIR = _REPO_ROOT / "09_HARDWARE_LIBRARY"
_INDEX_DIR = _REPO_ROOT / "_rag_index"

EMBEDDING_MODEL_DEFAULT = "text-embedding-3-small"

# ─────────────────────────────────────────────────────────────────────────────
# Markdown helpers
# ─────────────────────────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_YAML_BLOCK_RE = re.compile(r"```ya?ml\n(.*?)```", re.DOTALL)
_HTML_META_RE = re.compile(r"<!--\s*metadata\s*\n(.*?)-->", re.DOTALL)


def _parse_yaml_inline(text: str) -> dict[str, Any]:
    """Parse simple key: value YAML (no nested, no lists beyond inline)."""
    result: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            result[key.strip()] = val
    return result


def _extract_file_metadata(text: str) -> dict[str, Any]:
    """Find ## metadata section and extract the YAML block inside it."""
    # Locate ## metadata heading (may appear after frontmatter and H1)
    meta_match = re.search(r"^##\s+metadata\s*\n", text, re.MULTILINE)
    if not meta_match:
        return {}
    after = text[meta_match.end():]
    block_match = _YAML_BLOCK_RE.search(after)
    if not block_match:
        return {}
    return _parse_yaml_inline(block_match.group(1))


def _extract_entry_metadata_comment(chunk_text: str) -> dict[str, Any]:
    """Extract <!-- metadata ... --> comment from within a chunk."""
    m = _HTML_META_RE.search(chunk_text)
    if not m:
        return {}
    return _parse_yaml_inline(m.group(1))


# ─────────────────────────────────────────────────────────────────────────────
# KB file parsing
# ─────────────────────────────────────────────────────────────────────────────

def _split_kb_entries(text: str, heading_level: int, prefix: str) -> list[str]:
    """Split markdown text into entry chunks based on heading level and prefix."""
    marker = "#" * heading_level + " "
    lines = text.splitlines(keepends=True)
    chunks: list[str] = []
    current: list[str] = []
    in_entries = False

    for line in lines:
        is_entry = line.startswith(marker) and (not prefix or line[len(marker):].startswith(prefix))
        if is_entry:
            if current:
                chunks.append("".join(current))
            current = [line]
            in_entries = True
        else:
            if in_entries:
                current.append(line)

    if current:
        chunks.append("".join(current))
    return [c.strip() for c in chunks if c.strip()]


def parse_kb_file(path: Path) -> list[dict[str, Any]]:
    """Parse one KB_*.md file into a list of chunk records."""
    text = path.read_text(encoding="utf-8")

    # Strip frontmatter so ## metadata search doesn't get confused
    fm_match = _FRONTMATTER_RE.match(text)
    body = text[fm_match.end():] if fm_match else text

    file_meta = _extract_file_metadata(body)
    if not file_meta:
        print(f"  WARNING: {path.name} — no ## metadata block found; skipped (add metadata to enable RAG)", file=sys.stderr)
        return []

    category = file_meta.get("rag_category", "unknown")
    severity_default = file_meta.get("rag_severity_default", "medium")
    verified_default = file_meta.get("rag_verified_default", "NOT_VERIFIED")
    source_pattern = file_meta.get("rag_source_pattern", "field_experience_anon")
    prefix_id = file_meta.get("rag_entry_id_prefix", "KB")
    try:
        split_level = int(file_meta.get("rag_entry_split_heading_level", "2"))
    except ValueError:
        split_level = 2
    split_prefix = file_meta.get("rag_entry_split_prefix", "").strip('"').strip("'")

    # Remove ## metadata section from body before splitting
    body_no_meta = re.sub(
        r"^##\s+metadata\s*\n```ya?ml\n.*?```\s*\n", "", body,
        flags=re.MULTILINE | re.DOTALL,
    )

    chunks = _split_kb_entries(body_no_meta, split_level, split_prefix)
    records: list[dict[str, Any]] = []

    for idx, chunk in enumerate(chunks, start=1):
        override = _extract_entry_metadata_comment(chunk)
        entry_id = override.get("entry_id") or f"{prefix_id}-{idx:03d}"
        records.append(
            {
                "entry_id": entry_id,
                "category": override.get("category", category),
                "severity": override.get("severity", severity_default),
                "verified": override.get("verified", verified_default),
                "source": override.get("source", source_pattern),
                "vendor": override.get("vendor") or None,
                "chunk_text": chunk,
                "source_file": path.relative_to(_REPO_ROOT).as_posix(),
            }
        )
    return records


# ─────────────────────────────────────────────────────────────────────────────
# Hardware library parsing
# ─────────────────────────────────────────────────────────────────────────────

_DEVICE_CATEGORY_MAP = {
    "drives": "device_spec",
    "io_modules": "device_spec",
    "sensors": "device_spec",
    "valves": "device_spec",
    "hmi": "device_spec",
}


def parse_hw_file(path: Path) -> list[dict[str, Any]]:
    """Parse one device MD file from 09_HARDWARE_LIBRARY as a single chunk."""
    text = path.read_text(encoding="utf-8")

    fm_match = _FRONTMATTER_RE.match(text)
    body = text[fm_match.end():] if fm_match else text

    meta_match = re.search(r"^##\s+metadata\s*\n", body, re.MULTILINE)
    if not meta_match:
        return []
    after = body[meta_match.end():]
    block_match = _YAML_BLOCK_RE.search(after)
    if not block_match:
        return []

    dev_meta = _parse_yaml_inline(block_match.group(1))
    device_id = dev_meta.get("device_id", path.stem)
    vendor = dev_meta.get("vendor", "")
    category = _DEVICE_CATEGORY_MAP.get(dev_meta.get("category", ""), "device_spec")
    last_verified = dev_meta.get("last_verified", "")
    verified = "VERIFIED" if last_verified else "NOT_VERIFIED"

    return [
        {
            "entry_id": device_id,
            "category": category,
            "severity": "low",
            "verified": verified,
            "source": dev_meta.get("datasheet_ref", "vendor_datasheet_anon"),
            "vendor": vendor or None,
            "chunk_text": text.strip(),
            "source_file": path.relative_to(_REPO_ROOT).as_posix(),
        }
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Embedding
# ─────────────────────────────────────────────────────────────────────────────

def _embed_texts(texts: list[str], api_key: str, model: str) -> list[list[float]]:
    try:
        from openai import OpenAI  # lazy import — optional at package level
    except ImportError as exc:
        raise SystemExit("openai package required: pip install openai>=1.50.0") from exc

    client = OpenAI(api_key=api_key)
    # Batch in chunks of 100 to respect API limits
    embeddings: list[list[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(input=batch, model=model)
        embeddings.extend([r.embedding for r in response.data])
    return embeddings


# ─────────────────────────────────────────────────────────────────────────────
# BM25 keyword index (offline mode — no API needed)
# ─────────────────────────────────────────────────────────────────────────────

import math
from collections import Counter as _Counter


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def build_bm25_index(records: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> dict[str, Any]:
    """Build a BM25 index from records. Returns a serialisable dict."""
    corpus = [_tokenize(r["chunk_text"]) for r in records]
    N = len(corpus)
    avgdl = sum(len(doc) for doc in corpus) / max(N, 1)

    df: dict[str, int] = {}
    for doc in corpus:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1

    idf = {
        term: math.log((N - freq + 0.5) / (freq + 0.5) + 1)
        for term, freq in df.items()
    }

    tf_docs: list[dict[str, float]] = []
    for doc in corpus:
        tf_raw = dict(_Counter(doc))
        dl = len(doc)
        tf_bm25 = {
            term: (cnt * (k1 + 1)) / (cnt + k1 * (1 - b + b * dl / avgdl))
            for term, cnt in tf_raw.items()
        }
        tf_docs.append(tf_bm25)

    return {"records": records, "idf": idf, "tf_docs": tf_docs,
            "avgdl": avgdl, "N": N, "k1": k1, "b": b}


def _save_bm25_index(bm25: dict[str, Any]) -> None:
    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    path = _INDEX_DIR / "bm25.json"
    # sort_keys: the index is committed — a rebuild with unchanged content
    # must be byte-identical, or every rebuild floods the git diff with
    # hash-order noise (2026-07-10 finding: 2828-line phantom diff).
    path.write_text(json.dumps(bm25, ensure_ascii=False, indent=2,
                               sort_keys=True), encoding="utf-8")
    print(f"  Saved BM25 index ({len(bm25['records'])} records) -> _rag_index/bm25.json")


# ─────────────────────────────────────────────────────────────────────────────
# Semantic index write
# ─────────────────────────────────────────────────────────────────────────────

def _save_index(records: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
    try:
        import numpy as np
    except ImportError as exc:
        raise SystemExit("numpy required: pip install numpy") from exc

    _INDEX_DIR.mkdir(parents=True, exist_ok=True)

    metadata_path = _INDEX_DIR / "metadata.json"
    embeddings_path = _INDEX_DIR / "embeddings.npy"

    # Strip chunk_text from metadata (stored separately for space efficiency)
    meta_records = [{k: v for k, v in r.items() if k != "chunk_text"} for r in records]
    chunk_texts = [r["chunk_text"] for r in records]

    # Store chunk_texts alongside metadata
    for m, ct in zip(meta_records, chunk_texts):
        m["chunk_text"] = ct

    metadata_path.write_text(json.dumps(meta_records, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(str(embeddings_path), np.array(embeddings, dtype="float32"))

    print(f"  Saved {len(records)} records -> _rag_index/")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def collect_records() -> list[dict[str, Any]]:
    """Collect all chunk records from KB and hardware library."""
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # KB files
    for path in sorted(_KB_DIR.glob("KB_*.md")):
        file_records = parse_kb_file(path)
        for r in file_records:
            if r["entry_id"] in seen_ids:
                print(f"  WARNING: duplicate entry_id {r['entry_id']} in {path.name} — skipped")
                continue
            seen_ids.add(r["entry_id"])
            records.append(r)
        if file_records:
            print(f"  {path.name}: {len(file_records)} entries")

    # Hardware library files
    for path in sorted(_HW_DIR.rglob("*.md")):
        if path.name.startswith("_"):
            continue  # skip schema / prompt files
        file_records = parse_hw_file(path)
        for r in file_records:
            if r["entry_id"] in seen_ids:
                print(f"  WARNING: duplicate entry_id {r['entry_id']} in {path.name} — skipped")
                continue
            seen_ids.add(r["entry_id"])
            records.append(r)
        if file_records:
            print(f"  {path.relative_to(_HW_DIR)}: {len(file_records)} entries")

    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build RAG index from KB + hardware library")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""), help="OpenAI API key")
    parser.add_argument("--model", default=EMBEDDING_MODEL_DEFAULT, help="Embedding model")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print records without embedding")
    parser.add_argument("--offline", action="store_true",
                        help="Build keyword (BM25) index only — no API key needed")
    args = parser.parse_args(argv)

    print("Collecting records...")
    records = collect_records()
    print(f"Total: {len(records)} chunks")

    if not records:
        print("No records found. Check KB_*.md files have ## metadata blocks.")
        return 1

    if args.dry_run:
        for r in records:
            print(f"  [{r['entry_id']}] {r['category']} / {r['severity']} / {r['verified']}")
        return 0

    if args.offline:
        print("Building BM25 keyword index (offline mode)...")
        bm25 = build_bm25_index(records)
        _save_bm25_index(bm25)
        return 0

    if not args.api_key:
        print("ERROR: OPENAI_API_KEY not set. Pass --api-key or set the environment variable.")
        return 1

    print(f"Embedding {len(records)} chunks with {args.model}...")
    texts = [r["chunk_text"] for r in records]
    embeddings = _embed_texts(texts, args.api_key, args.model)

    _save_index(records, embeddings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
