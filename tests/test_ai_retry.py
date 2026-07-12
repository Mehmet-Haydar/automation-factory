"""K-3 — AIClient retry/backoff proof testi.

Düzeltme: _is_retryable() geçici API hatalarını (429, 503, overloaded) tanımalı.
_with_retry() bu hatalarda exponential backoff ile yeniden denemeli; kalıcı
hatalarda (auth, bad request) hemen fırlatmalı.

Fix varken GEÇMELİ — fix geri alınırsa KIRILMALI.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _is_retryable — birim testleri
# ---------------------------------------------------------------------------

class TestIsRetryable:

    def _fn(self):
        from ai_client import _is_retryable
        return _is_retryable

    # ---- 429 / rate-limit ----

    def test_429_status_code_attr_retryable(self):
        fn = self._fn()
        exc = Exception("request failed")
        exc.status_code = 429
        assert fn(exc) is True

    def test_503_status_code_attr_retryable(self):
        fn = self._fn()
        exc = Exception("service unavailable")
        exc.status_code = 503
        assert fn(exc) is True

    def test_529_overloaded_retryable(self):
        """Anthropic 529 overloaded should be retried."""
        fn = self._fn()
        exc = Exception("overloaded")
        exc.status_code = 529
        assert fn(exc) is True

    def test_rate_limit_phrase_retryable(self):
        fn = self._fn()
        assert fn(Exception("Rate limit exceeded")) is True

    def test_too_many_requests_phrase_retryable(self):
        fn = self._fn()
        assert fn(Exception("Too many requests — please slow down")) is True

    def test_service_unavailable_phrase_retryable(self):
        fn = self._fn()
        assert fn(Exception("503 Service Unavailable")) is True

    def test_resource_exhausted_phrase_retryable(self):
        fn = self._fn()
        assert fn(Exception("RESOURCE_EXHAUSTED: quota exceeded")) is True

    def test_high_demand_phrase_retryable(self):
        fn = self._fn()
        assert fn(Exception("high demand — try again later")) is True

    # ---- Kalıcı hatalar — retry yapılmamalı ----

    def test_401_auth_not_retryable(self):
        fn = self._fn()
        exc = Exception("Unauthorized")
        exc.status_code = 401
        assert fn(exc) is False

    def test_400_bad_request_not_retryable(self):
        fn = self._fn()
        exc = Exception("Invalid model name")
        exc.status_code = 400
        assert fn(exc) is False

    def test_value_error_not_retryable(self):
        fn = self._fn()
        assert fn(ValueError("invalid input")) is False

    def test_import_error_not_retryable(self):
        fn = self._fn()
        assert fn(ImportError("missing package")) is False

    def test_generic_runtime_error_not_retryable(self):
        fn = self._fn()
        assert fn(RuntimeError("something went wrong")) is False


# ---------------------------------------------------------------------------
# _with_retry — davranış testleri
# ---------------------------------------------------------------------------

class TestWithRetry:

    def _fn(self):
        from ai_client import _with_retry
        return _with_retry

    def test_success_on_first_attempt(self):
        """İlk denemede başarı → retry yok, sonuç döner."""
        _with_retry = self._fn()
        fn = MagicMock(return_value="ok")
        result = _with_retry(fn, max_retries=3, base_delay=0)
        assert result == "ok"
        assert fn.call_count == 1

    def test_retryable_error_then_success(self):
        """Geçici hata → retry → başarı."""
        _with_retry = self._fn()

        transient = Exception("503 Service Unavailable")
        transient.status_code = 503

        fn = MagicMock(side_effect=[transient, transient, "ok"])
        result = _with_retry(fn, max_retries=3, base_delay=0)
        assert result == "ok"
        assert fn.call_count == 3

    def test_max_retries_exhausted_raises(self):
        """max_retries kadar retry sonrası hâlâ başarısız → hata fırlatılır."""
        _with_retry = self._fn()

        transient = Exception("rate limit")
        fn = MagicMock(side_effect=transient)

        with pytest.raises(Exception, match="rate limit"):
            _with_retry(fn, max_retries=2, base_delay=0)

        assert fn.call_count == 3  # initial + 2 retries

    def test_non_retryable_raises_immediately(self):
        """Kalıcı hata → hiç retry yapmadan hemen fırlatılır."""
        _with_retry = self._fn()

        permanent = ValueError("bad input")
        fn = MagicMock(side_effect=permanent)

        with pytest.raises(ValueError, match="bad input"):
            _with_retry(fn, max_retries=3, base_delay=0)

        assert fn.call_count == 1  # sadece bir kez denendi

    def test_backoff_timing(self):
        """Retry aralarında time.sleep doğru argümanla çağrılır."""
        _with_retry = self._fn()

        transient = Exception("503 Service Unavailable")
        transient.status_code = 503
        fn = MagicMock(side_effect=[transient, transient, "ok"])

        with patch("ai_client.time.sleep") as mock_sleep:
            result = _with_retry(fn, max_retries=3, base_delay=2.0)

        assert result == "ok"
        # İlk bekleme: 2^0 * 2.0 = 2s; ikinci: 2^1 * 2.0 = 4s
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert sleep_calls == [2.0, 4.0], f"Bekleme süreleri yanlış: {sleep_calls}"

    def test_retryable_raises_after_all_attempts(self):
        """Tüm retry'lar başarısız olursa son exception yükseltilir."""
        _with_retry = self._fn()

        err = Exception("overloaded")
        fn = MagicMock(side_effect=err)

        with pytest.raises(Exception, match="overloaded"):
            _with_retry(fn, max_retries=1, base_delay=0)


# ---------------------------------------------------------------------------
# UsageInfo.truncated — alan varlık testi
# ---------------------------------------------------------------------------

def test_usage_info_has_truncated_field():
    """UsageInfo.truncated alanı mevcut ve default False olmalı."""
    from ai_client import UsageInfo
    u = UsageInfo()
    assert hasattr(u, "truncated"), "UsageInfo'da 'truncated' alanı yok"
    assert u.truncated is False

def test_usage_info_to_dict_includes_truncated():
    """to_dict() çıktısı 'truncated' anahtarını içermeli."""
    from ai_client import UsageInfo
    u = UsageInfo(truncated=True)
    d = u.to_dict()
    assert "truncated" in d, f"to_dict() 'truncated' içermiyor: {d}"
    assert d["truncated"] is True

def test_usage_info_str_shows_truncated():
    """__str__() truncated=True olduğunda [TRUNCATED] göstermeli."""
    from ai_client import UsageInfo
    u = UsageInfo(truncated=True)
    assert "TRUNCATED" in str(u), f"str() TRUNCATED içermiyor: {str(u)!r}"

def test_usage_info_str_normal_no_truncated():
    """__str__() truncated=False olduğunda [TRUNCATED] göstermemeli."""
    from ai_client import UsageInfo
    u = UsageInfo(truncated=False)
    assert "TRUNCATED" not in str(u)


# ---------------------------------------------------------------------------
# WorkflowStep.max_tokens — alan varlık ve SCL adımları değer testi
# ---------------------------------------------------------------------------

def test_workflow_step_has_max_tokens_field():
    """WorkflowStep.max_tokens alanı mevcut ve default 16384 olmalı
    (4× 2026-07-07 — AI client sağlayıcı tavanına kırpar)."""
    from workbench.core.ai_runner import WorkflowStep
    step = WorkflowStep(name="test", prompt_template="x", output_suffix=".md")
    assert hasattr(step, "max_tokens"), "WorkflowStep'te 'max_tokens' alanı yok"
    assert step.max_tokens == 16384

def test_builtin_scl_steps_have_higher_max_tokens():
    """SCL üretim adımları 4096'dan yüksek max_tokens değerine sahip olmalı."""
    from workbench.core.ai_runner import BUILTIN_WORKFLOWS
    scl_generating_workflows = [
        "IO Extraction → SCL Generation",
        "Full Pipeline",
    ]
    for wf_name in scl_generating_workflows:
        steps = BUILTIN_WORKFLOWS[wf_name]
        for step in steps:
            if step.output_suffix.endswith(".scl"):
                assert step.max_tokens > 4096, (
                    f"Workflow '{wf_name}', step '{step.name}': "
                    f"max_tokens={step.max_tokens} — SCL adımı için 4096'dan büyük olmalı"
                )

def test_code_output_suffixes_contains_scl():
    """_CODE_OUTPUT_SUFFIXES .scl, .st, .awl içermeli."""
    from workbench.core.ai_runner import _CODE_OUTPUT_SUFFIXES
    assert ".scl" in _CODE_OUTPUT_SUFFIXES
    assert ".st" in _CODE_OUTPUT_SUFFIXES
    assert ".awl" in _CODE_OUTPUT_SUFFIXES
    assert ".md" not in _CODE_OUTPUT_SUFFIXES
