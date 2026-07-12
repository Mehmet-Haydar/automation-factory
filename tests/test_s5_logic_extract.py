"""Proof tests — deterministic S5 interlock extraction + self-proof.

The extractor's contract: whatever it emits was verified against the
original instruction stream on random vectors; whatever it cannot verify
it refuses loudly. These tests pin the RLO semantics (sequential AND/OR,
bare-O groups, parentheses, S/R latches, timers) and the refusal list.
"""
from __future__ import annotations

from s5_logic_extract import (
    And, Not, Or, Var, parse_network, render_expr,
)


def _p(lines):
    return parse_network("PBX", 1, list(lines))


# ---------------------------------------------------------------------------
# Core RLO semantics
# ---------------------------------------------------------------------------

def test_simple_and_chain():
    nl = _p(["\tA\tI 1.0", "\tAN\tF 2.0", "\t=\tQ 4.0"])
    assert nl.parsed and nl.verified_vectors > 0
    c = nl.coils["Q4.0"]
    assert render_expr(c.assign) == "I1.0 AND NOT M2.0", (
        "F bayrağı M'e çevrilmeli, sıralı AND doğru")


def test_bare_o_builds_or_of_and_groups():
    # A a A b O A c A d  =  (a AND b) OR (c AND d)
    nl = _p(["\tA\tI 1.0", "\tA\tI 1.1", "\tO", "\tA\tI 2.0",
             "\tA\tI 2.1", "\t=\tQ 4.0"])
    assert nl.parsed
    e = nl.coils["Q4.0"].assign
    env = {"I1.0": True, "I1.1": True, "I2.0": False, "I2.1": False}
    assert e.eval(env) is True
    env = {"I1.0": True, "I1.1": False, "I2.0": True, "I2.1": True}
    assert e.eval(env) is True
    env = {"I1.0": True, "I1.1": False, "I2.0": True, "I2.1": False}
    assert e.eval(env) is False


def test_parentheses():
    # A a A( O b O c ) = a AND (b OR c)
    nl = _p(["\tA\tI 1.0", "\tA(", "\tO\tI 2.0", "\tO\tI 2.1", "\t)",
             "\t=\tQ 4.0"])
    assert nl.parsed
    e = nl.coils["Q4.0"].assign
    assert e.eval({"I1.0": True, "I2.0": False, "I2.1": True})
    assert not e.eval({"I1.0": False, "I2.0": True, "I2.1": True})
    assert not e.eval({"I1.0": True, "I2.0": False, "I2.1": False})


def test_set_reset_latch_records_both_conditions():
    nl = _p(["\tA\tI 8.0", "\tS\tF 8.0", "\tAN\tI 8.1", "\tO\tI 4.6",
             "\tR\tF 8.0", "\tNOP\t0"])
    assert nl.parsed
    c = nl.coils["M8.0"]
    assert render_expr(c.set_cond) == "I8.0"
    assert render_expr(c.reset_cond) == "NOT I8.1 OR I4.6"
    assert c.assign is None


def test_consecutive_coils_share_rlo():
    nl = _p(["\tA\tI 1.0", "\t=\tQ 4.0", "\t=\tQ 4.1"])
    assert nl.parsed
    assert render_expr(nl.coils["Q4.0"].assign) == "I1.0"
    assert render_expr(nl.coils["Q4.1"].assign) == "I1.0"


def test_timer_recorded_with_start_condition_and_used_as_input():
    nl = _p(["\tA\tF 3.0", "\tL\tKT 050.0", "\tSE\tT 1", "\tNOP\t0",
             "\tA\tT 1", "\t=\tQ 28.4"])
    assert nl.parsed
    t = nl.timers["T1"]
    assert t.kind == "SE" and t.literal.startswith("KT")
    assert render_expr(t.start) == "M3.0"
    assert render_expr(nl.coils["Q28.4"].assign) == "T1"


# ---------------------------------------------------------------------------
# Fail-safe refusals — "bilmiyorum" loudly
# ---------------------------------------------------------------------------

def test_jump_refused():
    nl = _p(["\tA\tI 1.0", "\tJC\t=M001", "M001:\tS\tQ 4.0"])
    assert not nl.parsed and "JC" in nl.reason


def test_word_load_refused_but_time_literal_allowed():
    assert not _p(["\tL\tKF +5", "\tT\tFW 111", "\t=\tQ 1.0"]).parsed
    assert _p(["\tA\tI 1.0", "\tL\tKT 100.1", "\tSD\tT 9", "\tNOP\t0",
               "\tA\tT 9", "\t=\tQ 1.0"]).parsed


def test_unknown_instruction_refused():
    nl = _p(["\tFOO\tI 1.0", "\t=\tQ 1.0"])
    assert not nl.parsed


def test_trailing_be_is_harmless():
    nl = _p(["\tA\tI 1.0", "\t=\tQ 4.0", "\tBE"])
    assert nl.parsed, "blok sonu BE ağı düşürmemeli"


def test_no_coil_refused():
    nl = _p(["\tA\tI 1.0", "\tA\tI 1.1"])
    assert not nl.parsed and "no coil" in nl.reason


# ---------------------------------------------------------------------------
# The proof itself
# ---------------------------------------------------------------------------

def test_every_parsed_network_reports_vectors():
    nl = _p(["\tA\tI 1.0", "\tO\tI 1.1", "\tAN\tF 5.5", "\t=\tQ 2.2"])
    assert nl.parsed and nl.verified_vectors >= 128


def test_expression_tree_types():
    nl = _p(["\tA\tI 1.0", "\tO\tI 1.1", "\t=\tQ 2.2"])
    e = nl.coils["Q2.2"].assign
    assert isinstance(e, Or)
    assert isinstance(e.a, Var) and isinstance(e.b, Var)
    assert render_expr(Not(And(Var("I1.0"), Var("I1.1")))) \
        == "NOT (I1.0 AND I1.1)"


def test_titled_network_headers_are_not_dropped(tmp_path):
    """S5W writes named networks as "[13<TAB>FLM Einrichtanwahl" — the old
    number-only header regex silently DROPPED every titled network
    (live finding 2026-07-06: PB1 lost 15/34 nets). Titles must parse."""
    from pathlib import Path

    from s5_logic_extract import extract_project_logic

    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "PB9.AWL").write_text(
        "###PG:82000000\n"
        "[1\t\n\tA\tI 0.0\n\t=\tQ 1.0\n\t***\t]\n"
        "[2\tFLM Einrichtanwahl\n\tA\tI 7.0\n\t=\tF 6.1\n\t***\t]\n"
        "[3\tNetzwerk mit Titel 3\n\tA\tI 7.1\n\t=\tF 6.3\n\tBE\t]\n",
        encoding="utf-8")
    nets = extract_project_logic(tmp_path)
    assert [n.network for n in nets] == [1, 2, 3], \
        "başlıklı ağlar sessizce düşürülemez"
    assert all(n.parsed for n in nets)
