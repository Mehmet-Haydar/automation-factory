"""Proof tests — decision cascade / delta engine (dilim ④, 2026-07-07).

Pins the contract: ONE decision vocabulary (KEEP/REPLACE/DROP, DE/EN/TR,
DROP > REPLACE > KEEP priority, honest UNCLASSIFIED); the cascade reports
propagation against the SAME evidence the Gate-3 reconciliation reads
(they can never disagree); the engine is read-only; the Old⇄Target dossier
page regenerates with every decisions save and never touches decisions.
"""

from __future__ import annotations

import json
from pathlib import Path

import decision_cascade as dc
import factory_web as fw

_RD01_HEADER = (
    "| Tag | Address | Type | Dir | Equipment | Description | NormalState | "
    "EngUnit | RangeMin | RangeMax | Safety | SrcModule | OldTag | Notes | Status |\n"
    "|-----|---------|------|-----|-----------|-------------|-------------|"
    "---------|----------|---------|--------|----------|--------|-------|--------|\n"
)

_RD01 = (
    "---\nstatus: DRAFT_UNVERIFIED\n---\n# RD01 IO List\n\n## Signals\n"
    + _RD01_HEADER
    + "| LMP_RUN | %Q5.0 | DQ | OUT | H1 | Meldeleuchte laeuft | | | | | NO | PB2 | A 5.0 | | DRAFT_UNVERIFIED |\n"
    + "| MOT_A | %Q0.0 | DQ | OUT | M1 | Motorschuetz Y-Delta | | | | | NO | PB1 | A 0.0 | | DRAFT_UNVERIFIED |\n"
    + "| ESTOP_1 | %I0.3 | SAFE_DI | IN | S0 | NOT-AUS Pult | | | | | YES | PB1 | E 0.3 | | DRAFT_UNVERIFIED |\n"
)

_RD11_HEADER = (
    "| HMI_TagID | PLC_Tag | ScreenRef | ElementType | Label_EN | Label_TR | "
    "Label_DE | ReadWrite | MinValue | MaxValue | EngUnit | Notes |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
)

_RD11_WITH_LAMP = (
    "# RD11_HMI\n\n## Sheet 2: TagList\n\n" + _RD11_HEADER
    + "| HMI_LMP_RUN | DB_HMI.Sts.bRun | SCR001 | Indicator | Running |  | "
    "LAEUFT | Read | | | | legacy Q5.0 |\n")


def _project(tmp_path: Path, rd11: str | None = _RD11_WITH_LAMP) -> Path:
    md = tmp_path / "metadata"
    md.mkdir(exist_ok=True)
    (md / "RD01_IO_List.md").write_text(_RD01, encoding="utf-8")
    if rd11 is not None:
        (md / "RD11_HMI.md").write_text(rd11, encoding="utf-8")
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 3}), encoding="utf-8")
    return tmp_path


def _decide(root: Path, entries: dict) -> None:
    out = root / "metadata" / "machine_dossier"
    out.mkdir(parents=True, exist_ok=True)
    (out / "decisions.json").write_text(
        json.dumps(entries, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------ vocabulary --

def test_verb_vocabulary_de_en_tr():
    assert dc.parse_verb("bleibt 1:1") == "KEEP"
    assert dc.parse_verb("KEEP as is") == "KEEP"
    assert dc.parse_verb("kalacak, wie bisher") == "KEEP"
    assert dc.parse_verb("Ersatz durch FU") == "REPLACE"
    assert dc.parse_verb("Y-Delta → VFD") == "REPLACE"
    assert dc.parse_verb("kontaktör yerine sürücü") == "REPLACE"
    assert dc.parse_verb("entfällt ersatzlos") == "DROP"
    assert dc.parse_verb("DROP - lamp obsolete") == "DROP"
    assert dc.parse_verb("kaldırılacak") == "DROP"


def test_verb_priority_and_honesty():
    # DROP beats a courtesy KEEP/REPLACE fragment in the same sentence
    assert dc.parse_verb("bleibt nicht — ersatzlos entfällt") == "DROP"
    # REPLACE beats KEEP
    assert dc.parse_verb("bleibt, aber neu als FU") == "REPLACE"
    # unknown text is never guessed
    assert dc.parse_verb("") == "UNCLASSIFIED"
    assert dc.parse_verb("siehe E-Plan Blatt 12") == "UNCLASSIFIED"


# ------------------------------------------------------------ cascade -----

def test_drop_with_remaining_hmi_ref_is_pending(tmp_path):
    root = _project(tmp_path)
    _decide(root, {"%Q5.0": {"decision": "entfällt ersatzlos", "impact": ""}})
    c = dc.compute_cascade(root)
    d = c["devices"][0]
    assert d["verb"] == "DROP" and d["pending"] is True
    a = next(a for a in d["affected"] if a["artifact"] == "RD11")
    assert a["key"] == "HMI_LMP_RUN" and a["status"] == "pending"
    assert c["summary"]["DROP"] == 1 and c["summary"]["pending"] == 1


def test_drop_propagated_when_no_ref_remains(tmp_path):
    root = _project(tmp_path, rd11=None)   # no HMI table → nothing references it
    _decide(root, {"%Q5.0": {"decision": "DROP", "impact": ""}})
    c = dc.compute_cascade(root)
    d = c["devices"][0]
    assert d["pending"] is False
    assert any(a["status"] == "propagated" for a in d["affected"])


def test_replace_drive_cascades_fb_and_hmi(tmp_path):
    root = _project(tmp_path)
    out = root / "_output" / "scl"
    out.mkdir(parents=True)
    (out / "_assembly_manifest.json").write_text(
        json.dumps({"devices": {"M1": {"fb": "FB_Motor_DOL"}}}), encoding="utf-8")
    _decide(root, {"%Q0.0": {"decision": "Ersatz durch FU (Frequenzumrichter)",
                             "impact": "Sollwert + Störworte neu"}})
    c = dc.compute_cascade(root)
    d = c["devices"][0]
    assert d["verb"] == "REPLACE" and d["equipment"] == "M1"
    fb = next(a for a in d["affected"] if a["artifact"] == "FB")
    assert fb["key"] == "FB_Motor_DOL" and fb["status"] == "pending"
    assert d["pending"] is True


def test_keep_cascades_nothing_and_safety_is_flagged(tmp_path):
    root = _project(tmp_path)
    _decide(root, {"%I0.3": {"decision": "bleibt 1:1 (hardwired)", "impact": ""}})
    c = dc.compute_cascade(root)
    d = c["devices"][0]
    assert d["verb"] == "KEEP" and d["affected"] == [] and d["pending"] is False
    assert d["safety"] is True, "NOT-AUS cihazı işaretli kalmalı"


def test_shared_vocabulary_with_gate3(tmp_path):
    """The reconciliation and the cascade read the SAME verb — a decision
    the cascade calls DROP must raise gate-3's decision_not_propagated
    while the tag remains (single source of truth, no drift)."""
    import gate3_consistency as g3c
    root = _project(tmp_path)
    _decide(root, {"%Q5.0": {"decision": "entfällt ersatzlos", "impact": ""}})
    assert dc.parse_verb("entfällt ersatzlos") == "DROP"
    r = g3c.run(root)
    assert any(f["kind"] == "decision_not_propagated" for f in r["findings"])


# ------------------------------------------------------------ delta page --

def test_delta_page_written_and_refreshed_on_save(tmp_path):
    from machine_dossier import save_decisions
    root = _project(tmp_path)
    save_decisions(root, {"%Q5.0": {"decision": "entfällt ersatzlos",
                                    "impact": ""}})
    fp = root / "metadata" / "machine_dossier" / dc.DELTA_FILE
    assert fp.is_file()
    text = fp.read_text(encoding="utf-8")
    assert "OLD ⇄ TARGET" in text and "DROP" in text and "[pending]" in text
    # decisions are never touched by the byproduct
    dj = json.loads((root / "metadata" / "machine_dossier" /
                     "decisions.json").read_text(encoding="utf-8"))
    assert dj["%Q5.0"]["decision"] == "entfällt ersatzlos"
    # refresh follows the decisions (DROP → KEEP flips the page)
    save_decisions(root, {"%Q5.0": {"decision": "bleibt 1:1", "impact": ""}})
    assert "KEEP" in fp.read_text(encoding="utf-8")


def test_endpoint_and_gui_wiring(tmp_path):
    root = _project(tmp_path)
    _decide(root, {"%Q5.0": {"decision": "entfällt ersatzlos", "impact": ""}})
    api = fw.Api()
    api.root = root
    api.settings = {"username": "Eng"}
    r = api.get_decision_cascade()
    assert r["ok"] and r["summary"]["DROP"] == 1
    assert r["devices"][0]["addr"] == "%Q5.0"
    # GUI: the dossier grid carries the Old→Target toggle wired to the endpoint
    app_js = (Path(fw.__file__).resolve().parent.parent
              / "webgui" / "app.js").read_text(encoding="utf-8")
    assert "get_decision_cascade" in app_js
    assert "dg-delta" in app_js and "renderDecisionDelta" in app_js
