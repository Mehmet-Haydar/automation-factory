#!/usr/bin/env python3
"""
legacy_pdf_extract.py — PDF → text extraction for legacy PLC code listings.

"S5/S7 for Windows" and STEP5/STEP7 print exports are often only available
as PDF. This module extracts the text layer with pdfplumber, scores how
much it looks like a real AWL/STL listing, and — when the PDF is a scan
with no usable text layer — falls back to Gemini Vision transcription
(caller provides the client; consent/guard/audit are the caller's duty).

Output convention (next to the source PDF in _raw/legacy_code/):
    <stem>.extracted.txt        — the extracted/transcribed listing
    <stem>.extracted.meta.json  — {source_pdf, method, quality, confirmed}

The engineer MUST review and confirm the extracted text before it is used
by Retrofit Pre-Analysis: classic print/OCR confusions (O↔0, I↔1, B↔8)
silently corrupt addresses like "E 1.0" → "E 1.O".
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Quality heuristics
# ---------------------------------------------------------------------------

# German + English AWL/STL mnemonics at line start (S5 and S7 families).
_OPCODE_RE = re.compile(
    r"^\s*(U|UN|O|ON|X|XN|S|R|=|L|T|FP|FN|ZV|ZR|SI|SE|SA|SV|SS|"
    r"SPA|SPB|SPBN|SPBB|SPZ|SPN|SPP|SPM|SPO|SLW|SRW|SLD|SRD|"
    r"AUF|TAK|TAD|BLD|NOP|BE|BEA|BEB|BEU|CALL|UC|CC|"
    r"A|AN|JU|JC|JCN|OPN|RLO)\b",
    re.IGNORECASE,
)

# Operand shapes: E 1.0 / A 4.7 / M 10.1 / T 5 / Z 3 / MW 100 / DB 20 / PEW 256 …
_OPERAND_RE = re.compile(
    r"\b(E|A|I|Q|M|T|Z|C)\s?\d+\.\d\b"
    r"|\b(EW|AW|IW|QW|MW|MB|MD|PEW|PAW|EB|AB|DW|DBW|DBB|DBD)\s?\d+\b"
    r"|\b(DB|FB|FC|OB|SB|PB)\s?\d+\b",
    re.IGNORECASE,
)

# Network / segment markers in listings
_NETWORK_RE = re.compile(r"\b(NETZWERK|NETWORK|SEGMENT|NW)\s*[:#]?\s*\d+", re.IGNORECASE)

# Below this many characters per page the PDF is treated as a scan
# (image-only pages yield 0–50 chars of furniture from pdfplumber).
MIN_CHARS_PER_PAGE = 200

# Refuse single-shot Vision transcription beyond this size — the result
# would be silently truncated, which is worse than a clear error.
MAX_OCR_PAGES = 100


@dataclass
class QualityReport:
    chars_per_page: float
    opcode_line_ratio: float   # share of non-empty lines that look like AWL
    network_count: int
    score: int                 # 0–100, for the UI badge
    needs_ocr: bool


@dataclass
class ExtractionResult:
    text: str
    page_count: int
    method: str                # "pdfplumber" | "gemini_ocr"
    quality: QualityReport
    # S-5: True when the OCR response hit the max_tokens limit — the
    # transcription is then INCOMPLETE and the engineer must be told.
    truncated: bool = False


def assess_quality(text: str, page_count: int) -> QualityReport:
    """Score extracted text for 'is this a usable AWL/STL listing?'."""
    pages = max(1, page_count)
    chars_per_page = len(text) / pages

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if lines:
        awl_lines = sum(
            1 for ln in lines if _OPCODE_RE.match(ln) or _OPERAND_RE.search(ln)
        )
        opcode_ratio = awl_lines / len(lines)
    else:
        opcode_ratio = 0.0

    network_count = len(_NETWORK_RE.findall(text))

    # 0–50 points for text volume, 0–50 for listing-likeness.
    vol_score = min(50, int(50 * chars_per_page / 800))
    awl_score = min(50, int(50 * opcode_ratio / 0.30))
    score = vol_score + awl_score

    return QualityReport(
        chars_per_page=round(chars_per_page, 1),
        opcode_line_ratio=round(opcode_ratio, 3),
        network_count=network_count,
        score=score,
        needs_ocr=chars_per_page < MIN_CHARS_PER_PAGE,
    )


# ---------------------------------------------------------------------------
# pdfplumber extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_path: Path) -> ExtractionResult:
    """Extract the text layer of *pdf_path* page by page.

    Raises RuntimeError when pdfplumber is unavailable or the PDF is
    unreadable — callers surface the message to the engineer.
    """
    try:
        import pdfplumber  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber is not installed — run: pip install pdfplumber"
        ) from exc

    pages_text: list[str] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            for n, page in enumerate(pdf.pages, start=1):
                txt = page.extract_text() or ""
                pages_text.append(f"--- page {n} ---\n{txt}")
    except Exception as exc:
        raise RuntimeError(f"Could not read PDF '{pdf_path.name}': {exc}") from exc

    text = "\n\n".join(pages_text)
    quality = assess_quality(
        # quality is judged on the raw payload, not our page markers
        "\n".join(t.split("\n", 1)[1] if "\n" in t else "" for t in pages_text),
        page_count,
    )
    return ExtractionResult(
        text=text, page_count=page_count, method="pdfplumber", quality=quality
    )


# ---------------------------------------------------------------------------
# Gemini Vision OCR fallback
# ---------------------------------------------------------------------------

OCR_SYSTEM_PROMPT = (
    "You are a transcription engine for scanned PLC code listings "
    "(Siemens S5/S7 AWL/STL, printed by 'S5/S7 for Windows' or STEP5/STEP7). "
    "Transcribe the document EXACTLY, line by line. Do NOT interpret, "
    "summarise, translate or reformat. Preserve indentation, German "
    "mnemonics (U/UN/O/ON/L/T/SPB...), operands (E 1.0, A 4.7, MW 100, "
    "DB 20) and comments verbatim. Mark every unreadable character as '?'. "
    "Output plain text only — no markdown, no commentary."
)

OCR_USER_PROMPT = (
    "Transcribe the attached scanned PLC code listing exactly. "
    "Plain text only, preserve line structure."
)


def ocr_via_vision(pdf_path: Path, client, page_count: int,
                   max_tokens: int = 32768) -> ExtractionResult:
    """Transcribe a scanned PDF via Gemini Vision.

    *client* is an ai_client.AIClient(provider='google') instance. The
    CALLER is responsible for classification-guard, consent and audit
    logging — this function only performs the call.
    """
    if page_count > MAX_OCR_PAGES:
        raise RuntimeError(
            f"'{pdf_path.name}' has {page_count} pages — beyond the "
            f"{MAX_OCR_PAGES}-page single-shot OCR limit. Split the PDF "
            "(e.g. per block/chapter) and retry."
        )
    response, _usage = client.chat_with_files(
        system=OCR_SYSTEM_PROMPT,
        user=OCR_USER_PROMPT,
        files=[pdf_path],
        max_tokens=max_tokens,
    )
    text = (response or "").strip()
    quality = assess_quality(text, page_count)
    quality.needs_ocr = False  # OCR already happened; don't loop
    return ExtractionResult(
        text=text, page_count=page_count, method="gemini_ocr", quality=quality,
        truncated=bool(getattr(_usage, "truncated", False)),
    )


# ---------------------------------------------------------------------------
# Sidecar files
# ---------------------------------------------------------------------------

def extraction_paths(pdf_path: Path) -> tuple[Path, Path]:
    txt = pdf_path.with_suffix("")  # drop .pdf
    return (
        txt.parent / (txt.name + ".extracted.txt"),
        txt.parent / (txt.name + ".extracted.meta.json"),
    )


def write_extraction(pdf_path: Path, result: ExtractionResult) -> Path:
    """Persist text + meta sidecars; returns the text path. confirmed=False."""
    txt_path, meta_path = extraction_paths(pdf_path)
    txt_path.write_text(result.text, encoding="utf-8")
    meta = {
        "source_pdf": pdf_path.name,
        "method": result.method,
        "page_count": result.page_count,
        "quality": asdict(result.quality),
        "truncated": result.truncated,
        "confirmed": False,
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    return txt_path


def load_extraction_meta(pdf_path: Path) -> Optional[dict]:
    _txt, meta_path = extraction_paths(pdf_path)
    if not meta_path.is_file():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def confirm_extraction(pdf_path: Path, edited_text: Optional[str] = None) -> dict:
    """Mark an extraction as engineer-confirmed (optionally with edits)."""
    txt_path, meta_path = extraction_paths(pdf_path)
    meta = load_extraction_meta(pdf_path)
    if meta is None:
        raise RuntimeError(
            f"No extraction found for '{pdf_path.name}' — run extraction first."
        )
    if edited_text is not None:
        txt_path.write_text(edited_text, encoding="utf-8")
        meta["edited_by_engineer"] = True
    meta["confirmed"] = True
    meta["confirmed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    return meta
