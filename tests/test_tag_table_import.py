"""IO tag table -> TIA Openness wiring (M4 follow-up).

Covers the three layers added when the orphaned tia_tag_export.py was
connected to the Openness bridge:

  1. XML format — Openness V14+ import shape (SW.Tags.PlcTagTable, unique
     IDs, MultilingualText comments with the project's output language).
     The old SW.PlcTagTable shape is the V13 format and TIA V19 rejects it.
  2. Bridge — tag table imported BEFORE the SCL sources; a tag failure is
     a loud warning, never an abort (blocks must still import).
  3. factory_web — _prepare_tag_xml never raises and explains every skip.

No TIA Portal in CI — the Openness core is faked at the bridge seam.
"""

from __future__ import annotations

import importlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tia_tag_export import run_export

fw = importlib.import_module("factory_web")


_HW03 = """# HW03 IEC Tags

| IEC Tag Name | Type | Address | Original Name | Description |
|--------------|------|---------|---------------|-------------|
| Motor_Start  | DI   | %I0.0   | MOTOR START   | Start button |
| Motor_Run    | DQ   | %Q0.0   | MOTOR RUN     | Contactor output |
| Temp_Raw     | AI   | %IW256  | TEMP          | Temperature raw value |
| No_Comment   | DI   | %I0.1   | NC            | |
"""


_RD01 = """# RD01 — IO List

| Tag | Description | IO_Type | Address | SafetyRelated | Status |
|-----|-------------|---------|---------|---------------|--------|
| MOT_HYD_001_FBM | Main contactor feedback | DI | %I1.0 | N | done |
| MOT_HYD_001_MAIN | Main contactor | DQ | %Q4.0 | N | done |
| SEN_OILTEMP_001_VAL | Oil temperature raw | AI | %IW10 | N | done |
"""


def _mk_project(tmp_path: Path, output_language: str = "DE",
                version: str = "V19") -> Path:
    proj = tmp_path / "proj"
    (proj / "metadata").mkdir(parents=True)
    state = {"target_tia_version": version}
    if output_language:
        state["output_language"] = output_language
    (proj / "PROJECT_STATE.json").write_text(json.dumps(state), encoding="utf-8")
    (proj / "metadata" / "HW03_IEC_Tags.md").write_text(_HW03, encoding="utf-8")
    (proj / "metadata" / "RD01_IO_List.md").write_text(_RD01, encoding="utf-8")
    return proj


def _export_root(proj: Path) -> ET.Element:
    res = run_export(proj, write_xlsx=False)
    assert res.ok, res.warnings
    return ET.fromstring(res.xml_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1) XML format — Openness V14+ import shape
# ---------------------------------------------------------------------------

class TestTagXmlOpennessFormat:
    def test_v14_plus_element_names(self, tmp_path):
        root = _export_root(_mk_project(tmp_path))
        assert root.find("SW.Tags.PlcTagTable") is not None, (
            "Openness V14+ import format requires SW.Tags.PlcTagTable")
        assert root.find("SW.PlcTagTable") is None, (
            "SW.PlcTagTable is the V13 shape — TIA V19 refuses it")
        assert root.find("Engineering").get("version") == "V19"

    def test_tags_carry_composition_name_and_address(self, tmp_path):
        root = _export_root(_mk_project(tmp_path))
        tags = root.findall(".//SW.Tags.PlcTag")
        assert len(tags) == 4
        for t in tags:
            assert t.get("CompositionName") == "Tags"
            attrs = t.find("AttributeList")
            assert attrs.find("Name") is not None
            assert attrs.find("DataTypeName") is not None
            assert attrs.find("LogicalAddress") is not None

    def test_comment_is_multilingual_text_with_project_culture(self, tmp_path):
        root = _export_root(_mk_project(tmp_path, output_language="DE"))
        tag = next(t for t in root.findall(".//SW.Tags.PlcTag")
                   if t.find("AttributeList/Name").text == "Motor_Start")
        assert tag.find("AttributeList/Comment") is None, (
            "inline <Comment> in AttributeList is the V13 shape")
        item = tag.find("ObjectList/MultilingualText/ObjectList/"
                        "MultilingualTextItem")
        assert item is not None
        assert item.find("AttributeList/Culture").text == "de-DE"
        assert item.find("AttributeList/Text").text == "Start button"

    def test_tag_without_comment_has_no_multilingual_text(self, tmp_path):
        root = _export_root(_mk_project(tmp_path))
        tag = next(t for t in root.findall(".//SW.Tags.PlcTag")
                   if t.find("AttributeList/Name").text == "No_Comment")
        assert tag.find("ObjectList") is None

    def test_culture_follows_output_language(self, tmp_path):
        root = _export_root(_mk_project(tmp_path, output_language="EN"))
        cultures = {c.text for c in root.findall(".//Culture")}
        assert cultures == {"en-US"}

    def test_culture_defaults_to_en_us_when_language_missing(self, tmp_path):
        root = _export_root(_mk_project(tmp_path, output_language=""))
        cultures = {c.text for c in root.findall(".//Culture")}
        assert cultures == {"en-US"}

    def test_ids_unique_across_document(self, tmp_path):
        root = _export_root(_mk_project(tmp_path))
        ids = [el.get("ID") for el in root.iter() if el.get("ID") is not None]
        assert len(ids) == len(set(ids)), (
            "Openness requires document-unique IDs — duplicates make the "
            "import throw")

    def test_stable_filename_when_not_timestamped(self, tmp_path):
        proj = _mk_project(tmp_path)
        out = proj / "_output" / "tia_import"
        r1 = run_export(proj, output_dir=out, write_xlsx=False,
                        timestamped=False)
        r2 = run_export(proj, output_dir=out, write_xlsx=False,
                        timestamped=False)
        assert r1.xml_path == r2.xml_path == out / "TIA_TagTable_proj.xml"
        assert len(list(out.glob("*.xml"))) == 1, (
            "automated re-sends must overwrite, not accumulate")


# ---------------------------------------------------------------------------
# 1b) Program names + culture fallbacks (2026-06-10 live-TIA findings)
# ---------------------------------------------------------------------------

class TestRd01ProgramNames:
    """Live finding B2: the assembled OB1 references raw RD01 names
    (MOT_HYD_001_FBM); the IEC-prefixed export left 11 'Tag not defined'
    compile errors."""

    def test_rd01_mode_uses_raw_program_names(self, tmp_path):
        res = run_export(_mk_project(tmp_path), write_xlsx=False,
                         name_source="rd01")
        assert res.ok, res.warnings
        names = {t.name for t in res.tags}
        assert "MOT_HYD_001_FBM" in names
        assert not any(n.startswith(("DI_", "DQ_", "AI_")) for n in names), (
            "rd01 mode must carry the names OB1 references — no IEC prefixes")

    def test_rd01_mode_ignores_hw03(self, tmp_path):
        # _mk_project has BOTH files; rd01 mode must not fall back to the
        # HW03 review names (Motor_Start etc.) the program never references.
        res = run_export(_mk_project(tmp_path), write_xlsx=False,
                         name_source="rd01")
        names = {t.name for t in res.tags}
        assert "Motor_Start" not in names

    def test_default_mode_still_prefers_hw03(self, tmp_path):
        res = run_export(_mk_project(tmp_path), write_xlsx=False)
        assert {t.name for t in res.tags} >= {"Motor_Start", "Motor_Run"}


class TestCultureFallbackHelpers:
    """Live finding B1: Openness refuses the whole import when a comment
    Culture is not a project language."""

    def _xml(self, tmp_path) -> str:
        res = run_export(_mk_project(tmp_path, output_language="DE"),
                         write_xlsx=False)
        return res.xml_path.read_text(encoding="utf-8")

    def test_rewrite_culture_replaces_every_occurrence(self, tmp_path):
        from bridges.tia.openness_core import _rewrite_tag_xml_culture
        out = _rewrite_tag_xml_culture(self._xml(tmp_path), "en-GB")
        assert "<Culture>de-DE</Culture>" not in out
        assert out.count("<Culture>en-GB</Culture>") == 3  # 3 commented tags

    def test_strip_comments_keeps_tags_and_addresses(self, tmp_path):
        from bridges.tia.openness_core import _strip_tag_comments
        out = _strip_tag_comments(self._xml(tmp_path))
        root = ET.fromstring(out)
        assert not list(root.iter("MultilingualText")), "comments must go"
        tags = root.findall(".//SW.Tags.PlcTag")
        assert len(tags) == 4, "every tag must survive the strip"
        for t in tags:
            assert t.find("AttributeList/Name") is not None
            assert t.find("AttributeList/LogicalAddress") is not None
        assert out.startswith('<?xml version="1.0" encoding="utf-8"?>'), (
            "stripped file must stay a valid Openness import document")


# ---------------------------------------------------------------------------
# 2) Bridge — tag import ordering and fail-soft behaviour
# ---------------------------------------------------------------------------

class _FakeCore:
    def __init__(self, tag_error: Exception | None = None):
        self.calls: list = []
        self._tag_error = tag_error

    def start_portal(self, with_ui=True):
        self.calls.append("start")

    def open_project(self, p):
        self.calls.append("open")
        return object()

    def find_plc(self, proj, name):
        return object(), object()

    def import_tag_table(self, plc_sw, xml, project=None):
        self.calls.append(("tags", Path(xml).name))
        if self._tag_error:
            raise self._tag_error
        return ["TIA_Tags_proj"], ["note from core"]

    def import_scl_files(self, plc_sw, files, skip_safety=True,
                         safety_block_names=None, on_file=None):
        self.calls.append("scl")
        from bridges.tia.openness_core import ImportSummary
        names = [Path(f).name for f in files]
        return ImportSummary(sources_added=names, blocks_generated=names)


def _mk_bridge(core):
    from bridges.tia.v19 import TiaV19Bridge
    settings = {"bridges": {
        "enabled": {"tia_v19": True},
        "tia": {"default_plc_name": "PLC_1",
                "auto_compile_after_import": False,
                "skip_safety_blocks": False},
    }}
    bridge = TiaV19Bridge(settings)
    bridge._core = core
    bridge._install = object()
    return bridge


@pytest.fixture
def scl_and_ap(tmp_path):
    scl = tmp_path / "FB_X.scl"
    scl.write_text('FUNCTION_BLOCK "FB_X"\nEND_FUNCTION_BLOCK\n',
                   encoding="utf-8")
    ap = tmp_path / "plant.ap19"
    ap.write_text("", encoding="utf-8")
    return scl, ap


class TestBridgeTagImport:
    def test_tag_table_imported_before_scl_sources(self, tmp_path, scl_and_ap):
        scl, ap = scl_and_ap
        core = _FakeCore()
        bridge = _mk_bridge(core)
        r = bridge.import_scl_to_project(ap, [scl],
                                         tag_xml=tmp_path / "tags.xml")
        assert r.success, r.message
        assert any("Tag table imported: TIA_Tags_proj" in d for d in r.details)
        assert "note from core" in r.warnings, (
            "core notes (culture adapted / comments dropped) must reach "
            "the job log")
        assert core.calls.index(("tags", "tags.xml")) < core.calls.index("scl"), (
            "tags must land before the SCL sources so symbolic IO references "
            "resolve at compile time")

    def test_tag_failure_warns_but_blocks_continue(self, tmp_path, scl_and_ap):
        scl, ap = scl_and_ap
        from bridges.tia.openness_core import OpennessError
        core = _FakeCore(tag_error=OpennessError("culture not in project"))
        bridge = _mk_bridge(core)
        r = bridge.import_scl_to_project(ap, [scl],
                                         tag_xml=tmp_path / "tags.xml")
        assert r.success, "a tag failure must not abort the block import"
        assert any("Tag table import FAILED" in w for w in r.warnings), (
            "the failure must be loud — silent tag loss is the M4 "
            "silent-success flaw all over again")
        assert "scl" in core.calls

    def test_no_tag_xml_skips_tag_import(self, scl_and_ap):
        scl, ap = scl_and_ap
        core = _FakeCore()
        bridge = _mk_bridge(core)
        r = bridge.import_scl_to_project(ap, [scl], tag_xml=None)
        assert r.success
        assert not any(isinstance(c, tuple) and c[0] == "tags"
                       for c in core.calls)


# ---------------------------------------------------------------------------
# 3) factory_web._prepare_tag_xml — never raises, always explains
# ---------------------------------------------------------------------------

def _mk_api(root: Path):
    api = object.__new__(fw.Api)
    api.settings = {}
    api.root = root
    return api


class TestPrepareTagXml:
    def test_generates_xml_into_tia_import_dir(self, tmp_path):
        proj = _mk_project(tmp_path)
        xml, msgs = _mk_api(proj)._prepare_tag_xml()
        assert xml is not None and xml.is_file()
        assert xml.parent == proj / "_output" / "tia_import"
        assert any("3 tags" in m for m in msgs)
        text = xml.read_text(encoding="utf-8")
        assert "<Name>MOT_HYD_001_FBM</Name>" in text, (
            "send_to_tia must ship the program's RD01 names")
        assert "DI_MOT_HYD_001_FBM" not in text

    def test_project_without_io_data_returns_none_with_reason(self, tmp_path):
        proj = tmp_path / "empty"
        proj.mkdir()
        xml, msgs = _mk_api(proj)._prepare_tag_xml()
        assert xml is None
        assert any("not be sent" in m for m in msgs), (
            "the skip must be explained in the job log — no silent tag loss")
