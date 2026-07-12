"""S-19 / B-P12 — TIA hedef versiyonu kontrat kontrolü.

Domain kararı (2026-06-11):
  Kontratta listelenmeyen TIA versiyonuna gönderim uyarı üretir ve açık
  mühendis onayı olmadan İLERLEMEZ.
  Fail-closed: kontratta TIA versiyon bilgisi hiç yoksa da "listelenmemiş"
  say (uyarı + onay iste).

Bu dosya _check_tia_version_contract yardımcısını ve send_to_tia entegrasyon
kapısını test eder.

Fix yokken KIRILMALI testler:
  - test_unlisted_version_blocked
  - test_no_contract_field_blocked
  - test_empty_version_blocked
  - test_send_to_tia_unlisted_version_refused
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

fw = importlib.import_module("factory_web")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _proj(tmp_path: Path, state: dict) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "PROJECT_STATE.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    return proj


def _mk_api(root: Path):
    api = object.__new__(fw.Api)
    api.settings = {}
    api.root = root
    return api


def _proj_with_versions(tmp_path: Path, allowed: list[str] | None) -> Path:
    state: dict = {"data_classification": "PUBLIC"}
    if allowed is not None:
        state["allowed_tia_versions"] = allowed
    return _proj(tmp_path, state)


# ---------------------------------------------------------------------------
# Unit: _check_tia_version_contract
# ---------------------------------------------------------------------------

class TestCheckTiaVersionContract:
    """Direct unit tests for the helper function (no bridge mocking needed)."""

    def test_listed_version_passes(self, tmp_path):
        """Version in allowlist → gate passes (None returned)."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19", "V20"]))
        err = api._check_tia_version_contract("V19", None)
        assert err is None

    def test_listed_version_case_insensitive(self, tmp_path):
        """Lowercase input must still match the uppercase contract."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19"]))
        err = api._check_tia_version_contract("v19", None)
        assert err is None

    def test_unlisted_version_blocked(self, tmp_path):
        """Version not in list → error without consent (B-P12 core rule)."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19"]))
        err = api._check_tia_version_contract("V20", None)
        assert err is not None
        assert "V20" in err or "v20" in err.lower()
        assert "kontratt" in err.lower() or "contract" in err.lower() or "listelen" in err.lower()

    def test_no_contract_field_blocked(self, tmp_path):
        """Absent allowed_tia_versions → fail-closed (unlisted)."""
        api = _mk_api(_proj_with_versions(tmp_path, None))
        err = api._check_tia_version_contract("V21", None)
        assert err is not None, (
            "No contract field must be treated as unlisted — fail-closed"
        )

    def test_empty_contract_list_blocked(self, tmp_path):
        """Empty list → fail-closed."""
        api = _mk_api(_proj_with_versions(tmp_path, []))
        err = api._check_tia_version_contract("V19", None)
        assert err is not None

    def test_empty_version_string_blocked(self, tmp_path):
        """Missing version string → always blocked (cannot approve unknown target)."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19"]))
        err = api._check_tia_version_contract("", None)
        assert err is not None

    def test_none_version_blocked(self, tmp_path):
        """None version → always blocked."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19"]))
        err = api._check_tia_version_contract(None, None)  # type: ignore[arg-type]
        assert err is not None


# ---------------------------------------------------------------------------
# Mühendis onayı ile listelenmemiş versiyon
# ---------------------------------------------------------------------------

class TestContractVersionApproval:
    """Unlisted version passes ONLY with explicit engineer approval."""

    def test_unlisted_approved_by_engineer_passes(self, tmp_path):
        """Explicit version_approved + engineer name → gate passes for unlisted."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19"]))
        consent = {"version_approved": True, "engineer": "Hans Becker"}
        err = api._check_tia_version_contract("V20", consent)
        assert err is None, (
            "Unlisted version with version_approved=True and engineer name "
            "must pass — engineer takes explicit responsibility"
        )

    def test_unlisted_approved_false_blocked(self, tmp_path):
        """version_approved=False with engineer name → still blocked."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19"]))
        consent = {"version_approved": False, "engineer": "Hans Becker"}
        err = api._check_tia_version_contract("V20", consent)
        assert err is not None

    def test_unlisted_no_engineer_name_blocked(self, tmp_path):
        """version_approved=True but empty engineer name → blocked."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19"]))
        consent = {"version_approved": True, "engineer": ""}
        err = api._check_tia_version_contract("V20", consent)
        assert err is not None

    def test_unlisted_engineer_only_no_approved_blocked(self, tmp_path):
        """Engineer name without version_approved → blocked."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19"]))
        consent = {"engineer": "Hans Becker"}
        err = api._check_tia_version_contract("V20", consent)
        assert err is not None

    def test_listed_version_needs_no_approval_field(self, tmp_path):
        """Listed version passes without any approval fields."""
        api = _mk_api(_proj_with_versions(tmp_path, ["V19", "V20"]))
        err = api._check_tia_version_contract("V20", {})
        assert err is None


# ---------------------------------------------------------------------------
# Entegrasyon: send_to_tia versiyon kapısı
# ---------------------------------------------------------------------------

class TestSendToTiaVersionGate:
    """send_to_tia must refuse when version is unlisted and no approval given."""

    def _setup_project_with_sources(self, tmp_path: Path, allowed: list[str] | None):
        state: dict = {"data_classification": "PUBLIC"}
        if allowed is not None:
            state["allowed_tia_versions"] = allowed
        proj = _proj(tmp_path, state)
        out = proj / "_output" / "scl"
        out.mkdir(parents=True)
        (out / "OB_Main.scl").write_text(
            'ORGANIZATION_BLOCK "OB_Main"\nEND_ORGANIZATION_BLOCK\n',
            encoding="utf-8",
        )
        return proj

    def test_send_to_tia_unlisted_version_refused(self, tmp_path):
        """S-19 core: unlisted version → send_to_tia returns ok=False without bridge call."""
        proj = self._setup_project_with_sources(tmp_path, ["V19"])
        ap = tmp_path / "plant.ap20"
        ap.write_text("", encoding="utf-8")
        api = _mk_api(proj)
        # No consent, V20 not in contract
        r = api.send_to_tia({"project_path": str(ap)})
        assert not r["ok"], "Must be refused when version is unlisted"
        assert r.get("version_check_failed") is True, (
            "version_check_failed flag must be set so GUI can show the right prompt"
        )
        assert "V20" in r["msg"] or "v20" in r["msg"].lower()

    def test_send_to_tia_no_contract_refused(self, tmp_path):
        """No allowed_tia_versions in state → fail-closed, blocked."""
        proj = self._setup_project_with_sources(tmp_path, None)
        ap = tmp_path / "plant.ap19"
        ap.write_text("", encoding="utf-8")
        api = _mk_api(proj)
        r = api.send_to_tia({"project_path": str(ap)})
        assert not r["ok"], "No contract must block the transfer"
        assert r.get("version_check_failed") is True

    def test_send_to_tia_listed_version_proceeds_to_bridge(self, tmp_path):
        """Listed version passes version gate and proceeds to next check (bridge)."""
        proj = self._setup_project_with_sources(tmp_path, ["V19"])
        ap = tmp_path / "plant.ap19"
        ap.write_text("", encoding="utf-8")

        # Mock bridge manager so we don't need TIA Portal
        class _Bridge:
            display_name = "TIA V19 (mock)"
        class _Mgr:
            def get(self, bid): return _Bridge()
            def is_enabled(self, bid): return False   # → "disabled" error
            def tia_settings(self): return {"default_plc_name": "PLC_1"}

        api = _mk_api(proj)
        api._bridge_mgr = _Mgr()
        r = api.send_to_tia({"project_path": str(ap)})
        # version gate passes → reaches disabled check
        assert not r["ok"]
        assert "disabled" in r["msg"].lower(), (
            "Version gate must pass for listed V19; next failure should be disabled-bridge"
        )
        assert not r.get("version_check_failed"), (
            "version_check_failed must NOT be set when version gate passes"
        )

    def test_send_to_tia_unlisted_with_approval_proceeds(self, tmp_path):
        """Unlisted version + explicit engineer approval → version gate passes."""
        proj = self._setup_project_with_sources(tmp_path, ["V19"])
        ap = tmp_path / "plant.ap20"
        ap.write_text("", encoding="utf-8")

        class _Bridge:
            display_name = "TIA V20 (mock)"
        class _Mgr:
            def get(self, bid): return _Bridge()
            def is_enabled(self, bid): return False   # → "disabled" error
            def tia_settings(self): return {"default_plc_name": "PLC_1"}

        api = _mk_api(proj)
        api._bridge_mgr = _Mgr()
        r = api.send_to_tia({
            "project_path": str(ap),
            "consent": {"version_approved": True, "engineer": "Hans Becker"},
        })
        # Version gate passes with approval → hits disabled-bridge check
        assert not r["ok"]
        assert "disabled" in r["msg"].lower(), (
            "With explicit approval, unlisted version must clear the version gate"
        )
        assert not r.get("version_check_failed")

    def test_error_message_contains_how_to_approve(self, tmp_path):
        """Error message must explain HOW to approve so GUI can guide the engineer."""
        proj = self._setup_project_with_sources(tmp_path, ["V19"])
        ap = tmp_path / "plant.ap20"
        ap.write_text("", encoding="utf-8")
        api = _mk_api(proj)
        r = api.send_to_tia({"project_path": str(ap)})
        msg = r["msg"].lower()
        assert "version_approved" in msg or "onay" in msg, (
            "Error must mention the approval mechanism so the GUI can prompt correctly"
        )
