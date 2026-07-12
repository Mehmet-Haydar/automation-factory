"""
tests/test_c1_softstarter_errorcode.py — Proof test: C-1 Hata Kodu Cakismasi fix

Sinif C-1: FB_Motor_SoftStarter step 10 (ramp-up) ve step 30 (ramp-down) ayni
hata kodunu (16#0010) kullaniyordu. Fix: step 30 -> 16#0011 (Ramp-down timeout).

Bu test:
  1. SCL'de 16#0010 ve 16#0011'in FARKLI satirlarda bulunugunu assert eder.
  2. Step 30 blogunun 16#0011 kullandigini, 16#0010 KULLANMADIGINI assert eder.
  3. Step 10 blogunun 16#0010 kullandigini assert eder.
  4. fb_acceptance_check gate'inin FB_Motor_SoftStarter icin PASS donduugunu dogrular.
  5. Contract'ta 16#0011 kayitli oldugunu dogrular.

Fix geri alinirsa (ramp-down tekrar 16#0010 yapilirsa): test 2 kirilir (FAIL).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
sys.path.insert(0, str(_SCRIPTS))

from fb_acceptance_check import run_gate  # noqa: E402

SCL_PATH = (
    _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "motor" / "FB_Motor_SoftStarter.scl"
)
CONTRACT_PATH = (
    _ROOT
    / "06_KNOWLEDGE_BASE"
    / "contracts"
    / "motor"
    / "FB_Motor_SoftStarter.contract.json"
)


# ---------------------------------------------------------------------------
# Yardimci: step blogunu satirlara gore cikar
# ---------------------------------------------------------------------------

def _extract_step_block(scl_text: str, step_marker: str) -> str:
    """Verilen step yorumundan (ornek: '10: // RAMP UP') bir sonraki step'e kadar olan
    metin blogu doner. Basit regex; makul SCL formati icin yeterli."""
    pattern = re.compile(
        rf"({re.escape(step_marker)}.*?)(?=\n\s+\d+:\s*//|\Z)",
        re.DOTALL,
    )
    m = pattern.search(scl_text)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Test 1: Farkli kodlar farkli satirlarda bulunmali
# ---------------------------------------------------------------------------

def test_both_error_codes_present_in_scl():
    """SCL'de hem 16#0010 hem 16#0011 bulunmali."""
    scl = SCL_PATH.read_text(encoding="utf-8")
    assert re.search(r"16#0010", scl), "16#0010 (Ramp-up timeout) SCL'de bulunamadi"
    assert re.search(r"16#0011", scl), "16#0011 (Ramp-down timeout) SCL'de bulunamadi"


# ---------------------------------------------------------------------------
# Test 2 (Koruyucu / Proof): Step 30 ramp-down blogu 16#0011 kullanmali,
#         16#0010 KULLANMAMALI — fix geri alinirsa bu test kirilir.
# ---------------------------------------------------------------------------

def test_step30_uses_rampdown_specific_error_code():
    """Step 30 (RAMP DOWN) blogu 16#0011 kullanmali; 16#0010 OLMAMALI.
    Bu test fix olmadan FAIL eder (koruyucu davranis).
    """
    scl = SCL_PATH.read_text(encoding="utf-8")
    step30_block = _extract_step_block(scl, "30: // RAMP DOWN")

    assert step30_block, "Step 30 (RAMP DOWN) blogu SCL'de bulunamadi"
    assert re.search(r"16#0011", step30_block), (
        "Step 30 ramp-down timeout hata kodu 16#0011 olmali; mevcut degil"
    )
    assert not re.search(r"out_wErrorCode\s*:=\s*16#0010", step30_block), (
        "Step 30, ramp-up kodu 16#0010 kullaniyor — hata kodu cakismasi hala mevcut!"
    )


# ---------------------------------------------------------------------------
# Test 3: Step 10 ramp-up blogu 16#0010 kullanmali (degismemeli)
# ---------------------------------------------------------------------------

def test_step10_still_uses_rampup_error_code():
    """Step 10 (RAMP UP) blogu 16#0010 kullanmaya devam etmeli."""
    scl = SCL_PATH.read_text(encoding="utf-8")
    step10_block = _extract_step_block(scl, "10: // RAMP UP")

    assert step10_block, "Step 10 (RAMP UP) blogu SCL'de bulunamadi"
    assert re.search(r"16#0010", step10_block), (
        "Step 10 ramp-up timeout hata kodu 16#0010 olmali; mevcut degil"
    )


# ---------------------------------------------------------------------------
# Test 4: Gate acceptance check PASS olmali
# ---------------------------------------------------------------------------

def test_gate_passes_for_softstarter():
    """fb_acceptance_check gate'i FB_Motor_SoftStarter icin PASS dondurmeli."""
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


# ---------------------------------------------------------------------------
# Test 5: Contract'ta 16#0011 kayitli olmali
# ---------------------------------------------------------------------------

def test_contract_registers_rampdown_error_code():
    """Contract error_codes listesinde 16#0011 (Ramp-down timeout) kayitli olmali."""
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    error_codes = contract.get("constraints", {}).get("error_codes", [])
    hexes = [ec["hex"].upper() for ec in error_codes]
    assert "16#0011" in hexes, (
        f"Contract'ta 16#0011 kaydi bulunamadi. Mevcut kodlar: {hexes}"
    )
