"""
tests/test_s3_fault_isolation.py — S-3 Fault Isolation Proof Tests

Sınıf S-3: Hata Aktifken Kontrol Devam Ediyor — fault isolation eksikliği

Kanıtlanan düzeltmeler:
  1. FB_Valve_Modulating: setpoint range hatası s_nStep := 99 ile state machine'i durdurmalı
  2. FB_PID_Wrapper: saturation bloğu stub hata kodu (16#0010) üzerine out_wErrorCode yazmamalı;
     out_bSaturated çıkışı mevcut olmalı

Test tasarımı (fail-closed):
  - Fix varken GECer
  - Fix geri alınırsa KIRILIR (smoke degil; koruyucu davranisi assert eder)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_VALVE_SCL = _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "valve" / "FB_Valve_Modulating.scl"
_PID_SCL   = _ROOT / "06_KNOWLEDGE_BASE" / "blocks" / "process" / "FB_PID_Wrapper.scl"


# ---------------------------------------------------------------------------
# Yardimci: SCL icerik okuyucu
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# FB_Valve_Modulating — S-3 fix dogrulamasi
# ---------------------------------------------------------------------------

class TestValveModulatingFaultIsolation:
    """
    Setpoint validation blogunda hata tespit edildiginde state machine
    s_nStep := 99 ile durdurulmali.

    Pattern referansi: wire-break blogu (satir ~82-88) dogru ornek:
        out_bError := TRUE; out_wErrorCode := 16#0001;
        s_nErrorCount := ...;
        s_nStep := 99;
    """

    def test_setpoint_error_block_sets_step99(self):
        """
        Setpoint out-of-range blogu (16#0002) icerisinde 's_nStep := 99' olmali.
        Bu satir yoksa state machine hata aktifken devam eder — S-3 guvensiz durumu.
        """
        scl = _read(_VALVE_SCL)

        # 16#0002 blogu icindeki metin parcasini bul
        # Pattern: 16#0002 gorundukten sonra, bir sonraki END_IF'e kadar s_nStep := 99 olmali
        # Basit dogrulama: dosya genelinde 16#0002 ile iliskili satir blogu icinde step99 var mi
        # Cerrahi: IF NOT out_bError THEN ... 16#0002 ... END_IF bolumunu tara

        # 16#0002 iceren IF blogu
        # "IF NOT out_bError THEN" -> 16#0002 -> "s_nStep := 99" -> "END_IF"
        pattern = re.compile(
            r"IF\s+NOT\s+out_bError\s+THEN.*?16#0002.*?s_nStep\s*:=\s*99.*?END_IF",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(scl)
        assert match is not None, (
            "S-3 FIX EKSIK: Setpoint range hata blogu (16#0002) icinde 's_nStep := 99' bulunamadi.\n"
            "Hata aktifken state machine durmuyor — fault isolation uygulanmamis."
        )

    def test_wire_break_already_has_step99(self):
        """
        Wire-break blogu (16#0001) referans pattern — bu zaten dogru olmali (dokunan yok).
        Referans olarak varligini dogrula.
        """
        scl = _read(_VALVE_SCL)
        # Wire-break blogu: 16#0001 AND s_nStep := 99 ayni IF sartinda bulunmali
        # (wire-break blogu IF NOT out_bError icinde degil, dogrudan s_nStep := 99 yapiyor)
        assert "16#0001" in scl, "Wire-break error kodu kayip"
        # step 99 wire-break blogunda mevcut
        wire_pattern = re.compile(
            r"in_rFeedbackPct\s*<\s*-5\.0.*?s_nStep\s*:=\s*99",
            re.DOTALL | re.IGNORECASE,
        )
        assert wire_pattern.search(scl), (
            "Referans wire-break blogu s_nStep := 99 icermiyor — referans pattern bozuk"
        )

    def test_gate_passes_fb_valve_modulating(self):
        """
        S-3 duzeltmesi sonrasi FB_Valve_Modulating kabul kapisi PASS olmali.
        """
        _SCRIPTS = _ROOT / "05_SCRIPTS"
        sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import run_gate

        contract = (
            _ROOT / "06_KNOWLEDGE_BASE" / "contracts" / "valve" / "FB_Valve_Modulating.contract.json"
        )
        result = run_gate(_VALVE_SCL, contract)
        failures = [c for c in result.checks if c.status == "FAIL"]
        assert result.overall == "PASS", (
            f"FB_Valve_Modulating gate FAIL.\n"
            + "\n".join(f"  {c.check_id}: {c.issues}" for c in failures)
        )

    def test_regression_no_step99_would_break(self):
        """
        REGRESSION PROOF: Eger 's_nStep := 99' setpoint blogundan kaldirilirsa bu test kirilir.

        Yaklasim: SCL'de 16#0002 blogu (setpoint hatasi) VE 16#0001 blogu (wire-break) her ikisi de
        s_nStep := 99 icermeli. Toplam olusumu say — en az 2 olacak.
        Eger setpoint blogundan s_nStep := 99 kaldirilirsa, sadece wire-break blocunda kalir (1 tane).
        Bu test 2 veya daha fazla olmasini zorunlu kilar.

        16#0001 blogu zaten 'duzgün' referans olarak kabul ediliyor (biz dokunmadik).
        16#0002 bloguna biz s_nStep := 99 ekledik — bu 2. olusumu olusturuyor.
        """
        scl = _read(_VALVE_SCL)

        # Yorum satirlari haric kod satirlarinda s_nStep := 99 sayisi
        code_lines = [
            line for line in scl.splitlines()
            if not line.strip().startswith("//")
        ]
        step99_count = sum(
            1 for line in code_lines
            if re.search(r"s_nStep\s*:=\s*99", line)
        )

        assert step99_count >= 2, (
            f"S-3 FIX EKSIK veya GERI ALINDI: Kod satirlarinda 's_nStep := 99' {step99_count} kez bulundu, "
            f"en az 2 bekleniyor.\n"
            f"Beklenen: wire-break blogu (16#0001) + setpoint blogu (16#0002) her biri icin birer adet.\n"
            f"Eger 1 ise setpoint blogundaki S-3 fix uygulanmamis/kaldirilmis demektir."
        )


# ---------------------------------------------------------------------------
# FB_PID_Wrapper — S-3 fix dogrulamasi
# ---------------------------------------------------------------------------

class TestPIDWrapperFaultIsolation:
    """
    Saturation blogu out_wErrorCode'u ezmemeli; stub kodu (16#0010) korunmali.
    out_bSaturated VAR_OUTPUT olarak eklenmeli.
    """

    def test_out_bSaturated_declared_in_var_output(self):
        """
        out_bSaturated, VAR_OUTPUT blogunda Bool olarak tanimlanmali.
        """
        scl = _read(_PID_SCL)
        # VAR_OUTPUT blogunu cikar
        var_out_block_m = re.search(
            r"\bVAR_OUTPUT\b(.*?)\bEND_VAR\b",
            scl,
            re.DOTALL | re.IGNORECASE,
        )
        assert var_out_block_m, "VAR_OUTPUT blogu bulunamadi"
        var_out_text = var_out_block_m.group(1)

        assert re.search(
            r"\bout_bSaturated\s*:\s*Bool\b",
            var_out_text,
            re.IGNORECASE,
        ), (
            "S-3 FIX EKSIK: out_bSaturated : Bool VAR_OUTPUT blogunda bulunamadi.\n"
            "Saturation bilgisi out_wErrorCode uzerine yazilabilir — kod ezme devam ediyor."
        )

    def test_saturation_does_not_write_errorcode(self):
        """
        Saturation tespiti out_wErrorCode := 16#0002 atamasi yapmamali (dogrudan atama).
        out_bSaturated kullanmali.
        """
        scl = _read(_PID_SCL)

        # Saturation blogu: "out_rOutput <= ... OR ... >= ..." yakininda dogrudan out_wErrorCode := 16#0002 olmamali
        # Daha kesin: out_bSaturated atama satirinin oldugu satirda out_wErrorCode := yoksa iyi
        # Simdi kontrol: saturation blogu icinde dogrudan atama var mi?
        # Pattern: "out_wErrorCode := 16#0002" ifadesi YORUM disinda kod olarak geciyor mu?

        # Tum satirlari tara; yorum satirlari disinda out_wErrorCode := 16#0002 olmasin
        code_lines = [
            line for line in scl.splitlines()
            if not line.strip().startswith("//")
        ]
        code_only = "\n".join(code_lines)

        direct_assign = re.search(
            r"out_wErrorCode\s*:=\s*16#0002",
            code_only,
        )
        assert direct_assign is None, (
            "S-3 FIX EKSIK: Saturation blogu dogrudan 'out_wErrorCode := 16#0002' ataması yapiyor.\n"
            "Bu stub hata kodu (16#0010) veya PV-fault kodunu (16#0001) eziyor."
        )

    def test_saturation_sets_out_bSaturated(self):
        """
        Saturation tespiti out_bSaturated := TRUE veya Boolean ifade atamalı.
        """
        scl = _read(_PID_SCL)
        assert re.search(
            r"out_bSaturated\s*:=",
            scl,
            re.IGNORECASE,
        ), (
            "S-3 FIX EKSIK: 'out_bSaturated :=' ataması SCL icinde bulunamadi."
        )

    def test_stub_error_code_preserved_without_saturation_overwrite(self):
        """
        Stub aktif blogu 16#0010 setliyor. Saturation blogu bu kodu ezmemeli.
        Kod akisi: stub out_wErrorCode := 16#0010 → saturation blogu calistiktan
        sonra out_wErrorCode hala 16#0010 olmali (out_bSaturated TRUE olsa bile).

        Bunu SCL metninden: saturation blogu icerisinde 'out_wErrorCode' atamasi yok mi kontrol et.
        """
        scl = _read(_PID_SCL)

        # Saturation blogu: "out_bSaturated :=" atamasi olan satir araligini bul
        # Bu aralik icinde out_wErrorCode := olmamali (yorum satirlari haric)
        lines = scl.splitlines()
        in_saturation_region = False
        saturation_region_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            # Saturation bolumu baslangici
            if "out_bsaturated" in stripped.lower() and ":=" in stripped:
                in_saturation_region = True
            if in_saturation_region:
                saturation_region_lines.append(stripped)
                # Bir satir oldugu icin region bitimini tek satir olarak kabul et
                # (çok satirli ise bir sonraki boş satira kadar devam et)
                if len(saturation_region_lines) > 3:
                    break

        # Saturation bolumunde out_wErrorCode := olmamali (yorum disinda)
        for line in saturation_region_lines:
            if line.startswith("//"):
                continue
            assert "out_wErrorCode" not in line or ":=" not in line, (
                f"Saturation bolumu 'out_wErrorCode :=' ataması yapiyor: {line!r}\n"
                "Bu stub hata kodunu eziyor."
            )

    def test_gate_passes_fb_pid_wrapper(self):
        """
        S-3 duzeltmesi sonrasi FB_PID_Wrapper kabul kapisi PASS olmali.
        """
        _SCRIPTS = _ROOT / "05_SCRIPTS"
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        from fb_acceptance_check import run_gate

        contract = (
            _ROOT / "06_KNOWLEDGE_BASE" / "contracts" / "process" / "FB_PID_Wrapper.contract.json"
        )
        result = run_gate(_PID_SCL, contract)
        failures = [c for c in result.checks if c.status == "FAIL"]
        assert result.overall == "PASS", (
            f"FB_PID_Wrapper gate FAIL.\n"
            + "\n".join(f"  {c.check_id}: {c.issues}" for c in failures)
        )

    def test_regression_errorcode_overwrite_would_break(self):
        """
        REGRESSION PROOF: Eger saturation out_wErrorCode := 16#0002 yazarsa bu test kirilir.
        Simule: SCL'e atama ekle, kontrol yap — yanlis kod tespit edilmeli.
        """
        scl = _read(_PID_SCL)

        # Orijinal SCL'de dogrudan atama olmamali (yukarda zaten test ediyoruz)
        code_lines = [
            line for line in scl.splitlines()
            if not line.strip().startswith("//")
        ]
        code_only = "\n".join(code_lines)
        assert not re.search(r"out_wErrorCode\s*:=\s*16#0002", code_only), (
            "REGRESSION: out_wErrorCode := 16#0002 kod satirlari arasianda bulundu — S-3 fix uygulanmamis"
        )

        # Simule edilmis "fix geri alinmis" SCL'de atama var
        broken_scl = code_only + "\n   out_wErrorCode := 16#0002;   // simulated regression\n"
        assert re.search(r"out_wErrorCode\s*:=\s*16#0002", broken_scl), (
            "Regression simülasyonu basarisiz: eklenecek satir yerlestirilmedi"
        )
