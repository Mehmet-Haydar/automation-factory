"""C-A3 regresyonu: hardware_sizer SAFE_* IO'yu non-F-CPU'da standart IO'ya
sessizce dönüştürmemeli.

Önceki davranış:
  is_safety and not is_safety_cpu:
      result.warnings.append(...)
      io_type = io_type.replace("SAFE_", "")   # downgrade
Sonra normal modülle BOM ve customer report üretiliyordu — saha kurulumunda
F-DI yerine standart DI bağlanma riski, SIL/PLr ihlali.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hardware_sizer import (
    IOCount,
    SafetyMisconfigurationError,
    SizerResult,
    generate_sizer_md,
    generate_sizer_xlsx,
    size_modules,
)


def _io_with_safety():
    return IOCount(di=10, dq=8, safe_di=4, safe_dq=2, source="test")


def test_strict_raises_on_safe_io_without_f_cpu():
    io = _io_with_safety()
    with pytest.raises(SafetyMisconfigurationError) as excinfo:
        size_modules(io, platform="S7_1500", cpu="CPU 1515-2 PN", reserve_pct=20)
    msg = str(excinfo.value)
    assert "F-CPU" in msg
    assert "CPU 1515-2 PN" in msg
    # Mention of the unsafe channel count keeps the error actionable.
    assert "6" in msg  # 4 + 2 = 6 safety channels


def test_strict_passes_with_f_cpu():
    io = _io_with_safety()
    res = size_modules(io, platform="S7_1500", cpu="CPU 1515F-2 PN", reserve_pct=20)
    assert not res.errors
    # The SAFE_DI / SAFE_DQ rows did get sized to F-modules.
    types = {rec.io_type for rec in res.recommendations}
    assert "SAFE_DI" in types
    assert "SAFE_DQ" in types


def test_non_strict_records_error_and_drops_safe_rows():
    """run_sizer uses strict_safety=False — we must still flag the error AND
    we MUST NOT sneak the safety channels into a standard-module row."""
    io = _io_with_safety()
    res = size_modules(
        io,
        platform="S7_1500",
        cpu="CPU 1515-2 PN",
        reserve_pct=20,
        strict_safety=False,
    )
    assert res.errors, "expected safety/CPU error to be recorded"
    assert res.safety_misconfigured is True
    # Standard DI/DQ from RD01 may still be sized; safety types must NOT appear
    # under their downgraded standard names with the safety channel counts.
    safe_types = {rec.io_type for rec in res.recommendations}
    assert "SAFE_DI" not in safe_types
    assert "SAFE_DQ" not in safe_types
    # The total channel count for DI must reflect the standard DI input only
    # (10), not the safety channels silently added on top (10 + 4 = 14).
    di_recs = [r for r in res.recommendations if r.io_type == "DI"]
    if di_recs:
        assert di_recs[0].raw_count == 10


def test_no_safe_channels_with_standard_cpu_is_fine():
    io = IOCount(di=8, dq=6, source="test")
    res = size_modules(io, platform="S7_1500", cpu="CPU 1515-2 PN")
    assert not res.errors


def test_bom_xlsx_refuses_when_errors_present(tmp_path: Path):
    """C-A3: even if a caller hands a SizerResult with errors to the BOM
    writer, the writer must refuse — no €21k spreadsheet shipped quietly."""
    res = SizerResult(
        io_count=_io_with_safety(),
        reserve_pct=20,
        platform="S7_1500",
        cpu="CPU 1515-2 PN",
        errors=["unsafe: F-CPU required"],
        safety_misconfigured=True,
    )
    out = tmp_path / "BOM.xlsx"
    assert generate_sizer_xlsx(res, out) is False
    assert not out.exists()


def test_bom_md_refuses_when_errors_present(tmp_path: Path):
    res = SizerResult(
        io_count=_io_with_safety(),
        reserve_pct=20,
        platform="S7_1500",
        cpu="CPU 1515-2 PN",
        errors=["unsafe: F-CPU required"],
        safety_misconfigured=True,
    )
    out = tmp_path / "BOM.md"
    assert generate_sizer_md(res, out) is False
    assert not out.exists()


# ---------------------------------------------------------------------------
# N-C2 — count_from_rd01 SafetyRelated=Y promotion
# ---------------------------------------------------------------------------

from hardware_sizer import count_from_rd01


def _write_rd01(tmp_path: Path, rows: list[str]) -> Path:
    """Write a minimal RD01 IO-list MD with the canonical 15-column header."""
    header = (
        "| Tag | Address | Type | Direction | Equipment | Description | "
        "NormalState | EngUnit | RangeMin | RangeMax | SafetyRelated | "
        "SourceModule | OldTag | Notes | Status |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    p = tmp_path / "RD01_IO_List.md"
    p.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return p


def test_safety_related_y_with_di_type_counts_as_safe_di(tmp_path):
    """N-C2: a row with Type=DI and SafetyRelated=Y must go to safe_di, not di."""
    rows = [
        "| F_E_Stop_N | %I0.0 | DI | DI | Panel | E-Stop | | | | | Y | | | | Active |",
    ]
    p = _write_rd01(tmp_path, rows)
    c = count_from_rd01(p)
    assert c.safe_di == 1, (
        f"Expected safe_di=1 for Type=DI SafetyRelated=Y, got safe_di={c.safe_di} di={c.di}"
    )
    assert c.di == 0, (
        f"Row with SafetyRelated=Y must NOT increment di — got di={c.di}"
    )


def test_safety_related_y_with_dq_type_counts_as_safe_dq(tmp_path):
    """N-C2: a row with Type=DQ and SafetyRelated=Y must go to safe_dq, not dq."""
    rows = [
        "| F_Valve_Out | %Q0.0 | DQ | DQ | Valve | Safety valve | | | | | Y | | | | Active |",
    ]
    p = _write_rd01(tmp_path, rows)
    c = count_from_rd01(p)
    assert c.safe_dq == 1, (
        f"Expected safe_dq=1 for Type=DQ SafetyRelated=Y, got safe_dq={c.safe_dq} dq={c.dq}"
    )
    assert c.dq == 0, f"Row with SafetyRelated=Y DQ must NOT increment dq — got dq={c.dq}"


def test_standard_di_without_safety_flag_counts_normally(tmp_path):
    """N-C2: Type=DI SafetyRelated=N (or empty) must still be counted as di."""
    rows = [
        "| Sensor1 | %I1.0 | DI | DI | Conveyor | Run sensor | | | | | N | | | | Active |",
        "| Sensor2 | %I1.1 | DI | DI | Conveyor | Stop sensor | | | | | | | | | Active |",
    ]
    p = _write_rd01(tmp_path, rows)
    c = count_from_rd01(p)
    assert c.di == 2, f"Expected di=2 for standard DI rows, got di={c.di}"
    assert c.safe_di == 0, f"Expected safe_di=0, got safe_di={c.safe_di}"


def test_explicit_f_di_type_counts_as_safe_di_regardless_of_safety_col(tmp_path):
    """An explicit F-DI type must always go to safe_di, even if SafetyRelated=N."""
    rows = [
        "| F_Guard | %I2.0 | F-DI | DI | Guard | Gate guard | | | | | N | | | | Active |",
    ]
    p = _write_rd01(tmp_path, rows)
    c = count_from_rd01(p)
    assert c.safe_di == 1, f"F-DI type must always be safe_di, got safe_di={c.safe_dq}"
    assert c.di == 0


def test_mixed_safety_and_standard_channels(tmp_path):
    """N-C2: mixed list — standard DI and safety-promoted DI counted correctly."""
    rows = [
        "| F_E_Stop | %I0.0 | DI | DI | Panel | E-Stop | | | | | Y | | | | Active |",
        "| F_Gate   | %I0.1 | DI | DI | Gate  | Gate   | | | | | Y | | | | Active |",
        "| Run_Btn  | %I0.2 | DI | DI | Panel | Run    | | | | | N | | | | Active |",
        "| Stop_Btn | %I0.3 | DI | DI | Panel | Stop   | | | | |   | | | | Active |",
    ]
    p = _write_rd01(tmp_path, rows)
    c = count_from_rd01(p)
    assert c.safe_di == 2, f"Expected safe_di=2, got {c.safe_di}"
    assert c.di == 2,      f"Expected di=2, got {c.di}"


def test_safety_y_di_triggers_safety_misconfigured_without_f_cpu(tmp_path):
    """N-C2 end-to-end: safe_di promoted from DI+SafetyRelated=Y must trigger
    SafetyMisconfigurationError when no F-CPU is configured."""
    from hardware_sizer import size_modules, SafetyMisconfigurationError

    rows = [
        "| F_E_Stop | %I0.0 | DI | DI | Panel | E-Stop | | | | | Y | | | | Active |",
    ]
    p = _write_rd01(tmp_path, rows)
    io = count_from_rd01(p)
    assert io.safe_di == 1, "Precondition: safe_di must be 1 after count_from_rd01"

    with pytest.raises(SafetyMisconfigurationError):
        size_modules(io, platform="S7_1500", cpu="CPU 1515-2 PN", reserve_pct=20)
