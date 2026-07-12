"""
test_safety_checks.py

S-1 sınıfı proof testleri:

F-01 — generate_sequence_fb() çağrıldığında _rag_safety_check çağrılmalı ve
        rag_warnings/rag_mode response dict'ine eklenmelidir.

F-03 — ingest_device() çağrıldığında check_ai_send (data-classification guard)
        çağrılmalıdır; guard False döndürürse AI çağrısı gerçekleşmemeli,
        method early-return yapmalıdır (fail-closed).

Proof kuralı: fix geri alınırsa testler kırılmalıdır (smoke değil).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
for _p in (_ROOT, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# ---------------------------------------------------------------------------
# Ortak yardımcılar
# ---------------------------------------------------------------------------

def _make_api(project_root: Path | None = None) -> "factory_web.Api":
    """Minimal Api nesnesi — proje kök dizini isteğe bağlı."""
    import factory_web
    api = factory_web.Api()
    api.root = project_root
    api.settings = {
        "ai_provider": "anthropic",
        "ai_model": "claude-sonnet-4-6",
        "api_keys": {"anthropic": "sk-test-fake"},
    }
    return api


def _minimal_project(tmp_path: Path) -> Path:
    """generate_sequence_fb için gerekli minimum proje dosyaları."""
    (tmp_path / "PROJECT_STATE.json").write_text("{}", encoding="utf-8")
    (tmp_path / "PROJECT_MAESTRO.md").write_text(
        "---\nproject_name: Test\ndata_classification: PUBLIC\n---\n",
        encoding="utf-8",
    )
    # metadata dizini + RD03 taslağı
    meta = tmp_path / "metadata"
    meta.mkdir()
    (meta / "RD03_Flowchart.md").write_text(
        "# RD03\n\n| Step | Description |\n|------|-------------|\n| 1 | Start |\n",
        encoding="utf-8",
    )
    return tmp_path


# ===========================================================================
# F-01 — generate_sequence_fb: _rag_safety_check çağrılmalı
# ===========================================================================

class TestGenerateSequenceFbRagSafetyCheck:

    def test_rag_safety_check_is_called(self, tmp_path):
        """generate_sequence_fb çağrıldığında _rag_safety_check mutlaka çağrılmalı.

        Proof: Bu test fix olmadan geçmez — _rag_safety_check çağrısı koda
        eklenmeden önce 'call_count == 0' olur ve assert başarısız olur.
        """
        import factory_web

        project = _minimal_project(tmp_path)
        api = _make_api(project)

        _rag_calls: list[str] = []

        def fake_rag_safety_check(self_inner, query: str):
            _rag_calls.append(query)
            return [], "bm25"

        # ai_send_allowed: izin ver (guard bypass)
        fake_gate = MagicMock()
        fake_gate.allowed = True
        fake_gate.reason = ""
        fake_gate.requires_anonymization = False

        with patch.object(factory_web.Api, "_rag_safety_check", fake_rag_safety_check):
            with patch("factory_web.check_ai_send", return_value=fake_gate,
                       create=True):
                with patch("data_classification_guard.check_ai_send",
                           return_value=fake_gate):
                    # RD03 bulundu — şimdi AI çağrısını taklit et
                    with patch("ai_client.AIClient") as mock_ai_cls:
                        mock_client = MagicMock()
                        mock_client.chat.return_value = (
                            "FUNCTION_BLOCK FB_Seq_Test\nEND_FUNCTION_BLOCK\n", {}
                        )
                        mock_ai_cls.return_value = mock_client
                        with patch("factory_web._audit_log", return_value=None):
                            with patch("scl_validator.validate_scl_file") as mock_val:
                                mock_val.return_value = MagicMock(
                                    error_count=0, issues=[]
                                )
                                api.generate_sequence_fb()

        assert len(_rag_calls) >= 1, (
            "generate_sequence_fb _rag_safety_check'i HİÇ çağırmadı — "
            "S-1/F-01 fix eksik veya geri alındı."
        )

    def test_rag_warnings_in_response(self, tmp_path):
        """Uyarılar varsa response dict'te rag_warnings ve rag_mode anahtarları bulunmalı."""
        import factory_web

        project = _minimal_project(tmp_path)
        api = _make_api(project)

        sample_warning = {
            "entry_id": "KB-SAF-001",
            "severity": "critical(safety)",
            "chunk_text": "E-stop must be monitored.",
            "not_verified": True,
            "_rag_mode": "bm25",
            "_rag_fallback_reason": None,
        }

        def fake_rag_with_warnings(self_inner, query: str):
            return [sample_warning], "bm25"

        fake_gate = MagicMock()
        fake_gate.allowed = True
        fake_gate.reason = ""
        fake_gate.requires_anonymization = False

        with patch.object(factory_web.Api, "_rag_safety_check", fake_rag_with_warnings):
            with patch("data_classification_guard.check_ai_send",
                       return_value=fake_gate):
                with patch("ai_client.AIClient") as mock_ai_cls:
                    mock_client = MagicMock()
                    mock_client.chat.return_value = (
                        "FUNCTION_BLOCK FB_Seq_Test\nEND_FUNCTION_BLOCK\n", {}
                    )
                    mock_ai_cls.return_value = mock_client
                    with patch("factory_web._audit_log", return_value=None):
                        with patch("scl_validator.validate_scl_file") as mock_val:
                            mock_val.return_value = MagicMock(
                                error_count=0, issues=[]
                            )
                            result = api.generate_sequence_fb()

        assert "rag_warnings" in result, (
            "response dict'te 'rag_warnings' anahtarı yok — "
            "S-1/F-01 fix eksik ya da return dict güncellenmedi."
        )
        assert "rag_mode" in result, (
            "response dict'te 'rag_mode' anahtarı yok."
        )
        assert isinstance(result["rag_warnings"], list)
        assert result["rag_warnings"] == [sample_warning]
        assert result["rag_mode"] == "bm25"

    def test_rag_warnings_empty_list_when_no_hits(self, tmp_path):
        """Uyarı yoksa rag_warnings boş liste olmalı (None değil)."""
        import factory_web

        project = _minimal_project(tmp_path)
        api = _make_api(project)

        def fake_rag_no_hits(self_inner, query: str):
            return [], "bm25"

        fake_gate = MagicMock()
        fake_gate.allowed = True
        fake_gate.reason = ""
        fake_gate.requires_anonymization = False

        with patch.object(factory_web.Api, "_rag_safety_check", fake_rag_no_hits):
            with patch("data_classification_guard.check_ai_send",
                       return_value=fake_gate):
                with patch("ai_client.AIClient") as mock_ai_cls:
                    mock_client = MagicMock()
                    mock_client.chat.return_value = (
                        "FUNCTION_BLOCK FB_Seq_Test\nEND_FUNCTION_BLOCK\n", {}
                    )
                    mock_ai_cls.return_value = mock_client
                    with patch("factory_web._audit_log", return_value=None):
                        with patch("scl_validator.validate_scl_file") as mock_val:
                            mock_val.return_value = MagicMock(
                                error_count=0, issues=[]
                            )
                            result = api.generate_sequence_fb()

        assert result.get("rag_warnings") == [], (
            "Uyarı olmasa bile rag_warnings boş liste olmalı."
        )


# ===========================================================================
# F-03 — ingest_device: check_ai_send (data-classification guard) çağrılmalı
# ===========================================================================

_GOOD_DEVICE_MD = """\
# TestVendor TestModel — drives

## metadata
```yaml
schema_version: "1.0"
device_id: "TV_TESTMODEL"
vendor: "TestVendor"
model: "TestModel 1000"
category: "drives"
subcategory: "ac_drive"
part_number: "TV-1000"
datasheet_ref: "TestVendor TestModel Manual v1.0"
library_path: "drives/TestVendor/TestModel_1000.md"
last_verified: "2026-06"
```

## 1. General Info

| Field | Value |
|-------|-------|
| Full Name | TestVendor TestModel 1000 |

## 2. Communication Interfaces

| Interface | Protocol | Notes |
|-----------|----------|-------|
| PROFINET | IRT | Standard telegram 1 |
"""


def _make_ingest_pdf(tmp_path: Path) -> Path:
    """Test için minimal (stub) PDF dosyası oluşturur."""
    pdf = tmp_path / "device.pdf"
    pdf.write_bytes(b"%PDF-1.4 stub")
    return pdf


def _patch_pdf_read(mock_pdf, text: str = "Device technical data " * 10):
    """pdfplumber.open context manager mock'unu yapılandır."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = text
    ctx = MagicMock()
    ctx.__enter__ = lambda s: MagicMock(pages=[mock_page])
    ctx.__exit__ = MagicMock(return_value=False)
    mock_pdf.return_value = ctx


class TestIngestDeviceCheckAiSend:

    def test_check_ai_send_is_called(self, tmp_path):
        """ingest_device api_key resolve edildikten sonra check_ai_send çağırmalı.

        Proof: fix kaldırılırsa guard hiç çağrılmaz ve assert başarısız olur.
        """
        import factory_web

        pdf = _make_ingest_pdf(tmp_path)

        guard_calls: list = []

        fake_gate = MagicMock()
        fake_gate.allowed = True
        fake_gate.reason = ""

        def fake_check_ai_send(root, provider, settings, **kwargs):
            guard_calls.append((root, provider))
            return fake_gate

        with patch("factory_web.FACTORY_ROOT", tmp_path):
            hw_lib = tmp_path / "09_HARDWARE_LIBRARY"
            hw_lib.mkdir(exist_ok=True)
            prompt_file = hw_lib / "_PROMPT_DEVICE_SPEC_EXTRACT.md"
            prompt_file.write_text(
                "## SYSTEM PROMPT (give to the AI)\nExtract device.\n---\n"
                "## USER MESSAGE\n[PASTE PDF]\n",
                encoding="utf-8",
            )
            with patch("pdfplumber.open") as mock_pdf:
                _patch_pdf_read(mock_pdf)
                with patch(
                    "data_classification_guard.check_ai_send",
                    side_effect=fake_check_ai_send,
                ):
                    with patch("factory_web._audit_log", return_value=None):
                        with patch("ai_client.AIClient") as mock_ai_cls:
                            mock_ai_cls.return_value.chat.return_value = (
                                _GOOD_DEVICE_MD, {}
                            )
                            api = _make_api()
                            api.ingest_device(str(pdf))

        assert len(guard_calls) >= 1, (
            "ingest_device check_ai_send'i HİÇ çağırmadı — "
            "S-1/F-03 fix eksik veya geri alındı."
        )

    def test_check_ai_send_false_blocks_ai_call(self, tmp_path):
        """check_ai_send False (allowed=False) döndürürse AI çağrısı asla gerçekleşmemeli.

        Proof: fail-closed davranışını doğrular — guard False iken AIClient
        instantiate edilirse test hata verir.
        """
        import factory_web

        pdf = _make_ingest_pdf(tmp_path)

        blocked_gate = MagicMock()
        blocked_gate.allowed = False
        blocked_gate.reason = "TEST-BLOCKED: CONFIDENTIAL project"

        def fake_guard_deny(root, provider, settings, **kwargs):
            return blocked_gate

        with patch("factory_web.FACTORY_ROOT", tmp_path):
            hw_lib = tmp_path / "09_HARDWARE_LIBRARY"
            hw_lib.mkdir(exist_ok=True)
            prompt_file = hw_lib / "_PROMPT_DEVICE_SPEC_EXTRACT.md"
            prompt_file.write_text(
                "## SYSTEM PROMPT (give to the AI)\nExtract device.\n---\n"
                "## USER MESSAGE\n[PASTE PDF]\n",
                encoding="utf-8",
            )
            with patch("pdfplumber.open") as mock_pdf:
                _patch_pdf_read(mock_pdf)
                with patch(
                    "data_classification_guard.check_ai_send",
                    side_effect=fake_guard_deny,
                ):
                    with patch("factory_web._audit_log", return_value=None):
                        # AIClient çağrılırsa test kasıtlı olarak başarısız olur
                        def boom(*a, **kw):
                            raise AssertionError(
                                "ingest_device: AIClient check_ai_send guard "
                                "False döndürdükten sonra hâlâ çağrıldı — "
                                "S-1/F-03 fail-closed davranışı bozulmuş."
                            )

                        with patch("ai_client.AIClient", side_effect=boom):
                            api = _make_api()
                            result = api.ingest_device(str(pdf))

        assert result["ok"] is False, (
            "ingest_device guard reddi sonrası ok=True döndü — "
            "early-return eksik."
        )
        assert "C4" in result.get("msg", "") or "block" in result.get("msg", "").lower() or \
               "TEST-BLOCKED" in result.get("msg", ""), (
            f"Guard red mesajı response'a yansımadı: {result.get('msg')}"
        )

    def test_check_ai_send_false_early_return(self, tmp_path):
        """check_ai_send False döndürürse method erken dönmeli ve ok=False olmalı."""
        import factory_web

        pdf = _make_ingest_pdf(tmp_path)

        blocked_gate = MagicMock()
        blocked_gate.allowed = False
        blocked_gate.reason = "RESTRICTED project cannot send to public AI"

        with patch("factory_web.FACTORY_ROOT", tmp_path):
            hw_lib = tmp_path / "09_HARDWARE_LIBRARY"
            hw_lib.mkdir(exist_ok=True)
            prompt_file = hw_lib / "_PROMPT_DEVICE_SPEC_EXTRACT.md"
            prompt_file.write_text(
                "## SYSTEM PROMPT (give to the AI)\nExtract device.\n---\n"
                "## USER MESSAGE\n[PASTE PDF]\n",
                encoding="utf-8",
            )
            with patch("pdfplumber.open") as mock_pdf:
                _patch_pdf_read(mock_pdf)
                with patch(
                    "data_classification_guard.check_ai_send",
                    return_value=blocked_gate,
                ):
                    with patch("factory_web._audit_log", return_value=None):
                        with patch("ai_client.AIClient") as mock_ai_cls:
                            api = _make_api()
                            result = api.ingest_device(str(pdf))
                            # Guard False iken AIClient.chat HİÇ çağrılmamalı
                            assert mock_ai_cls.return_value.chat.call_count == 0, (
                                "ingest_device guard sonrası AIClient.chat çağrıldı — "
                                "fail-closed bozulmuş."
                            )

        assert result["ok"] is False
        assert result.get("msg"), "Guard red mesajı boş"
