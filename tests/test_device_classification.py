"""S-8 (B-P3 + B-L10) — device/platform identity coverage.

B-P3: PUMP/FAN/CONV/COMP — the most common motor-driven loads in real
retrofits — fell to #UNKNOWN because only MOT/MTR/MOTOR prefixes were
recognised. B-L10: the platform badge scanned ``_input/`` while the
pre-analysis pipeline read ``_raw/legacy_code/`` — two diverging truths.
"""

from __future__ import annotations

import importlib
import inspect

from program_assembler import Device, _classify_device


def _dev(prefix, desc, signals=None):
    d = Device(device_id=f"{prefix}_001_X", prefix=prefix, description=desc)
    d.signals.extend(signals or [{"desc": "", "type": "DI"}])
    return d


class TestMotorLoadPrefixes:
    def test_pump_fan_conv_comp_classify_as_motor(self):
        for prefix in ("PUMP", "PUMPE", "PMP", "FAN", "CONV", "CNV",
                       "COMP", "KOMP", "LUEFTER"):
            assert _classify_device(_dev(prefix, "")) == "FB_Motor_DOL", (
                f"{prefix} #UNKNOWN'a düştü — B-P3 geri geldi")

    def test_pump_with_vfd_keyword(self):
        assert _classify_device(_dev("PUMP", "Kühlwasserpumpe mit FU")) == "FB_Motor_VFD"

    def test_classic_motor_prefixes_unchanged(self):
        assert _classify_device(_dev("MOT", "")) == "FB_Motor_DOL"
        assert _classify_device(_dev("MTR", "Stern-Dreieck Anlauf")) == "FB_Motor_StarDelta"


class TestDescriptionFallback:
    def test_unknown_prefix_with_pump_description(self):
        assert _classify_device(_dev("M1", "Pumpe Kühlwasser")) == "FB_Motor_DOL"

    def test_unknown_prefix_with_conveyor_description(self):
        assert _classify_device(_dev("X9", "Förderband 3 Antrieb")) == "FB_Motor_DOL"

    def test_german_ventil_is_not_a_motor(self):
        # "Ventil" = valve — must never land in the motor family. (Since the
        # device lexicon it classifies CORRECTLY as a valve; before it was
        # merely guarded to None.)
        got = _classify_device(_dev("XX", "Magnetventil Wasser"))
        assert got == "FB_Valve_OnOff", got
        assert got is None or not got.startswith("FB_Motor"), (
            "Ventil motor ailesine düştü — Almanca sözlük regresyonu")

    def test_pid_wins_over_motor_fallback(self):
        # A controller that merely mentions a pump stays a PID wrapper.
        assert _classify_device(
            _dev("TC", "PID controller for pump speed")) == "FB_PID_Wrapper"

    def test_analog_device_stays_analog(self):
        d = _dev("PT", "pressure", signals=[{"desc": "", "type": "AI"}])
        assert _classify_device(d) == "FB_AnalogScale"

    def test_truly_unknown_still_unknown(self):
        assert _classify_device(_dev("ZZ", "limit switch bracket")) is None


class TestSingleScanAuthority:
    def test_scan_covers_raw_legacy_dir(self, tmp_path):
        from platform_detector import scan_input_folder
        raw = tmp_path / "_raw" / "legacy_code"
        raw.mkdir(parents=True)
        (raw / "old.awl").write_text("STEP 5\nU E 1.0\nSPB =M001\n",
                                     encoding="utf-8")
        scan = scan_input_folder(tmp_path / "_input", extra_dirs=[raw])
        assert scan.files, "_raw/legacy_code dosyaları taramaya girmedi"
        assert "S5" in scan.detected_platforms, scan.detected_platforms

    def test_scan_without_extra_dirs_unchanged(self, tmp_path):
        from platform_detector import scan_input_folder
        inp = tmp_path / "_input"
        inp.mkdir()
        (inp / "prog.scl").write_text("FUNCTION_BLOCK FB1", encoding="utf-8")
        scan = scan_input_folder(inp)
        assert scan.files

    def test_analyzer_passes_raw_dir(self):
        pa = importlib.import_module("project_analyzer")
        src = inspect.getsource(pa.analyze_project)
        assert "extra_dirs" in src and "legacy_code" in src, (
            "platform rozeti yine yalnız _input/ okuyor — iki doğruluk kaynağı")
