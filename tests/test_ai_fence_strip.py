"""K-1 — _strip_code_fence proof testi.

Düzeltme: ai_runner._strip_code_fence(), LLM'in .scl çıktısına sardığı
markdown çitlerini temizlemelidir. .md çıktıları etkilenmemeli.

Fix varken GEÇMELİ — fix geri alınırsa (fence temizleme kaldırılırsa) KIRILMALI.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _strip_code_fence — birim testleri
# ---------------------------------------------------------------------------

class TestStripCodeFence:

    def _fn(self):
        from workbench.core.ai_runner import _strip_code_fence
        return _strip_code_fence

    def test_no_fence_returns_text_stripped(self):
        """Çit yoksa metin (strip sonrası) olduğu gibi döner."""
        fn = self._fn()
        code = "FUNCTION_BLOCK FB_Motor\nVAR\nEND_VAR\nEND_FUNCTION_BLOCK"
        assert fn(code) == code

    def test_scl_fence_extracted(self):
        """```scl ... ``` çiti çıkarılır, yalnızca kod kalır."""
        fn = self._fn()
        raw = "```scl\nFUNCTION_BLOCK FB_Test\nEND_FUNCTION_BLOCK\n```"
        result = fn(raw)
        assert result == "FUNCTION_BLOCK FB_Test\nEND_FUNCTION_BLOCK"
        assert "```" not in result

    def test_generic_fence_extracted(self):
        """Lang etiketi olmayan ``` ... ``` çiti de temizlenir."""
        fn = self._fn()
        raw = "```\nFUNCTION_BLOCK FB_X\nEND_FUNCTION_BLOCK\n```"
        result = fn(raw)
        assert "```" not in result
        assert "FUNCTION_BLOCK FB_X" in result

    def test_iec_fence_extracted(self):
        """```iec ve ```st etiketleri de desteklenir."""
        fn = self._fn()
        for lang in ("iec", "st", "IEC61131"):
            raw = f"```{lang}\nFUNCTION_BLOCK FB_X\nEND_FUNCTION_BLOCK\n```"
            result = fn(raw)
            assert "```" not in result, f"lang={lang}: çit temizlenmedi"
            assert "FUNCTION_BLOCK FB_X" in result

    def test_prose_before_fence_discarded(self):
        """Çitten önce gelen düzyazı açıklama atılır, yalnızca kod döner."""
        fn = self._fn()
        raw = (
            "Here is the generated SCL code:\n\n"
            "```scl\n"
            "FUNCTION_BLOCK FB_Motor\n"
            "VAR\n"
            "END_VAR\n"
            "END_FUNCTION_BLOCK\n"
            "```\n\n"
            "The code is IEC 61131-3 compliant."
        )
        result = fn(raw)
        assert "```" not in result
        assert "Here is" not in result
        assert "IEC 61131-3" not in result
        assert "FUNCTION_BLOCK FB_Motor" in result
        assert "END_FUNCTION_BLOCK" in result

    def test_multiline_scl_body_preserved(self):
        """Çok satırlı SCL gövdesi eksiksiz korunur."""
        fn = self._fn()
        body = (
            "FUNCTION_BLOCK FB_Motor\n"
            "VAR_INPUT\n"
            "    in_bStart : BOOL;\n"
            "END_VAR\n"
            "VAR_OUTPUT\n"
            "    out_bRun : BOOL;\n"
            "END_VAR\n"
            "BEGIN\n"
            "    out_bRun := in_bStart;\n"
            "END_FUNCTION_BLOCK"
        )
        raw = f"```scl\n{body}\n```"
        assert fn(raw) == body

    def test_incomplete_fence_returns_original(self):
        """Kapanış çiti olmayan yanıt orijinal halini korur (truncated LLM çıktısı)."""
        fn = self._fn()
        raw = "```scl\nFUNCTION_BLOCK FB_X\n"  # kapanış yok
        result = fn(raw)
        # Kapanış çiti yoksa metnin tamamı döner (strip edilmiş)
        assert "FUNCTION_BLOCK" in result

    def test_windows_crlf_fence_extracted(self):
        """Windows CRLF satır sonları (\\r\\n) olan çit temizlenir."""
        fn = self._fn()
        raw = "```scl\r\nFUNCTION_BLOCK FB_X\r\nEND_FUNCTION_BLOCK\r\n```"
        result = fn(raw)
        assert "```" not in result
        assert "FUNCTION_BLOCK FB_X" in result


# ---------------------------------------------------------------------------
# AutoFlowRunner entegrasyon: .scl çıktılar temizlenir, .md dokunulmaz
# ---------------------------------------------------------------------------

class TestAutoFlowFenceStripping:

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

    def test_scl_output_has_no_fence(self, tmp_path):
        """.scl adım çıktısı diske fence olmadan yazılmalı."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8"
        )
        source = tmp_path / "input.awl"
        source.write_text("(*test*)", encoding="utf-8")

        fenced_scl = "```scl\nFUNCTION_BLOCK FB_Test\nEND_FUNCTION_BLOCK\n```"
        mock_usage = MagicMock()
        mock_usage.truncated = False
        mock_client = MagicMock()
        mock_client.chat.return_value = (fenced_scl, mock_usage)

        runner = self._make_runner(tmp_path)

        with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
             patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
             patch("workbench.core.ai_runner.check_ai_send", return_value=(True, "ok")), \
             patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
             patch("workbench.core.ai_runner.AIClient", return_value=mock_client):
            runner._run("IO Extraction → SCL Generation", source)

        # REPORTS dizininde .scl dosyası yazıldı mı?
        scl_files = list((tmp_path / "REPORTS").rglob("*.scl"))
        assert scl_files, "REPORTS/ altında .scl dosyası bulunamadı"

        content = scl_files[0].read_text(encoding="utf-8")
        assert "```" not in content, f".scl dosyasında markdown çiti kaldı: {content!r}"
        assert "FUNCTION_BLOCK FB_Test" in content

    def test_md_output_not_stripped(self, tmp_path):
        """.md adım çıktısı fence içeriyorsa olduğu gibi korunur."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8"
        )
        source = tmp_path / "input.awl"
        source.write_text("(*test*)", encoding="utf-8")

        md_with_fence = "# Analysis\n\n```scl\nsome_code\n```\n\nSee above."
        mock_usage = MagicMock()
        mock_usage.truncated = False
        mock_client = MagicMock()
        mock_client.chat.return_value = (md_with_fence, mock_usage)

        runner = self._make_runner(tmp_path)

        with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
             patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
             patch("workbench.core.ai_runner.check_ai_send", return_value=(True, "ok")), \
             patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
             patch("workbench.core.ai_runner.AIClient", return_value=mock_client):
            runner._run("Analyze → Validate", source)

        md_files = list((tmp_path / "REPORTS").rglob("*.md"))
        assert md_files, "REPORTS/ altında .md dosyası bulunamadı"

        content = md_files[0].read_text(encoding="utf-8")
        # .md çıktısında fence korunmalı
        assert "```scl" in content, f".md dosyasından fence hatalı silindi: {content!r}"

    def test_truncation_warning_emitted(self, tmp_path):
        """SCL adımı truncated=True döndürürse on_warn çağrılmalı."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8"
        )
        source = tmp_path / "input.awl"
        source.write_text("(*test*)", encoding="utf-8")

        truncated_usage = MagicMock()
        truncated_usage.truncated = True
        mock_client = MagicMock()
        mock_client.chat.return_value = ("FUNCTION_BLOCK FB_X\nEND_FUNCTION_BLOCK", truncated_usage)

        runner = self._make_runner(tmp_path)

        with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
             patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
             patch("workbench.core.ai_runner.check_ai_send", return_value=(True, "ok")), \
             patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
             patch("workbench.core.ai_runner.AIClient", return_value=mock_client):
            runner._run("IO Extraction → SCL Generation", source)

        runner.on_warn.assert_called()
        warn_msg = runner.on_warn.call_args[0][0]
        assert "SCL_TRUNCATION" in warn_msg or "truncat" in warn_msg.lower(), (
            f"Truncation uyarısı bekleniyor: {warn_msg!r}"
        )
