"""I3 — Bit-adres regex 0-7 araligi _S7_BIT ile tutarli."""

from workbench.core.io_validator import _address_width


def test_valid_bit_addresses():
    for addr in ["%I0.0", "%I0.7", "%Q0.0", "%Q9999.7", "%M0.0", "%M0.7",
                 "I0.0", "Q0.7"]:
        assert _address_width(addr) == "bit", f"{addr!r} should be 'bit'"


def test_invalid_bit_8_and_9_return_none():
    # Bit 8 and 9 are out of range for S7 — must not be classified as 'bit'
    for addr in ["%I0.8", "%I0.9", "%Q0.8", "M0.8"]:
        result = _address_width(addr)
        assert result != "bit", f"{addr!r} should NOT be classified as 'bit' (got {result!r})"


def test_db_bit_valid():
    assert _address_width("DB1.DBX0.0") == "bit"
    assert _address_width("DB1.DBX5.7") == "bit"


def test_db_bit_out_of_range():
    assert _address_width("DB1.DBX0.8") != "bit"


def test_byte_word_dword_unaffected():
    assert _address_width("%IB1") == "byte"
    assert _address_width("%IW2") == "word"
    assert _address_width("%QD3") == "dword"
    assert _address_width("DB1.DBB0") == "byte"
    assert _address_width("DB1.DBW0") == "word"
    assert _address_width("DB1.DBD0") == "dword"


# -- M-A1: S7 peripheral (PIW / PQW / PID) addresses --

def test_peripheral_addresses_validate_as_s7():
    from workbench.core.io_list_io import IORow
    from workbench.core.io_validator import validate_rows
    rows = [
        IORow(tag="F_E_Stop_North",  address="%PIW100", dtype="WORD", direction="DI", safety_related="Y"),
        IORow(tag="F_E_Stop_South",  address="PIW102",  dtype="WORD", direction="DI", safety_related="Y"),
        IORow(tag="Cyl_Cmd",         address="%PQW256", dtype="WORD", direction="DO"),
        IORow(tag="AnalogCh1",       address="PID768",  dtype="REAL", direction="AI"),
        IORow(tag="ByteSlot",        address="PIB512",  dtype="BYTE", direction="DI"),
    ]
    issues = validate_rows(rows, platform="S7_1500")
    # No "does not match S7 syntax" errors on the address column.
    addr_errors = [i for i in issues if i.column == "address" and i.severity == "error" and "S7" in i.message]
    assert addr_errors == [], f"peripheral addresses falsely rejected: {addr_errors}"


def test_peripheral_address_width_and_class():
    from workbench.core.io_validator import _address_class
    assert _address_width("PIW100") == "word"
    assert _address_width("%PQW256") == "word"
    assert _address_width("PID768") == "dword"
    assert _address_width("PIB512") == "byte"
    # PIW is an input -> 'I' class; PQW is an output -> 'Q' class.
    assert _address_class("PIW100") == "I"
    assert _address_class("%PQW256") == "Q"


# ---------------------------------------------------------------------------
# N-M2 — Direction↔Type semantic mismatch + SafetyRelated type warning
# ---------------------------------------------------------------------------

from workbench.core.io_list_io import IORow
from workbench.core.io_validator import validate_rows


class TestDirectionTypeMismatch:
    """N-M2: Direction=DI/DQ + numeric/string Type must produce a warning.
    Without the fix these combinations were silently accepted."""

    def test_di_direction_with_real_type_warns(self):
        row = IORow(tag="Sensor1", address="%I0.0", dtype="REAL", direction="DI")
        issues = validate_rows([row])
        warnings = [i for i in issues if i.severity == "warning" and "direction" in i.message.lower()
                    or (i.severity == "warning" and i.column == "dtype" and "REAL" in i.message)]
        assert warnings, (
            "Direction=DI + Type=REAL combination was NOT warned — N-M2 fix missing"
        )

    def test_dq_direction_with_word_type_warns(self):
        row = IORow(tag="Output1", address="%Q0.0", dtype="WORD", direction="DQ")
        issues = validate_rows([row])
        dtype_warnings = [i for i in issues
                          if i.severity == "warning" and i.column == "dtype"
                          and "WORD" in i.message]
        assert dtype_warnings, (
            "Direction=DQ + Type=WORD combination was NOT warned — N-M2 fix missing"
        )

    def test_di_direction_with_bool_type_no_warning(self):
        row = IORow(tag="Sensor2", address="%I0.1", dtype="BOOL", direction="DI")
        issues = validate_rows([row])
        dtype_warnings = [i for i in issues
                          if i.severity == "warning" and i.column == "dtype"
                          and "digital" in i.message.lower()]
        assert not dtype_warnings, (
            f"BOOL on DI direction should NOT warn about type mismatch: {dtype_warnings}"
        )

    def test_di_direction_with_string_type_warns(self):
        row = IORow(tag="Label1", address="%IW0", dtype="STRING", direction="DI")
        issues = validate_rows([row])
        dtype_warnings = [i for i in issues
                          if i.severity == "warning" and i.column == "dtype"
                          and "STRING" in i.message]
        assert dtype_warnings, (
            "Direction=DI + Type=STRING combination was NOT warned"
        )


class TestSafetyRelatedTypeWarning:
    """S-1 / B-L8: SafetyRelated=Y + non-safety Type must now produce an ERROR
    (escalated from warning per IEC 61508 spirit — fail-closed).  The gate must
    be blocked, not merely flagged, when a safety channel is mislabelled."""

    def test_safety_y_with_di_type_is_error(self):
        """The key S-1 case: SafetyRelated=Y but Type=DI (standard, not F-DI).
        This must produce a gate-blocking ERROR, not just a warning."""
        row = IORow(
            tag="F_E_Stop", address="%I0.0", dtype="DI",
            direction="DI", safety_related="Y"
        )
        issues = validate_rows([row])
        # S-1: severity must be "error", not "warning"
        safety_errors = [i for i in issues
                         if i.severity == "error"
                         and "not a safety type" in i.message.lower()]
        assert safety_errors, (
            "SafetyRelated=Y + Type=DI combination must produce an ERROR "
            "(S-1/B-L8 fail-closed: was warning, promoted to error) — fix missing"
        )

    def test_safety_y_with_f_di_type_no_mismatch_error(self):
        """SafetyRelated=Y + Type=F-DI is consistent; no type-mismatch error."""
        row = IORow(
            tag="F_E_Stop", address="%I0.0", dtype="F-DI",
            direction="DI", safety_related="Y"
        )
        issues = validate_rows([row])
        # Check that there is no "not a safety type" issue at any severity
        type_mismatch = [i for i in issues
                         if "not a safety type" in i.message.lower()]
        assert not type_mismatch, (
            f"F-DI with SafetyRelated=Y should not produce a type mismatch issue: {type_mismatch}"
        )

    def test_safety_n_with_di_type_no_error(self):
        """SafetyRelated=N + Type=DI is a normal row — no safety-type error."""
        row = IORow(
            tag="Sensor1", address="%I0.0", dtype="DI",
            direction="DI", safety_related="N"
        )
        issues = validate_rows([row])
        safety_type_errors = [i for i in issues
                               if "not a safety type" in i.message.lower()]
        assert not safety_type_errors
