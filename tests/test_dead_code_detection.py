"""
tests/test_c4_dead_code_dol.py — C-4 Dead Code Temizligi Proof Testleri

Sinif C-4: Hesaplanan Ama Expose Edilmeyen Deger
  - s_tStepElapsed : Time  (VAR'da tanimli, hicbir VAR_OUTPUT'a baglanmiyor)
  - s_tonStepTime  : TON   (yalnizca s_tStepElapsed'i besliyor, .Q ve .ET baska yerde kullanilmiyor)

Test tasarimi (fail-closed):
  - Fix varken GECER (dead kod kaldirildiktan sonra SCL temiz)
  - Fix geri alinirsa KIRILIR (dead degiskenler geri gelirse assertion hata verir)
  - Acceptance gate (fb_acceptance_check) PASS olmali

Neden bu testler 'smoke' degil 'proof':
  - Sadece "dosya var mi" kontrol etmiyoruz.
  - Dead koddaki degiskenleri dogrudan assert ederek geri-calis durumunu capture ederiz.
  - Gate PASS testi fb_acceptance_check'in tum MUST kontrollerini kapsar.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_DOL_SCL = _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "motor" / "FB_Motor_DOL.scl"
_CONTRACT = _ROOT / "06_KNOWLEDGE_BASE" / "contracts" / "motor" / "FB_Motor_DOL.contract.json"
_SCRIPTS = _ROOT / "05_SCRIPTS"


def _read_dol() -> str:
    return _DOL_SCL.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# C-4 Dead Variable: s_tStepElapsed
# ---------------------------------------------------------------------------

class TestDeadVarRemoved:
    """
    s_tStepElapsed : Time VAR blogunda bulunmamali (dead — hicbir output'a baglanmiyor).

    REGRESSION: Eger bu degisken geri eklenirse (fix geri alinirsa) test kirilir.
    """

    def test_s_tStepElapsed_not_in_var_block(self):
        """
        VAR blogu icinde 's_tStepElapsed' bildirimi olmamali.
        Fix geri alinirsa (declaration eklenir) bu test KIRILIR.
        """
        scl = _read_dol()
        # VAR ... END_VAR blogunu cikar (statik degiskenler)
        var_block_m = re.search(
            r"\bVAR\b(?!_)(.*?)\bEND_VAR\b",
            scl,
            re.DOTALL | re.IGNORECASE,
        )
        assert var_block_m, "VAR blogu bulunamadi — dosya yapisi bozuk"
        var_text = var_block_m.group(1)

        assert not re.search(r"\bs_tStepElapsed\b", var_text, re.IGNORECASE), (
            "C-4 FIX GERI ALINDI: 's_tStepElapsed' VAR blogunda tekrar tanimlandi.\n"
            "Bu dead deger; hicbir VAR_OUTPUT'a baglanmiyor — kaldirilmasi gerekir."
        )

    def test_s_tStepElapsed_not_assigned_anywhere(self):
        """
        's_tStepElapsed :=' atamasi SCL genelinde olmamali.
        Fix geri alinirsa (atama satirlari geri gelirse) bu test KIRILIR.
        """
        scl = _read_dol()
        code_lines = [
            line for line in scl.splitlines()
            if not line.strip().startswith("//")
        ]
        code_only = "\n".join(code_lines)

        assert not re.search(r"\bs_tStepElapsed\s*:=", code_only, re.IGNORECASE), (
            "C-4 FIX GERI ALINDI: 's_tStepElapsed :=' ataması kod satirlarinda bulundu.\n"
            "Bu dead kod — s_tStepElapsed hicbir cikis portuna bagli degil."
        )


# ---------------------------------------------------------------------------
# C-4 Dead Timer: s_tonStepTime
# ---------------------------------------------------------------------------

class TestDeadTimerRemoved:
    """
    s_tonStepTime : TON yalnizca s_tStepElapsed'i besliyordu.
    s_tStepElapsed kaldirilinca s_tonStepTime da tamamen dead oldu.

    REGRESSION: Timer bildirimi veya cagrilar geri gelirse test KIRILIR.
    """

    def test_s_tonStepTime_not_declared_in_var(self):
        """
        VAR blogunda 's_tonStepTime' TON bildirimi olmamali.
        Fix geri alinirsa bu test KIRILIR.
        """
        scl = _read_dol()
        var_block_m = re.search(
            r"\bVAR\b(?!_)(.*?)\bEND_VAR\b",
            scl,
            re.DOTALL | re.IGNORECASE,
        )
        assert var_block_m, "VAR blogu bulunamadi"
        var_text = var_block_m.group(1)

        assert not re.search(r"\bs_tonStepTime\b", var_text, re.IGNORECASE), (
            "C-4 FIX GERI ALINDI: 's_tonStepTime' VAR blogunda tekrar tanimlandi.\n"
            "s_tStepElapsed kaldirilinca bu timer instance'i da dead hale geldi."
        )

    def test_s_tonStepTime_not_called_in_code(self):
        """
        's_tonStepTime(...)' cagrilari SCL genelinde olmamali.
        Fix geri alinirsa bu test KIRILIR.
        """
        scl = _read_dol()
        code_lines = [
            line for line in scl.splitlines()
            if not line.strip().startswith("//")
        ]
        code_only = "\n".join(code_lines)

        assert not re.search(r"\bs_tonStepTime\b", code_only, re.IGNORECASE), (
            "C-4 FIX GERI ALINDI: 's_tonStepTime' cagrilari kod satirlarinda bulundu.\n"
            "Bu timer tamamen dead — s_tStepElapsed ile birlikte kaldirilmali."
        )


# ---------------------------------------------------------------------------
# Pozitif kontrol: step gecis takibi s_nStepLast uzerinden devam etmeli
# ---------------------------------------------------------------------------

class TestStepTransitionStillWorks:
    """
    s_tonStepTime kaldirildiktan sonra step gecis takibi s_nStepLast uzerinden
    hala calisıyor olmali. Bu iki degisken dokunulmamali.
    """

    def test_s_nStepLast_still_present_in_var(self):
        """
        s_nStepLast VAR blogunda hala tanimli olmali.
        Dead code temizligi bu degiskene dokunmamali.
        """
        scl = _read_dol()
        var_block_m = re.search(
            r"\bVAR\b(?!_)(.*?)\bEND_VAR\b",
            scl,
            re.DOTALL | re.IGNORECASE,
        )
        assert var_block_m, "VAR blogu bulunamadi"
        var_text = var_block_m.group(1)
        assert re.search(r"\bs_nStepLast\b", var_text, re.IGNORECASE), (
            "s_nStepLast VAR blogunda bulunamadi — yanlis silme yapilmis olabilir."
        )

    def test_s_nStepLast_assigned_in_code(self):
        """
        's_nStepLast := s_nStep' atamasi hala kod icerisinde olmali.
        Step gecis takibi kaldirılmamali.
        """
        scl = _read_dol()
        code_lines = [
            line for line in scl.splitlines()
            if not line.strip().startswith("//")
        ]
        code_only = "\n".join(code_lines)
        assert re.search(r"\bs_nStepLast\s*:=\s*s_nStep\b", code_only, re.IGNORECASE), (
            "Step gecis takibi kaybolmis: 's_nStepLast := s_nStep' ataması bulunamadi.\n"
            "C-4 fix sadece timer'i kaldirmali, step takibini degil."
        )


# ---------------------------------------------------------------------------
# Acceptance Gate: FB_Motor_DOL PASS olmali
# ---------------------------------------------------------------------------

class TestAcceptanceGatePassesDOL:
    """
    C-4 duzeltmesi sonrasi FB_Motor_DOL.scl acceptance gate'den gecmeli.
    Tum MUST kontrolleri (G-01..G-05) PASS olmali.
    """

    def test_gate_overall_pass(self):
        """
        run_gate(FB_Motor_DOL.scl, DOL.contract.json) == PASS.
        Fix geri alinirsa ya da baska bir MUST ihlali varsa bu test KIRILIR.
        """
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import run_gate

        result = run_gate(_DOL_SCL, _CONTRACT)
        failures = [c for c in result.checks if c.status == "FAIL"]
        assert result.overall == "PASS", (
            f"FB_Motor_DOL acceptance gate FAIL.\n"
            + "\n".join(f"  {c.check_id}: {c.issues}" for c in failures)
        )

    def test_gate_label_auto_verified(self):
        """Gate etiketi AUTO_VERIFIED icermeli."""
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import run_gate

        result = run_gate(_DOL_SCL, _CONTRACT)
        assert "AUTO_VERIFIED" in result.label, (
            f"Beklenen 'AUTO_VERIFIED' label, bulunan: {result.label!r}"
        )

    def test_interface_check_passes(self):
        """G-02: Tum zorunlu portlar dogru IEC tipleriyle beyan edilmeli."""
        import json
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import check_interface

        scl = _DOL_SCL.read_text(encoding="utf-8")
        contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
        cr = check_interface(scl, contract)
        assert cr.status == "PASS", f"Interface kontrol hatasi: {cr.issues}"

    def test_behaviors_pass(self):
        """G-03: Tum MUST davranis pattern'leri mevcut olmali."""
        import json
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import check_behaviors

        scl = _DOL_SCL.read_text(encoding="utf-8")
        contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
        cr = check_behaviors(scl, contract)
        must_fails = [i for i in cr.issues if not i.startswith("[SHOULD]")]
        assert not must_fails, f"Davranis MUST hatalari: {must_fails}"
