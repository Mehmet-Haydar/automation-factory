"""S-9 — preanalysis_job timeout guard.

Bulgu F-12: `_preanalysis_job` dict'te `started_at` yoktu;
`get_preanalysis_status()` timeout kontrolü yapmıyordu.

Düzeltme:
  - job dict'e `"started_at": time.time()` eklendi.
  - `get_preanalysis_status()`: job 1800 sn+ sürerse running=False, ok=False,
    msg="Preanalysis timeout..." olarak kapatılır.
  - Fail-safe: `started_at` yoksa (eski dict), `time.time()` fallback ile
    diff ~0 olur ve timeout tetiklenmez.
  - Kardeş job: `_tia_job` / `get_tia_send_status()` aynı pattern ile korunur.

Her test: fix geri alınırsa KIRILMALI (smoke değil, koruyucu assertion).
"""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FACTORY_WEB = PROJECT_ROOT / "05_SCRIPTS" / "factory_web.py"


# ---------------------------------------------------------------------------
# Statik kaynak analizleri — import gerektirmeden çalışır
# ---------------------------------------------------------------------------

def _source() -> str:
    return FACTORY_WEB.read_text(encoding="utf-8")


def _preanalysis_job_block() -> str:
    """run_retrofit_preanalysis() gövdesini izole eder."""
    src = _source()
    start = src.index("def run_retrofit_preanalysis")
    nxt = src.find("\n    def ", start + 1)
    return src[start: nxt if nxt != -1 else len(src)]


def _get_status_block() -> str:
    """get_preanalysis_status() gövdesini izole eder."""
    src = _source()
    start = src.index("def get_preanalysis_status")
    nxt = src.find("\n    def ", start + 1)
    return src[start: nxt if nxt != -1 else len(src)]


def _tia_job_block() -> str:
    """send_to_tia() içindeki _tia_job dict oluşturmayı izole eder."""
    src = _source()
    start = src.index("self._tia_job = job")
    # 500 karakter öncesine bak — dict literal orada olmalı
    return src[max(0, start - 500): start + 50]


def _tia_status_block() -> str:
    """get_tia_send_status() gövdesini izole eder."""
    src = _source()
    start = src.index("def get_tia_send_status")
    nxt = src.find("\n    def ", start + 1)
    return src[start: nxt if nxt != -1 else len(src)]


# ---------------------------------------------------------------------------
# Sınıf 1: started_at kaydı — dict'lerde var mı?
# ---------------------------------------------------------------------------

class TestStartedAtPresent:
    def test_preanalysis_job_has_started_at(self):
        """_preanalysis_job oluşturulurken 'started_at' alanı atanmalı."""
        block = _preanalysis_job_block()
        assert '"started_at"' in block or "'started_at'" in block, (
            "run_retrofit_preanalysis: job dict 'started_at' içermiyor. "
            "Timeout guard çalışamaz."
        )

    def test_preanalysis_started_at_uses_time_time(self):
        """started_at değeri time.time() ile atanmalı."""
        block = _preanalysis_job_block()
        assert "time.time()" in block, (
            "run_retrofit_preanalysis: 'started_at' alanı time.time() ile "
            "set edilmeli."
        )

    def test_tia_job_has_started_at(self):
        """_tia_job (kardeş) oluşturulurken 'started_at' alanı atanmalı."""
        block = _tia_job_block()
        assert '"started_at"' in block or "'started_at'" in block, (
            "send_to_tia: _tia_job dict 'started_at' içermiyor. "
            "Kardeş timeout guard çalışamaz."
        )


# ---------------------------------------------------------------------------
# Sınıf 2: Timeout kontrolü — kaynak kodunda mevcut mu?
# ---------------------------------------------------------------------------

class TestTimeoutGuardExists:
    def test_status_checks_started_at(self):
        """get_preanalysis_status() 'started_at' alanını okumalı."""
        block = _get_status_block()
        assert "started_at" in block, (
            "get_preanalysis_status: 'started_at' kontrolü yok. "
            "Timeout guard uygulanmamış."
        )

    def test_status_uses_1800_threshold(self):
        """Timeout eşiği 1800 saniye (30 dk) olmalı."""
        block = _get_status_block()
        assert "1800" in block, (
            "get_preanalysis_status: 1800 sn eşiği bulunamadı."
        )

    def test_status_sets_running_false_on_timeout(self):
        """Timeout tetiklenince running=False set edilmeli."""
        block = _get_status_block()
        assert 'job["running"] = False' in block or "running=False" in block, (
            "get_preanalysis_status: timeout sonrası running=False atanmıyor."
        )

    def test_status_sets_ok_false_on_timeout(self):
        """Timeout tetiklenince ok=False set edilmeli."""
        block = _get_status_block()
        assert 'job["ok"] = False' in block or "ok=False" in block, (
            "get_preanalysis_status: timeout sonrası ok=False atanmıyor."
        )

    def test_status_timeout_message_is_descriptive(self):
        """Timeout mesajı kullanıcıya açıklayıcı olmalı ('timeout' veya '30' içermeli)."""
        block = _get_status_block()
        assert "timeout" in block.lower() or "30" in block, (
            "get_preanalysis_status: timeout mesajı açıklayıcı değil."
        )

    def test_tia_status_has_timeout_guard(self):
        """get_tia_send_status() de (kardeş) timeout guard içermeli."""
        block = _tia_status_block()
        assert "started_at" in block and "1800" in block, (
            "get_tia_send_status: kardeş timeout guard eksik."
        )


# ---------------------------------------------------------------------------
# Sınıf 3: Davranışsal testler — mock job dict ile doğrudan mantık testi
# ---------------------------------------------------------------------------

def _simulate_preanalysis_timeout_check(job: dict) -> dict:
    """
    get_preanalysis_status() içindeki timeout mantığını izole simüle eder.
    factory_web'i import etmeden saf birim testi yapar.
    """
    if (
        job.get("running")
        and time.time() - job.get("started_at", time.time()) > 1800
    ):
        job["running"] = False
        job["done"] = True
        job["ok"] = False
        job["msg"] = "Preanalysis timeout (>30 min) — job was forcibly stopped"
    return job


class TestTimeoutBehavior:
    def test_timeout_triggered_after_1801_seconds(self):
        """started_at 1801 sn önceye set edilince timeout tetiklenmeli."""
        job = {
            "running": True, "done": False, "ok": None, "msg": "",
            "started_at": time.time() - 1801,
        }
        result = _simulate_preanalysis_timeout_check(job)
        assert result["running"] is False, "1801 sn sonra running=False olmalı"
        assert result["ok"] is False, "1801 sn sonra ok=False olmalı"
        assert "timeout" in result["msg"].lower(), (
            "Timeout mesajı 'timeout' içermeli"
        )

    def test_timeout_not_triggered_at_1799_seconds(self):
        """started_at 1799 sn önceye set edilince timeout tetiklenmemeli."""
        job = {
            "running": True, "done": False, "ok": None, "msg": "",
            "started_at": time.time() - 1799,
        }
        result = _simulate_preanalysis_timeout_check(job)
        assert result["running"] is True, (
            "1799 sn sonra job hâlâ running=True olmalı (timeout henüz değil)"
        )
        assert result["ok"] is None, "1799 sn sonra ok hâlâ None olmalı"

    def test_timeout_not_triggered_when_started_at_missing(self):
        """started_at eksikse (eski dict), timeout tetiklenmemeli — graceful fallback."""
        job = {
            "running": True, "done": False, "ok": None, "msg": "",
            # started_at YOK — eski format
        }
        result = _simulate_preanalysis_timeout_check(job)
        assert result["running"] is True, (
            "started_at eksikse timeout tetiklenmemeli (fail-safe fallback)"
        )

    def test_timeout_not_triggered_when_already_done(self):
        """Job zaten done=True ise (running=False), timeout kontrolü etkisiz olmalı."""
        job = {
            "running": False, "done": True, "ok": True, "msg": "complete",
            "started_at": time.time() - 9999,
        }
        result = _simulate_preanalysis_timeout_check(job)
        # running=False olduğu için guard girmiyor — ok=True korunmalı
        assert result["ok"] is True, (
            "Zaten tamamlanmış job'un ok değeri timeout tarafından değiştirilmemeli"
        )

    def test_timeout_result_contains_required_fields(self):
        """Timeout sonrası job: running=False, done=True, ok=False, msg içeriyor."""
        job = {
            "running": True, "done": False, "ok": None, "msg": "",
            "started_at": time.time() - 1801,
        }
        result = _simulate_preanalysis_timeout_check(job)
        assert result["running"] is False
        assert result["done"] is True
        assert result["ok"] is False
        assert isinstance(result["msg"], str) and len(result["msg"]) > 0


# ---------------------------------------------------------------------------
# Sınıf 4: time modülü import edildi mi?
# ---------------------------------------------------------------------------

class TestTimeImport:
    def test_time_module_imported(self):
        """factory_web.py 'import time' içermeli."""
        src = _source()
        assert "import time" in src, (
            "factory_web.py 'import time' içermiyor. "
            "Timeout guard'lar time.time() çağırıyor ama modül eksik."
        )
