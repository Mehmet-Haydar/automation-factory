"""S-7 (B-P4) — IO-list validation errors must block gate advance.

io_validator flagged duplicate addresses as severity="error", but the
result never reached PROJECT_STATE, so _gate_advance_blockers could not
see it: a project with two signals on the same physical address could
sign off Gate 4 and generate code against a broken IO map.
"""

from __future__ import annotations

import importlib
import json

fw = importlib.import_module("factory_web")


class TestBlockerLogic:
    RD = {f"RD{n:02d}": "done" for n in range(1, 15)}

    def test_io_errors_block_validation_gate(self):
        # Gate 5 (Validation) carries a validate action and is non-approval.
        blockers = fw._gate_advance_blockers(
            5, self.RD, "Eng", {"errors": 0, "scope": "compile"},
            last_io_validation={"errors": 2, "file": "RD01_IO_List.md"})
        assert any("IO list" in b for b in blockers), blockers

    def test_io_errors_block_human_review_gate(self):
        # extract_io was removed from gate actions; IO-list errors are now gated
        # at the validate gates. Gate 3 (Human Review) carries a validate action.
        blockers = fw._gate_advance_blockers(
            3, self.RD, "Hans Becker (TÜV)",
            last_io_validation={"errors": 1, "file": "RD01_IO_List.md"})
        assert any("IO list" in b for b in blockers), blockers

    def test_clean_io_validation_does_not_block(self):
        blockers = fw._gate_advance_blockers(
            5, self.RD, "Eng", {"errors": 0, "scope": "compile"},
            last_io_validation={"errors": 0, "file": "RD01_IO_List.md"})
        assert not any("IO list" in b for b in blockers), blockers

    def test_not_run_yet_does_not_block(self):
        # Same semantics as last_validation: absent == not run → no blocker.
        blockers = fw._gate_advance_blockers(
            5, self.RD, "Eng", {"errors": 0, "scope": "compile"},
            last_io_validation=None)
        assert not any("IO list" in b for b in blockers), blockers

    def test_gate_without_io_actions_unaffected(self):
        # Gate 7 (export/send only) — IO result must not block it.
        blockers = fw._gate_advance_blockers(
            7, self.RD, "Eng", {"errors": 0, "scope": "compile"},
            last_io_validation={"errors": 3, "file": "RD01_IO_List.md"})
        assert not any("IO list" in b for b in blockers), blockers


class TestValidatePersistsResult:
    def _api(self, tmp_path):
        api = object.__new__(fw.Api)
        api.settings = {}
        api.root = tmp_path
        return api

    def test_validate_io_list_writes_state(self, tmp_path, monkeypatch):
        md = tmp_path / "RD01_IO_List.md"
        md.write_text("| Tag |\n|---|\n| X |\n", encoding="utf-8")

        from workbench.core import io_list_io, io_validator

        class _Issue:
            row_index, column, severity, message = 1, "address", "error", "Duplicate address"

        monkeypatch.setattr(io_list_io, "read_md", lambda p: ([{"tag": "X"}], {}))
        monkeypatch.setattr(io_validator, "validate_rows",
                            lambda rows, platform: [_Issue(), _Issue()])

        r = self._api(tmp_path).validate_io_list("RD01_IO_List.md")
        assert r["ok"] and len(r["issues"]) == 2
        state = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        assert state["last_io_validation"]["errors"] == 2
        assert state["last_io_validation"]["file"] == "RD01_IO_List.md"

    def test_scl_validation_evidence_not_clobbered(self, tmp_path, monkeypatch):
        # The IO result lives under its own key — the W-A5 compile evidence
        # in last_validation must survive an IO validation run.
        (tmp_path / "PROJECT_STATE.json").write_text(
            json.dumps({"last_validation": {"errors": 0, "scope": "compile"}}),
            encoding="utf-8")
        md = tmp_path / "RD01_IO_List.md"
        md.write_text("| Tag |\n|---|\n", encoding="utf-8")

        from workbench.core import io_list_io, io_validator
        monkeypatch.setattr(io_list_io, "read_md", lambda p: ([], {}))
        monkeypatch.setattr(io_validator, "validate_rows", lambda rows, platform: [])

        self._api(tmp_path).validate_io_list("RD01_IO_List.md")
        state = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))
        assert state["last_validation"] == {"errors": 0, "scope": "compile"}
        assert state["last_io_validation"]["errors"] == 0
