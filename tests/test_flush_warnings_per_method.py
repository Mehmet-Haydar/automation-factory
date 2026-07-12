"""R-O-1 — _flush_warnings() Tek Çağrı Noktasına Bağlı: proof testleri.

Bu testler:
  - Fix VARKEN geçmeli.
  - Fix GERİ ALINIRSA (_attach_warnings() çağrısı ilgili metoddan kaldırılırsa)
    ya da _attach_warnings() yardımcısı silinirse KIRILMALI.

Kapsam:
  1. _attach_warnings() yardımcısı — biriktirilen uyarıları dönülen dict'e ekler,
     buffer'ı temizler.
  2. validate_io_list() — _project_state() çağrısı içerdiğinden get_state()
     çağrılmadan uyarı görülmeli.
  3. get_dashboard() — _project_state() çağrısı içerdiğinden get_state()
     çağrılmadan uyarı görülmeli.
  4. get_report() — _project_state() çağrısı içerdiğinden get_state()
     çağrılmadan uyarı görülmeli.
  5. get_gate_history() — _project_state() çağrısı içerdiğinden get_state()
     çağrılmadan uyarı görülmeli.
  6. advance_gate() — _project_state() çağrısı içerdiğinden get_state()
     çağrılmadan uyarı görülmeli.
  7. get_gate_model() — _project_state() çağrısı içerdiğinden get_state()
     çağrılmadan uyarı görülmeli.
  8. get_file_context() — _project_state() çağrısı içerdiğinden get_state()
     çağrılmadan uyarı görülmeli.
  9. Buffer çift flush durumunda (aynı uyarı iki kez) aynı uyarı iki kez
     dönülmemeli (buffer ikinci flushta boş olmalı).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "05_SCRIPTS"

for _p in (PROJECT_ROOT, SCRIPTS_DIR):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api(tmp_path: Path):
    """Minimal Api nesnesi — pywebview gerektirmez."""
    import factory_web as fw
    api = object.__new__(fw.Api)
    api.settings = {}
    api.root = tmp_path
    return api, fw


def _bad_state(tmp_path: Path) -> None:
    """tmp_path'a bozuk PROJECT_STATE.json yaz."""
    (tmp_path / "PROJECT_STATE.json").write_text("{broken json!!!", encoding="utf-8")


def _good_state(tmp_path: Path, gate: int = 2) -> None:
    """tmp_path'a geçerli PROJECT_STATE.json yaz."""
    import json
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": gate}), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# 1. _attach_warnings() yardımcısı
# ---------------------------------------------------------------------------

class TestAttachWarnings:

    def test_attach_warnings_function_exists(self):
        """_attach_warnings() factory_web modülünde tanımlı olmalı."""
        import factory_web as fw
        assert hasattr(fw, "_attach_warnings"), (
            "_attach_warnings() factory_web'de bulunamadı — "
            "R-O-1 fix uygulanmamış ya da geri alınmış"
        )

    def test_flush_empty_buffer_gives_empty_list(self, tmp_path):
        """Buffer boşken _attach_warnings() '_warnings': [] ekler."""
        import factory_web as fw
        fw._flush_warnings()  # önceki test artığı temizle
        result = fw._attach_warnings({"ok": True})
        assert "_warnings" in result
        assert result["_warnings"] == []

    def test_flush_with_pending_warning(self, tmp_path):
        """Buffer'da uyarı varken _attach_warnings() onu taşır ve buffer'ı temizler."""
        import factory_web as fw
        fw._flush_warnings()  # temizle
        fw._warn("test uyarisi", category="test")
        result = fw._attach_warnings({"ok": True})
        assert len(result["_warnings"]) == 1
        assert result["_warnings"][0]["msg"] == "test uyarisi"
        # Sonraki flush boş olmalı (buffer temizlenmiş)
        assert fw._flush_warnings() == []

    def test_double_flush_no_duplicate(self, tmp_path):
        """Aynı uyarı iki kez dönülmemeli — buffer ikinci flushta boş."""
        import factory_web as fw
        fw._flush_warnings()
        fw._warn("tek uyari", category="test")
        first = fw._attach_warnings({"x": 1})
        second = fw._attach_warnings({"x": 2})
        assert len(first["_warnings"]) == 1
        assert len(second["_warnings"]) == 0, (
            "Buffer ikinci flush'ta boş olmalı — "
            "aynı uyarı iki kez dönülmüş (çift flush sorunu)"
        )

    def test_existing_warnings_key_merged(self, tmp_path):
        """Yanıtta zaten '_warnings' varsa yeni uyarılar birleştirilir."""
        import factory_web as fw
        fw._flush_warnings()
        fw._warn("yeni uyari", category="test")
        result = fw._attach_warnings({"_warnings": [{"msg": "onceki", "category": "old"}]})
        assert len(result["_warnings"]) == 2
        msgs = [w["msg"] for w in result["_warnings"]]
        assert "onceki" in msgs
        assert "yeni uyari" in msgs


# ---------------------------------------------------------------------------
# 2. validate_io_list() — get_state() olmadan uyarı görülmeli
# ---------------------------------------------------------------------------

class TestValidateIoListWarnings:

    def test_warnings_in_response_without_get_state(self, tmp_path, monkeypatch):
        """validate_io_list() bozuk PROJECT_STATE.json varken '_warnings' içermeli.

        Bu test fix GERİ ALINIRSA KIRILIR: _attach_warnings() çağrısı
        validate_io_list()'den kaldırılırsa '_warnings' anahtarı olmaz.
        """
        import factory_web as fw
        _bad_state(tmp_path)
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()

        # io_list_io modülü yoksa test atlanır (entegrasyon değil birim test)
        io_md = tmp_path / "RD01_IO_LIST.md"
        io_md.write_text("# IO List\n\n| Tag | Address |\n| T1 | I0.0 |\n", encoding="utf-8")

        # validate_rows stub
        def _stub_validate_rows(rows, platform):
            return []

        monkeypatch.setattr(fw, "_flush_warnings", fw._flush_warnings)

        # Patch io_list_io and io_validator at the import level
        import types
        fake_io_mod = types.ModuleType("workbench.core.io_list_io")

        class _Row:
            pass

        fake_io_mod.read_md = lambda p: ([], {})
        fake_io_mod.read_xlsx = lambda p: ([], {})

        fake_val_mod = types.ModuleType("workbench.core.io_validator")
        fake_val_mod.validate_rows = _stub_validate_rows

        monkeypatch.setitem(sys.modules, "workbench.core.io_list_io", fake_io_mod)
        monkeypatch.setitem(sys.modules, "workbench.core.io_validator", fake_val_mod)

        result = api.validate_io_list("RD01_IO_LIST.md")

        assert "_warnings" in result, (
            "validate_io_list() yanıtında '_warnings' anahtarı yok — "
            "_attach_warnings() çağrısı eksik (fix geri alınmış olabilir)"
        )
        # Bozuk JSON → en az bir uyarı beklenir
        assert len(result["_warnings"]) > 0, (
            "Bozuk PROJECT_STATE.json varken validate_io_list() uyarı üretmedi — "
            "_project_state() -> _warn() zinciri çalışmıyor"
        )


# ---------------------------------------------------------------------------
# 3. get_dashboard() — get_state() olmadan uyarı görülmeli
# ---------------------------------------------------------------------------

class TestGetDashboardWarnings:

    def test_warnings_in_response_without_get_state(self, tmp_path):
        """get_dashboard() bozuk PROJECT_STATE.json varken '_warnings' içermeli."""
        import factory_web as fw
        _bad_state(tmp_path)
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()

        result = api.get_dashboard()

        assert "_warnings" in result, (
            "get_dashboard() yanıtında '_warnings' anahtarı yok — "
            "_attach_warnings() çağrısı eksik (fix geri alınmış olabilir)"
        )
        assert len(result["_warnings"]) > 0, (
            "Bozuk PROJECT_STATE.json varken get_dashboard() uyarı üretmedi"
        )

    def test_no_warnings_with_valid_state(self, tmp_path):
        """Geçerli PROJECT_STATE.json → get_dashboard() parse uyarısı üretmez."""
        import factory_web as fw
        _good_state(tmp_path, gate=3)
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()

        result = api.get_dashboard()

        assert "_warnings" in result
        parse_warns = [w for w in result["_warnings"] if w.get("category") == "parse"]
        assert len(parse_warns) == 0, (
            "Geçerli JSON varken get_dashboard() parse uyarısı üretemez"
        )


# ---------------------------------------------------------------------------
# 4. get_report() — get_state() olmadan uyarı görülmeli
# ---------------------------------------------------------------------------

class TestGetReportWarnings:

    def test_warnings_in_response_without_get_state(self, tmp_path):
        """get_report() bozuk PROJECT_STATE.json varken '_warnings' içermeli."""
        import factory_web as fw
        _bad_state(tmp_path)
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()

        result = api.get_report()

        assert "_warnings" in result, (
            "get_report() yanıtında '_warnings' anahtarı yok — "
            "_attach_warnings() çağrısı eksik"
        )
        assert len(result["_warnings"]) > 0


# ---------------------------------------------------------------------------
# 5. get_gate_history() — get_state() olmadan uyarı görülmeli
# ---------------------------------------------------------------------------

class TestGetGateHistoryWarnings:

    def test_warnings_in_response_without_get_state(self, tmp_path):
        """get_gate_history() bozuk PROJECT_STATE.json varken '_warnings' içermeli."""
        import factory_web as fw
        _bad_state(tmp_path)
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()

        result = api.get_gate_history()

        assert "_warnings" in result, (
            "get_gate_history() yanıtında '_warnings' anahtarı yok — "
            "_attach_warnings() çağrısı eksik"
        )
        assert len(result["_warnings"]) > 0


# ---------------------------------------------------------------------------
# 6. advance_gate() — get_state() olmadan uyarı görülmeli
# ---------------------------------------------------------------------------

class TestAdvanceGateWarnings:

    def test_warnings_in_error_response_without_get_state(self, tmp_path):
        """advance_gate() bozuk PROJECT_STATE.json varken '_warnings' içermeli.

        advance_gate() başarısız bile olsa (no project state) uyarılar
        dönülen dict'e eklenmeli.
        """
        import factory_web as fw
        _bad_state(tmp_path)
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()

        # İmza olmadan çağır — blockers ya da state parse hatası olacak
        result = api.advance_gate(signature="")

        assert "_warnings" in result, (
            "advance_gate() yanıtında '_warnings' anahtarı yok — "
            "_attach_warnings() çağrısı eksik"
        )

    def test_warnings_key_present_on_final_gate(self, tmp_path):
        """advance_gate() 'Already at the final gate' durumunda '_warnings' içermeli."""
        import factory_web as fw
        import json
        (tmp_path / "PROJECT_STATE.json").write_text(
            json.dumps({"gate": 7}), encoding="utf-8"
        )
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()

        result = api.advance_gate(signature="Test User (QA)")
        assert result.get("ok") is False
        assert "_warnings" in result, (
            "advance_gate() 'Already at the final gate' yanıtında '_warnings' yok"
        )


# ---------------------------------------------------------------------------
# 7. get_gate_model() — get_state() olmadan uyarı görülmeli
# ---------------------------------------------------------------------------

class TestGetGateModelWarnings:

    def test_warnings_in_response_without_get_state(self, tmp_path):
        """get_gate_model() bozuk PROJECT_STATE.json varken '_warnings' içermeli."""
        import factory_web as fw
        _bad_state(tmp_path)
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()

        result = api.get_gate_model()

        assert "_warnings" in result, (
            "get_gate_model() yanıtında '_warnings' anahtarı yok — "
            "_attach_warnings() çağrısı eksik"
        )
        assert len(result["_warnings"]) > 0


# ---------------------------------------------------------------------------
# 8. get_file_context() — get_state() olmadan uyarı görülmeli
# ---------------------------------------------------------------------------

class TestGetFileContextWarnings:

    def test_warnings_in_response_without_get_state(self, tmp_path, monkeypatch):
        """get_file_context() bozuk PROJECT_STATE.json varken '_warnings' içermeli."""
        import factory_web as fw
        _bad_state(tmp_path)
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()

        # Workbench modülleri genellikle yüklü olmayabilir; exception yolunda da
        # _attach_warnings çağrılmalı (except: actions=default, prompts=[])
        result = api.get_file_context("")

        assert "_warnings" in result, (
            "get_file_context() yanıtında '_warnings' anahtarı yok — "
            "_attach_warnings() çağrısı eksik (hem try hem except dalında olmalı)"
        )


# ---------------------------------------------------------------------------
# 9. Uyarı yalnızca tetiklendiği metodun yanıtında görünür (bağlam izolasyonu)
# ---------------------------------------------------------------------------

class TestWarningContextIsolation:

    def test_warning_not_leaked_to_next_call(self, tmp_path):
        """Birinci metodun uyarısı ikinci metodun yanıtına karışmamalı."""
        import factory_web as fw
        _bad_state(tmp_path)
        api, _fw = _make_api(tmp_path)
        fw._flush_warnings()  # temizle

        # İlk çağrı — bozuk JSON parse uyarısı üretir
        r1 = api.get_dashboard()
        assert len(r1["_warnings"]) > 0, "İlk çağrıda uyarı bekleniyor"

        # Bozuk JSON dosyasını kaldır; ikinci çağrı uyarısız olmalı
        (tmp_path / "PROJECT_STATE.json").write_text(
            '{"gate": 1}', encoding="utf-8"
        )
        r2 = api.get_dashboard()
        parse_warns = [w for w in r2["_warnings"] if w.get("category") == "parse"]
        assert len(parse_warns) == 0, (
            "İkinci çağrıda birinci çağrının uyarısı görünüyor — "
            "buffer birinci çağrıda temizlenmemiş (bağlam sızıntısı)"
        )
