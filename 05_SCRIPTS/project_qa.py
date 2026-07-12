#!/usr/bin/env python3
"""
project_qa.py — deterministic, source-cited project search ("ask the project").

Field reality: the question an engineer actually asks all day is tiny and
concrete — "Y5 neye bağlı?", "I19.4 nerede kullanılıyor?", "VEREINZELUNG
hangi adımda?". The answer already exists across RD01, the interlock draft,
the traceability matrix and the KB — this module finds it and CITES it.
No AI, offline, milliseconds; the answer is written to REPORTS/PROJECT_QA.md
so it renders in the GUI like every other report.

Honesty contract: only verbatim lines from project documents, each with its
source file. No hits → "not found in the project documents" (never a guess).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_UMLAUTS = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "s",
                          "Ä": "A", "Ö": "O", "Ü": "U"})

# operand-shaped queries get canonical + twin expansion (I9.4 ↔ E9.4)
_OPERAND_Q = re.compile(r"^([IEQAMF])\s*(\d{1,3})\.(\d)$|^([TCZ])\s*(\d{1,3})$",
                        re.I)

_SCAN_SOURCES = [
    ("metadata", "RD*.md"),
    ("REPORTS", "*.md"),
]
_MAX_HITS_PER_FILE = 12
_MAX_TOTAL = 80


@dataclass
class QAResult:
    query: str = ""
    hits: int = 0
    files: int = 0
    report_path: Path | None = None
    sections: list = field(default_factory=list)


def _fold(s: str) -> str:
    return s.translate(_UMLAUTS).lower()


def _query_variants(query: str) -> list[str]:
    q = query.strip()
    m = _OPERAND_Q.match(q.replace(" ", ""))
    if m:
        if m.group(1):
            letter = m.group(1).upper()
            twin = {"I": "E", "E": "I", "Q": "A", "A": "Q",
                    "M": "F", "F": "M"}.get(letter, letter)
            byte, bit = int(m.group(2)), m.group(3)
            return [f"{letter}{byte}.{bit}", f"{twin}{byte}.{bit}",
                    f"{letter} {byte}.{bit}", f"{twin} {byte}.{bit}",
                    f"%{letter}{byte}.{bit}", f"%{twin}{byte}.{bit}"]
        letter, num = m.group(4).upper(), int(m.group(5))
        return [f"{letter}{num}", f"{letter} {num}"]
    return [q]


def ask_project(project_root: Path, query: str) -> QAResult:
    root = Path(project_root)
    res = QAResult(query=query)
    if not query or not query.strip():
        return res
    variants = [_fold(v) for v in _query_variants(query)]

    total = 0
    for sub, pattern in _SCAN_SOURCES:
        base = root / sub
        if not base.is_dir():
            continue
        for fp in sorted(base.glob(pattern)):
            if fp.name == "PROJECT_QA.md":
                continue
            try:
                lines = fp.read_text(encoding="utf-8",
                                     errors="replace").splitlines()
            except Exception:
                continue
            file_hits: list[tuple[int, str]] = []
            for i, ln in enumerate(lines, 1):
                folded = _fold(ln)
                if any(v in folded for v in variants):
                    file_hits.append((i, ln.strip()))
                    if len(file_hits) >= _MAX_HITS_PER_FILE:
                        break
            if file_hits:
                res.sections.append((f"{sub}/{fp.name}", file_hits))
                res.files += 1
                total += len(file_hits)
                if total >= _MAX_TOTAL:
                    break
        if total >= _MAX_TOTAL:
            break
    res.hits = total

    # optional: KB retrieval (offline BM25) — cited as KB source
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent / "rag"))
        from retrieve import retrieve as _kb_retrieve  # type: ignore
        kb_hits = _kb_retrieve(query, top_k=3) or []
        kb_lines = [(0, f"{h.get('source', h.get('id', 'KB'))}: "
                        f"{str(h.get('text', ''))[:180]}")
                    for h in kb_hits if h]
        if kb_lines:
            res.sections.append(("KB (RAG)", kb_lines))
    except Exception:
        pass

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    L = [
        f"# PROJECT QA — “{query}”",
        "",
        f"Generated: {now} · {res.hits} hit(s) in {res.files} document(s)",
        "",
        "> Verbatim lines from the project documents, each with its "
        "source. Nothing here is generated or guessed.",
        "",
    ]
    if not res.sections:
        L.append(f"_“{query}” was not found in the project documents._")
    for src, hits in res.sections:
        L.append(f"## {src}")
        for lineno, text in hits:
            loc = f" (satır {lineno})" if lineno else ""
            L.append(f"- {text[:240]}{loc}")
        L.append("")

    reports = root / "REPORTS"
    reports.mkdir(exist_ok=True)
    path = reports / "PROJECT_QA.md"
    path.write_text("\n".join(L), encoding="utf-8")
    res.report_path = path
    return res


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("usage: project_qa.py <project_root> <query…>")
        raise SystemExit(2)
    r = ask_project(Path(sys.argv[1]), " ".join(sys.argv[2:]))
    print(f"hits={r.hits} files={r.files} -> {r.report_path}")
