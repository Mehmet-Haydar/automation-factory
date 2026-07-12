"""Proof tests — Delta assembly ("add one motor" change management).

Field reality: the most frequent job is not a fresh project but a CHANGE —
a new motor, a renamed valve. Regenerating the whole _output/ for that
clobbers manual tweaks and forces a full re-review. Delta mode:

  - full assemble writes `_assembly_manifest.json` (device → RD01 row hash)
  - compute_delta previews added / changed / removed devices
  - assemble_delta rewrites ONLY affected devices' instance DBs, always
    rebuilds OB_Main.scl (derived), leaves unchanged files byte-for-byte
    alone, and reports removed devices as orphaned — never deletes.
"""
from __future__ import annotations

import json

import pytest

import program_assembler as pa


SIGNALS = [
    {"name": "MOT_CONV_001_FB",  "type": "DI", "address": "%I0.0",
     "desc": "Conveyor run feedback", "raw": ""},
    {"name": "MOT_CONV_001_OL",  "type": "DI", "address": "%I0.1",
     "desc": "Conveyor overload thermal relay", "raw": ""},
    {"name": "MOT_CONV_001_RUN", "type": "DQ", "address": "%Q0.0",
     "desc": "Conveyor motor contactor", "raw": ""},
    {"name": "VLV_WATER_010_ZSO", "type": "DI", "address": "%I1.0",
     "desc": "Water valve open feedback", "raw": ""},
    {"name": "VLV_WATER_010_OPEN", "type": "DQ", "address": "%Q1.0",
     "desc": "Water valve open solenoid", "raw": ""},
]

NEW_MOTOR = [
    {"name": "MOT_MIX_002_FB",  "type": "DI", "address": "%I2.0",
     "desc": "Mixer run feedback", "raw": ""},
    {"name": "MOT_MIX_002_RUN", "type": "DQ", "address": "%Q2.0",
     "desc": "Mixer motor contactor", "raw": ""},
]


@pytest.fixture
def proj(tmp_path):
    res = pa.assemble_program(tmp_path, signals=SIGNALS)
    assert res.ok, res.msg
    return tmp_path


def test_full_assembly_writes_manifest(proj):
    mp = proj / "_output" / "scl" / pa.MANIFEST_NAME
    assert mp.is_file(), "tam koşu manifest yazmalı — delta'nın temel çizgisi"
    man = json.loads(mp.read_text(encoding="utf-8"))
    assert set(man["devices"]) == {"MOT_CONV_001", "VLV_WATER_010"}
    assert all(v["row_hash"] for v in man["devices"].values())


def test_delta_no_change_reports_clean(proj):
    d = pa.compute_delta(proj, signals=SIGNALS)
    assert d["manifest_exists"] is True
    assert d["added"] == [] and d["changed"] == [] and d["removed"] == []
    assert set(d["unchanged"]) == {"MOT_CONV_001", "VLV_WATER_010"}


def test_delta_preview_detects_add_change_remove(proj):
    changed = [dict(s) for s in SIGNALS if s["name"].startswith("MOT_")]
    changed[0] = {**changed[0], "desc": "Conveyor run feedback EDITED"}
    d = pa.compute_delta(proj, signals=changed + NEW_MOTOR)
    assert d["added"] == ["MOT_MIX_002"]
    assert d["changed"] == ["MOT_CONV_001"]
    assert d["removed"] == ["VLV_WATER_010"]


def test_delta_touches_only_affected_files(proj):
    out = proj / "_output" / "scl"
    # Engineer's manual tweak on the UNCHANGED valve DB must survive.
    vlv_db = out / "iDB_VLV_WATER_010.db"
    tweaked = vlv_db.read_text(encoding="utf-8") + "\n// manual site tweak\n"
    vlv_db.write_text(tweaked, encoding="utf-8")
    ob_before = (out / "OB_Main.scl").read_text(encoding="utf-8")

    res = pa.assemble_delta(proj, signals=SIGNALS + NEW_MOTOR)
    assert res.ok, res.msg
    assert res.delta_mode is True
    assert set(res.affected) == {"MOT_MIX_002"}
    assert "VLV_WATER_010" in res.skipped and "MOT_CONV_001" in res.skipped

    # New device generated…
    assert (out / "iDB_MOT_MIX_002.db").is_file()
    # …manual tweak preserved (byte-for-byte)…
    assert vlv_db.read_text(encoding="utf-8") == tweaked, (
        "Delta koşusu DEĞİŞMEMİŞ cihazın dosyasını ezdi — elle yapılan "
        "düzenleme kayboldu (delta'nın varlık sebebi bu)."
    )
    # …and OB_Main rebuilt to include the new device.
    ob_after = (out / "OB_Main.scl").read_text(encoding="utf-8")
    assert ob_after != ob_before
    assert "iDB_MOT_MIX_002" in ob_after
    assert "iDB_MOT_CONV_001" in ob_after, "eski cihaz OB'den düşmemeli"


def test_delta_never_deletes_removed_devices(proj):
    out = proj / "_output" / "scl"
    only_motor = [s for s in SIGNALS if s["name"].startswith("MOT_")]
    res = pa.assemble_delta(proj, signals=only_motor)
    assert res.ok, res.msg
    assert res.orphaned == ["VLV_WATER_010"]
    # Fail-safe: the file still exists; only the report tells the engineer.
    assert (out / "iDB_VLV_WATER_010.db").is_file(), (
        "Delta koşusu kaldırılan cihazın dosyasını SİLDİ — asla otomatik "
        "silinmemeli (fail-safe)."
    )
    assert any("ORPHANED" in w for w in res.warnings)
    # OB_Main no longer calls the removed device.
    ob = (out / "OB_Main.scl").read_text(encoding="utf-8")
    assert "iDB_VLV_WATER_010" not in ob


def test_delta_without_manifest_falls_back_to_full(tmp_path):
    res = pa.assemble_delta(tmp_path, signals=SIGNALS)
    assert res.ok, res.msg
    assert res.delta_mode is False, "manifest yokken tam koşuya düşmeli"
    assert (tmp_path / "_output" / "scl" / pa.MANIFEST_NAME).is_file()


def test_failed_run_does_not_move_baseline(proj, monkeypatch):
    """A delta run that produces validation errors must NOT rewrite the
    manifest — otherwise the pending change disappears from the preview."""
    mp = proj / "_output" / "scl" / pa.MANIFEST_NAME
    before = mp.read_text(encoding="utf-8")

    import scl_validator

    class _Issue:
        severity = "error"
        message = "forced failure"

    class _VR:
        error_count = 1
        warning_count = 0
        issues = [_Issue()]

    monkeypatch.setattr(scl_validator, "validate_scl_file", lambda p: _VR())
    res = pa.assemble_delta(proj, signals=SIGNALS + NEW_MOTOR)
    assert res.ok is False
    assert mp.read_text(encoding="utf-8") == before, (
        "Başarısız koşu manifest'i güncelledi — bekleyen değişiklik önizlemeden kayboldu."
    )
