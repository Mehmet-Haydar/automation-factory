"""Proof tests — field-audit (saha-uygunluğu) Faz-2 fixes.

B-11: no hardcoded version in index.html (support screenshots showed v3.3.0
      while the app was v3.8.1).
B-13: primitive dev workflows hidden from the GUI workflow list.
B-15: Gate 6 honestly named (PLCSIM licence / manual-test declaration).
B-06: RD11/RD12 get a platform-based N/A suggestion on pre-TIA machines.
Parity: dead Backend.run_action removed from app.js.
"""
from __future__ import annotations

import json

import factory_web as fw

APP_JS = fw.FACTORY_ROOT / "webgui" / "app.js"
INDEX_HTML = fw.FACTORY_ROOT / "webgui" / "index.html"


# ---------------------------------------------------------------------------
# B-11 — version comes from get_state(), never a literal in the HTML
# ---------------------------------------------------------------------------

def test_index_html_has_no_hardcoded_version():
    import re
    html = INDEX_HTML.read_text(encoding="utf-8")
    m = re.search(r'id="app-version"[^>]*>([^<]*)<', html)
    assert m, "app-version elementi index.html'de yok"
    assert not re.search(r"v\d+\.\d+\.\d+", m.group(1)), (
        f"app-version hâlâ hardcoded sürüm içeriyor: '{m.group(1)}' — "
        "get_state().version doldurmalı (B-11)."
    )


# ---------------------------------------------------------------------------
# Parity — dead Backend.run_action removed (no Python counterpart exists)
# ---------------------------------------------------------------------------

def test_dead_run_action_removed_from_backend_wrapper():
    js = APP_JS.read_text(encoding="utf-8")
    assert '_call("run_action"' not in js, (
        "Backend.run_action hâlâ app.js'te — Python tarafında karşılığı yok, "
        "çağrılırsa 'method not found' ile düşer."
    )


def test_api_has_no_run_action_method():
    assert not hasattr(fw.Api, "run_action")


# ---------------------------------------------------------------------------
# B-13 — dev-only workflows hidden from the GUI list, still runnable
# ---------------------------------------------------------------------------

def test_get_workflows_hides_dev_chains():
    api = fw.Api()
    names = {w["name"] for w in api.get_workflows()}
    from workbench.core.ai_runner import DEV_ONLY_WORKFLOWS, BUILTIN_WORKFLOWS
    assert names.isdisjoint(DEV_ONLY_WORKFLOWS), (
        f"Dev-only workflow'lar GUI listesine sızdı: {names & DEV_ONLY_WORKFLOWS}"
    )
    # The real methodology stays visible…
    assert "Retrofit Pre-Analysis" in names
    # …and the hidden ones still exist for tests/scripting.
    for wf in DEV_ONLY_WORKFLOWS:
        assert wf in BUILTIN_WORKFLOWS


# ---------------------------------------------------------------------------
# B-15 — Gate 6 name does not overstate what was verified
# ---------------------------------------------------------------------------

def test_gate6_is_not_called_plain_simulation():
    assert fw.GATE_NAMES[5] != "Simulation", (
        "Gate 6 'Simulation' adı PLCSIM koşusu yapılmış izlenimi verir; "
        "manuel-test beyanıyla da geçilebiliyor (B-15)."
    )
    assert "PLCSIM" in fw.GATE_NAMES[5]


def test_gate6_name_synced_to_frontend():
    js = APP_JS.read_text(encoding="utf-8")
    assert fw.GATE_NAMES[5] in js, (
        "app.js statik GATE_NAMES backend ile senkron değil"
    )


# ---------------------------------------------------------------------------
# B-06 — platform-based N/A suggestion for RD11/RD12
# ---------------------------------------------------------------------------

def _minimal_project(tmp_path):
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 1, "project_type": "retrofit"}), encoding="utf-8")
    legacy = tmp_path / "_raw" / "legacy_code"
    legacy.mkdir(parents=True)
    # .s5d extension votes S5 — an unmistakably pre-TIA platform
    (legacy / "prog.s5d").write_bytes(b"\x00\x01" * 200)
    (tmp_path / "metadata").mkdir()
    return tmp_path


def test_rd11_rd12_get_na_hint_on_legacy_platform(tmp_path):
    api = fw.Api()
    api.root = _minimal_project(tmp_path)
    model = api.get_gate_model()
    gate2 = next(g for g in model["gates"] if g["n"] == 2)
    docs = {d["rd"]: d for d in gate2["docs"]}
    for rd in ("RD11", "RD12"):
        assert docs[rd].get("na_hint"), (
            f"{rd} için eski-platform N/A önerisi yok (B-06) — mühendis "
            "var olmayan HMI export'unu aramaya devam eder."
        )
    # Other RDs must NOT carry the hint
    assert not docs["RD04"].get("na_hint")


def test_no_na_hint_without_detected_platform(tmp_path):
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps({"gate": 1, "project_type": "retrofit"}), encoding="utf-8")
    (tmp_path / "metadata").mkdir()
    api = fw.Api()
    api.root = tmp_path
    model = api.get_gate_model()
    gate2 = next(g for g in model["gates"] if g["n"] == 2)
    docs = {d["rd"]: d for d in gate2["docs"]}
    assert not docs["RD11"].get("na_hint"), (
        "Platform tespit edilmeden N/A önerisi verilmemeli (yanlış yönlendirme)"
    )
