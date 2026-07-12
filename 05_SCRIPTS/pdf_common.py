#!/usr/bin/env python3
"""
pdf_common.py — shared PDF infrastructure for all document generators
(customer_report, FAT/SAT protocols, SISTEMA prep list, CE assessment).

Extracted from customer_report.py (Phase 1.4) so every
generator uses one style/table implementation.  customer_report keeps its
hand-built story; the protocol generators use ``markdown_to_pdf`` which
renders the Markdown subset our generators emit (headings, pipe tables,
blockquotes, fenced code, paragraphs, horizontal rules).

Fail-safe contract:
- reportlab missing            → PdfUnavailableError (caller produces MD and
  warns loudly — same pattern as customer_report).
- any render error             → exception propagates; the caller must keep
  the MD output and surface the error.  A silent half-written PDF is never
  left behind (written to a temp name, renamed only on success).

Unicode: Helvetica lacks Turkish ğ/ş/İ/ı.  ``ensure_unicode_font`` registers
the first available system TTF (Arial on Windows, DejaVu on Linux) and
returns its family name; when none is found it falls back to Helvetica with
a loud warning (DE/EN render fine, TR degrades visibly, never silently).
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Optional

# -- reportlab optional --------------------------------------------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, Preformatted,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class PdfUnavailableError(RuntimeError):
    """reportlab is not installed — PDF output cannot be produced."""

    def __init__(self) -> None:
        super().__init__(
            "PDF output unavailable: reportlab is not installed "
            "(pip install reportlab). The Markdown version is still produced."
        )


# -- shared palette (identical values to the former customer_report block) ----
if HAS_REPORTLAB:
    NAVY   = colors.HexColor("#1E3A5F")
    STEEL  = colors.HexColor("#2E86AB")
    LIGHT  = colors.HexColor("#D1E8F5")
    GREEN  = colors.HexColor("#059669")
    ORANGE = colors.HexColor("#D97706")
    GRAY   = colors.HexColor("#6B7280")
    LGRAY  = colors.HexColor("#F3F4F6")


# -- Unicode font registration -------------------------------------------------

_FONT_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    # (family-name, regular path, bold path)
    ("DocSans",
     r"C:\Windows\Fonts\arial.ttf",
     r"C:\Windows\Fonts\arialbd.ttf"),
    ("DocSans",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("DocSans",
     "/usr/share/fonts/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
)

_registered_family: Optional[str] = None


def ensure_unicode_font() -> tuple[str, str]:
    """Register a Unicode TTF once; return (regular, bold) font names.

    Falls back to Helvetica with a loud warning when no candidate exists —
    Turkish characters will then render incorrectly, which the warning says
    explicitly (never a silent degradation).
    """
    global _registered_family
    if not HAS_REPORTLAB:
        raise PdfUnavailableError()
    if _registered_family:
        return _registered_family, _registered_family + "-Bold"
    for family, regular, bold in _FONT_CANDIDATES:
        if os.path.isfile(regular) and os.path.isfile(bold):
            pdfmetrics.registerFont(TTFont(family, regular))
            pdfmetrics.registerFont(TTFont(family + "-Bold", bold))
            _registered_family = family
            return family, family + "-Bold"
    warnings.warn(
        "pdf_common: no Unicode TTF found (Arial/DejaVu) — falling back to "
        "Helvetica. Turkish characters (ğ, ş, İ, ı) will NOT render correctly "
        "in the PDF.",
        stacklevel=2,
    )
    return "Helvetica", "Helvetica-Bold"


# -- shared style/table helpers (formerly private in customer_report) ----------

def build_styles(font_regular: str = "Helvetica",
                 font_bold: str = "Helvetica-Bold") -> dict:
    if not HAS_REPORTLAB:
        raise PdfUnavailableError()
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"], fontName=font_bold,
            fontSize=26, textColor=NAVY, spaceAfter=10, alignment=TA_CENTER,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", parent=base["Normal"], fontName=font_regular,
            fontSize=14, textColor=STEEL, spaceAfter=8, alignment=TA_CENTER,
        ),
        "cover_info": ParagraphStyle(
            "cover_info", parent=base["Normal"], fontName=font_regular,
            fontSize=11, textColor=GRAY, spaceAfter=5, alignment=TA_CENTER,
        ),
        "section_head": ParagraphStyle(
            "section_head", parent=base["Heading1"], fontName=font_bold,
            fontSize=13, textColor=NAVY, spaceBefore=14, spaceAfter=6,
        ),
        "sub_head": ParagraphStyle(
            "sub_head", parent=base["Heading2"], fontName=font_bold,
            fontSize=11, textColor=STEEL, spaceBefore=10, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName=font_regular,
            fontSize=10, spaceAfter=4, leading=14,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontName=font_regular,
            fontSize=8, textColor=GRAY, spaceAfter=3,
        ),
        "check": ParagraphStyle(
            "check", parent=base["Normal"], fontName=font_regular,
            fontSize=10, leftIndent=10, spaceAfter=5,
        ),
        "quote": ParagraphStyle(
            "quote", parent=base["Normal"], fontName=font_regular,
            fontSize=9, textColor=GRAY, leftIndent=12, spaceAfter=6,
            leading=12,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], fontName=font_regular,
            fontSize=8, leading=10,
        ),
        "cell_head": ParagraphStyle(
            "cell_head", parent=base["Normal"], fontName=font_bold,
            fontSize=8, leading=10, textColor=colors.white,
        ),
    }


def hr() -> "HRFlowable":
    if not HAS_REPORTLAB:
        raise PdfUnavailableError()
    return HRFlowable(width="100%", thickness=1, color=LIGHT,
                      spaceAfter=6, spaceBefore=2)


def section(styles: dict, title: str) -> list:
    if not HAS_REPORTLAB:
        raise PdfUnavailableError()
    return [Spacer(1, 0.3 * cm), Paragraph(title, styles["section_head"]), hr()]


def table(data: list[list], col_widths: list,
          font_bold: str = "Helvetica-Bold") -> "Table":
    if not HAS_REPORTLAB:
        raise PdfUnavailableError()
    t = Table(data, colWidths=col_widths, repeatRows=1)
    # FONTNAME only bites for plain-string cells (Paragraph cells keep their
    # own style); pass the registered Unicode bold so a header is never
    # rendered with a non-Unicode font regardless of cell type.
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  font_bold),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LGRAY]),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",          (0, 0), (-1, -1), 0.25, GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    return t


# -- Markdown-subset → PDF ------------------------------------------------------

def _escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))


def _inline(text: str) -> str:
    """Escape XML, then map the inline markdown our generators emit."""
    import re
    out = _escape(text)
    # Generators emit <br> as an intentional line break inside a table cell;
    # _escape just turned it into literal "&lt;br&gt;". Restore it to the
    # reportlab line-break tag so the customer PDF does not show "<br>" text.
    out = out.replace("&lt;br/&gt;", "<br/>").replace("&lt;br&gt;", "<br/>")
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"`([^`]+)`", r"\1", out)   # code spans: keep literal text
    out = re.sub(r"^_\((.+)\)_$", r"<i>(\1)</i>", out)
    return out


def _split_md_row(line: str) -> list[str]:
    # "| a | b |" → ["a", "b"]  (outer pipes removed, cells stripped)
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def _col_widths(rows: list[list[str]], usable: float) -> list:
    """Distribute usable width proportionally to column content length.

    Every column gets an absolute minimum wider than the cell padding —
    a proportional share below the padding makes reportlab fail with
    "negative availWidth" on narrow columns like "Nr.".
    """
    ncols = max(len(r) for r in rows)
    min_w = 1.1 * cm  # > 12pt padding + a few characters
    weights = []
    for i in range(ncols):
        longest = max((len(r[i]) if i < len(r) else 0) for r in rows)
        weights.append(max(4, min(longest, 60)))
    total = sum(weights)
    widths = [usable * w / total for w in weights]
    deficit = sum(max(0.0, min_w - w) for w in widths)
    if deficit > 0:
        shrinkable = sum(w - min_w for w in widths if w > min_w)
        out = []
        for w in widths:
            if w < min_w:
                out.append(min_w)
            elif shrinkable > 0:
                out.append(w - deficit * (w - min_w) / shrinkable)
            else:
                out.append(w)
        widths = out
    return widths


def markdown_to_pdf(md_text: str, dest: Path, title: str,
                    author: str = "AUTOMATION FACTORY") -> Path:
    """Render the generator Markdown subset to *dest* (A4).

    Raises PdfUnavailableError when reportlab is missing and propagates any
    render error.  The file is written atomically: a partial PDF never
    remains at *dest* (tmp name → rename on success).
    """
    if not HAS_REPORTLAB:
        raise PdfUnavailableError()

    font_regular, font_bold = ensure_unicode_font()
    styles = build_styles(font_regular, font_bold)

    page_w, _ = A4
    usable = page_w - 3.0 * cm

    story: list = []
    lines = md_text.splitlines()
    i = 0
    table_buf: list[list[str]] = []
    code_buf: list[str] = []
    in_code = False

    def flush_table():
        if not table_buf:
            return
        widths = _col_widths(table_buf, usable)
        data = []
        for r_idx, row in enumerate(table_buf):
            style = styles["cell_head"] if r_idx == 0 else styles["cell"]
            # pad short rows so reportlab gets a rectangular matrix
            padded = row + [""] * (len(table_buf[0]) - len(row))
            data.append([Paragraph(_inline(c), style) for c in padded])
        story.append(table(data, widths, font_bold=font_bold))
        story.append(Spacer(1, 0.25 * cm))
        table_buf.clear()

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if in_code:
            if stripped.startswith("```"):
                story.append(Preformatted("\n".join(code_buf), styles["small"]))
                story.append(Spacer(1, 0.2 * cm))
                code_buf.clear()
                in_code = False
            else:
                code_buf.append(raw)
            i += 1
            continue

        if stripped.startswith("```"):
            flush_table()
            in_code = True
            i += 1
            continue

        if stripped.startswith("|"):
            cells = _split_md_row(stripped)
            # skip separator rows |---|---|
            if not all(set(c) <= set("-: ") for c in cells):
                table_buf.append(cells)
            i += 1
            continue

        flush_table()

        if not stripped:
            i += 1
            continue
        if stripped.startswith("# "):
            story.append(Paragraph(_inline(stripped[2:]), styles["cover_title"]))
            story.append(hr())
        elif stripped.startswith("## "):
            story.extend(section(styles, _inline(stripped[3:])))
        elif stripped.startswith("### "):
            story.append(Paragraph(_inline(stripped[4:]), styles["sub_head"]))
        elif stripped.startswith("> "):
            story.append(Paragraph(_inline(stripped[2:]), styles["quote"]))
        elif stripped in ("---", "***"):
            story.append(hr())
        elif stripped.startswith("- "):
            story.append(Paragraph("• " + _inline(stripped[2:]), styles["check"]))
        else:
            story.append(Paragraph(_inline(stripped), styles["body"]))
        i += 1

    flush_table()
    if in_code and code_buf:  # unterminated fence — render what we have
        story.append(Preformatted("\n".join(code_buf), styles["small"]))

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    doc = SimpleDocTemplate(
        str(tmp), pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=title, author=author,
    )
    try:
        doc.build(story)
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return dest
