"""Proof tests — Machine Dossier generator (deterministic, no AI)."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from machine_dossier import (
    build_decision_rows, build_state_table, generate_machine_dossier,
    parse_block_calls,
)

_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / \
    "Kunde_Mueller_Conveyor_Retrofit"


def _mk_project(tmp_path: Path) -> Path:
    """Two S5 threads: thread A (M1.0→M1.2, enable rail M8.0, reset rail
    M9.0) triggers thread B (M2.0→M2.2) via M1.2 — WITHOUT a reset link,
    exactly the 1N→2N pattern of the blind-test machine."""
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "PB9.AWL").write_text(
        "###PG:82000000\n"
        "[1\t\n\tA\tI 0.0\n\tA\tF 8.0\n\tS\tF 1.0\n"
        "\tA\tF 1.1\n\tO\tF 9.0\n\tR\tF 1.0\n\t***\t]\n"
        "[2\t\n\tA\tF 1.0\n\tA\tI 0.1\n\tA\tF 8.0\n\tS\tF 1.1\n"
        "\tA\tF 1.2\n\tO\tF 9.0\n\tR\tF 1.1\n\t***\t]\n"
        "[3\t\n\tA\tF 1.1\n\tA\tI 0.2\n\tA\tF 8.0\n\tS\tF 1.2\n"
        "\tA\tI 0.3\n\tO\tF 9.0\n\tR\tF 1.2\n\tBE\t]\n",
        encoding="utf-8")
    (legacy / "PB10.AWL").write_text(
        "###PG:82000000\n"
        "[1\t\n\tA\tF 1.2\n\tA\tI 1.0\n\tS\tF 2.0\n"
        "\tA\tF 2.1\n\tR\tF 2.0\n\t***\t]\n"
        "[2\t\n\tA\tF 2.0\n\tA\tI 1.1\n\tS\tF 2.1\n"
        "\tA\tF 2.2\n\tR\tF 2.1\n\t***\t]\n"
        "[3\t\n\tA\tF 2.1\n\tA\tI 1.2\n\tS\tF 2.2\n"
        "\tA\tI 1.3\n\tR\tF 2.2\n\tBE\t]\n",
        encoding="utf-8")
    (legacy / "OB1.AWL").write_text(
        "###PG:80000000\n"
        "[1\t\n\tJU\tPB 9\n\tJU\tPB 10\n\tJU\tPB 30\n\tBE\t]\n",
        encoding="utf-8")
    (legacy / "sym.seq").write_text(
        "M 1.0\tSTEP ONE START\n"
        "M 1.1\tSTEP TWO\n"
        "M 1.2\tSTEP THREE END\n"
        "M 8.0\tCHAIN ENABLE\n"
        "M 9.0\tCHAIN RESET\n"
        "E 0.1\tSENSOR POS B\n",
        encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------- threads --

def test_threads_split_where_components_merge(tmp_path):
    """M1.2 appears in M2.0's SET (trigger) — plain connected components
    would merge both chains into one; the thread split must NOT."""
    st = build_state_table(_mk_project(tmp_path))
    assert len(st["chains"]) == 2, "trigger referansı zincirleri birleştirmemeli"
    a, b = st["chains"]
    assert a["members"] == ["M1.0", "M1.1", "M1.2"]
    assert b["members"] == ["M2.0", "M2.1", "M2.2"]


def test_rails_detected_and_filtered_from_conditions(tmp_path):
    st = build_state_table(_mk_project(tmp_path))
    a = st["chains"][0]
    assert [r["addr"] for r in a["enable_rails"]] == ["M8.0"]
    assert [r["addr"] for r in a["reset_rails"]] == ["M9.0"]
    # step 2's displayed transition = only the distinctive sensor
    step2 = a["steps"][1]
    assert [(c["neg"], c["addr"]) for c in step2["conditions"]] == \
        [(False, "I0.1")]
    assert step2["conditions"][0]["label"] == "SENSOR POS B"


def test_cross_thread_trigger_recorded(tmp_path):
    st = build_state_table(_mk_project(tmp_path))
    trig = st["triggers"]
    assert any(t["from_step"] == "M1.2" and t["to_chain"] == "chain_2"
               for t in trig), "1N→2N tetiği kaydedilmeli"


def test_block_calls_in_source_order(tmp_path):
    _mk_project(tmp_path)
    calls = parse_block_calls(tmp_path / "_raw" / "legacy_code")
    assert calls == [("OB1", "PB9"), ("OB1", "PB10"), ("OB1", "PB30")]


# ---------------------------------------------------------------- output ---

def test_generate_writes_every_page(tmp_path):
    summ = generate_machine_dossier(_mk_project(tmp_path))
    out = tmp_path / "metadata" / "machine_dossier"
    expected = [
        "state_table.json", "01_operator_flow.svg", "02_block_structure.svg",
        "03_grafcet_1.svg", "03_grafcet_2.svg", "04_decision_table.md",
        "05_plant_summary.md", "06_ce_matrix.md",
    ]
    for name in expected:
        assert (out / name).exists(), f"{name} üretilmeli"
    assert summ.chains == 2 and summ.steps == 6
    # SVGs must be well-formed XML
    for svg in out.glob("*.svg"):
        ET.fromstring(svg.read_text(encoding="utf-8"))
    st = json.loads((out / "state_table.json").read_text(encoding="utf-8"))
    assert st["schema"] == "state_table/v1"


def test_grafcet_uses_symbols_and_marks_unknown(tmp_path):
    generate_machine_dossier(_mk_project(tmp_path))
    out = tmp_path / "metadata" / "machine_dossier"
    g1 = (out / "03_grafcet_1.svg").read_text(encoding="utf-8")
    assert "STEP TWO" in g1, "sembol adı diyagramda görünmeli"
    g2 = (out / "03_grafcet_2.svg").read_text(encoding="utf-8")
    assert "❓" in g2, "isimsiz sinyal ❓ ile işaretlenmeli — asla tahmin yok"


def test_every_generated_md_carries_draft_label(tmp_path):
    generate_machine_dossier(_mk_project(tmp_path))
    out = tmp_path / "metadata" / "machine_dossier"
    for md in out.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        assert "DRAFT" in text or "ENGINEER" in text, \
            f"{md.name}: dürüstlük etiketi zorunlu"


def test_block_structure_marks_unknown_role(tmp_path):
    generate_machine_dossier(_mk_project(tmp_path))
    out = tmp_path / "metadata" / "machine_dossier"
    bs = (out / "02_block_structure.svg").read_text(encoding="utf-8")
    assert "PB30" in bs and "❓" in bs, "rolü bilinmeyen blok ❓ kalmalı"
    assert "PB9" in bs


# ------------------------------------------------------------- decisions ---

def test_decision_rows_never_prefill_engineer_columns():
    rows = build_decision_rows(_EXAMPLE)
    assert len(rows) > 10, "örnek projeden satırlar gelmeli"
    for r in rows:
        assert r[-1] == "" and r[-2] == "", \
            "KARAR sütunları asla otomatik doldurulmaz"


def test_decisions_persist_across_regeneration(tmp_path):
    """The engineer's DECISION entries live in decisions.json — regenerating
    the dossier must NEVER erase them (they merge back into xlsx/md)."""
    import shutil

    from machine_dossier import load_decisions, save_decisions

    _mk_project(tmp_path)
    meta = tmp_path / "metadata"
    meta.mkdir(exist_ok=True)
    shutil.copy(_EXAMPLE / "metadata" / "RD01_IO_List.md",
                meta / "RD01_IO_List.md")

    rows = build_decision_rows(tmp_path)
    assert rows, "RD01 kopyasından satırlar gelmeli"
    addr = rows[0][0]

    save_decisions(tmp_path, {addr: {
        "decision": "frequency drive (VFD)",
        "impact": "3 DO removed, 1 AO added"}})
    assert load_decisions(tmp_path)[addr]["decision"] == "frequency drive (VFD)"

    # full regeneration — the classic data-loss moment
    generate_machine_dossier(tmp_path)
    rows2 = build_decision_rows(tmp_path)
    row = next(r for r in rows2 if r[0] == addr)
    assert row[-2] == "frequency drive (VFD)" and row[-1].startswith("3 DO"), \
        "yeniden üretim mühendis kararını SİLMEMELİ"
    md = (tmp_path / "metadata" / "machine_dossier" /
          "04_decision_table.md").read_text(encoding="utf-8")
    assert "frequency drive (VFD)" in md


def test_empty_decision_removes_entry(tmp_path):
    import shutil

    from machine_dossier import load_decisions, save_decisions

    _mk_project(tmp_path)
    (tmp_path / "metadata").mkdir(exist_ok=True)
    shutil.copy(_EXAMPLE / "metadata" / "RD01_IO_List.md",
                tmp_path / "metadata" / "RD01_IO_List.md")
    addr = build_decision_rows(tmp_path)[0][0]
    save_decisions(tmp_path, {addr: {"decision": "x", "impact": ""}})
    save_decisions(tmp_path, {addr: {"decision": "", "impact": ""}})
    assert addr not in load_decisions(tmp_path), "boşaltmak girdiyi kaldırmalı"


# ------------------------------------------------------------- OR / AST ---

def _mk_or_project(tmp_path: Path) -> Path:
    """Single thread where step 2 fires on (prev ∧ (I0.1 ∨ I0.4)) — the
    parenthesised OR that used to flatten into the AND list."""
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    (legacy / "PB9.AWL").write_text(
        "###PG:82000000\n"
        "[1\t\n\tA\tI 0.0\n\tS\tF 1.0\n"
        "\tA\tF 1.1\n\tR\tF 1.0\n\t***\t]\n"
        "[2\t\n\tA\tF 1.0\n\tA(\t\n\tO\tI 0.1\n\tO\tI 0.4\n\t)\t\n"
        "\tS\tF 1.1\n\tA\tF 1.2\n\tR\tF 1.1\n\t***\t]\n"
        "[3\t\n\tA\tF 1.1\n\tA\tI 0.2\n\tS\tF 1.2\n"
        "\tA\tI 0.3\n\tR\tF 1.2\n\tBE\t]\n",
        encoding="utf-8")
    (legacy / "sym.seq").write_text(
        "E 0.1\tSENSOR POS B\nE 0.4\tBYPASS HAND\n", encoding="utf-8")
    return tmp_path


def test_cond_groups_preserve_or_structure():
    """Unit: (prev ∧ (a ∨ ¬b) ∧ rail) → one OR group; hidden atoms only at
    AND level; OR alternatives are never hidden (meaning would change)."""
    from machine_dossier import _cond_groups
    from s5_logic_extract import And, Not, Or, Var

    e = And(And(Var("M1.0"), Or(Var("I0.1"), Not(Var("I0.4")))), Var("M8.0"))
    groups = _cond_groups(e, hide={"M1.0", "M8.0", "I0.1"},
                          names={"I0.1": "POS B"})
    assert groups == [{"kind": "or", "atoms": [
        {"neg": False, "addr": "I0.1", "label": "POS B"},
        {"neg": True, "addr": "I0.4", "label": ""},
    ]}], "OR alternatifleri tek grup kalmalı ve asla gizlenmemeli"


def test_cond_groups_deep_mix_falls_back_to_expr():
    """Sum-of-products at top level is NOT forced into a fake atom list —
    it falls back to the exact rendered expression (honest, never wrong)."""
    from machine_dossier import _cond_groups
    from s5_logic_extract import And, Or, Var

    e = Or(And(Var("I0.1"), Var("I0.2")), Var("I0.3"))
    groups = _cond_groups(e, set(), {})
    assert len(groups) == 1 and groups[0]["kind"] == "expr"
    assert "I0.3" in groups[0]["text"]


def test_grafcet_draws_or_alternatives(tmp_path):
    """Integration: parenthesised OR in the AWL survives into
    state_table.cond_groups and the GRAFCET SVG shows ∨ alternatives."""
    _mk_or_project(tmp_path)
    st = build_state_table(tmp_path)
    step2 = st["chains"][0]["steps"][1]
    ors = [g for g in step2["cond_groups"] if g["kind"] == "or"]
    assert len(ors) == 1, "OR yapısı düz listeye inmemeli"
    assert {(a["neg"], a["addr"]) for a in ors[0]["atoms"]} == \
        {(False, "I0.1"), (False, "I0.4")}
    assert ors[0]["atoms"][0]["label"] == "SENSOR POS B"

    generate_machine_dossier(tmp_path)
    svg = (tmp_path / "metadata" / "machine_dossier" /
           "03_grafcet_1.svg").read_text(encoding="utf-8")
    assert "∨" in svg and "BYPASS HAND" in svg


def test_operator_flow_honest_when_no_chain(tmp_path):
    (tmp_path / "_raw" / "legacy_code").mkdir(parents=True)
    summ = generate_machine_dossier(tmp_path)
    assert any("no proven step chain" in w for w in summ.warnings)
    flow = (tmp_path / "metadata" / "machine_dossier" /
            "01_operator_flow.svg").read_text(encoding="utf-8")
    assert "honest refusal" in flow
