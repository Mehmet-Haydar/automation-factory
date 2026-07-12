"""Proof tests — Hardware workbench backend (2026-07-06 GUI rework).

The hardware page became a real workspace: list devices with their verified
state, open/edit the MD sheets, create skeletons. These tests pin the
security and honesty rules:
  - every path stays inside the hardware library root (traversal refused)
  - schema/underscore files are not editable devices
  - verified state is reported honestly (missing → NOT_VERIFIED)
  - skeletons are born NOT_VERIFIED and never overwrite an existing sheet
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


_DEVICE_MD = """\
# TestVendor TM-1 — drives

## metadata
```yaml
schema_version: "1.0"
device_id: "TV_TM1"
vendor: "TestVendor"
model: "TM-1"
category: "drives"
subcategory: "ac_drive"
part_number: "TV-0001"
verified: NOT_VERIFIED
```

## 1. General Info

body
"""


def _make_api(tmp_path, monkeypatch):
    import factory_web
    monkeypatch.setattr(factory_web, "FACTORY_ROOT", tmp_path)
    # keep tests hermetic — never rebuild the real BM25 index from here
    monkeypatch.setattr(factory_web.Api, "_rebuild_bm25_index",
                        staticmethod(lambda: ""))
    lib = tmp_path / "09_HARDWARE_LIBRARY"
    (lib / "drives" / "TestVendor").mkdir(parents=True)
    (lib / "drives" / "TestVendor" / "TM1.md").write_text(
        _DEVICE_MD, encoding="utf-8")
    (lib / "_SCHEMA_DEVICE.md").write_text("# schema", encoding="utf-8")
    api = factory_web.Api()
    api.root = None
    return api


def test_get_hw_library_reports_verified_honestly(tmp_path, monkeypatch):
    api = _make_api(tmp_path, monkeypatch)
    r = api.get_hw_library()
    assert r["ok"] and r["categories"] == ["drives"]
    (d,) = r["devices"]
    assert d["id"] == "TV_TM1" and d["verified"] == "NOT_VERIFIED"
    assert d["part_number"] == "TV-0001"
    assert d["rel_path"] == "drives/TestVendor/TM1.md"


def test_device_text_roundtrip(tmp_path, monkeypatch):
    api = _make_api(tmp_path, monkeypatch)
    rel = "drives/TestVendor/TM1.md"
    assert api.get_device_text(rel)["text"].startswith("# TestVendor")
    new_text = _DEVICE_MD + "\nedited by engineer\n"
    assert api.save_device_text(rel, new_text)["ok"]
    assert api.get_device_text(rel)["text"].endswith("edited by engineer\n")


def test_paths_outside_library_are_refused(tmp_path, monkeypatch):
    api = _make_api(tmp_path, monkeypatch)
    (tmp_path / "secret.md").write_text("x", encoding="utf-8")
    for bad in ("../secret.md", "..\\secret.md",
                str(tmp_path / "secret.md"), ""):
        assert not api.get_device_text(bad)["ok"], bad
        assert not api.save_device_text(bad, "y")["ok"], bad
    # traversal must not have touched the outside file
    assert (tmp_path / "secret.md").read_text(encoding="utf-8") == "x"


def test_schema_and_empty_saves_refused(tmp_path, monkeypatch):
    api = _make_api(tmp_path, monkeypatch)
    assert not api.save_device_text("_SCHEMA_DEVICE.md", "overwrite")["ok"], \
        "underscore files are library plumbing, not devices"
    assert not api.save_device_text("drives/TestVendor/TM1.md", "   ")["ok"], \
        "empty save would silently destroy a device sheet"


def test_create_device_skeleton_not_verified_and_no_overwrite(tmp_path,
                                                              monkeypatch):
    api = _make_api(tmp_path, monkeypatch)
    r = api.create_device("sensors", "ifm", "O5D100")
    assert r["ok"] and r["rel_path"] == "sensors/ifm/O5D100.md"
    text = api.get_device_text(r["rel_path"])["text"]
    assert "verified: NOT_VERIFIED" in text and "DRAFT" in text
    assert 'library_path: "sensors/ifm/O5D100.md"' in text
    # the new device appears in the catalog
    ids = {d["id"] for d in api.get_hw_library()["devices"]}
    assert r["device_id"] in ids
    # second create must refuse — never clobber engineer work
    assert not api.create_device("sensors", "ifm", "O5D100")["ok"]
    assert not api.create_device("", "ifm", "O5D100")["ok"]
