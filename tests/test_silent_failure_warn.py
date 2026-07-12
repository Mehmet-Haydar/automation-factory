"""O-1 — Sessiz Hata Yutma: _warn mekanizması proof testleri.

Bu testler:
  - Fix VARKEN geçmeli.
  - Fix GERİ ALINIRSA (except bloğundaki _warn çağrısı kaldırılırsa) kırılmalı.

Kapsam:
  1. factory_web._project_state   — bozuk JSON → warning emit edilir, {} döner
  2. data_classification_guard    — bozuk JSON → warning emit edilir, CONFIDENTIAL döner
  3. bom_manager.scan_library     — okunamayan MD → warning emit edilir, katalog entry atlanır
  4. webgui/index.html            — style-src-elem 'self'; style-src-attr 'unsafe-inline'
                                    (unsafe-inline blok seviyesinde yok)
"""
from __future__ import annotations

import importlib
import json
import logging
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "05_SCRIPTS"

for _p in (PROJECT_ROOT, SCRIPTS_DIR):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)


# ---------------------------------------------------------------------------
# 1. factory_web._project_state — bozuk JSON uyarı yayar, {} döner
# ---------------------------------------------------------------------------

class TestProjectStateWarn:
    """_project_state bozuk JSON'da {} döner VE _warn çağırır."""

    def _make_api(self, root: Path):
        """Api nesnesini minimal patch ile oluştur (pywebview gerektirmez)."""
        import factory_web as fw
        # Api.__init__ self.settings ve self.root atar; _load_settings ve
        # _resolve_root mock'lanır.
        api = object.__new__(fw.Api)
        api.settings = {}
        api.root = root
        return api, fw

    def test_returns_empty_dict_on_bad_json(self, tmp_path):
        """Bozuk JSON → {} döner (davranış değişmez)."""
        state_file = tmp_path / "PROJECT_STATE.json"
        state_file.write_text("{broken json!!!}", encoding="utf-8")

        api, _fw = self._make_api(tmp_path)
        result = api._project_state()
        assert result == {}

    def test_warning_emitted_on_bad_json(self, tmp_path, caplog):
        """Bozuk JSON → WARNING seviyesinde log kaydı oluşur."""
        import factory_web as fw

        state_file = tmp_path / "PROJECT_STATE.json"
        state_file.write_text("{broken json!!!}", encoding="utf-8")

        api = object.__new__(fw.Api)
        api.settings = {}
        api.root = tmp_path

        with caplog.at_level(logging.WARNING, logger="factory_web"):
            api._project_state()

        assert any(
            "parse error" in rec.message.lower() or "PROJECT_STATE.json" in rec.message
            for rec in caplog.records
        ), (
            "Bozuk JSON parse hatası warning olarak loglanmamis — "
            "_warn() cagrilmiyor (fix geri alinmis olabilir)"
        )

    def test_warning_appears_in_get_state_response(self, tmp_path, caplog, monkeypatch):
        """get_state() yaniti _warnings listesi içerir (parse hatası varsa)."""
        import factory_web as fw

        state_file = tmp_path / "PROJECT_STATE.json"
        state_file.write_text("{broken json!!!}", encoding="utf-8")

        api = object.__new__(fw.Api)
        api.settings = {}
        api.root = tmp_path

        # get_state() bazı iç metodları çağırır; stub'layalım
        monkeypatch.setattr(api, "_build_tree", lambda: [], raising=False)
        monkeypatch.setattr(api, "_prompts", lambda: [], raising=False)
        monkeypatch.setattr(api, "_library_data", lambda: [], raising=False)
        monkeypatch.setattr(api, "default_open", lambda: None, raising=False)
        monkeypatch.setattr(fw, "_run_git", lambda *a, **kw: "main")

        # Önceki testten kalan buffer'ı temizle
        fw._flush_warnings()

        with caplog.at_level(logging.WARNING, logger="factory_web"):
            result = api.get_state()

        assert "_warnings" in result, "get_state() yanıtında '_warnings' anahtarı yok"
        assert len(result["_warnings"]) > 0, (
            "Bozuk PROJECT_STATE.json varken _warnings listesi boş — "
            "_warn() / _flush_warnings() entegrasyonu eksik"
        )

    def test_valid_json_produces_no_warning(self, tmp_path, caplog):
        """Geçerli JSON → warning yok."""
        import factory_web as fw

        state_file = tmp_path / "PROJECT_STATE.json"
        state_file.write_text('{"gate": 2}', encoding="utf-8")

        api = object.__new__(fw.Api)
        api.settings = {}
        api.root = tmp_path

        with caplog.at_level(logging.WARNING, logger="factory_web"):
            result = api._project_state()

        assert result == {"gate": 2}
        parse_warns = [r for r in caplog.records if "parse" in r.message.lower()]
        assert len(parse_warns) == 0


# ---------------------------------------------------------------------------
# 2. data_classification_guard — bozuk JSON uyarı yayar, CONFIDENTIAL döner
# ---------------------------------------------------------------------------

class TestClassificationGuardWarn:

    def test_bad_state_json_still_confidential(self, tmp_path):
        """Bozuk PROJECT_STATE.json → CONFIDENTIAL (fail-closed değişmez)."""
        from data_classification_guard import read_project_classification

        (tmp_path / "PROJECT_STATE.json").write_text("{not valid", encoding="utf-8")
        result = read_project_classification(tmp_path)
        assert result == "CONFIDENTIAL"

    def test_bad_state_json_emits_warning(self, tmp_path, caplog):
        """Bozuk PROJECT_STATE.json → WARNING loglanır."""
        from data_classification_guard import read_project_classification

        (tmp_path / "PROJECT_STATE.json").write_text("{not valid", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="data_classification_guard"):
            read_project_classification(tmp_path)

        assert any(
            "PROJECT_STATE.json" in rec.message or "parse" in rec.message.lower()
            for rec in caplog.records
        ), (
            "Bozuk PROJECT_STATE.json parse hatası loglanmamis — "
            "_warn() cagrilmiyor (fix geri alinmis olabilir)"
        )

    def test_bad_maestro_emits_warning(self, tmp_path, caplog, monkeypatch):
        """PROJECT_MAESTRO.md okuma hatası → WARNING loglanır."""
        from data_classification_guard import read_project_classification

        maestro = tmp_path / "PROJECT_MAESTRO.md"
        maestro.write_text("data_classification: PUBLIC\n", encoding="utf-8")

        # read_text'i hata atacak şekilde patch'le
        original_is_file = Path.is_file

        def patched_is_file(self):
            return True

        def patched_read_text(self, *args, **kwargs):
            if self.name == "PROJECT_STATE.json":
                raise OSError("disk error sim")
            if self.name == "PROJECT_MAESTRO.md":
                raise OSError("maestro read error sim")
            raise OSError("unexpected")

        monkeypatch.setattr(Path, "read_text", patched_read_text)
        monkeypatch.setattr(Path, "is_file", patched_is_file)

        with caplog.at_level(logging.WARNING, logger="data_classification_guard"):
            result = read_project_classification(tmp_path)

        assert result == "CONFIDENTIAL"
        assert len(caplog.records) >= 1, (
            "OSError yakalandığında warning loglanmamis — "
            "_warn() bloğu eksik (fix geri alinmis olabilir)"
        )


# ---------------------------------------------------------------------------
# 3. bom_manager.scan_library — okunamayan MD uyarı yayar, entry atlanır
# ---------------------------------------------------------------------------

class TestBomManagerWarn:

    def test_unreadable_md_emits_warning(self, tmp_path, caplog, monkeypatch):
        """Okunamayan MD → warning yayılır, katalog boş döner."""
        import bom_manager

        lib_root = tmp_path / "lib"
        lib_root.mkdir()
        bad_md = lib_root / "bad_device.md"
        bad_md.write_text("device_id: SIM_BAD\n", encoding="utf-8")

        # read_text'i hata atacak şekilde patch'le
        original_read_text = Path.read_text

        def patched_read_text(self, *args, **kwargs):
            if self.name == "bad_device.md":
                raise OSError("permission denied sim")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", patched_read_text)

        with caplog.at_level(logging.WARNING, logger="bom_manager"):
            catalog = bom_manager.scan_library(lib_root)

        assert "SIM_BAD" not in catalog, "Hatalı MD yanlışlıkla kataloğa eklendi"
        assert any(
            "scan_library" in rec.message or "cannot read" in rec.message
            for rec in caplog.records
        ), (
            "Okunamayan MD için warning loglanmamis — "
            "_warn() cagrilmiyor (fix geri alinmis olabilir)"
        )

    def test_readable_md_no_warning(self, tmp_path, caplog):
        """Geçerli MD → warning yok, entry katalogda."""
        import bom_manager

        lib_root = tmp_path / "lib"
        (lib_root / "plc").mkdir(parents=True)
        (lib_root / "plc" / "cpu1500.md").write_text(
            'device_id: "CPU1515"\nvendor: "Siemens"\nmodel: "1515-2PN"\n',
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING, logger="bom_manager"):
            catalog = bom_manager.scan_library(lib_root)

        assert "CPU1515" in catalog
        assert len(caplog.records) == 0


# ---------------------------------------------------------------------------
# 4. webgui/index.html — style-src 'unsafe-inline' global blok yoktur
# ---------------------------------------------------------------------------

class TestCSPStyleSrc:
    INDEX_HTML = PROJECT_ROOT / "webgui" / "index.html"

    def test_no_global_unsafe_inline_style_src(self):
        """style-src directive'inde tek başına 'unsafe-inline' bulunmamalı.

        Kabul edilebilir: style-src-attr 'unsafe-inline' (element attribute)
        Kabul edilemez:  style-src 'unsafe-inline' (hem <style> hem attribute)
        """
        content = self.INDEX_HTML.read_text(encoding="utf-8")
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip().lower()
            # "style-src 'self' 'unsafe-inline'" veya "style-src 'unsafe-inline'" pattern'i
            if "style-src" in stripped and "'unsafe-inline'" in stripped:
                # style-src-attr veya style-src-elem ile başlıyorsa geçerli
                assert stripped.startswith("style-src-"), (
                    f"Satir: {line!r}\n"
                    "style-src directive'inde 'unsafe-inline' hâlâ mevcut — "
                    "fix geri alınmış olabilir. "
                    "Beklenen: style-src-elem 'self'; style-src-attr 'unsafe-inline'"
                )

    def test_style_src_elem_self_present(self):
        """style-src-elem 'self' directive'i CSP'de bulunmalı."""
        content = self.INDEX_HTML.read_text(encoding="utf-8")
        assert "style-src-elem" in content and "'self'" in content, (
            "style-src-elem 'self' CSP'de bulunamadı — "
            "fix uygulanmamış veya geri alınmış olabilir"
        )

    def test_no_inline_style_block(self):
        """HTML'de <style> bloğu bulunmamalı (CSP'yi ihlal eder)."""
        content = self.INDEX_HTML.read_text(encoding="utf-8")
        import re
        style_blocks = re.findall(r"<style[\s>]", content, re.IGNORECASE)
        assert len(style_blocks) == 0, (
            f"<style> bloğu bulundu: {style_blocks} — "
            "style-src-elem 'self' ihlal edilecek"
        )
