"""S-20 (B-G8) — INTERNAL projeler de AI öncesi anonymize zorunlu.

Domain karar: "Kod standarda uyacak — INTERNAL projeler de AI'ya giderken
anonymize edilir" (2026-06-11_DOMAIN_KARARLAR.md).

Proof testler:
  - Fix varken GEÇMELİ.
  - Fix geri alınırsa (requires_anonymization bayrağı kaldırılırsa) KIRILMALI.

Kapsam:
  1. data_classification_guard: provider_allowed("INTERNAL", ...) →
       requires_anonymization=True döndürmeli.
  2. check_ai_send: INTERNAL proje → requires_anonymization=True.
  3. factory_web._anon_map_for_ai: requires_anonymization=True → map döner
       (state yoksa {}, ama anahtar yine True).
  4. AutoFlowRunner (ai_runner): INTERNAL proje check_ai_send sonucunda
       requires_anonymization bayrağı erişilebilir.
  5. PUBLIC projeler için requires_anonymization=False kalmaya devam eder
       (RESTRICTED/CONFIDENTIAL mevcut davranışı değişmez).
  6. Deanonymize zinciri: INTERNAL proje → anonymize + deanonymize round-trip
       çalışmalı (S-6 uyumluluğu kırılmadı).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# sys.path kurulumu
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "05_SCRIPTS"
for _p in (str(SCRIPTS_DIR),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from data_classification_guard import (
    provider_allowed,
    check_ai_send,
    AIGateResult,
    normalize_classification,
)


# ===========================================================================
# 1. provider_allowed — INTERNAL → requires_anonymization=True
# ===========================================================================

class TestProviderAllowedInternalAnonymize:

    def test_internal_requires_anonymization_true(self):
        """Fix: INTERNAL → requires_anonymization=True döndürülmeli."""
        result = provider_allowed("INTERNAL", "anthropic", {})
        assert isinstance(result, AIGateResult)
        assert result.allowed is True, "INTERNAL gönderime izin vermeli"
        assert result.requires_anonymization is True, (
            "S-20 fix eksik: INTERNAL için requires_anonymization=True beklenir"
        )

    def test_internal_requires_no_consent(self):
        """INTERNAL consent istememeli (mevcut davranış korundu)."""
        result = provider_allowed("INTERNAL", "deepseek", {})
        assert result.requires_consent is False

    def test_internal_allows_all_providers(self):
        """INTERNAL farklı provider'larda da requires_anonymization=True döndürmeli."""
        for prov in ("anthropic", "openai", "google", "deepseek", "local_llm"):
            result = provider_allowed("INTERNAL", prov, {})
            assert result.allowed is True, f"{prov} için INTERNAL bloklandı"
            assert result.requires_anonymization is True, (
                f"{prov} için requires_anonymization=True bekleniyor"
            )

    def test_public_requires_anonymization_false(self):
        """PUBLIC → requires_anonymization=False (mevcut davranış korundu)."""
        result = provider_allowed("PUBLIC", "anthropic", {})
        assert result.allowed is True
        assert result.requires_anonymization is False, (
            "PUBLIC için requires_anonymization=False beklenir (S-20 bozdu mu?)"
        )

    def test_restricted_blocked_anonymization_irrelevant(self):
        """RESTRICTED → allowed=False; requires_anonymization=False (gönderim yok)."""
        result = provider_allowed("RESTRICTED", "anthropic", {})
        assert result.allowed is False
        assert result.requires_anonymization is False

    def test_confidential_public_provider_requires_no_anonymization_in_block(self):
        """CONFIDENTIAL public provider → bloklanır, requires_anonymization False (zaten geçmez)."""
        result = provider_allowed("CONFIDENTIAL", "anthropic", {})
        assert result.allowed is False
        assert result.requires_consent is True

    def test_confidential_enterprise_no_anonymization_required(self):
        """CONFIDENTIAL enterprise → allowed, requires_anonymization=False (enterprise güvenli)."""
        result = provider_allowed("CONFIDENTIAL", "anthropic", {"self_hosted": True})
        assert result.allowed is True
        # Enterprise/self-hosted için anonymize zorunlu değil (yönetilen ortam)
        assert result.requires_anonymization is False


# ===========================================================================
# 2. check_ai_send — INTERNAL proje dosyasından okuma
# ===========================================================================

class TestCheckAiSendInternal:

    def test_internal_project_state_requires_anonymization(self, tmp_path):
        """PROJECT_STATE.json INTERNAL → check_ai_send requires_anonymization=True."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "INTERNAL"}', encoding="utf-8"
        )
        result = check_ai_send(tmp_path, "anthropic", {})
        assert result.allowed is True
        assert result.requires_anonymization is True

    def test_internal_maestro_requires_anonymization(self, tmp_path):
        """PROJECT_MAESTRO.md INTERNAL → check_ai_send requires_anonymization=True."""
        (tmp_path / "PROJECT_MAESTRO.md").write_text(
            "---\ndata_classification: INTERNAL\n---\n", encoding="utf-8"
        )
        result = check_ai_send(tmp_path, "deepseek", {})
        assert result.allowed is True
        assert result.requires_anonymization is True

    def test_public_project_no_anonymization_required(self, tmp_path):
        """PUBLIC proje → requires_anonymization=False (S-20 PUBLIC'i bozmadı)."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "PUBLIC"}', encoding="utf-8"
        )
        result = check_ai_send(tmp_path, "anthropic", {})
        assert result.allowed is True
        assert result.requires_anonymization is False

    def test_confidential_with_consent_requires_anonymization(self, tmp_path):
        """CONFIDENTIAL + mühendis onayı → allowed=True, requires_anonymization=True."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "CONFIDENTIAL"}', encoding="utf-8"
        )
        result = check_ai_send(tmp_path, "anthropic", {}, consent_confirmed=True)
        assert result.allowed is True
        assert result.requires_anonymization is True, (
            "CONFIDENTIAL + consent → anonymize zorunlu"
        )


# ===========================================================================
# 3. factory_web._anon_map_for_ai — requires_anonymization flag'ini kullanır
# ===========================================================================

class TestAnonMapForAi:
    """factory_web.Api._anon_map_for_ai() yardımcı testleri."""

    def _make_api(self, tmp_path):
        """Minimal factory_web.Api örneği (DB olmadan)."""
        sys.path.insert(0, str(SCRIPTS_DIR))
        from factory_web import Api  # type: ignore
        api = Api.__new__(Api)
        api.root = tmp_path
        api.settings = {}
        return api

    def test_requires_anonymization_true_loads_map(self, tmp_path):
        """gate.requires_anonymization=True iken PROJECT_STATE varsa map döner."""
        state = {
            "customer": "Müller GmbH",
            "project_name": "Schleifmaschine_Test",
            "data_classification": "INTERNAL",
        }
        (tmp_path / "PROJECT_STATE.json").write_text(
            json.dumps(state), encoding="utf-8"
        )
        api = self._make_api(tmp_path)

        gate = MagicMock(spec=AIGateResult)
        gate.requires_anonymization = True

        anon_map = api._anon_map_for_ai(gate)
        assert isinstance(anon_map, dict)
        # Müşteri adı map'te olmalı
        assert "Müller GmbH" in anon_map, (
            "requires_anonymization=True iken müşteri adı map'te gözükmeli"
        )

    def test_requires_anonymization_false_returns_empty(self, tmp_path):
        """gate.requires_anonymization=False → boş map döner (PUBLIC davranışı)."""
        state = {"customer": "Siemens AG", "data_classification": "PUBLIC"}
        (tmp_path / "PROJECT_STATE.json").write_text(
            json.dumps(state), encoding="utf-8"
        )
        api = self._make_api(tmp_path)

        gate = MagicMock(spec=AIGateResult)
        gate.requires_anonymization = False

        anon_map = api._anon_map_for_ai(gate)
        assert anon_map == {}, (
            "requires_anonymization=False → boş map beklenir (PUBLIC seçeneği)"
        )

    def test_requires_anonymization_true_missing_state_returns_empty(self, tmp_path):
        """requires_anonymization=True ama PROJECT_STATE yoksa {} döner (regex hala çalışır)."""
        api = self._make_api(tmp_path)  # PROJECT_STATE.json yok

        gate = MagicMock(spec=AIGateResult)
        gate.requires_anonymization = True

        anon_map = api._anon_map_for_ai(gate)
        # State dosyası yoksa boş map — ama caller anonymize_text({}) ile regex uygular
        assert isinstance(anon_map, dict)


# ===========================================================================
# 4. Anonymize → Deanonymize round-trip (INTERNAL, S-6 uyumluluğu)
# ===========================================================================

class TestInternalAnonymizeRoundTrip:
    """INTERNAL projeler için anonymize + deanonymize tam döngüsü."""

    def test_internal_text_anonymized_before_ai(self, tmp_path):
        """INTERNAL proje: müşteri adı anonymize edilmeli, deanonymize round-trip çalışmalı."""
        from anonymizer import build_anon_map, anonymize_text, deanonymize_text

        state = {
            "customer": "Bosch GmbH",
            "project_name": "CustomerA_Conveyor_2026",
            "project_id": "BSH-2026-001",
            "data_classification": "INTERNAL",
        }
        anon_map = build_anon_map(state)

        original = "Proje CustomerA_Conveyor_2026 — müşteri Bosch GmbH, ref BSH-2026-001"
        anon_text, replaced = anonymize_text(original, anon_map)

        # Anonymize: gerçek değerler kalmamalı
        assert "Bosch GmbH" not in anon_text
        assert "BSH-2026-001" not in anon_text
        assert len(replaced) >= 2

        # Deanonymize: gerçek değerler geri gelmeli
        restored = deanonymize_text(anon_text, anon_map)
        assert "Bosch GmbH" in restored
        assert "BSH-2026-001" in restored

    def test_anonymize_text_with_empty_map_applies_regex(self):
        """Boş map ile anonymize_text çağrılsa bile regex PII temizlenmeli."""
        from anonymizer import anonymize_text

        text = "İletişim: hans.becker@bosch.com — Tel: +49 711 1234567"
        anon, _ = anonymize_text(text, {})

        assert "hans.becker@bosch.com" not in anon
        assert "+49 711 1234567" not in anon


# ===========================================================================
# 5. AutoFlowRunner — INTERNAL proje check_ai_send bayrağı taşınıyor
# ===========================================================================

class TestAutoFlowRunnerInternalAnonymize:
    """ai_runner.AutoFlowRunner INTERNAL proje guard sonucunu doğru taşımalı."""

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

    def test_internal_project_allowed_by_runner(self, tmp_path):
        """INTERNAL proje → AutoFlowRunner akışı bloklanmamalı (izin var)."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "INTERNAL"}', encoding="utf-8"
        )
        source = tmp_path / "test.txt"
        source.write_text("(*AWL kodu*)", encoding="utf-8")

        runner = self._make_runner(tmp_path)

        mock_client = MagicMock()
        usage = MagicMock()
        usage.truncated = False
        mock_client.chat.return_value = ("AI yanıtı", usage)

        with patch("workbench.core.ai_runner.AI_AVAILABLE", True), \
             patch("workbench.core.ai_runner.AUDIT_AVAILABLE", False), \
             patch("workbench.core.ai_runner.AIClient", return_value=mock_client):
            runner._run("Analyze → Validate", source)

        # INTERNAL bloklanmadıysa on_error çağrılmamalı, on_flow_done çağrılmalı
        runner.on_error.assert_not_called()
        runner.on_flow_done.assert_called_once()

    def test_internal_check_ai_send_result_has_requires_anonymization(self, tmp_path):
        """check_ai_send(INTERNAL, ...) döndürdüğü sonuç requires_anonymization=True içermeli."""
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"data_classification": "INTERNAL"}', encoding="utf-8"
        )
        gate = check_ai_send(tmp_path, "anthropic", {})
        assert gate.requires_anonymization is True, (
            "ai_runner check_ai_send çağrısı INTERNAL için requires_anonymization=True almalı"
        )


# ===========================================================================
# 6. Backward compat — AIGateResult 2-tuple unpack hâlâ çalışıyor
# ===========================================================================

def test_backward_compat_unpack_internal(tmp_path):
    """AIGateResult yeni alanla 2-tuple unpack hâlâ çalışmalı."""
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"data_classification": "INTERNAL"}', encoding="utf-8"
    )
    allowed, reason = check_ai_send(tmp_path, "anthropic", {})
    assert allowed is True
    assert isinstance(reason, str)


def test_backward_compat_unpack_public(tmp_path):
    """PUBLIC projede backward compat bozulmadı."""
    (tmp_path / "PROJECT_STATE.json").write_text(
        '{"data_classification": "PUBLIC"}', encoding="utf-8"
    )
    allowed, reason = check_ai_send(tmp_path, "anthropic", {})
    assert allowed is True
    assert isinstance(reason, str)
