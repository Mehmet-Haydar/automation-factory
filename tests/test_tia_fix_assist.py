"""Send-to-TIA live step view + compile-error assistance.

Covers the safety rails of the AI fix-proposal flow:
- classification: only FB_Seq_* is proposable; library/assembler/tags get
  deterministic hints, never AI patches;
- propose guards: disabled mode and non-FB_Seq targets are refused BEFORE
  any AI call; a proposal that fails scl_validator is never shown;
- apply: engineer name + checkbox required; _history backup + audit trail;
- job step lifecycle: structured steps reach get_tia_send_status, and a
  step left "running" by a crash is flipped to "fail".

No TIA Portal in CI — the bridge layer is faked (same approach as
test_tia_direct_path.py).
"""

from __future__ import annotations

import importlib
import json
import time
import types
from pathlib import Path

import pytest

fw = importlib.import_module("factory_web")
tfa = importlib.import_module("tia_fix_assist")
from bridges.base import BridgeResult

FACTORY_KB_BLOCKS = fw.FACTORY_ROOT / "06_KNOWLEDGE_BASE" / "blocks"

OLD_SCL = (
    'FUNCTION_BLOCK "FB_Seq_Demo"\n'
    "VAR_INPUT\n"
    "    in_bStart : Bool;\n"
    "END_VAR\n"
    "BEGIN\n"
    "    IF in_bStart THEN\n"
    "    END_IF;\n"
    "END_FUNCTION_BLOCK\n"
)
FIXED_SCL = (
    'FUNCTION_BLOCK "FB_Seq_Demo"\n'
    "VAR_INPUT\n"
    "    in_bStart : Bool;\n"
    "END_VAR\n"
    "BEGIN\n"
    "    IF in_bStart THEN\n"
    "        ;\n"
    "    END_IF;\n"
    "END_FUNCTION_BLOCK\n"
)
BROKEN_SCL = (
    'FUNCTION_BLOCK "FB_Seq_Demo"\n'
    "BEGIN\n"
    "    IF in_bStart THEN\n"  # never closed -> validator NESTING error
    "END_FUNCTION_BLOCK\n"
)


def _proj(tmp_path: Path, classification: str = "PUBLIC") -> Path:
    proj = tmp_path / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "PROJECT_STATE.json").write_text(
        json.dumps({"data_classification": classification,
                    # S-19 (B-P12): send_to_tia requires the target TIA version
                    # to be contract-listed; .ap19 fixtures infer V19.
                    "allowed_tia_versions": ["V19"],
                    # S-1 (M-01): code-gen/transfer now passes the RD05 gate;
                    # the fixture ships a reviewed RD05.
                    "rd_status": {"RD05_Safety": {"status": "REVIEWED"}}}),
        encoding="utf-8")
    md = proj / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD05_Safety.md").write_text(
        "# RD05 Safety\n"
        "| SF | Function | PLr |\n|---|---|---|\n"
        "| SF-01 | E-stop | d |\n| SF-02 | Guard door | c |\n",
        encoding="utf-8")
    return proj


class _Mgr:
    def __init__(self, mode="hints", enabled=True):
        self._tia = {"default_plc_name": "PLC_1", "fix_assist_mode": mode,
                     "live_progress": True}
        self._enabled = enabled
        self.saved_enabled: dict = {}

    def get(self, bid):  # overridden per-test when a bridge is needed
        return None

    def is_enabled(self, bid):
        return self._enabled

    def tia_settings(self):
        return self._tia

    def set_enabled(self, bid, en):
        self.saved_enabled[bid] = en


def _mk_api(root: Path, mode="hints") -> "fw.Api":
    api = object.__new__(fw.Api)
    api.settings = {}
    api.root = root
    api._bridge_mgr = _Mgr(mode=mode)
    return api


def _arm_ai(api, monkeypatch, response=FIXED_SCL, calls=None):
    """Wire the AI-call pattern of tia_fix_propose to fakes."""
    api.get_provider_for_task = lambda t: {"provider": "anthropic",
                                           "model": "test-model",
                                           "max_tokens": 1000}
    api._resolve_api_key = lambda p: "sk-test"
    api._pii_soft_warn = lambda p: []
    import data_classification_guard as dcg
    monkeypatch.setattr(dcg, "check_ai_send",
                        lambda *a, **k: types.SimpleNamespace(
                            allowed=True, reason=""))

    class _FakeClient:
        def __init__(self, provider, api_key, model):
            pass

        def chat(self, system, user, max_tokens=0):
            if calls is not None:
                calls.append(user)
            return response, None

    import ai_client
    monkeypatch.setattr(ai_client, "AIClient", _FakeClient)


def _seed_job(api, errors):
    api._tia_job = {"running": False, "done": True, "ok": False,
                    "msg": "Compile finished with ERRORS", "lines": [],
                    "details": [], "bridge": "tia_v19",
                    "operation": "import_compile", "steps": [],
                    "error_analysis": [], "compile_errors": errors,
                    "fix_proposal": None}


def _seed_fbseq(proj: Path, text=OLD_SCL) -> Path:
    out = proj / "_output" / "scl"
    out.mkdir(parents=True, exist_ok=True)
    p = out / "FB_Seq_Demo.scl"
    p.write_text(text, encoding="utf-8")
    return p


E_SEQ = {"block": "FB_Seq_Demo", "severity": "Error", "text": "Syntax error at ';'"}
E_LIB = {"block": "FB_Motor_DOL", "severity": "Error", "text": "Type mismatch"}
E_OB = {"block": "OB_Main", "severity": "Error", "text": "Unknown identifier"}
E_TAG = {"block": "OB_Main", "severity": "Error",
         "text": "Tag 'MOT_HYD_001_FBM' is not defined"}


# ---------------------------------------------------------------------------
# Classification — origin decides what may ever be AI-proposed
# ---------------------------------------------------------------------------

class TestClassify:
    def test_fbseq_is_the_only_proposable_category(self):
        groups = tfa.classify([E_SEQ, E_LIB, E_OB, E_TAG],
                              kb_blocks_dir=FACTORY_KB_BLOCKS)
        by_cat = {g["category"]: g for g in groups}
        assert by_cat["ai_generated"]["proposable"] is True
        for cat, g in by_cat.items():
            if cat != "ai_generated":
                assert g["proposable"] is False, (
                    f"{cat} must NEVER be AI-proposable — library blocks are "
                    "SHA-verified, assembler output is generated")

    def test_library_block_recognised_from_kb(self):
        groups = tfa.classify([E_LIB], kb_blocks_dir=FACTORY_KB_BLOCKS)
        assert groups[0]["category"] == "library"

    def test_tag_errors_beat_block_origin(self):
        # "tag not defined" in an OB is a tag-table problem, not OB code.
        groups = tfa.classify([E_TAG], kb_blocks_dir=FACTORY_KB_BLOCKS)
        assert groups[0]["category"] == "tags"

    def test_assembler_and_unknown(self):
        groups = tfa.classify(
            [E_OB, {"block": "FB_Mystery", "severity": "Error", "text": "x"}],
            library_names=set())
        cats = {g["category"] for g in groups}
        assert cats == {"assembler", "unknown"}

    def test_ai_group_first_in_display_order(self):
        groups = tfa.classify([E_LIB, E_SEQ], kb_blocks_dir=FACTORY_KB_BLOCKS)
        assert groups[0]["category"] == "ai_generated"

    def test_every_category_has_a_hint(self):
        for cat, hint in tfa.HINTS.items():
            assert hint and len(hint) > 20, f"hint missing for {cat}"

    def test_diff_helper(self):
        d = tfa.make_diff("a\n", "b\n", "f.scl")
        assert "-a" in d and "+b" in d


# ---------------------------------------------------------------------------
# tia_fix_propose — guards fire BEFORE any AI call
# ---------------------------------------------------------------------------

class TestProposeGuards:
    def test_mode_off_refuses_without_ai_call(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path), mode="off")
        calls: list = []
        _arm_ai(api, monkeypatch, calls=calls)
        _seed_job(api, [E_SEQ])
        _seed_fbseq(api.root)
        r = api.tia_fix_propose({})
        assert not r["ok"] and "disabled" in r["msg"]
        assert calls == [], "disabled mode must never reach the AI"

    def test_hints_mode_also_refuses(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path), mode="hints")
        calls: list = []
        _arm_ai(api, monkeypatch, calls=calls)
        _seed_job(api, [E_SEQ])
        _seed_fbseq(api.root)
        assert not api.tia_fix_propose({})["ok"]
        assert calls == []

    def test_non_fbseq_block_refused(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path), mode="suggest")
        calls: list = []
        _arm_ai(api, monkeypatch, calls=calls)
        _seed_job(api, [E_SEQ])
        _seed_fbseq(api.root)
        r = api.tia_fix_propose({"block": "FB_Motor_DOL"})
        assert not r["ok"] and "FB_Seq" in r["msg"]
        assert calls == [], "library blocks must never be sent for AI fixing"

    def test_no_ai_errors_refused(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path), mode="suggest")
        calls: list = []
        _arm_ai(api, monkeypatch, calls=calls)
        _seed_job(api, [E_LIB, E_TAG])  # nothing AI-generated failed
        _seed_fbseq(api.root)
        assert not api.tia_fix_propose({})["ok"]
        assert calls == []

    def test_validator_failing_proposal_never_shown(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path), mode="suggest")
        _arm_ai(api, monkeypatch, response=BROKEN_SCL)
        _seed_job(api, [E_SEQ])
        _seed_fbseq(api.root)
        r = api.tia_fix_propose({})
        assert not r["ok"] and "validator" in r["msg"].lower()
        assert getattr(api, "_tia_fix_proposal", None) is None

    def test_unchanged_source_is_not_a_proposal(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path), mode="suggest")
        _arm_ai(api, monkeypatch, response=OLD_SCL)
        _seed_job(api, [E_SEQ])
        _seed_fbseq(api.root)
        assert not api.tia_fix_propose({})["ok"]


# ---------------------------------------------------------------------------
# propose → apply happy path + approval gate
# ---------------------------------------------------------------------------

class TestProposeApply:
    def _propose(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path), mode="suggest")
        _arm_ai(api, monkeypatch)
        _seed_job(api, [E_SEQ])
        target = _seed_fbseq(api.root)
        r = api.tia_fix_propose({})
        assert r["ok"], r["msg"]
        return api, target, r

    def test_propose_returns_diff_and_writes_nothing(self, tmp_path, monkeypatch):
        api, target, r = self._propose(tmp_path, monkeypatch)
        assert "FB_Seq_Demo.scl" in r["proposal"]["file"]
        assert "+        ;" in r["proposal"]["diff"]
        assert target.read_text(encoding="utf-8") == OLD_SCL, (
            "propose must NOT touch the file — only apply may")
        log = (api.root / "AI_DECISION_LOG.jsonl").read_text(encoding="utf-8")
        assert "tia_fix:propose" in log

    def test_apply_requires_engineer_approval(self, tmp_path, monkeypatch):
        api, target, _ = self._propose(tmp_path, monkeypatch)
        assert not api.tia_fix_apply({})["ok"]
        assert not api.tia_fix_apply({"engineer": "E"})["ok"]
        assert not api.tia_fix_apply({"confirmed": True})["ok"]
        assert target.read_text(encoding="utf-8") == OLD_SCL

    def test_apply_writes_backup_audit_and_clears(self, tmp_path, monkeypatch):
        api, target, _ = self._propose(tmp_path, monkeypatch)
        r = api.tia_fix_apply({"engineer": "Test Eng", "confirmed": True})
        assert r["ok"], r["msg"]
        assert target.read_text(encoding="utf-8") == FIXED_SCL
        hist = list((target.parent / "_history").glob("*_FB_Seq_Demo.scl"))
        assert len(hist) == 1
        assert hist[0].read_text(encoding="utf-8") == OLD_SCL
        # The audit log stores prompt HASHES, not text — the engineer name
        # lives in the hashed prompt; the entry itself is what we verify.
        log = (api.root / "AI_DECISION_LOG.jsonl").read_text(encoding="utf-8")
        assert "tia_fix:apply" in log
        assert api._tia_fix_proposal is None
        assert "Re-run Import + Compile" in r["msg"], (
            "re-send is manual by design — the message must say so")

    def test_apply_without_proposal_refused(self, tmp_path):
        api = _mk_api(_proj(tmp_path))
        assert not api.tia_fix_apply({"engineer": "E", "confirmed": True})["ok"]

    def test_discard_clears_proposal(self, tmp_path, monkeypatch):
        api, target, _ = self._propose(tmp_path, monkeypatch)
        assert api.tia_fix_discard()["ok"]
        assert api._tia_fix_proposal is None
        assert not api.tia_fix_apply({"engineer": "E", "confirmed": True})["ok"]


# ---------------------------------------------------------------------------
# send_to_tia job: structured steps + error analysis wiring
# ---------------------------------------------------------------------------

def _wait_job(api, timeout=8.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = api.get_tia_send_status()
        if st.get("done"):
            return st
        time.sleep(0.05)
    raise AssertionError("TIA job did not finish in time")


class _FakeBridge:
    display_name = "TIA V19 (fake)"

    def __init__(self, result, step_script=()):
        self._result = result
        self._script = step_script
        self._on_status = None
        self._on_step = None

    def import_scl_to_project(self, ap, files, plc_name=None,
                              do_compile=True, tag_xml=None):
        for sid, stt, info in self._script:
            self._on_step(sid, stt, info)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def _send(api, bridge, tmp_path, mode="hints"):
    out = api.root / "_output" / "scl"
    out.mkdir(parents=True, exist_ok=True)
    if not list(out.glob("*.scl")):
        (out / "FB_Seq_Demo.scl").write_text(OLD_SCL, encoding="utf-8")
    ap = tmp_path / "plant.ap19"
    ap.write_text("", encoding="utf-8")
    mgr = _Mgr(mode=mode)
    mgr.get = lambda bid: bridge
    api._bridge_mgr = mgr
    r = api.send_to_tia({"project_path": str(ap), "import_tags": False})
    assert r["ok"], r["msg"]


class TestJobSteps:
    def test_steps_flow_into_status(self, tmp_path):
        api = _mk_api(_proj(tmp_path))
        res = BridgeResult(success=True, message="ok")
        bridge = _FakeBridge(res, step_script=[
            ("portal", "ok", ""), ("open_project", "ok", "plant.ap19"),
            ("find_plc", "ok", "PLC_1"), ("import_scl", "ok", "2 blocks"),
            ("compile", "ok", "0 errors"), ("save", "ok", "")])
        _send(api, bridge, tmp_path)
        st = _wait_job(api)
        steps = {s["id"]: s for s in st["steps"]}
        assert steps["prepare_tags"]["status"] == "skip"  # import_tags=False
        assert steps["compile"]["status"] == "ok"
        assert steps["import_scl"]["info"] == "2 blocks"
        assert "download" not in steps, "no download step in import-only flow"

    def test_crashed_step_never_left_running(self, tmp_path):
        api = _mk_api(_proj(tmp_path))
        bridge = _FakeBridge(RuntimeError("portal exploded"),
                             step_script=[("portal", "running", "")])
        _send(api, bridge, tmp_path)
        st = _wait_job(api)
        assert not st["succeeded"]
        steps = {s["id"]: s for s in st["steps"]}
        assert steps["portal"]["status"] == "fail", (
            "a step left 'running' by a crash must flip to fail — "
            "no eternal spinner in the GUI")

    def test_error_analysis_populated_in_hints_mode(self, tmp_path):
        api = _mk_api(_proj(tmp_path))
        res = BridgeResult(success=False, message="Compile ERRORS")
        res.compile_errors = [E_SEQ, E_LIB]
        bridge = _FakeBridge(res, step_script=[("compile", "fail", "2 errors")])
        _send(api, bridge, tmp_path, mode="hints")
        st = _wait_job(api)
        cats = {g["category"] for g in st["error_analysis"]}
        assert cats == {"ai_generated", "library"}
        assert st["fix_assist_mode"] == "hints"
        assert st["fix_proposal"] is None, "hints mode never pre-generates AI fixes"

    def test_error_analysis_off_mode_stays_raw(self, tmp_path):
        api = _mk_api(_proj(tmp_path))
        res = BridgeResult(success=False, message="Compile ERRORS")
        res.compile_errors = [E_SEQ]
        bridge = _FakeBridge(res)
        _send(api, bridge, tmp_path, mode="off")
        st = _wait_job(api)
        assert st["error_analysis"] == [], (
            "mode off = the user fixes everything line by line — no panels")

    def test_auto_propose_attaches_proposal(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path))
        _arm_ai(api, monkeypatch)
        res = BridgeResult(success=False, message="Compile ERRORS")
        res.compile_errors = [E_SEQ]
        bridge = _FakeBridge(res)
        _send(api, bridge, tmp_path, mode="auto_propose")
        st = _wait_job(api)
        assert st["fix_proposal"], "auto_propose must pre-generate the proposal"
        assert st["fix_proposal"]["block"] == "FB_Seq_Demo"
        target = api.root / "_output" / "scl" / "FB_Seq_Demo.scl"
        assert target.read_text(encoding="utf-8") == OLD_SCL, (
            "auto_propose NEVER applies — engineer approval still required")


# ---------------------------------------------------------------------------
# Settings: new keys persist, invalid mode rejected
# ---------------------------------------------------------------------------

class TestSettings:
    def test_roundtrip(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path))
        monkeypatch.setattr(fw, "_save_settings", lambda d: None)
        r = api.set_tia_settings({"live_progress": False,
                                  "fix_assist_mode": "suggest"})
        assert r["ok"]
        tia = api._bridge_mgr.tia_settings()
        assert tia["live_progress"] is False
        assert tia["fix_assist_mode"] == "suggest"

    def test_invalid_mode_rejected(self, tmp_path, monkeypatch):
        api = _mk_api(_proj(tmp_path))
        monkeypatch.setattr(fw, "_save_settings", lambda d: None)
        r = api.set_tia_settings({"fix_assist_mode": "auto_apply"})
        assert not r["ok"], (
            "auto_apply does not exist BY DESIGN — fixes always need approval")
        assert api._bridge_mgr.tia_settings()["fix_assist_mode"] == "hints"

    def test_assist_mode_fail_safe_default(self, tmp_path):
        api = _mk_api(_proj(tmp_path))
        api._bridge_mgr.tia_settings()["fix_assist_mode"] = "garbage"
        assert api._tia_assist_mode() == "hints"

    def test_defaults_in_bridge_manager(self):
        from bridges.bridge_manager import DEFAULT_BRIDGE_SETTINGS
        assert DEFAULT_BRIDGE_SETTINGS["tia"]["live_progress"] is True
        assert DEFAULT_BRIDGE_SETTINGS["tia"]["fix_assist_mode"] == "hints"


# ---------------------------------------------------------------------------
# Bridge step API (base class)
# ---------------------------------------------------------------------------

class TestBridgeStepApi:
    def test_step_callback_and_exception_safety(self):
        from bridges.base import BridgeBase, BridgeStatus

        class _B(BridgeBase):
            bridge_id = "t"

            def detect(self):
                return BridgeStatus.READY

        b = _B({}, on_status=None)
        seen = []
        b._on_step = lambda sid, stt, info: seen.append((sid, stt, info))
        b.step("compile", "running")
        assert seen == [("compile", "running", "")]
        b._on_step = lambda *a: 1 / 0
        b.step("compile", "ok")  # must not raise

    def test_job_step_ignores_unknown_ids(self):
        job = {"steps": [{"id": "compile", "label": "Compile",
                          "status": "pending", "info": ""}]}
        fw._job_step(job, "download", "ok")  # not in this flow — ignored
        fw._job_step(job, "compile", "ok", "0 errors")
        assert job["steps"][0]["status"] == "ok"
        assert job["steps"][0]["info"] == "0 errors"
