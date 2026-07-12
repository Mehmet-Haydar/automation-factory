"""IO reconciliation — cross-source provenance + delta (deterministic).

Parses the produced RD01 IO table and reports where each signal came from,
what is new (in the new design, not in legacy), orphaned (legacy only),
duplicated (address conflict) — the engineer validates this before code gen.
"""

from __future__ import annotations

import json
from pathlib import Path

import factory_web as fw

_HEADER = (
    "| Tag | Address | Type | Dir | Equipment | Description | NormalState | "
    "EngUnit | RangeMin | RangeMax | Safety | SrcModule | OldTag | Notes | Status |\n"
    "|-----|---------|------|-----|-----------|-------------|-------------|"
    "---------|----------|---------|--------|----------|--------|-------|--------|\n"
)

_ROWS = (
    "| MOT_A | %Q0.0 | DQ | OUT | Conv | run | | | | | NO | EPLAN-1 | | | DRAFT_UNVERIFIED |\n"
    "| MOT_B | %Q0.0 | DQ | OUT | Conv | run2 | | | | | NO | EPLAN-1 | OLD_MOTB | | DRAFT_UNVERIFIED |\n"
    "| SENS_C | | DI | IN | Conv | sensor | | | | | YES | CODE | OLD_SENSC | | DRAFT_UNVERIFIED |\n"
    "| GHOST_D | | DI | IN | Conv | ghost | | | | | NO | ? | | | DRAFT_UNVERIFIED |\n"
)

_RD01 = (
    "---\nstatus: DRAFT_UNVERIFIED\n---\n# RD01 IO List\n\n## Signals\n"
    + _HEADER + _ROWS
    + "\n## Conflicts\nMOT_A and MOT_B share %Q0.0.\n"
)


def _api(root: Path, rd01: str = _RD01) -> fw.Api:
    (root / "PROJECT_STATE.json").write_text(json.dumps({"gate": 4}), encoding="utf-8")
    md = root / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD01_IO_List.md").write_text(rd01, encoding="utf-8")
    api = fw.Api()
    api.root = root
    api.settings = {"username": "Eng"}
    return api


def test_reconciliation_report(tmp_path):
    r = _api(tmp_path).get_io_reconciliation()
    assert r["ok"] and r["exists"]
    rep = r["report"]
    assert rep["total"] == 4
    assert rep["by_source"] == {"EPLAN-1": 2, "CODE": 1, "?": 1}
    assert "MOT_A" in rep["new_signals"]          # address, no legacy tag
    assert "SENS_C" in rep["orphan_signals"]      # legacy tag, no address
    assert "GHOST_D" in rep["ghost_rows"]         # neither
    assert "%Q0.0" in rep["duplicate_addresses"]  # conflict
    assert rep["errors"] == 1 and rep["safety"] == 1
    # AI-written section surfaced verbatim
    assert "Conflicts" in r["sections"]


def test_ack_flow_and_staleness(tmp_path):
    api = _api(tmp_path)
    assert api.get_io_reconciliation()["acknowledged"] is False
    assert api.ack_io_reconciliation("checked")["ok"] is True
    r = api.get_io_reconciliation()
    assert r["acknowledged"] is True and r["ack"]["by"] == "Eng"
    # Editing RD01 invalidates the ack (hash changes → re-validate).
    (tmp_path / "metadata" / "RD01_IO_List.md").write_text(_RD01 + "\nedit\n", encoding="utf-8")
    r2 = api.get_io_reconciliation()
    assert r2["acknowledged"] is False and r2["stale_ack"] is True


def test_gate4_blocked_without_reconciliation_ack():
    rd = {f"RD{n:02d}": "done" for n in range(1, 15)}
    b = fw._gate_advance_blockers(4, rd, "Hans Becker (TÜV)", io_reconciliation_ok=False)
    assert any("reconciliation" in x.lower() for x in b)
    b2 = fw._gate_advance_blockers(4, rd, "Hans Becker (TÜV)", io_reconciliation_ok=True)
    assert not any("reconciliation" in x.lower() for x in b2)


def test_no_rd01_file_is_graceful(tmp_path):
    (tmp_path / "PROJECT_STATE.json").write_text(json.dumps({"gate": 4}), encoding="utf-8")
    api = fw.Api(); api.root = tmp_path; api.settings = {}
    r = api.get_io_reconciliation()
    assert r["ok"] is False and r.get("exists") is False
