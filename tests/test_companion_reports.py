"""Proof tests — assumption ledger, traceability matrix, stem propagation."""
from __future__ import annotations

from pathlib import Path

from assumption_ledger import generate_assumption_ledger
from rd01_autocomplete import propagate_equipment_by_stem
from traceability_matrix import generate_traceability_matrix


# ---------------------------------------------------------------------------
# Stem propagation — guarded inheritance
# ---------------------------------------------------------------------------

def test_stem_propagation_inherits_unique_match():
    rows = [
        {"desc": "KE ROLLENBAHN 1.1 * 7-M3 (EINLAUF)", "equipment": "M3"},
        {"desc": "K ROLLENBAHN 1.1 SCHUETZ (EINLAUF)", "equipment": ""},
        {"desc": "K ROLLENBAHN 1.2 SCHUETZ", "equipment": ""},
    ]
    n = propagate_equipment_by_stem(rows)
    assert n == 1
    assert rows[1]["equipment"] == "M3", "aynı makine parçası mirası"
    assert rows[2]["equipment"] == "", "1.2 farklı parça — dokunulmaz"


def test_stem_propagation_refuses_ambiguity_and_generic_words():
    rows = [
        {"desc": "KE ROLLENBAHN 1 * 7-M3", "equipment": "M3"},
        {"desc": "KE ROLLENBAHN 1 * 7-M4", "equipment": "M4"},
        {"desc": "K ROLLENBAHN 1 SCHUETZ", "equipment": ""},   # 2 aday
        {"desc": "KE HYDRAULIK", "equipment": "P1"},
        {"desc": "ST HYDRAULIK EIN", "equipment": ""},          # sayı yok
    ]
    n = propagate_equipment_by_stem(rows)
    assert n == 0, "belirsizlik ve sayısız eşleşme ASLA doldurmaz"
    assert rows[2]["equipment"] == "" and rows[4]["equipment"] == ""


# ---------------------------------------------------------------------------
# Assumption ledger
# ---------------------------------------------------------------------------

def _mini_project(tmp_path: Path) -> Path:
    md = tmp_path / "metadata"
    md.mkdir(parents=True)
    (md / "RD01_IO_List.md").write_text(
        "| Tag | Address | Type | Dir | Equipment | Description | OldTag | Notes | Status |\n"
        "|--|--|--|--|--|--|--|--|--|\n"
        "| A | %I1.0 | DI | IN | M1 | x | | | DRAFT_UNVERIFIED |\n",
        encoding="utf-8")
    (md / "RD05_Safety_DRAFT_UNVERIFIED.md").write_text(
        "status: DRAFT_UNVERIFIED\nNOT_VERIFIED estop chain\n",
        encoding="utf-8")
    (md / "RD03_Flowchart.md").write_text(
        "## Assumptions\n- ASSUMPTION: start interlock inferred from code\n",
        encoding="utf-8")
    rep = tmp_path / "REPORTS"
    rep.mkdir()
    (rep / "ASSEMBLY_REPORT.md").write_text(
        "Result: OK — Assembled 2 device instance(s), 5 unknown item(s) "
        "need engineering.\n"
        "- **M1**: in_bFeedbackRun ambiguous — candidates: A, B (wire "
        "manually)\n",
        encoding="utf-8")
    return tmp_path


def test_ledger_collects_all_uncertainty_classes(tmp_path):
    root = _mini_project(tmp_path)
    s = generate_assumption_ledger(root)
    text = s.report_path.read_text(encoding="utf-8")
    assert s.blockers >= 1, "RD05 imza zorunluluğu BLOCKER"
    assert "NOT_VERIFIED" in text
    assert "ambiguous" in text
    assert "5 #UNKNOWN" in text
    assert "ASSUMPTION: start interlock" in text
    assert "DRAFT_UNVERIFIED" in text


# ---------------------------------------------------------------------------
# Traceability matrix
# ---------------------------------------------------------------------------

def test_matrix_joins_rd01_manifest_and_ob1(tmp_path):
    root = _mini_project(tmp_path)
    out = root / "_output" / "scl"
    out.mkdir(parents=True)
    (out / "OB_Main.scl").write_text(
        '    "iDB_M1"(\n        in_bFeedbackRun := "A"\n    );\n',
        encoding="utf-8")
    (out / "_assembly_manifest.json").write_text(
        '{"devices": {"M1": {"row_hash": "x", "fb": "FB_Motor_DOL"}}}',
        encoding="utf-8")
    s = generate_traceability_matrix(root)
    assert s.rows == 1 and s.bound == 1 and s.with_device == 1
    text = s.report_path.read_text(encoding="utf-8")
    assert "| A | %I1.0 | M1 | FB_Motor_DOL | `iDB_M1.in_bFeedbackRun` |" \
        in text.replace("| x |", "| x |") or "iDB_M1.in_bFeedbackRun" in text
