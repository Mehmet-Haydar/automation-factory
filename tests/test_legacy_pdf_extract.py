"""M1 — legacy-code PDF input layer.

Covers: pdfplumber text extraction, AWL quality heuristics, sidecar
write/confirm lifecycle, sidecar exclusion from _raw listing, the
pre-analysis refusal for unconfirmed PDFs, and the concat path that feeds
confirmed extracted text (not the PDF binary) into the workflow.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

import legacy_pdf_extract as lpe

fw = importlib.import_module("factory_web")


# ---------------------------------------------------------------------------
# Minimal one-page PDF builder (no extra deps — exact xref offsets)
# ---------------------------------------------------------------------------

def _build_pdf(text_lines: list[str]) -> bytes:
    def esc(s: str) -> str:
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    stream = (
        "BT /F1 10 Tf 50 770 Td 12 TL\n"
        + "\n".join(f"({esc(l)}) Tj T*" for l in text_lines)
        + "\nET"
    )
    stream_b = stream.encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        b"<< /Length " + str(len(stream_b)).encode() + b" >>\nstream\n"
        + stream_b + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        b"trailer\n<< /Size " + str(len(objs) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    )
    return bytes(out)


AWL_LINES = [
    "NETZWERK 1",
    "U E 1.0",
    "UN E 1.1",
    "O M 10.2",
    "= A 4.0",
    "L MW 100",
    "T MW 102",
    "SPB FC30",
    "CALL FB 10, DB 10",
] * 30  # enough volume to clear the chars/page floor


@pytest.fixture
def awl_pdf(tmp_path) -> Path:
    pdf = tmp_path / "old_listing.pdf"
    pdf.write_bytes(_build_pdf(AWL_LINES))
    return pdf


# ---------------------------------------------------------------------------
# Quality heuristics
# ---------------------------------------------------------------------------

class TestQuality:
    def test_awl_listing_scores_high(self):
        q = lpe.assess_quality("\n".join(AWL_LINES), page_count=1)
        assert q.opcode_line_ratio > 0.8
        assert q.score >= 60
        assert not q.needs_ocr

    def test_prose_scores_low_on_opcode_ratio(self):
        prose = "\n".join(["This is the operating manual of the machine."] * 200)
        q = lpe.assess_quality(prose, page_count=1)
        assert q.opcode_line_ratio < 0.1

    def test_empty_text_needs_ocr(self):
        q = lpe.assess_quality("", page_count=5)
        assert q.needs_ocr
        assert q.score == 0

    def test_scanned_pdf_thin_text_needs_ocr(self):
        # A scan yields a few chars of furniture per page
        q = lpe.assess_quality("page 1\npage 2", page_count=10)
        assert q.needs_ocr


# ---------------------------------------------------------------------------
# pdfplumber extraction
# ---------------------------------------------------------------------------

class TestExtractPdfText:
    def test_extracts_awl_text_layer(self, awl_pdf):
        res = lpe.extract_pdf_text(awl_pdf)
        assert res.method == "pdfplumber"
        assert res.page_count == 1
        assert "U E 1.0" in res.text
        assert "SPB FC30" in res.text
        assert not res.quality.needs_ocr

    def test_unreadable_pdf_raises_runtime_error(self, tmp_path):
        bad = tmp_path / "broken.pdf"
        bad.write_bytes(b"%PDF-1.4 garbage")
        with pytest.raises(RuntimeError, match="broken.pdf"):
            lpe.extract_pdf_text(bad)


# ---------------------------------------------------------------------------
# Sidecar lifecycle
# ---------------------------------------------------------------------------

class TestSidecars:
    def test_write_then_confirm_roundtrip(self, awl_pdf):
        res = lpe.extract_pdf_text(awl_pdf)
        txt_path = lpe.write_extraction(awl_pdf, res)
        assert txt_path.name == "old_listing.extracted.txt"
        meta = lpe.load_extraction_meta(awl_pdf)
        assert meta is not None
        assert meta["confirmed"] is False
        assert meta["method"] == "pdfplumber"

        meta2 = lpe.confirm_extraction(awl_pdf, edited_text="U E 1.0\n= A 4.0\n")
        assert meta2["confirmed"] is True
        assert meta2["edited_by_engineer"] is True
        assert txt_path.read_text(encoding="utf-8") == "U E 1.0\n= A 4.0\n"

    def test_confirm_without_extraction_raises(self, tmp_path):
        pdf = tmp_path / "never_extracted.pdf"
        pdf.write_bytes(_build_pdf(["U E 1.0"]))
        with pytest.raises(RuntimeError, match="never_extracted"):
            lpe.confirm_extraction(pdf)

    def test_ocr_page_limit_enforced(self, awl_pdf):
        class _NeverCalledClient:
            def chat_with_files(self, **kw):
                raise AssertionError("must not be called past the page limit")

        with pytest.raises(RuntimeError, match="page"):
            lpe.ocr_via_vision(awl_pdf, _NeverCalledClient(),
                               page_count=lpe.MAX_OCR_PAGES + 1)


# ---------------------------------------------------------------------------
# Api integration
# ---------------------------------------------------------------------------

def _mk_api(root: Path):
    api = object.__new__(fw.Api)
    api.settings = {"api_keys": {"google": "k-g", "anthropic": "k-a"}}
    api.root = root
    return api


def _mk_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "_raw" / "legacy_code").mkdir(parents=True)
    return proj


class TestRawListing:
    def test_sidecars_hidden_pdf_and_txt_listed(self, tmp_path):
        proj = _mk_project(tmp_path)
        lc = proj / "_raw" / "legacy_code"
        (lc / "a.awl").write_text("U E 1.0", encoding="utf-8")
        (lc / "b.pdf").write_bytes(_build_pdf(["U E 1.0"]))
        (lc / "b.extracted.txt").write_text("U E 1.0", encoding="utf-8")
        (lc / "b.extracted.meta.json").write_text("{}", encoding="utf-8")
        (lc / "notes.txt").write_text("plain text export", encoding="utf-8")

        st = _mk_api(proj).get_raw_folder_status()
        names = st["by_category"]["legacy_code"]
        assert "a.awl" in names
        assert "b.pdf" in names
        assert "notes.txt" in names, ".txt exports must now be accepted"
        assert "b.extracted.txt" not in names, "sidecars must stay hidden"
        assert "b.extracted.meta.json" not in names


class TestPreanalysisRefusal:
    def test_unconfirmed_pdf_blocks_preanalysis(self, tmp_path):
        proj = _mk_project(tmp_path)
        (proj / "_raw" / "legacy_code" / "scan.pdf").write_bytes(
            _build_pdf(["U E 1.0"]))
        api = _mk_api(proj)
        r = api.run_retrofit_preanalysis({"engineer": "Test Eng", "confirmed": True})
        assert not r["ok"]
        assert "scan.pdf" in r["msg"]
        assert "confirm" in r["msg"].lower()


class TestPreanalysisConcat:
    def test_confirmed_pdf_text_feeds_workflow_once(self, tmp_path, monkeypatch):
        proj = _mk_project(tmp_path)
        lc = proj / "_raw" / "legacy_code"
        (lc / "code.awl").write_text("UN E 2.0\n", encoding="utf-8")
        pdf = lc / "listing.pdf"
        pdf.write_bytes(_build_pdf(AWL_LINES))
        res = lpe.extract_pdf_text(pdf)
        lpe.write_extraction(pdf, res)
        lpe.confirm_extraction(pdf, edited_text="U E 9.9\n= A 9.9\n")

        # Open classification gate + fake runner (no real AI call)
        import data_classification_guard as dcg

        class _Gate:
            allowed = True
            reason = "ok"
            def __iter__(self):
                return iter((True, "ok"))

        monkeypatch.setattr(dcg, "check_ai_send", lambda *a, **kw: _Gate())

        from workbench.core import ai_runner as ar

        class _FakeRunner:
            def __init__(self, **kw):
                self.kw = kw
            def run_async(self, wf, src):
                self.kw["on_flow_done"]()

        monkeypatch.setattr(ar, "AutoFlowRunner", _FakeRunner)

        api = _mk_api(proj)
        r = api.run_retrofit_preanalysis({"engineer": "Test Eng", "confirmed": True})
        assert r["ok"], r.get("msg")

        concat = (proj / "_raw" / "_preanalysis_legacy_concat.txt").read_text(
            encoding="utf-8")
        assert "UN E 2.0" in concat, "plain .awl must be included"
        assert "U E 9.9" in concat, "confirmed extracted text must be included"
        assert "listing.pdf (extracted text)" in concat
        assert concat.count("U E 9.9") == 1, (
            "extracted text must not be concatenated twice (pdf + sidecar)"
        )


class TestStep5NativeFiles:
    """STEP5 archive folders (real-world: 4711st.s5d + 4711Z0.SEQ + .INI).

    .SEQ symbol tables are near-text and carry the IO list gold (tag +
    German description); .s5d is binary MC5 program code that would poison
    a text LLM — it must be skipped LOUDLY with export instructions.
    """

    # Real STEP5 .SEQ record shape: control byte + fixed-width columns
    SEQ_SAMPLE = (
        b"\x1aE    4.0\x00E 4.0\x00KE HYDR.MOTOR NETZSCHUETZ\r\n"
        b"\x1aE    4.1\x00E 4.1\x00KE HYDR.MOTOR DREIECKS.\r\n"
        b"\x1aE    4.2\x00E 4.2\x00KE HYDR.MOTOR STERNSCHUETZ\r\n"
    ) * 20

    def _run_preanalysis(self, proj, monkeypatch):
        import data_classification_guard as dcg

        class _Gate:
            allowed = True
            reason = "ok"
            def __iter__(self):
                return iter((True, "ok"))

        monkeypatch.setattr(dcg, "check_ai_send", lambda *a, **kw: _Gate())
        from workbench.core import ai_runner as ar

        class _FakeRunner:
            def __init__(self, **kw):
                self.kw = kw
            def run_async(self, wf, src):
                self.kw["on_flow_done"]()

        monkeypatch.setattr(ar, "AutoFlowRunner", _FakeRunner)
        return _mk_api(proj).run_retrofit_preanalysis(
            {"engineer": "Test Eng", "confirmed": True})

    def test_seq_symbol_table_accepted_and_concatenated(self, tmp_path, monkeypatch):
        proj = _mk_project(tmp_path)
        lc = proj / "_raw" / "legacy_code"
        (lc / "4711Z0.SEQ").write_bytes(self.SEQ_SAMPLE)
        st = _mk_api(proj).get_raw_folder_status()
        assert "4711Z0.SEQ" in st["by_category"]["legacy_code"], (
            ".seq symbol tables must be accepted — they ARE the IO list")

        r = self._run_preanalysis(proj, monkeypatch)
        assert r["ok"], r.get("msg")
        concat = (proj / "_raw" / "_preanalysis_legacy_concat.txt").read_text(
            encoding="utf-8")
        assert "STERNSCHUETZ" in concat, "symbol descriptions must reach the AI"

    def test_binary_s5d_skipped_loudly_not_fed_to_ai(self, tmp_path, monkeypatch):
        proj = _mk_project(tmp_path)
        lc = proj / "_raw" / "legacy_code"
        # realistic MC5 binary: low printable ratio
        (lc / "4711st.s5d").write_bytes(bytes(range(256)) * 60)
        (lc / "code.awl").write_text("U E 1.0\n", encoding="utf-8")

        st = _mk_api(proj).get_raw_folder_status()
        assert "4711st.s5d" in st["by_category"]["legacy_code"], (
            ".s5d must be VISIBLE in the listing so the engineer knows it exists")

        r = self._run_preanalysis(proj, monkeypatch)
        assert r["ok"], r.get("msg")
        concat = (proj / "_raw" / "_preanalysis_legacy_concat.txt").read_text(
            encoding="utf-8", errors="strict")  # binary leak would explode here
        assert "4711st.s5d" not in concat, "binary program must NOT be concatenated"
        assert "U E 1.0" in concat
        warns = " ".join(w["msg"] for w in (r.get("_warnings") or []))
        assert "S5/S7 for Windows" in warns or "AWL" in warns, (
            "skip must be loud, with export instructions")
