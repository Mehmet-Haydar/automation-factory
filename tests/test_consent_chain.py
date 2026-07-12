"""B-L3 / B-G1 / B-G2 — Consent zinciri tutarsızlığı proof testi.

Kapsam:
  1. CONFIDENTIAL + consent verilmiş → AutoFlowRunner guard'dan GEÇER, adım çalışır.
  2. CONFIDENTIAL + consent YOK     → runner bloklar (on_error IP_LEAKAGE mesajı taşır).
  3. RESTRICTED + consent verilmiş  → HER ZAMAN bloklar (fail-closed kanıtı).
  4. Kaynak-tarama guard: ai_runner.py içindeki HER check_ai_send çağrısı
     consent_confirmed ilettiğini kaynak koddan assert eder (meta-guard).

Fix varken: GEÇMELİ.
Fix geri alınırsa (consent_confirmed kaldırılırsa): KIRILMALI.
"""

from __future__ import annotations

import inspect
import re
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _make_runner(project_root: Path, provider: str = "anthropic",
                 consent_confirmed: bool = False):
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
        consent_confirmed=consent_confirmed,
    )


def _run_sync(runner, workflow_name: str, source_file: Path) -> None:
    """_run'u ana thread'de (sync) çalıştırır; daemon thread beklemez."""
    runner._run(workflow_name, source_file)


def _make_source(tmp_path: Path) -> Path:
    src = tmp_path / "test.txt"
    src.write_text("legacy code content", encoding="utf-8")
    return src


# ---------------------------------------------------------------------------
# Test 1: CONFIDENTIAL + consent verilmiş → guard'dan geçer, adım çalışır
# ---------------------------------------------------------------------------

def test_confidential_consent_confirmed_passes_guard(tmp_path):
    """CONFIDENTIAL proje + mühendis onayı → check_ai_send consent_confirmed=True
    ile çağrılmalı ve runner adımı çalıştırmalı (on_error çağrılmamalı)."""
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: CONFIDENTIAL\n---\n", encoding="utf-8"
    )
    source = _make_source(tmp_path)

    runner = _make_runner(tmp_path, provider="anthropic", consent_confirmed=True)

    mock_client = MagicMock()
    mock_client.chat.return_value = ("AI response text", {})

    with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
         patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
         patch("workbench.core.ai_runner.check_ai_send",
               return_value=(True, "CONFIDENTIAL — consent geçti")) as mock_guard, \
         patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
         patch("workbench.core.ai_runner.AIClient", return_value=mock_client):

        _run_sync(runner, "Analyze → Validate", source)

    # guard consent_confirmed=True ile çağrılmalı
    call_kwargs = mock_guard.call_args[1] if mock_guard.call_args else {}
    assert call_kwargs.get("consent_confirmed") is True, (
        f"check_ai_send consent_confirmed=True ile çağrılmadı. "
        f"Gerçek kwargs: {call_kwargs!r} — "
        f"consent_confirmed runner.__init__'ten _run()'a iletilmiyor."
    )

    # on_error çağrılmamalı (guard geçti)
    runner.on_error.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: CONFIDENTIAL + consent YOK → bloklar, IP_LEAKAGE mesajı verir
# ---------------------------------------------------------------------------

def test_confidential_no_consent_blocks_runner(tmp_path):
    """CONFIDENTIAL proje + consent=False (default) → runner bloklanmalı,
    on_error mesajında IP_LEAKAGE veya CONFIDENTIAL geçmeli."""
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\ndata_classification: CONFIDENTIAL\n---\n", encoding="utf-8"
    )
    source = _make_source(tmp_path)

    # consent_confirmed=False (fail-safe default)
    runner = _make_runner(tmp_path, provider="anthropic", consent_confirmed=False)

    with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
         patch("workbench.core.ai_runner.CLASSIFICATION_GUARD_AVAILABLE", True), \
         patch("workbench.core.ai_runner.check_ai_send",
               return_value=(False, "CONFIDENTIAL — onaysız bloklandı")) as mock_guard, \
         patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
         patch("workbench.core.ai_runner.AIClient") as mock_client_cls:

        _run_sync(runner, "Analyze → Validate", source)

    # guard consent_confirmed=False ile çağrılmalı
    call_kwargs = mock_guard.call_args[1] if mock_guard.call_args else {}
    assert call_kwargs.get("consent_confirmed") is False, (
        f"check_ai_send consent_confirmed=False bekleniyor, gelen: {call_kwargs!r}"
    )

    # on_error çağrıldı mı?
    runner.on_error.assert_called_once()
    error_msg = runner.on_error.call_args[0][0]
    assert ("IP_LEAKAGE" in error_msg or "CONFIDENTIAL" in error_msg or
            "classification" in error_msg.lower()), (
        f"on_error mesajı beklenen içeriği taşımıyor: {error_msg!r}"
    )

    # AIClient hiç çağrılmamalı
    mock_client_cls.assert_not_called()

    # on_flow_done çağrılmamalı
    runner.on_flow_done.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: RESTRICTED + consent verilmiş → HER ZAMAN bloklar (fail-closed)
# ---------------------------------------------------------------------------

def test_restricted_consent_has_no_effect(tmp_path):
    """RESTRICTED sınıfta consent=True olsa bile runner bloklanmalı.
    check_ai_send RESTRICTED için requires_consent=False döner (always blocked),
    consent_confirmed'in RESTRICTED'ı açmaması fail-closed kanıtıdır."""
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"data_classification": "RESTRICTED"}', encoding="utf-8"
    )
    source = _make_source(tmp_path)

    # consent_confirmed=True versen bile RESTRICTED geçemez
    runner = _make_runner(tmp_path, provider="anthropic", consent_confirmed=True)

    with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
         patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
         patch("workbench.core.ai_runner.AIClient") as mock_client_cls:
        # Gerçek check_ai_send kullanılıyor (CLASSIFICATION_GUARD_AVAILABLE=gerçek)
        _run_sync(runner, "Analyze → Validate", source)

    # RESTRICTED hiçbir koşulda geçemez
    runner.on_error.assert_called_once()
    error_msg = runner.on_error.call_args[0][0]
    assert ("IP_LEAKAGE" in error_msg or "RESTRICTED" in error_msg or
            "blocked" in error_msg.lower() or "classification" in error_msg.lower()), (
        f"RESTRICTED blok mesajı bekleniyor: {error_msg!r}"
    )

    # AIClient hiç çağrılmamalı
    mock_client_cls.assert_not_called()

    # on_flow_done çağrılmamalı
    runner.on_flow_done.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Kaynak tarama guard (meta-test)
# — ai_runner.py içindeki HER check_ai_send çağrısı consent_confirmed iletmeli
# ---------------------------------------------------------------------------

def test_all_check_ai_send_calls_forward_consent_confirmed():
    """ai_runner.py içindeki HER check_ai_send(...) çağrısı consent_confirmed
    keyword argümanını iletmelidir. Bu meta-guard, ileride eklenen yeni çağrı
    noktalarının consent zincirini kırmadığını otomatik olarak yakalar.

    Fix geri alınırsa (consent_confirmed= kaldırılırsa) bu test KIRILIR.
    """
    from workbench.core import ai_runner
    src = inspect.getsource(ai_runner)

    # Tüm check_ai_send( çağrısı bloklarını bul.
    # Pattern: check_ai_send( ... ) — çok satırlı olabilir.
    # Basit yaklaşım: her check_ai_send( başlayan blok için sonraki 5 satırı kontrol et.
    call_pattern = re.compile(r"check_ai_send\s*\(", re.MULTILINE)
    lines = src.splitlines()

    violations: list[str] = []
    for i, line in enumerate(lines):
        if "check_ai_send(" in line or "check_ai_send (" in line:
            # Bu satırdan itibaren 8 satırı birleştir (çok satırlı çağrı kapsamı)
            block = "\n".join(lines[i:i+8])
            if "consent_confirmed" not in block:
                violations.append(f"Satır ~{i+1}: {line.strip()!r}")

    assert not violations, (
        "ai_runner.py içindeki şu check_ai_send çağrıları consent_confirmed "
        "iletmiyor (B-L3/B-G1/B-G2 zinciri kırık):\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Test 5: runner.__init__ consent_confirmed'i saklamalı
# ---------------------------------------------------------------------------

def test_runner_stores_consent_confirmed(tmp_path):
    """AutoFlowRunner.__init__ consent_confirmed parametresini self.consent_confirmed
    olarak saklamalıdır (varsayılan False)."""
    from workbench.core.ai_runner import AutoFlowRunner

    runner_false = AutoFlowRunner(
        provider="anthropic", model="m", api_key="k",
        project_root=tmp_path,
        on_step_start=MagicMock(), on_step_chunk=MagicMock(),
        on_step_done=MagicMock(), on_flow_done=MagicMock(),
        on_error=MagicMock(),
    )
    assert runner_false.consent_confirmed is False, (
        "Varsayılan consent_confirmed False olmalı (fail-safe default)."
    )

    runner_true = AutoFlowRunner(
        provider="anthropic", model="m", api_key="k",
        project_root=tmp_path,
        on_step_start=MagicMock(), on_step_chunk=MagicMock(),
        on_step_done=MagicMock(), on_flow_done=MagicMock(),
        on_error=MagicMock(),
        consent_confirmed=True,
    )
    assert runner_true.consent_confirmed is True, (
        "consent_confirmed=True iletilince self.consent_confirmed True olmalı."
    )


# ---------------------------------------------------------------------------
# Test 6: factory_web run_retrofit_preanalysis consent_confirmed'i runner'a iletmeli
# — Kaynak tarama meta-guard
# ---------------------------------------------------------------------------

def test_factory_web_preanalysis_runner_gets_consent_confirmed():
    """factory_web.py'deki run_retrofit_preanalysis; AutoFlowRunner'ı kurarken
    consent_confirmed= keyword argümanını açıkça geçmelidir.

    Fix geri alınırsa (consent_confirmed= satırı kaldırılırsa) bu test KIRILIR.
    """
    import factory_web as fw
    import ast

    src = inspect.getsource(fw)
    tree = ast.parse(src)

    api_cls = next(
        n for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == "Api"
    )
    method_node = next(
        (n for n in api_cls.body
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
         and n.name == "run_retrofit_preanalysis"),
        None,
    )
    assert method_node is not None, (
        "run_retrofit_preanalysis metodu factory_web.Api'de bulunamadı."
    )

    method_src = ast.get_source_segment(src, method_node) or ""

    # AutoFlowRunner çağrısı consent_confirmed= içermeli
    assert "consent_confirmed=" in method_src, (
        "run_retrofit_preanalysis içindeki AutoFlowRunner(...) çağrısı "
        "consent_confirmed= parametresini iletmiyor — B-L3/B-G1 zinciri kırık."
    )

    # Hardcode True bırakılmamış olmalı (gerçek onaydan türetilmeli)
    # "consent_confirmed=True" sabit ifadesi olmamalı; değişken olmalı
    assert "consent_confirmed=True" not in method_src, (
        "run_retrofit_preanalysis içinde consent_confirmed=True hardcode "
        "hâlâ duruyor — B-G2 fix geri alınmış."
    )
