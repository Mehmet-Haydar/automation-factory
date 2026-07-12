"""
test_safety_signal_typing.py — Proof tests for S-1 / B-L8 (SAFETY sınıfı)

Doğrulanan davranışlar:
1. iec_tag_generator._detect_type  → SAFE_DI/SAFE_DQ tanıma (tüm varyantlar)
2. generate_tags                   → F_ önekli tag üretimi (io_validator ile tutarlı)
3. io_validator.validate_rows      → SafetyRelated=Y + yanlış tip/önek → ERROR (gate-blocking)
4. hardware_sizer.size_modules     → SAFE IO → F-modül önerisi veya açık uyarı (sessiz değil)
5. Regresyon                       → normal DI/DQ davranışı değişmedi

engineer review required: warning→error escalation per IEC 61508 spirit — fail-closed
Bu testler S-1/B-L8 denetim bulgusunu kapatır; merge öncesi mühendis incelemesi gerekir.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Proje kökü sys.path'e ekle (test runner conf'u yoksa)
_FACTORY_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _FACTORY_ROOT / "05_SCRIPTS"
for _p in [str(_FACTORY_ROOT), str(_SCRIPTS_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# 1) iec_tag_generator._detect_type — SAFE_DI / SAFE_DQ tanıma
# ---------------------------------------------------------------------------

from iec_tag_generator import _detect_type, generate_tags, _tag_prefix_for_type


class TestDetectTypeSafetySignals:
    """_detect_type, güvenlik tiplerini UNK veya DI/DQ olarak değil,
    SAFE_DI / SAFE_DQ olarak döndürmeli."""

    # --- SAFE_DI varyantları ---
    @pytest.mark.parametrize("cell_value", [
        "SAFE_DI",
        "SAFE DI",
        "F-DI",
        "FDI",
        "f-di",
        "safe_di",
        "Safe DI",
    ])
    def test_safe_di_variants_detected(self, cell_value):
        result = _detect_type(cell_value)
        assert result == "SAFE_DI", (
            f"_detect_type({cell_value!r}) returned {result!r}, expected 'SAFE_DI'. "
            "S-1/B-L8 fix: safety IO must be explicitly typed."
        )

    # --- SAFE_DQ varyantları ---
    @pytest.mark.parametrize("cell_value", [
        "SAFE_DQ",
        "SAFE DQ",
        "F-DQ",
        "FDQ",
        "f-dq",
        "safe_dq",
        "Safe DQ",
    ])
    def test_safe_dq_variants_detected(self, cell_value):
        result = _detect_type(cell_value)
        assert result == "SAFE_DQ", (
            f"_detect_type({cell_value!r}) returned {result!r}, expected 'SAFE_DQ'. "
            "S-1/B-L8 fix: safety IO must be explicitly typed."
        )

    def test_safe_di_not_detected_as_plain_di(self):
        """SAFE_DI 'DI' olarak geri dönmemeli — önek kaybolursa tag güvensiz olur."""
        result = _detect_type("SAFE_DI")
        assert result != "DI", (
            "SAFE_DI must NOT be detected as plain 'DI' — "
            "that would strip the safety designation and generate an unsafe tag."
        )

    def test_safe_dq_not_detected_as_plain_dq(self):
        result = _detect_type("SAFE_DQ")
        assert result != "DQ", (
            "SAFE_DQ must NOT be detected as plain 'DQ'."
        )

    def test_safe_di_not_unk(self):
        """Önceki hata: SAFE_DI → UNK (eşleşme yoktu), şimdi SAFE_DI olmalı."""
        result = _detect_type("SAFE_DI")
        assert result != "UNK", (
            "SAFE_DI returned UNK — the fix is not applied. "
            "B-L8 failure mode: E-stop generated as unsafely-named tag."
        )


# ---------------------------------------------------------------------------
# 2) generate_tags — F_ önekli tag üretimi (SAFE_DI / SAFE_DQ)
# ---------------------------------------------------------------------------

class TestGenerateTagsSafetyPrefix:
    """SAFE_DI/SAFE_DQ sinyalleri F_ önekli tag üretmeli; SAFE_DI_ değil."""

    def _make_signal(self, name: str, sig_type: str) -> dict:
        return {"name": name, "type": sig_type, "address": "%I0.0", "desc": "test", "raw": ""}

    def test_safe_di_generates_f_prefix(self):
        signals = [self._make_signal("EStop_North", "SAFE_DI")]
        result = generate_tags(signals)
        assert len(result.tags) == 1
        tag_name = result.tags[0].tag_name
        assert tag_name.startswith("F_"), (
            f"SAFE_DI tag must start with 'F_', got {tag_name!r}. "
            "S-1/B-L8: io_validator checks for F_ prefix — inconsistency = gate failure."
        )
        # Signal type in the record must remain SAFE_DI (not overwritten)
        assert result.tags[0].signal_type == "SAFE_DI"

    def test_safe_dq_generates_f_prefix(self):
        signals = [self._make_signal("SafeValve_Out", "SAFE_DQ")]
        result = generate_tags(signals)
        assert len(result.tags) == 1
        tag_name = result.tags[0].tag_name
        assert tag_name.startswith("F_"), (
            f"SAFE_DQ tag must start with 'F_', got {tag_name!r}."
        )

    def test_safe_di_tag_not_prefixed_with_safe_di(self):
        """Eski hata durumu: prefix='SAFE_DI' → SAFE_DI_ESTOP_N — bu YANLIŞ."""
        signals = [self._make_signal("EStop_N", "SAFE_DI")]
        result = generate_tags(signals)
        tag_name = result.tags[0].tag_name
        assert not tag_name.startswith("SAFE_DI_"), (
            f"Tag {tag_name!r} starts with 'SAFE_DI_' — the type string was used "
            "as a prefix instead of 'F_'. This produces an io_validator error "
            "because F_ prefix is missing."
        )


# ---------------------------------------------------------------------------
# 3) io_validator — SafetyRelated=Y + yanlış tip/önek → ERROR (gate-blocking)
# ---------------------------------------------------------------------------

from workbench.core.io_list_io import IORow
from workbench.core.io_validator import validate_rows


class TestIOValidatorSafetyError:
    """S-1 / B-L8: SafetyRelated=Y + yanlış durum gate-blocking ERROR üretmeli.
    Önceki davranış sadece 'warning' üretiyordu — gate'i bloklamıyordu."""

    def test_safety_y_non_safety_type_produces_error(self):
        """SafetyRelated=Y ama Type=DI (standart) → ERROR (eski: warning)."""
        row = IORow(
            tag="F_E_Stop", address="%I0.0", dtype="DI",
            direction="DI", safety_related="Y"
        )
        issues = validate_rows([row])
        errors = [i for i in issues
                  if i.severity == "error" and "not a safety type" in i.message.lower()]
        assert errors, (
            "SafetyRelated=Y + Type=DI must produce severity='error', not 'warning'. "
            "S-1/B-L8 fail-closed: gate must block, not just flag."
        )

    def test_safety_y_missing_f_prefix_produces_error(self):
        """SafetyRelated=Y ama tag F_ öneksiz → ERROR (eski: warning)."""
        row = IORow(
            tag="E_Stop_N", address="%I0.0", dtype="F-DI",
            direction="DI", safety_related="Y"
        )
        issues = validate_rows([row])
        prefix_errors = [i for i in issues
                         if i.severity == "error"
                         and "f_ prefix" in i.message.lower()]
        assert prefix_errors, (
            "SafetyRelated=Y + missing F_ prefix must produce severity='error'. "
            "An unprefixed safety tag is indistinguishable from standard IO in TIA Safety."
        )

    def test_safety_y_correct_type_and_prefix_no_safety_error(self):
        """SafetyRelated=Y + Type=F-DI + tag F_ önekli → safety hatası YOK."""
        row = IORow(
            tag="F_E_Stop_N", address="%I0.0", dtype="F-DI",
            direction="DI", safety_related="Y"
        )
        issues = validate_rows([row])
        safety_issues = [i for i in issues
                         if "not a safety type" in i.message.lower()
                         or "f_ prefix" in i.message.lower()]
        assert not safety_issues, (
            f"Correct safety row produced unexpected safety issue(s): {safety_issues}"
        )

    def test_safety_y_safe_dq_type_no_mismatch(self):
        """SafetyRelated=Y + Type=SAFE_DQ + F_ önek → hata yok."""
        row = IORow(
            tag="F_Safety_Valve", address="%Q0.0", dtype="SAFE_DQ",
            direction="DQ", safety_related="Y"
        )
        issues = validate_rows([row])
        safety_type_errors = [i for i in issues
                               if "not a safety type" in i.message.lower()]
        assert not safety_type_errors, (
            f"SAFE_DQ with SafetyRelated=Y must not produce type mismatch: {safety_type_errors}"
        )

    def test_no_false_positive_for_standard_di(self):
        """SafetyRelated=N + Type=DI → güvenlik hatası YOK (regresyon koruması)."""
        row = IORow(
            tag="Run_Sensor", address="%I0.1", dtype="DI",
            direction="DI", safety_related="N"
        )
        issues = validate_rows([row])
        safety_errors = [i for i in issues
                         if "not a safety type" in i.message.lower()
                         or "f_ prefix" in i.message.lower()]
        assert not safety_errors, (
            f"Standard DI with SafetyRelated=N must produce no safety errors: {safety_errors}"
        )


# ---------------------------------------------------------------------------
# 4) hardware_sizer — SAFE IO → F-modül önerisi veya açık uyarı (sessiz değil)
# ---------------------------------------------------------------------------

from hardware_sizer import IOCount, size_modules, SafetyMisconfigurationError


class TestHardwareSizerSafeIO:
    """SAFE IO için sessiz davranış yasak — ya F-modül önerilmeli ya açık uyarı."""

    def test_safe_di_on_f_cpu_gets_f_module(self):
        """F-CPU'da SAFE_DI → ET200SP F-DI modülü önerilmeli."""
        io = IOCount(di=4, safe_di=2, source="test")
        res = size_modules(io, platform="S7_1500", cpu="CPU 1515F-2 PN")
        assert not res.errors
        safe_recs = [r for r in res.recommendations if r.io_type == "SAFE_DI"]
        assert safe_recs, (
            "SAFE_DI channels on an F-CPU must produce a SAFE_DI module recommendation. "
            "Silent skip = BOM missing F-module = SIL/PLr gap."
        )
        # Modül adında "F-DI" veya "F_DI" veya "Safety" geçmeli
        mod_name = safe_recs[0].module.name
        assert any(kw in mod_name for kw in ("F-DI", "F_DI", "Safety", "F-DQ")), (
            f"Recommended module for SAFE_DI does not look like an F-module: {mod_name!r}"
        )

    def test_safe_dq_on_f_cpu_gets_f_module(self):
        """F-CPU'da SAFE_DQ → ET200SP F-DQ modülü önerilmeli."""
        io = IOCount(dq=4, safe_dq=2, source="test")
        res = size_modules(io, platform="S7_1500", cpu="CPU 1515F-2 PN")
        assert not res.errors
        safe_recs = [r for r in res.recommendations if r.io_type == "SAFE_DQ"]
        assert safe_recs, (
            "SAFE_DQ channels on an F-CPU must produce a SAFE_DQ module recommendation."
        )

    def test_safe_di_on_platform_without_f_module_warns_explicitly(self):
        """S7_1200 katalogunda F-modül yok → açık 'F-module required' uyarısı çıkmalı.
        Sessiz skip (eski davranış) kabul edilemez."""
        # S7_1200 has no F-modules in the built-in catalog — but first we need
        # an F-CPU marker. Use a fictitious F variant since S7-1200 doesn't have
        # one in the catalog but we want to test the "no F-module found" branch.
        io = IOCount(safe_di=2, source="test")
        # Use strict_safety=False so SafetyMisconfigurationError is not raised
        # (we want to reach the _best_module lookup to test the new warning)
        # We'll use a synthetic CPU that passes the F-CPU check.
        res = size_modules(
            io, platform="S7_1200", cpu="CPU 1212F",
            strict_safety=False
        )
        # Either: explicit F-module warning or an error about CPU mismatch.
        # The key invariant is: NO silent skip (no output at all for the channels).
        safe_recs = [r for r in res.recommendations if r.io_type == "SAFE_DI"]
        f_module_warnings = [w for w in res.warnings if "F-module" in w or "f-module" in w.lower()]
        has_explicit_output = bool(safe_recs or f_module_warnings or res.errors)
        assert has_explicit_output, (
            "SAFE_DI channels must produce EITHER a module recommendation OR an "
            "explicit warning/error — silent skip is not acceptable. "
            "S-1/B-L8: 'SAFE IO requires F-module — not sized automatically'."
        )

    def test_safe_di_non_f_cpu_strict_raises(self):
        """Non-F-CPU + SAFE_DI → SafetyMisconfigurationError (C-A3 regression)."""
        io = IOCount(safe_di=4, source="test")
        with pytest.raises(SafetyMisconfigurationError):
            size_modules(io, platform="S7_1500", cpu="CPU 1515-2 PN")

    def test_safe_di_non_f_cpu_non_strict_records_error(self):
        """Non-strict mode: error kaydedilmeli, sessiz geçmemeli."""
        io = IOCount(safe_di=4, safe_dq=2, source="test")
        res = size_modules(
            io, platform="S7_1500", cpu="CPU 1515-2 PN",
            strict_safety=False
        )
        assert res.errors, "Expected error to be recorded for SAFE_* on non-F-CPU"
        assert res.safety_misconfigured is True


# ---------------------------------------------------------------------------
# 5) Regresyon — normal DI/DQ davranışı değişmedi
# ---------------------------------------------------------------------------

class TestRegressionStandardIO:
    """Normal DI/DQ/AI/AQ sinyalleri S-1 değişikliklerinden etkilenmemeli."""

    def test_plain_di_still_detected(self):
        assert _detect_type("DI") == "DI"
        assert _detect_type("digital input") == "DI"
        assert _detect_type("dijital giriş") == "DI"

    def test_plain_dq_still_detected(self):
        assert _detect_type("DQ") == "DQ"
        assert _detect_type("digital output") == "DQ"

    def test_plain_ai_still_detected(self):
        assert _detect_type("AI") == "AI"
        assert _detect_type("analog input") == "AI"

    def test_plain_aq_still_detected(self):
        assert _detect_type("AQ") == "AQ"
        assert _detect_type("analog output") == "AQ"

    def test_plain_di_generates_di_prefix_tag(self):
        signals = [{"name": "Run_Sensor", "type": "DI", "address": "%I0.0", "desc": "", "raw": ""}]
        result = generate_tags(signals)
        assert result.tags[0].tag_name.startswith("DI_")

    def test_plain_dq_generates_dq_prefix_tag(self):
        signals = [{"name": "Motor_Out", "type": "DQ", "address": "%Q0.0", "desc": "", "raw": ""}]
        result = generate_tags(signals)
        assert result.tags[0].tag_name.startswith("DQ_")

    def test_standard_di_io_validator_no_safety_error(self):
        row = IORow(tag="Run_OK", address="%I1.0", dtype="DI", direction="DI", safety_related="N")
        issues = validate_rows([row])
        assert all(
            "not a safety type" not in i.message.lower()
            and "f_ prefix" not in i.message.lower()
            for i in issues
        ), f"Standard DI produced unexpected safety issue: {issues}"

    def test_standard_sizing_unchanged(self):
        io = IOCount(di=10, dq=8, ai=4, source="test")
        res = size_modules(io, platform="S7_1500", cpu="CPU 1515-2 PN")
        assert not res.errors
        di_recs = [r for r in res.recommendations if r.io_type == "DI"]
        assert di_recs, "Standard DI must still be sized"
        assert di_recs[0].raw_count == 10


# ---------------------------------------------------------------------------
# 6) _tag_prefix_for_type helper — doğrudan birim testi
# ---------------------------------------------------------------------------

class TestTagPrefixForType:
    def test_safe_di_maps_to_f(self):
        assert _tag_prefix_for_type("SAFE_DI") == "F"

    def test_safe_dq_maps_to_f(self):
        assert _tag_prefix_for_type("SAFE_DQ") == "F"

    def test_di_maps_to_di(self):
        assert _tag_prefix_for_type("DI") == "DI"

    def test_dq_maps_to_dq(self):
        assert _tag_prefix_for_type("DQ") == "DQ"

    def test_unk_maps_to_empty(self):
        assert _tag_prefix_for_type("UNK") == ""
