"""M3 — library-first program assembler.

End-to-end against the REAL curated library: synthetic RD01 signals in →
verbatim block copies + instance DBs + OB1 with bindings out, everything
passing scl_validator (incl. the STRUCTURAL_BUG rule) and the contract
acceptance gate. Unknowns must surface, never vanish.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import program_assembler as pa
from ob1_generator import InstanceCall, generate_instance_db, generate_ob1_from_instances
from scl_validator import validate_scl


SIGNALS = [
    {"name": "MOT_CONV_001_FB",   "type": "DI", "address": "%I0.0",
     "desc": "Conveyor run feedback", "raw": ""},
    {"name": "MOT_CONV_001_OL",   "type": "DI", "address": "%I0.1",
     "desc": "Conveyor overload thermal relay", "raw": ""},
    {"name": "MOT_CONV_001_RUN",  "type": "DQ", "address": "%Q0.0",
     "desc": "Conveyor motor contactor", "raw": ""},
    {"name": "VLV_WATER_010_ZSO", "type": "DI", "address": "%I1.0",
     "desc": "Water valve open feedback", "raw": ""},
    {"name": "VLV_WATER_010_OPEN", "type": "DQ", "address": "%Q1.0",
     "desc": "Water valve open solenoid", "raw": ""},
    {"name": "XYZ_WEIRD_099_X",   "type": "DI", "address": "%I9.9",
     "desc": "mystery device", "raw": ""},
    {"name": "freeform tag",      "type": "DI", "address": "",
     "desc": "not following naming standard", "raw": ""},
]


@pytest.fixture(scope="module")
def assembled(tmp_path_factory):
    proj = tmp_path_factory.mktemp("proj")
    res = pa.assemble_program(proj, signals=SIGNALS)
    return proj, res


class TestMapping:
    def test_motor_and_valve_matched(self, assembled):
        _proj, res = assembled
        stems = {m.contract_stem for m in res.matches}
        assert "FB_Motor_DOL" in stems
        assert "FB_Valve_OnOff" in stems

    def test_unknowns_surface_never_dropped(self, assembled):
        _proj, res = assembled
        items = {u["item"] for u in res.unknown}
        assert "XYZ_WEIRD_099" in items, "unmapped device must appear in #UNKNOWN"
        assert "freeform tag" in items, "non-standard tag must appear in #UNKNOWN"

    def test_motor_field_bindings(self, assembled):
        _proj, res = assembled
        mot = next(m for m in res.matches if m.device.device_id == "MOT_CONV_001")
        assert mot.in_bindings.get("in_bFeedbackRun") == "MOT_CONV_001_FB"
        assert mot.in_bindings.get("in_bFeedbackOverload") == "MOT_CONV_001_OL"
        assert "MOT_CONV_001_RUN" in mot.out_bindings.values()

    def test_control_ports_left_default_not_guessed(self, assembled):
        _proj, res = assembled
        mot = next(m for m in res.matches if m.device.device_id == "MOT_CONV_001")
        bound_ports = set(mot.in_bindings) | set(mot.out_bindings)
        for forbidden in ("in_bStartCmd", "in_bStopCmd", "in_bEnable",
                          "in_bReset", "in_bManualMode"):
            assert forbidden not in bound_ports, (
                f"{forbidden} is control logic — must never be wired to field IO")


class TestVerbatimCopy:
    def test_copies_are_verbatim_sha_proven(self, assembled):
        _proj, res = assembled
        assert res.copied, "matched blocks must be copied"
        assert all(c["verbatim"] for c in res.copied)

    def test_system_blocks_always_included(self, assembled):
        proj, res = assembled
        names = {c["name"] for c in res.copied}
        for required in ("FB_ModeManager.scl", "FB_Watchdog.scl",
                         "FB_AlarmHandler.scl", "OB_Startup_OB100.scl"):
            assert required in names

    def test_no_ai_generated_device_logic(self, assembled):
        proj, res = assembled
        out = proj / "_output" / "scl"
        lib_shas = {c["name"]: c["sha256"] for c in res.copied}
        for name, sha in lib_shas.items():
            assert pa._sha256(out / name) == sha


class TestGeneratedSources:
    def test_instance_dbs_generated(self, assembled):
        proj, res = assembled
        out = proj / "_output" / "scl"
        db = out / "iDB_MOT_CONV_001.db"
        assert db.is_file()
        text = db.read_text(encoding="utf-8")
        assert 'DATA_BLOCK "iDB_MOT_CONV_001"' in text
        mot = next(m for m in res.matches if m.device.device_id == "MOT_CONV_001")
        assert f'"{mot.fb_block_name}"' in text, "DB must reference the FB by its declared name"

    def test_ob1_calls_instance_dbs_no_static_var(self, assembled):
        proj, _res = assembled
        ob1 = (proj / "_output" / "scl" / "OB_Main.scl").read_text(encoding="utf-8")
        assert '"iDB_MOT_CONV_001"(' in ob1
        assert 'in_bFeedbackRun := "MOT_CONV_001_FB"' in ob1
        assert '=> "MOT_CONV_001_RUN"' in ob1
        # the old generator declared FB instances in an OB VAR block — invalid in TIA
        assert "\nVAR\n" not in ob1.replace("VAR_TEMP", "VARTEMP_MASKED")

    def test_todos_visible_in_ob1(self, assembled):
        proj, _res = assembled
        ob1 = (proj / "_output" / "scl" / "OB_Main.scl").read_text(encoding="utf-8")
        assert "TODO(#UNKNOWN)" in ob1


class TestValidationAndGate:
    def test_all_assembled_scl_structurally_clean(self, assembled):
        _proj, res = assembled
        bad = [v for v in res.validation if v["errors"]]
        assert not bad, f"assembled SCL must validate clean: {bad}"

    def test_copied_blocks_pass_contract_gate(self, assembled):
        _proj, res = assembled
        assert res.gate_results, "contract gate must run for copied blocks"
        failed = [g for g in res.gate_results if g["overall"] != "PASS"]
        assert not failed, f"library drift detected: {failed}"

    def test_overall_ok(self, assembled):
        _proj, res = assembled
        assert res.ok, res.msg


class TestReport:
    def test_report_written_with_unknown_section(self, assembled):
        proj, res = assembled
        assert res.report_path and res.report_path.is_file()
        text = res.report_path.read_text(encoding="utf-8")
        assert "#UNKNOWN" in text
        assert "XYZ_WEIRD_099" in text
        assert "PENDING_TIA_VERIFY" in text, "label honesty must survive in the report"
        assert "SHA-256" in text


class TestEmptyRd01:
    def test_empty_signal_list_fails_loud(self, tmp_path):
        res = pa.assemble_program(tmp_path, signals=[])
        assert not res.ok
        assert "RD01" in res.msg


class TestOb1GeneratorUnits:
    def test_instance_db_source_shape(self):
        src = generate_instance_db("iDB_X", "FB_MOTOR_DOL")
        assert src.startswith('DATA_BLOCK "iDB_X"')
        assert '"FB_MOTOR_DOL"' in src
        assert src.rstrip().endswith("END_DATA_BLOCK")

    def test_ob1_from_instances_validates(self):
        calls = [InstanceCall(instance_db="iDB_A", fb_name="FB_X",
                              in_bindings={"in_b": "TAG_A"},
                              out_bindings={"out_b": "TAG_B"},
                              todos=["wire in_c"])]
        src = generate_ob1_from_instances(calls)
        vr = validate_scl(src)
        assert vr.error_count == 0, [i.message for i in vr.issues]
