"""S-5 (B-L9 + B-L13) — truncation must be visible for EVERY AI output.

The detection layer (ai_client UsageInfo.truncated) existed, but two
consumers ignored it:
- ai_runner warned only for code suffixes (.scl/.st/.awl) — RD02/RD03
  .md drafts were silently cut off on large legacy archives;
- the OCR path (legacy_pdf_extract.ocr_via_vision) never read the flag,
  and the multimodal client path never even set it.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# AutoFlowRunner — .md steps now warn too
# ---------------------------------------------------------------------------

class TestRunnerTruncationAllOutputs:
    def _make_runner(self, tmp_path):
        from workbench.core.ai_runner import AutoFlowRunner
        return AutoFlowRunner(
            provider="anthropic",
            model="test-model",
            api_key="sk-test",
            project_root=tmp_path,
            on_step_start=MagicMock(),
            on_step_chunk=MagicMock(),
            on_step_done=MagicMock(),
            on_flow_done=MagicMock(),
            on_error=MagicMock(),
            on_warn=MagicMock(),
        )

    def _run_truncated(self, tmp_path, workflow):
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8"
        )
        source = tmp_path / "input.awl"
        source.write_text("(*test*)", encoding="utf-8")
        usage = MagicMock()
        usage.truncated = True
        client = MagicMock()
        client.chat.return_value = ("# partial output", usage)
        runner = self._make_runner(tmp_path)
        with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
             patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
             patch("workbench.core.ai_runner.check_ai_send", return_value=(True, "ok")), \
             patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
             patch("workbench.core.ai_runner.AIClient", return_value=client):
            runner._run(workflow, source)
        return runner

    def test_md_step_truncation_warns(self, tmp_path):
        # "Analyze → Validate" produces .md output — the old suffix filter
        # suppressed this warning entirely.
        runner = self._run_truncated(tmp_path, "Analyze → Validate")
        warns = [c[0][0] for c in runner.on_warn.call_args_list]
        assert any("TRUNCATION" in w for w in warns), (
            f".md adımı kırpıldığında uyarı yok — eski sessiz mod geri gelmiş: {warns!r}")

    def test_no_warning_without_truncation(self, tmp_path):
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8"
        )
        source = tmp_path / "input.awl"
        source.write_text("(*test*)", encoding="utf-8")
        usage = MagicMock()
        usage.truncated = False
        client = MagicMock()
        client.chat.return_value = ("# complete", usage)
        runner = self._make_runner(tmp_path)
        with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
             patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
             patch("workbench.core.ai_runner.check_ai_send", return_value=(True, "ok")), \
             patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
             patch("workbench.core.ai_runner.AIClient", return_value=client):
            runner._run("Analyze → Validate", source)
        warns = [c[0][0] for c in runner.on_warn.call_args_list]
        assert not any("TRUNCATION" in w for w in warns)

    def test_truncation_check_has_no_suffix_filter(self):
        # Meta-guard: the truncation condition must not be re-narrowed to
        # code suffixes.
        from workbench.core import ai_runner
        src = inspect.getsource(ai_runner)
        for line in src.splitlines():
            if 'getattr(usage, "truncated"' in line and line.lstrip().startswith("if "):
                assert "_CODE_OUTPUT_SUFFIXES" not in line, (
                    "truncation uyarısı yine suffix'e daraltılmış: " + line.strip())
                break
        else:
            raise AssertionError("truncation kontrolü ai_runner'da bulunamadı")


# ---------------------------------------------------------------------------
# OCR path — flag is set, propagated and persisted
# ---------------------------------------------------------------------------

class _FakeVisionClient:
    def __init__(self, truncated):
        self._truncated = truncated

    def chat_with_files(self, **kw):
        return "L 0.0\nT 1.0", SimpleNamespace(truncated=self._truncated)


class TestOcrTruncation:
    def test_ocr_truncated_flag_propagates(self, tmp_path):
        from legacy_pdf_extract import ocr_via_vision
        pdf = tmp_path / "listing.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        res = ocr_via_vision(pdf, _FakeVisionClient(truncated=True), page_count=3)
        assert res.truncated is True

    def test_ocr_complete_flag_false(self, tmp_path):
        from legacy_pdf_extract import ocr_via_vision
        pdf = tmp_path / "listing.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        res = ocr_via_vision(pdf, _FakeVisionClient(truncated=False), page_count=3)
        assert res.truncated is False

    def test_truncated_persisted_to_meta(self, tmp_path):
        import json
        from legacy_pdf_extract import (ExtractionResult, QualityReport,
                                        extraction_paths, write_extraction)
        pdf = tmp_path / "listing.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        res = ExtractionResult(
            text="L 0.0", page_count=3, method="gemini_ocr",
            quality=QualityReport(chars_per_page=10, opcode_line_ratio=1.0,
                                  network_count=0, score=50, needs_ocr=False),
            truncated=True,
        )
        write_extraction(pdf, res)
        _txt, meta_path = extraction_paths(pdf)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["truncated"] is True, (
            "confirm ekranının okuduğu meta'da truncated izi yok")

    def test_extraction_result_defaults_not_truncated(self):
        # pdfplumber path never passes the flag — default must stay False.
        from legacy_pdf_extract import ExtractionResult, QualityReport
        res = ExtractionResult(
            text="x", page_count=1, method="pdfplumber",
            quality=QualityReport(1, 0, 0, 0, True))
        assert res.truncated is False


# ---------------------------------------------------------------------------
# Detection layer — multimodal client path sets the flag in BOTH SDK branches
# ---------------------------------------------------------------------------

class TestMultimodalDetectionLayer:
    def test_chat_with_files_sets_truncated_in_both_branches(self):
        import ai_client
        src = inspect.getsource(ai_client.AIClient._chat_google_with_files)
        assert src.count("usage.truncated = True") >= 2, (
            "multimodal yol (yeni + legacy SDK) MAX_TOKENS finish_reason'da "
            "usage.truncated set etmeli — OCR kırpılması yine görünmez olur")


# ---------------------------------------------------------------------------
# factory_web — the user-visible warning
# ---------------------------------------------------------------------------

class TestExtractWarnsOnTruncation:
    def test_source_warns_and_reports_truncated(self):
        fw = importlib.import_module("factory_web")
        src = inspect.getsource(fw.Api.extract_legacy_pdfs)
        assert "truncated" in src and "INCOMPLETE" in src, (
            "extract_legacy_pdfs kırpılmış OCR'ı kullanıcıya bildirmeli")
