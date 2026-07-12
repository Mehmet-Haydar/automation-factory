"""R-S-1 proof test — merkezi is_f_cpu() yardımcısı.

Bu test iki şeyi kanıtlar:
1. is_f_cpu() doğru True/False kararı verir (en az 10 case).
2. 4 çağrı noktasının hepsi is_f_cpu()'ya yönlendirilmiş — eski inline
   pattern'ler kaldırılmış (fix geri alınırsa bu testler KIRILIR).

Fix geri alınma senaryosu:
  - is_f_cpu() kaldırılırsa → import hatası → TÜM testler KIRILIR.
  - Çağrı noktası eski pattern'e döndürülürse → callsite testleri KIRILIR.
"""

from __future__ import annotations

import importlib
import re
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# 1. Temel birim testler — is_f_cpu() doğruluğu
# ---------------------------------------------------------------------------

from workbench.core.safety_utils import is_f_cpu


class TestIsFCpuTrue:
    """Bilinen F-CPU model adları → True bekleniyor."""

    def test_1515tf(self):
        assert is_f_cpu("CPU 1515TF-2 PN") is True, "TF modeli tanınmalı"

    def test_1518f_bare(self):
        assert is_f_cpu("CPU 1518F") is True, "Sondaki F (tire yok) tanınmalı"

    def test_1516pro_f_space(self):
        assert is_f_cpu("CPU 1516pro F") is True, "Boşluk + sondaki F tanınmalı"

    def test_317f_2(self):
        assert is_f_cpu("CPU 317F-2") is True, "Tire + F orta konum tanınmalı"

    def test_1515f_2_pn(self):
        assert is_f_cpu("CPU 1515F-2 PN") is True, "Klasik S7-1500F formu"

    def test_sf_prefix_upper(self):
        assert is_f_cpu("SF314C-2 PN/DP") is True, "SF ön-eki S7-300 ailesi"

    def test_sf_word_boundary(self):
        assert is_f_cpu("CPU SF 3xx") is True, "SF kelime sınırı"

    def test_lowercase_f(self):
        assert is_f_cpu("cpu 1518f") is True, "Küçük harf insensitive"

    def test_tf_word(self):
        assert is_f_cpu("CPU 1515TF") is True, "TF eki (kelime sınırı)"

    def test_f_dash_suffix(self):
        assert is_f_cpu("CPU 315F-2 PN/DP") is True, "S7-300 F-CPU"


class TestIsFCpuFalse:
    """Standart (non-safety) CPU'lar → False bekleniyor."""

    def test_1516_3_pn_dp(self):
        assert is_f_cpu("CPU 1516-3 PN/DP") is False, "Standart 1516 F-CPU değil"

    def test_simatic_pc(self):
        assert is_f_cpu("SIMATIC PC") is False, "PC platformu F-CPU değil"

    def test_empty_string(self):
        assert is_f_cpu("") is False, "Boş string → fail-safe False"

    def test_none(self):
        assert is_f_cpu(None) is False, "None → fail-safe False"

    def test_1515_2_pn(self):
        assert is_f_cpu("CPU 1515-2 PN") is False, "Sayı içinde F harfi yok"

    def test_standard_317(self):
        assert is_f_cpu("CPU 317-2 PN/DP") is False, "S7-300 standart CPU"

    def test_profinet_io_device(self):
        assert is_f_cpu("ET200SP IM 155-6 PN HF") is False, "IO cihazı CPU değil"

    def test_fc_block_name_not_cpu(self):
        # "FC" blok adı F-CPU ile karıştırılmamalı.
        # is_f_cpu bağımsız çalışır; bu string F-CPU adlandırma kalıbı taşımıyor.
        assert is_f_cpu("FC_ConveyorCtrl") is False, "FC blok adı F-CPU sayılmaz"

    def test_ford_brand_unrelated(self):
        assert is_f_cpu("FORD FOCUS") is False, "Alakasız string False döner"


# ---------------------------------------------------------------------------
# 2. Callsite testleri — çağrı noktaları is_f_cpu()'ya yönleniyor mu?
# ---------------------------------------------------------------------------
# Fikir: is_f_cpu fonksiyonunu mock ile izleyip çağrı noktası
# kodunun onu kullandığını kanıtlıyoruz. Mock olmadan eski inline
# pattern'ler farklı davranır; tespit edilir.

# --- 2a. hardware_sizer: size_modules → is_f_cpu çağrıları ---

def test_hardware_sizer_uses_is_f_cpu_for_safety_check():
    """size_modules, F-CPU tespiti için is_f_cpu()'yu çağırıyor olmalı.
    Eğer eski inline pattern'e dönülürse mock bypass edilir → test KIRILIR.
    """
    from workbench.core.safety_utils import is_f_cpu as real_fn
    import hardware_sizer as hs

    called_with = []

    def tracking_fn(cpu_model):
        called_with.append(cpu_model)
        return real_fn(cpu_model)

    # hardware_sizer kendi modül namespace'inde _is_f_cpu adıyla import etti
    with patch.object(hs, "_is_f_cpu", side_effect=tracking_fn):
        from hardware_sizer import IOCount, size_modules, SafetyMisconfigurationError
        io = IOCount(di=2, dq=2, source="test")
        size_modules(io, platform="S7_1500", cpu="CPU 1515F-2 PN", reserve_pct=20)

    assert called_with, (
        "hardware_sizer.size_modules _is_f_cpu'yu çağırmadı — "
        "inline pattern'e geri mi döndü? (R-S-1 fix geri alındı)"
    )
    assert "CPU 1515F-2 PN" in called_with


def test_hardware_sizer_fcpu_correct_true():
    """CPU 1515F-2 PN → F-CPU olarak tanınmalı → SafetyMisconfigurationError fırlatılmamalı."""
    from hardware_sizer import IOCount, size_modules
    io = IOCount(di=2, dq=2, safe_di=1, source="test")
    res = size_modules(io, platform="S7_1500", cpu="CPU 1515F-2 PN", reserve_pct=20)
    assert not res.errors, f"F-CPU ile safe IO kabul edilmeli: {res.errors}"


def test_hardware_sizer_non_fcpu_raises_with_safe_io():
    """CPU 1515-2 PN (standart) + safe_di → SafetyMisconfigurationError."""
    from hardware_sizer import IOCount, size_modules, SafetyMisconfigurationError
    io = IOCount(di=2, dq=2, safe_di=1, source="test")
    with pytest.raises(SafetyMisconfigurationError):
        size_modules(io, platform="S7_1500", cpu="CPU 1515-2 PN", reserve_pct=20)


# --- 2b. script_protocol_generator: _build_precheck_items → is_f_cpu çağrısı ---

def test_protocol_generator_uses_is_f_cpu():
    """_build_prechecks F-CPU tespiti için _is_f_cpu'yu çağırmalı."""
    import script_protocol_generator as spg

    called_with = []

    def tracking_fn(cpu_model):
        called_with.append(cpu_model)
        from workbench.core.safety_utils import is_f_cpu
        return is_f_cpu(cpu_model)

    state = {"target_cpu": "CPU 1518F", "target_platform": "S7_1500", "target_tia_version": "V19"}
    with patch.object(spg, "_is_f_cpu", side_effect=tracking_fn):
        spg._build_prechecks(state)

    assert called_with, (
        "script_protocol_generator._build_prechecks _is_f_cpu çağırmadı — "
        "inline pattern'e geri mi döndü? (R-S-1 fix geri alındı)"
    )


def test_protocol_generator_f_cpu_adds_safety_check():
    """F-CPU verildiğinde Safety Consistency Check adımı eklenmeli."""
    import script_protocol_generator as spg
    state = {"target_cpu": "CPU 1515F-2 PN", "target_platform": "S7_1500", "target_tia_version": "V19"}
    items = spg._build_prechecks(state)
    descriptions = [i.description for i in items]
    assert any("Consistency Check" in d or "F-CPU" in d for d in descriptions), (
        "F-CPU için FAT/SAT protokolüne safety consistency check adımı eklenmeli"
    )


def test_protocol_generator_non_f_cpu_no_safety_check():
    """Standart CPU'da Safety Consistency Check adımı eklenmemeli."""
    import script_protocol_generator as spg
    state = {"target_cpu": "CPU 1516-3 PN/DP", "target_platform": "S7_1500", "target_tia_version": "V19"}
    items = spg._build_prechecks(state)
    descriptions = [i.description for i in items]
    assert not any("Consistency Check" in d for d in descriptions), (
        "Standart CPU'da F-CPU consistency check adımı olmamalı"
    )


# --- 2c. tia_export: _build_checklist → is_f_cpu çağrısı ---

def test_tia_export_uses_is_f_cpu():
    """_build_checklist F-CPU tespiti için _is_f_cpu'yu çağırmalı."""
    import tia_export as te

    called_with = []

    def tracking_fn(cpu_model):
        called_with.append(cpu_model)
        from workbench.core.safety_utils import is_f_cpu
        return is_f_cpu(cpu_model)

    state = {"target_cpu": "CPU 1518F", "target_platform": "S7_1500"}
    with patch.object(te, "_is_f_cpu", side_effect=tracking_fn):
        # imza: _build_checklist(project_path, state, scl_files)
        te._build_checklist(Path("/nonexistent_dummy"), state, [])

    assert called_with, (
        "tia_export._build_checklist _is_f_cpu çağırmadı — "
        "inline pattern'e geri mi döndü? (R-S-1 fix geri alındı)"
    )


def test_tia_export_f_cpu_adds_safety_checklist_item():
    """F-CPU ile _build_checklist Safety satırları içermeli."""
    import tia_export as te
    state = {"target_cpu": "CPU 1518F", "target_platform": "S7_1500"}
    # imza: _build_checklist(project_path, state, scl_files)
    items = te._build_checklist(Path("/dummy"), state, [])
    safety_items = [i for i in items if i.category == "Safety"]
    assert safety_items, "F-CPU için checklist'e Safety kalemleri eklenmeli"


def test_tia_export_non_f_cpu_no_false_positive():
    """'CPU 1516-3 PN/DP' standart CPU → Safety checklist kalemi olmamalı.
    Bu test özellikle eski `'F' in cpu.upper()` pattern'ının aşırı genişliğini
    doğrular: daraltılmış regex standart CPU'yu yanlış sınıflandırmamalı (R-S-1).
    """
    import tia_export as te
    state = {"target_cpu": "CPU 1516-3 PN/DP", "target_platform": "S7_1500"}
    items = te._build_checklist(Path("/dummy"), state, [])
    safety_items = [i for i in items if i.category == "Safety"]
    assert not safety_items, (
        "Standart CPU için Safety checklist kalemi olmamalı — "
        "eski 'F in cpu.upper()' daraltıldı (R-S-1)"
    )


# --- 2d. prompt_meta: F-CPU uyarı satırı is_f_cpu'ya bağlı mı? ---

def test_prompt_meta_uses_is_f_cpu():
    """build_smart_brief F-CPU tespiti için _is_f_cpu'yu çağırmalı."""
    import prompt_meta as pm
    import tempfile, json as _json

    called_with = []

    def tracking_fn(cpu_model):
        called_with.append(cpu_model)
        from workbench.core.safety_utils import is_f_cpu
        return is_f_cpu(cpu_model)

    # Eğer eski inline pattern'e dönüldüyse bu mock bypass edilir ve
    # called_with boş kalır → test KIRILIR.
    state_data = {"target_cpu": "CPU 1515F-2 PN", "target_platform": "S7_1500"}

    with tempfile.TemporaryDirectory() as td:
        project_path = Path(td)
        (project_path / "PROJECT_STATE.json").write_text(
            _json.dumps(state_data), encoding="utf-8"
        )

        # Minimal PromptMeta ile build_smart_brief çağırıyoruz
        meta = pm.PromptMeta(name="test", path=project_path / "dummy_prompt.md")

        with patch.object(pm, "_is_f_cpu", side_effect=tracking_fn):
            try:
                pm.build_smart_brief(meta, "# test prompt", project_path=project_path)
            except Exception:
                pass  # dosya eksik olabilir — çağrının gerçekleşmesi yeterli

    assert called_with, (
        "prompt_meta.build_smart_brief _is_f_cpu çağırmadı — "
        "inline pattern'e geri mi döndü? (R-S-1 fix geri alındı)"
    )
