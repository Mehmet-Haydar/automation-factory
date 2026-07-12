"""Proof tests — B-09: TIA bridge must not report a false READY.

Field-audit finding: detect() returned READY even when the user was not in
the 'Siemens TIA Openness' Windows group ("warning only") and never checked
pythonnet at all — the engineer discovered the dead-end at SEND time, inside
a modal, with no fallback hint. Every known dead-end must surface as
NOT_CONFIGURED at detect time, with an actionable message that names the
manual-export escape hatch (.scl files via TIA external sources).
"""
from __future__ import annotations

import importlib.util

import pytest

from bridges.base import BridgeStatus
from bridges.tia import v19 as v19mod
from bridges.tia.v19 import TiaV19Bridge


class _FakeInstall:
    engineering_dll = "C:/fake/Siemens.Engineering.dll"
    version = "V19"
    project_ext = ".ap19"


@pytest.fixture
def bridge():
    return TiaV19Bridge(settings={"bridges": {"tia": {}}})


def _patch_clr(monkeypatch, present: bool):
    real = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util, "find_spec",
        lambda name, *a, **k: (object() if present else None)
        if name == "clr" else real(name, *a, **k),
    )


def test_missing_pythonnet_is_not_ready(bridge, monkeypatch):
    monkeypatch.setattr(v19mod, "find_one", lambda v: _FakeInstall())
    _patch_clr(monkeypatch, present=False)
    assert bridge.detect() == BridgeStatus.NOT_CONFIGURED
    assert "pythonnet" in bridge.last_error
    assert "External source files" in bridge.last_error, (
        "Hata mesajı manuel-import kaçış yolunu göstermiyor"
    )


def test_missing_openness_group_is_not_ready(bridge, monkeypatch):
    monkeypatch.setattr(v19mod, "find_one", lambda v: _FakeInstall())
    _patch_clr(monkeypatch, present=True)
    monkeypatch.setattr(v19mod, "is_user_in_openness_group", lambda: False)
    assert bridge.detect() == BridgeStatus.NOT_CONFIGURED, (
        "B-09 regresyonu: Openness grubu eksikken READY dönüyor"
    )
    assert "Openness" in bridge.last_error
    assert "External source files" in bridge.last_error


def test_all_prereqs_met_is_ready(bridge, monkeypatch):
    monkeypatch.setattr(v19mod, "find_one", lambda v: _FakeInstall())
    _patch_clr(monkeypatch, present=True)
    monkeypatch.setattr(v19mod, "is_user_in_openness_group", lambda: True)
    assert bridge.detect() == BridgeStatus.READY


def test_group_check_indeterminate_stays_ready(bridge, monkeypatch):
    """is_user_in_openness_group() -> None (can't determine, e.g. non-admin
    query failure) must NOT block — only a definite False blocks."""
    monkeypatch.setattr(v19mod, "find_one", lambda v: _FakeInstall())
    _patch_clr(monkeypatch, present=True)
    monkeypatch.setattr(v19mod, "is_user_in_openness_group", lambda: None)
    assert bridge.detect() == BridgeStatus.READY


def test_manual_dll_path_also_preflighted(bridge, monkeypatch, tmp_path):
    """The manual-DLL branch used to return READY unconditionally."""
    dll = tmp_path / "Siemens.Engineering.dll"
    dll.write_bytes(b"\x00")
    bridge.settings = {"bridges": {"tia": {"tia_v19_dll_path": str(dll)}}}
    _patch_clr(monkeypatch, present=False)
    assert bridge.detect() == BridgeStatus.NOT_CONFIGURED
    assert "pythonnet" in bridge.last_error


def test_check_can_be_disabled_in_settings(bridge, monkeypatch):
    """openness_user_check=False keeps the old behavior for exotic setups."""
    bridge.settings = {"bridges": {"tia": {"openness_user_check": False}}}
    monkeypatch.setattr(v19mod, "find_one", lambda v: _FakeInstall())
    _patch_clr(monkeypatch, present=True)
    monkeypatch.setattr(
        v19mod, "is_user_in_openness_group",
        lambda: (_ for _ in ()).throw(AssertionError("check çağrılmamalıydı")),
    )
    assert bridge.detect() == BridgeStatus.READY
