"""Proof tests — Schrittkette detection from proven S/R logic."""
from __future__ import annotations

from s5_logic_extract import parse_network
from sequence_map import build_chains


def _chain_nets():
    """M1.0 -> M1.1 -> M1.2 step chain + one unrelated latch."""
    n1 = parse_network("PB9", 1, [
        "\tA\tI 0.0", "\tS\tF 1.0",
        "\tA\tF 1.1", "\tO\tF 9.9", "\tR\tF 1.0"])
    n2 = parse_network("PB9", 2, [
        "\tA\tF 1.0", "\tA\tI 0.1", "\tS\tF 1.1",
        "\tA\tF 1.2", "\tR\tF 1.1"])
    n3 = parse_network("PB9", 3, [
        "\tA\tF 1.1", "\tA\tI 0.2", "\tS\tF 1.2",
        "\tA\tF 9.9", "\tR\tF 1.2"])
    n4 = parse_network("PB9", 4, [   # unrelated latch (no chain)
        "\tA\tI 5.0", "\tS\tF 50.0", "\tA\tI 5.1", "\tR\tF 50.0"])
    return [n1, n2, n3, n4]


def test_chain_detected_and_ordered():
    latches, chains = build_chains(_chain_nets())
    assert "M1.0" in latches and "M50.0" in latches
    assert len(chains) == 1, "3 adımlık tek zincir bulunmalı"
    assert chains[0] == ["M1.0", "M1.1", "M1.2"], "topolojik sıra korunmalı"


def test_negated_reference_is_not_an_edge():
    # M2.1's SET contains NOT M2.0 — lockout, not a predecessor
    a = parse_network("PB9", 1, [
        "\tA\tI 0.0", "\tS\tF 2.0", "\tA\tI 0.1", "\tR\tF 2.0"])
    b = parse_network("PB9", 2, [
        "\tAN\tF 2.0", "\tA\tI 0.2", "\tS\tF 2.1",
        "\tA\tI 0.3", "\tR\tF 2.1"])
    c = parse_network("PB9", 3, [
        "\tA\tF 2.1", "\tA\tI 0.4", "\tS\tF 2.2",
        "\tA\tI 0.5", "\tR\tF 2.2"])
    latches, chains = build_chains([a, b, c])
    # M2.0 must not be chained to M2.1 (negated); M2.1->M2.2 alone is only
    # a 2-node component -> below the ≥3 threshold
    assert chains == []


def test_assign_only_flags_are_not_steps():
    n = parse_network("PB9", 1, ["\tA\tI 0.0", "\t=\tF 3.0"])
    latches, chains = build_chains([n])
    assert "M3.0" not in latches, "salt '=' merker adım kilidi değildir"


# ---------------------------------------------------------------------------
# RD03 cross-check — AI story vs proven chain
# ---------------------------------------------------------------------------

def _rd03(tmp_path, rows: str):
    md = tmp_path / "metadata"
    md.mkdir(parents=True, exist_ok=True)
    (md / "RD03_Flowchart.md").write_text(
        "## Step Sequence\n"
        "| StepID | StepName | EntryCondition | Actions | ExitCondition "
        "| NextStep | Status |\n"
        "|--|--|--|--|--|--|--|\n" + rows, encoding="utf-8")


def _legacy_chain(tmp_path):
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "PB9.AWL").write_text(
        "###PG:82000000\n"
        "[1\t\n\tA\tI 0.0\n\tS\tF 1.0\n\tA\tF 1.1\n\tR\tF 1.0\n\t***\t]\n"
        "[2\t\n\tA\tF 1.0\n\tA\tI 0.1\n\tS\tF 1.1\n\tA\tF 1.2\n\tR\tF 1.1\n"
        "\t***\t]\n"
        "[3\t\n\tA\tF 1.1\n\tA\tI 0.2\n\tS\tF 1.2\n\tA\tI 0.3\n\tR\tF 1.2\n"
        "\tBE\t]\n",
        encoding="utf-8")


def test_rd03_crosscheck_confirms_true_story(tmp_path):
    from sequence_map import crosscheck_rd03
    _legacy_chain(tmp_path)
    _rd03(tmp_path,
          "| S001 | a | x | Set F 1.0 (step1) | y | S002 | DRAFT |\n"
          "| S002 | b | x | Set F 1.1 (step2) | y | S003 | DRAFT |\n"
          "| S003 | c | x | Set F 1.2 (step3) | y | (end) | DRAFT |\n")
    r = crosscheck_rd03(tmp_path)
    assert r.steps == 3 and r.known_markers == 3
    assert r.edges_checked == 2 and r.edges_confirmed == 2
    assert not r.mismatches


def test_rd03_crosscheck_catches_invented_step_and_wrong_order(tmp_path):
    from sequence_map import crosscheck_rd03
    _legacy_chain(tmp_path)
    _rd03(tmp_path,
          "| S001 | a | x | Set F 1.1 (step2!) | y | S002 | DRAFT |\n"
          "| S002 | b | x | Set F 1.0 (step1!) | y | S003 | DRAFT |\n"
          "| S003 | c | x | Set F 7.7 (uydurma) | y | (end) | DRAFT |\n")
    r = crosscheck_rd03(tmp_path)
    assert r.known_markers == 2, "M7.7 kanıtlı kilit değil"
    assert r.edges_confirmed == 0, "ters sıra onaylanmamalı"
    assert any("M7.7" in m for m in r.mismatches)
    assert any("order may be wrong" in m for m in r.mismatches)
