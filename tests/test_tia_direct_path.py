"""M4 — TIA Openness direct path: classification consent matrix, send_to_tia
preconditions, compile-evidence recording and the honest label upgrade.

No TIA Portal in CI — the bridge layer is mocked; the 41 plcsim safety
tests elsewhere keep covering the download guards.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

import tia_export
from tia_export import TIAExportClassificationError

fw = importlib.import_module("factory_web")


def _proj(tmp_path: Path, classification: str | None) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    if classification is not None:
        (proj / "PROJECT_STATE.json").write_text(
            json.dumps({"data_classification": classification}), encoding="utf-8")
    return proj


def _mk_api(root: Path):
    api = object.__new__(fw.Api)
    api.settings = {}
    api.root = root
    return api


# ---------------------------------------------------------------------------
# tia_export classification gate (Path B)
# ---------------------------------------------------------------------------

class TestExportClassificationGate:
    def test_restricted_always_blocked_even_with_consent(self, tmp_path):
        proj = _proj(tmp_path, "RESTRICTED")
        with pytest.raises(TIAExportClassificationError, match="RESTRICTED"):
            tia_export._check_project_classification_for_export(
                proj, local_transfer_consent=True)

    def test_confidential_blocked_without_consent(self, tmp_path):
        proj = _proj(tmp_path, "CONFIDENTIAL")
        with pytest.raises(TIAExportClassificationError, match="consent"):
            tia_export._check_project_classification_for_export(proj)

    def test_confidential_allowed_with_consent(self, tmp_path):
        proj = _proj(tmp_path, "CONFIDENTIAL")
        tia_export._check_project_classification_for_export(
            proj, local_transfer_consent=True)  # no raise

    def test_public_allowed_without_consent(self, tmp_path):
        proj = _proj(tmp_path, "PUBLIC")
        tia_export._check_project_classification_for_export(proj)

    def test_missing_state_fail_closed(self, tmp_path):
        proj = _proj(tmp_path, None)
        with pytest.raises(TIAExportClassificationError):
            tia_export._check_project_classification_for_export(proj)

    def test_db_sources_included_in_package(self, tmp_path):
        proj = _proj(tmp_path, "PUBLIC")
        out = proj / "_output" / "scl"
        out.mkdir(parents=True)
        (out / "FB_X.scl").write_text(
            'FUNCTION_BLOCK "FB_X"\nEND_FUNCTION_BLOCK\n', encoding="utf-8")
        (out / "iDB_X.db").write_text(
            'DATA_BLOCK "iDB_X"\n"FB_X"\nBEGIN\nEND_DATA_BLOCK\n', encoding="utf-8")
        result = tia_export.prepare_tia_package(proj, overwrite=True)
        exported = {p.name for p in (proj / "_output" / "tia_import").rglob("*")
                    if p.is_file()}
        assert "iDB_X.db" in exported, (
            "M3 instance-DB sources must ship with the TIA package")


# ---------------------------------------------------------------------------
# factory_web consent gate (direct path)
# ---------------------------------------------------------------------------

class TestTiaConsentGate:
    def test_restricted_refused(self, tmp_path):
        api = _mk_api(_proj(tmp_path, "RESTRICTED"))
        err = api._tia_consent_gate({"engineer": "E", "confirmed": True}, "t")
        assert err and "RESTRICTED" in err

    def test_confidential_needs_consent(self, tmp_path):
        api = _mk_api(_proj(tmp_path, "CONFIDENTIAL"))
        assert api._tia_consent_gate(None, "t")
        assert api._tia_consent_gate({"engineer": "", "confirmed": True}, "t")
        assert api._tia_consent_gate({"engineer": "E", "confirmed": False}, "t")

    def test_confidential_with_consent_passes_and_audits(self, tmp_path):
        proj = _proj(tmp_path, "CONFIDENTIAL")
        api = _mk_api(proj)
        err = api._tia_consent_gate({"engineer": "Test Eng", "confirmed": True}, "t")
        assert err is None
        log = proj / "AI_DECISION_LOG.jsonl"
        assert log.is_file() and "tia_local_transfer_consent" in log.read_text(
            encoding="utf-8"), "consent must leave an audit trail"

    def test_public_passes_without_consent(self, tmp_path):
        api = _mk_api(_proj(tmp_path, "PUBLIC"))
        assert api._tia_consent_gate(None, "t") is None

    def test_unknown_classification_fail_closed(self, tmp_path):
        api = _mk_api(_proj(tmp_path, None))
        assert api._tia_consent_gate(None, "t") is not None


# ---------------------------------------------------------------------------
# send_to_tia preconditions (bridge mocked / not reached)
# ---------------------------------------------------------------------------

class TestSendToTiaPreconditions:
    def test_refuses_when_no_assembled_sources(self, tmp_path):
        api = _mk_api(_proj(tmp_path, "PUBLIC"))
        r = api.send_to_tia({})
        assert not r["ok"]
        assert "Assemble" in r["msg"]

    def test_refuses_without_project_path(self, tmp_path):
        proj = _proj(tmp_path, "PUBLIC")
        out = proj / "_output" / "scl"
        out.mkdir(parents=True)
        (out / "a.scl").write_text("FUNCTION_BLOCK \"A\"\nEND_FUNCTION_BLOCK",
                                   encoding="utf-8")
        r = _mk_api(proj).send_to_tia({})
        assert not r["ok"]
        assert ".ap19" in r["msg"] or ".ap20" in r["msg"]

    def test_refuses_disabled_bridge(self, tmp_path, monkeypatch):
        proj = _proj(tmp_path, "PUBLIC")
        # B-P12: V20 must be in the contract so the version gate passes and
        # the disabled-bridge check is reached (that is what this test covers).
        (proj / "PROJECT_STATE.json").write_text(
            json.dumps({"data_classification": "PUBLIC",
                        "allowed_tia_versions": ["V20"]}),
            encoding="utf-8")
        out = proj / "_output" / "scl"
        out.mkdir(parents=True)
        (out / "a.scl").write_text("FUNCTION_BLOCK \"A\"\nEND_FUNCTION_BLOCK",
                                   encoding="utf-8")
        ap = tmp_path / "plant.ap20"
        ap.write_text("", encoding="utf-8")
        api = _mk_api(proj)

        class _Bridge:
            display_name = "TIA V20 (mock)"
        class _Mgr:
            def get(self, bid): return _Bridge()
            def is_enabled(self, bid): return False
            def tia_settings(self): return {"default_plc_name": "PLC_1"}
        api._bridge_mgr = _Mgr()
        r = api.send_to_tia({"project_path": str(ap)})
        assert not r["ok"]
        assert "disabled" in r["msg"].lower()


# ---------------------------------------------------------------------------
# Compile evidence + honest label upgrade
# ---------------------------------------------------------------------------

class TestCompileEvidence:
    def test_record_compile_success_upgrades_validation_scope(self, tmp_path):
        proj = _proj(tmp_path, "PUBLIC")
        api = _mk_api(proj)
        api._record_compile_success([Path("OB_Main.scl"), Path("FB_X.scl")], "V20")

        ev = json.loads((proj / "REPORTS" / "gate_results" / "tia_compile.json")
                        .read_text(encoding="utf-8"))
        assert ev["label"].startswith("AUTO_VERIFIED_compile"), (
            "compile success earns the compile tier — but never more "
            "(PLCSIM still pending)")
        assert "PENDING_PLCSIM_VERIFY" in ev["label"]

        state = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        assert state["last_validation"] == {"errors": 0, "scope": "compile"}

    def test_compile_scope_clears_wa5_structural_blocker(self, tmp_path):
        # W-A5 blocked gate advance on structural-only validation unless the
        # engineer ticked accept_structural_only. After a real TIA compile the
        # honest path needs no checkbox.
        all_done = {f"RD{n:02d}": "done" for n in range(1, 15)}
        blockers_structural = fw._gate_advance_blockers(
            3, all_done, signature="Hans Becker (TUV)",
            last_validation={"errors": 0, "scope": "structural_only"},
            accept_structural_only=False)
        assert blockers_structural, "structural-only must still require the checkbox"

        blockers_compile = fw._gate_advance_blockers(
            3, all_done, signature="Hans Becker (TUV)",
            last_validation={"errors": 0, "scope": "compile"},
            accept_structural_only=False)
        assert blockers_compile == [], (
            "a clean TIA compile must satisfy the gate without the "
            "accept_structural_only escape hatch")


# ---------------------------------------------------------------------------
# V21 bridge support (user runs TIA V21)
# ---------------------------------------------------------------------------

class TestV21Bridge:
    def test_v21_bridge_class_constants(self):
        from bridges.tia.v21 import TiaV21Bridge
        assert TiaV21Bridge.bridge_id == "tia_v21"
        assert TiaV21Bridge._TARGET_VERSION == "V21"
        assert TiaV21Bridge._PROJECT_EXT == ".ap21"

    def test_v21_in_registry_and_defaults(self):
        from bridges.bridge_manager import BRIDGE_REGISTRY, DEFAULT_BRIDGE_SETTINGS
        assert ("bridges.tia.v21", "TiaV21Bridge") in BRIDGE_REGISTRY
        assert "tia_v21" in DEFAULT_BRIDGE_SETTINGS["enabled"]
        assert "tia_v21_dll_path" in DEFAULT_BRIDGE_SETTINGS["tia"]

    def test_version_detect_scans_v21(self):
        import inspect
        from bridges.tia import version_detect
        src = inspect.getsource(version_detect.find_installs)
        assert "range(14, 22)" in src, "default scan must include V21"

    def test_set_project_target_accepts_v21(self, tmp_path):
        proj = _proj(tmp_path, "PUBLIC")
        api = _mk_api(proj)
        r = api.set_project_target({"target_tia_version": "V21"})
        assert r["ok"]
        state = json.loads((proj / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        assert state["target_tia_version"] == "V21"
