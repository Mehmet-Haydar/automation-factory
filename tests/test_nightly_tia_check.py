"""Nightly TIA compile driver proof tests (Faz 7, Kademe 2 prep).

These tests pin the contract that keeps the driver honest:
- the block inventory is exactly the 18 library blocks and all exist,
- preflight succeeds without Openness,
- a missing block / project / bridge is a LOUD failure, never a silent green,
- log hygiene: no filesystem path leaks into stdout.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import nightly_tia_check as ntc


# ---- block inventory ----------------------------------------------------

def test_inventory_is_18_blocks():
    assert len(ntc.BLOCK_RELPATHS) == 18
    assert len(set(ntc.BLOCK_RELPATHS)) == 18  # no duplicates


def test_all_inventory_blocks_exist_on_disk():
    blocks = ntc.resolve_blocks()
    assert len(blocks) == 18
    assert all(p.is_file() for p in blocks)


def test_missing_block_is_loud_failure(tmp_path):
    # Empty KB → resolve must raise, never return an empty/short list.
    (tmp_path / "blocks").mkdir()
    with pytest.raises(FileNotFoundError):
        ntc.resolve_blocks(tmp_path)


# ---- preflight ----------------------------------------------------------

def test_preflight_ok_without_openness():
    lines: list[str] = []
    rc = ntc.run_preflight(out=lines.append)
    assert rc == 0
    text = "\n".join(lines)
    assert "PREFLIGHT OK" in text
    assert text.count("[READY]") == 18


# ---- full run: fail-safe defaults --------------------------------------

def test_full_run_no_project_is_failure():
    lines: list[str] = []
    rc = ntc.run_full(None, out=lines.append)
    assert rc == 1
    assert "FAIL" in "\n".join(lines)


def test_full_run_missing_project_does_not_leak_path():
    lines: list[str] = []
    bogus = Path("Z:/secret/customer/Beispielmaschine_4711/Scratch.ap19")
    rc = ntc.run_full(bogus, out=lines.append)
    assert rc == 1
    out = "\n".join(lines)
    # Log hygiene: neither the path nor the customer token may appear.
    assert "Beispielmaschine_4711" not in out
    assert "secret" not in out
    assert "Z:/" not in out and "Z:\\" not in out


def test_block_name_strips_path():
    assert ntc.block_name("motor/FB_Motor_DOL.scl") == "FB_Motor_DOL"
