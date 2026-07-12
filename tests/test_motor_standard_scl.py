"""
tests/test_c2_c3_motor_standard.py — Proof test: C-2 ve C-3 fix'leri
                                      FB_Motor_Standard.scl

Sinif C-2: Hata Sayaci Eksikligi
  16#0004 (Manual/Auto conflict) blogu s_nErrorCount artirmiyor.
  Fix: out_wErrorCode atamasindan sonra s_nErrorCount := s_nErrorCount + 1 eklendi.

Sinif C-3: Step Transition Edge Detection Hatasi
  s_nStepLast := s_nStep; ataması koşulsuz yapilıyor, diger FB'lerde IF korumasi var.
  Fix: IF s_nStep <> s_nStepLast THEN ... END_IF; sarmalandı.

Bu testler:
  1. C-2: 16#0004 blogunun s_nErrorCount artisini icerigini dogrular.
  2. C-2-guard: s_nErrorCount artisi olmadan test FAIL eder (koruyucu).
  3. C-3: IF korumasinin varligi + koşulsuz atama yokluğunu dogrular.
  4. C-3-guard: IF korumasi olmadan test FAIL eder (koruyucu).
  5. Gate acceptance check PASS olmali.

Fix geri alinirsa: test 1 ve 3 kirilir.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
sys.path.insert(0, str(_SCRIPTS))

from fb_acceptance_check import run_gate  # noqa: E402

SCL_PATH = (
    _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "motor" / "FB_Motor_Standard.scl"
)
CONTRACT_PATH = (
    _ROOT
    / "06_KNOWLEDGE_BASE"
    / "contracts"
    / "motor"
    / "FB_Motor_DOL.contract.json"
)


# ---------------------------------------------------------------------------
# Yardimci: 16#0004 bloğunu çıkart
# ---------------------------------------------------------------------------

def _extract_0004_block(scl_text: str) -> str:
    """IF (...) AND in_bStartCmd bloğunu başından END_IF'e kadar döner."""
    pattern = re.compile(
        r"(IF\s+\(in_bManualMode.*?AND\s+in_bStartCmd\s+THEN.*?END_IF\s*;)",
        re.DOTALL,
    )
    m = pattern.search(scl_text)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# C-2 Test 1 (Koruyucu / Proof): 16#0004 bloğu s_nErrorCount artırmali
# ---------------------------------------------------------------------------

def test_c2_0004_block_increments_error_count():
    """16#0004 Manual/Auto conflict bloğu s_nErrorCount artismini icermeli.
    Fix geri alinirsa bu test FAIL eder (koruyucu davranis).
    """
    scl = SCL_PATH.read_text(encoding="utf-8")
    block = _extract_0004_block(scl)

    assert block, "16#0004 IF bloğu SCL'de bulunamadi"
    assert re.search(r"s_nErrorCount\s*:=\s*s_nErrorCount\s*\+\s*1", block), (
        "16#0004 blogu s_nErrorCount artirmıyor — C-2 fix eksik veya geri alindi!"
    )


# ---------------------------------------------------------------------------
# C-2 Test 2: s_nErrorCount artışı out_wErrorCode atamasından SONRA olmali
# ---------------------------------------------------------------------------

def test_c2_error_count_after_error_code_assignment():
    """s_nErrorCount artisi out_wErrorCode := 16#0004 atamasindan sonra gelmeli."""
    scl = SCL_PATH.read_text(encoding="utf-8")
    block = _extract_0004_block(scl)

    assert block, "16#0004 IF bloğu SCL'de bulunamadi"

    pos_code = block.find("16#0004")
    m = re.search(r"s_nErrorCount\s*:=\s*s_nErrorCount\s*\+\s*1", block)
    assert m, "s_nErrorCount artisi 16#0004 bloğunda bulunamadi"

    assert m.start() > pos_code, (
        "s_nErrorCount artisi out_wErrorCode atamasindan ONCE geliyor — siralama hatasi"
    )


# ---------------------------------------------------------------------------
# C-3 Test 1 (Koruyucu / Proof): IF korumasi mevcut olmali
# ---------------------------------------------------------------------------

def test_c3_step_last_has_if_guard():
    """s_nStepLast ataması IF s_nStep <> s_nStepLast korumasi altinda olmali.
    Fix geri alinirsa bu test FAIL eder (koruyucu davranis).
    """
    scl = SCL_PATH.read_text(encoding="utf-8")
    assert re.search(
        r"IF\s+s_nStep\s*<>\s*s_nStepLast\s+THEN\s+s_nStepLast\s*:=\s*s_nStep\s*;\s+END_IF\s*;",
        scl,
        re.DOTALL,
    ), (
        "IF s_nStep <> s_nStepLast korumasi bulunamadi — C-3 fix eksik veya geri alindi!"
    )


# ---------------------------------------------------------------------------
# C-3 Test 2: Koşulsuz atama (naked assignment) OLMAMALI
# ---------------------------------------------------------------------------

def test_c3_no_naked_steplast_assignment():
    """Koşulsuz 's_nStepLast := s_nStep;' satiri OLMAMALI (IF korumasi altinda olmali).
    Bu test, IF bloğu DISINDA koşulsuz atama varligi durumunda FAIL eder.
    """
    scl = SCL_PATH.read_text(encoding="utf-8")
    # Satir bazli kontrol: IF'siz, girintili doğrudan atama yok
    lines = scl.splitlines()
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped == "s_nStepLast := s_nStep;":
            # Önceki satirin IF icermesi gerekiyor
            prev = lines[i - 2].strip() if i >= 2 else ""
            assert "IF" in prev or "THEN" in prev, (
                f"Satir {i}: koşulsuz 's_nStepLast := s_nStep;' bulundu — "
                "C-3 IF korumasi eksik veya geri alindi!"
            )


# ---------------------------------------------------------------------------
# Test 3: Gate acceptance check FB_Motor_Standard icin PASS olmali
# ---------------------------------------------------------------------------

def test_gate_passes_for_motor_standard():
    """fb_acceptance_check gate'i FB_Motor_Standard icin PASS dondurmeli."""
    assert SCL_PATH.exists(), f"SCL dosyasi bulunamadi: {SCL_PATH}"
    assert CONTRACT_PATH.exists(), f"Contract dosyasi bulunamadi: {CONTRACT_PATH}"

    result = run_gate(SCL_PATH, CONTRACT_PATH)
    failed_checks = [
        f"{c.check_id} ({c.check_type}): {c.issues}"
        for c in result.checks
        if c.status == "FAIL"
    ]
    assert result.overall == "PASS", (
        f"Gate PASS bekleniyor ama FAIL dondu.\nBasarisiz kontroller:\n"
        + "\n".join(failed_checks)
    )
