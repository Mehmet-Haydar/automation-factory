"""Tests for AIClient.chat_with_files() — Gemini Vision multimodal."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "05_SCRIPTS"))

from ai_client import AIClient


def test_chat_with_files_raises_for_non_google():
    client = AIClient(provider="anthropic", api_key="sk-ant-test", model="claude-sonnet-4-6")
    with patch.object(client, "_lazy_init"):
        try:
            client.chat_with_files(system="s", user="u", files=[])
        except NotImplementedError as exc:
            assert "google" in str(exc).lower()
        else:
            raise AssertionError("Expected NotImplementedError")


def _make_google_mock(tmp_file: Path, response_text: str = "Extracted: 3 DI signals"):
    """Build a minimal google.genai mock without requiring the real package."""
    mock_genai = types.ModuleType("genai")
    mock_types = types.ModuleType("types")

    mock_client = MagicMock()
    mock_ufile = MagicMock()
    mock_ufile.uri = "gs://fake/file"
    mock_ufile.mime_type = "application/pdf"
    mock_ufile.name = "files/abc123"
    mock_client.files.upload.return_value = mock_ufile
    mock_client.models.generate_content_stream = None

    mock_response = MagicMock()
    mock_response.text = response_text
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 50
    mock_client.models.generate_content.return_value = mock_response

    class FakeUploadConfig:
        def __init__(self, **kw): pass
    class FakePart:
        @staticmethod
        def from_uri(file_uri, mime_type): return object()
        @staticmethod
        def from_text(text): return object()
    class FakeConfig:
        def __init__(self, **kw): pass

    mock_types.UploadFileConfig   = FakeUploadConfig
    mock_types.Part               = FakePart
    mock_types.GenerateContentConfig = FakeConfig
    mock_genai.Client             = lambda **kw: mock_client
    mock_genai.types              = mock_types

    return mock_client, mock_genai, mock_types


def test_chat_with_files_cleans_up_uploaded_files(tmp_path):
    """Uploaded files must be deleted from Google servers after the call."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"%PDF-1.4 fake content")

    mock_client, mock_genai, mock_types = _make_google_mock(test_file)

    google_module = types.ModuleType("google")
    google_module.genai = mock_genai

    with patch.dict(sys.modules, {"google": google_module, "google.genai": mock_genai, "google.genai.types": mock_types}):
        client = AIClient(provider="google", api_key="fake-key", model="gemini-2.5-pro")
        client._client = mock_client

        text, usage = client.chat_with_files(
            system="You are a PLC engineer",
            user="Extract IO signals",
            files=[test_file],
        )

    assert text == "Extracted: 3 DI signals"
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    mock_client.files.delete.assert_called_once_with(name="files/abc123")


def test_chat_with_files_cleanup_on_exception(tmp_path):
    """Files must be deleted even when the API call raises an exception."""
    test_file = tmp_path / "drawing.png"
    test_file.write_bytes(b"\x89PNG fake")

    mock_client, mock_genai, mock_types = _make_google_mock(test_file)
    mock_client.models.generate_content.side_effect = RuntimeError("API quota exceeded")

    google_module = types.ModuleType("google")
    google_module.genai = mock_genai

    with patch.dict(sys.modules, {"google": google_module, "google.genai": mock_genai, "google.genai.types": mock_types}):
        client = AIClient(provider="google", api_key="fake-key", model="gemini-2.5-pro")
        client._client = mock_client
        try:
            client.chat_with_files(system="s", user="u", files=[test_file])
        except RuntimeError:
            pass

    mock_client.files.delete.assert_called_once_with(name="files/abc123")


# ---------------------------------------------------------------------------
# AutoFlowRunner `usage` NameError fix — taşındı: test_ai_runner_usage.py
# ---------------------------------------------------------------------------

class TestAiRunnerUsage:
    """SCL step'te `usage` değişkeni bağlanmazsa NameError oluşurdu (regression guard)."""

    class _FakeUsage:
        truncated = True

    def _make_runner(self, project_root, on_warn):
        from workbench.core.ai_runner import AutoFlowRunner
        return AutoFlowRunner(
            provider="openai", model="test-model", api_key="sk-test",
            project_root=project_root,
            on_step_start=MagicMock(), on_step_chunk=MagicMock(),
            on_step_done=MagicMock(), on_flow_done=MagicMock(),
            on_error=MagicMock(), on_warn=on_warn,
        )

    def test_scl_step_does_not_raise_name_error(self, tmp_path):
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8"
        )
        source = tmp_path / "io.txt"
        source.write_text("DI0 Start\nDI1 Stop\n", encoding="utf-8")
        on_warn = MagicMock()
        runner = self._make_runner(tmp_path, on_warn)
        mock_client = MagicMock()
        mock_client.chat.return_value = (
            "```scl\nFUNCTION_BLOCK \"FB_Test\"\nBEGIN\n;\nEND_FUNCTION_BLOCK\n```",
            self._FakeUsage(),
        )
        with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
             patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
             patch("workbench.core.ai_runner.check_ai_send", return_value=(True, "PUBLIC")), \
             patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
             patch("workbench.core.ai_runner.AIClient", return_value=mock_client):
            runner._run("IO Extraction → SCL Generation", source)
        runner.on_error.assert_not_called()
        runner.on_flow_done.assert_called_once()
        assert on_warn.called, "truncation warning should fire for a truncated .scl step"
        assert any("SCL_TRUNCATION" in str(c.args[0]) for c in on_warn.call_args_list)
