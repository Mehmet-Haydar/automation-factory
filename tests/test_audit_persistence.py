"""tests/test_audit_persistence.py — S-4 / B-G4 compliance fix proof testleri.

SINIF S-4 (COMPLIANCE): AI_DECISION_LOG git-stage dışı + sessiz AuditLogError yutulması.

Kontrat:
  - Fix VARKEN  → tüm testler GEÇMELİ.
  - Fix GERİ ALINIRSA → davranışı koruyucu assert'ler KIRILMALI (smoke değil).

Kapsam:
  1. project_git.auto_commit_step — stage listesinde AI_DECISION_LOG.jsonl var.
  2. factory_web.confirm_extracted_text — AuditLogError yutulmuyor: _warn çağrılır,
     onay yine de işlenir (bloklanmaz).
  3. Meta-guard: factory_web.py + project_git.py içinde `except AuditLogError`
     bloklarının hiçbiri yalnız `pass` içermiyor.
"""

from __future__ import annotations

import ast
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "05_SCRIPTS"

for _p in (PROJECT_ROOT, SCRIPTS_DIR):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

# Stub out optional GUI/webview dependency before importing factory_web
for _mod in ("webview", "keyring"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import factory_web as fw  # noqa: E402
from factory_web import Api  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api(root: Path | None = None, settings: dict | None = None) -> Api:
    """Minimal Api nesnesi — pywebview gerektirmez."""
    api = object.__new__(Api)
    api.settings = settings or {}
    api.root = root
    return api


# ===========================================================================
# 1. project_git.auto_commit_step — stage listesi
# ===========================================================================

class TestAutoCommitStageList:
    """AI_DECISION_LOG.jsonl, auto_commit_step'in stage pattern listesinde bulunmalı."""

    def test_ai_decision_log_in_stage_patterns_source(self):
        """Kaynak-tarama: project_git.py'deki stage pattern listesi AI_DECISION_LOG.jsonl içermeli.

        Fix geri alınırsa ("AI_DECISION_LOG.jsonl" pattern listesinden çıkarılırsa) bu test
        kırılır ve log dosyası yedeksiz kalır.
        """
        source = (SCRIPTS_DIR / "project_git.py").read_text(encoding="utf-8")
        assert "AI_DECISION_LOG.jsonl" in source, (
            "project_git.py stage listesinde 'AI_DECISION_LOG.jsonl' bulunamadı — "
            "B-G4/S-4 fix geri alınmış: onay/karar geçmişi git geçmişine girmiyor."
        )

    def test_ai_decision_log_staged_in_auto_commit(self, tmp_path):
        """Davranışsal: auto_commit_step, AI_DECISION_LOG.jsonl dosyasını git add ile stage eder.

        tmp_path'da sahte bir git repo oluşturulur, log dosyası bırakılır,
        auto_commit_step çağrılır, ardından 'git add' çağrılarında log dosyasının
        geçip geçmediği doğrulanır.
        """
        # _run mock'unu kullanarak git çağrılarını yakala
        from project_git import auto_commit_step

        (tmp_path / ".git").mkdir()

        added_patterns: list[str] = []

        def fake_run(args: list, cwd, env_extra=None):
            if args and args[0] == "add":
                added_patterns.append(args[1])
                return True, ""
            if args and args[0] == "diff":
                # Staged değişiklik var gibi davran (commit tetiklensin)
                return True, "AI_DECISION_LOG.jsonl"
            if args and args[0] == "commit":
                return True, "mock-commit-sha"
            return True, ""

        # Dosyayı oluştur ki target.exists() True dönsün
        (tmp_path / "AI_DECISION_LOG.jsonl").write_text(
            '{"seq":1}\n', encoding="utf-8"
        )

        with patch("project_git._run", side_effect=fake_run):
            result = auto_commit_step(tmp_path, "test-step")

        assert "AI_DECISION_LOG.jsonl" in added_patterns, (
            f"auto_commit_step, AI_DECISION_LOG.jsonl'yi stage etmedi. "
            f"Stage edilen pattern'ler: {added_patterns!r}\n"
            "B-G4/S-4 fix geri alınmış olabilir."
        )

    def test_missing_log_file_does_not_break_commit(self, tmp_path):
        """AI_DECISION_LOG.jsonl yoksa auto_commit_step hata vermemeli (exists kontrolü).

        Log dosyası henüz oluşmamışsa auto_commit_step sessizce atlamalı.
        """
        from project_git import auto_commit_step

        (tmp_path / ".git").mkdir()

        def fake_run(args: list, cwd, env_extra=None):
            if args and args[0] == "add":
                return True, ""
            if args and args[0] == "diff":
                return True, ""  # staged değişiklik yok
            return True, ""

        with patch("project_git._run", side_effect=fake_run):
            result = auto_commit_step(tmp_path, "test-step-no-log")

        # Hata vermeden tamamlandı
        assert result is not None, "auto_commit_step None döndürmemeli"


# ===========================================================================
# 2. factory_web.confirm_extracted_text — AuditLogError yutulmuyor
# ===========================================================================

class TestConfirmExtractedTextAuditWarn:
    """AuditLogError fırlatıldığında _warn çağrılmalı, onay yine de işlenmeli."""

    def _setup_confirm(self, tmp_path: Path):
        """confirm_extracted_text için gerekli dosya yapısını hazırla."""
        raw_dir = tmp_path / "_raw" / "legacy_code"
        raw_dir.mkdir(parents=True)
        pdf_file = raw_dir / "test_legacy.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")
        return pdf_file

    def test_audit_log_error_triggers_warn_not_silent(self, tmp_path, caplog):
        """AuditLogError fırlatılınca _warn çağrılır (sessiz pass YOK).

        Fix geri alınırsa (except AuditLogError: pass haline gelirse)
        caplog'da compliance kategorisinde uyarı bulunamaz ve test kırılır.
        """
        from ai_decision_log import AuditLogError

        pdf_file = self._setup_confirm(tmp_path)
        api = _make_api(root=tmp_path)

        # Flush önceki buffer'ı temizle
        fw._flush_warnings()

        def raise_audit_error(*args, **kwargs):
            raise AuditLogError("disk full simulation")

        def fake_confirm_extraction(pdf_path, edited_text):
            return {"extracted": "dummy text", "status": "ok"}

        with patch("factory_web._audit_log", side_effect=raise_audit_error), \
             patch("factory_web.Api.confirm_extracted_text.__module__"):
            pass  # module-level patch, no-op

        # legacy_pdf_extract.confirm_extraction mock
        mock_legacy = MagicMock()
        mock_legacy.confirm_extraction = fake_confirm_extraction

        with patch.dict(sys.modules, {"legacy_pdf_extract": mock_legacy}), \
             patch("factory_web._audit_log", side_effect=raise_audit_error), \
             caplog.at_level(logging.WARNING, logger="factory_web"):
            result = api.confirm_extracted_text("test_legacy.pdf")

        # Uyarı logger'a yazılmış olmalı (compliance kategorisi)
        warn_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("audit log write failed" in m.lower() or "not recorded" in m.lower()
                   for m in warn_messages), (
            f"AuditLogError sessizce yutulmuş: compliance uyarısı logger'a yazılmamış.\n"
            f"Log kayıtları: {warn_messages!r}\n"
            "B-G4/S-4 fix geri alınmış: 'except AuditLogError: pass' hâlâ aktif."
        )

    def test_audit_log_error_warning_in_response(self, tmp_path):
        """AuditLogError fırlatılınca yanıt dict'inde _warnings listesi uyarı içermeli.

        _warn() çağrıldığında _attach_warnings() bunu response'a ekler;
        fix geri alınırsa _warnings listesi boş olur.
        """
        from ai_decision_log import AuditLogError

        pdf_file = self._setup_confirm(tmp_path)
        api = _make_api(root=tmp_path)

        fw._flush_warnings()

        def raise_audit_error(*args, **kwargs):
            raise AuditLogError("permission denied simulation")

        def fake_confirm_extraction(pdf_path, edited_text):
            return {"extracted": "ok", "status": "confirmed"}

        mock_legacy = MagicMock()
        mock_legacy.confirm_extraction = fake_confirm_extraction

        with patch.dict(sys.modules, {"legacy_pdf_extract": mock_legacy}), \
             patch("factory_web._audit_log", side_effect=raise_audit_error):
            result = api.confirm_extracted_text("test_legacy.pdf")

        assert "_warnings" in result, (
            "confirm_extracted_text yanıtında '_warnings' anahtarı yok — "
            "_attach_warnings() çağrılmıyor olabilir."
        )
        warning_msgs = [w.get("msg", "") for w in result.get("_warnings", [])]
        assert any("audit log write failed" in m.lower() or "not recorded" in m.lower()
                   for m in warning_msgs), (
            f"_warnings listesinde compliance uyarısı bulunamadı: {warning_msgs!r}\n"
            "Fix geri alınmış olabilir — AuditLogError sessizce yutulmuş."
        )

    def test_confirmation_still_succeeds_on_audit_error(self, tmp_path):
        """AuditLogError durumunda onay işlemi yine de ok=True dönmeli (bloklanmaz).

        Audit yazma hatası onayı bloklamamalı — sadece kullanıcı uyarılır.
        Fix bu dengeyi bozmamalı.
        """
        from ai_decision_log import AuditLogError

        pdf_file = self._setup_confirm(tmp_path)
        api = _make_api(root=tmp_path)

        fw._flush_warnings()

        def raise_audit_error(*args, **kwargs):
            raise AuditLogError("network timeout simulation")

        def fake_confirm_extraction(pdf_path, edited_text):
            return {"extracted": "ok", "status": "confirmed"}

        mock_legacy = MagicMock()
        mock_legacy.confirm_extraction = fake_confirm_extraction

        with patch.dict(sys.modules, {"legacy_pdf_extract": mock_legacy}), \
             patch("factory_web._audit_log", side_effect=raise_audit_error):
            result = api.confirm_extracted_text("test_legacy.pdf")

        assert result.get("ok") is True, (
            f"AuditLogError durumunda onay bloklandı: {result!r}\n"
            "confirm_extracted_text AuditLogError'da ok=True dönmeli (davranış değişmemeli)."
        )

    def test_audit_warn_has_compliance_category(self, tmp_path):
        """_warn() 'compliance' kategorisiyle çağrılmalı.

        Kategori hem log kaydını hem de UI filtresini etkiler.
        Fix geri alınırsa kategori bulunamaz veya uyarı hiç çıkmaz.
        """
        from ai_decision_log import AuditLogError

        pdf_file = self._setup_confirm(tmp_path)
        api = _make_api(root=tmp_path)

        fw._flush_warnings()

        def raise_audit_error(*args, **kwargs):
            raise AuditLogError("category test")

        def fake_confirm_extraction(pdf_path, edited_text):
            return {"extracted": "ok"}

        mock_legacy = MagicMock()
        mock_legacy.confirm_extraction = fake_confirm_extraction

        with patch.dict(sys.modules, {"legacy_pdf_extract": mock_legacy}), \
             patch("factory_web._audit_log", side_effect=raise_audit_error):
            result = api.confirm_extracted_text("test_legacy.pdf")

        # _warnings listesinde compliance kategorisi olmalı
        warnings = result.get("_warnings", [])
        categories = [w.get("category", "") for w in warnings]
        assert "compliance" in categories, (
            f"Beklenen kategori 'compliance', bulunan: {categories!r}\n"
            "B-G4/S-4: _warn() compliance kategorisiyle çağrılmalı."
        )


# ===========================================================================
# 3. Meta-guard: `except AuditLogError` bloklarında yalnız `pass` yok
# ===========================================================================

class TestNoSilentAuditLogErrorPass:
    """factory_web.py ve project_git.py'de except AuditLogError: pass kombinasyonu olmadığını
    kaynak kodu analizi ile doğrular.

    AST tabanlı analiz kullanılır: pass-only except bloğu tespit edilir.
    Bu test fix geri alındığında (pass bloğu eklenmesi) hemen kırılır.
    """

    TARGET_FILES = [
        SCRIPTS_DIR / "factory_web.py",
        SCRIPTS_DIR / "project_git.py",
    ]

    def _find_silent_audit_excepts(self, filepath: Path) -> list[str]:
        """AST analizi: AuditLogError yakalan ve yalnız pass içeren except bloklarını bul."""
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
        violations: list[str] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.Try, ast.TryStar)):
                continue
            for handler in getattr(node, "handlers", []):
                # Handler tipi AuditLogError mi?
                handler_type = handler.type
                is_audit_error = False
                if isinstance(handler_type, ast.Name):
                    is_audit_error = handler_type.id == "AuditLogError"
                elif isinstance(handler_type, ast.Attribute):
                    is_audit_error = handler_type.attr == "AuditLogError"

                if not is_audit_error:
                    continue

                # Gövde yalnızca pass mi?
                body = handler.body
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    violations.append(
                        f"{filepath.name}:{handler.lineno} — "
                        f"'except AuditLogError: pass' (sessiz yutma)"
                    )

        return violations

    def test_no_silent_pass_in_factory_web(self):
        """factory_web.py'de except AuditLogError: pass bulunmamalı."""
        violations = self._find_silent_audit_excepts(SCRIPTS_DIR / "factory_web.py")
        assert violations == [], (
            "factory_web.py'de sessiz AuditLogError yakaları bulundu:\n" +
            "\n".join(violations) + "\n"
            "B-G4/S-4 fix geri alınmış — audit hataları sessizce yutuluyordur."
        )

    def test_no_silent_pass_in_project_git(self):
        """project_git.py'de except AuditLogError: pass bulunmamalı."""
        violations = self._find_silent_audit_excepts(SCRIPTS_DIR / "project_git.py")
        assert violations == [], (
            "project_git.py'de sessiz AuditLogError yakaları bulundu:\n" +
            "\n".join(violations) + "\n"
            "B-G4/S-4 fix geri alınmış — audit hataları sessizce yutuluyordur."
        )

    def test_audit_log_error_catch_count_factory_web(self):
        """factory_web.py'de tüm AuditLogError yakaları sayılır ve hepsi non-silent olmalı.

        Sayım: toplam except AuditLogError blok sayısı bilgi amaçlı loglanır.
        """
        source = (SCRIPTS_DIR / "factory_web.py").read_text(encoding="utf-8")
        # Basit metin taraması: except AuditLogError satır sayısı
        lines = source.splitlines()
        catch_lines = [
            (i + 1, line.strip())
            for i, line in enumerate(lines)
            if "except AuditLogError" in line
        ]
        # Bunların hiçbirinin sonraki satırı yalnız 'pass' olmamalı (AST testi zaten doğruluyor)
        # Bu test sayımı bilgi olarak raporlar ve sıfır olmamalı (en az 1 catch var)
        assert len(catch_lines) >= 1, (
            "factory_web.py'de hiç 'except AuditLogError' bulunamadı — "
            "audit hata yönetimi tamamen kaldırılmış olabilir."
        )
