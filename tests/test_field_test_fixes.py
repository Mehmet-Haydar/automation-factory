"""Proof tests — findings from the REAL-AI field test (2026-07-02).

A synthetic 1998 Mischanlage (19 signals, German legacy naming) was run
through the live pipeline with DeepSeek+Gemini. Three defects surfaced and
are pinned here:

F-2  Fresh project displayed gate 7/7 with ZERO signatures — _effective_gate
     trusted the doc-derived position when the stored counter was 0/absent.
F-1  create_project happily created outside the O-2 whitelist; open_project
     then refused the very same path.
B-03 All 19 realistic legacy tags (K1, F_M1, LSL_B1 …) fell to #UNKNOWN.
     Fixes: RD01 Equipment-column fallback grouping + German compound-noun
     classification ("Dosierpumpe") + German electrical synonyms
     (Schuetz=contactor→run, Motorschutz→overload).
"""
from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw
import program_assembler as pa


# ---------------------------------------------------------------------------
# F-2 — no phantom gate progression
# ---------------------------------------------------------------------------

def test_fresh_project_with_all_drafts_is_gate_1():
    all_done = {f"RD{n:02d}": "done" for n in range(1, 15)}
    assert fw._effective_gate(0, all_done) == 1, (
        "F-2 regresyonu: sayaçsız taze proje, taslaklar yazılınca gate 7/7 "
        "görünüyordu — hiç imza yokken ilerleme iddia edilemez."
    )
    # The stored counter still self-heals DOWNWARD (inflated legacy counter)…
    partial = dict(all_done); partial["RD05"] = "empty"
    assert fw._effective_gate(5, partial) == 2
    # …and an honestly-advanced project keeps its position.
    assert fw._effective_gate(4, all_done) == 4


# ---------------------------------------------------------------------------
# F-1 — create/open whitelist consistency
# ---------------------------------------------------------------------------

def test_create_project_records_projects_folder(tmp_path, monkeypatch):
    api = fw.Api()
    api.settings = {"username": "Eng"}
    monkeypatch.setattr(fw, "_save_settings", lambda s: None)
    r = api.create_project("blank", "WhitelistTest", str(tmp_path),
                           {"data_classification": "PUBLIC"})
    assert r["ok"], r
    assert api.settings.get("projects_folder") == str(tmp_path), (
        "F-1 regresyonu: whitelist dışında yaratılan proje projects_folder'a "
        "kaydedilmedi — open_project aynı projeyi reddeder."
    )
    # And open_project now accepts it.
    assert api._check_open_project_path(Path(r["path"])) is None


def test_new_project_state_seeds_gate_1(tmp_path, monkeypatch):
    api = fw.Api()
    api.settings = {}
    monkeypatch.setattr(fw, "_save_settings", lambda s: None)
    r = api.create_project("blank", "GateSeed", str(tmp_path), {})
    st = json.loads((Path(r["path"]) / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    assert st.get("gate") == 1


# ---------------------------------------------------------------------------
# B-03 — Equipment-column fallback grouping
# ---------------------------------------------------------------------------

MISCHANLAGE = [
    {"name": "F_M1",   "type": "DI", "address": "%I0.3", "equipment": "M1",
     "desc": "Motorschutz Foerderband M1", "raw": ""},
    {"name": "K1_RM",  "type": "DI", "address": "%I0.4", "equipment": "M1",
     "desc": "Rueckmeldung Schuetz K1", "raw": ""},
    {"name": "K1",     "type": "DQ", "address": "%Q4.0", "equipment": "M1",
     "desc": "Schuetz Foerderband M1", "raw": ""},
    {"name": "LSL_B1", "type": "DI", "address": "%I0.5", "equipment": "P1",
     "desc": "Fuellstand min Tank B1", "raw": ""},
    {"name": "FU_STO", "type": "DI", "address": "%I0.6", "equipment": "P1",
     "desc": "Stoerung Frequenzumrichter P1", "raw": ""},
    {"name": "FU_FREI", "type": "DQ", "address": "%Q4.1", "equipment": "P1",
     "desc": "Freigabe FU Dosierpumpe P1", "raw": ""},
    {"name": "Y1",     "type": "DQ", "address": "%Q4.4", "equipment": "Y1",
     "desc": "Magnetventil Wasser", "raw": ""},
    # station-level: plant id must NOT group (dash rejects it)
    {"name": "S_NotAus", "type": "DI", "address": "%I0.0", "equipment": "MA-3",
     "desc": "NOT-AUS Kanal 1", "raw": ""},
]


def test_equipment_column_groups_legacy_tags():
    devices, loose = pa.group_devices(MISCHANLAGE)
    ids = {d.device_id for d in devices}
    assert ids == {"M1", "P1", "Y1"}, (
        f"B-03 regresyonu: Equipment kolonu gruplaması çalışmıyor — {ids}"
    )
    loose_names = {s["name"] for s in loose}
    assert loose_names == {"S_NotAus"}, (
        "İstasyon kimliği (MA-3) cihaz gibi gruplanmamalı"
    )


def test_station_sized_equipment_group_stays_unknown():
    sigs = [{"name": f"X{i}", "type": "DI", "address": "", "equipment": "MA3",
             "desc": "Pumpe irgendwas", "raw": ""} for i in range(8)]
    devices, loose = pa.group_devices(sigs)
    assert devices == [], (
        f"{pa._EQUIP_GROUP_MAX_SIGNALS}+ sinyalli ekipman grubu tek motor "
        "olarak sınıflandırılamaz — istasyon riski."
    )
    assert len(loose) == 8


def test_german_compound_pump_classifies_as_vfd():
    devices, _ = pa.group_devices(MISCHANLAGE)
    p1 = next(d for d in devices if d.device_id == "P1")
    assert pa._classify_device(p1) == "FB_Motor_VFD", (
        "'Dosierpumpe' bileşik kelimesi + 'Frequenzumrichter' → VFD motor "
        "sınıflandırması yapılmalı (Almanca bileşik-isim regresyonu)."
    )


def test_german_synonyms_bind_schuetz_and_motorschutz(tmp_path):
    res = pa.assemble_program(tmp_path, signals=MISCHANLAGE)
    assert res.ok, res.msg
    m1 = next(m for m in res.matches if m.device.device_id == "M1")
    assert m1.in_bindings.get("in_bFeedbackOverload") == "F_M1", (
        "'Motorschutz' overload eş anlamlısı olarak bağlanmalı"
    )
    bound_outputs = set(m1.out_bindings.values())
    assert "K1" in bound_outputs, (
        "'Schuetz' (kontaktör) çıkışı run/main portuna bağlanmalı"
    )


def test_real_field_set_end_to_end(tmp_path):
    """The full Mischanlage set: 3 devices matched, station signals honest."""
    res = pa.assemble_program(tmp_path, signals=MISCHANLAGE)
    stems = {m.contract_stem for m in res.matches}
    assert stems == {"FB_Motor_DOL", "FB_Motor_VFD", "FB_Valve_OnOff"}
    unknown_items = {u["item"] for u in res.unknown}
    assert "S_NotAus" in unknown_items  # never silently dropped
