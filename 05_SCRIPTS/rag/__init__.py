"""
05_SCRIPTS/rag — Knowledge Base RAG module.

Provides:
  ingest.py  — parse KB_*.md + 09_HARDWARE_LIBRARY/**/*.md, embed, save index
  retrieve.py — load index, embed query, return top-k chunks

Exceptions:
  RAGIndexNotFoundError — raised when _rag_index/ is missing (run ingest.py first)
"""

from __future__ import annotations


class RAGIndexNotFoundError(RuntimeError):
    """Raised when _rag_index/ does not exist or is empty.

    Caller must run ingest.py before querying.
    """
