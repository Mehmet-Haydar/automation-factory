"""Version Compare GUI API (factory_web.Api.version_compare_*).

The deterministic scan/diff deliberately works WITHOUT an open project
(api.root=None) — it is local and side-effect free. The diff endpoint
addresses files by (version index, relname) so the JS bridge never passes
raw absolute paths; traversal attempts are refused.
"""

from __future__ import annotations

import importlib
from pathlib import Path

fw = importlib.import_module("factory_web")

SEQ_TAB = (
    b"\tE    1.0\tE 1.0\tMOTOR EIN\r\n"
    b"\tE    1.1\tE 1.1\tMOTOR AUS\r\n"
)


def _mk_api(root=None):
    api = object.__new__(fw.Api)
    api.settings = {"api_keys": {}}
    api.root = root
    return api


def _mk_versions(tmp_path: Path) -> tuple[str, str]:
    v1 = tmp_path / "2018-08-18"; v1.mkdir()
    v2 = tmp_path / "_aktiv"; v2.mkdir()
    (v1 / "4711Z0.SEQ").write_bytes(SEQ_TAB)
    (v2 / "4711Z0.SEQ").write_bytes(SEQ_TAB.replace(b"MOTOR AUS", b"MOTOR HALT"))
    (v1 / "old_only.txt").write_bytes(b"alt\r\n")
    return str(v1), str(v2)


class TestScan:
    def test_requires_two_folders(self):
        api = _mk_api()
        assert api.version_compare_scan([])["ok"] is False
        assert api.version_compare_scan(["only-one"])["ok"] is False
        assert api.version_compare_scan("not-a-list")["ok"] is False

    def test_works_without_open_project(self, tmp_path):
        v1, v2 = _mk_versions(tmp_path)
        api = _mk_api(root=None)
        r = api.version_compare_scan([v1, v2])
        assert r["ok"], r.get("msg")
        assert r["summary"]["total"] == 2
        assert "_warnings" in r, "every public API response carries _warnings"

    def test_missing_folder_is_honest(self, tmp_path):
        api = _mk_api()
        r = api.version_compare_scan([str(tmp_path), str(tmp_path / "nope")])
        assert r["ok"] is False
        assert "nope" in r["msg"]


class TestDiff:
    def test_diff_before_scan_refused(self):
        api = _mk_api()
        r = api.version_compare_diff(0, 1, "x.txt")
        assert r["ok"] is False
        assert "scan" in r["msg"].lower()

    def test_happy_path_seq(self, tmp_path):
        v1, v2 = _mk_versions(tmp_path)
        api = _mk_api()
        assert api.version_compare_scan([v1, v2])["ok"]
        d = api.version_compare_diff(0, 1, "4711Z0.SEQ")
        assert d["ok"] and d["mode"] == "seq"
        assert d["changed"][0]["operand"] == "E 1.1"

    def test_missing_side_becomes_removed_only(self, tmp_path):
        v1, v2 = _mk_versions(tmp_path)
        api = _mk_api()
        assert api.version_compare_scan([v1, v2])["ok"]
        d = api.version_compare_diff(0, 1, "old_only.txt")
        assert d["ok"] and d["mode"] == "removed_only"

    def test_traversal_refused(self, tmp_path):
        v1, v2 = _mk_versions(tmp_path)
        api = _mk_api()
        assert api.version_compare_scan([v1, v2])["ok"]
        secret = tmp_path / "secret.txt"
        secret.write_text("top secret")
        for bad in ("..\\secret.txt", "../secret.txt", str(secret)):
            d = api.version_compare_diff(0, 1, bad)
            assert d["ok"] is False, f"must refuse {bad!r}"

    def test_invalid_index_refused(self, tmp_path):
        v1, v2 = _mk_versions(tmp_path)
        api = _mk_api()
        assert api.version_compare_scan([v1, v2])["ok"]
        assert api.version_compare_diff(0, 99, "x")["ok"] is False
        assert api.version_compare_diff("a", 1, "x")["ok"] is False


# ---------------------------------------------------------------------------
# Version Compare AI hypotheses (S-20 + audit gate) — taşındı: test_version_compare_ai.py
# ---------------------------------------------------------------------------

import json as _json  # noqa: E402

_GOOD_REPLY = (
    "HYPOTHESIS: Timer description updated after commissioning tuning "
    "| CONFIDENCE: medium | EVIDENCE: ~ E 1.1 desc changed\n"
    "HYPOTHESIS: Hydraulics enable chain re-wired — SAFETY: engineer "
    "review required | CONFIDENCE: low | EVIDENCE: + E 2.0 added"
)

_SEQ_OLD = (
    b"\tE    1.0\tE 1.0\tMOTOR EIN\r\n"
    b"\tE    1.1\tE 1.1\tMUELLER GMBH ALT\r\n"
)
_SEQ_NEW = (
    b"\tE    1.0\tE 1.0\tMOTOR EIN\r\n"
    b"\tE    1.1\tE 1.1\tMUELLER GMBH NEU\r\n"
)


def _mk_hyp_project(tmp_path: Path, classification: str = "INTERNAL") -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "PROJECT_STATE.json").write_text(
        _json.dumps({"data_classification": classification, "customer": "MUELLER GMBH"}),
        encoding="utf-8")
    return root


def _mk_hyp_versions(tmp_path: Path) -> list:
    v1 = tmp_path / "2018-08-18"; v1.mkdir()
    v2 = tmp_path / "_aktiv"; v2.mkdir()
    (v1 / "4711Z0.SEQ").write_bytes(_SEQ_OLD)
    (v2 / "4711Z0.SEQ").write_bytes(_SEQ_NEW)
    return [str(v1), str(v2)]


def _mk_hyp_api(root=None):
    api = object.__new__(fw.Api)
    api.settings = {"api_keys": {"anthropic": "test-key-1234"}}
    api.root = root
    return api


class _FakeHypAIClient:
    reply = ""
    calls: list = []

    def __init__(self, provider=None, api_key=None, model=None):
        pass

    def chat(self, system="", user="", max_tokens=0):
        _FakeHypAIClient.calls.append({"system": system, "user": user})
        return self.__class__.reply, {"in": 1, "out": 1}


def _mock_hyp_ai(monkeypatch, reply: str):
    import ai_client
    _FakeHypAIClient.reply = reply
    _FakeHypAIClient.calls = []
    monkeypatch.setattr(ai_client, "AIClient", _FakeHypAIClient)


class TestVersionCompareHypotheses:
    """S-20 + audit gate: AI hypothesis generation safeguards."""

    def test_no_open_project_refused(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, _GOOD_REPLY)
        api = _mk_hyp_api(root=None)
        r = api.version_compare_hypotheses(_mk_hyp_versions(tmp_path))
        assert r["ok"] is False
        assert "Open a project" in r["msg"]
        assert _FakeHypAIClient.calls == []

    def test_bad_folders_refused(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, _GOOD_REPLY)
        api = _mk_hyp_api(root=_mk_hyp_project(tmp_path))
        assert api.version_compare_hypotheses([])["ok"] is False
        assert _FakeHypAIClient.calls == []

    def test_missing_api_key_refused(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, _GOOD_REPLY)
        api = _mk_hyp_api(root=_mk_hyp_project(tmp_path))
        api.settings["api_keys"] = {}
        r = api.version_compare_hypotheses(_mk_hyp_versions(tmp_path))
        assert r["ok"] is False and "API key" in r["msg"]
        assert _FakeHypAIClient.calls == []

    def test_restricted_blocked_ai_never_called(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, _GOOD_REPLY)
        api = _mk_hyp_api(root=_mk_hyp_project(tmp_path, "RESTRICTED"))
        r = api.version_compare_hypotheses(_mk_hyp_versions(tmp_path))
        assert r["ok"] is False and "[C4]" in r["msg"]
        assert _FakeHypAIClient.calls == []

    def test_confidential_needs_consent(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, _GOOD_REPLY)
        folders = _mk_hyp_versions(tmp_path)
        api = _mk_hyp_api(root=_mk_hyp_project(tmp_path, "CONFIDENTIAL"))
        r = api.version_compare_hypotheses(folders)
        assert r["ok"] is False and "[C4]" in r["msg"]
        assert _FakeHypAIClient.calls == []
        r = api.version_compare_hypotheses(folders, {"confirmed": True})
        assert r["ok"] is True, r.get("msg")
        assert len(_FakeHypAIClient.calls) == 1

    def test_audit_failure_blocks_before_chat(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, _GOOD_REPLY)
        def _boom(*a, **kw): raise fw.AuditLogError("log not writable")
        monkeypatch.setattr(fw, "_audit_log", _boom)
        api = _mk_hyp_api(root=_mk_hyp_project(tmp_path))
        r = api.version_compare_hypotheses(_mk_hyp_versions(tmp_path))
        assert r["ok"] is False and "[EU AI Act]" in r["msg"]
        assert _FakeHypAIClient.calls == []

    def test_internal_customer_name_not_in_prompt(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, _GOOD_REPLY)
        api = _mk_hyp_api(root=_mk_hyp_project(tmp_path, "INTERNAL"))
        r = api.version_compare_hypotheses(_mk_hyp_versions(tmp_path))
        assert r["ok"] is True, r.get("msg")
        prompt = _FakeHypAIClient.calls[0]["user"]
        assert "E 1.1" in prompt
        assert "MUELLER GMBH" not in prompt, "S-20: customer name must be anonymized"
        log = (api.root / "AI_DECISION_LOG.jsonl").read_text(encoding="utf-8")
        assert "MUELLER GMBH" not in log

    def test_audit_log_written_on_success(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, _GOOD_REPLY)
        api = _mk_hyp_api(root=_mk_hyp_project(tmp_path))
        assert api.version_compare_hypotheses(_mk_hyp_versions(tmp_path))["ok"] is True
        log = (api.root / "AI_DECISION_LOG.jsonl").read_text(encoding="utf-8")
        assert "vcompare:hypotheses" in log

    def test_well_formed_reply_parsed_into_cards(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, _GOOD_REPLY)
        api = _mk_hyp_api(root=_mk_hyp_project(tmp_path))
        r = api.version_compare_hypotheses(_mk_hyp_versions(tmp_path))
        assert r["ok"] is True and r["label"] == "DRAFT_UNVERIFIED"
        hs = r["hypotheses"]
        assert len(hs) == 2
        assert hs[0]["confidence"] == "medium"
        assert "E 1.1" in hs[0]["evidence"]
        assert "SAFETY: engineer review required" in hs[1]["text"]

    def test_malformed_reply_degrades_to_raw_card(self, tmp_path, monkeypatch):
        _mock_hyp_ai(monkeypatch, "The changes look like routine maintenance.")
        api = _mk_hyp_api(root=_mk_hyp_project(tmp_path))
        r = api.version_compare_hypotheses(_mk_hyp_versions(tmp_path))
        assert r["ok"] is True
        assert len(r["hypotheses"]) == 1, "no silent loss — raw becomes one card"
        assert "maintenance" in r["raw"]
