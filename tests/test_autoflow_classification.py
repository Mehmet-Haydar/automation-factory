"""I-2 — AutoFlowRunner classification guard fix proof testi.

Koruma: _run() data_classification_guard.check_ai_send() sonucuna göre
fail-closed davranmalıdır.

Fix varken GEÇMELİ — fix geri alınırsa (guard çağrısı kaldırılırsa)
KIRILMALI.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _make_runner(project_root: Path, provider: str = "anthropic"):
    """AutoFlowRunner örneği; tüm callback'leri MagicMock olarak bağlar."""
    from workbench.core.ai_runner import AutoFlowRunner

    return AutoFlowRunner(
        provider=provider,
        model="test-model",
        api_key="sk-test",
        project_root=project_root,
        on_step_start=MagicMock(),
        on_step_chunk=MagicMock(),
        on_step_done=MagicMock(),
        on_flow_done=MagicMock(),
        on_error=MagicMock(),
    )


def _run_sync(runner, workflow_name: str, source_file: Path):
    """_run'u ana thread'de (sync) çalıştırır; threading.Thread'i beklemez."""
    runner._run(workflow_name, source_file)


# ---------------------------------------------------------------------------
# Test 1: CONFIDENTIAL proje + public provider → bloklanmalı, on_error çağrılmalı
# ---------------------------------------------------------------------------

def test_confidential_project_blocks_autoflow(tmp_path):
    """CONFIDENTIAL proje verisi public AI sağlayıcısına gönderilemez."""
    # CONFIDENTIAL proje oluştur
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: CONFIDENTIAL\n---\n", encoding="utf-8"
    )
    source = tmp_path / "test.txt"
    source.write_text("some content", encoding="utf-8")

    runner = _make_runner(tmp_path, provider="anthropic")

    # ai_client ve audit log'u mock'la — guard bloklarsa bunlara ulaşılmamalı
    with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
         patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
         patch("workbench.core.ai_runner.check_ai_send", return_value=(False, "CONFIDENTIAL — blok")) as mock_guard, \
         patch("workbench.core.ai_runner.AIClient") as mock_client_cls:

        _run_sync(runner, "Analyze → Validate", source)

    # Guard çağrıldı mı?
    mock_guard.assert_called_once()

    # on_error çağrıldı mı?
    runner.on_error.assert_called_once()
    error_msg = runner.on_error.call_args[0][0]
    assert "IP_LEAKAGE" in error_msg or "sınıflandırma" in error_msg.lower() or "blok" in error_msg.lower(), (
        f"on_error mesajı beklenen içeriği taşımıyor: {error_msg!r}"
    )

    # AIClient hiç oluşturulmamalı (API çağrısı yapılmamalı)
    mock_client_cls.assert_not_called()

    # on_flow_done çağrılmamalı
    runner.on_flow_done.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: PUBLIC proje + public provider → guard geçer, akış devam eder
# ---------------------------------------------------------------------------

def test_public_project_allows_autoflow(tmp_path):
    """PUBLIC proje verisi public AI sağlayıcısına gönderilebilir."""
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"data_classification": "PUBLIC"}', encoding="utf-8"
    )
    source = tmp_path / "test.txt"
    source.write_text("some content", encoding="utf-8")

    runner = _make_runner(tmp_path, provider="openai")

    mock_client = MagicMock()
    mock_client.chat.return_value = ("result text", {})

    with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
         patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
         patch("workbench.core.ai_runner.check_ai_send", return_value=(True, "PUBLIC — izin var")) as mock_guard, \
         patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
         patch("workbench.core.ai_runner.AIClient", return_value=mock_client):

        _run_sync(runner, "Analyze → Validate", source)

    mock_guard.assert_called_once()
    # on_error çağrılmamalı
    runner.on_error.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: Guard modülü yüklenemedi → fail-closed, bloklanmalı
# ---------------------------------------------------------------------------

def test_guard_unavailable_is_fail_closed(tmp_path):
    """Guard modülü import edilemezse fail-closed: workflow bloklanmalı."""
    source = tmp_path / "test.txt"
    source.write_text("some content", encoding="utf-8")

    runner = _make_runner(tmp_path, provider="openai")

    with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
         patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", False), \
         patch("workbench.core.ai_runner.AIClient") as mock_client_cls:

        _run_sync(runner, "Analyze → Validate", source)

    runner.on_error.assert_called_once()
    error_msg = runner.on_error.call_args[0][0]
    assert "fail-closed" in error_msg.lower() or "yüklenemedi" in error_msg.lower(), (
        f"on_error fail-closed mesajı bekleniyor: {error_msg!r}"
    )
    mock_client_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: RESTRICTED proje → mutlaka bloklanmalı
# ---------------------------------------------------------------------------

def test_restricted_project_always_blocked(tmp_path):
    """RESTRICTED proje verisi hiçbir AI sağlayıcısına gönderilemez."""
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"data_classification": "RESTRICTED"}', encoding="utf-8"
    )
    source = tmp_path / "test.txt"
    source.write_text("secret content", encoding="utf-8")

    runner = _make_runner(tmp_path, provider="openai")

    # Gerçek check_ai_send'i kullan (mock değil)
    from workbench.core.ai_runner import CLASSIFICATION_GUARD_AVAILABLE

    with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
         patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
         patch("workbench.core.ai_runner.AIClient") as mock_client_cls:

        _run_sync(runner, "Analyze → Validate", source)

    runner.on_error.assert_called_once()
    mock_client_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: Guard False döndürürken AuditLog kaydı yazılmalı
# ---------------------------------------------------------------------------

def test_blocked_flow_writes_audit_log(tmp_path):
    """Classification guard bloklaması AuditLog'a 'BLOCKED' kaydı düşürmeli."""
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: CONFIDENTIAL\n---\n", encoding="utf-8"
    )
    source = tmp_path / "test.txt"
    source.write_text("content", encoding="utf-8")

    runner = _make_runner(tmp_path, provider="anthropic")

    mock_log = MagicMock()

    with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
         patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
         patch("workbench.core.ai_runner.check_ai_send", return_value=(False, "CONFIDENTIAL — blok")), \
         patch("workbench.core.ai_runner.AUDIT_AVAILABLE", True), \
         patch("workbench.core.ai_runner.log_ai_action", mock_log):

        _run_sync(runner, "Analyze → Validate", source)

    # Audit log çağrıldı mı?
    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args[1] if mock_log.call_args[1] else {}
    call_args = mock_log.call_args[0] if mock_log.call_args[0] else ()
    # prompt_id'de BLOCKED geçmeli
    prompt_id_val = call_kwargs.get("prompt_id", "")
    assert "BLOCKED" in prompt_id_val, (
        f"Audit log prompt_id'de BLOCKED bekleniyor: {prompt_id_val!r}"
    )
