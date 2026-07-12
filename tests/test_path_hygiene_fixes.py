"""Proof tests for the 2026-06-14 comprehensive pre-final-test audit.

Pins the fixes for the independently-found findings so they cannot regress:
  B-01  backend hands the UI a PROJECT-RELATIVE path (reveal_path refuses
        absolute paths, so an absolute one silently failed to open the folder).
  B-02  RD05-not-ready / SISTEMA-input errors carry NO full project path into
        the GUI log (log hygiene).
  B-07  the PDF inliner turns <br> into a real <br/> break, not literal
        "&lt;br&gt;" text in the customer document.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "05_SCRIPTS"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _mk_project(tmp_path: Path, *, with_rd05: bool = True, name: str = "SecretCust_4711") -> Path:
    proj = tmp_path / name
    meta = proj / "metadata"
    meta.mkdir(parents=True)
    (proj / "PROJECT_STATE.json").write_text(
        json.dumps({"project_name": "Demo", "project_type": "retrofit",
                    # AUDIT-004b: banner blocks without a recorded review
                    "rd_verifications": {"RD05": {"reviewed": True}}}),
        encoding="utf-8")
    (meta / "RD01_IO_List.md").write_text(
        "| Tag | Address | Type |\n|---|---|---|\n| xStart | %I0.0 | DI |\n", encoding="utf-8")
    if with_rd05:
        (meta / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
            "# RD05\n| Func | Desc | PLr |\n|---|---|---|\n| EStop | E | d |\n", encoding="utf-8")
    return proj


def _api(root: Path):
    import factory_web
    api = factory_web.Api()
    api.root = root
    return api


# ── B-01: relative paths the UI can actually reveal ─────────────────────

def test_generate_fat_returns_relative_path(tmp_path):
    proj = _mk_project(tmp_path)
    api = _api(proj)
    r = api.generate_fat("FAT", "de", False)
    assert r["ok"] is True, r.get("msg")
    assert r["path"] and not Path(r["path"]).is_absolute()
    # The relative path resolves to the real produced file under the root,
    assert (proj / r["path"]).exists()
    # and reveal_path's I-A3 absolute-path rejection must NOT trigger (the
    # actual explorer launch is platform-specific and not asserted here).
    with patch("subprocess.Popen"):
        assert "Absolute and traversal" not in api.reveal_path(r["path"]).get("msg", "")


def test_generate_ce_returns_relative_path(tmp_path):
    proj = _mk_project(tmp_path)
    api = _api(proj)
    r = api.generate_ce_assessment("de", False)
    assert r["ok"] is True, r.get("msg")
    assert r["path"] and not Path(r["path"]).is_absolute()


# ── B-02: no project path leaks into the GUI message ────────────────────

def test_rd05_blocked_message_has_no_project_path(tmp_path):
    proj = _mk_project(tmp_path, with_rd05=False, name="SecretCust_9999")
    # remove metadata entirely to trigger the "metadata not found" branch
    api = _api(tmp_path / "SecretCust_9999_missing")
    r = api.generate_fat("FAT", "de", False)
    assert r["ok"] is False
    assert "SecretCust_9999" not in r["msg"]
    assert str(proj) not in r["msg"]


def test_sistema_prep_input_error_has_no_project_path(tmp_path):
    proj = tmp_path / "SecretCust_8888"     # no metadata/RD05
    proj.mkdir()
    (proj / "PROJECT_STATE.json").write_text("{}", encoding="utf-8")
    api = _api(proj)
    r = api.generate_sistema_prep("de")
    assert r["ok"] is False
    assert "SecretCust_8888" not in r["msg"]
    assert str(proj) not in r["msg"]


# ── B-07: PDF inliner restores <br> ──────────────────────────────────────

def test_pdf_inline_br_is_real_break_not_literal():
    from pdf_common import _inline
    out = _inline("**Q**<br>_hint_")
    assert "<br/>" in out
    assert "&lt;br" not in out
